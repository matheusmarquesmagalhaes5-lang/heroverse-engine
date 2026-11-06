import sys, numpy as np
from faster_whisper import WhisperModel
a = np.frombuffer(open(sys.argv[1],'rb').read(), dtype='int16').astype('float32')/32768
wins=[(310.5,316.5),(2240,2250),(395.5,401),(22,31),(1594,1599),(2150,2155.4)]
for name in ('small.en','medium.en'):
    m = WhisperModel(name, device='cpu', compute_type='int8', cpu_threads=4)
    for x,y in wins:
        segs,_=m.transcribe(a[int(x*16000):int(y*16000)], word_timestamps=True, beam_size=5, condition_on_previous_text=False)
        print(name, x, ' '.join(f"{w.word.strip()}({w.probability:.2f})" for s in segs for w in s.words))
