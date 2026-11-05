#!/usr/bin/env python3
"""Same-story still reuse (owner 2026-11-05): an APPROVED still of another plan of the same story, reframed into a NEW
still of this plan, approved only by its own review; a third of the plan's stills at most, never under its source's
line, and the plan keeps its own Keeper and insight. Each REUSE_* refusal and the happy path."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_check as pc  # noqa: E402
import scene_stills as ss  # noqa: E402
import still_reuse as sr  # noqa: E402

SHORT = json.loads((HERE / "plans" / "genesis-12-short.json").read_text())
LONG = json.loads((HERE / "plans" / "genesis-10-11-long.json").read_text())
CHECKS = list(pc.REUSE_REVIEW_CHECKS)
REVIEWER = "claude-session-reviewer"


def jpeg(path, size, colour=(120, 80, 40)):
    from PIL import Image
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path, "JPEG", quality=90)


class Reuse(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix=".test-reuse-", dir=HERE))   # inside the repository (repo_path)
        self.saved = (pc.STILLS_DIR, pc.REUSE_PLANS_DIR, ss.HERE)
        pc.STILLS_DIR, pc.REUSE_PLANS_DIR, ss.HERE = self.dir, self.dir / "plans", self.dir
        self.short, self.long = copy.deepcopy(SHORT), copy.deepcopy(LONG)
        self.write_plans()
        for f in (HERE / "stills").glob("genesis-12-short-s-*.json"):
            shutil.copyfile(f, self.dir / f.name)
        for shot in ("s-kiln", "s-confound", "s-gathered", "s-top", "s-behold", "s-foundation", "s-babel"):
            self.source(shot)

    def tearDown(self):
        pc.STILLS_DIR, pc.REUSE_PLANS_DIR, ss.HERE = self.saved
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_plans(self):
        ss.save(self.dir / "plans" / "genesis-12-short.json", self.short)
        ss.save(self.dir / "plans" / "genesis-10-11-long.json", self.long)

    def source(self, shot, size=(2560, 1440), status="APPROVED", pixels=None):
        """An APPROVED long still of the test's own (its real prompt), at SIZE; PIXELS: its download's."""
        sid = f"genesis-10-11-long-{shot}"
        rec = json.loads((HERE / "stills" / f"{sid}.json").read_text())
        img = self.dir / f"{sid}.jpg"
        jpeg(img, size)
        rec.update(status=status, repo_path=ss.rel(img), sha256=ss.sha256(img), size=list(size),
                   candidate=f"{sid}-1-1" if pixels else None)
        if pixels:
            ss.save(self.dir / "candidates" / f"{sid}-1-1.json", {"download": {"pixels": list(pixels)}})
        ss.save(self.dir / f"{sid}.json", rec)
        return rec

    def derive(self, shot="s-kiln", **kw):
        return sr.derive(self.short, shot, f"genesis-10-11-long-{shot}", "2026110501", stills_dir=self.dir, **kw)

    def approve(self, shot="s-kiln", checked=CHECKS, note="Looked at the reframed 9:16 image: kiln centred."):
        still = f"genesis-12-short-{shot}"
        return ss.approve(still, f"{still}-2026110501-1", 9.5, note, stills_dir=self.dir, reviewer=REVIEWER,
                          checked=checked)

    def frame(self, shot="s-kiln"):
        i = next(k for k, s in enumerate(self.short["shots"]) if s["id"] == shot)
        return pc.frame_problems(i, self.short["shots"][i], self.short, self.dir)

    def codes(self, rows):
        return {r.split()[0] for r in rows}

    # ---------- happy path ----------
    def test_a_reframed_same_story_still_is_a_new_record_approved_by_its_own_review(self):
        meta = self.derive()
        self.assertEqual(meta["crop"]["box"], [875, 0, 810, 1440])
        self.assertEqual(meta["size"], [1080, 1920])
        rec = self.approve()
        src = pc.still_record("genesis-10-11-long-s-kiln", self.dir)
        self.assertEqual(rec["status"], "APPROVED")
        self.assertEqual(rec["derived_from"]["sha256"], src["sha256"])
        self.assertNotEqual(rec["sha256"], src["sha256"])
        self.assertEqual(rec["approved"]["review"]["reviewed_sha256"], rec["sha256"])
        self.assertNotEqual(rec["approved"]["note"], src["approved"]["note"])
        self.assertEqual(self.frame(), [])
        self.assertEqual(pc.reuse_plan_problems(self.short, self.dir), [])

    def test_passages_overlap_by_book_and_verse(self):
        self.assertTrue(pc.same_story(SHORT, LONG))
        self.assertFalse(pc.same_story({"passage": "Genesis 12:1-9"}, {"passage": "Genesis 11:1-9"}))
        self.assertTrue(pc.same_story({"passage": "Exodus 3", "story_id": "x"}, {"passage": "Genesis 1", "story_id": "x"}))
        self.assertEqual(pc.passage_ranges("Genesis 10-11:9 (KJV), with Genesis 12:2"),
                         [("Genesis", 10001, 11009), ("Genesis", 12002, 12002)])

    def test_candidates_list_same_story_matches(self):
        rows = sr.candidates(self.short, stills_dir=self.dir, plans_dir=self.dir / "plans")
        self.assertEqual(rows["s-kiln"][0]["still"], "genesis-10-11-long-s-kiln")
        self.assertEqual(rows["s-mercy"], [])

    # ---------- refusals ----------
    def test_other_story_is_refused(self):
        self.long["passage"] = "Exodus 3:1-5 (KJV)"
        self.write_plans()
        with self.assertRaisesRegex(SystemExit, "REUSE_OTHER_STORY"):
            self.derive()

    def test_source_not_approved_is_refused(self):
        self.source("s-kiln", status="DRAFT")
        with self.assertRaisesRegex(SystemExit, "REUSE_SOURCE_NOT_APPROVED"):
            self.derive()

    def test_source_bytes_changed_is_refused(self):
        self.derive()
        rec = self.approve()
        jpeg(self.dir / "genesis-10-11-long-s-kiln.jpg", (2560, 1440), colour=(1, 2, 3))
        self.assertIn("REUSE_SOURCE_NOT_APPROVED", self.codes(self.frame()))
        self.assertTrue(rec)

    def test_low_resolution_counts_the_generated_pixels(self):
        self.source("s-kiln", size=(1920, 1080), pixels=(1672, 941))   # 529x941 generated pixels in the crop
        with self.assertRaisesRegex(SystemExit, "REUSE_LOW_RES"):
            self.derive()

    def test_off_centre_crop_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "REUSE_CROP_OFF_CENTRE"):
            self.derive(x=0)

    def test_crop_outside_the_source_is_refused(self):
        rec = dict(pc.still_record("genesis-12-short-s-kiln", self.dir), sha256="a" * 64, size=[1080, 1920],
                   derived_from={"still": "genesis-10-11-long-s-kiln",
                                 "sha256": pc.still_record("genesis-10-11-long-s-kiln", self.dir)["sha256"]},
                   crop={"box": [2000, 0, 810, 1440], "source_size": [2560, 1440]})
        self.assertIn("REUSE_CROP_INVALID", self.codes(pc.derived_still_problems(rec, self.short, self.dir, False)))

    def test_no_review_of_the_reframed_image_is_refused(self):
        self.derive()
        with self.assertRaisesRegex(SystemExit, "REUSE_NO_REVIEW"):
            self.approve(checked=None)
        with self.assertRaisesRegex(SystemExit, "REUSE_NO_REVIEW"):
            self.approve(checked=CHECKS[:2])

    def test_an_approval_copied_from_the_source_is_refused(self):
        self.derive()
        src_note = pc.still_record("genesis-10-11-long-s-kiln", self.dir)["approved"]["note"]
        self.approve(note=src_note)
        self.assertIn("REUSE_NO_REVIEW", self.codes(self.frame()))

    def test_a_review_of_another_image_is_refused(self):
        self.derive()
        rec = self.approve()
        rec["approved"]["review"]["reviewed_sha256"] = rec["derived_from"]["sha256"]
        ss.save(self.dir / "genesis-12-short-s-kiln.json", rec)
        self.assertIn("REUSE_NO_REVIEW", self.codes(self.frame()))

    def test_god_with_a_face_is_refused(self):
        rec = dict(pc.still_record("genesis-12-short-s-kiln", self.dir), sha256="a" * 64, size=[1080, 1920],
                   derived_from={"still": "genesis-10-11-long-s-kiln",
                                 "sha256": pc.still_record("genesis-10-11-long-s-kiln", self.dir)["sha256"]},
                   crop={"box": [875, 0, 810, 1440], "source_size": [2560, 1440]})
        rec["prompt"] += " The face of God looks down on the kiln."
        self.assertIn("REUSE_GOD_FACE", self.codes(pc.derived_still_problems(rec, self.short, self.dir, False)))

    def test_off_scene_source_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "REUSE_OFF_SCENE"):
            sr.derive(self.short, "s-kiln", "genesis-10-11-long-s-behold", "2026110501", stills_dir=self.dir)

    def test_same_plan_chain_and_incomplete_records_are_refused(self):
        own = self.source("s-kiln")
        own_short = dict(own, id="genesis-12-short-s-x", episode="genesis-12-short")
        ss.save(self.dir / "genesis-12-short-s-x.json", own_short)
        base = {"prompt": own["prompt"], "sha256": "a" * 64, "size": [1080, 1920],
                "crop": {"box": [875, 0, 810, 1440], "source_size": [2560, 1440]}}
        same = dict(base, derived_from={"still": "genesis-12-short-s-x", "sha256": own["sha256"]})
        self.assertIn("REUSE_SAME_PLAN", self.codes(pc.derived_still_problems(same, self.short, self.dir, False)))
        chained = dict(own, derived_from={"still": "x", "sha256": "b" * 64})
        ss.save(self.dir / "genesis-10-11-long-s-kiln.json", chained)
        chain = dict(base, derived_from={"still": "genesis-10-11-long-s-kiln", "sha256": own["sha256"]})
        self.assertIn("REUSE_CHAIN", self.codes(pc.derived_still_problems(chain, self.short, self.dir, False)))
        self.assertIn("REUSE_RECORD_INCOMPLETE", self.codes(pc.derived_still_problems(base, self.short, self.dir)))

    def test_more_than_a_third_of_the_stills_is_refused(self):
        pending = {s: f"genesis-10-11-long-{s}" for s in ("s-kiln", "s-gathered", "s-top", "s-behold",
                                                           "s-foundation", "s-babel")}   # 6 of 17 > 5
        self.assertIn("REUSE_SHARE_TOO_HIGH", self.codes(pc.reuse_plan_problems(self.short, self.dir, pending)))
        del pending["s-babel"]
        self.assertNotIn("REUSE_SHARE_TOO_HIGH", self.codes(pc.reuse_plan_problems(self.short, self.dir, pending)))

    def test_the_same_narration_line_as_the_source_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "REUSE_SAME_LINE"):
            self.derive("s-confound")

    def test_a_plan_without_its_own_keeper_insight_is_refused(self):
        self.short["narration"] = [x for x in self.short["narration"] if x["kind"] != "insight"]
        rows = pc.reuse_plan_problems(self.short, self.dir, {"s-kiln": "genesis-10-11-long-s-kiln"})
        self.assertIn("REUSE_NO_ORIGINAL_LAYER", self.codes(rows))
        self.short = copy.deepcopy(SHORT)
        self.short["narration"][0]["text"] = next(x["text"] for x in LONG["narration"] if x["kind"] == "story")
        rows = pc.reuse_plan_problems(self.short, self.dir, {"s-kiln": "genesis-10-11-long-s-kiln"})
        self.assertIn("REUSE_NO_ORIGINAL_LAYER", self.codes(rows))

    def test_a_plan_without_reuse_is_unchanged(self):
        self.assertEqual(pc.reuse_plan_problems(SHORT), [])


if __name__ == "__main__":
    unittest.main()
