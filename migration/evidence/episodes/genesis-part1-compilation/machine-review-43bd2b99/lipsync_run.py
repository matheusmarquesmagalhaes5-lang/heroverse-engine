import json,sys,subprocess
from pathlib import Path
W,S=sys.argv[1],Path(sys.argv[2])
sys.path.insert(0,W+'/migration/production/bible')
import lipsync_check as lc
M=S/'../master/m.mp4'; FM=str(S/'../models/face_landmarker.task'); SN=str(S/'../models/syncnet_v2.model')
spans=json.load(open(S/'spans.json')); out=[]
for i,sp in enumerate(spans):
    clip=S/f'c{i:02d}.mp4'; wav=S/f'c{i:02d}.wav'
    d=sp['end']-sp['start']
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(sp['start']),'-t',f'{d:.2f}','-i',str(M),'-c:v','libx264','-crf','16','-preset','fast','-c:a','pcm_s16le',str(clip)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(clip),'-vn','-ac','1','-ar','16000',str(wav)],check=True)
    r={**sp}
    try:
        res=lc.check(str(clip),str(wav),FM,SN); r['sync']=res['mouth'].get('sync'); r['face_frames']=res['mouth'].get('face_frames'); r['flags']=res.get('flags')
    except BaseException as e: r['sync_error']=str(e)[:200]
    try:
        sm=lc.still_mouth(str(clip),FM); r['still_mouth_flags']=sm.get('flags'); r['opening_range']=sm.get('opening_range')
    except BaseException as e: r['still_error']=str(e)[:200]
    out.append(r); print(json.dumps(r),flush=True)
    clip.unlink(); wav.unlink()
json.dump(out,open(S/'lip.json','w'),indent=1)
