#!/usr/bin/env python3
"""Offline checks of the arc compilation long (E251): plan refusal, a real ffmpeg render of tiny stand-ins (framing,
join, loudness, QA) and the defect-gated review track through long_review, prepublish_gate and publication_binding."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "migration/publish"))
sys.path.insert(0, str(ROOT / "migration/production"))
import compilation_long as cl  # noqa: E402
import long_review as lr  # noqa: E402
import owner_quality_policy as oq  # noqa: E402
import prepublish_gate as pg  # noqa: E402
import publication_binding as pb  # noqa: E402

PLAN = ROOT / "migration/production/bible/compilations/arc-02-noah-compilation.json"
FFMPEG = shutil.which("ffmpeg") is not None
SHA = "a" * 64


def ff(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


class PlanTests(unittest.TestCase):
    def test_the_real_plan_is_accepted(self):
        plan = cl.load(PLAN)
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertEqual([c["short"] for c in plan["chapters"]],
                         [f"genesis-0{n}-short" for n in (6, 7, 8, 9)])
        self.assertLessEqual(len(plan["title"]), 100)

    def test_a_public_long_is_a_chapter(self):
        plan = cl.load(PLAN)
        long_ch = {"long": {"id": "flood-ends-long", "pilot": "pilot-017", "video_id": "1m-NUJhkdMY",
                            "sha256": "9" * 64, "seconds": 501.8},
                   "title": "The Flood Ends", "reference": "Genesis 8-9"}
        plan["chapters"].append(long_ch)
        self.assertEqual(cl.plan_problems(plan), [])
        src = cl.sources(plan)
        self.assertEqual(src[-1][:3], ("flood-ends-long", "pilot-017-sha256-" + "9" * 64 + ".mp4", "9" * 64))
        self.assertEqual(cl.chapter_url(long_ch), "https://www.youtube.com/watch?v=1m-NUJhkdMY")
        for mutate in (lambda c: c["long"].update(sha256="x"), lambda c: c["long"].update(video_id=""),
                       lambda c: c["long"].update(pilot="p17")):
            bad = copy.deepcopy(plan)
            mutate(bad["chapters"][-1])
            self.assertTrue(any("not a public long" in x for x in cl.plan_problems(bad)))

    def test_e284_the_complete_noah_plan_uses_the_voiceover_fallback_and_the_release_master(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertEqual(plan["title"], "The Complete Story of Noah (Genesis 5-9) KJV")
        self.assertEqual([cl.chapter_id(c) for c in plan["chapters"]],
                         [f"genesis-0{n}-short" for n in (6, 7, 8, 9)] + ["flood-ends-long"])
        self.assertEqual(cl.sources(plan)[-1][1], "bible-flood-ends-long-sha256-" + plan["chapters"][-1]["long"]["sha256"] + ".mp4")
        self.assertTrue(cl.has_voiceover(plan))
        for key in ("hook", "close"):
            self.assertNotIn("Genesis five to seven", plan[key]["text"])
        for mutate, text in ((lambda p: p["hook"]["voiceover"].update(still_sha256="0" * 64), "still missing or changed"),
                             (lambda p: p["close"]["voiceover"].update(voice_id="af_heart"), "pinned voice"),
                             (lambda p: p["close"].update(quote="0 credits (exact, fresh)"), "no-Pavo zero-credit"),
                             (lambda p: p["hook"].pop("pavo_attempt"), "Pavo attempt"),
                             (lambda p: p["chapters"][-1]["long"].update(asset="bible-other-sha256-" + "0" * 64 + ".mp4"), "release master")):
            bad = copy.deepcopy(plan)
            mutate(bad)
            self.assertTrue(any(text in x for x in cl.plan_problems(bad)), text)

    def test_e289_a_keeper_segment_under_10_s_is_no_chapter_of_its_own(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")
        seg = lambda kind, a, b: {"kind": kind, "start": a, "end": b}
        tl = {"segments": [seg("hook", 0, 9.3), seg("short", 9.3, 80), seg("short", 80, 246), seg("short", 246, 414),
                           seg("short", 414, 580), seg("long", 580, 1073), seg("close", 1073, 1082.5)]}
        _, rows = cl.description(plan, tl)
        self.assertEqual(rows[0], (0, plan["chapters"][0]["title"]))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1][1], plan["chapters"][-1]["title"])
        self.assertTrue(all(b[0] - a[0] >= 10 for a, b in zip(rows, rows[1:])))   # the preflight's own rule
        tl["segments"][0]["end"], tl["segments"][-1]["start"] = 12.0, 1070.0       # 10 s or more: its own chapter again
        _, rows = cl.description(plan, tl)
        self.assertEqual((rows[0][1], rows[-1][1]), (plan["chapter_zero"], plan["chapter_last"]))

    def test_refusals(self):
        plan = cl.load(PLAN)
        for mutate, text in ((lambda p: p["chapters"].reverse(), "canonical order"),
                             (lambda p: p["chapters"].pop(1), "canonical order"),
                             (lambda p: p["hook"].update(quote="2 credits"), "zero-credit"),
                             (lambda p: p["close"].update(audio_sha256="0" * 64), "changed"),
                             (lambda p: p["chapters"][0].update(short="nope"), "unknown short")):
            p = copy.deepcopy(plan)
            mutate(p)
            self.assertTrue(any(text in x for x in cl.plan_problems(p)), text)

    def test_e254_each_chapter_cuts_the_shorts_own_series_cta(self):
        plan = cl.load(PLAN)
        for c in plan["chapters"]:   # the Shorts close with "the full story is in the long video" / "part N tomorrow"
            self.assertIsInstance(c.get("end_s"), (int, float), c["short"])
        self.assertNotIn("FULL STORY", json.dumps(plan["thumbnail"]).upper())   # Genesis 5-7 is not the full story
        for bad in (5, 10_000, "70"):
            p = copy.deepcopy(plan)
            p["chapters"][0]["end_s"] = bad
            self.assertTrue(any("end_s" in x for x in cl.plan_problems(p)), bad)

    def test_sources_are_the_episode_records_masters(self):
        for sid, asset, sha, ep in cl.sources(cl.load(PLAN)):
            self.assertEqual(asset, f"bible-{sid}-sha256-{sha}.mp4")
            self.assertEqual(sha, ep["output_sha256"])


@unittest.skipUnless(FFMPEG, "ffmpeg")
class RenderTests(unittest.TestCase):
    def test_short_card_keeper_join_and_loudness(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            ff("-f", "lavfi", "-i", "testsrc=s=270x480:r=30:d=3", "-f", "lavfi", "-i", "sine=f=300:r=44100:d=3",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", t / "short.mp4")
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", t / "k.mp4")
            ff("-f", "lavfi", "-i", "sine=f=200:r=24000:d=1.5", t / "k.wav")
            cl.render_short(t / "short.mp4", t / "s.mp4")
            cl.render_short(t / "short.mp4", t / "c.mp4", None, ("PART 1 OF 4", "Enoch Walked With God", "Genesis 5:21-24 (KJV)"))
            cl.render_keeper(t / "k.mp4", t / "k.wav", t / "h.mp4")
            for f, secs in (("s.mp4", 3.0), ("c.mp4", 3.0), ("h.mp4", 2.0 + 2 * cl.BEAT)):
                p = json.loads(cl.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                       "stream=width,height", "-of", "json", t / f]).stdout)["streams"][0]
                self.assertEqual((p["width"], p["height"]), (1920, 1080), f)
                self.assertAlmostEqual(cl.duration(t / f), secs, delta=0.15, msg=f)
            lufs, peak = cl.loudness(t / "s.mp4")
            self.assertTrue(cl.LUFS_BAND[0] <= lufs <= cl.LUFS_BAND[1] + 1.0, lufs)   # fades lower the mean a little
            self.assertLessEqual(peak, cl.TRUE_PEAK_MAX)   # E251: -0.8 dBTP after AAC failed the first real build
            self.assertEqual(cl.fps("30000/1001") > 29.9, True)
            self.assertAlmostEqual(cl.fps("30/1"), 30.0)
            self.assertLess(abs(cl.fps("295249920/9864919") - cl.FPS), cl.FPS_TOLERANCE)   # the real master's average
            # the Keeper clip: still beat of silence at the head (the line starts after BEAT)
            head = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-t", "0.4", "-i", t / "h.mp4", "-af", "volumedetect",
                           "-f", "null", "-"]).stderr
            self.assertIn("max_volume: -91", head)


@unittest.skipUnless(FFMPEG, "ffmpeg")
class CardTests(unittest.TestCase):
    def test_e258_the_chapter_card_is_drawn_over_its_short_not_dead_air(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            ff("-f", "lavfi", "-i", "testsrc=s=270x480:r=30:d=4", "-f", "lavfi", "-i", "sine=f=300:r=44100:d=4",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", t / "short.mp4")
            cl.render_short(t / "short.mp4", t / "c.mp4", None, ("PART 1 OF 4", "Enoch Walked With God", "Genesis 5:21-24 (KJV)"))
            log = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", t / "c.mp4", "-vf", "blackdetect=d=0.1:pic_th=0.98",
                          "-af", "silencedetect=n=-60dB:d=0.5", "-f", "null", "-"]).stderr
            self.assertNotIn("black_start", log)
            self.assertNotIn("silence_start", log)
        self.assertFalse(hasattr(cl, "render_card"))
        plan = cl.load(PLAN)
        segs = cl.script_segments(plan)
        self.assertEqual([s["kind"] for s in segs], ["hook"] + ["short"] * len(plan["chapters"]) + ["close"])
        self.assertTrue(all(s["text"].strip() for s in segs))


def review_doc(**kw):
    issues = ["0:10 a caption touches the card edge", "3:00 mild AI artifact"]
    base = {"model": "claude-session-reviewer", "output_sha256": SHA, "issues": issues,
            "defects": [{"issue": 0, "category": "d", "resolved": False}, {"issue": 1, "category": "info", "resolved": False}],
            "publish_decision": {"decision": "publish", "by": "claude-session-reviewer", "note": "watched and heard it"},
            "evidence": ["watched the master", "listened to the joins"]}
    base.update(kw)
    return base


class ReviewTrackTests(unittest.TestCase):
    def test_defect_gate_rules(self):
        self.assertEqual(oq.compilation_problems(review_doc(), SHA), [])   # a score floor is not part of this track
        bad = review_doc(defects=[{"issue": 0, "category": "a", "resolved": False}, {"issue": 1, "category": "info", "resolved": False}])
        self.assertIn("REVIEW_DEFECT_UNRESOLVED", oq.compilation_problems(bad, SHA))
        ok = review_doc(defects=[{"issue": 0, "category": "b", "resolved": True}, {"issue": 1, "category": "info", "resolved": False}])
        self.assertEqual(oq.compilation_problems(ok, SHA), [])
        for kw, code in ((dict(model="gemini-3.8-flash"), "REVIEW_MODEL_NOT_DESIGNATED"),
                         (dict(output_sha256="b" * 64), "REVIEW_NOT_FOR_THIS_FILE"),
                         (dict(publish_decision={"decision": "hold", "by": "claude-session-reviewer", "note": "x"}), "REVIEW_DECISION_MISSING"),
                         (dict(defects=[{"issue": 0, "category": "d", "resolved": True}]), "REVIEW_DEFECTS_INVALID")):
            self.assertIn(code, oq.compilation_problems(review_doc(**kw), SHA))

    def pilot(self, root, review=None):
        d = Path(root) / "pilot-016"
        (d / "out").mkdir(parents=True)
        (d / "inspection").mkdir()
        (d / "script.json").write_text(json.dumps({"pilot_id": "pilot-016", "archetype": pg.COMPILATION_ARCHETYPE}))
        (d / "out/manifest.json").write_text(json.dumps({"output_sha256": SHA, "output_seconds": 600}))
        if review is not None:
            (d / "inspection/claude_review.json").write_text(json.dumps(review))
        return d

    def test_long_review_routes_to_the_defect_gate(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.pilot(t)
            lr.main(str(d))
            self.assertEqual(json.loads((d / "out/review.json").read_text())["status"], "AWAITING_REVIEW")
            d = self.pilot(t + "/x", review_doc())
            lr.main(str(d))
            r = json.loads((d / "out/review.json").read_text())
            self.assertEqual((r["status"], r["track"]), ("PASS", "compilation"))
            self.assertEqual(oq.compilation_problems({**r["watched_review"], "output_sha256": SHA}, SHA), [])

    def gate_items(self, review):
        return {i["item"]: i["state"] for i in pg.compilation_review_items(review, SHA)}

    def test_gate_review_items(self):
        self.assertEqual(set(self.gate_items(None).values()), {"UNKNOWN"})
        passed = {"status": "PASS", "output_sha256": SHA, "watched_review": {k: v for k, v in review_doc().items() if k != "output_sha256"}}
        self.assertEqual(set(self.gate_items(passed).values()), {"PASS"})
        unresolved = copy.deepcopy(passed)
        unresolved["watched_review"]["defects"][0] = {"issue": 0, "category": "e", "resolved": False}
        self.assertEqual(self.gate_items(unresolved)["no_unresolved_a_b_e"], "FAIL")

    def test_other_tracks_are_unchanged(self):
        self.assertNotIn(pg.COMPILATION, pg.STANDARD_VERSIONS)
        self.assertIn(pg.STORY_V5, pg.STANDARD_VERSIONS)
        self.assertEqual(pg.score_hard_keys(pg.STORY_V5), ("minutes",))
        self.assertTrue(oq.check({"status": "PASS", "model": "claude-session-reviewer", "overall": 9.4,
                                  "output_sha256": SHA}, SHA, oq.LONG_REVIEWERS))   # the 9.5 floor still refuses

    def test_frozen_criteria_hash(self):
        self.assertEqual(pg.sha256_file(pg.CRITERIA_FILES[pg.COMPILATION]), pg.FROZEN_CRITERIA_SHA256[pg.COMPILATION])


if __name__ == "__main__":
    unittest.main()
