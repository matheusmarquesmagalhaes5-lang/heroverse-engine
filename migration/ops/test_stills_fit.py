#!/usr/bin/env python3
"""stills_fit sizes a scene-stills dispatch to today's remaining FLUX images; it never asks more than is left."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stills_fit  # noqa: E402


def plan(n):
    return {"episode": "x-short", "shots": [{"id": f"s-{i}", "first_frame": f"x-short-s-{i}"} for i in range(n)]
            + [{"id": "k-close"}]}


class Fit(unittest.TestCase):
    def test_partial_allocation_still_makes_stills(self):
        # 2026-11-05: 34 used of 44 and 17 shots x 2 asked -> refused; 10 left fit 10 shots at 1 candidate
        pending = [(f"s-{i}", 1) for i in range(17)]
        got = stills_fit.fit(pending, 10, prefer=2)
        self.assertEqual((len(got["shots"]), got["candidates"], got["images"]), (10, 1, 10))

    def test_prefers_candidates_when_everything_fits(self):
        got = stills_fit.fit([("a", 1), ("b", 1)], 44, prefer=2)
        self.assertEqual((got["shots"], got["candidates"], got["images"]), (["a", "b"], 2, 4))

    def test_never_exceeds_remaining(self):
        for rem in range(0, 12):
            got = stills_fit.fit([("a", 2), ("b", 1), ("c", 3)], rem, prefer=3)
            self.assertLessEqual(got["images"], rem)

    def test_nothing_left(self):
        self.assertEqual(stills_fit.fit([("a", 1)], 0)["shots"], [])

    def test_pending_skips_approved_excluded_and_frameless(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x-short-s-0.json").write_text(json.dumps({"status": "APPROVED"}))
            Path(d, "x-short-s-1.json").write_text(json.dumps({"status": "DRAFT"}))
            got = stills_fit.pending_shots(plan(4), stills_dir=d, exclude={"s-3"})
        self.assertEqual([s for s, _ in got], ["s-1", "s-2"])

    def test_cli_with_used(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "plan.json")
            p.write_text(json.dumps(plan(17)))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = stills_fit.main(["stills_fit.py", str(p), "--used", "34"])
        res = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertLessEqual(res["images"], res["remaining"])
        self.assertEqual(res["remaining"], stills_fit.dispatch_guard.cf_daily_images() - 34)

    def test_cli_rejects_unknown_option(self):
        with self.assertRaises(SystemExit):
            stills_fit.main(["stills_fit.py", "p.json", "--force", "1"])


if __name__ == "__main__":
    unittest.main()
