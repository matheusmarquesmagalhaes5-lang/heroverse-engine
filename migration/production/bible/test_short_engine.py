#!/usr/bin/env python3
"""short_engine.py: shots tile the Short, clips are never looped or slowed past MAX_SLOW, captions stay short."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import short_engine as se


class Plan(unittest.TestCase):
    def test_e146_native_picture_and_audio_use_the_same_measured_source_onset(self):
        import episode_build as eb
        import long_build as lb
        import pavo_native as pn
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            clip = d / "native.mp4"
            clip.write_bytes(b"approved native clip")
            layout = {"lines": [{"start": 0.0, "end": 2.0}], "total": 3.2}
            spans = {"s-eve": ([0], 0.6, 2.6)}
            approvals = {"s-eve": {"clip_sha256": eb.sha256(clip),
                                    "speech": {"gain_db": 1.0, "onset": 0.6, "end": 2.6}}}
            mixed = []
            with patch.object(eb, "native_spans", return_value=spans), \
                    patch.object(eb.clip_timing, "measure", return_value={"clip_sha256": eb.sha256(clip),
                                 "video_seconds": 4.0, "audio_seconds": 4.0}), \
                    patch.object(pn, "premix", side_effect=lambda voice, places, out, total: mixed.extend(places)):
                voice, seconds, onsets = eb.native_voice({}, d, layout, {"s-eve": str(clip)},
                                                        {"s-eve": 4.0}, approvals)
            cuts = eb.shift_onsets([{"shot": "s-eve", "clip": str(clip), "start": 0.0, "end": 3.2,
                                     "src_start": 0.0, "speed": 1.0, "talk": {"start": 0.0, "end": 2.0}}], onsets)
            self.assertEqual(cuts[0]["src_start"], mixed[0]["src_start"])
            timeline = d / "timeline.json"
            timeline.write_text(json.dumps({"voice_seconds": 2.0, "sentences": layout["lines"]}))
            cplan = {"voice": voice, "timeline": str(timeline), "music": "unused", "shots": cuts,
                     "native_onsets": onsets}
            # The real renderer must reach its media stage after validating this synchronized plan. Stop exactly
            # there: no encode is needed to reproduce the former PLAN_REFUSED at the producer/consumer boundary.
            with patch.object(se, "duration", return_value=4.0), \
                    patch.object(lb, "run", side_effect=RuntimeError("media stage reached")):
                with self.assertRaisesRegex(RuntimeError, "media stage reached"):
                    lb.render(cplan, d / "out.mp4")
            self.assertEqual(se.talk_problems(cuts, layout["lines"], onsets), [])
            for change in ({"src_start": 0.0}, {"src_start": 0.7}, {"speed": 1.1}, {"end": 1.9}, {"start": 0.1}):
                wrong = [dict(cuts[0], **change)]
                self.assertIn("TALK_NOT_ALIGNED 0", se.talk_problems(wrong, layout["lines"], onsets), change)
            # A positive offset without an actual native audio placement is still refused; Kokoro remains at 0.
            self.assertIn("TALK_NOT_ALIGNED 0", se.talk_problems(cuts, layout["lines"]))
            kokoro = copy.deepcopy(cuts)
            kokoro[0]["src_start"] = 0.0
            self.assertEqual(se.talk_problems(kokoro, layout["lines"]), [])
            kokoro[0]["src_start"] = 0.0005
            self.assertIn("TALK_NOT_ALIGNED 0", se.talk_problems(kokoro, layout["lines"]))
            for invalid in (float("nan"), float("inf"), -float("inf"), -0.1):
                self.assertIn("TALK_NOT_ALIGNED 0", se.talk_problems(cuts, layout["lines"], {"s-eve": invalid}))

    def test_shots_must_tile_the_short(self):
        ok = [{"start": 0.0, "end": 5.0}, {"start": 5.0, "end": 10.0}]
        self.assertEqual(se.check_shots(ok, 10.0), [])
        gap = [{"start": 0.0, "end": 5.0}, {"start": 5.5, "end": 10.0}]
        self.assertTrue(any(p.startswith("SHOT_GAP_OR_OVERLAP") for p in se.check_shots(gap, 10.0)))
        self.assertTrue(any(p.startswith("SHOTS_END") for p in se.check_shots(ok, 12.0)))
        self.assertIn("SHOT_TOO_SHORT 1", se.check_shots([{"start": 0.0, "end": 9.5}, {"start": 9.5, "end": 10.0}], 10.0))

    def test_clip_is_slowed_at_most_max_slow_never_looped(self):
        self.assertEqual(se.speed({"start": 0, "end": 5, "src_start": 0}, 6.58), 1.0)
        self.assertAlmostEqual(se.speed({"start": 0, "end": 9.65, "src_start": 0}, 8.0), 9.65 / 8.0)
        self.assertIsNone(se.speed({"start": 0, "end": 9.0, "src_start": 1.0}, 6.58))

    def test_captions_two_words_inside_the_sentence(self):
        cards = se.chunks({"start": 1.0, "end": 4.0, "text": "And Enoch walked with God:"})
        self.assertEqual([c["text"] for c in cards], ["And Enoch", "walked with", "God:"])
        self.assertAlmostEqual(cards[0]["start"], 1.0)
        self.assertAlmostEqual(cards[-1]["end"], 4.0)
        ass = se.build_ass([{"start": 0.3, "end": 2.0, "text": "a {b} c\\d"}])
        self.assertNotIn("{b}", ass)
        self.assertIn("WrapStyle: 0", ass)

    def test_e249_scripture_is_styled_apart_and_cited_with_chapter_and_verse(self):
        ass = se.build_ass([
            {"start": 0.0, "end": 2.0, "text": "our own words here"},
            {"start": 2.0, "end": 5.0, "text": "There went in two and two", "kind": "scripture",
             "reference": "Genesis 7:9 (KJV)"}])
        lines = [x for x in ass.splitlines() if x.startswith("Dialogue")]
        own = [x for x in lines if ",Cap,," in x]
        scr = [x for x in lines if ",Scr,," in x]
        ref = [x for x in lines if ",Ref,," in x]
        self.assertEqual(len(own), 2)                     # our commentary stays in the normal captions
        self.assertTrue(scr and not any("our own" in x for x in scr))
        self.assertEqual(len(ref), 1)                     # one citation for the whole quotation
        self.assertTrue(ref[0].endswith("Genesis 7:9 · KJV"))
        self.assertIn(",0:00:02.00,0:00:05.00,Ref,", ref[0])
        self.assertIn("Style: Scr,DejaVu Serif", ass)     # its own typography
        self.assertEqual(se.citation("Genesis 6:13 (KJV)"), "Genesis 6:13 · KJV")
        self.assertEqual(se.citation(None), "")
        # scripture without a reference is never silently shown as plain captions with a made-up citation
        plain = se.build_ass([{"start": 0, "end": 1, "text": "x y", "kind": "scripture"}])
        self.assertNotIn(",Ref,,", plain)

    def test_e249_compose_timeline_carries_kind_and_reference_to_the_captions(self):
        src = (Path(__file__).resolve().parent / "episode_build.py").read_text()
        self.assertIn('who.update(kind="scripture", reference=items[k]["reference"])', src)



class Crossfades(unittest.TestCase):
    """Owner 2026-11-02: a long-first long blends the picture into and out of each talking shot, in the silence next to
    his words; the Shorts keep cuts only."""

    SCENE_A = {"start": 0.0, "end": 5.0, "kind": "scene"}
    TALK = {"start": 5.0, "end": 8.6, "kind": "keeper", "talk": {"start": 5.0, "end": 8.6}}
    SCENE_B = {"start": 8.6, "end": 14.0, "kind": "scene"}

    def shots(self):
        return [dict(self.SCENE_A), dict(self.TALK), dict(self.SCENE_B)]

    def test_a_window_lies_in_the_silence_next_to_a_talking_shot(self):
        said = [{"start": 0.4, "end": 4.4}, {"start": 5.0, "end": 8.6}, {"start": 9.0, "end": 13.0}]
        found = se.transitions(self.shots(), said, 0.3)
        self.assertEqual([(w["between"], w["side"], w["frames"]) for w in found], [(0, "into", 9), (1, "out", 9)])
        self.assertEqual((found[0]["start"], found[0]["end"]), (4.7, 5.0))   # ends on his first word
        self.assertEqual((found[1]["start"], found[1]["end"]), (8.6, 8.9))   # starts on his last word's end
        self.assertEqual(se.transition_problems(found, said), [])

    def test_no_window_without_the_option_between_scenes_or_without_room(self):
        said = [{"start": 5.0, "end": 8.6}]
        self.assertEqual(se.transitions(self.shots(), said, 0), [])          # the Shorts: cuts only
        self.assertEqual(se.transitions(self.shots(), said, None), [])
        two = [dict(self.SCENE_A), dict(self.SCENE_B, start=5.0)]
        self.assertEqual(se.transitions(two, said, 0.3), [])                 # scene to scene stays a cut
        tight = [{"start": 0.4, "end": 4.9}, {"start": 5.0, "end": 8.6}, {"start": 8.7, "end": 12.0}]    # a gap too small for a clean blend
        self.assertEqual(se.transitions(self.shots(), tight, 0.3), [])
        near = [{"start": 0.4, "end": 4.0}, {"start": 5.0, "end": 8.6}, {"start": 8.8, "end": 12.0}]     # 0.2 s of silence: a shorter window
        out = [w for w in se.transitions(self.shots(), near, 0.3) if w["side"] == "out"]
        self.assertEqual(out[0]["frames"], 5)
        self.assertLessEqual(out[0]["end"], 8.8 - se.XFADE_CLEAR + 1e-6)
        self.assertEqual(se.transitions(self.shots(), [], 9.0)[0]["frames"], round(se.XFADE_MAX * se.FPS))

    def test_a_window_over_a_word_is_refused(self):
        bad = [{"between": 0, "side": "into", "start": 4.7, "end": 5.0, "frames": 9}]
        self.assertEqual(se.transition_problems(bad, [{"start": 4.8, "end": 6.0}]), ["XFADE_OVER_SPEECH 0 into"])

    def test_the_blend_keeps_every_frame_count_and_leaves_the_words_untouched(self):
        import shutil
        import subprocess
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg missing")
        fps, w, h = se.FPS, 160, 90
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)

            def clip(name, colour, seconds):
                path = d / name
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                                f"color=c={colour}:s={w}x{h}:r={fps}:d={seconds}", "-c:v", "libx264", "-pix_fmt",
                                "yuv420p", str(path)], check=True)
                return path
            red, blue, green = clip("a.mp4", "red", 6), clip("b.mp4", "blue", 6), clip("c.mp4", "green", 6)
            shots = self.shots()
            shots[0].update(clip=str(red), src_start=0.0)
            shots[1].update(clip=str(blue), src_start=0.0, speed=1.0)
            shots[2].update(clip=str(green), src_start=0.0)
            parts = []
            for i, s in enumerate(shots):
                part = d / f"p{i}.mp4"
                se.encode(Path(s["clip"]), part, round((s["end"] - s["start"]) * fps))
                parts.append(part)
            said = [{"start": 0.4, "end": 4.4}, {"start": 5.0, "end": 8.6}, {"start": 9.0, "end": 13.0}]
            windows = se.transitions(shots, said, 0.3)
            joined = se.join_with_crossfades(d, parts, shots, windows, w, h)
            self.assertEqual(sum(se.frame_count(p) for p in joined), sum(se.frame_count(p) for p in parts))
            (d / "list.txt").write_text("".join(f"file '{p}'\n" for p in joined))
            whole = d / "whole.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                            str(d / "list.txt"), "-c", "copy", str(whole)], check=True)

            def pixel(t):   # the (R, G, B) centre pixel at time t
                raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.4f}", "-i", str(whole), "-frames:v",
                                      "1", "-vf", "crop=1:1:80:45,format=rgb24", "-f", "rawvideo", "-"],
                                     capture_output=True, check=True).stdout
                return tuple(raw[:3])
            red_px, blue_px, green_px = pixel(1.0), pixel(6.0), pixel(12.0)
            self.assertGreater(red_px[0], 200)
            self.assertGreater(blue_px[2], 200)
            self.assertGreater(green_px[1], 100)
            # inside the first window (4.7-5.0) red gives way to blue, never to black
            early, mid, late = pixel(4.7 + 1.0 / fps), pixel(4.85), pixel(4.98)
            self.assertGreater(early[0], late[0])
            self.assertGreater(late[2], early[2])
            self.assertGreater(mid[0] + mid[2], 150)
            # the first word and everything after it is the talker's own picture; the shot before is untouched until 4.7
            self.assertGreater(pixel(5.05)[2], 200)
            self.assertGreater(pixel(4.65)[0], 200)
            # out of the talker: blue to green inside 8.6-8.9, then green
            self.assertGreater(pixel(8.55)[2], 200)
            self.assertGreater(pixel(8.9 + 2.0 / fps)[1], 100)
            self.assertGreater(pixel(8.75)[0] + pixel(8.75)[1] + pixel(8.75)[2], 120)

if __name__ == "__main__":
    unittest.main()
