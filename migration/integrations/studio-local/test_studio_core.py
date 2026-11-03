#!/usr/bin/env python3
"""Offline tests of the Studio runner's queue/receipt rules and of the cloud mapping (no browser, no network)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2] if len(HERE.parents) > 2 else HERE
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "migration/channel"))
import studio_core as core  # noqa: E402

try:
    import related_map as rm  # noqa: E402
except ImportError:      # on the PC only the runner's own files exist
    rm = None

A, B, C = "AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"
NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def job(v=A, t=B, **kw):
    return {"video_id": v, "action": "related_video", "target_video_id": t, "reason": "x", **kw}


class QueueTests(unittest.TestCase):
    def test_parse_rejects_bad_jobs(self):
        good, bad = core.parse_queue({"jobs": [job(), job(v="short"), job(v=A, t=A),
                                               {**job(), "action": "pin"}, "x"]})
        self.assertEqual(len(good), 1)
        self.assertEqual([p for _, p in bad], ["BAD_VIDEO_ID", "SELF_TARGET", "UNKNOWN_ACTION", "NOT_AN_OBJECT"])

    def test_no_jobs_list_raises(self):
        with self.assertRaises(ValueError):
            core.parse_queue({"jobs": None})

    def test_one_target_per_video_newest_wins(self):
        good, _ = core.parse_queue({"jobs": [job(t=B), job(t=C)]})
        self.assertEqual([j["target_video_id"] for j in good], [C])

    def test_pending_skips_done_and_already_but_retries_failed(self):
        jobs = [job(A, B), job(C, B), job("DDDDDDDDDDD", B)]
        rec = [{"results": [core.result(jobs[0], "DONE", at=NOW), core.result(jobs[1], "FAILED", "x", at=NOW)]},
               {"results": [core.result(jobs[2], "ALREADY", at=NOW)]}]
        self.assertEqual(core.pending(jobs, rec), [jobs[1]])

    def test_done_for_another_target_does_not_hide_a_changed_job(self):
        rec = [{"results": [core.result(job(A, B), "DONE", at=NOW)]}]
        self.assertEqual(core.pending([job(A, C)], rec), [job(A, C)])

    def test_cap_of_30_even_if_more_requested(self):
        jobs = [job(f"{i:011d}", B) for i in range(50)]
        self.assertEqual(len(core.pending(jobs, [], limit=99)), 30)
        self.assertEqual(len(core.pending(jobs, [], limit=5)), 5)
        self.assertEqual(core.pending(jobs, [], limit=0), [])


class ReceiptTests(unittest.TestCase):
    def test_result_shape_and_unknown_outcome(self):
        r = core.result(job(), "FAILED", "y" * 500, at=NOW)
        self.assertEqual(r["at"], "2026-11-03T12:00:00Z")
        self.assertEqual(len(r["detail"]), 300)
        with self.assertRaises(ValueError):
            core.result(job(), "MAYBE")

    def test_merge_appends_to_the_days_receipt(self):
        first = core.merge_receipt(None, [core.result(job(), "DONE", at=NOW)], at=NOW)
        second = core.merge_receipt(first, [core.result(job(C, B), "ALREADY", at=NOW)], at=NOW)
        self.assertEqual(len(second["results"]), 2)
        self.assertEqual(second["version"], "studio-receipt-v1")
        json.loads(core.dump(second))

    def test_receipt_path_by_date(self):
        self.assertEqual(core.receipt_path(NOW), "migration/evidence/studio/2026-11-03.json")

    def test_receipt_holds_no_cookie_like_fields(self):
        doc = core.merge_receipt(None, [core.result(job(), "DONE", at=NOW)], at=NOW)
        self.assertEqual(set(doc["results"][0]), {"video_id", "action", "target_video_id", "outcome", "detail", "at"})


class MatchTests(unittest.TestCase):
    def test_id_in_link(self):
        self.assertTrue(core.text_matches("", B, None, ["https://www.youtube.com/watch?v=" + B]))

    def test_title_match_normalised(self):
        self.assertTrue(core.text_matches("Related video\n  Noah  and the FLOOD", B, "noah and the flood"))

    def test_no_match(self):
        self.assertFalse(core.text_matches("Select video", B, "Noah", ["/channel/x"]))
        self.assertFalse(core.text_matches("anything", B))


@unittest.skipIf(rm is None, "cloud mapping not on this machine")
class MappingTests(unittest.TestCase):
    L, S1, S2, CUT, OLD, COMP, X = ("LLLLLLLLLLL", "SSSSSSSSSS1", "SSSSSSSSSS2", "CUTCUTCUT01", "OLDOLDOLD01",
                                    "COMPCOMP001", "SSSSSSSSSS3")

    def entries(self):
        e = lambda vid, at, **kw: {"video_id": vid, "uploaded_at": at, **kw}  # noqa: E731
        return {"pilot-001:aa": e(self.L, "2026-10-01"), "pilot-002:aa": e("LONG2LONG02", "2026-10-02"),
                "pilot-003:aa": e(self.COMP, "2026-10-03"),
                "short:pilot-001:bb": e(self.OLD, "2026-10-04", long_video_id=self.L),
                "bible:g-01-short:cc": e(self.S1, "2026-10-05"), "bible:g-02-short:cc": e(self.S2, "2026-10-06"),
                "bible:g-03-short:cc": e(self.X, "2026-10-06"),
                "bible:x-cut:dd": e(self.CUT, "2026-10-07")}

    def build(self, public, arcs=None, done=None):
        arcs = arcs or {"arcs": [{"shorts": ["g-01-short"], "long": {"pilot": "pilot-001"}}]}
        return rm.build(self.entries(), arcs, {"x-cut": "pilot-001"}, [("pilot-003", ["g-02-short"])],
                        public, already_done=done or {})

    def test_rules(self):
        pub = {v: None for v in (self.L, "LONG2LONG02", self.COMP, self.OLD, self.S1, self.S2, self.CUT, self.X)}
        jobs, skipped = self.build(pub)
        m = {j["video_id"]: j["target_video_id"] for j in jobs}
        self.assertEqual(m[self.OLD], self.L)                 # old short -> its long
        self.assertEqual(m[self.CUT], self.L)                 # cut -> source long
        self.assertEqual(m[self.S1], self.L)                  # arc long
        self.assertEqual(m[self.S2], self.COMP)               # compilation chapter
        self.assertEqual(m[self.X], self.COMP)                # no arc long -> newest public long (the compilation)
        self.assertEqual(skipped, [])
        self.assertNotIn(self.L, m)                           # longs get no job
        self.assertTrue(all(j["action"] == "related_video" and j["reason"] for j in jobs))

    def test_non_public_video_and_target_skipped(self):
        pub = {v: None for v in (self.L, self.S1)}
        jobs, skipped = self.build(pub)
        self.assertEqual([j["video_id"] for j in jobs], [self.S1])
        self.assertIn("NOT_PUBLIC", [s["why"] for s in skipped])
        pub2 = {v: None for v in (self.S1, self.S2)}          # no public long at all
        jobs2, skipped2 = self.build(pub2)
        self.assertEqual(jobs2, [])
        self.assertTrue([s for s in skipped2 if s["why"] != "NOT_PUBLIC"])
        self.assertTrue(all(s["why"] in ("NO_TARGET", "TARGET_NOT_PUBLIC", "NOT_PUBLIC") for s in skipped2))

    def test_compilation_not_public_falls_back_to_arc_or_newest(self):
        pub = {v: None for v in (self.L, "LONG2LONG02", self.S2)}
        jobs, _ = self.build(pub)
        self.assertEqual(jobs[0]["target_video_id"], "LONG2LONG02")      # newest public long

    def test_already_done_skipped(self):
        pub = {v: None for v in (self.L, self.CUT)}
        jobs, skipped = self.build(pub, done={self.CUT: self.L})
        self.assertEqual(jobs, [])
        self.assertEqual([s["why"] for s in skipped if s["video_id"] == self.CUT], ["ALREADY_DONE by hand"])

    def test_target_title_carried(self):
        jobs, _ = self.build({self.L: "The Long", self.OLD: "o"})
        self.assertEqual(jobs[0]["target_title"], "The Long")

    def test_real_repository_state(self):
        entries = rm.read_json(rm.LEDGER)["entries"]
        vids = rm.classify(entries)
        pub = {v: None for v, r in vids.items()}
        jobs, skipped = rm.build(entries, rm.read_json(rm.ARCS), rm.load_cut_sources(rm.CUTS),
                                 rm.load_compilations(rm.COMPILATIONS), pub)
        keys = {j["video_id"] for j in jobs}
        self.assertFalse(keys & set(rm.ALREADY_DONE))
        for j in jobs:
            self.assertIsNone(core.job_problem(j))
        cut = [j for j in jobs if j["reason"].startswith("cut")]
        # the three first flood cuts are done by hand; every later cut gets a job to its source long (E280: the cuts
        # published after the queue was written made this assertion red on main)
        self.assertFalse({j["video_id"] for j in cut} & set(rm.ALREADY_DONE))
        for j in cut:
            self.assertEqual(j["target_video_id"], "1m-NUJhkdMY")
            self.assertTrue(j["reason"].endswith("cut of its source long"))

    def test_committed_queue_is_valid(self):
        doc = rm.read_json(rm.OUT)
        if doc is None:
            self.skipTest("no queue yet")
        good, bad = core.parse_queue(doc)
        self.assertEqual(bad, [])
        self.assertEqual(len(good), len(doc["jobs"]))
        self.assertFalse({j["video_id"] for j in good} & set(rm.ALREADY_DONE))

    def test_cli_requires_one_public_source(self):
        with self.assertRaises(SystemExit):
            rm.main(["build"])
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / "p.json"
            pf.write_text(json.dumps(["ku2MTQKmXaU", "1m-NUJhkdMY"]))
            out = Path(d) / "o.json"
            with patch("builtins.print"):
                self.assertEqual(rm.main(["build", "--public-file", str(pf), "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["jobs"][0]["target_video_id"], "1m-NUJhkdMY")


class RunnerImportTests(unittest.TestCase):
    def test_logged_in_uses_cookie_names_only_with_a_list(self):
        try:
            import runner  # noqa: E402
        except Exception as e:  # noqa: BLE001
            self.skipTest(f"runner import: {e}")
        calls = []

        class Ctx:
            def cookies(self, urls):      # Playwright takes ONE argument: a url or a list of urls
                calls.append(urls)
                return [{"name": "SAPISID", "value": "secret"}]
        self.assertTrue(runner.logged_in(Ctx()))
        self.assertIsInstance(calls[0], list)

    def test_dry_run_prints_pending_without_browser(self):
        try:
            import runner  # noqa: E402
        except Exception as e:  # noqa: BLE001
            self.skipTest(f"runner import: {e}")
        queue = {"jobs": [job(A, B), job(C, B)]}
        done = [{"results": [core.result(job(A, B), "DONE", at=NOW)]}]
        with patch.object(runner, "fetch_queue_and_receipts", return_value=(queue, done)), \
                patch.object(runner, "local_ledger", return_value={"results": []}), \
                patch.object(runner, "log"), patch("builtins.print") as pr:
            self.assertEqual(runner.main(["run", "--dry-run"]), 0)
        self.assertIn(f"WOULD related_video {C} -> {B}", " ".join(str(c.args[0]) for c in pr.call_args_list))


if __name__ == "__main__":
    unittest.main()
