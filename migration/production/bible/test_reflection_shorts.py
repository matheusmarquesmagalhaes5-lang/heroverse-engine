"""The Keeper reflection split-screen Short (reflection_shorts.py), owner rule 02/11: the bottom half is the Keeper really
speaking, 2-4 approved Pavo talking clips. The reflection plan (plan_check, track keeper-reflection, 1:1 chest-up talking
Keeper shots), the spec checker (duration window, a published approved long, the segments' words, the approved clips, the
E266 flag split: hard flags and wrong words block, the lip-sync / audio-offset flags do not), the render (two 1080x960
halves, the clips joined by crossfades, their own audio, captions, -14 LUFS) on fixture clips, and the unchanged
downstream: publish_episode's track rules (the standard 9.5 review floor stays), native-review and arc-links."""
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
import episode_build as eb  # noqa: E402
import native_review as nr  # noqa: E402
import plan_check as pc  # noqa: E402
import publish_episode as pe  # noqa: E402
import reflection_shorts as rs  # noqa: E402
import test_long_first as tlf  # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None

VIDEO_ID = "AbCdEfGhIjK"
VERSE = ("Genesis 7:4 (KJV)", "For yet seven days, and I will cause it to rain upon the earth forty days and forty nights; "
         "and every living substance that I have made will I destroy from off the face of the earth.")
SEG1 = "Seven days of warning, and he spent them building. Notice what the story leaves out: no argument, no plea."
SEG2 = "Obedience here is quiet, slow work done before anyone can see why. I find that harder than any miracle."
EPISODE = "genesis-long-test-reflection-1"
KEEPER_PROMPT = (
    "Painterly cinematic realism with Old-Master light, one warm grade, cinema camera, fine film grain. Close-up from the "
    "chest up, his face large in the centre of the frame, static camera. The narrator, an original elderly storyteller of "
    "about seventy with Middle Eastern features, weathered warm olive skin with deep lines on the forehead, kind deep-set "
    "brown eyes, a very long silver-white beard and long silver hair under a hooded brown wool robe, seated cross-legged by "
    "a small campfire at night under a starry desert sky, holding an old rolled scroll in both hands, centred in the frame "
    "holds his head level and looks straight into the camera and speaks to the camera, his lips moving clearly with every "
    "word, LOOK. Night in the open desert, the campfire's warm flicker on his face, deep blue darkness and stars behind "
    "him. Tender and grave. No text, no logos.")
LOOKS = ("a calm kind look", "a gentle questioning look", "a warm expectant look", "a grave tender look")


def reflection_plan(texts=(SEG1, SEG2), episode=EPISODE):
    return {"source_policy": "pavo_speech_stock", "track": pc.REFLECTION_TRACK, "version": "bible-plan-v2", "episode": episode,
            "part": 1, "aspect_ratio": "1:1", "narration": [{"kind": "insight", "text": t} for t in texts],
            "shots": [{"kind": "keeper", "id": f"k-r{i + 1}", "lines": [i], "audio_route": "kokoro",
                       "prompt": KEEPER_PROMPT.replace("LOOK", LOOKS[i % len(LOOKS)])} for i in range(len(texts))]}


def spec_of(**kw):
    spec = {"version": rs.VERSION, "track": rs.TRACK, "layout": rs.LAYOUT, "id": EPISODE,
            "long": "genesis-long-test", "pilot": "pilot-099",
            "report": "migration/evidence/episodes/genesis-long-test/report-1.json",
            "clip": {"start": 0.2, "end": 22.2, "x": 0.5, "audio": "duck"},
            "plan": f"migration/production/bible/plans/{EPISODE}.json",
            "segments": [{"shot": "k-r1", "text": SEG1}, {"shot": "k-r2", "text": SEG2}],
            "title": "What Noah never said #shorts",
            "description": "The Keeper on Genesis 7 (public domain), AI visuals. The full story: the long video.",
            "tags": ["noah", "bible"], "first_comment": f"The whole story, in the long video: https://youtu.be/{VIDEO_ID}"}
    spec.update(kw)
    return spec


def make_clip(path, freq, seconds=10.0, speech=9.4):
    """A 1:1 Pavo-like clip: tone for `speech` s (the Keeper's line), silence after (the pad that Pavo keeps)."""
    tlf.ff("-f", "lavfi", "-i", f"testsrc2=size=640x640:rate=30:duration={seconds}", "-f", "lavfi",
           "-i", f"sine=frequency={freq}:sample_rate=48000:duration={seconds}", "-af",
           f"volume=-18dB,volume=0:enable='gt(t,{speech})'", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", path)


def make_root(t, spec=None, published=True, flags=None, accepted=None, score=9.6, make_clips=True, said=None, words_proof=None):
    """flags: {shot: [flags]} of the probe record; accepted / words_proof: what the approval recorded."""
    root, base, _ = tlf.cut_root(t, [])
    spec = spec or spec_of()
    (root / "migration/production/bible/reflections").mkdir(parents=True, exist_ok=True)
    (root / "migration/publish").mkdir(parents=True, exist_ok=True)
    ledger = {"entries": {f"pilot-099:{tlf.SHA}": {"video_id": VIDEO_ID}} if published else {}}
    (root / "migration/publish/ledger.json").write_text(json.dumps(ledger))
    plan = reflection_plan([s["text"] for s in spec["segments"]], spec["id"])
    plan["shots"] = plan["shots"][:len(spec["segments"])]
    (root / "migration/production/bible/plans" / f"{spec['id']}.json").write_text(json.dumps(plan))
    approvals, probe = {}, {"episode": spec["id"], "run_id": "123456", "shots": {}}
    clips = root / "clips"
    clips.mkdir()
    for i, seg in enumerate(spec["segments"]):
        sid = seg["shot"]
        path = clips / f"{sid}.mp4"
        if FFMPEG and make_clips:
            make_clip(path, 200 + 40 * i)
        else:
            path.write_bytes(f"clip {i}".encode())
        sha = cl.sha256(path)
        asset = eb.shot_asset_name(spec["id"], sid, sha)
        probe["shots"][sid] = {"request": {"audio": {"words": said if said is not None else eb.spoken_words(seg["text"])}},
                               "clips": [{"asset": asset, "clip_sha256": sha, "flags": (flags or {}).get(sid, [])}]}
        approvals[sid] = {"asset": asset, "clip_sha256": sha, "clip_seconds": 10.0, "score": score, "model": "claude-session-reviewer",
                          "note": "watched and heard the clip: the Keeper says the line, lips on the words",
                          "probe_record": f"migration/evidence/shots/{spec['id']}/123456.json"}
        if accepted and sid in accepted:
            approvals[sid]["accepted_flags"] = accepted[sid]
        if words_proof and sid in words_proof:
            approvals[sid]["words"] = {"clip_sha256": sha, "flags": []}
    (root / "migration/evidence/shots" / spec["id"]).mkdir(parents=True)
    (root / "migration/evidence/shots" / spec["id"] / "123456.json").write_text(json.dumps(probe))
    (root / rs.SHOTS).mkdir(parents=True, exist_ok=True)
    (root / rs.SHOTS / f"{spec['id']}.json").write_text(json.dumps({"episode": spec["id"], "shots": approvals}))
    path = root / f"migration/production/bible/reflections/{spec['id'].replace('-reflection-', '-')}.json"
    path.write_text(json.dumps(spec))
    return root, spec, path


def sidecar_trim(kind, trim):
    return trim + 1.0 if kind == "other-trim" else trim


def codes(result):
    return [p.split()[0] for p in result["problems"]]


class ReflectionPlan(unittest.TestCase):
    def test_a_keeper_reflection_plan_is_two_to_four_talking_keeper_shots_at_1_1(self):
        got = pc.check(reflection_plan())
        self.assertEqual(got["problems"], [])
        self.assertEqual(got["estimate"]["shots"], 2)
        self.assertEqual(pc.check(reflection_plan((SEG1, SEG2, SEG1.replace("Seven", "Eight"))) )["problems"], [])
        self.assertEqual(pc.REFLECTION_RATIOS, ("1:1",))
        self.assertEqual(pc.RATIOS, ("9:16",))   # the Shorts keep 9:16
        self.assertIn("REFLECTION_SEGMENTS", " ".join(pc.check(reflection_plan((SEG1,)))["problems"]))
        five = reflection_plan((SEG1,) * 5)
        self.assertTrue(any(p.startswith("REFLECTION_SEGMENTS") for p in pc.check(five)["problems"]))

    def test_each_shot_is_a_talking_keeper_framed_chest_up(self):
        for edit, code in ((lambda p: p.update(aspect_ratio="9:16"), "ASPECT_RATIO"),
                           (lambda p: p["shots"][0].update(voiceover=True), "REFLECTION_SHOT_FIELDS"),
                           (lambda p: p["shots"][0].update(kind="scene"), "SHOT_KIND"),
                           (lambda p: p["shots"][0].update(lines=[1]), "REFLECTION_SHOT_FIELDS"),
                           (lambda p: p["shots"][0].update(prompt=p["shots"][0]["prompt"].replace("Close-up from the chest up",
                                                                                                "Medium shot")), "KEEPER_FRAMING_16X9"),
                           (lambda p: p["shots"][0].update(prompt=p["shots"][0]["prompt"].replace(", his lips moving clearly with every word", "")
                                                           .replace("speaks to the camera", "")), "KEEPER_NOT_SPEAKING"),
                           (lambda p: p["shots"][1].update(prompt=p["shots"][0]["prompt"]), "PROMPT_REPEATED"),
                           (lambda p: p["narration"][0].update(kind="story"), "NARRATION_LINE"),
                           (lambda p: p["narration"][1].update(text="Obedience is quiet work, slow and plain and unseen"),
                            "REFLECTION_SEGMENT_NOT_A_SENTENCE"),
                           (lambda p: p["narration"][1].update(text="Yes."), "KEEPER_LINE_TOO_SHORT")):
            plan = reflection_plan()
            edit(plan)
            self.assertTrue(any(p.startswith(code) for p in pc.check(plan)["problems"]), (code, pc.check(plan)["problems"]))

    def test_a_segment_one_clip_cannot_carry_is_refused(self):
        long_line = " ".join(["Obedience is quiet, slow work."] * 8)
        self.assertTrue(any(p.startswith("KEEPER_LINE_TOO_LONG") for p in pc.check(reflection_plan((SEG1, long_line)))["problems"]))

    def test_the_build_measures_it_without_a_short_story_shape(self):
        got = eb.predict(reflection_plan(), [8.0, 8.0])
        self.assertEqual(got[0], [])
        self.assertTrue(pc.reflection(reflection_plan()) and not pc.reflection({}))
        # a Short plan (9:16, scenes, a climax) is still judged by the Short's rules
        self.assertEqual(pc.check(json.loads(tlf.SHORT_PLAN.read_text()))["problems"], [])


class Scaffold(unittest.TestCase):
    def test_the_probe_plan_comes_from_the_longs_keeper_and_passes_plan_check(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            long_plan = tlf.long_plan()
            long_plan["shots"][-1].update(kind="keeper", prompt=KEEPER_PROMPT.replace("LOOK", "a calm kind look"))
            (root / "migration/production/bible/plans/genesis-long-test.json").write_text(json.dumps(long_plan))
            plan = rs.scaffold(spec, root)
            self.assertEqual(pc.check(plan)["problems"], [])
            self.assertEqual([s["id"] for s in plan["shots"]], ["k-r1", "k-r2"])
            self.assertEqual((plan["track"], plan["aspect_ratio"], plan["episode"]), (pc.REFLECTION_TRACK, "1:1", EPISODE))
            self.assertNotEqual(plan["shots"][0]["prompt"], plan["shots"][1]["prompt"])
            self.assertEqual([x["text"] for x in plan["narration"]], [SEG1, SEG2])
            self.assertIn("a gentle questioning look", plan["shots"][1]["prompt"])
            noisy = tlf.long_plan()
            noisy["shots"] = [s for s in noisy["shots"] if s["kind"] != "keeper"]
            (root / "migration/production/bible/plans/genesis-long-test.json").write_text(json.dumps(noisy))
            with self.assertRaisesRegex(SystemExit, "LONG_HAS_NO_TALKING_KEEPER_PROMPT"):
                rs.scaffold(spec, root)


class Check(unittest.TestCase):
    def test_a_good_reflection_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path = make_root(t)
            got = rs.check(spec, root, spec_path=str(path.relative_to(root)))
            self.assertEqual(got["problems"], [])
            self.assertEqual((got["reflection"]["first"], got["reflection"]["last"]), (0, 3))
            self.assertEqual((got["reflection"]["words"], got["reflection"]["long_video_id"]), (38, VIDEO_ID))
            self.assertEqual(got["reflection"]["segments"], 2)
            self.assertEqual(got["reflection"]["offsets"], [0.3, 10.1])
            self.assertAlmostEqual(got["reflection"]["bottom_end"], 20.1)
            self.assertAlmostEqual(got["reflection"]["seconds"], 22.0)
            spec["clip"].update(audio="mute")
            spec["verse"] = {"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 5.0}
            self.assertEqual(rs.check(spec, root)["problems"], [])

    def test_v1_the_still_motion_bottom_half_is_retired(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            old = dict(spec, version="bible-reflection-v1")
            self.assertEqual(codes(rs.check(old, root)), ["SPEC_VERSION_RETIRED"])
            for field in ({"keeper_image": "x-k-insight"}, {"motion": "push_in"}, {"reflection": {"text": SEG1 + " " + SEG2}}):
                self.assertIn("SPEC_STILL_FIELDS", codes(rs.check(dict(spec, **field), root)), field)

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
            self.assertEqual(rs.SECONDS, (20.0, 40.0))

    def test_the_top_clip_never_repeats_another_short_of_the_same_long(self):
        # E279: another cut of the long (or reflection) already holds this footage and speech
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            other = tlf.cut("genesis-07-cut-1", start=0.25, end=22.3)
            cuts = root / "migration/production/bible/cuts/genesis-long-test.json"
            cuts.write_text(json.dumps({"cuts": [other]}))
            self.assertIn("CLIP_OVERLAPS_ANOTHER", codes(rs.check(spec, root)))
            cuts.write_text(json.dumps({"cuts": [dict(other, start=22.0, end=40.0)]}))   # 0.2 s: only the fade
            self.assertNotIn("CLIP_OVERLAPS_ANOTHER", codes(rs.check(spec, root)))
            twin = dict(spec, id="genesis-long-test-reflection-2")
            (root / "migration/production/bible/reflections/genesis-long-test-2.json").write_text(json.dumps(twin))
            self.assertIn("CLIP_OVERLAPS_ANOTHER", codes(rs.check(spec, root)))

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

    def test_the_segments_are_whole_sentences_in_the_plan_and_the_reflection_has_its_length(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            cases = ((dict(segments=spec["segments"][:1]), "SEGMENTS"),
                     (dict(segments=[spec["segments"][0], {"shot": "k-r2", "text": SEG2.replace("miracle", "wonder")}]), "SEGMENT_NOT_IN_PLAN"),
                     (dict(segments=[spec["segments"][0], {"shot": "k-r1", "text": SEG2}]), "SEGMENTS_SHOT_REPEATED"),
                     (dict(segments="no"), "SEGMENTS"), (dict(plan="migration/production/bible/plans/other.json"), "PLAN_PATH"))
            for kw, code in cases:
                self.assertIn(code, codes(rs.check(dict(spec, **kw), root)), kw)
            one = spec_of(segments=[{"shot": "k-r1", "text": SEG1}])
            self.assertIn("SEGMENTS", codes(rs.check(one, root)))   # 2-4 segments
            self.assertEqual(rs.SEGMENTS, (2, 4))
            self.assertEqual(rs.WORDS, (20, 80))
            short = dict(spec, segments=[{"shot": "k-r1", "text": "Wait."}, {"shot": "k-r2", "text": "Listen."}])
            self.assertIn("REFLECTION_LENGTH", codes(rs.check(short, root)))
        with tempfile.TemporaryDirectory() as t:
            banned = spec_of(segments=[{"shot": "k-r1", "text": SEG1}, {"shot": "k-r2", "text": SEG2 + " Shocking."}])
            root, spec, _ = make_root(t, banned)
            self.assertIn("REFLECTION_BANNED_WORDS", codes(rs.check(spec, root)))

    def test_every_segment_has_an_approved_pavo_clip_of_its_own_words(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, score=9.0)
            self.assertIn("SEGMENT_CLIP_SCORE", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            f = root / rs.SHOTS / f"{EPISODE}.json"
            doc = json.loads(f.read_text())
            gone = doc["shots"].pop("k-r2")
            f.write_text(json.dumps(doc))
            self.assertIn("SEGMENT_CLIP_NOT_APPROVED", codes(rs.check(spec, root)))
            doc["shots"]["k-r2"] = dict(gone, source="footage")   # a footage / still-motion source is not a talking Keeper
            f.write_text(json.dumps(doc))
            self.assertIn("SEGMENT_CLIP_NOT_PAVO", codes(rs.check(spec, root)))
            doc["shots"]["k-r2"] = dict(gone, revocation={"by": "claude-session-reviewer", "reason": "mouth wrong"})
            f.write_text(json.dumps(doc))
            self.assertIn("SHOT_REVIEW_REVOKED", codes(rs.check(spec, root)))
            doc["shots"]["k-r2"] = dict(gone, clip_seconds=2.0)
            f.write_text(json.dumps(doc))
            self.assertIn("SEGMENT_CLIP_SECONDS", codes(rs.check(spec, root)))
            doc["shots"]["k-r2"] = dict(gone, model="someone")
            f.write_text(json.dumps(doc))
            self.assertIn("SEGMENT_CLIP_REVIEW", codes(rs.check(spec, root)))
            doc["shots"]["k-r2"] = dict(gone, asset="shot-x.mp4")
            f.write_text(json.dumps(doc))
            self.assertIn("SEGMENT_CLIP_ASSET", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:   # wrong words: the clip was made for another line
            root, spec, _ = make_root(t, said=["other", "words"])
            self.assertIn("SEGMENT_CLIP_WRONG_WORDS", codes(rs.check(spec, root)))
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            (root / "migration/evidence/shots" / EPISODE / "123456.json").unlink()
            self.assertIn("SEGMENT_PROBE_RECORD", codes(rs.check(spec, root)))

    def test_the_flag_split_for_a_talking_clip(self):
        # soft (lips a little off, the audio offset) and a words flag with the ASR's proof: informative, the clip ships
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, flags={"k-r1": ["MOUTH_NOT_IN_SYNC", "AUDIO_OFFSET"], "k-r2": ["AUDIO_NOT_OUR_LINE"]},
                                      accepted={"k-r1": ["MOUTH_NOT_IN_SYNC"], "k-r2": ["AUDIO_NOT_OUR_LINE"]},
                                      words_proof={"k-r2": True})
            got = rs.check(spec, root)
            self.assertEqual(got["problems"], [])
            clips = got["reflection"]["clips"]
            self.assertEqual(clips[0]["flags"]["soft"], ["MOUTH_NOT_IN_SYNC", "AUDIO_OFFSET"])
            self.assertEqual(clips[1]["flags"]["words"], ["AUDIO_NOT_OUR_LINE"])
            self.assertEqual(clips[1]["accepted_flags"], ["AUDIO_NOT_OUR_LINE"])
        # AUDIO_NOT_OUR_LINE without the pinned ASR's proof on that clip blocks (the words may differ)
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t, flags={"k-r2": ["AUDIO_NOT_OUR_LINE"]}, accepted={"k-r2": ["AUDIO_NOT_OUR_LINE"]})
            self.assertIn("SEGMENT_CLIP_WORDS_UNPROVEN", codes(rs.check(spec, root)))
        # hard: no face, a broken render, a policy problem, a talking mouth where none is wanted
        for flag in ("FACE_NOT_FOUND", "NO_VIDEO", "GOD_SHOT_FACE", "MOUTH_TALKING"):
            with tempfile.TemporaryDirectory() as t:
                root, spec, _ = make_root(t, flags={"k-r1": [flag, "MOUTH_NOT_IN_SYNC"]}, accepted={"k-r1": ["MOUTH_NOT_IN_SYNC", flag]})
                self.assertIn("SEGMENT_CLIP_HARD_FLAG", codes(rs.check(spec, root)), flag)

    def test_the_keeper_clips_fit_the_top_clip(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            f = root / rs.SHOTS / f"{EPISODE}.json"
            doc = json.loads(f.read_text())
            for k in doc["shots"]:
                doc["shots"][k]["clip_seconds"] = 12.0
            f.write_text(json.dumps(doc))
            self.assertIn("REFLECTION_TOO_LONG_FOR_CLIP", codes(rs.check(spec, root)))   # 24 s of clips in 22 s
            for k in doc["shots"]:
                doc["shots"][k]["clip_seconds"] = 6.0
            f.write_text(json.dumps(doc))
            self.assertIn("REFLECTION_TOO_SHORT_FOR_CLIP", codes(rs.check(spec, root)))   # a frozen last frame, little speech

    def test_the_verse_is_quoted_only_exactly_and_only_if_shown(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            wrong = dict(spec, verse={"reference": VERSE[0], "text": VERSE[1].replace("seven", "six"), "start": 0.5, "end": 5.0})
            self.assertIn("VERSE_NOT_KJV", codes(rs.check(wrong, root)))
            late = dict(spec, verse={"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 30.0})
            self.assertIn("VERSE_INVALID", codes(rs.check(late, root)))
            self.assertIn("VERSE_INVALID", codes(rs.check(dict(spec, verse={"reference": VERSE[0]}), root)))

    def test_the_package_points_to_the_long(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            for kw, code in ((dict(first_comment="Watch the long video."), "FIRST_COMMENT_NOT_TO_THE_LONG"),
                             (dict(description="The Keeper on Genesis 7 (public domain KJV), AI visuals."), "DESCRIPTION_NOT_TO_THE_LONG"),
                             (dict(description="The full story, the long video."), "DISCLOSURE_MISSING"),
                             (dict(title=""), "TITLE_MISSING"), (dict(title="t" * 101), "TITLE_LENGTH"),
                             (dict(bottom={"y": 2}), "BOTTOM_Y")):
                self.assertIn(code, codes(rs.check(dict(spec, **kw), root)), kw)


@unittest.skipUnless(FFMPEG, "ffmpeg")
class Render(unittest.TestCase):
    def prepare(self, t, spec=None, **kw):
        root, spec, path = make_root(t, spec, **kw)
        clean = Path(t) / "clean.mp4"
        tlf.ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=300", "-t", "25",
               "-af", "volume=-20dB", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-shortest", clean)
        rep = json.loads((root / spec["report"]).read_text())
        rep["composed"]["clean"].update(output_sha256=cl.sha256(clean), release_asset=bl.clean_asset("genesis-long-test", cl.sha256(clean)))
        (root / spec["report"]).write_text(json.dumps(rep))
        work = Path(t) / "work"
        (work / "clips").mkdir(parents=True)
        for sid in ("k-r1", "k-r2"):
            shutil.copy(root / "clips" / f"{sid}.mp4", work / "clips" / f"{sid}.mp4")
        return root, spec, path, clean, work

    def test_the_speech_span_of_a_clip(self):
        with tempfile.TemporaryDirectory() as t:
            clip = Path(t) / "c.mp4"
            make_clip(clip, 220)
            first, last, seconds, tail = rs.speech_span(clip)
            self.assertEqual(first, 0.0)
            self.assertAlmostEqual(last, 9.4, delta=0.2)
            self.assertAlmostEqual(tail, 0.6, delta=0.25)

    def test_render_is_two_halves_with_the_keeper_clips_captions_and_gain(self):
        with tempfile.TemporaryDirectory() as t:
            spec = spec_of(verse={"reference": VERSE[0], "text": VERSE[1], "start": 0.5, "end": 5.0})
            root, spec, path, clean, work = self.prepare(t, spec)
            rec = rs.render(path, clean, work, Path(t) / "out", root=root)
            self.assertTrue(all(rec["checks"].values()), rec["checks"])
            self.assertEqual(rec["frame"], [1080, 1920])
            self.assertAlmostEqual(rec["seconds"], 22.0, delta=0.2)
            self.assertEqual(rec["output_sha256"], cl.sha256(Path(t) / "out" / f"{spec['id']}.mp4"))
            self.assertEqual([s["shot"] for s in rec["segments"]], ["k-r1", "k-r2"])
            self.assertEqual([s["start"] for s in rec["segments"]], [0.3, 10.1])
            self.assertEqual(rec["voice"]["source"], "pavo-talking-clips")
            self.assertEqual(rec["sentences"][0]["start"], 0.3)
            self.assertEqual(rec["sentences"][-1]["segment"], "r01")
            self.assertEqual(rec["bottom"]["crossfade"], rs.XFADE)
            # the halves: the top is the clip (testsrc2 is busy), the bottom the Keeper clips (not black, not still)
            frames = []
            for at in ("3", "15"):
                frame = Path(t) / f"f{at}.png"
                tlf.ff("-i", Path(t) / "out" / f"{spec['id']}.mp4", "-ss", at, "-frames:v", "1", "-vf", "crop=1080:960:0:960", frame)
                frames.append(frame.read_bytes())
                self.assertTrue(frame.stat().st_size > 10_000)
            self.assertNotEqual(frames[0], frames[1])   # clip 1 at 3 s, clip 2 at 15 s
            with self.assertRaisesRegex(SystemExit, "CLEAN_MASTER_SHA256_MISMATCH"):
                rs.render(path, Path(t) / "out" / f"{spec['id']}.mp4", work, Path(t) / "out2", root=root)
            # the record: its own, no review, the track rules of publish_episode pass
            episode = json.loads(rs.record(path, Path(t) / "out" / f"{spec['id']}.json", root=root).read_text())
            self.assertEqual((episode["track"], episode["layout"], episode["parent"]["long"]), (rs.TRACK, rs.LAYOUT, "genesis-long-test"))
            self.assertEqual([x["kind"] for x in episode["narration"]], ["insight", "insight"])
            self.assertEqual([s["shot"] for s in episode["segments"]], ["k-r1", "k-r2"])
            self.assertEqual(episode["scripture"], [{"reference": VERSE[0], "text": VERSE[1]}])
            self.assertNotIn("keeper_image", episode)
            self.assertNotIn("review", episode)
            self.assertEqual(pe.short_problems(episode), [])
            self.assertEqual(pe.problems(dict(episode, part=1))[:1], ["REVIEW_MISSING"])   # reviewed on its own master next

    def test_render_refuses_a_missing_or_other_clip_and_a_crossfade_over_a_word(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path, clean, work = self.prepare(t)
            (work / "clips" / "k-r2.mp4").write_bytes(b"another file")
            with self.assertRaisesRegex(SystemExit, "CLIP_FILE_MISSING k-r2"):
                rs.render(path, clean, work, Path(t) / "out", root=root)
            (work / "clips" / "k-r2.mp4").unlink()
            shutil.copy(root / "clips" / "k-r2.mp4", work / "clips" / "k-r2.mp4")
            # a first clip whose speech runs to its last frame: the crossfade would fade his last word
            tight = root / "clips" / "tight.mp4"
            make_clip(tight, 260, speech=9.95)
            sha = cl.sha256(tight)
            f = root / rs.SHOTS / f"{EPISODE}.json"
            doc = json.loads(f.read_text())
            doc["shots"]["k-r1"].update(clip_sha256=sha, asset=eb.shot_asset_name(EPISODE, "k-r1", sha))
            f.write_text(json.dumps(doc))
            probe = root / "migration/evidence/shots" / EPISODE / "123456.json"
            rec = json.loads(probe.read_text())
            rec["shots"]["k-r1"]["clips"][0].update(clip_sha256=sha, asset=doc["shots"]["k-r1"]["asset"])
            probe.write_text(json.dumps(rec))
            shutil.copy(tight, work / "clips" / "k-r1.mp4")
            with self.assertRaisesRegex(SystemExit, "SEGMENT_TAIL_TOO_SHORT k-r1"):
                rs.render(path, clean, work, Path(t) / "out", root=root)

    def trim_k_r1(self, root, trim, sidecar):
        """k-r1 approved with an out point (approve-shot --trim-out), its words proof on the trimmed media as given."""
        f = root / rs.SHOTS / f"{EPISODE}.json"
        doc = json.loads(f.read_text())
        doc["shots"]["k-r1"]["trim_out_s"] = trim
        f.write_text(json.dumps(doc))
        sha = doc["shots"]["k-r1"]["clip_sha256"]
        side = root / "migration/evidence/shots" / EPISODE / "speech" / f"{sha}.json"
        side.parent.mkdir(parents=True, exist_ok=True)
        if sidecar:
            pinned = eb.pavo_native.criteria()["speech"]["asr_model"]["model_bin_sha256"]
            heard = " ".join(eb.spoken_words(SEG1)) if sidecar == "line" else "you mealy"
            side.write_text(json.dumps({"shot": "k-r1", "clip_sha256": sha, "trim_out_s": sidecar_trim(sidecar, trim),
                                        "measures": {"asr": {"model_bin_sha256": pinned, "text": heard}}}))

    def test_e282_the_check_honours_an_approved_trim_and_reverifies_the_words_on_the_trimmed_clip(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, _ = make_root(t)
            self.assertEqual(rs.check(spec, root)["reflection"]["clips"][0]["seconds"], 10.0)
            self.trim_k_r1(root, 9.55, None)   # no ASR proof on the trimmed media
            self.assertIn("SEGMENT_TRIM_WORDS_UNPROVEN", codes(rs.check(spec, root)))
            self.trim_k_r1(root, 9.55, "other-trim")   # the proof is for another cut
            self.assertIn("SEGMENT_TRIM_WORDS_UNPROVEN", codes(rs.check(spec, root)))
            self.trim_k_r1(root, 9.55, "extra")   # the trimmed clip still carries extra speech
            self.assertIn("SEGMENT_TRIM_WORDS", codes(rs.check(spec, root)))
            self.trim_k_r1(root, 12.0, "line")   # an out point past the clip
            self.assertIn("SEGMENT_CLIP_TRIM", codes(rs.check(spec, root)))
            self.trim_k_r1(root, 9.55, "line")
            got = rs.check(spec, root)
            self.assertEqual(got["problems"], [])
            first = got["reflection"]["clips"][0]
            self.assertEqual((first["trim_out_s"], first["seconds"]), (9.55, 9.55))   # the used length is the out point
            self.assertIsNone(got["reflection"]["clips"][1]["trim_out_s"])

    def test_e282_a_trimmed_clip_shortens_its_crossfade_a_full_clip_keeps_the_gate(self):
        spans = [(0.0, 9.4, 9.6, 0.2), (0.0, 9.0, 10.0, 1.0)]
        trimmed = [{"shot": "a", "trim_out_s": 9.6}, {"shot": "b"}]
        self.assertEqual(rs.join_fades(trimmed, spans), [0.18])
        with self.assertRaisesRegex(SystemExit, "SEGMENT_TAIL_TOO_SHORT a"):
            rs.join_fades([{"shot": "a"}, {"shot": "b"}], spans)   # not trimmed: the 0.22 s gate holds
        self.assertEqual(rs.join_fades(trimmed, [(0.0, 9.5, 9.6, 0.09), spans[1]]), [0.0])   # no room: a plain cut
        offsets, end = rs.timeline([{"seconds": 9.6, "fade": 0.18}, {"seconds": 10.0, "fade": rs.XFADE}])
        self.assertEqual((offsets, end), ([0.3, 9.72], 19.72))
        parts, label = rs.bottom_graph([9.6, 10.0], 0.5, 22.0, fades=[0.18])
        self.assertTrue(any("xfade=transition=fade:duration=0.18:offset=9.420" in p for p in parts), parts)

    def test_e282_render_cuts_each_clip_at_its_approved_out_point(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path, clean, work = self.prepare(t)
            self.trim_k_r1(root, 9.55, "line")
            rec = rs.render(path, clean, work, Path(t) / "out", root=root)
            self.assertTrue(all(rec["checks"].values()), rec["checks"])
            first, second = rec["segments"]
            self.assertEqual(first["trim_out_s"], 9.55)
            self.assertNotIn("trim_out_s", second)
            self.assertAlmostEqual(first["seconds"], 9.55, delta=0.1)   # measured on the trimmed media, not the 10 s clip
            self.assertEqual(cl.sha256(work / "clips" / "k-r1.mp4"), json.loads(
                (root / rs.SHOTS / f"{EPISODE}.json").read_text())["shots"]["k-r1"]["clip_sha256"])   # the approved bytes stay
            self.assertAlmostEqual(cl.duration(work / "trimmed" / "k-r1.mp4"), 9.55, delta=0.1)
            self.assertTrue(rs.XFADE_MIN <= rec["bottom"]["crossfades"][0] <= rs.XFADE)
            self.assertAlmostEqual(second["start"], 0.3 + first["seconds"] - rec["bottom"]["crossfades"][0], delta=0.01)

    def test_e286_a_clip_set_faster_than_the_band_is_retimed_by_at_most_ten_percent(self):
        with tempfile.TemporaryDirectory() as t:
            clip = Path(t) / "c.mp4"
            make_clip(clip, 220, seconds=8.0, speech=6.0)
            slow = rs.retime_media(clip, 0.9, Path(t) / "slow.mp4")
            self.assertAlmostEqual(cl.duration(slow), 8.0 / 0.9, delta=0.12)   # picture and voice stretched together
            self.assertTrue(rs.has_audio(slow))
            first, last, _, _ = rs.speech_span(slow)
            self.assertAlmostEqual(last - first, 6.0 / 0.9, delta=0.25)
        with tempfile.TemporaryDirectory() as t:
            root, spec, path, clean, work = self.prepare(t)
            for i, sid in enumerate(("k-r1", "k-r2")):
                fast = root / "clips" / f"fast{i}.mp4"
                make_clip(fast, 260 + i, speech=3.0)
                sha = cl.sha256(fast)
                f = root / rs.SHOTS / f"{EPISODE}.json"
                doc = json.loads(f.read_text())
                doc["shots"][sid].update(clip_sha256=sha, asset=eb.shot_asset_name(EPISODE, sid, sha))
                f.write_text(json.dumps(doc))
                probe = root / "migration/evidence/shots" / EPISODE / "123456.json"
                rec = json.loads(probe.read_text())
                rec["shots"][sid]["clips"][0].update(clip_sha256=sha, asset=doc["shots"][sid]["asset"])
                probe.write_text(json.dumps(rec))
                shutil.copy(fast, work / "clips" / f"{sid}.mp4")
            with self.assertRaisesRegex(SystemExit, "VOICE_PACE .*needs x"):
                rs.render(path, clean, work, Path(t) / "out", root=root)

    def test_fetch_clips_takes_the_approved_bytes_by_their_asset_names(self):
        with tempfile.TemporaryDirectory() as t:
            root, spec, path, clean, work = self.prepare(t)
            got = {}

            def fetch(name, dst):
                got[name] = dst
                shutil.copy(root / "clips" / ("k-r1.mp4" if "k-r1" in name else "k-r2.mp4"), dst)
            self.assertEqual(rs.fetch_clips(path, Path(t) / "w2", root=root, fetch=fetch), ["k-r1", "k-r2"])
            self.assertEqual(len(got), 2)
            self.assertTrue(all(n.startswith("shot-genesis-long-test-reflection-1-k-r") for n in got))
            wrong = lambda name, dst: Path(dst).write_bytes(b"not the clip")   # noqa: E731
            with self.assertRaisesRegex(SystemExit, "SHOT_CLIP_SHA256_MISMATCH"):
                rs.fetch_clips(path, Path(t) / "w3", root=root, fetch=wrong)


class Downstream(unittest.TestCase):
    def episode(self, **kw):
        rec = {"id": "genesis-long-test-reflection-1", "format": "short", "track": pe.REFLECTION_TRACK, "part": 1, "seconds": 30.0,
               "output_sha256": tlf.SHA, "title": "t", "description": "Genesis 7 (public domain), AI. The full story: the long video.",
               "parent": {"long": "genesis-long-test", "pilot": "pilot-099", "clean_master_sha256": tlf.CLEAN},
               "narration": [{"kind": "insight", "text": SEG1}, {"kind": "insight", "text": SEG2}]}
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
        self.assertIn("bible-reflection-v2", guard)
        self.assertIn("(cuts|reflections)", review)
        self.assertTrue(re.fullmatch(r"migration/production/bible/(cuts|reflections)/[a-z0-9-]+\.json",
                                     "migration/production/bible/reflections/flood-ends-long-1.json"))


if __name__ == "__main__":
    unittest.main()
