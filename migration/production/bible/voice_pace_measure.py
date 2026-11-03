#!/usr/bin/env python3
"""Measure a Kokoro voice's pace in words a second, in CI (no local model, 0 credits).

The method of evidence/voice/20261028/cain-voice.json: each line is voiced sentence by sentence (pilot_render.sentences)
with the hash-pinned Kokoro v1.0 assets at speed 1.0, a SENTENCE_GAP of silence between sentences, and a line's pace is
its words over the seconds from its first sentence's start to its last sentence's end. A voice's pace is its words over
its seconds across its lines. Every run voices the calibration lines of Cain (am_eric) as well; they must come out within
CALIBRATION_TOL of the recorded 3.34 or the run says METHOD_DRIFT and records nothing.

usage: voice_pace_measure.py LINES_JSON MODEL VOICES OUT_JSON
LINES_JSON: {"voices": {"builder": {"voice_id": "bm_lewis", "speed": 1.0, "lines": ["...", ...]}}}
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SENTENCE_GAP = 0.18            # pilot_render.SENTENCE_GAP
CALIBRATION_TOL = 0.04         # relative
CAIN = ROOT / "migration/evidence/voice/20261028/cain-voice.json"


def sentences(text):           # pilot_render.sentences, repeated so this file imports nothing heavy
    return [s.strip() for s in re.split(r"(?<=[.!?:;])\s+", text) if s.strip()]


def words(text):               # plan_check.words
    return len(text.split())


class _FloatSpeed:
    """The v1.0 fp16 model takes `speed` as a float tensor; kokoro-onnx 0.4.9 sends int32 (the repo's own adapter,
    hero_engine KokoroFloatSpeed, casts it the same way)."""
    def __init__(self, sess):
        self._sess = sess

    def run(self, names, inputs, *args, **kwargs):
        inputs = dict(inputs)
        if "speed" in inputs:
            inputs["speed"] = inputs["speed"].astype("float32")
        return self._sess.run(names, inputs, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._sess, name)


def voiced(kokoro, voice, speed, line):
    """Seconds from the first sentence's start to the last sentence's end, with the gaps between sentences."""
    total, parts = 0.0, sentences(line)
    for k, sentence in enumerate(parts):
        samples, rate = kokoro.create(re.sub(r"\b(LORD|GOD)\b", lambda m: m.group(1).capitalize(), sentence),
                                      voice=voice, speed=speed, lang="en-us")
        total += len(samples) / rate + (SENTENCE_GAP if k < len(parts) - 1 else 0.0)
    return total


def measure(kokoro, voice, speed, lines):
    each = []
    for line in lines:
        seconds = voiced(kokoro, voice, speed, line)
        each.append({"line": line, "words": words(line), "seconds": round(seconds, 3),
                     "pace": round(words(line) / seconds, 3)})
    total_w, total_s = sum(e["words"] for e in each), sum(e["seconds"] for e in each)
    paces = [e["pace"] for e in each]
    return {"voice_id": voice, "speed": speed, "lines": len(each), "pace": round(total_w / total_s, 3),
            "line_min": min(paces), "line_max": max(paces), "each": each}


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__)
    from kokoro_onnx import Kokoro
    kokoro = Kokoro(argv[2], argv[3])
    kokoro.sess = _FloatSpeed(kokoro.sess)
    spec = json.loads(Path(argv[1]).read_text())
    cain = json.loads(CAIN.read_text())["pace_by_voice_words_per_s"]["cain"]
    calibration = measure(kokoro, "am_eric", 1.0, [e["line"] for e in cain["each"]])
    drift = abs(calibration["pace"] - cain["pace"]) / cain["pace"]
    out = {"version": "voice-pace-measure-v1", "how": ("voice_pace_measure.py in voice-pace.yml: kokoro-onnx 0.4.9 with the "
           "hash-pinned Kokoro v1.0 assets, sentence by sentence at speed 1.0, a 0.18 s gap, words over seconds of a line "
           "from its first sentence's start to its last sentence's end (the method of cain-voice.json)."),
           "calibration": {"voice": "am_eric (Cain's 8 lines of cain-voice.json)", "recorded": cain["pace"],
                           "measured": calibration["pace"], "relative_drift": round(drift, 4)},
           "pace_by_voice_words_per_s": {}}
    print(json.dumps(out["calibration"]))
    if drift > CALIBRATION_TOL:
        Path(argv[4]).write_text(json.dumps(dict(out, status="METHOD_DRIFT"), indent=1))
        print("METHOD_DRIFT", file=sys.stderr)
        return 1
    for who, v in spec["voices"].items():
        out["pace_by_voice_words_per_s"][who] = measure(kokoro, v["voice_id"], v.get("speed", 1.0), v["lines"])
        print(who, json.dumps({k: out["pace_by_voice_words_per_s"][who][k] for k in ("pace", "line_min", "line_max")}))
    Path(argv[4]).write_text(json.dumps(dict(out, status="MEASURED"), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
