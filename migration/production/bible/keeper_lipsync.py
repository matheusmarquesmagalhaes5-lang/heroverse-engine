#!/usr/bin/env python3
"""Keeper lip-sync with OUR audio (owner 2026-11-05: "No guardiao eu quero lipsync pra ele falar.. verifique algo
gratuito e de qualidade"): a Pavo SILENT frontal Keeper clip (mouth closed, `pavo_mode: silent`) + our exact Kokoro
line -> the Keeper speaks the line. Pavo never hears or garbles a word; the lips follow ours.

Model: MuseTalk 1.5 (TMElyralab; code MIT, weights "for any purpose, even commercially"; one UNet step per frame, CPU
capable). LatentSync (Apache-2.0 code, OpenRAIL++ weights) needs insightface's detector models (research-only) and CUDA
(`.to("cuda")` hard-coded), and is a 20-step diffusion per 16 frames (hours on a CPU runner): GPU route only. Wav2Lip is
non-commercial: rejected. See OPERATIONS "Keeper lip-sync (our audio)".

This module is the glue around the model and is what the tests cover (no torch here):
  fetch DIR                       the pinned weights, every file by sha256 (fail closed)
  prepare CLIP WAV FACE_MODEL WORK [--tail S] [--cap S]
                                  source gate (the silent clip's own still-mouth + face), the clip cut to the line plus
                                  a tail, the MuseTalk task file; prints one JSON line
  finish WORK LIPSYNC_VIDEO FACE_MODEL SYNCNET OUT_DIR SECONDS
                                  our line over the lip-synced picture (pavo_audio.mux_ours, bit-exact PCM), the strict
                                  gates on that clip and on the silent source (baseline), frame sheets; exit 1 on a flag
  pins                            print the pin table as JSON
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MODEL = "musetalk-1.5"
MODELS = (MODEL,)
MUSETALK_REPO = "https://github.com/TMElyralab/MuseTalk"
MUSETALK_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"
TAIL_S = 0.5                    # picture kept after the last word (the mouth closes again), seconds
FACE_FRAMES_MIN = 0.8           # lipsync_check.FACE_FRAMES_MIN, repeated for the module's own flag
HF = "https://huggingface.co"
# name -> (url at a pinned revision, sha256, size, destination under the MuseTalk checkout)
PINS = {
    "musetalkV15/unet.pth": (f"{HF}/TMElyralab/MuseTalk/resolve/2bcb936e2fddb4d86db4c62fd45b387d0c061571/musetalkV15/unet.pth",
                             "7ebf6c98c181e20838e4c0054e96e944ac60d5d692cc01db42839fe11b787007", 3400074924),
    "musetalkV15/musetalk.json": (f"{HF}/TMElyralab/MuseTalk/resolve/2bcb936e2fddb4d86db4c62fd45b387d0c061571/musetalkV15/musetalk.json",
                                  "5b6923aee04d71692e0e9846c471e0a4ea07a4f686d39545e472bd4ba17e1b47", 748),
    "sd-vae/diffusion_pytorch_model.bin": (f"{HF}/stabilityai/sd-vae-ft-mse/resolve/31f26fdeee1355a5c34592e401dd41e45d25a493/diffusion_pytorch_model.bin",
                                           "1b4889b6b1d4ce7ae320a02dedaeff1780ad77d415ea0d744b476155c6377ddc", 334707217),
    "sd-vae/config.json": (f"{HF}/stabilityai/sd-vae-ft-mse/resolve/31f26fdeee1355a5c34592e401dd41e45d25a493/config.json",
                           "92d3dfb746fca211a2c9e019e285f8597412211728dce3c5bcf4eda0f2d62e7e", 547),
    "whisper/pytorch_model.bin": (f"{HF}/openai/whisper-tiny/resolve/169d4a4341b33bc18d8881c4b69c2e104e1cc0af/pytorch_model.bin",
                                  "9607f98a2b22d9e229ae43c52ecea79dcede9e0c5cfae67e8da6eda86d8aac1d", 151095027),
    "whisper/config.json": (f"{HF}/openai/whisper-tiny/resolve/169d4a4341b33bc18d8881c4b69c2e104e1cc0af/config.json",
                            "ffdccec4f3211f4c63310f2b7098f309fe70f3952cedc5e4d11e43f5b2379b98", 1983),
    "whisper/preprocessor_config.json": (f"{HF}/openai/whisper-tiny/resolve/169d4a4341b33bc18d8881c4b69c2e104e1cc0af/preprocessor_config.json",
                                         "9b5cd03a36fbb8a627c64d98a5b5b126ead95a77720723944487311f0110b666", 184990),
    "dwpose/dw-ll_ucoco_384.pth": (f"{HF}/yzd-v/DWPose/resolve/1a7144101628d69ee7a3768d1ee3a094070dc388/dw-ll_ucoco_384.pth",
                                   "0d9408b13cd863c4e95a149dd31232f88f2a12aa6cf8964ed74d7d97748c7a07", 406878486),
    "face-parse-bisent/79999_iter.pth": ("https://drive.google.com/uc?export=download&id=154JgKpzCPW82qINcVieuPH3fZ2e0P812",
                                         "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567", 53289463),
    "face-parse-bisent/resnet18-5c106cde.pth": ("https://download.pytorch.org/models/resnet18-5c106cde.pth",
                                                "5c106cde386e87d4033832f2996f5493238eda96ccf559d1d62760c4de0613f8", 46830571),
    "s3fd.pth": ("https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth",
                 "619a31681264d3f7f7fc7a16a42cbbe8b23f31a256f75a366e5a1bcd59b33543", 89843225),
}
# where each pin lands inside the MuseTalk checkout (relative); s3fd sits next to the detector that loads it
DEST = {"s3fd.pth": "musetalk/utils/face_detection/detection/sfd/s3fd.pth"}


def dest_of(name):
    return DEST.get(name, f"models/{name}")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(root, opener=urllib.request.urlopen):
    """Every pinned weight into the MuseTalk checkout `root`, verified by sha256; a mismatch deletes the file and fails."""
    for name, (url, sha, size) in PINS.items():
        target = Path(root) / dest_of(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256_of(target) == sha:
            continue
        with opener(url, timeout=120) as r, open(target, "wb") as out:
            for block in iter(lambda: r.read(1 << 20), b""):
                out.write(block)
        if sha256_of(target) != sha:
            target.unlink()
            raise SystemExit(f"LIPSYNC_WEIGHT_SHA_MISMATCH {name}")
    return sorted(PINS)


def wav_seconds(wav):
    import wave
    with wave.open(str(wav), "rb") as w:
        return w.getnframes() / w.getframerate()


def video_seconds(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of",
                          "json", str(clip)], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["streams"][0]["duration"])


def span_s(line_s, clip_s, tail=TAIL_S):
    """Seconds of picture the model works on: the line plus a tail, never more than the clip (cost grows with frames)."""
    return round(min(clip_s, line_s + tail), 3)


def source_flags(still):
    """The silent source must really be a still, frontal mouth: talking mouth or no face stays a flag (no lip-sync is
    painted over a clip that already moves its lips or hides its face)."""
    flags = []
    if "MOUTH_TALKING" in still.get("flags", []):
        flags.append("LIPSYNC_SOURCE_MOUTH_TALKING")
    if "FACE_NOT_FOUND" in still.get("flags", []):
        flags.append("LIPSYNC_SOURCE_FACE_NOT_FOUND")
    return flags


def result_flags(check, clip, audio_ok):
    """Gates on the lip-synced clip: SyncNet in sync (lipsync_check thresholds, unchanged), the face found, no clip
    artifact, and the audio exactly our line."""
    flags = list(check.get("flags", []))
    flags += [f"CLIP_{f}" for f in clip.get("flags", [])]
    if not audio_ok:
        flags.append("AUDIO_NOT_OURS")
    return flags


def run(*cmd, **kw):
    return subprocess.run(list(map(str, cmd)), check=True, **kw)


def prepare(clip, wav, face_model, work, tail=TAIL_S, cap=None):
    import lipsync_check
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    still = lipsync_check.still_mouth(str(clip), str(face_model))
    line_s, clip_s = wav_seconds(wav), video_seconds(clip)
    seconds = span_s(line_s, clip_s, tail)
    if cap:
        seconds = min(seconds, cap)   # a timing probe only: the line is cut, so the result is never a deliverable
    src = work / "source-cut.mp4"
    run("ffmpeg", "-nostdin", "-v", "error", "-y", "-i", clip, "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264", "-crf", "12",
        "-pix_fmt", "yuv420p", src)
    line = work / "line-padded.wav"
    run("ffmpeg", "-nostdin", "-v", "error", "-y", "-i", wav, "-af", "apad", "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", line)
    (work / "task.yaml").write_text(f'task_0:\n video_path: "{src}"\n audio_path: "{line}"\n result_name: "lipsync.mp4"\n')
    info = {"model": MODEL, "line_seconds": round(line_s, 3), "clip_seconds": round(clip_s, 3), "processed_seconds": seconds,
            "source_still_mouth": still, "flags": source_flags(still)}
    (work / "prepare.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info))
    return 1 if info["flags"] else 0


def sheet(video, dest, seconds, cols=4):
    rows = max(1, -(-int(seconds) // cols))
    run("ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-vf", f"fps=1,scale=480:-2,tile={cols}x{rows}", "-frames:v", "1",
        "-q:v", "3", dest)


def finish(work, lip_video, face_model, syncnet, out_dir, seconds):
    import clip_check
    import lipsync_check
    import pavo_audio
    work, out_dir = Path(work), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    line = work / "line-padded.wav"
    final = out_dir / "keeper-lipsync.mp4"
    # the model's picture (re-encoded by the model's own ffmpeg step) with OUR line, bit-exact PCM, as the only audio
    pavo_audio.mux_ours(lip_video, line, final)
    audio_ok = True
    try:
        pavo_audio.assert_ours(final, line)
    except SystemExit:
        audio_ok = False
    check = lipsync_check.check(str(final), str(line), str(face_model), str(syncnet))
    clip = clip_check.check(str(final))
    flags = result_flags(check, clip, audio_ok)
    # the silent source with the same line laid over it: the baseline the lip-sync has to beat (not a gate)
    src_with_line = out_dir / "baseline-silent-with-line.mp4"
    pavo_audio.mux_ours(work / "source-cut.mp4", line, src_with_line)
    base = lipsync_check.check(str(src_with_line), str(line), str(face_model), str(syncnet))
    sheet(final, out_dir / "sheet-lipsync.jpg", seconds)
    sheet(src_with_line, out_dir / "sheet-silent-source.jpg", seconds)
    run("ffmpeg", "-nostdin", "-v", "error", "-y", "-i", out_dir / "sheet-silent-source.jpg", "-i", out_dir / "sheet-lipsync.jpg",
        "-filter_complex", "vstack", "-q:v", "3", out_dir / "sheet-compare.jpg")
    report = {"model": MODEL, "commit": MUSETALK_COMMIT, "final": final.name, "final_sha256": sha256_of(final),
              "lipsync": check, "silent_source_with_line": {k: base[k] for k in ("mouth", "flags")},
              "clip_check": clip, "audio_ours": audio_ok, "flags": flags}
    (out_dir / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("model", "final_sha256", "flags")}), json.dumps(check["mouth"]))
    return 1 if flags else 0


def main(argv):
    if argv[:1] == ["pins"]:
        print(json.dumps({"commit": MUSETALK_COMMIT, "weights": {k: v[1] for k, v in PINS.items()}}))
        return 0
    if argv[:1] == ["fetch"] and len(argv) == 2:
        print(json.dumps(fetch(argv[1])))
        return 0
    if argv[:1] == ["prepare"] and len(argv) in (5, 7, 9):
        opts = dict(zip(argv[5::2], argv[6::2]))
        if set(opts) - {"--tail", "--cap"}:
            raise SystemExit(__doc__)
        return prepare(*argv[1:5], tail=float(opts.get("--tail", TAIL_S)), cap=float(opts["--cap"]) if "--cap" in opts else None)
    if argv[:1] == ["finish"] and len(argv) == 7:
        return finish(argv[1], argv[2], argv[3], argv[4], argv[5], float(argv[6]))
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
