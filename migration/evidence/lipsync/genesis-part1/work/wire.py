"""E309: bind every reviewed lip-synced clip into the Genesis Part 1 plan. Keeper beats get a `lipsync` record (with the
line's sentence offsets, from word timestamps of the exact line); inherited spans become chapter `patches`.
argv: worktree scratchpad reviewed.json  (reviewed.json: {id: note} for clips whose frames were viewed)"""
import json, re, sys, difflib, hashlib, subprocess
from pathlib import Path
W, S = Path(sys.argv[1]), Path(sys.argv[2]); notes = json.load(open(sys.argv[3]))
sys.path.insert(0, str(W / 'migration/production/bible')); import compilation_long as cl
D = 'migration/evidence/lipsync/genesis-part1'
res = json.load(open(S / 'g1res/results.json'))
jobs = {l.split('\t')[0]: l.rstrip('\n').split('\t') for l in open(S / 'g1jobs.tsv') if l.strip()}
h = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
norm = lambda t: re.sub(r"[^a-z0-9']", '', t.lower())
_m = None
def words(wav):
    global _m
    import numpy as np
    from faster_whisper import WhisperModel
    _m = _m or WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)
    a = subprocess.run(['ffmpeg', '-v', 'error', '-i', wav, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    segs, _ = _m.transcribe(np.frombuffer(a, dtype='int16').astype('float32') / 32768, word_timestamps=True, beam_size=5,
                            condition_on_previous_text=False)
    return [(w.start, w.end, w.word) for s in segs for w in s.words]
def timed(text, ws, shift=0.0):
    sents = [x for x in re.split(r'(?<=[.?!:;])\s+', text.strip()) if x.strip()]
    toks = [(si, norm(t)) for si, x in enumerate(sents) for t in x.split() if norm(t)]
    sm = difflib.SequenceMatcher(None, [t for _, t in toks], [norm(w[2]) for w in ws], autojunk=False)
    tm = {}
    for b in sm.get_matching_blocks():
        for k in range(b.size):
            tm[b.a + k] = ws[b.b + k]
    rows = []
    for si, x in enumerate(sents):
        idx = [i for i, (j, _) in enumerate(toks) if j == si and i in tm]
        if idx:
            rows.append({'text': x, 'start': round(tm[idx[0]][0] + shift, 3), 'end': round(tm[idx[-1]][1] + shift, 3)})
    return rows
# measured locally (lipsync_check.check, same pinned models) on the run's clip with the picture delayed by this much
DELAY = {'b-brick': (0.08, {'offset': -1, 'conf': 6.592}), 'b-name': (0.08, {'offset': -1, 'conf': 6.877}), 'b-tower': (0.08, {'offset': -1, 'conf': 6.718})}
def record(i):
    r = res[i]; run = r['run_id']; clip = S / f'g1res/{i}/{run}/keeper-lipsync.mp4'
    assert r['conclusion'] == 'success' and h(clip) == r['final'], i
    sync = DELAY[i][1] if i in DELAY else r['sync']; assert sync['conf'] >= cl.LIPSYNC_CONF_MIN and abs(sync['offset']) <= cl.LIPSYNC_OFFSET_MAX, (i, sync)
    _, c, cs, a, as_ = jobs[i]; assert h(W / c) == cs and h(W / a) == as_, i
    return {'clip': f'shot-genesis-part1-compilation-{i}-sha256-{r["final"]}.mp4', 'sha256': r['final'], 'run_id': run,
            'line': a, 'line_sha256': as_, 'source': c, 'source_sha256': cs,
            'sync': {'conf': sync['conf'], 'offset': sync['offset']}, 'face_frames': r['face'], 'review': notes[i],
            **({'picture_delay_s': DELAY[i][0], 'sync_as_run': {'conf': r['sync']['conf'], 'offset': r['sync']['offset']}} if i in DELAY else {})}
P = W / 'migration/production/bible/compilations/genesis-part1-compilation.json'
plan = json.load(open(P)); done, missing = [], []
for key, k in cl.keeper_sections(plan):
    lips = 0
    for i, b in zip(cl.beat_ids(key, k), k['beats']):
        if not cl.keeper_face(b['still']['approved_still']):
            continue
        if i not in notes:
            missing.append(i); continue
        rec = record(i); rec['sentences'] = timed(b['text'], words(str(W / rec['line'])))
        b['lipsync'] = rec; done.append(i); lips += 1
    if lips:
        k['lipsync'] = {'used': True, 'reason': 'E309: every beat over the Keeper\'s face is a MuseTalk 1.5 lip-synced clip of its exact line (SyncNet conf >= 2.7, |offset| <= 2); the other beats are voice-over on scene stills.'}
chap = {(c.get('short') or c['long']['id']): c for c in plan['chapters']}
for f, key_at in (('inherited.json', 'long_start'), ('inherited-shorts.json', 'short_start')):
    for x in json.load(open(W / D / f)):
        i = x['id']
        if i not in notes:
            missing.append(i); continue
        c = chap[x['chapter']]; at = x[key_at]; secs = round((x.get('long_end') or x.get('short_end')) - at, 3)
        p = {'id': i, 'at': round(at, 3), 'seconds': secs, 'lipsync': record(i)}
        if 'short' in c:   # the Short's burned caption of that line, re-drawn on the patch (plan text, word timing of the line)
            kind = 'insight' if 'insight' in i else 'cta'
            text = next(n['text'] for n in json.load(open(W / f'migration/production/bible/plans/{x["chapter"]}.json'))['narration'] if n.get('kind') == kind)
            p['captions'] = timed(text, words(str(W / p['lipsync']['line'])), at)
        c['patches'] = [y for y in c.get('patches') or [] if y.get('id') != i] + [p]
        c['patches'].sort(key=lambda y: y['at']); done.append(i)
P.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + '\n')
print(json.dumps({'wired': done, 'missing': missing}))
