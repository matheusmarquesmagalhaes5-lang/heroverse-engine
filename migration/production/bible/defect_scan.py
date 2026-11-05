#!/usr/bin/env python3
"""Free local defect scan (owner 2026-11-05: replace Gemini's defect list with a free, CPU-only detector).

DETECTOR ONLY. The output is information (WARN / INFO lines with timestamps) for the reviewer; it never approves,
never scores, never enters `issues`, `machine_verdict`, claude_review, APPROVAL.json or any gate.

It covers the seven classes native-review.yml `defect_scan` asked Gemini for, with deterministic tools that run on a
free GitHub runner (no provider, no secret, no upload of the master anywhere):

  mispronunciation / garbled_word / speech_cut
      the pinned small.en full pass (the same model local-review uses) is compared with the exact script; every
      sentence that pass did not hear cleanly is decoded again in its own window by small.en AND by a second, larger
      pinned model (medium.en). Only words that ALL decodes miss are WARN ("consensus"); a miss that any decode hears
      is INFO (an ASR slip; the Babel calibration's three known false alarms are this case).
  loudness_jump
      ffmpeg ebur128 short-term loudness (3 s) every 0.1 s; a change of LOUDNESS_JUMP_LU within 1 s, away from
      silence and the edges, is WARN.
  music_voice_clash
      Demucs htdemucs separates voice from accompaniment; each script sentence's voice level against the music under
      it (dB, RMS on the separated stems). Below CLASH_WARN_DB is WARN.
  visual_glitch
      every frame at the native rate on a 64x36 grey proxy: a one- or two-frame flash (a frame unlike both
      neighbours while the neighbours match), plus ffmpeg black/freeze; WARN.
  sync
      lip-sync needs faces; this scan does not judge it. Talking shots stay with lipsync.yml (SyncNet) and the reviewer.

Thresholds are PROVISIONAL, set on one owner-approved master (Babel long, sha256 0386d34a...; see
evidence/reviewer-calibration/free-defect-scan-calibration.json). Promoting any of them to a refusal needs more
calibrated masters and its own decision; this file never does that.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_review as lr  # noqa: E402  (stdlib at import; numpy / faster-whisper only inside the measuring functions)

VERSION = 'free-defect-scan-v1'
CLASSES = ('mispronunciation', 'garbled_word', 'speech_cut', 'loudness_jump', 'music_voice_clash', 'visual_glitch', 'sync')
SECOND_ASR = {'package': 'faster-whisper==1.2.1', 'repo': 'Systran/faster-whisper-medium.en',
              'revision': 'a29b04bd15381511a9af671baec01072039215e3', 'license': 'MIT (code and converted Whisper weights)',
              'files': {'config.json': '4a1848ebabe7938d9797c15a2e8e4ce1d36e6fd4a43d096ae5955257c67c7962',
                        'tokenizer.json': '929c5252409436dce1b38a75d1abbcb5e132d170d8e324e4e04ed915fa2d22df',
                        'vocabulary.txt': 'ff77588746d3a2595d32ab5b69ffd7b95ce2441ac57533cb66fc3eb575a115cf',
                        'model.bin': '11b220779aea4c6f3ce9d2549c8a95ea869ed84066864b999531ef53e594fe5b'}}
DEMUCS = {'package': 'demucs==4.0.1', 'model': 'htdemucs', 'license': 'MIT (code and released weights); repository archived 2025-01-01',
          'weights': '955717e8-8726e21a.th',
          'weights_sha256': '8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'}
LOUDNESS_JUMP_LU = 8.0        # short-term (3 s) change within 1 s; Babel (approved) peaks at 3.0 LU
LOUD_FLOOR_LUFS = -35.0       # both sides of a jump must be programme, not silence or a fade
CLASH_WARN_DB = 3.0           # separated voice over separated music, per sentence
CLASH_INFO_DB = 5.0           # Babel (approved): lowest sentence 6.5 dB, median 8.1 dB
GLITCH_DIFF = 18.0            # mean absolute grey difference (0-255) to both neighbours
GLITCH_NEIGHBOURS = 0.35      # the neighbours differ by at most this share of that difference
WINDOW_PAD = 0.6              # s around a sentence for the window re-decode
WINDOW_MIN = 4.0              # s: whisper often returns nothing for a 1-2 s clip (Babel 06:51 'Babel.' decoded empty)


class Refusal(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Refusal(code)


def finding(t, cls, level, text):
    assert cls in CLASSES and level in ('WARN', 'INFO')
    return {'t': round(float(t), 2), 'at': lr.clock(t), 'class': cls, 'level': level, 'text': text}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify_files(model_dir, files, code):
    for name, want in files.items():
        require(sha256_file(Path(model_dir) / name) == want, code)


# ---------------------------------------------------------------- speech: consensus of independent decodes
def sentence_tokens(sentence):
    return [p for t in lr.norm_tokens(sentence['text']) for p in lr.spell_token(t)]


def heard_tokens(text):
    return [p for t in lr.norm_tokens(text) for p in lr.spell_token(t)]


def soundex(word):
    """American Soundex: proper names the ASR spells differently ('Babel' / 'Beybell') sound the same."""
    w = re.sub(r'[^a-z]', '', word.lower())
    if not w:
        return ''
    codes = {**dict.fromkeys('bfpv', '1'), **dict.fromkeys('cgjkqsxz', '2'), **dict.fromkeys('dt', '3'),
             'l': '4', **dict.fromkeys('mn', '5'), 'r': '6'}
    out, last = w[0].upper(), codes.get(w[0], '')
    for ch in w[1:]:
        c = codes.get(ch, '')
        if c and c != last:
            out += c
        if ch not in 'hw':
            last = c
    return (out + '000')[:4]


def same_word(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75 or (len(a) >= 4 and soundex(a) == soundex(b))


def misses(expected, heard):
    """Script tokens of one sentence that a decode did not hear (exact, near-spelled ratio >= 0.75 like compare(), or
    the same Soundex code for a word of 4+ letters)."""
    import difflib
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, expected, heard, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'replace':
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                if not same_word(expected[i1 + k], heard[j1 + k]):
                    out.append((i1 + k, heard[j1 + k]))
            out += [(k, None) for k in range(i1 + pairs, i2)]
        elif tag == 'delete':
            out += [(k, None) for k in range(i1, i2)]
    return out


def candidates(sentences, cmp_):
    """Sentences the full pass did not hear completely (any garbled or missing word)."""
    bad = {g['sentence'] for g in cmp_['garbled']} | {g['sentence'] for g in cmp_['missing']}
    bad |= {n for n, c in cmp_['sentence_coverage'].items() if c < 1.0}
    return sorted(n for n in bad if sentences[n].get('start') is not None)


def classify_speech(n, sentence, decodes):
    """decodes: {name: heard text of this sentence's window}. WARN only for tokens every decode misses."""
    exp = sentence_tokens(sentence)
    per = {name: misses(exp, heard_tokens(text)) for name, text in decodes.items()}
    common = set.intersection(*[{k for k, _ in m} for m in per.values()]) if per else set()
    t = sentence['start']
    detail = '; '.join(f'{name}: "{text.strip()[:90]}"' for name, text in decodes.items())
    if not common:
        heard_by = [name for name, m in per.items() if not m]
        return [finding(t, 'garbled_word', 'INFO', f'sentence {n}: the full pass missed words that a window decode heard '
                        f'({", ".join(heard_by) or "partly"}); ASR slip, not a defect by itself. {detail}')]
    words = [exp[k] for k in sorted(common)]
    run_ = sorted(common)
    contiguous = run_[-1] - run_[0] + 1 == len(run_)
    edge = contiguous and (run_[-1] == len(exp) - 1 or run_[0] == 0)   # the sentence's end (or start) never heard
    if len(common) >= 3 and edge:
        cls = 'speech_cut'
    elif len(common) == 1:
        cls = 'mispronunciation'
    else:
        cls = 'garbled_word'
    return [finding(t, cls, 'WARN', f'sentence {n}: every decode missed "{" ".join(words[:12])}" '
                    f'(script: "{sentence["text"][:90]}"). {detail}')]


def window(samples, start, end, rate=16000):
    pad = max(WINDOW_PAD, (WINDOW_MIN - (end - start)) / 2)
    a = max(0, int((start - pad) * rate))
    b = min(len(samples), int((end + pad) * rate))
    return samples[a:b]


def decode_text(model, clip):
    segments, _ = model.transcribe(clip, language='en', beam_size=5, vad_filter=False, word_timestamps=False,
                                   condition_on_previous_text=False)
    return ' '.join(s.text.strip() for s in segments)


def speech_scan(samples, sentences, heard, models):
    """models: {name: WhisperModel}; returns (findings, stats)."""
    cmp_ = lr.compare(sentences, heard)
    out, rows = [], []
    for n in candidates(sentences, cmp_):
        s = sentences[n]
        clip = window(samples, s['start'], s['end'])
        decodes = {name: decode_text(m, clip) for name, m in models.items()}
        out += classify_speech(n, s, decodes)
        rows.append({'sentence': n, 'start': s['start'], 'decodes': decodes})
    return out, {'full_pass_coverage': cmp_['coverage'], 'rechecked_sentences': len(rows), 'rechecks': rows}


# ---------------------------------------------------------------- loudness jumps (ebur128 short-term)
FRAMELOG = re.compile(r't:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf)\s+S:\s*(-?[\d.]+|-inf)')


def parse_framelog(text):
    rows = []
    for t, m, s in FRAMELOG.findall(text):
        rows.append((float(t), -120.0 if m == '-inf' else float(m), -120.0 if s == '-inf' else float(s)))
    return rows


def loudness_jumps(rows, duration, step=1.0):
    """Short-term loudness change >= LOUDNESS_JUMP_LU within `step` s, both sides programme, edges excluded.
    One finding per jump (the largest change of a 3 s neighbourhood)."""
    if not rows:
        return []
    times = [r[0] for r in rows]
    st = [r[2] for r in rows]
    lag = max(1, round(step / max(times[1] - times[0], 1e-3))) if len(times) > 1 else 1
    hits = []
    for k in range(lag, len(rows)):
        a, b, t = st[k - lag], st[k], times[k]
        if t < 3.5 or t > duration - 3.0 or min(a, b) < LOUD_FLOOR_LUFS:
            continue
        if abs(b - a) >= LOUDNESS_JUMP_LU:
            hits.append((t, b - a))
    out, last = [], -10.0
    for t, d in hits:
        if t - last < 3.0 and out and abs(d) <= abs(out[-1][1]):
            continue
        if t - last < 3.0 and out:
            out[-1] = (t, d)
        else:
            out.append((t, d))
        last = t
    return [finding(t - step, 'loudness_jump', 'WARN', f'short-term loudness changes {d:+.1f} LU within {step:.0f} s') for t, d in out]


def max_jump(rows, duration, step=1.0):
    """The largest short-term change inside the scanned programme (the calibration margin)."""
    if len(rows) < 2:
        return None
    lag = max(1, round(step / max(rows[1][0] - rows[0][0], 1e-3)))
    vals = [abs(rows[k][2] - rows[k - lag][2]) for k in range(lag, len(rows))
            if 3.5 <= rows[k][0] <= duration - 3.0 and min(rows[k][2], rows[k - lag][2]) >= LOUD_FLOOR_LUFS]
    return round(max(vals), 1) if vals else None


def ebur128_framelog(master):
    r = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-v', 'verbose', '-i', str(master), '-vn',
                        '-af', 'ebur128=framelog=verbose', '-f', 'null', '-'], capture_output=True, timeout=3600)
    return parse_framelog(r.stderr.decode('utf-8', 'replace'))


# ---------------------------------------------------------------- music over voice (separated stems)
def rms_db(x):
    import numpy as np
    return float(10 * np.log10(max(float((x.astype('float64') ** 2).mean()), 1e-12))) if len(x) else -120.0


def clash(voice, music, sentences, heard, rate):
    """Per sentence: separated voice RMS over separated music RMS, on the heard speech frames of that sentence."""
    import numpy as np
    rows, out = [], []
    for n, s in enumerate(sentences):
        if s.get('start') is None:
            continue
        words = [w for w in heard if w['start'] >= s['start'] - 0.3 and w['end'] <= s['end'] + 0.3]
        if not words:
            continue
        mask = np.zeros(len(voice), bool)
        for w in words:
            mask[int(w['start'] * rate):int(w['end'] * rate)] = True
        if mask.sum() < rate * 0.3:
            continue
        v, m = rms_db(voice[mask]), rms_db(music[mask])
        rows.append({'sentence': n, 'start': s['start'], 'voice_db': round(v, 1), 'music_db': round(m, 1), 'margin_db': round(v - m, 1)})
    for r in rows:
        if r['margin_db'] < CLASH_WARN_DB:
            out.append(finding(r['start'], 'music_voice_clash', 'WARN', f"sentence {r['sentence']}: voice only {r['margin_db']} dB over the music under it"))
        elif r['margin_db'] < CLASH_INFO_DB:
            out.append(finding(r['start'], 'music_voice_clash', 'INFO', f"sentence {r['sentence']}: voice {r['margin_db']} dB over the music"))
    margins = sorted(r['margin_db'] for r in rows)
    stats = {'sentences': len(rows), 'min_margin_db': margins[0] if margins else None,
             'median_margin_db': margins[len(margins) // 2] if margins else None, 'rows': rows}
    return out, stats


SEPARATION_CHUNK = 60.0       # s per Demucs call: memory stays flat for a 20 min master


def separate(master, weights_dir, threads):
    """Demucs htdemucs on the master's stereo 44.1 kHz audio, 60 s at a time; returns (voice mono, music mono, rate).
    The mix goes in unnormalised: on the Babel master the separate.py-style mean/std normalisation returned voice and
    music at the same level (0 dB margin on every sentence) while the raw mix separated cleanly (about +8 dB)."""
    import numpy as np
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    torch.set_num_threads(threads)
    rate = 44100
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(master), '-vn', '-ac', '2', '-ar', str(rate), '-f', 'f32le', '-'],
                       capture_output=True, timeout=3600)
    require(r.returncode == 0 and r.stdout, 'AUDIO_DECODE_FAILED')
    wav = np.frombuffer(r.stdout, dtype='<f4').reshape(-1, 2).T
    if weights_dir:   # the hash-verified file sits in <dir>/hub/checkpoints, torch.hub's cache: no download, same loader
        os.environ['TORCH_HOME'] = str(weights_dir)
        require(sha256_file(Path(weights_dir) / 'hub/checkpoints' / DEMUCS['weights']) == DEMUCS['weights_sha256'], 'DEMUCS_WEIGHTS_HASH_MISMATCH')
    model = get_model(DEMUCS['model'])
    model.eval()
    k = list(model.sources).index('vocals')
    step = int(SEPARATION_CHUNK * rate)
    voice = np.zeros(wav.shape[1], np.float32)
    music = np.zeros(wav.shape[1], np.float32)
    for a in range(0, wav.shape[1], step):
        piece = torch.from_numpy(wav[:, a:a + step].copy())
        with torch.no_grad():
            src = apply_model(model, piece[None], shifts=0, split=True, overlap=0.25, progress=False, num_workers=0)[0]
        voice[a:a + step] = src[k].mean(0).numpy()
        music[a:a + step] = (src.sum(0) - src[k]).mean(0).numpy()
    return voice, music, rate


# ---------------------------------------------------------------- visual glitches (every frame)
def flash_frames(diffs, fps, skip=()):
    """diffs[k] = (d(k-1,k), d(k,k+1), d(k-1,k+1)) for frame k. A glitch frame differs from both neighbours by
    GLITCH_DIFF while the neighbours match each other (a cut has a large d(k-1,k+1))."""
    out, last = [], -1.0
    for k, (a, b, c) in enumerate(diffs):
        t = k / fps
        if min(a, b) >= GLITCH_DIFF and c <= GLITCH_NEIGHBOURS * min(a, b) and t - last > 0.5:
            if any(abs(t - s) < 0.1 for s in skip):
                continue
            out.append(finding(t, 'visual_glitch', 'WARN', f'single-frame flash: frame {k} differs {min(a, b):.0f}/255 from both neighbours that match ({c:.0f})'))
            last = t
    return out


def frame_diffs(master, w=64, h=36):
    import numpy as np
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(master), '-an', '-vf',
                          f'scale={w}:{h}:flags=area,format=gray', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    frames = []
    try:
        while True:
            buf = p.stdout.read(w * h)
            if len(buf) < w * h:
                break
            frames.append(np.frombuffer(buf, dtype=np.uint8).astype(np.float32))
    finally:
        p.stdout.close()
        p.wait()
    f = np.stack(frames) if frames else np.zeros((0, w * h), np.float32)
    out = []
    for k in range(1, len(f) - 1):
        out.append((float(np.abs(f[k] - f[k - 1]).mean()), float(np.abs(f[k + 1] - f[k]).mean()), float(np.abs(f[k + 1] - f[k - 1]).mean())))
    return [(0.0, 0.0, 0.0)] + out + [(0.0, 0.0, 0.0)]


def video_scan(master, duration, fps):
    det = lr.detect_video(master)
    diffs = frame_diffs(master)
    out = flash_frames(diffs, fps)
    scores = [min(a, b) for a, b, c in diffs if c <= GLITCH_NEIGHBOURS * min(a, b)]
    for b in det['black']:
        if b['end'] - b['start'] >= 0.1 and 0.1 < b['start'] and b['end'] < duration - 1.5:
            out.append(finding(b['start'], 'visual_glitch', 'WARN', f"black frames for {b['end'] - b['start']:.2f} s"))
    for f in det['freezes']:
        end = f['end'] if f['end'] is not None else duration
        out.append(finding(f['start'], 'visual_glitch', 'INFO', f"frozen picture for {end - f['start']:.1f} s (a held still may be intended)"))
    return out, {'frames': len(diffs), 'max_flash_score': round(max(scores), 1) if scores else 0.0,
                 'scene_changes': len(det['scene_changes']), 'black': len(det['black']), 'freezes': len(det['freezes'])}


# ---------------------------------------------------------------- the scan
def scan(master, plan, sha, small_dir, medium_dir, demucs_dir=None, skip_demucs=False, threads=None, asr=None):
    from faster_whisper import WhisperModel
    threads = threads or os.cpu_count() or 2
    timings, stages = {}, {}
    t0 = time.time()
    require(sha256_file(master) == sha, 'MASTER_SHA256_MISMATCH')
    info = lr.probe(master)
    num, den = (info['fps'] or '30/1').split('/')
    fps = float(num) / float(den or 1)
    ref = lr.reference_for(plan, sha)
    require(ref['sentences'], 'NO_SCRIPT_REFERENCE')
    sentences = ref['sentences']
    samples = lr.decode_mono(master)
    timings['decode'] = round(time.time() - t0, 1)
    verify_files(small_dir, lr.ASR['files'], 'ASR_MODEL_HASH_MISMATCH')
    verify_files(medium_dir, SECOND_ASR['files'], 'SECOND_ASR_MODEL_HASH_MISMATCH')
    t = time.time()
    small = WhisperModel(str(small_dir), device='cpu', compute_type='int8', cpu_threads=threads, local_files_only=True)
    segments = (asr or lr.run_asr)(small, samples)
    heard = lr.flatten_heard(segments)
    timings['asr_full_pass_small'] = round(time.time() - t, 1)
    t = time.time()
    medium = WhisperModel(str(medium_dir), device='cpu', compute_type='int8', cpu_threads=threads, local_files_only=True)
    found, stages['speech'] = speech_scan(samples, sentences, heard, {'small.en': small, 'medium.en': medium})
    timings['asr_window_rechecks'] = round(time.time() - t, 1)
    t = time.time()
    rows = ebur128_framelog(master)
    found += loudness_jumps(rows, info['duration'])
    stages['loudness'] = {'frames': len(rows), 'max_short_term_change_lu_per_s': max_jump(rows, info['duration'])}
    timings['loudness'] = round(time.time() - t, 1)
    if skip_demucs:
        stages['clash'] = {'status': 'NOT_RUN'}
    else:
        t = time.time()
        voice, music, rate = separate(master, demucs_dir, threads)
        more, stages['clash'] = clash(voice, music, sentences, heard, rate)
        found += more
        timings['separation_and_clash'] = round(time.time() - t, 1)
    t = time.time()
    more, stages['video'] = video_scan(master, info['duration'], fps)
    found += more
    timings['video'] = round(time.time() - t, 1)
    found.append(finding(0, 'sync', 'INFO', 'lip-sync is not judged here: talking shots stay with lipsync.yml (SyncNet) and the reviewer'))
    timings['total'] = round(time.time() - t0, 1)
    found.sort(key=lambda f: (f['t'], f['class']))
    return {'version': VERSION, 'detector_only': True, 'never_an_approval': True, 'sha256': sha, 'plan': plan,
            'duration': round(info['duration'], 2), 'reference': ref['source'], 'threads': threads,
            'seconds_per_minute': round(timings['total'] / max(info['duration'] / 60, 1e-6), 1),
            'counts': {lvl: sum(1 for f in found if f['level'] == lvl) for lvl in ('WARN', 'INFO')},
            'findings': found, 'stages': stages, 'timings': timings,
            'tools': {'asr': {k: lr.ASR[k] for k in ('package', 'repo', 'revision')},
                      'second_asr': {k: SECOND_ASR[k] for k in ('package', 'repo', 'revision', 'license')},
                      'separator': DEMUCS if not skip_demucs else None,
                      'thresholds': {'loudness_jump_lu': LOUDNESS_JUMP_LU, 'clash_warn_db': CLASH_WARN_DB,
                                     'clash_info_db': CLASH_INFO_DB, 'glitch_diff': GLITCH_DIFF}}}


def summary(r):
    lines = [f"## Free defect scan ({r['version']}): detector only, never an approval", '',
             f"- {r['counts']['WARN']} WARN, {r['counts']['INFO']} INFO; {r['seconds_per_minute']} s of runner time per minute of video "
             f"({r['timings']['total']} s for {r['duration']} s, {r['threads']} threads)", '']
    lines += [f"- {f['at']} **{f['level']}** [{f['class']}] {f['text'][:220]}" for f in r['findings'] if f['level'] == 'WARN']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--sha256', required=True)
    ap.add_argument('--small', required=True)
    ap.add_argument('--medium', required=True)
    ap.add_argument('--demucs-dir')
    ap.add_argument('--skip-demucs', action='store_true')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    try:
        require(re.fullmatch(r'migration/production/bible/(plans|compilations|cuts|reflections)/[a-z0-9-]+\.json', a.plan), 'PLAN_INVALID')
        require(re.fullmatch(r'[0-9a-f]{64}', a.sha256), 'HASH_INVALID')
        r = scan(Path(a.master), a.plan, a.sha256, a.small, a.medium, a.demucs_dir, a.skip_demucs)
    except Exception as e:   # never echo paths of private media
        print(str(e) if isinstance(e, Refusal) else 'DEFECT_SCAN_FAILED_' + type(e).__name__)
        return 1
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    sm = os.environ.get('GITHUB_STEP_SUMMARY')
    if sm:
        with open(sm, 'a') as f:
            f.write(summary(r))
    print(f"DEFECT_SCAN_COMPLETE WARN={r['counts']['WARN']} INFO={r['counts']['INFO']} (detector only)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
