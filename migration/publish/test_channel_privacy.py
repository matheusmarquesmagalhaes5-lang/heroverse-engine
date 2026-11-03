#!/usr/bin/env python3
"""Offline: channel-privacy.yml mode unschedule holds scheduled uploads (private, no publishAt) and never touches a
public video (owner, 2026-10-26: the scheduled prayer longs pilot-008 and pilot-014 stop; nothing is deleted)."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "migration" / "channel"))
import channel_privacy as cp  # noqa: E402


class FakeYouTube:
    def __init__(self, videos):
        self.videos = videos          # id -> status
        self.writes = []

    def __call__(self, tok, method, endpoint, params, body=None):
        if method == "GET":
            vid = params["id"]
            return {"items": [{"status": dict(self.videos[vid]), "snippet": {"channelId": cp.CHANNEL}}] if vid in self.videos else []}
        self.writes.append(body)
        self.videos[body["id"]] = {k: v for k, v in body["status"].items()}   # no publishAt sent: the schedule is gone
        return {"status": self.videos[body["id"]]}


def run(plan, videos):
    yt = FakeYouTube(videos)
    with tempfile.TemporaryDirectory() as t:
        p, out = Path(t) / "hold-plan.json", Path(t) / "receipt.json"
        p.write_text(json.dumps(plan))
        error, log = None, io.StringIO()
        with patch.object(cp, "token", return_value="fixture"), patch.object(cp, "call", yt), \
                contextlib.redirect_stdout(log):
            try:
                cp.unschedule(p, out)
            except SystemExit as e:
                error = str(e)
        run.receipt, run.log = json.loads(out.read_text()), log.getvalue()
        return run.receipt["changes"], yt, error


class Unschedule(unittest.TestCase):
    def test_scheduled_becomes_private_without_publish_at_and_public_is_left_alone(self):
        plan = {"channel_id": cp.CHANNEL, "to_unschedule": ["sched", "pub", "held"]}
        changes, yt, error = run(plan, {
            "sched": {"privacyStatus": "private", "publishAt": "2026-10-27T00:00:00Z"},
            "pub": {"privacyStatus": "public"},
            "held": {"privacyStatus": "private"}})
        self.assertIsNone(error)
        by = {c["video_id"]: c for c in changes}
        self.assertEqual(by["sched"]["result"], "UNSCHEDULED")
        self.assertEqual(by["sched"]["before"], {"privacy": "private", "publishAt": "2026-10-27T00:00:00Z"})  # the undo
        self.assertEqual(by["pub"]["result"], "SKIPPED_ALREADY_PUBLIC")
        self.assertEqual(by["held"]["result"], "ALREADY_UNSCHEDULED")
        self.assertEqual([w["id"] for w in yt.writes], ["sched"])          # one write; the public video untouched
        self.assertEqual(yt.writes[0]["status"]["privacyStatus"], "private")
        self.assertNotIn("publishAt", yt.writes[0]["status"])

    def test_a_held_video_already_public_is_reported_plainly_and_never_hidden(self):
        # review of #415: pilot-014's slot (26/10 10:00) may pass before the hold runs; the skip must be visible
        changes, yt, error = run({"channel_id": cp.CHANNEL, "to_unschedule": ["53Xysf9x46c", "sched"]}, {
            "53Xysf9x46c": {"privacyStatus": "public"},
            "sched": {"privacyStatus": "private", "publishAt": "2026-10-27T00:00:00Z"}})
        self.assertIsNone(error)                                              # a skip, not a failure
        self.assertEqual([w["id"] for w in yt.writes], ["sched"])             # never hidden here
        self.assertEqual(run.receipt["already_public_not_changed"], ["53Xysf9x46c"])
        self.assertIn("HELD_VIDEO_ALREADY_PUBLIC 53Xysf9x46c", run.log)
        self.assertIn("::warning::", run.log)                                 # shown on the Actions run page

    def test_a_missing_video_fails_the_run(self):
        changes, yt, error = run({"channel_id": cp.CHANNEL, "to_unschedule": ["gone"]}, {})
        self.assertEqual((changes[0]["result"], error, yt.writes), ("SKIPPED_NOT_OWNED_OR_MISSING", "UNSCHEDULE_INCOMPLETE", []))

    def test_the_hold_plan_lists_ledger_videos_it_describes(self):
        plan = json.loads((ROOT / "migration/channel/hold-plan.json").read_text())
        ledger = json.loads((ROOT / "migration/publish/ledger.json").read_text())["entries"]
        uploaded = {v.get("video_id") for v in ledger.values()}
        self.assertEqual(plan["channel_id"], cp.CHANNEL)
        self.assertTrue(plan["to_unschedule"])
        self.assertTrue(set(plan["to_unschedule"]) <= set(plan["videos"]))     # every held id is described
        self.assertTrue(set(plan["to_unschedule"]) <= uploaded)                # and is one of our uploads
        self.assertIn("previous", plan)                                         # older holds stay on record
        wf = (ROOT / ".github/workflows/channel-privacy.yml").read_text()
        self.assertIn("unschedule migration/channel/hold-plan.json", wf)


class Release(unittest.TestCase):
    """channel-privacy.yml mode release (owner 2026-11-03): a held, approved upload goes public; nothing else."""

    PLAN = {"channel_id": cp.CHANNEL, "releases": [{"video_id": "v1", "pilot": "pilot-017"}]}

    def run_release(self, status, hold=None, binding=(), ledger_vid=None):
        yt = FakeYouTube({"v1": status})
        sha = json.loads((ROOT / "migration/production/pilot-017/out/qa.json").read_text())["output_sha256"]
        ledger = {"entries": {f"pilot-017:{sha}": {"video_id": ledger_vid or "v1", "steps": {}}}}
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "plan.json").write_text(json.dumps(self.PLAN))
            (t / "hold.json").write_text(json.dumps(hold or {"to_unschedule": ["other"]}))
            (t / "ledger.json").write_text(json.dumps(ledger))
            error = None
            with patch.object(cp, "token", return_value="fixture"), patch.object(cp, "call", yt), \
                    patch.object(cp, "publication_binding", lambda pilot, commit=None: list(binding)), \
                    patch.object(cp, "LEDGER", t / "ledger.json"), patch.object(cp, "HOLD_PLAN", t / "hold.json"), \
                    patch.object(cp, "PUBLICATION_HOLD", t / "none"), contextlib.redirect_stdout(io.StringIO()):
                try:
                    cp.release(t / "plan.json", t / "receipt.json")
                except SystemExit as e:
                    error = str(e)
            return json.loads((t / "receipt.json").read_text())["changes"][0], yt, error, json.loads((t / "ledger.json").read_text())

    def test_a_held_private_upload_goes_public_with_read_back_and_a_ledger_entry(self):
        change, yt, error, ledger = self.run_release({"privacyStatus": "private", "uploadStatus": "uploaded",
                                                      "containsSyntheticMedia": True})
        self.assertIsNone(error)
        self.assertEqual(change["result"], "RELEASED")
        self.assertEqual(change["after"]["privacy"], "public")
        self.assertEqual(yt.writes[0]["status"]["privacyStatus"], "public")
        self.assertNotIn("publishAt", yt.writes[0]["status"])
        self.assertTrue(yt.writes[0]["status"]["containsSyntheticMedia"])           # the AI disclosure is kept
        self.assertEqual(next(iter(ledger["entries"].values()))["released"]["privacy"], "public")

    def test_already_public_is_not_written(self):
        change, yt, error, _ = self.run_release({"privacyStatus": "public", "uploadStatus": "processed"})
        self.assertEqual((change["result"], yt.writes, error), ("ALREADY_PUBLIC", [], None))

    def test_refused_while_still_in_the_hold_plan(self):
        change, yt, error, _ = self.run_release({"privacyStatus": "private", "uploadStatus": "uploaded"},
                                                hold={"to_unschedule": ["v1"]})
        self.assertIn("VIDEO_STILL_IN_HOLD_PLAN", change["problems"])
        self.assertEqual((yt.writes, error), ([], "RELEASE_INCOMPLETE"))

    def test_refused_when_the_ledger_upload_is_another_video(self):
        change, yt, error, _ = self.run_release({"privacyStatus": "private", "uploadStatus": "uploaded"}, ledger_vid="other")
        self.assertIn("VIDEO_NOT_THE_LEDGER_UPLOAD_OF_THIS_FILE", change["problems"])
        self.assertEqual(yt.writes, [])

    def test_refused_when_the_publication_evidence_no_longer_binds_the_file(self):
        change, yt, error, _ = self.run_release({"privacyStatus": "private", "uploadStatus": "uploaded"},
                                                binding=["PUBLICATION_BINDING_FAILED x"])
        self.assertEqual((change["result"], yt.writes), ("REFUSED", []))

    def test_a_video_still_uploading_is_refused(self):
        change, yt, error, _ = self.run_release({"privacyStatus": "private", "uploadStatus": "failed"})
        self.assertEqual((change["problems"], yt.writes), (["UPLOAD_NOT_USABLE"], []))

    def test_an_evidence_commit_is_checked_on_its_own_tree_and_only_if_the_evidence_is_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            sha = "a" * 40
            ev = Path(t) / sha
            pilot = ev / "migration/production/pilot-017"
            (ev / "migration/publish").mkdir(parents=True)
            shutil.copytree(ROOT / "migration/production/pilot-017", pilot)
            (ev / "migration/publish/publication_binding.py").write_text("import sys\nsys.exit(0)\n")
            with patch.dict(os.environ, {"EVIDENCE_DIR": t}):
                self.assertEqual(cp.publication_binding("pilot-017", sha), [])
                (pilot / "out/gate.json").write_text("{}")                      # evidence altered since the upload
                self.assertTrue(cp.publication_binding("pilot-017", sha)[0].startswith("EVIDENCE_CHANGED_SINCE_UPLOAD"))
                self.assertEqual(cp.publication_binding("pilot-017", "zz"), ["EVIDENCE_COMMIT_UNUSABLE"])

    def test_the_release_plan_and_workflow_are_wired(self):
        plan = json.loads((ROOT / "migration/channel/release-plan.json").read_text())
        hold = json.loads((ROOT / "migration/channel/hold-plan.json").read_text())
        self.assertEqual(plan["channel_id"], cp.CHANNEL)
        self.assertFalse({r["video_id"] for r in plan["releases"]} & set(hold["to_unschedule"]))   # released = not held
        self.assertIn("release migration/channel/release-plan.json", (ROOT / ".github/workflows/channel-privacy.yml").read_text())


if __name__ == "__main__":
    unittest.main()
