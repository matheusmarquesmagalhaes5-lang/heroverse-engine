#!/usr/bin/env python3
"""E286 evidence: does a stored Pavo clip stay in sync when OUR exact audio is laid over its picture?

Owner 2026-11-03: Pavo does only what we send; the fault is ours when we judge the words on Pavo's returned (re-synthesized)
audio and discard clips whose picture is good. This script takes an already generated clip and the Kokoro line we sent
with it (regenerated deterministically in CI, see pavo-audio-eval.yml), lays our line over the clip's picture
(pavo_audio.mux_ours) and measures, with the existing lipsync_check, the SyncNet offset and confidence of the mouth
against OUR audio and the face. Nothing is generated, nothing approved.

usage: pavo_audio_eval.py CLIP.mp4 LINE.wav FACE_LANDMARKER.task SYNCNET.model OUT_DIR   one JSON line, exit 0 always
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python -I adds no script directory
import lipsync_check as lc  # noqa: E402
import pavo_audio  # noqa: E402


def evaluate(clip, line, model, weights, out_dir):
    clip, line, out_dir = Path(clip), Path(line), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    own = lc.check(str(clip), str(line), model, weights)              # as judged today: Pavo's returned track
    composed = out_dir / (clip.stem + ".ours.mp4")
    pavo_audio.mux_ours(clip, line, composed)
    ours = lc.check(str(composed), str(line), model, weights)         # the same picture, OUR audio
    sync, own_sync = ours["mouth"].get("sync"), own["mouth"].get("sync")
    return {"clip": clip.name, "pavo_track": {"audio": own["audio"], "sync": own_sync, "flags": own["flags"]},
            "ours": {"audio": ours["audio"], "sync": sync, "face_frames": ours["mouth"]["face_frames"],
                     "flags": ours["flags"], "lips_corr": ours["mouth"]["corr"],
                     "in_sync": not lc.sync_verdict(sync)}}


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    print(json.dumps(evaluate(*sys.argv[1:])))
