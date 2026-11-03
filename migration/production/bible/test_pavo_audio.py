#!/usr/bin/env python3
"""E287: the kept talking clip carries OUR request audio, never Pavo's re-synthesized track (real ffmpeg media)."""
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
import episode_build as eb  # noqa: E402
import pavo_audio  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def write_line(path, seconds=2.0, hz=300.0):
    """A stand-in for the request's Kokoro WAV: 44.1 kHz mono 16-bit, a modulated tone (not silence, not a pure sine)."""
    n = int(seconds * pavo_audio.RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(pavo_audio.RATE)
        w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * hz * i / pavo_audio.RATE)
                                                   * (0.6 + 0.4 * math.sin(2 * math.pi * 3 * i / pavo_audio.RATE))))
                               for i in range(n)))
    return path


def pavo_clip(path, seconds=3.0, hz=523.0):
    """What Pavo returns: a picture and ITS OWN track (another tone: re-timed, with a tail, other words)."""
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=d={seconds}:s=64x64:r=24",
                    "-f", "lavfi", "-i", f"sine=f={hz}:d={seconds}:r=48000", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg required")
class AudioIsOurs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.line = write_line(self.tmp / "line.wav")
        self.raw = pavo_clip(self.tmp / "raw.mp4")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_e287_the_kept_clip_carries_our_request_audio_never_pavos_track(self):
        # Pavo's own track is NOT the line (this is the E287 defect: words were judged on it) ...
        with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_OURS"):
            pavo_audio.assert_ours(self.raw, self.line)
        # ... the kept clip is Pavo's picture with our line over it: the audio digest IS the request's
        kept = pavo_audio.mux_ours(self.raw, self.line, self.tmp / "kept.mp4")
        proof = pavo_audio.assert_ours(kept, self.line)
        self.assertEqual(proof["route"], "ours")
        self.assertEqual(proof["samples"], 2 * pavo_audio.RATE)
        with wave.open(str(self.line), "rb") as w:
            import hashlib
            self.assertEqual(proof["sha256"], hashlib.sha256(w.readframes(w.getnframes())).hexdigest())
        self.assertEqual(pavo_audio.verify(kept, proof), proof)
        # the picture is Pavo's, copied: same codec, size and length, one audio stream and it is ours (PCM, bit-exact)
        probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,"
                                           "height:format=duration", "-of", "json", str(kept)], capture_output=True,
                                          text=True, check=True).stdout)
        kinds = [(s["codec_type"], s["codec_name"]) for s in probe["streams"]]
        self.assertEqual(kinds, [("video", "h264"), ("audio", "pcm_s16le")])
        self.assertAlmostEqual(float(probe["format"]["duration"]), 3.0, delta=0.1)   # padded to the picture, line is 2 s

    def test_a_changed_shorter_or_missing_audio_is_refused(self):
        kept = pavo_audio.mux_ours(self.raw, self.line, self.tmp / "kept.mp4")
        proof = pavo_audio.assert_ours(kept, self.line)
        other = write_line(self.tmp / "other.wav", hz=310.0)   # a different line (one word changed, in effect)
        with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_OURS"):
            pavo_audio.verify(pavo_audio.mux_ours(self.raw, other, self.tmp / "other.mp4"), proof)
        longer = dict(proof, samples=proof["samples"] * 2)   # the proof claims more audio than the clip carries as ours
        with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_OURS"):
            pavo_audio.verify(kept, longer)
        silent = self.tmp / "silent.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(self.raw), "-an", "-c:v", "copy", str(silent)],
                       check=True)
        with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_OURS"):
            pavo_audio.verify(silent, proof)
        for bad in (None, {}, dict(proof, route="pavo"), dict(proof, samples=0), dict(proof, sha256=None)):
            with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_OURS"):
                pavo_audio.verify(kept, bad)

    def test_only_the_requests_own_wav_format_is_a_digest(self):
        odd = self.tmp / "odd.wav"
        with wave.open(str(odd), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(b"\0" * 400)
        with self.assertRaisesRegex(SystemExit, "AUDIO_LINE_FORMAT"):
            pavo_audio.proof_of(odd)

    def test_the_engine_keeps_pavos_picture_with_our_audio_and_records_the_proof(self):
        """episode_build.shot_runner's attempt() on real media: the clip it returns (the one that is checked, kept,
        hashed and uploaded) has our line; the request's WAV is the layout's own file."""
        import test_episode_build as t
        saved = (eb.pavo_audio.mux_ours, eb.pavo_audio.assert_ours, eb.clip_flags, eb.lipsync_flags, eb.face_flags)
        t.real_ours()
        work = Path(tempfile.mkdtemp(dir=eb.REPO, prefix=".test-ours-"))
        try:
            plan = t.dialogue_plan()
            layout = t.layout_for(plan, [2.4, 3.0, 2.5, 3.1])
            (work / "refs.json").write_text(json.dumps({"keeper": ["k.jpg"], "eve": ["eve.jpg"]}))
            wav = eb.REPO / layout["speakers"]["s-eve"]["wav"]
            wav.parent.mkdir(parents=True, exist_ok=True)
            self.addCleanup(shutil.rmtree, eb.REPO / ".episode" / "x", True)
            write_line(wav)
            seen = {}
            eb.clip_flags = lambda path, aspect=None: []
            eb.face_flags = lambda py, model, clip: ([], {"faces": {"frames_sampled": 4, "faces_found": 0}})

            def lips(py, model, clip, line):    # lipsync_check's input: the KEPT clip against OUR line
                seen["clip"], seen["line"] = Path(clip), Path(line)
                pavo_audio.assert_ours(clip, line)   # what lipsync_check would hear is our line
                return [], {"audio": {"corr": 1.0, "lag_ms": 0}, "mouth": {"face_frames": 1.0, "sync": {}}}
            eb.lipsync_flags = lips
            shot = next(s for s in plan["shots"] if s["id"] == "s-eve")
            refs = {"keeper": ["k.jpg"], "eve": ["eve.jpg"]}
            client = t.FakeClient([{"conversation_id": "1", "status": "submitted"}], {"1": [t.done("1")]})
            req, attempt, check, raw, final = eb.shot_runner(
                shot, plan["shots"].index(shot), plan, layout, refs, work, client,
                lambda url, dst: shutil.copyfile(self.raw, dst), "py", "model", lambda s: None)
            record, path = attempt(1)
            flags, measures = check(path)
            self.assertEqual(flags, [])
            self.assertEqual(Path(path), final)
            self.assertEqual(seen["line"], wav)
            self.assertEqual(record["audio"], pavo_audio.proof_of(wav))
            pavo_audio.verify(final, record["audio"])
            with self.assertRaises(SystemExit):   # Pavo's raw track is not ours
                pavo_audio.verify(raw, record["audio"])
        finally:
            eb.pavo_audio.mux_ours, eb.pavo_audio.assert_ours, eb.clip_flags, eb.lipsync_flags, eb.face_flags = saved
            shutil.rmtree(work)


class SecondGenerationOnlyForAVisualDefect(unittest.TestCase):
    def test_a_words_flag_never_buys_a_generation_and_a_visual_defect_does(self):
        self.assertEqual((eb.TALK_ATTEMPTS, eb.TALK_ATTEMPTS_MAX), (1, 2))
        for flag in ("FACE_NOT_FOUND", "MOUTH_NOT_IN_SYNC", "MOUTH_TALKING", "NO_VIDEO", "CLIP_ASPECT_MISMATCH"):
            self.assertTrue(eb.visual_defect([flag]), flag)
        self.assertFalse(eb.visual_defect([]))
        self.assertFalse(eb.visual_defect(["AUDIO_NOT_OUR_LINE"]))
        calls = []
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)

        def attempt(n, video=True):
            calls.append(n)
            if not video:
                return {"generation": n}, None
            (tmp / f"c{n}.mp4").write_bytes(b"v")
            return {"generation": n}, tmp / f"c{n}.mp4"
        for flags, spent in ((["AUDIO_NOT_OUR_LINE"], 1), (["FACE_NOT_FOUND"], 2)):
            calls.clear()
            try:
                eb.make_shot("k-a", attempt, lambda p, f=flags: (f, None), attempts=eb.TALK_ATTEMPTS_MAX,
                             regenerate=eb.visual_defect)
            except eb.ShotFailed:
                pass
            self.assertEqual(len(calls), spent, flags)   # a words flag stops at one generation, a visual defect at two
        # no video at all reads as NO_VIDEO (a visual defect): the second generation is allowed, never a third
        calls.clear()
        with self.assertRaises(eb.ShotFailed):
            eb.make_shot("k-a", lambda n: attempt(n, video=False), lambda p: ([], None), attempts=eb.TALK_ATTEMPTS_MAX,
                         regenerate=eb.visual_defect)
        self.assertEqual(calls, [1, 2])


class ApprovalNeedsTheProof(unittest.TestCase):
    def test_a_record_made_under_ours_refuses_a_clip_without_the_proof_and_a_words_flag(self):
        proof = {"route": "ours", "sha256": "a" * 64, "samples": 88200, "seconds": 2.0}
        entry = {"request": {"audio": {"speaker": "keeper", "voice": {}, "words": ["a"]}}}
        ours = {"pavo_audio": "ours"}
        self.assertIsNone(eb.ours_audio_problem(ours, entry, {"audio": proof, "flags": []}))
        self.assertIn("no pavo_audio proof", eb.ours_audio_problem(ours, entry, {"flags": []}))
        self.assertIn("no pavo_audio proof", eb.ours_audio_problem(ours, entry, {"audio": dict(proof, route="pavo")}))
        self.assertIn("no pavo_audio proof", eb.ours_audio_problem(ours, entry, {"audio": dict(proof, sha256="x")}))
        self.assertIn("words flag", eb.ours_audio_problem(ours, entry, {"audio": proof, "flags": ["AUDIO_NOT_OUR_LINE"]}))
        # a legacy record (Pavo's track kept) and a native-speech request keep their own rules
        self.assertIsNone(eb.ours_audio_problem({}, entry, {"flags": ["AUDIO_NOT_OUR_LINE"]}))
        native = {"request": {"audio": {"route": "pavo_native", "words": ["a"]}}}
        self.assertIsNone(eb.ours_audio_problem(ours, native, {"flags": []}))


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg required")
class RemuxOurAudioOverAStoredClip(unittest.TestCase):
    """E288: a clip stored before E287 (Pavo's track kept) becomes a probe clip with OUR request audio, nothing generated."""
    def setUp(self):
        from unittest import mock
        import test_episode_build as t   # its import stubs the mux: the real one is what this class tests
        t.real_ours()
        self.addCleanup(t.stub_ours)
        self.tmp = Path(tempfile.mkdtemp(dir=eb.REPO, prefix=".test-remux-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.raw = pavo_clip(self.tmp / "raw.mp4")
        self.sha = eb.sha256(self.raw)
        self.src = self.tmp / "src"
        self.src.mkdir()
        shutil.copyfile(self.raw, self.src / eb.shot_asset_name("ep", "k-a", self.sha))
        self.shots = self.tmp / "shots"
        self.shots.mkdir()
        self.old_request = "r" * 64
        (self.shots / "111111.json").write_text(json.dumps({"episode": "ep", "shots": {"k-a": {
            "request_sha256": self.old_request, "clip_seconds": 6, "clips": [
                {"asset": eb.shot_asset_name("ep", "k-a", self.sha), "clip_sha256": self.sha, "uploaded": True, "flags": []}]}}}))
        self.line = write_line(self.tmp / "line.wav")
        self.work = self.tmp / "work"
        self.work.mkdir()
        (self.work / "layout.json").write_text("{}")
        (self.work / "refs.json").write_text("{}")
        self.plan = {"episode": "ep", "shots": [{"id": "k-a", "kind": "keeper"}]}
        self.mock = mock
        self.flags = []
        self.seen = {}

        def runner(*a, **k):
            def check(path):
                self.seen["clip"] = Path(path)
                pavo_audio.assert_ours(path, self.line)   # the strict checks hear OUR line
                return list(self.flags), {"lipsync": {"audio": {"corr": 1.0}, "mouth": {"face_frames": 1.0, "sync": {"offset": -1}}}}
            return None, None, check, None, None
        self.patches = [
            mock.patch.object(eb, "request_problems", lambda *a: []),
            mock.patch.object(eb, "request", lambda *a, **k: {"audios": ["x"], "sound": False}),
            mock.patch.object(eb, "native_speech", lambda *a: False),
            mock.patch.object(eb.plan_check, "talking", lambda shot: True),
            mock.patch.object(eb, "talk_record", lambda layout, shot: {"wav": str(self.line.relative_to(eb.REPO))}),
            mock.patch.object(eb, "request_identity", lambda *a, **k: (self.old_request, {"audio": {"words": ["a"]}})),
            mock.patch.object(eb, "shot_runner", runner)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def remux(self, prefix=None):
        return eb.remux_step(self.plan, self.work, "py", "model", self.tmp / "out", [("k-a", prefix or self.sha[:8])], self.src,
                             sheet=lambda video, dst: Path(dst).write_bytes(b"jpg"), shots_dir=self.shots)

    def test_the_stored_picture_gets_our_line_and_a_probe_record_approve_shot_accepts(self):
        record = self.remux()
        clip = record["shots"]["k-a"]["clips"][0]
        self.assertEqual((record["pavo_audio"], clip["remux_of"], clip["flags"]), ("ours", self.sha, []))
        kept = self.tmp / "out" / clip["asset"]
        self.assertEqual(clip["clip_sha256"], eb.sha256(kept))
        self.assertNotEqual(clip["clip_sha256"], self.sha)   # the audio changed, so the clip is a new content-hash asset
        pavo_audio.verify(kept, clip["audio"])                # the proof binds the kept bytes to our WAV
        self.assertEqual(clip["audio"], pavo_audio.proof_of(self.line))
        with self.assertRaises(SystemExit):
            pavo_audio.verify(self.raw, clip["audio"])        # the stored clip's own track is not ours
        self.assertEqual(self.seen["clip"].name, "k-a.mp4")
        self.assertIsNone(eb.ours_audio_problem(record, record["shots"]["k-a"], clip))
        self.assertEqual(eb.probe_assets(self.tmp / "out", "ep"), [clip["asset"]])   # the record job's own name check

    def test_a_failed_check_is_recorded_not_hidden_and_a_changed_request_is_refused(self):
        self.flags = ["MOUTH_NOT_IN_SYNC"]
        record = self.remux()
        self.assertEqual(record["shots"]["k-a"]["clips"][0]["soft_flags"], ["MOUTH_NOT_IN_SYNC"])
        self.old_request = "z" * 64   # the plan now sends another request than the stored clip's
        with self.patch_identity():
            with self.assertRaisesRegex(SystemExit, "SHOT_REQUEST_CHANGED k-a"):
                self.remux()

    def patch_identity(self):
        return self.mock.patch.object(eb, "request_identity", lambda *a, **k: ("n" * 64, {}))

    def test_inputs_and_sources_are_exact(self):
        self.assertEqual(eb.remux_items("k-r1:dae7a9, k-r2:7f043f"), [("k-r1", "dae7a9"), ("k-r2", "7f043f")])
        for bad in ("", "k-r1", "k-r1:xyz", "k-r1:abc", "k-r1:dae7a9,k-r1:dae7a9", "K:dae7a9"):
            with self.assertRaisesRegex(SystemExit, "REMUX_SHOTS_REFUSED"):
                eb.remux_items(bad)
        with self.assertRaisesRegex(SystemExit, "REMUX_SOURCE_CLIP"):
            eb.remux_source("ep", "k-a", "ffffff", self.shots)
        with self.assertRaisesRegex(SystemExit, "REMUX_SOURCE_CLIP"):
            eb.remux_source("ep", "k-b", self.sha[:8], self.shots)
        self.assertEqual(eb.remux_source("ep", "k-a", self.sha[:8], self.shots)[1], self.sha)
        (self.src / eb.shot_asset_name("ep", "k-a", self.sha)).write_bytes(b"other")   # the asset is not the recorded bytes
        with self.assertRaisesRegex(SystemExit, "REMUX_STORED_CLIP_MISSING"):
            self.remux()


if __name__ == "__main__":
    unittest.main()
