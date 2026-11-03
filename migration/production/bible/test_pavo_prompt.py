#!/usr/bin/env python3
"""E290: the Pavo talking-shot prompt standard (pavo_prompt.build, PROMPT_GUIDE "Pavo talking-shot prompt standard"),
the 0.3 s silence pad after our line, and the daily lessons file production reads before any Pavo request."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import episode_build as eb  # noqa: E402
import pavo_prompt as pp  # noqa: E402
import plan_check as pc  # noqa: E402

CHARS = pp.ch.registry()
SETTING = "Night in the open desert, the campfire's warm flicker on his face, deep blue darkness and stars behind him."


def keeper_shot(emotion="grave", **pavo):
    return {"id": "k-hook", "kind": "keeper", "lines": [0], "audio_route": "kokoro",
            "pavo": dict({"emotion": emotion, "setting": SETTING, "wardrobe": "fire"}, **pavo)}


def flood_plan():
    return json.loads((HERE / "plans/flood-ends-long.json").read_text())


class Builder(unittest.TestCase):
    def test_the_prompt_has_the_eight_parts_in_the_owners_order(self):
        plan = flood_plan()
        p = pp.build(keeper_shot(), plan, CHARS)
        keeper = CHARS["keeper"]
        order = ["Image 1 is the narrator.", pp.STYLE, pc.KEEPER_FRAMING_16X9, keeper["look"], keeper["wardrobe"]["fire"],
                 SETTING, "speaks the words of the audio clip", "lips move only while the voice speaks",
                 "mouth closed and still before the first word and after the last word",
                 "no extra words, no humming, no mouthing after the line", "looks straight into the camera",
                 "with a grave look", "No text, no logos, no second person, no hand over the mouth, no head turn away."]
        at = [p.find(x) for x in order]
        self.assertNotIn(-1, at, p)
        self.assertEqual(at, sorted(at), p)
        self.assertTrue(p.startswith("Image 1 is the narrator. " + pp.STYLE))
        # the builder already binds Image 1 and the audio clause: the request's bind_prompt changes nothing
        self.assertIn(eb.BOUND_AUDIO.format(pronoun="his"), p)
        self.assertEqual(eb.bind_prompt(p, "keeper", CHARS), p)

    def test_a_built_keeper_prompt_passes_every_keeper_rule_at_every_aspect(self):
        for aspect in ("16:9", "9:16", "1:1"):
            s = dict(keeper_shot(), prompt=pp.build(keeper_shot(), flood_plan(), CHARS))
            self.assertEqual(pc.prompt_problems(0, s), [], aspect)
            self.assertEqual(pc.keeper_prompt_problems(0, s, CHARS["keeper"], aspect), [], aspect)
            self.assertEqual(pc.safe_area_problems(0, s), [], aspect)

    def test_a_character_scene_states_its_period_and_its_look(self):
        plan = flood_plan()
        s = {"id": "s-noah", "kind": "scene", "speaker": "noah", "characters": ["noah"],
             "line": "And Noah said, Blessed be the LORD God of Shem.", "reference": "Genesis 9:26 (KJV)",
             "pavo": {"emotion": "solemn", "gaze": "up toward the sky",
                      "setting": "Dawn on the wet hillside, pale gold light on his face, mist behind him."}}
        s["prompt"] = pp.build(s, plan, CHARS)
        self.assertTrue(s["prompt"].startswith("Image 1 is Noah. "))
        per = pc.period(plan)
        self.assertIn(per["setting"], s["prompt"])
        self.assertTrue(s["prompt"].endswith(per["exclude"]))
        self.assertEqual(pc.period_problems(0, s, per), [])
        self.assertEqual(pc.character_problems(0, ["noah"], s["prompt"], CHARS), [])
        self.assertEqual(pc.prompt_problems(0, s), [])
        self.assertEqual(pc.writing_problems(0, s), [])

    def test_malformed_fields_are_refused_before_any_prompt(self):
        plan = flood_plan()
        bad = {"very grave": keeper_shot(emotion="very grave"), "gaze": keeper_shot(gaze="just past the camera"),
               "wardrobe": keeper_shot(wardrobe="armour"), "extra": keeper_shot(hands="folded")}
        for why, s in bad.items():
            self.assertTrue(pp.field_problems(s, CHARS, plan), why)
            with self.assertRaisesRegex(SystemExit, "PAVO_FIELDS_INVALID"):
                pp.build(s, plan, CHARS)
        god = {"id": "s-voice", "kind": "scene", "speaker": "god", "pavo": {"emotion": "calm", "setting": SETTING}}
        self.assertIn("God is never shown", pp.field_problems(god, CHARS, plan)[0])


class TailPad(unittest.TestCase):
    def test_our_line_ends_on_clean_silence_and_never_reaches_the_clips_end(self):
        self.assertEqual(pp.tail_pad(7.55, 8), 0.3)                      # the retime target N - 0.45: a full 0.3 s
        self.assertEqual(pp.tail_pad(7.70, 8), 0.25)                     # 0.05 s always left before the picture ends
        self.assertEqual(pp.tail_pad(7.98, 8), 0.0)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "k.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(44100)
                w.writeframes(b"\x01\x00" * 44100)
            self.assertEqual(eb.pad_wav(path, 0.3), 0.3)
            with wave.open(str(path), "rb") as w:
                frames = w.readframes(w.getnframes())
            self.assertEqual(len(frames) // 2, 44100 + 13230)
            self.assertEqual(frames[:2 * 44100], b"\x01\x00" * 44100)      # our exact line, untouched
            self.assertEqual(set(frames[2 * 44100:]), {0})                 # then digital silence

    def test_only_a_standard_shot_digests_the_pad_so_approved_clips_keep_their_requests(self):
        req = {"prompt": "p", "aspect_ratio": "16:9", "sound": False, "references": None, "audios": ["k.wav"]}
        legacy = {"id": "k-close", "kind": "keeper", "lines": [0]}
        _, canon = eb.request_digest(req, legacy, ["a"], CHARS)
        self.assertNotIn("tail_pad", canon["audio"])
        self.assertEqual(sorted(canon["audio"]), ["speaker", "voice", "words"])
        _, canon = eb.request_digest(req, keeper_shot(), ["a"], CHARS)
        self.assertEqual(canon["audio"]["tail_pad"], pp.VERSION)


class Lessons(unittest.TestCase):
    def test_the_lessons_file_exists_and_keeps_its_structure(self):
        rows = pp.lessons()
        self.assertGreaterEqual(len(rows), 8)
        self.assertEqual([r["date"] for r in rows], sorted(r["date"] for r in rows))
        self.assertLessEqual({r["kind"] for r in rows}, {"worked", "failed", "rule"})
        self.assertTrue(all(r["evidence"].strip() for r in rows))
        today = {r["text"] for r in rows if r["date"] == "2026-11-03"}
        for seed in ("Tail mumbles", "Word swaps", "Our exact Kokoro WAV", "Pace", "overlapping"):
            self.assertTrue(any(seed in x for x in today), seed)
        self.assertTrue(any("full body" in r["text"] for r in rows))

    def test_a_lesson_is_appended_under_its_date_and_a_broken_file_stops_the_builder(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "pavo_lessons.md"
            path.write_text(pp.LESSONS.read_text())
            n = len(pp.lessons(path))
            rows = pp.append_lesson("2026-11-04", "worked", "Chest-up hook with the pad: no tail.", "shot-probe 1234567",
                                    path)
            self.assertEqual((len(rows), rows[-1]["date"], rows[-1]["kind"]), (n + 1, "2026-11-04", "worked"))
            self.assertEqual(len(pp.append_lesson("2026-11-04", "rule", "Keep it.", "E290", path)), n + 2)
            self.assertEqual(path.read_text().count("## 2026-11-04"), 1)
            with self.assertRaises(SystemExit):
                pp.append_lesson("2026-11-04", "maybe", "A guess.", "none", path)
            path.write_text(path.read_text() + "- an unstructured note\n")
            with self.assertRaisesRegex(SystemExit, "PAVO_LESSONS_INVALID"):
                pp.lessons(path)
            old, pp.LESSONS = pp.LESSONS, Path(t) / "missing.md"
            try:
                with self.assertRaisesRegex(SystemExit, "PAVO_LESSONS_INVALID"):
                    pp.build(keeper_shot(), flood_plan(), CHARS)
            finally:
                pp.LESSONS = old


if __name__ == "__main__":
    unittest.main()
