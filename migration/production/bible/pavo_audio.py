#!/usr/bin/env python3
"""E286: the audio of a Pavo talking clip is OURS (`pavo_audio: "ours"`, the default of the Kokoro-input route).

We send Pavo our exact Kokoro line (the request's input audio, sound false) and keep only what it makes of it: the
picture, the lips it animates for that voice. Its returned track is a re-synthesis that may re-time the line, add a
tail mumble or change a word, so the words are never judged on it (owner 2026-11-03: Pavo has no life of its own, it
does only what we send; judging our own line on Pavo's audio was our process defect). The clip we keep and approve is
Pavo's video with the request's own audio laid over it (mux_ours); the words are the request's words, exact by
construction, and assert_ours proves it on the kept bytes: the audio decoded from the clip equals the request's WAV,
sample for sample (the track is stored as PCM, never re-encoded). Lip sync, the face and the visual checks stay strict
and are measured against that same audio (lipsync_check on the muxed clip).

mux_ours(clip, line, dst)      Pavo's picture copied, our line as the only audio (silence-padded to the picture)
assert_ours(clip, line)        {route, sha256, samples, seconds}: the clip's audio is the line, else SystemExit
verify(clip, proof)            the same for a proof recorded earlier (a probe record's `audio`, an approval's)
"""
import hashlib
import json
import subprocess
import wave
from pathlib import Path

ROUTE = "ours"
RATE, CHANNELS = 44100, 1       # the request WAV's format (episode_build.lines_step): mono 44.1 kHz 16-bit PCM


def _fail(code, text):
    raise SystemExit(f"{code} ({text})")


def line_pcm(line):
    """The request WAV's samples (16-bit mono PCM bytes); refuses any other format, so a digest means one thing."""
    with wave.open(str(line), "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, CHANNELS, 2):
            _fail("AUDIO_LINE_FORMAT", f"{line}: {w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()}-bit; "
                  f"need {RATE} Hz mono 16-bit")
        return w.readframes(w.getnframes())


def _video_seconds(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                          "-of", "json", str(clip)], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["streams"][0]["duration"])


def mux_ours(clip, line, dst):
    """Pavo's picture (stream copy, never re-encoded) with OUR line as the only audio, stored as PCM so it stays
    bit-exact, padded with silence to (or cut at) the picture's length. Returns dst."""
    line_pcm(line)   # the format check, before anything is written
    seconds = _video_seconds(clip)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(clip), "-i", str(line), "-map", "0:v:0",
                    "-map", "1:a:0", "-c:v", "copy", "-af", "apad", "-c:a", "pcm_s16le", "-t", f"{seconds:.3f}",
                    str(dst)], check=True)
    return dst


def _decoded(clip):
    done = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(clip), "-vn", "-map", "0:a:0", "-ac",
                           str(CHANNELS), "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True)
    if done.returncode or not done.stdout:
        _fail("AUDIO_NOT_OURS", f"{clip}: no decodable audio track")
    return done.stdout


def proof_of(line):
    pcm = line_pcm(line)
    return {"route": ROUTE, "sha256": hashlib.sha256(pcm).hexdigest(), "samples": len(pcm) // 2,
            "seconds": round(len(pcm) / 2 / RATE, 3)}


def verify(clip, proof):
    """The audio digest equals the requested audio: the first `samples` samples decoded from the clip hash to the
    recorded sha256 of the request WAV. Anything else (Pavo's own track, a re-encoded one, a shorter one) is refused."""
    if not isinstance(proof, dict) or proof.get("route") != ROUTE or not isinstance(proof.get("samples"), int) \
            or proof["samples"] <= 0 or not isinstance(proof.get("sha256"), str):
        _fail("AUDIO_NOT_OURS", "no pavo_audio proof (route ours, sha256, samples)")
    got = _decoded(clip)[:2 * proof["samples"]]
    if len(got) != 2 * proof["samples"] or hashlib.sha256(got).hexdigest() != proof["sha256"]:
        _fail("AUDIO_NOT_OURS", f"{Path(clip).name}: the audio is not the requested line (digest of the first "
              f"{proof['samples']} samples differs from {proof['sha256'][:12]})")
    return proof


def assert_ours(clip, line):
    """The clip's audio is exactly this request WAV; returns the proof to record."""
    return verify(clip, proof_of(line))
