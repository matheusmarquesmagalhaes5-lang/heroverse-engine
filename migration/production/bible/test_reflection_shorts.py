"""The Keeper reflection split-screen Short (reflection_shorts.py): the spec checker (duration window, a published
approved long, the reflection's length and voice, no speech of the clip cut), the render (two 1080x960 halves, the
Keeper's still in motion, the voice over the ducked clip, captions, -14 LUFS) on a fixture long, and the
unchanged downstream: publish_episode's track rules (the standard 9.5 review floor stays), native-review and arc-links."""
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
import buzzy_long as bl  # noqa: E402
import native_review as nr  # noqa: E402
import publish_episode as pe  # noqa: E402
import reflection_shorts as rs  # noqa: E402
import test_long_first as tlf  # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None
try:
    import cv2  # noqa: F401
    import numpy  # noqa: F401
    MOTION = True
except ImportError:
    MOTION = False

VIDEO_ID = "AbCdEfGhIjK"
STILL = "genesis-long-test-k-insight"
VERSE = ("Genesis 7:4 (KJV)", "For yet seven days, and I will cause it to rain upon the earth forty days and forty nights; "
         "and every living substance that I have made will I destroy from off the face of the earth.")
REFLECTION = ("Seven days of warning, and he spent them building. Notice what the story leaves out: no argument, no "
              "plea. Obedience here is quiet, slow work done before anyone can see why. I find that harder than "
              "any miracle.")


def spec_of(**kw):
    spec = {"version": rs.VERSION, "track": rs.TRACK, "layout": rs.LAYOUT, "id": "genesis-long-test-reflection-1",
            "long": "genesis-long-test", "pilot": "pilot-099",
            "report": "migration/evidence/episodes/genesis-long-test/report-1.json",
            "clip": {"start": 0.2, "end": 22.2, "x": 0.5, "audio": "duck"},
            "reflection": {"text": REFLECTION}, "keeper_image": STILL,
            "title": "What Noah never said #shorts",
            "description": "The Keeper on Genesis 7 (public domain), AI visuals. The full story: the long video.",
            "tags": ["noah", "bible"], "first_comment": f"The whole story, in the long video: https://youtu.be/{VIDEO_ID}"}
    spec.update(kw)
    return spec


def make_root(t, spec=None, published=True, still_status="APPROVED", shot="k-insight"):
    root, base, _ = tlf.cut_root(t, [])
    (root / "migration/production/bible/reflections").mkdir(parents=True, exist_ok=True)
    (root / "migration/publish").mkdir(parents=True, exist_ok=True)
    ledger = {"entries": {f"pilot-099:{tlf.SHA}": {"video_id": VIDEO_ID}} if published else {}}
    (root / "migration/publish/ledger.json").write_text(json.dumps(ledger))
    stills = root / rs.STILLS
    stills.mkdir(parents=True, exist_ok=True)
    img = stills / f"{STILL}.jpg"
    if FFMPEG:
        tlf.ff("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=1", "-frames:v", "1", img)
    else:
        img.write_bytes(b"x")
    (stills / f"{STILL}.json").write_text(json.dumps({
        "id": STILL, "episode": "genesis-long-test", "shot": shot, "status": still_status, "prompt": "The narrator. Warm and grave.",
        "repo_path": f"migration/production/bible/stills/{STILL}.jpg", "sha256": cl.sha256(img), "size": [640, 360],
        "approved": {"score": 9.5, "by": "Claude's still review"}}))
    spec = spec or spec_of()
    path = root / f"migration/production/bible/reflections/{spec['id'].replace('-reflection-', '-')}.json"
    path.write_text(json.dumps(spec))
    return root, spec, path


def codes(result):
    return [p.split()[0] for p in result["problems"]]


class Check(unittest.TestCase):
    def test_a_good_reflection_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path = make_root(t)
            got = rs.check(spec, root, spec_path=str(path.relative_to(root)))
            self.assertEqual(got["problems"], [])
            self.assertEqual((got["reflection"]["first"], got["reflection"]["last"]), (0, 3))
            self.assertEqual((got["reflection"]["words"], got["reflection"]["long_video_id"]), (38, VIDEO_ID))
            self.assertAlmostEqual(got["reflection"]["seconds"], 22.0)
            spec["clip"].update(audio="mute")
            spec["verse"] = {"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 5.0}
            self.assertEqual(rs.check(spec, root)["problems"], [])

    def test_the_clip_is_in_the_window_and_never_cut_in_speech(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            for clip, code in (({"start": 1.0, "end": 22.2}, "CLIP_STARTS_INSIDE_SPEECH"),
                               ({"start": 0.2, "end": 20.0}, "CLIP_ENDS_INSIDE_SPEECH"),
                               ({"start": 4.2, "end": 22.2}, "CLIP_LENGTH"),
                               ({"start": 0.2, "end": 200.0}, "CLIP_RANGE"),
                               ({"start": 0.2, "end": 22.2, "x": 1.5}, "CLIP_X"),
                               ({"start": 0.2, "end": 22.2, "audio": "loud"}, "CLIP_AUDIO")):
                self.assertIn(code, codes(rs.check(dict(spec, clip=clip), root)), clip)
            # a clip over 40 s is refused even on sentence edges
            rep = json.loads((root / spec["report"]).read_text())
            rep["composed"]["seconds"] = 70.0
            rep["composed"]["sentences"].append(dict(rep["composed"]["sentences"][-1], start=24.35, end=69.0, text="Then the rain came."))
            (root / spec["report"]).write_text(json.dumps(rep))
            long_clip = dict(spec, clip={"start": 0.2, "end": 69.5})
            self.assertIn("CLIP_LENGTH", codes(rs.check(long_clip, root)))
            self.assertEqual(rs.SECONDS, (20.0, 40.0))

    def test_the_clip_comes_from_an_approved_published_long(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, published=False)
            self.assertIn("LONG_NOT_PUBLISHED", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            self.assertIn("PILOT", codes(rs.check(dict(spec, pilot="pilot-098"), root)))
            plan = json.loads((root / "migration/production/bible/plans/genesis-long-test.json").read_text())
            plan["track"] = "buzzy"
            (root / "migration/production/bible/plans/genesis-long-test.json").write_text(json.dumps(plan))
            self.assertIn("LONG_NOT_LONG_FIRST", codes(rs.check(spec, root)))
            self.assertIn("SPEC_PATH", codes(rs.check(spec, root, spec_path="migration/production/bible/reflections/other-1.json")))
            self.assertIn("SPEC_VERSION", codes(rs.check(dict(spec, track="buzzy-cut"), root)))

    def test_the_reflection_length_voice_and_words(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            too_short = "The Keeper waits. He is patient."
            too_many = " ".join(["Obedience is slow work."] * 25)
            sixty = " ".join(["Obedience is slow, quiet work done before the rain."] * 7)   # 63 words: 22 s cannot hold it
            for text, code in ((too_short, "REFLECTION_LENGTH"), (too_many, "REFLECTION_LENGTH"),
                               (sixty, "REFLECTION_TOO_LONG_FOR_CLIP"), (REFLECTION[:-1], "REFLECTION_NOT_A_SENTENCE"),
                               (REFLECTION + " Shocking.", "REFLECTION_BANNED_WORDS"), ("", "REFLECTION_MISSING")):
                self.assertIn(code, codes(rs.check(dict(spec, reflection={"text": text}), root)), text[:30])
            eighty = " ".join(["word"] * 79) + "."
            self.assertEqual(rs.WORDS, (20, 80))
            self.assertIn("REFLECTION_TOO_LONG_FOR_CLIP", codes(rs.check(dict(spec, reflection={"text": eighty}), root)))
            # the voice fills the clip: 20 words in a 22 s clip leave dead air
            self.assertIn("REFLECTION_TOO_SHORT_FOR_CLIP", codes(rs.check(dict(spec, reflection={"text": " ".join(["Slow work, done well."] * 5)}), root)))

    def test_the_verse_is_quoted_only_exactly_and_only_if_shown(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            wrong = dict(spec, verse={"reference": VERSE[0], "text": VERSE[1].replace("seven", "six"), "start": 0.5, "end": 5.0})
            self.assertIn("VERSE_NOT_KJV", codes(rs.check(wrong, root)))
            late = dict(spec, verse={"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 30.0})
            self.assertIn("VERSE_INVALID", codes(rs.check(late, root)))
            self.assertIn("VERSE_INVALID", codes(rs.check(dict(spec, verse={"reference": VERSE[0]}), root)))

    def test_the_keeper_image_is_an_approved_keeper_still(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, still_status="DRAFT")
            self.assertIn("KEEPER_IMAGE_NOT_APPROVED", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, shot="s-c1-dawn")
            self.assertIn("KEEPER_IMAGE_NOT_THE_KEEPER", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            self.assertIn("KEEPER_IMAGE_UNKNOWN", codes(rs.check(dict(spec, keeper_image="no-such-still"), root)))
            (root / rs.STILLS / f"{STILL}.jpg").write_bytes(b"another file")
            self.assertIn("KEEPER_IMAGE_SHA256_MISMATCH", codes(rs.check(spec, root)))

    def test_the_package_points_to_the_long(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            for kw, code in ((dict(first_comment="Watch the long video."), "FIRST_COMMENT_NOT_TO_THE_LONG"),
                             (dict(description="The Keeper on Genesis 7 (public domain KJV), AI visuals."), "DESCRIPTION_NOT_TO_THE_LONG"),
                             (dict(description="The full story, the long video."), "DISCLOSURE_MISSING"),
                             (dict(title=""), "TITLE_MISSING"), (dict(title="t" * 101), "TITLE_LENGTH"),
                             (dict(motion="no_such_move"), "MOTION_UNKNOWN")):
                self.assertIn(code, codes(rs.check(dict(spec, **kw), root)), kw)

    def test_voice_script_uses_the_pinned_keeper_voice(self):
        got = rs.voice_script(spec_of())
        self.assertEqual(got["voice"]["voice_id"], "am_michael")   # episode_build.VOICE: the long's Keeper
        self.assertEqual([s["text"] for s in got["segments"]], [REFLECTION])


def voice_fixture(work, speech=15.0):
    """What pilot_render.py voice writes (voice.wav, timeline.json), as a tone: the same shape, no Kokoro."""
    work.mkdir(parents=True, exist_ok=True)
    total = rs.LEAD_IN + speech + 0.3
    tlf.ff("-f", "lavfi", "-i", "sine=frequency=180:sample_rate=24000", "-t", f"{total:.2f}", "-af", "volume=-18dB", "-c:a", "pcm_s16le",
           work / "voice.wav")
    sentences, t0 = [], rs.LEAD_IN
    for i, s in enumerate(rs.speech_sentences(REFLECTION)):
        span = speech * len(s) / len(REFLECTION)
        sentences.append({"segment": "r00", "text": s, "start": round(t0, 3), "end": round(t0 + span - 0.18, 3)})
        t0 += span
    (work / "timeline.json").write_text(json.dumps({"segments": [{"id": "r00", "start": rs.LEAD_IN, "end": t0}], "sentences": sentences,
                                                    "voice_seconds": round(total, 3), "sample_rate": 24000, "voice_id": "am_michael", "speed": 1.0}))


@unittest.skipUnless(FFMPEG and MOTION, "ffmpeg, numpy and OpenCV")
class Render(unittest.TestCase):
    def prepare(self, t, spec=None):
        root, spec, path = make_root(t, spec)
        clean = Path(t) / "clean.mp4"
        tlf.ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=300", "-t", "25",
               "-af", "volume=-20dB", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-shortest", clean)
        rep = json.loads((root / spec["report"]).read_text())
        rep["composed"]["clean"].update(output_sha256=cl.sha256(clean), release_asset=bl.clean_asset("genesis-long-test", cl.sha256(clean)))
        (root / spec["report"]).write_text(json.dumps(rep))
        voice_fixture(Path(t) / "work")
        return root, spec, path, clean

    def test_render_is_two_halves_with_the_voice_captions_and_gain(self):
        with tempfile.TemporaryDirectory() as t:
            spec = spec_of(verse={"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 5.0})
            root, spec, path, clean = self.prepare(t, spec)
            rec = rs.render(path, clean, Path(t) / "work", Path(t) / "out", root=root)
            self.assertTrue(all(rec["checks"].values()), rec["checks"])
            self.assertEqual(rec["frame"], [1080, 1920])
            self.assertAlmostEqual(rec["seconds"], 22.0, delta=0.2)
            self.assertEqual(rec["output_sha256"], cl.sha256(Path(t) / "out" / f"{spec['id']}.mp4"))
            self.assertEqual(rec["voice"]["voice_id"], "am_michael")
            self.assertEqual(rec["keeper_image"]["id"], STILL)
            self.assertEqual(rec["sentences"][0]["start"], round(rs.LEAD_IN + rs.VOICE_AT, 3))
            self.assertTrue(rec["motion_direction"]["move"])
            # the halves: the top is the clip (testsrc2 is busy), the bottom the Keeper still (no pixel is black bars)
            frame = Path(t) / "f.png"
            tlf.ff("-i", Path(t) / "out" / f"{spec['id']}.mp4", "-ss", "10", "-frames:v", "1", frame)
            self.assertTrue(frame.stat().st_size > 10_000)
            with self.assertRaisesRegex(SystemExit, "CLEAN_MASTER_SHA256_MISMATCH"):
                rs.render(path, Path(t) / "out" / f"{spec['id']}.mp4", Path(t) / "work", Path(t) / "out2", root=root)
            # a voice that does not fit the clip is refused, never faster
            voice_fixture(Path(t) / "work2", speech=22.0)
            with self.assertRaisesRegex(SystemExit, "VOICE_TOO_LONG_FOR_CLIP"):
                rs.render(path, clean, Path(t) / "work2", Path(t) / "out3", root=root)
            # the record: its own, no review, the track rules of publish_episode pass
            episode = json.loads(rs.record(path, Path(t) / "out" / f"{spec['id']}.json", root=root).read_text())
            self.assertEqual((episode["track"], episode["layout"], episode["parent"]["long"]), (rs.TRACK, rs.LAYOUT, "genesis-long-test"))
            self.assertEqual([x["kind"] for x in episode["narration"]], ["insight"])
            self.assertEqual(episode["scripture"], [{"reference": VERSE[0], "text": VERSE[1]}])
            self.assertEqual(episode["credits"], {"vidiq": 0, "pavo": 0})
            self.assertNotIn("review", episode)
            self.assertEqual(pe.short_problems(episode), [])
            self.assertEqual(pe.problems(dict(episode, part=1))[:1], ["REVIEW_MISSING"])   # reviewed on its own master next


class Downstream(unittest.TestCase):
    def episode(self, **kw):
        rec = {"id": "genesis-long-test-reflection-1", "format": "short", "track": pe.REFLECTION_TRACK, "part": 1, "seconds": 30.0,
               "output_sha256": tlf.SHA, "title": "t", "description": "Genesis 7 (public domain), AI. The full story: the long video.",
               "parent": {"long": "genesis-long-test", "pilot": "pilot-099", "clean_master_sha256": tlf.CLEAN},
               "narration": [{"kind": "insight", "text": REFLECTION}]}
        rec.update(kw)
        return rec

    def test_publish_episode_track_rules(self):
        self.assertEqual(pe.short_problems(self.episode()), [])
        for kw, code in ((dict(seconds=15.0), "REFLECTION_LENGTH"), (dict(seconds=41.0), "REFLECTION_LENGTH"),
                         (dict(parent=None), "REFLECTION_PARENT_MISSING"),
                         (dict(description="Genesis 7 (public domain), AI."), "REFLECTION_DESCRIPTION_NOT_TO_THE_LONG"),
                         (dict(narration=[{"kind": "insight", "text": "Too short."}]), "REFLECTION_WORDS"),
                         (dict(narration=[]), "NARRATION_MISSING"), (dict(format="long"), "REFLECTION_NOT_A_SHORT")):
            self.assertTrue(any(p.startswith(code) for p in pe.short_problems(self.episode(**kw))), kw)
        # a whole-Short rule (170-179 s) or the cuts' 20-179 s window never applies to it
        self.assertEqual(pe.CUT_SECONDS, (20.0, 179.0))
        self.assertTrue(pe.short_problems(self.episode(seconds=120.0)))

    def test_its_review_keeps_the_standard_floor(self):
        review = {"reviewer": "claude-session-reviewer", "output_sha256": tlf.SHA, "overall": 9.6, "issues": []}
        self.assertEqual(pe.review_problems(self.episode(review=review)), [])
        self.assertIn("REVIEW_BELOW_FLOOR", pe.review_problems(self.episode(review=dict(review, overall=9.0))))
        # no lowered floor: the buzzy-cut defect decision alone (no overall) is not enough, and no Buzzy shot is asked for
        defect = {"reviewer": "claude-session-reviewer", "output_sha256": tlf.SHA, "issues": ["00:01 [info] soft"],
                  "defects": [{"issue": 0, "category": "info", "resolved": False}],
                  "publish_decision": {"decision": "publish", "by": "claude-session-reviewer", "note": "heard it"}}
        self.assertIn("REVIEW_BELOW_FLOOR", pe.review_problems(self.episode(review=defect)))
        self.assertIn("REVIEW_NOT_FOR_THIS_FILE", pe.review_problems(self.episode(review=dict(review, output_sha256="b" * 64))))
        self.assertIn("REVIEW_REVIEWER_NOT_DESIGNATED", pe.review_problems(self.episode(review=dict(review, reviewer="someone"))))
        self.assertNotIn("TRACK_UNKNOWN", pe.review_problems(self.episode(review=review)))
        self.assertIn("TRACK_UNKNOWN", pe.review_problems(self.episode(track="other", review=review)))

    def test_native_review_and_arc_links_know_it(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path = make_root(t)
            self.assertEqual((nr.track_for(path), nr.floor_for(path)), (rs.TRACK, 9.5))   # reviewed at the standard floor
            import arc_links
            eps = Path(t) / "episodes"
            eps.mkdir()
            (eps / "genesis-long-test-reflection-1.json").write_text(json.dumps(self.episode()))
            arcs = {"arcs": [{"id": "arc-x", "shorts": [], "long": {"pilot": "pilot-099"}}]}
            got = arc_links.resolve(arcs, {"entries": {}}, eps)
            self.assertEqual([s[0] for s in got[0]["shorts"]], ["genesis-long-test-reflection-1"])

    def test_dispatch_guard_accepts_a_reflection_spec_as_the_review_plan(self):
        import re
        guard = (ROOT / "migration/ops/dispatch_guard.py").read_text()
        review = (HERE / "native_review.py").read_text()
        self.assertIn("bible/reflections/", guard)
        self.assertIn("(cuts|reflections)", review)
        self.assertTrue(re.fullmatch(r"migration/production/bible/(cuts|reflections)/[a-z0-9-]+\.json",
                                     "migration/production/bible/reflections/flood-ends-long-1.json"))


if __name__ == "__main__":
    unittest.main()
