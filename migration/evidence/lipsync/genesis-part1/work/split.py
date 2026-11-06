"""Split a Keeper line WAV into two parts at the silence between sentences nearest its middle (sample-exact: the
parts concatenated are the line's own samples). argv: worktree id..."""
import sys, json, wave, re
from pathlib import Path
import numpy as np
W = Path(sys.argv[1]); D = W / 'migration/evidence/lipsync/genesis-part1/lines'
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)
out = {}
for i in sys.argv[2:]:
    with wave.open(str(D / f'{i}.wav'), 'rb') as w:
        p = w.getparams(); a = np.frombuffer(w.readframes(p.nframes), dtype='int16')
    sr = p.framerate
    import subprocess
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(D / f'{i}.wav'), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    segs, _ = m.transcribe(np.frombuffer(pcm, dtype='int16').astype('float32') / 32768, word_timestamps=True, beam_size=5, condition_on_previous_text=False)
    ws = [w for s in segs for w in s.words]
    mid = len(a) / sr / 2
    gaps = [(ws[k].end, ws[k + 1].start) for k in range(len(ws) - 1) if re.search(r'[.?!:;,]$', ws[k].word.strip()) and ws[k + 1].start - ws[k].end > 0.12]
    g = min(gaps, key=lambda x: abs((x[0] + x[1]) / 2 - mid))
    # the quietest 10 ms inside the gap
    lo, hi = int(g[0] * sr), int(g[1] * sr); win = int(0.01 * sr)
    e = [np.abs(a[s:s + win].astype(float)).mean() for s in range(lo, max(lo + 1, hi - win), win // 2)]
    cut = lo + int(np.argmin(e)) * (win // 2) + win // 2
    for n, part in ((1, a[:cut]), (2, a[cut:])):
        with wave.open(str(D / f'{i}-p{n}.wav'), 'wb') as w:
            w.setparams(p); w.writeframes(part.tobytes())
    out[i] = {'cut_s': round(cut / sr, 4), 'cut_sample': int(cut), 'gap': [round(g[0], 2), round(g[1], 2)], 'seconds': [round(cut / sr, 3), round((len(a) - cut) / sr, 3)]}
    print(i, out[i], flush=True)
json.dump(out, open(D.parent / 'splits.json', 'w'), indent=1)
