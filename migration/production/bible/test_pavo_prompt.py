#!/usr/bin/env python3
"""E290/E293: the Pavo talking-shot prompt standard (pavo_prompt.build, PROMPT_GUIDE "Pavo talking-shot prompt standard"):
the builder writes the passing prompt of record word for word (evidence/pavo-prompt-analysis/20261103.json), the input
audio is our line as cut (no added pad, as every passing generation), and the daily lessons file is read first."""
import hashlib
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


def keeper_shot(emotion="calm kind", **pavo):
    return {"id": "k-hook", "kind": "keeper", "lines": [0], "audio_route": "kokoro",
            "pavo": dict({"emotion": emotion, "setting": SETTING, "wardrobe": "fire"}, **pavo)}


def flood_plan():
    return json.loads((HERE / "plans/flood-ends-long.json").read_text())


EVIDENCE = HERE.parents[1] / "evidence"
# passing generations of record (approved, or E287 sync and face on our audio): (probe record, shot, plan, look)
PASSING = (("shots/flood-ends-long/41534197400.json", "k-insight", "flood-ends-long", "calm kind"),
           ("shots/flood-ends-long/41534197400.json", "k-close", "flood-ends-long", "warm expectant"),
           ("shots/flood-ends-long/41547308176.json", "k-hook", "flood-ends-long", "grave, intent"),
           ("shots/arc-02-noah-compilation-keeper/41629339290.json", "k-hook", "arc-02-noah-compilation-keeper",
            "grave, intent"),
           ("shots/flood-ends-long-reflection-1/41567543843.json", "k-r1", "flood-ends-long-reflection-1",
            "grave, intent"),
           ("shots/genesis-09-short/41254369410.json", "k-close", "genesis-09-short", "warm expectant"),
           ("shots/genesis-10-short/41574608645.json", "k-insight", "genesis-10-short", "grave knowing"))


class Builder(unittest.TestCase):
    def test_e293_the_keeper_prompt_is_the_passing_prompt_of_record_word_for_word(self):
        # owner 2026-11-03: "Always model the prompt on the way it was done the time it passed."
        for record, sid, plan_id, look in PASSING:
            sent = json.loads((EVIDENCE / record).read_text())["shots"][sid]["request"]["prompt"]
            plan = json.loads((HERE / f"plans/{plan_id}.json").read_text())
            shot = {"id": sid, "kind": "keeper", "lines": [], "pavo": {"emotion": look, "setting": SETTING,
                                                                        "wardrobe": "fire"}}
            self.assertEqual(pp.build(shot, plan, CHARS), sent, (record, sid))
            self.assertIn(hashlib.sha256(sent.encode()).hexdigest(), analysis["template_prompts"], (record, sid))

    def setUp(self):
        global analysis
        analysis = json.loads((HERE.parents[2] / pp.EVIDENCE).read_text())

    def test_e293_the_keeper_template_at_each_aspect(self):
        keeper, plan = CHARS["keeper"], flood_plan()
        look = f"{keeper['look']}, {keeper['wardrobe']['fire']}"
        wide = ("Image 1 is the narrator. " + pp.STYLE + " Close-up from the chest up, his face large in the centre of "
                f"the frame, static camera. The narrator, {look}, centred in the frame holds his head level and looks "
                "straight into the camera and speaks the words of the audio clip, his lips moving in sync with the "
                f"voice, a calm kind look. {SETTING} Tender and grave. No text, no logos.")
        tall = ("Image 1 is the narrator. " + pp.STYLE + f" Medium close-up, static camera. The narrator, {look}, holds "
                "his head level, looks straight into the camera and speaks the words of the audio clip, his lips moving "
                f"in sync with the voice, a calm kind look. {SETTING} Tender and grave. No text, no logos.")
        for aspect, want in (("16:9", wide), ("1:1", wide), ("9:16", tall)):
            plan["aspect_ratio"] = aspect
            p = pp.build(keeper_shot(), plan, CHARS)
            self.assertEqual(p, want, aspect)
            s = dict(keeper_shot(), prompt=p)
            self.assertEqual(pc.prompt_problems(0, s), [], aspect)
            self.assertEqual(pc.keeper_prompt_problems(0, s, keeper, aspect), [], aspect)
            if aspect != "9:16":   # a long-first prompt keeps him in the centre column (E259); a 9:16 Short is that column
                self.assertEqual(pc.safe_area_problems(0, s), [], aspect)
            # the builder already binds Image 1 and the audio clause: the request's bind_prompt changes nothing
            self.assertIn(eb.BOUND_AUDIO.format(pronoun="his"), p)
            self.assertEqual(eb.bind_prompt(p, "keeper", CHARS), p)
        # no wording that no generation of record used
        for never in ("the speaker centred", "lips move only", "no humming", "no second person", "head turn away"):
            self.assertNotIn(never, wide)

    def test_e293_a_character_follows_the_same_template_with_its_period(self):
        plan = flood_plan()
        setting = "Dawn on the wet hillside, pale gold light on his face, mist behind him."
        s = {"id": "s-noah", "kind": "scene", "speaker": "noah", "characters": ["noah"],
             "line": "And Noah said, Blessed be the LORD God of Shem.", "reference": "Genesis 9:26 (KJV)",
             "pavo": {"emotion": "solemn", "mood": "Solemn and grave", "gaze": "up toward the sky", "setting": setting}}
        s["prompt"] = pp.build(s, plan, CHARS)
        per, noah = pc.period(plan), CHARS["noah"]
        self.assertEqual(s["prompt"], (
            "Image 1 is Noah. " + pp.STYLE + f" Medium close-up, static camera. Noah, {noah['look']}, centred in the "
            "frame holds his head level and looks up toward the sky and speaks the words of the audio clip, his lips "
            f"moving in sync with the voice, a solemn look. {setting} Solemn and grave. {per['setting']} "
            f"{per['exclude']} No text, no logos."))
        self.assertEqual(pc.period_problems(0, s, per), [])
        self.assertEqual(pc.character_problems(0, ["noah"], s["prompt"], CHARS), [])
        self.assertEqual(pc.prompt_problems(0, s), [])
        self.assertEqual(pc.writing_problems(0, s), [])
        # a look of record carries its own mood; any other look must state one
        self.assertIn("is not a look of record", pp.field_problems(dict(s, pavo=dict(s["pavo"], mood=None)), CHARS,
                                                                   plan)[0])

    def test_e293_a_line_longer_than_any_of_record_is_refused(self):
        plan = flood_plan()
        plan["narration"] = [{"kind": "insight", "text": " ".join(["word"] * pp.LINE_WORDS_MAX) + "."}]
        shot = dict(keeper_shot(), lines=[0])
        self.assertTrue(pp.build(shot, plan, CHARS).startswith("Image 1 is the narrator."))
        plan["narration"][0]["text"] += " More."
        with self.assertRaisesRegex(SystemExit, "PAVO_LINE_WORDS"):
            pp.build(shot, plan, CHARS)

    def test_malformed_fields_are_refused_before_any_prompt(self):
        plan = flood_plan()
        bad = {"no mood": keeper_shot(emotion="very grave"), "long look": keeper_shot(emotion="a b c d", mood="X and y"),
               "mood": keeper_shot(mood="tender"), "gaze": keeper_shot(gaze="just past the camera"),
               "wardrobe": keeper_shot(wardrobe="armour"), "extra": keeper_shot(hands="folded")}
        for why, s in bad.items():
            self.assertTrue(pp.field_problems(s, CHARS, plan), why)
            with self.assertRaisesRegex(SystemExit, "PAVO_FIELDS_INVALID"):
                pp.build(s, plan, CHARS)
        god = {"id": "s-voice", "kind": "scene", "speaker": "god", "pavo": {"emotion": "calm", "setting": SETTING}}
        self.assertIn("God is never shown", pp.field_problems(god, CHARS, plan)[0])


class TailPad(unittest.TestCase):
    def test_our_line_goes_in_as_cut_like_every_passing_generation(self):
        # E293: no passing generation of record had added silence; the pad mechanism stays, set to none
        self.assertEqual(pp.TAIL_PAD, 0.0)
        self.assertEqual([pp.tail_pad(x, 8) for x in (7.55, 7.70, 7.98)], [0.0, 0.0, 0.0])
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


class SilentClips(unittest.TestCase):
    """Owner 2026-11-04: "Pode continuar fazendo com pavo mais coloca só vídeos sem narração.. e coloca a narração por
    fora..": a silent Pavo clip is an acting clip with no speech and no lip-sync; our Kokoro audio goes over it."""

    SET = "Dawn on the wet hillside, pale gold light on his face, mist behind him."

    def noah(self, **pavo):
        f = {"action": "shapes the clay with both hands, eyes on his work", "view": "profile", "setting": self.SET,
             "mood": "Solemn and grave"}
        return {"id": "n-hook", "kind": "scene", "speaker": "noah", "characters": ["noah"], "pavo_mode": "silent",
                "pavo_audio": "none", "line": "Make thee an ark of gopher wood.", "reference": "Genesis 6:14 (KJV)",
                "pavo": dict(f, **pavo)}

    def keeper(self, **pavo):
        f = {"action": "watches the fire, then slowly nods", "setting": SETTING, "wardrobe": "fire",
             "mood": "Tender and grave"}
        return {"id": "k-a", "kind": "keeper", "lines": [0], "pavo_mode": "silent", "pavo_audio": "none",
                "pavo": dict(f, **pavo)}

    def test_the_silent_template_is_the_passing_framing_with_an_action_and_the_silence_sentence(self):
        plan = {"aspect_ratio": "9:16", "narration": [{"text": "x"}]}
        built = pp.build(self.noah(), plan, CHARS)
        self.assertTrue(built.startswith("Image 1 is Noah. " + pp.STYLE + " Medium close-up, static camera. Noah, "))
        for must in ("seen in profile, centred in the frame, shapes the clay with both hands, eyes on his work, his mouth "
                     "closed.", self.SET + " Solemn and grave.", "No talking, no lip movement, no dialogue. No text, "
                     "no logos."):
            self.assertIn(must, built)
        self.assertIsNone(pp.silent_speech(built))
        self.assertEqual(pp.SILENT_VERSION, "pavo-silent-v1")
        self.assertEqual(pp.VERSION, "pavo-talk-v2")   # approved talking digests carry it: it does not move
        # the Keeper keeps his 16:9 chest-up framing; at 9:16 the medium close-up
        wide = pp.build(self.keeper(), {"aspect_ratio": "16:9", "narration": [{"text": "x"}]}, CHARS)
        self.assertIn("Close-up from the chest up, his face large in the centre of the frame, static camera. The narrator",
                      wide)
        self.assertIn("facing the camera, centred in the frame, watches the fire, then slowly nods",
                      wide)
        # a talking shot is untouched by the new mode
        self.assertIn("speaks the words of the audio clip", pp.build(keeper_shot(), flood_plan(), CHARS))

    def test_a_silent_prompt_never_asks_for_speech_or_lip_sync(self):
        plan = {"aspect_ratio": "9:16", "narration": [{"text": "x"}]}
        for action in ("speaks the words to the camera", "says his piece slowly", "moves his lips in sync with the voice",
                       "whispers a prayer aloud", "sings by the fire", "opens his mouth and shouts"):
            with self.assertRaisesRegex(SystemExit, "PAVO_SILENT_SPEECH"):
                pp.build(self.noah(action=action), plan, CHARS)
        with self.assertRaisesRegex(SystemExit, "PAVO_SILENT_SPEECH"):
            pp.build(self.keeper(mood="Tender and speaking"), plan, CHARS)
        self.assertIsNone(pp.silent_speech("Image 1 is the narrator. No talking, no lip movement, no dialogue."))
        self.assertIn("lipsync", pp.silent_speech("lipsync to the voice"))

    def test_a_characters_voiced_line_is_never_a_frontal_face_visibly_mouthing_it(self):
        plan = {"aspect_ratio": "9:16", "narration": [{"text": "x"}]}
        for bad in ({"view": "frontal"}, {"action": "looks into the camera with grave eyes"}):
            with self.assertRaisesRegex(SystemExit, "PAVO_SILENT_FRONTAL"):
                pp.build(self.noah(**bad), plan, CHARS)
        self.assertIn("turned three-quarters from the camera", pp.build(self.noah(view="three-quarter"), plan, CHARS))
        # the Keeper's own frontal, mouth-closed narration clip is the established voice-over look
        self.assertIn("facing the camera", pp.build(self.keeper(), plan, CHARS))

    def test_god_is_never_shown_and_pavo_audio_is_never_used(self):
        plan = {"aspect_ratio": "9:16", "narration": [{"text": "x"}]}
        god = dict(self.noah(), speaker="god", characters=[])
        with self.assertRaisesRegex(SystemExit, "God is never shown"):
            pp.build(god, plan, CHARS)
        for audio in ("pavo", "ours"):
            with self.assertRaisesRegex(SystemExit, "PAVO_SILENT_AUDIO"):
                pp.build(dict(self.noah(), pavo_audio=audio), plan, CHARS)
        for bad in ({"view": "behind"}, {"camera": "whip pan"}, {"mood": "grave"}, {"action": "Works."}, {"extra": "x"},
                    {"wardrobe": "armour"}):
            with self.assertRaisesRegex(SystemExit, "PAVO_FIELDS_INVALID"):
                pp.build(self.noah(**bad), plan, CHARS)
        with self.assertRaisesRegex(SystemExit, "PAVO_FIELDS_INVALID"):
            pp.build(self.keeper(wardrobe=None), plan, CHARS)


if __name__ == "__main__":
    unittest.main()
