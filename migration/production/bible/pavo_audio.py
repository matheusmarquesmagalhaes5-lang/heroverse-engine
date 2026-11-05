#!/usr/bin/env python3
"""Whose audio a Pavo talking clip carries, per shot (`pavo_audio`): "pavo" (the DEFAULT since owner 2026-11-03) or "ours".

OWNER 2026-11-03: "Quero com o audio do pavo tambem.. quero o video do pavo na integra. A narracao feita vai ser pras
imagens." A talking clip is used IN FULL with PAVO'S OWN audio; our Kokoro narration is only over the still and scene
shots. `pavo_audio: "pavo"` keeps the clip as Pavo returned it (the track is the one it made for our input line) and
records its proof (pavo_proof: the decoded audio digest, its loudness and true peak); `match_gain` brings it to the
narration's integrated LUFS within LOUDNESS_TOL with a true-peak limit. "ours" (E287, below) stays only as an explicit
per-shot option and for approvals recorded under it (route_of reads the recorded proof, so those digests do not move).

Owner 2026-11-04 ("só vídeos sem narração.. e coloca a narração por fora"): a shot with `pavo_mode: "silent"` has
`pavo_audio: "none"`: Pavo makes a silent acting clip (its track is stripped at generation), our Kokoro audio is laid
over it by the build's voice track, and Pavo's own audio is never used. Neither "pavo" nor "ours" applies to it.

E287: the audio of a Pavo talking clip is OURS (`pavo_audio: "ours"`, an explicit option).

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
import re
import subprocess
import wave
from pathlib import Path

ROUTE = "ours"                  # E287's route name (proofs recorded under it carry it)
OURS = ROUTE
PAVO = "pavo"
ROUTES = (PAVO, OURS)
NONE = "none"                   # owner 2026-11-04: a silent Pavo clip (`pavo_mode` "silent"): no Pavo audio, ours goes over it
DEFAULT = PAVO                  # owner 2026-11-03
LOUDNESS_TOL = 1.0              # dB: the Pavo audio's integrated LUFS within this of the narration's
TRUE_PEAK_MAX = -1.5            # dBTP ceiling of a Pavo track laid in the mix
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


# ---------- the Pavo route (owner 2026-11-03) ----------

def route_of(shot=None, recorded=None):
    """The route of one shot: its explicit `pavo_audio`, else the route its approval's audio proof recorded (an
    approval made under E287 keeps "ours", so its digests never move), else DEFAULT ("pavo"). Anything else is refused."""
    want = (shot or {}).get("pavo_audio")
    if want == NONE:
        if (shot or {}).get("pavo_mode") != "silent":
            _fail("PAVO_AUDIO_ROUTE_INVALID", "pavo_audio \"none\" belongs to a silent clip (pavo_mode \"silent\")")
        return NONE
    if want is not None:
        if want not in ROUTES:
            _fail("PAVO_AUDIO_ROUTE_INVALID", f"pavo_audio {want!r} (one of {', '.join(ROUTES)})")
        return want
    kept = (recorded or {}).get("route") if isinstance(recorded, dict) else recorded
    return kept if kept in ROUTES else DEFAULT


def measure(clip):
    """{lufs, true_peak_db} of the clip's audio (ffmpeg ebur128 with true peak); None for a measure it cannot read."""
    done = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(clip), "-vn", "-af", "ebur128=peak=true", "-f",
                           "null", "-"], capture_output=True, text=True)
    tail = done.stderr[done.stderr.rfind("Summary:"):]
    lufs = re.search(r"I:\s+(-?[0-9.]+) LUFS", tail)
    peak = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", tail)
    return {"lufs": float(lufs.group(1)) if lufs else None, "true_peak_db": float(peak.group(1)) if peak else None}


def pavo_proof(clip, line=None):
    """What a kept clip records on the Pavo route: the digest of its decoded audio (so a later byte of another track is
    caught), its length, and its loudness and true peak; with `line` (our request WAV) the narration's loudness too."""
    pcm = _decoded(clip)
    got = measure(clip)
    proof = {"route": PAVO, "sha256": hashlib.sha256(pcm).hexdigest(), "samples": len(pcm) // 2,
             "seconds": round(len(pcm) / 2 / RATE, 3), "lufs": got["lufs"], "true_peak_db": got["true_peak_db"]}
    if line is not None:
        try:
            ours = line_pcm(line)   # E287's clip is our line, silence-padded to the picture: its first samples ARE the line
        except SystemExit:          # a line in another format (a compilation's 24 kHz Kokoro WAV) cannot be that mux
            ours = None
        if ours is not None and pcm[:len(ours)] == ours:
            _fail("PAVO_AUDIO_IS_OURS", f"{Path(clip).name}: the track is our request WAV, not Pavo's (route {PAVO!r})")
        proof["narration_lufs"] = measure(line)["lufs"]
    return proof


def match_gain(clip_lufs, narration_lufs, true_peak_db, tol=LOUDNESS_TOL, ceiling=TRUE_PEAK_MAX):
    """{gain_db, matched_lufs, limited}: the one static gain that brings the clip to the narration's LUFS, and whether
    the true-peak ceiling then needs the limiter. LOUDNESS_NOT_MATCHED when the peaks are so far over the ceiling that
    the limiter would pull the integrated level more than `tol` below the narration's (6 dB of limiting is the line)."""
    nums = (clip_lufs, narration_lufs, true_peak_db)
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) or x != x or abs(x) == float("inf") for x in nums):
        _fail("LOUDNESS_NOT_MATCHED", "no loudness measure for the clip or the narration")
    gain = narration_lufs - clip_lufs
    over = true_peak_db + gain - ceiling
    if over > 6.0:
        _fail("LOUDNESS_NOT_MATCHED", f"the clip needs {gain:+.1f} dB but its peak would pass the {ceiling} dBTP ceiling "
              f"by {over:.1f} dB: the limiter would take the level more than {tol} dB off the narration's")
    return {"gain_db": round(gain, 2), "matched_lufs": round(clip_lufs + gain, 2), "limited": over > 0}


def match_filter(gain_db, ceiling=TRUE_PEAK_MAX):
    """The ffmpeg audio filter of one Pavo track: the static gain, then a true-peak-safe limiter at the ceiling."""
    return f"volume={gain_db:.2f}dB,alimiter=limit={10 ** (ceiling / 20):.4f}:level=false"


def pavo_verify(clip, proof):
    """The kept bytes are the clip whose Pavo audio the proof recorded (decoded digest equal)."""
    if not isinstance(proof, dict) or proof.get("route") != PAVO or not isinstance(proof.get("samples"), int) \
            or proof["samples"] <= 0 or not isinstance(proof.get("sha256"), str):
        _fail("AUDIO_NOT_PAVO", "no pavo_audio proof (route pavo, sha256, samples)")
    got = _decoded(clip)
    if len(got) != 2 * proof["samples"] or hashlib.sha256(got).hexdigest() != proof["sha256"]:
        _fail("AUDIO_NOT_PAVO", f"{Path(clip).name}: the audio is not the Pavo track the proof recorded")
    return proof


def verify_any(clip, proof):
    """verify() for a proof of either route."""
    if isinstance(proof, dict) and proof.get("route") == PAVO:
        return pavo_verify(clip, proof)
    return verify(clip, proof)
