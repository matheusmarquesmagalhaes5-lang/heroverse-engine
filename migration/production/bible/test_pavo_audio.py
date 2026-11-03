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
import unittest.mock
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
import episode_build as eb  # noqa: E402
import pavo_audio  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
# E287's tests below run on the explicit "ours" route (owner 2026-11-03 made "pavo" the default); the default and the
# Pavo route are tested in the classes at the end of this file, which set it back.
pavo_audio.DEFAULT = pavo_audio.OURS


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
        for bad in (None, {}, dict(proof, route="theirs"), dict(proof, samples=0), dict(proof, sha256=None)):
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
        self.assertIn("no pavo_audio proof", eb.ours_audio_problem(ours, entry, {"audio": dict(proof, route="theirs")}))
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


class RouteAndLoudness(unittest.TestCase):
    """Owner 2026-11-03: "pavo" (Pavo's own audio, the clip in full) is the default; "ours" is an explicit option."""
    def test_the_default_is_pavo_and_ours_is_only_explicit_or_recorded(self):
        with unittest.mock.patch.object(pavo_audio, "DEFAULT", pavo_audio.PAVO):
            self.assertEqual(pavo_audio.route_of({}), "pavo")
            self.assertEqual(pavo_audio.route_of(None), "pavo")
            self.assertEqual(pavo_audio.route_of({"pavo_audio": "ours"}), "ours")
            self.assertEqual(pavo_audio.route_of({}, {"route": "ours"}), "ours")      # an E287 approval keeps its route
            self.assertEqual(pavo_audio.route_of({"pavo_audio": "pavo"}, {"route": "ours"}), "pavo")   # explicit wins
            self.assertEqual(pavo_audio.route_of({}, {"route": "pavo"}), "pavo")
            self.assertEqual(pavo_audio.route_of({}, "ours"), "ours")                  # a compilation key's remux route
            with self.assertRaisesRegex(SystemExit, "PAVO_AUDIO_ROUTE_INVALID"):
                pavo_audio.route_of({"pavo_audio": "theirs"})
        self.assertEqual(pavo_audio.DEFAULT, "ours")   # this file's fixtures; the shipped default is asserted above
        self.assertEqual(pavo_audio.ROUTES, ("pavo", "ours"))
        shipped = subprocess.run([sys.executable, "-I", "-c", "import sys;sys.path.insert(0,%r);import pavo_audio;"
                                  "print(pavo_audio.DEFAULT)" % str(Path(__file__).resolve().parent)],
                                 capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(shipped, "pavo")

    def test_match_gain_lands_within_one_db_and_refuses_a_peak_the_limiter_cannot_hide(self):
        got = pavo_audio.match_gain(-22.0, -16.0, -12.0)
        self.assertEqual((got["gain_db"], got["matched_lufs"], got["limited"]), (6.0, -16.0, False))
        got = pavo_audio.match_gain(-22.0, -16.0, -6.0)   # +6 dB puts the peak at 0 dBTP: the limiter holds the ceiling
        self.assertTrue(got["limited"])
        self.assertLessEqual(abs(got["matched_lufs"] - -16.0), pavo_audio.LOUDNESS_TOL)
        with self.assertRaisesRegex(SystemExit, "LOUDNESS_NOT_MATCHED"):
            pavo_audio.match_gain(-30.0, -16.0, -3.0)
        for bad in (None, float("nan"), True):
            with self.assertRaisesRegex(SystemExit, "LOUDNESS_NOT_MATCHED"):
                pavo_audio.match_gain(bad, -16.0, -3.0)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg required")
    def test_the_filter_brings_a_real_pavo_track_to_the_narration_within_one_db_under_the_ceiling(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        clip = pavo_clip(tmp / "pavo.mp4", seconds=4.0)
        line = write_line(tmp / "line.wav", seconds=4.0)
        proof = pavo_audio.pavo_proof(clip, line)
        self.assertEqual(proof["route"], "pavo")
        gain = pavo_audio.match_gain(proof["lufs"], proof["narration_lufs"], proof["true_peak_db"])
        out = tmp / "matched.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(clip), "-vn", "-af",
                        pavo_audio.match_filter(gain["gain_db"]), str(out)], check=True)
        after = pavo_audio.measure(out)
        self.assertLessEqual(abs(after["lufs"] - proof["narration_lufs"]), pavo_audio.LOUDNESS_TOL)
        self.assertLessEqual(after["true_peak_db"], pavo_audio.TRUE_PEAK_MAX + 0.3)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg required")
    def test_the_proof_binds_pavos_own_track_and_refuses_our_line_labelled_as_pavos(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        clip = pavo_clip(tmp / "pavo.mp4")
        line = write_line(tmp / "line.wav")
        proof = pavo_audio.pavo_proof(clip, line)
        self.assertEqual(pavo_audio.verify_any(clip, proof), proof)
        import test_episode_build as t   # its import stubs mux_ours: the real one is wanted here
        ours = t.REAL_MUX(clip, line, tmp / "ours.mp4")
        with self.assertRaisesRegex(SystemExit, "PAVO_AUDIO_IS_OURS"):
            pavo_audio.pavo_proof(ours, line)
        with self.assertRaisesRegex(SystemExit, "AUDIO_NOT_PAVO"):
            pavo_audio.verify_any(ours, proof)
        self.assertEqual(pavo_audio.verify_any(ours, pavo_audio.proof_of(line))["route"], "ours")


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg required")
class PavoRouteInTheEngine(unittest.TestCase):
    def setUp(self):
        import test_episode_build as t
        self.t = t
        self.tmp = Path(tempfile.mkdtemp(dir=eb.REPO, prefix=".test-pavo-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(shutil.rmtree, eb.REPO / ".episode" / "x", True)
        self.raw = pavo_clip(self.tmp / "raw.mp4", seconds=3.0)
        self.saved = (eb.clip_flags, eb.lipsync_flags, eb.face_flags)
        self.addCleanup(lambda: setattr(eb, "clip_flags", self.saved[0]) or setattr(eb, "lipsync_flags", self.saved[1])
                        or setattr(eb, "face_flags", self.saved[2]))

    def runner(self, shot_patch=None):
        t = self.t
        plan = t.dialogue_plan()
        layout = t.layout_for(plan, [2.4, 3.0, 2.5, 3.1])
        wav = eb.REPO / layout["speakers"]["s-eve"]["wav"]
        wav.parent.mkdir(parents=True, exist_ok=True)
        write_line(wav)
        shot = next(s for s in plan["shots"] if s["id"] == "s-eve")
        shot.update(shot_patch or {})
        refs = {"keeper": ["k.jpg"], "eve": ["eve.jpg"]}
        (self.tmp / "refs.json").write_text(json.dumps(refs))
        client = t.FakeClient([{"conversation_id": "1", "status": "submitted"}], {"1": [t.done("1")]})
        out = eb.shot_runner(shot, plan["shots"].index(shot), plan, layout, refs, self.tmp, client,
                             lambda url, dst: shutil.copyfile(self.raw, dst), "py", "model", lambda s: None)
        return out, wav

    def test_the_default_keeps_the_pavo_clip_whole_with_its_own_track_and_never_refuses_the_words(self):
        seen = {}
        eb.clip_flags = lambda path, aspect=None: []

        def lips(py, model, clip, line):   # the mouth is judged against the track the clip CARRIES, not our line
            seen["line"] = Path(line)
            pavo_audio.pavo_verify(clip, seen["proof"])
            return ["AUDIO_NOT_OUR_LINE", "MOUTH_NOT_IN_SYNC"], {"audio": {"corr": 0.2}, "mouth": {"sync": {}}}
        eb.lipsync_flags = lips
        with unittest.mock.patch.object(pavo_audio, "DEFAULT", pavo_audio.PAVO):
            (req, attempt, check, raw, final), wav = self.runner()
            record, path = attempt(1)
            seen["proof"] = record["audio"]
            flags, _ = check(path)
        self.assertEqual(eb.sha256(final), eb.sha256(raw))                  # the clip as Pavo made it: in full, no trim, no mux
        self.assertEqual(record["audio"]["route"], "pavo")
        self.assertNotEqual(seen["line"], wav)                              # judged on its own track
        self.assertEqual(flags, ["MOUTH_NOT_IN_SYNC"])                      # words are not a flag; the visual gates stay
        self.assertFalse(eb.visual_defect([]) )
        self.assertEqual(record["audio"]["narration_lufs"], pavo_audio.measure(wav)["lufs"])
        self.assertIsNone(eb.ours_audio_problem({"pavo_audio": "pavo"}, {"request": {"audio": {"words": ["a"]}}},
                                                {"audio": record["audio"], "flags": flags}))

    def test_an_explicit_ours_shot_still_gets_our_line_over_pavos_picture(self):
        eb.clip_flags = lambda path, aspect=None: []
        eb.lipsync_flags = lambda py, model, clip, line: ([], {"audio": {}, "mouth": {"sync": {}}})
        eb.face_flags = eb.lipsync_flags
        self.t.real_ours()
        self.addCleanup(self.t.stub_ours)
        with unittest.mock.patch.object(pavo_audio, "DEFAULT", pavo_audio.PAVO):
            (req, attempt, check, raw, final), wav = self.runner({"pavo_audio": "ours"})
            record, path = attempt(1)
        self.assertEqual(record["audio"], pavo_audio.proof_of(wav))
        pavo_audio.verify(final, record["audio"])


class ReviewNotesAndTheKjvWarning(unittest.TestCase):
    LINE = "In the beginning God created the heaven and the earth"

    def test_another_word_is_a_note_and_only_a_kjv_quotation_warns(self):
        same = eb.pavo_review_notes(self.LINE, self.LINE.lower() + ".", True)
        self.assertEqual((same["words_differ"], same.get("warnings")), (False, None))
        other = eb.pavo_review_notes(self.LINE, "In the beginning the Lord created the heaven and the earth", False)
        self.assertEqual((other["words_differ"], other.get("warnings")), (True, None))      # a note, no warning, no refusal
        self.assertEqual(other["asr_text"], "In the beginning the Lord created the heaven and the earth")
        kjv = eb.pavo_review_notes(self.LINE, "In the beginning the Lord created the heaven and the earth", True)
        self.assertEqual(kjv["warnings"], ["WARN_KJV_WORDS"])
        self.assertEqual(eb.pavo_review_notes(self.LINE, None, True)["warnings"], ["WARN_KJV_WORDS"])   # not heard at all

    def test_a_scripture_item_marks_the_shot_as_a_kjv_quotation(self):
        import test_episode_build as t
        plan = t.dialogue_plan()
        self.assertFalse(eb.kjv_quote(plan, "s-eve"))
        self.assertFalse(eb.kjv_quote({"shots": []}, "nope"))
        items, carried = eb.plan_check.sequence(plan)
        index = next(i for i, s in enumerate(plan["shots"]) if s["id"] == "s-eve")
        with unittest.mock.patch.object(eb.plan_check, "sequence", lambda p: (
                [dict(it, kind="scripture") if k in carried[index] else it for k, it in enumerate(items)], carried)):
            self.assertTrue(eb.kjv_quote(plan, "s-eve"))


class ApprovalOnThePavoRoute(unittest.TestCase):
    """approve-shot on a clip that keeps Pavo's own audio: no words refusal, the whole clip is the speech span, the one gain
    matches the narration, the ASR text and any KJV warning are review notes."""
    def setUp(self):
        self.records = eb.REPO / "migration" / "evidence" / "shots"
        self.records.mkdir(parents=True, exist_ok=True)
        self.path = self.records / f".test-{os.getpid()}-pavo.json"
        self.shots = Path(tempfile.mkdtemp(dir=self.records.parent, prefix=".test-shots-"))
        self.addCleanup(shutil.rmtree, self.shots, True)
        self.addCleanup(self.path.unlink, True)
        self.sha = "c" * 64
        self.proof = {"route": "pavo", "sha256": "d" * 64, "samples": 6 * 44100, "seconds": 6.0, "lufs": -22.0,
                      "true_peak_db": -12.0, "narration_lufs": -16.0}

    def record(self, flags=("MOUTH_NOT_IN_SYNC",), kjv=False, audio=None):
        asset = eb.shot_asset_name("ep", "s-eve", self.sha)
        self.path.write_text(json.dumps({"episode": "ep", "run_id": "40500000777", "pavo_audio": "pavo", "shots": {"s-eve": {
            "request_sha256": "r" * 64, "clip_seconds": 6, "kjv_quote": kjv,
            "request": {"audio": {"words": ["in", "the", "beginning"]}}, "clips": [{
                "asset": asset, "clip_sha256": self.sha, "uploaded": True, "flags": list(flags),
                "audio": audio or self.proof,
                "media": {"version": "clip-media-v1", "clip_sha256": self.sha, "video_seconds": 6.04, "audio_seconds": 6.0}}]}}}))
        return asset

    def approve(self, asset, **kw):
        return eb.approve_shot(self.path, "s-eve", asset, "9.6", "heard and saw it", shots_dir=self.shots,
                               reviewer="claude-session-reviewer", **kw)

    def test_the_whole_clip_with_its_own_audio_is_approved_with_one_gain_and_no_words_gate(self):
        approved = self.approve(self.record())
        self.assertEqual(approved["audio"], self.proof)
        speech = approved["speech"]
        self.assertEqual((speech["route"], speech["onset"], speech["end"], speech["gain_db"], speech["flags"]),
                         ("pavo", 0.0, 6.0, 6.0, []))                      # the whole clip, +6 dB to -16 LUFS
        self.assertEqual(speech["tp_db"], pavo_audio.TRUE_PEAK_MAX)
        self.assertNotIn("trim_out_s", approved)                            # in full unless the approval says otherwise
        self.assertEqual(approved["review_notes"]["asr_text"], None)
        self.assertNotIn("warnings", approved["review_notes"])
        self.assertEqual(eb.speech_record_flags(approved, self.sha), [])

    def test_a_kjv_quotation_without_a_heard_text_warns_but_is_never_refused(self):
        approved = self.approve(self.record(kjv=True))
        self.assertEqual(approved["review_notes"]["warnings"], ["WARN_KJV_WORDS"])
        side = self.records / "ep" / "speech" / f"{self.sha}.json"
        self.addCleanup(shutil.rmtree, self.records / "ep", True)
        side.parent.mkdir(parents=True, exist_ok=True)
        notes = eb.pavo_review_notes("in the beginning", "in the end", True)
        side.write_text(json.dumps({"review_notes": notes}))
        again = self.approve(self.record(kjv=True))
        self.assertEqual(again["review_notes"]["asr_text"], "in the end")
        self.assertEqual(again["review_notes"]["warnings"], ["WARN_KJV_WORDS"])

    def test_a_trim_is_applied_only_when_the_approval_sets_it_and_a_hard_defect_still_bars(self):
        approved = self.approve(self.record(), trim_out_s=5.0)
        self.assertEqual((approved["trim_out_s"], approved["speech"]["end"]), (5.0, 5.0))
        with self.assertRaisesRegex(SystemExit, "SHOT_CHECKS_FAILED s-eve FACE_NOT_FOUND"):
            self.approve(self.record(flags=("FACE_NOT_FOUND",)))
        with self.assertRaisesRegex(SystemExit, "SHOT_AUDIO_NOT_OURS.*LOUDNESS_NOT_MATCHED"):
            self.approve(self.record(audio=dict(self.proof, lufs=-40.0, true_peak_db=-3.0)))


class NativeSpansForPavoApprovals(unittest.TestCase):
    def test_a_talking_shot_with_a_pavo_approval_is_laid_out_at_its_clip_length_on_any_plan(self):
        import test_episode_build as t
        plan = t.dialogue_plan()
        sha = "e" * 64
        media = {"version": "clip-media-v1", "clip_sha256": sha, "video_seconds": 7.04, "audio_seconds": 7.0}
        speech = {"route": "pavo", "clip_sha256": sha, "onset": 0.0, "end": 7.0, "gain_db": 2.0, "flags": []}
        approvals = {"s-eve": {"clip_sha256": sha, "media": media, "speech": speech, "audio": {"route": "pavo"}}}
        spans = eb.native_spans(plan, approvals)
        self.assertEqual({k: v[1:] for k, v in spans.items()}, {"s-eve": (0.0, 7.0)})
        self.assertEqual(eb.native_spans(plan, approvals, pavo=False), {})
        ours = {"s-eve": dict(approvals["s-eve"], speech=dict(speech, route="ours"))}
        self.assertEqual(eb.native_spans(plan, ours), {})
        self.assertEqual(eb.native_spans(plan, {}), {})
        place = eb.pavo_native.placements(plan, {"lines": [{"start": 1.5}] * 8}, {"s-eve": ([0], 0.0, 7.0)},
                                          {"s-eve": __file__}, {"s-eve": {"speech": dict(speech, tp_db=-1.5)}})[0]
        self.assertEqual((place["gain_db"], place["tp_db"], place["seconds"]), (2.0, -1.5, 7.0))
        self.assertIn("alimiter=limit=0.8414", eb.pavo_native.premix_filter([place], 20.0))


if __name__ == "__main__":
    unittest.main()
