#!/usr/bin/env python3
"""Keeper lip-sync glue (keeper_lipsync.py): pins, the source and result gates, the pinned fetch. No torch, no network."""
import hashlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keeper_lipsync as k  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


class Pins(unittest.TestCase):
    def test_every_weight_is_pinned_by_sha256_and_lands_inside_the_checkout(self):
        self.assertRegex(k.MUSETALK_COMMIT, r"^[0-9a-f]{40}$")
        for name, (url, sha, size) in k.PINS.items():
            self.assertRegex(sha, r"^[0-9a-f]{64}$", name)
            self.assertTrue(url.startswith("https://"), name)
            self.assertGreater(size, 0)
            dest = k.dest_of(name)
            self.assertNotIn("..", dest)
            self.assertFalse(dest.startswith("/"))
        for need in ("musetalkV15/unet.pth", "sd-vae/diffusion_pytorch_model.bin", "whisper/pytorch_model.bin",
                     "dwpose/dw-ll_ucoco_384.pth", "face-parse-bisent/79999_iter.pth", "s3fd.pth"):
            self.assertIn(need, k.PINS)

    def test_hugging_face_weights_are_read_at_a_commit_never_at_main(self):
        for name, (url, _, _) in k.PINS.items():
            if "huggingface.co" in url:
                self.assertRegex(url, r"/resolve/[0-9a-f]{40}/", name)

    def test_the_workflow_reads_the_code_pins_and_runs_no_secret(self):
        wf = (ROOT / ".github/workflows/lipsync.yml").read_text()
        self.assertIn("keeper_lipsync.py", wf)
        self.assertIn("MUSETALK_COMMIT", wf)
        self.assertNotIn("secrets.", wf)
        self.assertIn("permissions:\n  contents: read", wf)
        for action in re.findall(r"uses: (\S+)", wf):
            self.assertRegex(action, r"@[0-9a-f]{40}$", action)


class Fetch(unittest.TestCase):
    def test_a_weight_with_the_wrong_hash_is_deleted_and_refused(self):
        saved = dict(k.PINS)
        try:
            k.PINS.clear()
            k.PINS["x/w.bin"] = ("https://example.invalid/w", hashlib.sha256(b"good").hexdigest(), 4)
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(SystemExit) as e:
                    k.fetch(d, opener=lambda url, timeout: io.BytesIO(b"evil"))
                self.assertIn("LIPSYNC_WEIGHT_SHA_MISMATCH", str(e.exception))
                self.assertFalse((Path(d) / "models/x/w.bin").exists())
                self.assertEqual(k.fetch(d, opener=lambda url, timeout: io.BytesIO(b"good")), ["x/w.bin"])
                self.assertEqual((Path(d) / "models/x/w.bin").read_bytes(), b"good")
        finally:
            k.PINS.clear()
            k.PINS.update(saved)


class Gates(unittest.TestCase):
    def test_processed_span_is_the_line_plus_a_tail_and_never_beyond_the_clip(self):
        self.assertEqual(k.span_s(6.55, 8.0), 7.05)
        self.assertEqual(k.span_s(7.8, 8.0), 8.0)
        self.assertEqual(k.span_s(3.0, 8.0, 0.0), 3.0)

    def test_a_source_that_already_talks_or_hides_its_face_is_flagged(self):
        self.assertEqual(k.source_flags({"flags": []}), [])
        self.assertEqual(k.source_flags({"flags": ["MOUTH_NOT_CLOSED"]}), [])   # an acting mouth may breathe (warning, not a flag)
        self.assertEqual(k.source_flags({"flags": ["MOUTH_TALKING"]}), ["LIPSYNC_SOURCE_MOUTH_TALKING"])
        self.assertEqual(k.source_flags({"flags": ["FACE_NOT_FOUND"]}), ["LIPSYNC_SOURCE_FACE_NOT_FOUND"])

    def test_sync_face_artifact_and_audio_flags_all_stay_blocking(self):
        ok = {"flags": []}
        self.assertEqual(k.result_flags(ok, ok, True), [])
        self.assertEqual(k.result_flags({"flags": ["MOUTH_NOT_IN_SYNC"]}, ok, True), ["MOUTH_NOT_IN_SYNC"])
        self.assertEqual(k.result_flags({"flags": ["FACE_NOT_FOUND"]}, ok, True), ["FACE_NOT_FOUND"])
        self.assertEqual(k.result_flags(ok, {"flags": ["LETTERBOX_BARS"]}, True), ["CLIP_LETTERBOX_BARS"])
        self.assertEqual(k.result_flags(ok, ok, False), ["AUDIO_NOT_OURS"])
        self.assertEqual(k.result_flags({"flags": ["AUDIO_NOT_OUR_LINE"]}, ok, True), ["AUDIO_NOT_OUR_LINE"])   # never dropped

    def test_face_boxes_are_measured_sparsely_and_interpolated_per_frame(self):
        self.assertEqual(k.sample_indices(20, 8), [0, 8, 16, 19])
        self.assertEqual(k.sample_indices(17, 8), [0, 8, 16])
        self.assertEqual(k.sample_indices(1, 8), [0])
        out = k.interpolate([0, 4, 8], [(10, 10, 110, 110), (20, 20, 120, 120), (20, 20, 120, 120)], 10)
        self.assertEqual(len(out), 10)
        self.assertEqual(out[0], (10, 10, 110, 110))
        self.assertEqual(out[2], (15, 15, 115, 115))
        self.assertEqual(out[9], (20, 20, 120, 120))                     # held after the last measured frame
        # a frame with no face is skipped, never a zero box
        out = k.interpolate([0, 4, 8], [(0, 0, 100, 100), None, (8, 8, 108, 108)], 9)
        self.assertEqual(out[4], (4, 4, 104, 104))
        with self.assertRaises(SystemExit):
            k.interpolate([0, 4], [None, (0.0, 0.0, 0.0, 0.0)], 5)

    def test_a_picture_shorter_than_the_spoken_line_is_a_flag_but_a_silent_tail_is_not(self):
        self.assertEqual(k.line_cut_flags(6.55, 7.04), [])
        self.assertEqual(k.line_cut_flags(7.05, 7.04), [])            # within a frame's rounding
        self.assertEqual(k.line_cut_flags(7.2, 7.04), ["LIPSYNC_LINE_CUT"])

    def test_the_thresholds_are_the_unchanged_syncnet_gate(self):
        import lipsync_check as lc
        self.assertEqual((lc.SYNC_OFFSET_CENTRE, lc.SYNC_OFFSET_TOL, lc.SYNC_CONF_MIN), (-1.5, 1.5, 2.7))
        self.assertEqual(k.FACE_FRAMES_MIN, lc.FACE_FRAMES_MIN)


def report(**over):
    """A `finish` report as lipsync.yml writes it, with the source clip and the Kokoro line proof (2026-11-05 measures)."""
    r = {"model": "musetalk-1.5", "commit": k.MUSETALK_COMMIT, "final": "keeper-lipsync.mp4", "final_sha256": "c" * 64,
         "source_clip_sha256": "a" * 64, "line": {"route": "ours", "sha256": "b" * 64, "samples": 288855, "seconds": 6.55},
         "lipsync": {"audio": {"corr": 1.0, "lag_ms": 0}, "mouth": {"face_frames": 1.0, "sync": {"offset": 0, "conf": 3.128}},
                     "flags": []},
         "clip_check": {"flags": []}, "audio_ours": True, "flags": []}
    r.update(over)
    return r


class Proof(unittest.TestCase):
    """Owner 2026-11-05: AI lip-sync need not be human-perfect; "good enough to publish" is the existing gate: SyncNet
    confidence >= 2.7 in the calibrated offset, the face in >= 80 % of the frames, our Kokoro audio bit-exact. Clearly
    broken output still fails, and a proof qualifies only the clip, the line and the silent source it names."""
    LINE = {"route": "ours", "sha256": "b" * 64, "samples": 288855, "seconds": 6.55}

    def problems(self, rep=None, clip="c" * 64, line=LINE, sources=("a" * 64,)):
        return k.proof_problems(k.proof_of(rep or report(), "42024334433"), clip, line, sources)

    def test_a_lip_sync_that_passes_the_existing_gates_qualifies_its_own_clip(self):
        self.assertEqual(self.problems(), [])
        proof = k.proof_of(report(), "42024334433")
        self.assertEqual((proof["clip_sha256"], proof["source_clip_sha256"], proof["run_id"]),
                         ("c" * 64, "a" * 64, "42024334433"))
        self.assertEqual(proof["sync"]["conf"], 3.128)

    def test_a_thin_margin_is_good_enough_but_under_the_floor_is_not(self):
        mouth = lambda conf, offset=0, face=1.0: {"mouth": {"face_frames": face, "sync": {"offset": offset, "conf": conf}},
                                                  "flags": []}
        self.assertEqual(self.problems(report(lipsync=mouth(2.7))), [])              # the floor itself passes
        self.assertTrue(self.problems(report(lipsync=mouth(2.69))))                  # under it: refused
        self.assertTrue(self.problems(report(lipsync=mouth(3.1, offset=-13))))       # out of sync
        self.assertTrue(self.problems(report(lipsync=mouth(3.1, face=0.79))))        # face lost
        self.assertTrue(self.problems(report(lipsync={"mouth": {"face_frames": 1.0, "sync": None}, "flags": []})))

    def test_clearly_broken_output_and_foreign_audio_still_fail(self):
        self.assertTrue(self.problems(report(flags=["LIPSYNC_LINE_CUT"])))
        self.assertTrue(self.problems(report(clip_check={"flags": ["BLACK_START"]})))
        self.assertTrue(self.problems(report(audio_ours=False)))
        self.assertTrue(self.problems(report(model="wav2lip")))

    def test_the_proof_is_bound_to_its_clip_line_and_silent_source(self):
        self.assertIn("the proof is for another clip (clip sha256)", self.problems(clip="d" * 64))
        other = dict(self.LINE, sha256="e" * 64)
        self.assertTrue(any("not the Kokoro line" in p for p in self.problems(line=other)))
        self.assertTrue(any("silent source" in p for p in self.problems(sources=("f" * 64,))))
        self.assertTrue(self.problems(report(source_clip_sha256="c" * 64)))         # its own output is no source
        self.assertTrue(self.problems(report(line=None)))

    def test_the_first_probe_reports_carry_no_source_or_line_proof_and_cannot_be_used(self):
        import json
        old = json.loads((ROOT / "migration/evidence/lipsync/20261105/close-run42024334433/report.json").read_text())
        found = k.proof_problems(k.proof_of(old), old["final_sha256"])
        self.assertTrue(any("source" in p for p in found) and any("Kokoro line" in p for p in found), found)
        self.assertEqual(k.proof_problems(k.proof_of(dict(old, source_clip_sha256="a" * 64, line=self.LINE)),
                                          old["final_sha256"]), [])               # its measures themselves pass


if __name__ == "__main__":
    unittest.main()
