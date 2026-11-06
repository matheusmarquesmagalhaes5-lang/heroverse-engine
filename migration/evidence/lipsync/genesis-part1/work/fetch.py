"""For every finished lip-sync run of the branch: its artifact, the final clip + report; prints the SyncNet verdict."""
import json, subprocess, sys, zipfile, io, hashlib
from pathlib import Path
R = 'matheusmagah-cpu/heroverse-engine'; S = Path(sys.argv[1]); out = S / 'g1res'
jobs = {l.split('\t')[0]: l.strip().split('\t') for l in open(S / 'g1jobs.tsv') if l.strip()}
byaudio = {v[3]: k for k, v in jobs.items()}
gh = lambda *a: subprocess.run(['gh', 'api', *a], capture_output=True, check=True).stdout
runs = json.loads(gh(f'repos/{R}/actions/workflows/lipsync.yml/runs?per_page=50&branch=claude/genesis-part1-lipsync'))['workflow_runs']
res = {}
for r in runs:
    aid = next((a for a in byaudio if r['display_title'].endswith(a)), None)
    if not aid: continue
    i = byaudio[aid]
    if i in res: continue   # newest run per line only
    d = out / i / str(r['id']); d.mkdir(parents=True, exist_ok=True)
    row = {'id': i, 'run_id': r['id'], 'status': r['status'], 'conclusion': r['conclusion']}
    if r['status'] == 'completed':
        arts = json.loads(gh(f"repos/{R}/actions/runs/{r['id']}/artifacts"))['artifacts']
        for a in arts:
            if not (d / 'report.json').exists():
                z = zipfile.ZipFile(io.BytesIO(gh('-H', 'Accept: application/vnd.github+json', f"repos/{R}/actions/artifacts/{a['id']}/zip")))
                for n in z.namelist():
                    if n.endswith(('.json', '.mp4', '.jpg')):
                        (d / Path(n).name).write_bytes(z.read(n))
        rep = json.loads((d / 'report.json').read_text()) if (d / 'report.json').exists() else {}
        lip = (rep.get('lipsync') or {}); m = lip.get('mouth') or {}
        row.update(sync=m.get('sync'), face=m.get('face_frames'), flags=lip.get('flags'), final=rep.get('final_sha256'),
                   clip_flags=(rep.get('clip_check') or {}).get('flags'))
    res[i] = row
    print(json.dumps(row))
json.dump(res, open(out / 'results.json', 'w'), indent=1)
