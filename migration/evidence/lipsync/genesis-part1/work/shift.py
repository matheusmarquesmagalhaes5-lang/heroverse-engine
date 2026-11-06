import json,sys,subprocess
sys.path.insert(0,sys.argv[1]+'/migration/production/bible'); import lipsync_check as lc
S=sys.argv[2]; clip=sys.argv[3]
subprocess.run(['ffmpeg','-v','error','-y','-i',clip,'-vn','-ac','1','-ar','16000','a.wav'],check=True)
for sh in [float(x) for x in sys.argv[4:]]:
    # sh > 0: picture later than the sound
    vf = f"tpad=start_mode=clone:start_duration={sh}" if sh > 0 else f"trim=start={-sh},setpts=PTS-STARTPTS"
    subprocess.run(['ffmpeg','-v','error','-y','-i',clip,'-i','a.wav','-map','0:v','-map','1:a','-vf',vf,'-c:v','libx264','-crf','16','-c:a','pcm_s16le','-shortest','v.mp4'],check=True)
    r=lc.check('v.mp4','a.wav',S+'/models/face_landmarker.task',S+'/models/syncnet_v2.model')
    print('R',sh,json.dumps(r['mouth'].get('sync')),flush=True)
