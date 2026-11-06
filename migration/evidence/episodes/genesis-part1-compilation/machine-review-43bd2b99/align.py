"""Whole-master ASR-vs-script word alignment for pilot-023 (43bd2b99). Reference per segment: the build's timed report
(Keeper lines + the two longs), the Shorts' plans (narration + God's shot lines, 07-09), and for 02-06 (no script on
record) the KJV passage, so only quoted scripture is compared."""
import json, re, sys, difflib
W, words_f = sys.argv[1], sys.argv[2]
words = json.load(open(words_f))
tl = json.load(open(W + '/migration/production/pilot-023/out/timeline.json'))['segments']
rep = json.load(open(W + '/migration/evidence/episodes/genesis-part1-compilation/report-42125312688.json'))['composed']['sentences']
sys.path.insert(0, W + '/migration/production/bible'); import kjv_check
NUM = {'11': 'eleven', '12': 'twelve', '1': 'one', '950': 'nine hundred and fifty', '930': 'nine hundred and thirty', '150': 'an hundred and fifty',
       '40': 'forty', '7': 'seven', '600': 'six hundred', '300': 'three hundred', '50': 'fifty', '30': 'thirty', '450': 'four hundred and fifty', '5': 'five', '2': 'two', '3': 'three', '9': 'nine', '10': 'ten', '6': 'six', '8': 'eight', '17': 'seventeen', '27': 'twenty seventh', '365': 'three hundred sixty and five', '65': 'sixty and five'}
def norm(t):
    t = t.lower().replace('’', "'").replace('-', ' ')
    out = []
    for w in t.split():
        w = re.sub(r"[^a-z0-9']", '', w).strip("'")
        if not w: continue
        if w in NUM: out += NUM[w].split()
        elif w.endswith("'s"): out += [w[:-2], 's']
        else: out.append(w)
    return out
def heard(a, b):
    return [(w, s, p) for s, e, w, p in words if a - 0.3 <= s < b]
res = []
for r in tl:
    a, b = r['start'], r['start'] + r['seconds']
    if r['kind'] in ('hook', 'interlude', 'close', 'long'):
        ref = ' '.join(x['text'] for x in rep if a - 0.01 <= x['start'] < b)
        src = 'timed build report'
    else:
        p = W + f"/migration/production/bible/plans/{r['name']}.json"
        try:
            pl = json.load(open(p)); ref = ' '.join([n['text'] for n in pl['narration']] + [s['line'] for s in pl['shots'] if s.get('line')]); src = 'plan narration + shot lines (order not timed)'
        except FileNotFoundError:
            ep = json.load(open(W + f"/migration/production/bible/episodes/{r['name']}.json"))
            ref = ' '.join(t for *_, t in kjv_check.passage(ep['passage'])); src = 'KJV passage ' + ep['passage'] + ' (no script on record)'
    H = heard(a, b)
    hw = []; ht = []; hp = []
    for w, s, p in H:
        for t in norm(w): hw.append(t); ht.append(s); hp.append(p)
    rw = norm(ref)
    sm = difflib.SequenceMatcher(None, rw, hw, autojunk=False)
    diffs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal': continue
        t = ht[j1] if j1 < len(ht) else (ht[-1] if ht else a)
        diffs.append({'t': round(t, 2), 'op': op, 'script': ' '.join(rw[i1:i2])[:120], 'heard': ' '.join(hw[j1:j2])[:120],
                      'min_prob': round(min(hp[j1:j2]), 3) if j2 > j1 else None})
    res.append({'segment': r['name'], 'kind': r['kind'], 'start': round(a, 2), 'end': round(b, 2), 'reference': src,
                'script_words': len(rw), 'heard_words': len(hw), 'ratio': round(sm.ratio(), 3), 'divergences': diffs})
json.dump(res, open(sys.argv[3], 'w'), indent=1)
for x in res: print(x['segment'], x['kind'], x['ratio'], x['script_words'], x['heard_words'], len(x['divergences']))
