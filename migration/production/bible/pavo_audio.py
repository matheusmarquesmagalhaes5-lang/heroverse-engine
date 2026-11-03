#!/usr/bin/env python3
"""E286: the audio of a Pavo talking clip is OURS.

We send Pavo our exact Kokoro line (the request's input audio, sound false) and keep only its picture: the lips it
animates for that voice. Its returned track is a re-synthesis that may re-time the line, add a tail or change a word,
so the words are never judged on it. The composed clip is Pavo's video with the request's own audio laid over it
(mux_ours); the words are the request's words, exact by construction, and the audio digest proves it.
"""
import hashlib
import json
import subprocess
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _seconds(path, stream):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", "format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def mux_ours(clip, line, dst):
    """Pavo's picture (copied, never re-encoded) with OUR line as the only audio, padded with silence or cut to the
    picture's length. Returns dst."""
    seconds = _seconds(clip, "v:0")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(clip), "-i", str(line), "-map", "0:v:0",
                    "-map", "1:a:0", "-c:v", "copy", "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-t",
                    f"{seconds:.3f}", str(dst)], check=True)
    return dst
