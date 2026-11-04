#!/usr/bin/env python3
"""Offline checks of the audience retention / traffic-source report (YouTube Analytics API; no network, no credential)."""
from datetime import datetime, timezone
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audience_report as ar  # noqa: E402

NOW = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)
VIDEOS = [{"id": "LONG1", "title": "Babel", "short": False, "published": "2026-11-04T10:00", "views": 40},
          {"id": "SHORT1", "title": "Flood", "short": True, "published": "2026-11-01T10:00", "views": 900},
          {"id": "SHORT2", "title": "Ark", "short": True, "published": "2026-11-02T10:00", "views": 500}]
CURVE = [[round(i / 100, 2), 1.0 - i / 200, 1.0] for i in range(1, 101)]
SRC_LONG = [["SHORTS", 20, 40.0, 100.0], ["RELATED_VIDEO", 10, 30.0, 180.0], ["YT_SEARCH", 5, 10.0, 120.0],
            ["SUBSCRIBER", 3, 9.0, 200.0], ["NO_LINK_OTHER", 2, 1.0, 20.0]]
SRC_SHORT = [["SHORTS", 800, 100.0, 15.0], ["SUBSCRIBER", 100, 10.0, 20.0]]


class FakeQuery:
    def __init__(self, fail=None, empty=False):
        self.calls, self.log, self.fail, self.empty = 0, [], fail, empty

    def rows(self, start, end, metrics, dimensions, filters, sort=None, limit=None):
        self.calls += 1
        self.log.append((dimensions, filters, metrics))
        if self.fail:
            raise self.fail
        if self.empty:
            return []
        if dimensions == "elapsedVideoTimeRatio":
            return CURVE
        if dimensions == "insightTrafficSourceType":
            return SRC_LONG if "LONG1" in filters else SRC_SHORT
        if "RELATED_VIDEO" in filters:
            return [["SHORT1", 7, 20.0], ["OTHER", 3, 10.0]]
        return [["noah's ark", 4, 9.0]]


class Shapes(unittest.TestCase):
    def test_retention_curve_is_compact_with_checkpoints(self):
        r = ar.retention(CURVE)
        self.assertEqual(len(r["curve"]), ar.CURVE_POINTS)
        self.assertEqual((r["at_25"], r["at_50"], r["at_75"], r["at_end"]), (0.875, 0.75, 0.625, 0.5))
        self.assertEqual(r["relative_performance_mean"], 1.0)
        self.assertIsNone(ar.retention([]))

    def test_sources_group_shorts_feed_related_browse_search_and_keep_raw(self):
        s = ar.sources(SRC_LONG)
        g = s["grouped"]
        self.assertEqual((s["views"], g["shorts_feed"]["views"], g["related"]["views"], g["browse"]["views"],
                          g["search"]["views"], g["other"]["views"]), (40, 20, 10, 3, 5, 2))
        self.assertEqual(g["shorts_feed"]["share"], 0.5)
        self.assertIn("NO_LINK_OTHER", s["raw"])
        self.assertEqual(ar.sources([])["grouped"]["shorts_feed"]["share"], None)

    def test_referrers_resolve_our_own_shorts(self):
        r = ar.referrers([["SHORT1", 7, 1], ["X", 3, 1]], {"SHORT1"})
        self.assertEqual((r["views"], r["from_our_shorts"]), (10, 7))
        self.assertTrue(r["top"][0]["our_short"] and not r["top"][1]["our_short"])


class Run(unittest.TestCase):
    def go(self, q, state=None):
        return ar.run(lambda: q, state if state is not None else {}, VIDEOS, NOW)

    def test_a_run_reads_retention_and_sources_for_every_video_and_the_long_detail(self):
        q = FakeQuery()
        s = self.go(q)
        self.assertEqual(s["status"], "OK")
        self.assertEqual(set(s["per_video"]), {"LONG1", "SHORT1", "SHORT2"})
        dims = [d for d, _, _ in q.log]
        self.assertEqual(dims.count("elapsedVideoTimeRatio"), 3)
        self.assertEqual(dims.count("insightTrafficSourceDetail"), 2)   # related + search, the long only
        self.assertTrue(all(f.startswith("video==") for _, f, _ in q.log))
        f = s["funnel"]
        self.assertEqual((f["long_views"], f["from_shorts_feed"], f["from_our_shorts_related"]), (40, 20, 7))
        self.assertEqual(f["share_from_shorts"], round(27 / 40, 3))
        self.assertEqual(f["shorts_with_retention"], 2)
        self.assertEqual(s["range"], ["2026-08-07", "2026-11-05"])
        self.assertEqual(s["per_video"]["LONG1"]["search_terms"][0]["term"], "noah's ark")

    def test_no_rows_is_no_data_not_a_failure(self):
        s = self.go(FakeQuery(empty=True))
        self.assertEqual(s["status"], "NO_DATA")
        self.assertNotIn("reason", s)

    def test_scope_or_network_failure_is_unknown_with_a_secret_free_reason_and_keeps_history(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", None,
                                     io.BytesIO(json.dumps({"error": {"errors": [{"reason": "insufficientPermissions"}]}}).encode()))
        old = {"per_video": {"LONG1": {"kind": "long", "title": "Babel", "sources": ar.sources(SRC_LONG), "retention": None}}}
        s = self.go(FakeQuery(fail=err), old)
        self.assertEqual(s["status"], "UNKNOWN")
        self.assertIn("SCOPE_MISSING", s["reason"])
        self.assertIn("LONG1", s["per_video"])
        self.assertNotIn("Bearer", json.dumps(s))

    def test_a_400_for_one_video_is_noted_and_the_others_go_on(self):
        class Q(FakeQuery):
            def rows(self, start, end, metrics, dimensions, filters, sort=None, limit=None):
                if "SHORT2" in filters:
                    self.calls += 1
                    raise urllib.error.HTTPError("u", 400, "Bad", None, io.BytesIO(b"{}"))
                return super().rows(start, end, metrics, dimensions, filters, sort, limit)
        s = self.go(Q())
        self.assertEqual(s["status"], "OK")
        self.assertNotIn("SHORT2", s["per_video"])
        self.assertTrue(any("SHORT2" in p for p in s["problems"]))

    def test_the_call_cap_bounds_the_run(self):
        many = [{"id": f"S{n:03d}", "short": True, "title": "x", "published": f"2026-10-{n % 28 + 1:02d}"} for n in range(100)]
        q = FakeQuery()
        s = ar.run(lambda: q, {}, many, NOW)
        self.assertLessEqual(q.calls, ar.MAX_CALLS)
        self.assertLessEqual(len(s["per_video"]), ar.MAX_SHORTS)

    def test_the_time_cap_stops_the_run(self):
        ticks = iter([0, 0, 500, 500, 500, 500, 500])
        q = FakeQuery()
        s = ar.run(lambda: q, {}, VIDEOS, NOW, clock=lambda: next(ticks))
        self.assertTrue(any("cap" in p for p in s["problems"]))


class Files(unittest.TestCase):
    def test_main_writes_json_and_appends_a_section_and_cli_never_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "latest.md").write_text("# report\n")
            (out / "20261105.json").write_text(json.dumps({"video_index": {
                "LONG1": {"title": "Babel", "short": False, "published": "2026-11-04T10:00", "views": 40},
                "SHORT1": {"title": "Flood", "short": True, "published": "2026-11-01T10:00", "views": 900}}}))
            with contextlib.redirect_stdout(io.StringIO()):
                s = ar.main(tmp, None, NOW, lambda: FakeQuery())
            self.assertEqual(s["status"], "OK")
            md = (out / "latest.md").read_text()
            self.assertIn(ar.HEADING, md)
            self.assertIn("Short -> long: 40 long views, 20 from the Shorts feed, 7 from our own Shorts", md)
            self.assertEqual(json.loads((out / "audience.json").read_text())["version"], "audience-v1")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ar.cli([tmp], main=lambda *a: 1 / 0), 0)
                self.assertEqual(ar.cli(["--step-failed", "124", tmp]), 0)
            self.assertIn("STEP_FAILED exit 124 (timed out)", (out / "latest.md").read_text())
            self.assertEqual(json.loads((out / "audience.json").read_text())["version"], "audience-v1")   # history kept

    def test_the_host_is_pinned_and_the_token_is_never_in_the_url(self):
        seen = []

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req, timeout):
            seen.append(req)
            return Resp(b'{"rows": [["SHORTS", 1, 2, 3]]}')
        q = ar.Query("TOKEN", opener)
        self.assertEqual(q.rows("2026-08-01", "2026-11-01", ar.SOURCE_METRICS, "insightTrafficSourceType", "video==V"),
                         [["SHORTS", 1, 2, 3]])
        self.assertTrue(seen[0].full_url.startswith(ar.ANALYTICS + "?"))
        self.assertNotIn("TOKEN", seen[0].full_url)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer TOKEN")


class Workflow(unittest.TestCase):
    def test_wired_after_the_goal_report_with_the_secret_only_in_env_and_never_failing(self):
        wf = (Path(__file__).resolve().parents[2] / ".github/workflows/goal-report.yml").read_text()
        step = wf.split("- name: Audience retention and traffic sources")[1].split("- name:")[0]
        self.assertLess(wf.index("goal_report.py"), wf.index("audience_report.py"))
        self.assertIn("HERO_YT_AUTHORIZED_USER_JSON: ${{ secrets.HERO_YT_AUTHORIZED_USER_JSON }}", step)
        run = step.split("run:")[1]
        self.assertNotIn("secrets.", run)
        self.assertIn("timeout-minutes: 3", step)
        self.assertIn('timeout 150 "$RUNNER_TEMP/venv/bin/python" -I -B migration/mining/audience_report.py '
                      "migration/evidence/daily-report migration/publish/ledger.json", run)
        self.assertIn('[ "$rc" = 0 ] || python3 -I -B migration/mining/audience_report.py --step-failed "$rc" '
                      "migration/evidence/daily-report", run)
        self.assertNotIn("continue-on-error", wf)
        self.assertLess(wf.index("audience_report.py"), wf.index("- name: Record"))


if __name__ == "__main__":
    unittest.main()
