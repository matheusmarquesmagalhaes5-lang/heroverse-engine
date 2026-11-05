#!/usr/bin/env python3
"""Local native review (owner 2026-11-02): one exact private master -> audio HEARD + picture SEEN evidence; never an approval.

Replaces Gemini as the REQUIRED provider of the native review (E268). Everything runs on the GitHub runner, no
secret, no provider call, no spend:
  1. AUDIO HEARD   pinned faster-whisper small.en (CPU, int8, word timestamps) over the master's whole audio, compared with the
                   script (the build report's timed sentences, else the episode record or the plan): missing, extra,
                   garbled words, speech cut at the edges, sentence timing against the captions' timeline.
  2. AUDIO QUALITY ffmpeg ebur128 (integrated loudness, true peak, LRA), clipping, silence/dropout, silence inside speech,
                   voice against music balance (RMS, unweighted, stated as such).
  3. VIDEO SEEN    a dense timecoded frame sheet (1 frame / 2 s) for the session reviewer's own eyes, black / frozen /
                   duplicate-frame detection, scene-change pacing, caption-burn presence.
The result is `native-review-public-v1` (the shape native_review.py writes: same file name, same artifact name, same
issue format "MM:SS [category] text", same keys) so every consumer of the Gemini evidence reads it unchanged. Machine
measures are not a score: the rubric scores stay null until the session reviewer (claude_review) has looked at the
frame sheets and read the timestamped transcript; `visual_review_required` is always true.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_review as nr  # noqa: E402  (stdlib only; the Gemini provider stays, no longer required)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROVIDER = nr.DEFAULT_PROVIDER   # 'local'
VERSION = 'local-review-v1'
# Pinned ASR: faster-whisper small.en (CPU, int8) at one HuggingFace commit, every file verified by sha256 before use.
ASR = {'package': 'faster-whisper==1.2.1', 'repo': 'Systran/faster-whisper-small.en',
       'revision': 'd1d751a5f8271d482d14ca55d9e2deeebbae577f',
       'files': {'config.json': '666a9605530ac1f61fa8177f3702b4dacec9966749e42610839fcc32661d5fae',
                 'tokenizer.json': '929c5252409436dce1b38a75d1abbcb5e132d170d8e324e4e04ed915fa2d22df',
                 'vocabulary.txt': 'ff77588746d3a2595d32ab5b69ffd7b95ce2441ac57533cb66fc3eb575a115cf',
                 'model.bin': '62b2a45b05ee59acb4a5341b33ee35e041395d378d418a18acfe4c9e768ee37a'}}
TARGET_LUFS, LUFS_TOLERANCE = -14.0, 1.5
TRUE_PEAK_MAX = -1.0            # dBTP; the compose step limits below this
SPEECH_GAP_MAX = 1.5            # s of silence between two words of one sentence
SILENCE_DB, SILENCE_MIN = -45, 0.8
EDGE_FREE_START, EDGE_FREE_END = 0.5, 2.5   # an intended fade in / out
SHEET_STEP, SHEET_TILE = 2, (6, 5)           # 1 frame per 2 s, 30 frames (60 s) per sheet
MIN_COVERAGE = 0.95
MAX_DRIFT_START, MAX_DRIFT_END = 1.0, 1.5   # whisper's word times jitter by about 0.8 s (flood run 41509047639)
MIN_VOICE_OVER_MUSIC_DB = 4.0
FREEZE_MIN = 3.0
# Owner-approved research 2026-11-04 (TOOLS-MARKET item 2): per-sentence word error rate against the exact script and UTMOS22
# naturalness, both CPU, both WARN ONLY. The thresholds are PROVISIONAL (not yet calibrated on accepted masters); they never
# enter `issues`, `machine_verdict` or any gate. Promoting one to a refusal needs a recorded calibration (OPERATIONS.md).
WER_SENTENCE_WARN, WER_OVERALL_WARN, WER_MIN_WORDS = 0.30, 0.12, 4
UTMOS_SENTENCE_WARN, UTMOS_MEAN_WARN = 2.0, 2.8     # MOS 1-5 on the full mix (music lowers it); see UTMOS['limits']
UTMOS_MAX_CLIPS, UTMOS_CLIP_MIN, UTMOS_CLIP_MAX = 120, 1.5, 20.0
UTMOS = {'repo': 'tarepan/SpeechMOS', 'tag': 'v1.2.0', 'commit': 'ed25eacbfa42b99156c36ebec67a733b5dbb9b79',
         'weights': 'utmos22_strong_step7459_v1.pt', 'weights_bytes': 411179119,
         'weights_sha256': '38aa51ab79e2a4e09a1449758a4b37e9cbb2e8235a49662a732d33a9ba1e9bff',
         'packages': 'torch==2.5.1+cpu torchaudio==2.5.1+cpu',
         'limits': 'UTMOS22 scores clean speech; a mix with music reads lower, so it is a trend and a warning, never a score'}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
CATEGORY_CRITERION = {'a': 'audio_clarity_and_mix', 'b': 'opening_and_promise', 'c': 'audio_clarity_and_mix',
                      'd': 'captions_readable_and_synced', 'f': 'picture_quality'}


class Refusal(nr.Refusal):
    pass


def require(ok, code):
    if not ok:
        raise Refusal(code)


def run(cmd, timeout=3600, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, **kw)


def clock(seconds):
    s = max(0.0, float(seconds))
    return f'{int(s // 60):02d}:{s % 60:05.2f}'


def issue(seconds, category, text):
    return f'{clock(seconds)} [{category}] {text}'


# ---------------------------------------------------------------- inputs
def inputs(event=None):
    if event is None:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    i = event['inputs']
    p = i['plan']
    require(re.fullmatch(r'migration/production/bible/(plans|compilations|cuts|reflections)/[a-z0-9-]+\.json', p), 'PLAN_INVALID')
    require((ROOT / p).is_file(), 'PLAN_MISSING')
    require(re.fullmatch(r'[0-9a-f]{64}', i['sha256']), 'HASH_INVALID')
    return {'plan': p, 'sha256': i['sha256']}


# ---------------------------------------------------------------- the script the master must speak
def norm_tokens(text):
    text = str(text).lower().replace('’', "'").replace('‘', "'").replace('-', ' ').replace('—', ' ')
    return [t for t in (re.sub(r"[^a-z0-9']", '', w).strip("'") for w in text.split()) if t]


def reference_for(plan_path, sha, root=ROOT):
    """{'source', 'sentences': [{text, start, end, speaker}]} where start/end are None when the reference is untimed."""
    root = Path(root)
    for f in sorted((root / 'migration/evidence/episodes').glob('*/report-*.json')):
        try:
            c = json.loads(f.read_text()).get('composed') or {}
        except ValueError:
            continue
        if c.get('output_sha256') == sha and isinstance(c.get('sentences'), list) and c['sentences']:
            return {'source': f'{f.relative_to(root)} composed.sentences (timed)',
                    'sentences': [{'text': s['text'], 'start': s.get('start'), 'end': s.get('end'),
                                   'speaker': s.get('speaker')} for s in c['sentences'] if s.get('text')]}
    for f in sorted((root / 'migration/production/bible/episodes').glob('*.json')):
        try:
            rec = json.loads(f.read_text())
        except ValueError:
            continue
        if rec.get('output_sha256') == sha and isinstance(rec.get('narration'), list):
            return {'source': f'{f.relative_to(root)} narration',
                    'sentences': [{'text': n['text'], 'start': None, 'end': None, 'speaker': n.get('speaker')}
                                  for n in rec['narration'] if n.get('text')]}
    try:
        plan = json.loads((root / plan_path).read_text())
    except (OSError, ValueError):
        plan = {}
    items = plan.get('narration') if isinstance(plan, dict) else None
    if isinstance(items, list) and items:
        return {'source': f'{plan_path} narration (God\'s cold-open line and shot lines not included)',
                'sentences': [{'text': n['text'], 'start': None, 'end': None, 'speaker': n.get('speaker')}
                              for n in items if isinstance(n, dict) and n.get('text')]}
    return {'source': None, 'sentences': []}


# ---------------------------------------------------------------- 1. audio heard
ONES = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen '
        'seventeen eighteen nineteen').split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()
ORDINAL = {'one': 'first', 'two': 'second', 'three': 'third', 'five': 'fifth', 'eight': 'eighth', 'nine': 'ninth',
           'twelve': 'twelfth'}


def spell_int(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], 'hundred'] + (spell_int(n % 100) if n % 100 else [])
    return spell_int(n // 1000) + ['thousand'] + (spell_int(n % 1000) if n % 1000 else [])


def spell_token(t):
    """'950' -> nine hundred fifty, '17th' -> seventeenth: the script spells numbers, the ASR often writes digits."""
    m = re.fullmatch(r'(\d{1,6})(st|nd|rd|th)?', t)
    if not m:
        return [t]
    words = spell_int(int(m.group(1)))
    if m.group(2):
        last = words[-1]
        words[-1] = ORDINAL.get(last, last[:-1] + 'ieth' if last.endswith('y') else last + 'th')
    return words


def flatten_heard(segments):
    words = []
    for seg in segments:
        for w in seg.get('words', []):
            for t in norm_tokens(w['word']):
                for piece in spell_token(t):
                    words.append({'t': piece, 'start': float(w['start']), 'end': float(w['end'])})
    return words


def compare(sentences, heard):
    """Word-level alignment of the script against the heard words (difflib, exact then near-match)."""
    exp, owner = [], []
    for n, s in enumerate(sentences):
        for t in norm_tokens(s['text']):
            exp.append(t)
            owner.append(n)
    got = [w['t'] for w in heard]
    matcher = difflib.SequenceMatcher(None, exp, got, autojunk=False)
    matched = [None] * len(exp)      # index into heard
    missing, extra, garbled = [], [], []

    def heard_time(j):
        if not heard:
            return 0.0
        return heard[min(max(j, 0), len(heard) - 1)]['start']

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                matched[i1 + k] = j1 + k
        elif tag == 'replace':
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                a, b = exp[i1 + k], got[j1 + k]
                ratio = difflib.SequenceMatcher(None, a, b).ratio()
                if ratio >= 0.75:
                    matched[i1 + k] = j1 + k          # near-match (spelling, number words, proper names)
                else:
                    garbled.append({'expected': a, 'heard': b, 'sentence': owner[i1 + k], 'at': heard_time(j1 + k)})
            if i2 - i1 > pairs:
                run_ = list(range(i1 + pairs, i2))
                missing.append({'words': [exp[x] for x in run_], 'sentence': owner[run_[0]], 'at': heard_time(j1 + pairs)})
            if j2 - j1 > pairs:
                extra.append({'words': got[j1 + pairs:j2], 'at': heard_time(j1 + pairs)})
        elif tag == 'delete':
            missing.append({'words': exp[i1:i2], 'sentence': owner[i1], 'at': heard_time(j1)})
        elif tag == 'insert':
            extra.append({'words': got[j1:j2], 'at': heard_time(j1)})
    done = sum(1 for m in matched if m is not None)
    per = {}
    for k, m in enumerate(matched):
        t = per.setdefault(owner[k], [0, 0])
        t[1] += 1
        t[0] += m is not None
    return {'expected_words': len(exp), 'heard_words': len(got), 'matched_words': done,
            'coverage': round(done / len(exp), 4) if exp else None,
            'missing': missing, 'extra': extra, 'garbled': garbled,
            'sentence_coverage': {n: round(a / b, 3) for n, (a, b) in per.items() if b},
            'matched_index': matched, 'owner': owner}


def sentence_timing(sentences, heard, cmp_):
    """Heard start/end of each timed sentence against the timeline its captions use."""
    out = []
    by_sentence = {}
    for k, j in enumerate(cmp_['matched_index']):
        if j is not None:
            by_sentence.setdefault(cmp_['owner'][k], []).append(j)
    for n, s in enumerate(sentences):
        js = by_sentence.get(n)
        if not js or s.get('start') is None or s.get('end') is None:
            continue
        hs, he = heard[min(js)]['start'], heard[max(js)]['end']
        out.append({'sentence': n, 'text': s['text'][:60], 'start_offset': round(hs - s['start'], 2),
                    'end_offset': round(he - s['end'], 2), 'timeline_start': s['start'], 'timeline_end': s['end']})
    return out


def speech_gaps(sentences, heard):
    """Silence longer than SPEECH_GAP_MAX between two heard words inside one timed sentence."""
    gaps = []
    for a, b in zip(heard, heard[1:]):
        gap = b['start'] - a['end']
        if gap <= SPEECH_GAP_MAX:
            continue
        inside = any(s.get('start') is not None and s['start'] - 0.1 <= a['start'] and b['end'] <= s['end'] + 0.1
                     for s in sentences)
        if inside:
            gaps.append({'start': round(a['end'], 2), 'seconds': round(gap, 2)})
    return gaps


# ---------------------------------------------------------------- 1b. per-sentence WER and UTMOS (WARN only)
def sentence_wer(sentences, heard):
    """Word error rate per script sentence from the same normalised alignment as compare(): a near-spelled word
    (ratio >= 0.75) is still a substitution here (strict WER) and is also counted in `near`."""
    exp, owner = [], []
    for n, s in enumerate(sentences):
        for t in norm_tokens(s['text']):
            exp.append(t)
            owner.append(n)
    got = [w['t'] for w in heard]
    rows = {}

    def row(n):
        return rows.setdefault(n, {'sentence': n, 'ref_words': 0, 'sub': 0, 'del': 0, 'ins': 0, 'near': 0, 'at': None})

    for n in owner:
        row(n)['ref_words'] += 1

    def at(n, j):
        if rows[n]['at'] is None and heard:
            rows[n]['at'] = round(heard[min(max(j, 0), len(heard) - 1)]['start'], 2)

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, exp, got, autojunk=False).get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                at(owner[i1 + k], j1 + k)
        elif tag == 'replace':
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                r = row(owner[i1 + k])
                at(owner[i1 + k], j1 + k)
                r['sub'] += 1
                r['near'] += difflib.SequenceMatcher(None, exp[i1 + k], got[j1 + k]).ratio() >= 0.75
            for k in range(i1 + pairs, i2):
                row(owner[k])['del'] += 1
                at(owner[k], j1 + pairs)
            if j2 - j1 > pairs:
                row(owner[i2 - 1] if i2 > i1 else owner[max(i1 - 1, 0)])['ins'] += j2 - j1 - pairs
        elif tag == 'delete':
            for k in range(i1, i2):
                row(owner[k])['del'] += 1
                at(owner[k], j1)
        elif tag == 'insert' and exp:
            row(owner[i1 - 1] if i1 > 0 else owner[0])['ins'] += j2 - j1
    out = []
    for n in sorted(rows):
        r = rows[n]
        r['wer'] = round((r['sub'] + r['del'] + r['ins']) / r['ref_words'], 3) if r['ref_words'] else None
        if r['at'] is None and sentences[n].get('start') is not None:
            r['at'] = sentences[n]['start']
        out.append(r)
    total = sum(r['ref_words'] for r in out)
    errors = sum(r['sub'] + r['del'] + r['ins'] for r in out)
    return {'overall': {'ref_words': total, 'errors': errors, 'wer': round(errors / total, 4) if total else None,
                        'near_matches': sum(r['near'] for r in out)},
            'sentences': out}


def sentence_spans(sentences, heard, cmp_):
    """Heard (start, end) of each sentence from its matched words (the clip UTMOS listens to)."""
    by = {}
    for k, j in enumerate(cmp_['matched_index']):
        if j is not None:
            by.setdefault(cmp_['owner'][k], []).append(j)
    return {n: (heard[min(js)]['start'], heard[max(js)]['end']) for n, js in by.items()}


def utmos_scores(samples, spans, predict, rate=16000):
    """predict(list of float32 arrays) -> list of MOS floats. Clips are the heard sentence spans, 1.5-20 s, evenly
    thinned to UTMOS_MAX_CLIPS; the model is the pinned UTMOS22 strong learner (CPU)."""
    clips = [(n, a, b) for n, (a, b) in sorted(spans.items()) if UTMOS_CLIP_MIN <= b - a <= UTMOS_CLIP_MAX]
    if len(clips) > UTMOS_MAX_CLIPS:
        step = len(clips) / UTMOS_MAX_CLIPS
        clips = [clips[int(k * step)] for k in range(UTMOS_MAX_CLIPS)]
    if not clips:
        return {'status': 'NO_CLIPS', 'sentences': []}
    scores = predict([samples[int(a * rate):int(b * rate)] for _, a, b in clips])
    rows = [{'sentence': n, 'at': round(a, 2), 'seconds': round(b - a, 1), 'mos': round(float(m), 3)}
            for (n, a, b), m in zip(clips, scores)]
    values = [r['mos'] for r in rows]
    return {'status': 'OK', 'clips': len(rows), 'mean': round(sum(values) / len(values), 3), 'min': min(values),
            'sentences': rows}


def load_utmos(tool_dir):
    """Pinned UTMOS22 on CPU from `tool_dir` (code at UTMOS['commit'], the weights file at UTMOS['weights_sha256']),
    or None when the optional step did not install it. Never raises: the review does not depend on it."""
    try:
        tool_dir = Path(tool_dir)
        weights = tool_dir / UTMOS['weights']
        if not (tool_dir / 'code').is_dir() or not weights.is_file():
            return None
        h = hashlib.sha256()
        with open(weights, 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                h.update(block)
        if h.hexdigest() != UTMOS['weights_sha256']:
            return None
        import torch
        sys.path.insert(0, str(tool_dir / 'code'))
        from speechmos.utmos22.strong.model import UTMOS22Strong
        model = UTMOS22Strong()
        model.load_state_dict(torch.load(weights, map_location='cpu'))
        model.eval()
        torch.set_num_threads(os.cpu_count() or 2)

        def predict(clips):
            out = []
            with torch.no_grad():
                for c in clips:
                    out.append(float(model(torch.from_numpy(c).unsqueeze(0), 16000)[0]))
            return out
        return predict
    except Exception:   # noqa: BLE001 - optional tool: absence is reported as NOT_RUN, not a failed review
        return None


def warnings_for(m):
    """(seconds, text) WARNs from WER and UTMOS. Provisional thresholds; never defects, never a gate."""
    out = []
    a = m['audio']
    w = a.get('wer')
    if w:
        o = w['overall']
        if o['wer'] is not None and o['wer'] > WER_OVERALL_WARN:
            out.append((0, f"overall word error rate {o['wer']:.1%} against the script ({o['errors']} of {o['ref_words']} words)"))
        for r in w['sentences']:
            if r['ref_words'] >= WER_MIN_WORDS and r['wer'] is not None and r['wer'] > WER_SENTENCE_WARN:
                out.append((r['at'] or 0, f"sentence {r['sentence']} word error rate {r['wer']:.0%} "
                                          f"({r['sub']} substituted, {r['del']} missing, {r['ins']} extra of {r['ref_words']})"))
    u = a.get('utmos')
    if u and u.get('status') == 'OK':
        if u['mean'] < UTMOS_MEAN_WARN:
            out.append((0, f"mean UTMOS naturalness {u['mean']} over {u['clips']} sentences is below {UTMOS_MEAN_WARN}"))
        for r in u['sentences']:
            if r['mos'] < UTMOS_SENTENCE_WARN:
                out.append((r['at'], f"sentence {r['sentence']} UTMOS naturalness {r['mos']} is below {UTMOS_SENTENCE_WARN} (listen to it)"))
    return sorted(out)


# ---------------------------------------------------------------- 2. audio quality
def probe(path):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,avg_frame_rate,sample_rate,channels',
             '-of', 'json', str(path)])
    require(r.returncode == 0, 'FFPROBE_FAILED')
    j = json.loads(r.stdout)
    streams = j.get('streams', [])
    v = next((s for s in streams if s.get('codec_type') == 'video'), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    return {'duration': float(j['format']['duration']), 'has_video': v is not None, 'has_audio': a is not None,
            'width': (v or {}).get('width'), 'height': (v or {}).get('height'),
            'fps': (v or {}).get('avg_frame_rate'), 'sample_rate': (a or {}).get('sample_rate')}


def parse_ebur128(stderr):
    """Integrated loudness (LUFS), loudness range and true peak (dBTP) from ffmpeg's ebur128 summary."""
    tail = stderr[stderr.rfind('Summary:'):] if 'Summary:' in stderr else ''
    def grab(label, unit):
        m = re.search(rf'^\s*{label}:\s*(-?[\d.]+|-inf)\s*{unit}', tail, re.M)
        return None if not m or m.group(1) == '-inf' else float(m.group(1))
    return {'integrated_lufs': grab('I', 'LUFS'), 'lra': grab('LRA', 'LU'), 'true_peak_dbtp': grab('Peak', 'dBFS')}


def loudness(path):
    r = run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    m = parse_ebur128(r.stderr.decode('utf-8', 'replace'))
    require(m['integrated_lufs'] is not None, 'EBUR128_UNREADABLE')
    return m


def parse_astats(stderr):
    """Overall peak level (dBFS) and the number of samples at the peak (a clipped master has many)."""
    block = stderr[stderr.rfind('Overall'):] if 'Overall' in stderr else ''
    lvl = re.search(r'Peak level dB:\s*(-?[\d.]+|-inf)', block)
    cnt = re.search(r'Peak count:\s*(\d+)', block)
    return {'peak_dbfs': float(lvl.group(1)) if lvl and lvl.group(1) != '-inf' else None,
            'peak_count': int(cnt.group(1)) if cnt else None}


def clipping(path):
    r = run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'astats', '-f', 'null', '-'])
    return parse_astats(r.stderr.decode('utf-8', 'replace'))


def silences(path, duration):
    r = run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af',
             f'silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN}', '-f', 'null', '-'])
    text = r.stderr.decode('utf-8', 'replace')
    starts = [float(x) for x in re.findall(r'silence_start:\s*(-?[\d.]+)', text)]
    ends = [(float(a), float(b)) for a, b in re.findall(r'silence_end:\s*(-?[\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)', text)]
    out = []
    for k, s in enumerate(starts):
        e = ends[k][0] if k < len(ends) else duration
        out.append({'start': round(max(s, 0), 2), 'end': round(e, 2), 'seconds': round(e - max(s, 0), 2)})
    return out


def decode_mono(path, rate=16000):
    import numpy as np
    r = run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-'])
    require(r.returncode == 0 and r.stdout, 'AUDIO_DECODE_FAILED')
    return np.frombuffer(r.stdout, dtype='<f4').copy()


def balance(samples, heard, sentences, rate=16000):
    """Voice against music: RMS (unweighted) of speech windows against music-only windows, and sentences that fall
    far below the median speech level. Unmeasurable (None) when there is no clean music-only stretch."""
    import numpy as np
    win = int(rate * 0.05)
    n = len(samples) // win
    if n < 20 or not heard:
        return {'voice_over_music_db': None, 'quiet_sentences': []}
    db = 10 * np.log10(np.maximum((samples[:n * win].reshape(n, win) ** 2).mean(axis=1), 1e-12))
    t = (np.arange(n) + 0.5) * 0.05
    speech = np.zeros(n, bool)
    near = np.zeros(n, bool)
    for w in heard:
        speech |= (t >= w['start']) & (t <= w['end'])
        near |= (t >= w['start'] - 0.4) & (t <= w['end'] + 0.4)
    music = (~near) & (t > 1.0) & (t < n * 0.05 - 3.0) & (db > -70)
    result = {'voice_over_music_db': None, 'speech_rms_db': None, 'music_rms_db': None, 'quiet_sentences': []}
    if speech.sum() >= 20 and music.sum() >= 40:
        sp = 10 * np.log10((10 ** (db[speech] / 10)).mean())
        mu = 10 * np.log10((10 ** (db[music] / 10)).mean())
        result.update(speech_rms_db=round(float(sp), 1), music_rms_db=round(float(mu), 1),
                      voice_over_music_db=round(float(sp - mu), 1))
    levels = []
    for k, s in enumerate(sentences):
        if s.get('start') is None or s.get('end') is None:
            continue
        m = speech & (t >= s['start']) & (t <= s['end'])
        if m.sum() >= 10:
            levels.append((k, s, float(10 * np.log10((10 ** (db[m] / 10)).mean()))))
    if len(levels) >= 5:
        median = float(np.median([x[2] for x in levels]))
        result['quiet_sentences'] = [{'sentence': k, 'start': s['start'], 'below_median_db': round(median - lv, 1)}
                                     for k, s, lv in levels if median - lv > 9.0]
    return result


# ---------------------------------------------------------------- 3. video seen
def frame_sheets(path, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = (f"drawtext=fontfile={FONT}:text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.65,"
            if Path(FONT).exists() else '')
    cols, rows = SHEET_TILE
    vf = f'fps=1/{SHEET_STEP},scale=320:180,{text}tile={cols}x{rows}'
    r = run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(path), '-an', '-vf', vf, '-q:v', '4',
             str(out_dir / 'sheet-%03d.jpg')], timeout=3600)
    require(r.returncode == 0, 'SHEET_FAILED')
    return sorted(p.name for p in out_dir.glob('sheet-*.jpg'))


def detect_video(path):
    """freeze / black / scene changes at the native frame rate on a 320x180 proxy."""
    vf = (f"scale=320:180,freezedetect=n=0.001:d={FREEZE_MIN},blackdetect=d=0.2:pix_th=0.10,"
          "select='gt(scene,0.3)',showinfo")
    r = run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-v', 'info', '-i', str(path), '-an', '-vf', vf, '-f', 'null', '-'],
            timeout=3600)
    return parse_detect(r.stderr.decode('utf-8', 'replace'))


def parse_detect(text):
    fs = [float(x) for x in re.findall(r'freeze_start:\s*(-?[\d.]+)', text)]
    fe = [float(x) for x in re.findall(r'freeze_end:\s*(-?[\d.]+)', text)]
    freezes = [{'start': round(s, 2), 'end': round(fe[k], 2) if k < len(fe) else None} for k, s in enumerate(fs)]
    black = [{'start': float(a), 'end': float(b)} for a, b in
             re.findall(r'black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)', text)]
    scenes = sorted({round(float(x), 2) for x in re.findall(r'pts_time:\s*([\d.]+)', text)})
    return {'freezes': freezes, 'black': black, 'scene_changes': scenes}


def sample_frames(path, width=640, height=360):
    """Yield (time, rgb array) for 1 frame / 2 s."""
    import numpy as np
    size = width * height * 3
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-an', '-vf',
                          f'fps=1/{SHEET_STEP},scale={width}:{height}:flags=area,format=rgb24', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE)
    k = 0
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield k * SHEET_STEP, np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3)
            k += 1
    finally:
        p.stdout.close()
        p.wait()


def caption_like(frame):
    """Share of near-white pixels in the lower third (burned captions are white text on a dark outline)."""
    band = frame[int(frame.shape[0] * 0.62):]
    return float((band.min(axis=2) >= 225).mean())


def scan_frames(path, sentences):
    import numpy as np
    prev, stats = None, []
    for t, f in sample_frames(path):
        small = f[::4, ::4].astype(np.float32)
        luma = float((0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]).mean())
        diff = None if prev is None else float(np.abs(small - prev).mean())
        prev = small
        stats.append({'t': t, 'luma': luma, 'diff': diff, 'caption': caption_like(f)})
    speaking = [s for s in stats if any(x.get('start') is not None and x['start'] + 0.3 <= s['t'] <= x['end'] - 0.3 for x in sentences)]
    quiet = [s for s in stats if s not in speaking]
    black = [s['t'] for s in stats if s['luma'] < 12]
    runs, run_ = [], []
    for s in stats:
        if s['diff'] is not None and s['diff'] < 0.15:
            run_.append(s['t'])
        else:
            if len(run_) >= 3:
                runs.append((run_[0] - SHEET_STEP, run_[-1]))
            run_ = []
    if len(run_) >= 3:
        runs.append((run_[0] - SHEET_STEP, run_[-1]))
    present = [s for s in speaking if s['caption'] >= 0.0015]
    return {'samples': len(stats), 'black_samples': black,
            'duplicate_runs': [{'start': a, 'end': b} for a, b in runs],
            'caption_samples_speaking': len(speaking),
            'caption_like_speaking_ratio': round(len(present) / len(speaking), 3) if speaking else None,
            'caption_like_silent_ratio': round(sum(1 for s in quiet if s['caption'] >= 0.0015) / len(quiet), 3) if quiet else None}


def pacing(scenes, duration):
    marks = [0.0] + [s for s in scenes if 0 < s < duration] + [duration]
    gaps = [b - a for a, b in zip(marks, marks[1:])]
    longest = max(gaps) if gaps else duration
    at = marks[gaps.index(longest)] if gaps else 0.0
    return {'scene_changes': len(marks) - 2, 'mean_seconds_between_changes': round(duration / max(len(marks) - 1, 1), 2),
            'longest_without_change': round(longest, 2), 'longest_starts_at': round(at, 2)}


# ---------------------------------------------------------------- defects (same notation as native_review.BUZZY_DEFECTS)
def defects(m, duration, needs_captions=True):
    out = []   # (seconds, category, text)
    a = m['audio']
    if not m['probe']['has_audio']:
        out.append((0, 'c', 'no audio stream in the master'))
    if not m['probe']['has_video']:
        out.append((0, 'f', 'no video stream in the master'))
    cmp_ = a.get('compare')
    if cmp_ and cmp_['coverage'] is not None:
        if cmp_['coverage'] < MIN_COVERAGE:
            out.append((0, 'a', f"only {cmp_['coverage']:.1%} of the script's {cmp_['expected_words']} words were heard"))
        for g in cmp_['missing']:
            if len(g['words']) >= 3:
                out.append((g['at'], 'a', f"script words not heard (sentence {g['sentence']}): \"{' '.join(g['words'][:12])}\""))
        for n, c in cmp_['sentence_coverage'].items():
            if c < 0.8:
                out.append((a['sentence_starts'].get(n, 0) or 0, 'a', f'sentence {n} only {c:.0%} heard (garbled or cut)'))
        for g in cmp_['extra']:
            if len(g['words']) >= 4:
                out.append((g['at'], 'a', f"extra speech not in the script: \"{' '.join(g['words'][:12])}\""))
    first, last = a.get('first_word_start'), a.get('last_word_end')
    opens_at_zero = a.get('sentence_starts', {}).get(0) == 0.0   # a cold open that the plan starts on frame 0
    if first is not None and first < 0.08 and not opens_at_zero:
        out.append((0, 'a', 'speech begins at the very first frame (first word may be cut)'))
    if last is not None and last > duration - 0.08:
        out.append((last, 'a', 'speech runs to the last frame (last word may be cut)'))
    for t in a.get('timing', []):
        if abs(t['start_offset']) > MAX_DRIFT_START or abs(t['end_offset']) > MAX_DRIFT_END:
            out.append((t['timeline_start'], 'd', f"sentence {t['sentence']} heard {t['start_offset']:+.2f}s / {t['end_offset']:+.2f}s from its caption timeline"))
    for g in a.get('speech_gaps', []):
        out.append((g['start'], 'c', f"{g['seconds']} s of silence inside one sentence"))
    loud = a['loudness']
    if abs(loud['integrated_lufs'] - TARGET_LUFS) > LUFS_TOLERANCE:
        out.append((0, 'c', f"integrated loudness {loud['integrated_lufs']} LUFS, target {TARGET_LUFS} +/- {LUFS_TOLERANCE}"))
    if loud['true_peak_dbtp'] is not None and loud['true_peak_dbtp'] > TRUE_PEAK_MAX:
        out.append((0, 'c', f"true peak {loud['true_peak_dbtp']} dBTP is above {TRUE_PEAK_MAX}"))
    clip = a['clipping']
    if clip['peak_dbfs'] is not None and clip['peak_dbfs'] >= -0.1 and (clip['peak_count'] or 0) >= 3:
        out.append((0, 'c', f"clipping: {clip['peak_count']} samples at {clip['peak_dbfs']} dBFS"))
    for s in a['silences']:
        if s['start'] > EDGE_FREE_START and s['end'] < duration - EDGE_FREE_END:
            out.append((s['start'], 'c', f"the whole mix is silent for {s['seconds']} s (dropout)"))
    bal = a['balance']
    if bal.get('voice_over_music_db') is not None and bal['voice_over_music_db'] < MIN_VOICE_OVER_MUSIC_DB:
        out.append((0, 'c', f"voice only {bal['voice_over_music_db']} dB over the music-only level (music may drown the voice)"))
    for q in bal.get('quiet_sentences', []):
        out.append((q['start'], 'c', f"sentence {q['sentence']} is {q['below_median_db']} dB below the median speech level"))
    v = m['video']
    for f in v['freezes']:
        end = f['end'] if f['end'] is not None else duration
        out.append((f['start'], 'f', f'frozen picture for {end - f["start"]:.1f} s'))
    for b in v['black']:
        if b['end'] - b['start'] >= 0.2 and not (b['start'] < 0.1 or b['end'] > duration - 1.5):
            out.append((b['start'], 'f', f"black frames for {b['end'] - b['start']:.2f} s"))
    ratio = v['frames'].get('caption_like_speaking_ratio')
    if needs_captions and ratio is not None and v['frames']['caption_samples_speaking'] >= 10 and ratio < 0.25:
        out.append((0, 'd', f'burned captions barely detectable while speaking ({ratio:.0%} of speaking samples)'))
    return sorted(out, key=lambda x: x[0])


def informational(m):
    notes = []
    cmp_ = m['audio'].get('compare') or {}
    for g in cmp_.get('garbled', []):   # one word differently heard: a mispronunciation or an ASR slip, judged by the reviewer
        notes.append((g['at'], 'info', f"heard \"{g['heard']}\" for \"{g['expected']}\" (sentence {g['sentence']})"))
    if m['audio'].get('sentence_starts', {}).get(0) == 0.0 and m['audio'].get('first_word_start', 1) < 0.08:
        notes.append((0, 'info', 'speech opens on frame 0 by plan (cold open); confirm the first word is whole when listening to the sheet times'))
    v = m['video']
    for d in v['frames']['duplicate_runs']:
        notes.append((d['start'], 'info', f"near-identical frames from {clock(d['start'])} to {clock(d['end'])} (still hold; judge on the sheet)"))
    p = v['pacing']
    notes.append((p['longest_starts_at'], 'info', f"longest stretch without a scene change {p['longest_without_change']} s"))
    return notes


# ---------------------------------------------------------------- the one result (native-review-public-v1)
def public_evidence(i, ev, run_id, status='EVIDENCE_COMPLETE'):
    found = defects(ev['measures'], ev['measures']['probe']['duration']) if status == 'EVIDENCE_COMPLETE' else []
    notes = informational(ev['measures']) if status == 'EVIDENCE_COMPLETE' else []
    issues = [issue(t, c, x) for t, c, x in found + notes]
    links = {}
    for n, (t, c, x) in enumerate(found + notes):
        key = CATEGORY_CRITERION.get(c)
        if key:
            links.setdefault(key, []).append(n)
    warn = [issue(t, 'warn', x) for t, x in warnings_for(ev['measures'])] if status == 'EVIDENCE_COMPLETE' else []
    floor = nr.floor_for(i['plan'])
    clean = status == 'EVIDENCE_COMPLETE' and not found
    out = {'version': 'native-review-public-v1', 'provider': 'local', 'review_version': VERSION,
           'plan': i['plan'], 'output_sha256': i['sha256'],
           'model': f"local:faster-whisper-small.en@{ASR['revision'][:8]}+ffmpeg",
           'run_id': str(run_id), 'source_run_id': str(run_id), 'status': status,
           'coverage': {'video_sampling_fps': 1 / SHEET_STEP, 'native_audio': True, 'full_input': True,
                        'asr_full_audio': True, 'frame_detectors': 'every frame at 320x180 (freeze, black, scene)'},
           'retry_count': 0, 'production_approved': False, 'publication_ready': False,
           'visual_review_required': True, 'machine_verdict': 'NO_DEFECTS_FOUND' if clean else 'DEFECTS_FOUND',
           'asr': {'package': ASR['package'], 'repo': ASR['repo'], 'revision': ASR['revision'], 'model_bin_sha256': ASR['files']['model.bin']},
           'reference': ev.get('reference_source'), 'measures': ev['measures_public'],
           'transcript': ev.get('transcript', []), 'frame_sheets': ev.get('frame_sheets', []),
           'reviewed_at': ev.get('reviewed_at')}
    if status == 'EVIDENCE_COMPLETE':
        out['warnings'] = warn[:nr.PUBLIC_LIST_LIMIT * 3]
        out['warnings_note'] = ('WER and UTMOS are provisional, uncalibrated WARNs for the session reviewer to listen to; '
                                'they are not defects, not a score and not a gate')
        out.update(report_validated=True, scores={k: None for k in nr.RUBRIC}, overall=None,
                   scores_note='machine measures are not a score: the session reviewer scores after viewing the frame sheets and reading the transcript',
                   criterion_issues=links, issues=issues[:nr.PUBLIC_LIST_LIMIT * 3],
                   limitations=['Frames are sampled 1 per 2 s for the human/Claude review; freeze, black and scene detectors run on every frame at 320x180.',
                                'Voice-over-music balance is unweighted RMS, not perceptual.',
                                'Mouth sync, anatomy, scene-to-line match and policy need the session reviewer; a machine pass is not a picture review.',
                                'ASR near-matches (>=0.75 character similarity) count as heard, so a one-letter slip is not flagged.'],
                   owner_floor_met=bool(clean and floor < nr.DEFAULT_FLOOR),
                   every_criterion_at_least_9_5=False)
    return out


def public_status(ev):
    return ev.get('status', 'NO_RECEIPT')


def write_public(i, ev, out_dir, run_id):
    p = public_evidence(i, ev, run_id, ev.get('status', 'EVIDENCE_COMPLETE'))
    nr.save(Path(out_dir) / 'public-evidence.json', p)
    return p


# ---------------------------------------------------------------- the whole pass
def verify_model(model_dir):
    for name, want in ASR['files'].items():
        h = hashlib.sha256()
        with open(Path(model_dir) / name, 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                h.update(block)
        require(h.hexdigest() == want, 'ASR_MODEL_HASH_MISMATCH')


ASR_ATTEMPTS = 3


def run_asr(model, samples, attempts=ASR_ATTEMPTS):
    """One full pass of the pinned model. faster-whisper 1.2.1 sometimes raises IndexError inside its word-timestamp
    alignment (find_alignment) on this very master: runs 41951213420 and 41953276036 failed, 41952393844 passed, with
    identical inputs. A failed pass is repeated with the same parameters (never a different model or setting) up to
    `attempts` times; any other error, or the last IndexError, stays."""
    for attempt in range(1, attempts + 1):
        try:
            segments, _ = model.transcribe(samples, language='en', beam_size=3, vad_filter=False, word_timestamps=True,
                                           condition_on_previous_text=False)
            rows = []
            for s in segments:
                rows.append({'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(),
                             'words': [{'start': round(w.start, 2), 'end': round(w.end, 2), 'word': w.word.strip()}
                                       for w in (s.words or [])]})
            return rows
        except IndexError:
            print(f'LOCAL_REVIEW_ASR_INDEXERROR_ATTEMPT_{attempt}_OF_{attempts}')
            if attempt == attempts:
                raise


def transcribe(model_dir, samples):
    from faster_whisper import WhisperModel
    model = WhisperModel(str(model_dir), device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 2,
                         num_workers=1, local_files_only=True)
    return run_asr(model, samples)


def analyze(i, master, model_dir, out_dir, run_id, asr=transcribe, utmos_dir=None, utmos_predict=None):
    """Hear and see the exact master; write public-evidence.json and the frame sheets. Never an approval."""
    master = Path(master)
    require(hashlib.sha256(master.read_bytes()).hexdigest() == i['sha256'], 'MASTER_SHA256_MISMATCH')
    info = probe(master)
    require(info['has_audio'] and info['has_video'] and info['duration'] > 5, 'MASTER_NOT_AV')
    ref = reference_for(i['plan'], i['sha256'])
    samples = decode_mono(master)
    if asr is transcribe:
        verify_model(model_dir)
    segments = asr(model_dir, samples)
    heard = flatten_heard(segments)
    require(len(heard) >= 3, 'ASR_HEARD_NOTHING')
    sentences = ref['sentences']
    audio = {'loudness': loudness(master), 'clipping': clipping(master), 'silences': silences(master, info['duration']),
             'balance': balance(samples, heard, sentences),
             'first_word_start': heard[0]['start'], 'last_word_end': heard[-1]['end'],
             'speech_gaps': speech_gaps(sentences, heard), 'sentence_starts': {}}
    if sentences:
        cmp_ = compare(sentences, heard)
        audio['compare'] = cmp_
        audio['timing'] = sentence_timing(sentences, heard, cmp_)
        audio['sentence_starts'] = {n: s['start'] for n, s in enumerate(sentences) if s.get('start') is not None}
        audio['wer'] = sentence_wer(sentences, heard)
        predict = utmos_predict or (load_utmos(utmos_dir) if utmos_dir else None)
        if predict is None:
            audio['utmos'] = {'status': 'NOT_RUN', 'reason': 'optional UTMOS step not installed on this run'}
        else:
            try:
                audio['utmos'] = utmos_scores(samples, sentence_spans(sentences, heard, cmp_), predict)
            except Exception as e:   # noqa: BLE001 - WARN-only measure must not fail the review
                audio['utmos'] = {'status': 'ERROR', 'reason': type(e).__name__}
    video = dict(detect_video(master))
    video['frames'] = scan_frames(master, sentences)
    video['pacing'] = pacing(video['scene_changes'], info['duration'])
    sheets = frame_sheets(master, Path(out_dir) / 'frames')
    measures = {'probe': info, 'audio': audio, 'video': video}
    pub = json.loads(json.dumps(measures))
    if 'compare' in pub['audio']:   # keep the public file small: counts and runs, not index tables
        pub['audio']['compare'].pop('matched_index', None)
        pub['audio']['compare'].pop('owner', None)
    pub['audio'].pop('sentence_starts', None)
    if 'utmos' in pub['audio']:
        pub['audio']['utmos']['model'] = {k: UTMOS[k] for k in ('repo', 'tag', 'commit', 'weights_sha256')}
    from datetime import datetime, timezone
    ev = {'measures': measures, 'measures_public': pub, 'reference_source': ref['source'],
          'transcript': [{'start': s['start'], 'end': s['end'], 'text': s['text']} for s in segments],
          'frame_sheets': sheets, 'reviewed_at': datetime.now(timezone.utc).isoformat()[:19] + 'Z'}
    return write_public(i, ev, Path(out_dir) / 'public', run_id), ev


def summary(p):
    lines = [nr.summary_markdown(p).rstrip(), '',
             f"- provider: **local** ({p['model']}); machine verdict: **{p['machine_verdict']}**; visual review required: yes",
             f"- script reference: {p.get('reference') or 'none (transcript only)'}"]
    a = p['measures']['audio']
    lines.append(f"- loudness {a['loudness']['integrated_lufs']} LUFS, true peak {a['loudness']['true_peak_dbtp']} dBTP, "
                 f"voice over music {a['balance'].get('voice_over_music_db')} dB")
    if a.get('compare'):
        c = a['compare']
        lines.append(f"- transcript match {c['coverage']}: {c['matched_words']} of {c['expected_words']} script words heard; "
                     f"{len(c['missing'])} missing runs, {len(c['extra'])} extra runs, {len(c['garbled'])} garbled")
    if a.get('wer'):
        o = a['wer']['overall']
        u = a.get('utmos') or {}
        lines.append(f"- WER {o['wer']} ({o['errors']}/{o['ref_words']} words, {o['near_matches']} near-spelled); UTMOS "
                     + (f"mean {u['mean']} min {u['min']} over {u['clips']} sentences" if u.get('status') == 'OK' else str(u.get('status'))))
        lines += [f'- WARN {x}' for x in p.get('warnings', [])[:20]]
    lines.append(f"- frame sheets: {len(p['frame_sheets'])} (artifact local-review-frames, 1 frame / 2 s, 60 s per sheet)")
    return '\n'.join(lines) + '\n'


def main(argv):
    phase = argv[1] if len(argv) > 1 else ''
    try:
        i = inputs()
        if phase == 'check':
            print('LOCAL_REVIEW_CHECK_COMPLETE')
            return 0
        if phase == 'analyze':
            temp = Path(os.environ['RUNNER_TEMP'])
            p, _ = analyze(i, temp / 'master.mp4', temp / 'models/whisper', temp / 'local-review', os.environ.get('GITHUB_RUN_ID', ''),
                           utmos_dir=temp / 'utmos')
            sm = os.environ.get('GITHUB_STEP_SUMMARY')
            if sm:
                with open(sm, 'a') as f:
                    f.write(summary(p))
            print('LOCAL_REVIEW_ANALYZE_COMPLETE ' + p['machine_verdict'])
            return 0
        raise Refusal('PHASE_INVALID')
    except Exception as e:   # never echo paths of private media; the code is enough
        print(str(e) if isinstance(e, nr.Refusal) else 'LOCAL_REVIEW_' + phase.upper() + '_FAILED_' + type(e).__name__)
        if not isinstance(e, nr.Refusal):   # where, never a path or a message: the file name, function and line of the innermost frame
            tb = traceback.extract_tb(e.__traceback__)
            print('LOCAL_REVIEW_FAILED_AT ' + ' <- '.join(f'{Path(f.filename).name}:{f.name}:{f.lineno}' for f in reversed(tb[-4:])))
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
