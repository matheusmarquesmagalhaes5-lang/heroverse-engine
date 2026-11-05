#!/usr/bin/env python3
"""Offline checks of the arc compilation long (E251): plan refusal, a real ffmpeg render of tiny stand-ins (framing,
join, loudness, QA) and the defect-gated review track through long_review, prepublish_gate and publication_binding."""
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
import long_review as lr  # noqa: E402
import owner_quality_policy as oq  # noqa: E402
import prepublish_gate as pg  # noqa: E402
import publication_binding as pb  # noqa: E402

PLAN = ROOT / "migration/production/bible/compilations/arc-02-noah-compilation.json"
FFMPEG = shutil.which("ffmpeg") is not None
SHA = "a" * 64


def ff(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


class PlanTests(unittest.TestCase):
    def test_the_real_plan_is_accepted(self):
        plan = cl.load(PLAN)
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertEqual([c["short"] for c in plan["chapters"]],
                         [f"genesis-0{n}-short" for n in (6, 7, 8, 9)])
        self.assertLessEqual(len(plan["title"]), 100)

    def test_a_public_long_is_a_chapter(self):
        plan = cl.load(PLAN)
        long_ch = {"long": {"id": "flood-ends-long", "pilot": "pilot-017", "video_id": "1m-NUJhkdMY",
                            "sha256": "9" * 64, "seconds": 501.8},
                   "title": "The Flood Ends", "reference": "Genesis 8-9"}
        plan["chapters"].append(long_ch)
        self.assertEqual(cl.plan_problems(plan), [])
        src = cl.sources(plan)
        self.assertEqual(src[-1][:3], ("flood-ends-long", "pilot-017-sha256-" + "9" * 64 + ".mp4", "9" * 64))
        self.assertEqual(cl.chapter_url(long_ch), "https://www.youtube.com/watch?v=1m-NUJhkdMY")
        for mutate in (lambda c: c["long"].update(sha256="x"), lambda c: c["long"].update(video_id=""),
                       lambda c: c["long"].update(pilot="p17")):
            bad = copy.deepcopy(plan)
            mutate(bad["chapters"][-1])
            self.assertTrue(any("not a public long" in x for x in cl.plan_problems(bad)))

    def test_e284_the_complete_noah_plan_uses_the_voiceover_fallback_and_the_release_master(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertEqual(plan["title"], "The Complete Story of Noah (Genesis 5-9) KJV")
        self.assertEqual([cl.chapter_id(c) for c in plan["chapters"]],
                         [f"genesis-0{n}-short" for n in (6, 7, 8, 9)] + ["flood-ends-long"])
        self.assertEqual(cl.sources(plan)[-1][1], "bible-flood-ends-long-sha256-" + plan["chapters"][-1]["long"]["sha256"] + ".mp4")
        self.assertTrue(cl.has_voiceover(plan))
        for key in ("hook", "close"):
            self.assertNotIn("Genesis five to seven", plan[key]["text"])
        for mutate, text in ((lambda p: p["hook"]["voiceover"].update(still_sha256="0" * 64), "still missing or changed"),
                             (lambda p: p["close"]["voiceover"].update(voice_id="af_heart"), "pinned voice"),
                             (lambda p: p["close"].update(quote="0 credits (exact, fresh)"), "no-Pavo zero-credit"),
                             (lambda p: p["hook"].pop("pavo_attempt"), "Pavo attempt"),
                             (lambda p: p["chapters"][-1]["long"].update(asset="bible-other-sha256-" + "0" * 64 + ".mp4"), "release master")):
            bad = copy.deepcopy(plan)
            mutate(bad)
            self.assertTrue(any(text in x for x in cl.plan_problems(bad)), text)

    def test_e292_the_pavo_noah_plan_uses_the_remuxed_clips_and_an_approved_still_thumbnail(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-pavo-compilation.json")
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertFalse(cl.has_voiceover(plan))   # the owner's order: Pavo in the hook and the Keeper close
        self.assertEqual(plan["publish_at"], "2026-11-04T16:00:00Z")
        self.assertNotEqual(plan["pilot"], "pilot-018")   # pilot-018 is approved on master 1d5fc187
        for key in ("hook", "close"):
            self.assertEqual(plan[key]["remux"]["audio_route"], "ours")
        for mutate, text in ((lambda p: p["hook"].update(video_sha256="0" * 64), "hook video missing or changed"),
                             (lambda p: p["close"].update(quote="0 credits (no Pavo call: Kokoro voice-over on an approved still)"),
                              "not made at an exact zero-credit quote"),
                             (lambda p: p["thumbnail"]["still"].update(sha256="0" * 64), "thumbnail still missing or changed"),
                             (lambda p: p["thumbnail"]["still"].update(approved_still="flood-ends-long-s-nope"), "approved still")):
            bad = copy.deepcopy(plan)
            mutate(bad)
            self.assertTrue(any(text in x for x in cl.plan_problems(bad)), text)

    def test_e292_a_trimmed_keeper_clip_ends_at_its_line_and_has_no_closing_beat(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-pavo-compilation.json")
        for key in ("hook", "close"):
            self.assertEqual(plan[key]["trim_out_s"], 8.55)
        for bad_trim in (0, 2.9, 31, "8.5", True):
            bad = copy.deepcopy(plan)
            bad["hook"]["trim_out_s"] = bad_trim
            self.assertTrue(any("trim_out_s" in x for x in cl.plan_problems(bad)), bad_trim)
        if FFMPEG:
            base = ROOT / "migration/evidence/pavo/20261103/compilation-m2"
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "k.mp4"
                cl.render_keeper(base / "hook-clip.mp4", base / "hook.wav", out, 8.55)
                self.assertAlmostEqual(cl.duration(out), 8.55 + cl.BEAT, delta=0.1)

    def test_e289_a_keeper_segment_under_10_s_is_no_chapter_of_its_own(self):
        plan = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")
        seg = lambda kind, a, b: {"kind": kind, "start": a, "end": b}
        tl = {"segments": [seg("hook", 0, 9.3), seg("short", 9.3, 80), seg("short", 80, 246), seg("short", 246, 414),
                           seg("short", 414, 580), seg("long", 580, 1073), seg("close", 1073, 1082.5)]}
        _, rows = cl.description(plan, tl)
        self.assertEqual(rows[0], (0, plan["chapters"][0]["title"]))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1][1], plan["chapters"][-1]["title"])
        self.assertTrue(all(b[0] - a[0] >= 10 for a, b in zip(rows, rows[1:])))   # the preflight's own rule
        tl["segments"][0]["end"], tl["segments"][-1]["start"] = 12.0, 1070.0       # 10 s or more: its own chapter again
        _, rows = cl.description(plan, tl)
        self.assertEqual((rows[0][1], rows[-1][1]), (plan["chapter_zero"], plan["chapter_last"]))

    def test_refusals(self):
        plan = cl.load(PLAN)
        for mutate, text in ((lambda p: p["chapters"].reverse(), "canonical order"),
                             (lambda p: p["chapters"].pop(1), "canonical order"),
                             (lambda p: p["hook"].update(quote="2 credits"), "zero-credit"),
                             (lambda p: p["close"].update(audio_sha256="0" * 64), "changed"),
                             (lambda p: p["chapters"][0].update(short="nope"), "unknown short")):
            p = copy.deepcopy(plan)
            mutate(p)
            self.assertTrue(any(text in x for x in cl.plan_problems(p)), text)

    def test_e254_each_chapter_cuts_the_shorts_own_series_cta(self):
        plan = cl.load(PLAN)
        for c in plan["chapters"]:   # the Shorts close with "the full story is in the long video" / "part N tomorrow"
            self.assertIsInstance(c.get("end_s"), (int, float), c["short"])
        self.assertNotIn("FULL STORY", json.dumps(plan["thumbnail"]).upper())   # Genesis 5-7 is not the full story
        for bad in (5, 10_000, "70"):
            p = copy.deepcopy(plan)
            p["chapters"][0]["end_s"] = bad
            self.assertTrue(any("end_s" in x for x in cl.plan_problems(p)), bad)

    def test_sources_are_the_episode_records_masters(self):
        for sid, asset, sha, ep in cl.sources(cl.load(PLAN)):
            self.assertEqual(asset, f"bible-{sid}-sha256-{sha}.mp4")
            self.assertEqual(sha, ep["output_sha256"])


@unittest.skipUnless(FFMPEG, "ffmpeg")
class RenderTests(unittest.TestCase):
    def test_short_card_keeper_join_and_loudness(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            ff("-f", "lavfi", "-i", "testsrc=s=270x480:r=30:d=3", "-f", "lavfi", "-i", "sine=f=300:r=44100:d=3",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", t / "short.mp4")
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", t / "k.mp4")
            ff("-f", "lavfi", "-i", "sine=f=200:r=24000:d=1.5", t / "k.wav")
            cl.render_short(t / "short.mp4", t / "s.mp4")
            cl.render_short(t / "short.mp4", t / "c.mp4", None, ("PART 1 OF 4", "Enoch Walked With God", "Genesis 5:21-24 (KJV)"))
            cl.render_keeper(t / "k.mp4", t / "k.wav", t / "h.mp4")
            for f, secs in (("s.mp4", 3.0), ("c.mp4", 3.0), ("h.mp4", 2.0 + 2 * cl.BEAT)):
                p = json.loads(cl.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                       "stream=width,height", "-of", "json", t / f]).stdout)["streams"][0]
                self.assertEqual((p["width"], p["height"]), (1920, 1080), f)
                self.assertAlmostEqual(cl.duration(t / f), secs, delta=0.15, msg=f)
            lufs, peak = cl.loudness(t / "s.mp4")
            self.assertTrue(cl.LUFS_BAND[0] <= lufs <= cl.LUFS_BAND[1] + 1.0, lufs)   # fades lower the mean a little
            self.assertLessEqual(peak, cl.TRUE_PEAK_MAX)   # E251: -0.8 dBTP after AAC failed the first real build
            self.assertEqual(cl.fps("30000/1001") > 29.9, True)
            self.assertAlmostEqual(cl.fps("30/1"), 30.0)
            self.assertLess(abs(cl.fps("295249920/9864919") - cl.FPS), cl.FPS_TOLERANCE)   # the real master's average
            # the Keeper clip: still beat of silence at the head (the line starts after BEAT)
            head = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-t", "0.4", "-i", t / "h.mp4", "-af", "volumedetect",
                           "-f", "null", "-"]).stderr
            self.assertIn("max_volume: -91", head)


@unittest.skipUnless(FFMPEG, "ffmpeg")
class CardTests(unittest.TestCase):
    def test_e258_the_chapter_card_is_drawn_over_its_short_not_dead_air(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            ff("-f", "lavfi", "-i", "testsrc=s=270x480:r=30:d=4", "-f", "lavfi", "-i", "sine=f=300:r=44100:d=4",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", t / "short.mp4")
            cl.render_short(t / "short.mp4", t / "c.mp4", None, ("PART 1 OF 4", "Enoch Walked With God", "Genesis 5:21-24 (KJV)"))
            log = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", t / "c.mp4", "-vf", "blackdetect=d=0.1:pic_th=0.98",
                          "-af", "silencedetect=n=-60dB:d=0.5", "-f", "null", "-"]).stderr
            self.assertNotIn("black_start", log)
            self.assertNotIn("silence_start", log)
        self.assertFalse(hasattr(cl, "render_card"))
        plan = cl.load(PLAN)
        segs = cl.script_segments(plan)
        self.assertEqual([s["kind"] for s in segs], ["hook"] + ["short"] * len(plan["chapters"]) + ["close"])
        self.assertTrue(all(s["text"].strip() for s in segs))


GENESIS = ROOT / "migration/production/bible/compilations/genesis-part1-compilation.json"


class OriginalKeeperV2Tests(unittest.TestCase):
    """E306 (owner 2026-11-05: "sempre tem que promover coisas novas"; YPP refuses reused content): a v2 compilation
    carries new Keeper interludes; every quoted line is the KJV of its reference; the new share is measured."""

    def test_e306_the_genesis_part1_plan_is_accepted_and_adds_new_keeper_segments(self):
        plan = cl.load(GENESIS)
        self.assertEqual(cl.plan_problems(plan), [])
        self.assertEqual(plan["criteria"], cl.CRITERIA_V2)
        self.assertEqual([cl.chapter_id(c) for c in plan["chapters"]],
                         [f"genesis-0{n}-short" for n in range(2, 10)] + ["flood-ends-long", "genesis-10-11-long"])
        self.assertNotIn("genesis-01-short", json.dumps(plan["chapters"]))   # its review: a skier, a car, an aquarium
        self.assertNotIn("FULL MOVIE", plan["title"].upper())                # honest packaging: Shorts and stills
        self.assertEqual([it["after"] for it in plan["interludes"]], [0, 3, 4, 8, 9])
        words = sum(len(b["text"].split()) for _, k in cl.keeper_sections(plan) for b in k["beats"])
        self.assertGreater(words, 1000)   # minutes of new commentary, not a token line
        self.assertTrue(cl.has_voiceover(plan))
        ids = [s["id"] for s in self._voice_script(plan)]
        self.assertEqual(ids[:2], ["hook-01", "hook-02"])
        self.assertEqual(ids[-1], "close-04")
        self.assertEqual(len(ids), len(set(ids)))

    def _voice_script(self, plan):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "plan.json"
            f.write_text(json.dumps(plan))
            cl.voice_script(f, d)
            return cl.load(Path(d) / "voice-script.json")["segments"]

    def test_e306_refusals(self):
        plan = cl.load(GENESIS)
        cases = (
            (lambda p: p.update(criteria=cl.CRITERIA), "need compilation-qa-criteria-v2"),
            (lambda p: p.update(criteria="compilation-qa-criteria-v9"), "unknown criteria"),
            (lambda p: p["interludes"][1]["beats"][0].update(text=p["interludes"][1]["beats"][0]["text"].replace("enmity", "hatred")),
             "KJV_TEXT_MISMATCH"),
            (lambda p: p["interludes"][0]["beats"][0].update(reference="Genesis 1:1-5"), "KJV_VERSE_NOT_QUOTED"),
            (lambda p: p["interludes"][0]["beats"][1]["still"].update(sha256="0" * 64), "still missing or changed"),
            (lambda p: p["interludes"][0]["beats"][1]["still"].update(approved_still="arc-01-long-k-close-1"), "not an approved still"),
            (lambda p: p["hook"]["beats"][0].update(motion="zoom"), "motion must be"),
            (lambda p: p["close"].pop("lipsync"), "lipsync record"),
            (lambda p: p["close"].update(voice={"voice_id": "af_heart", "speed": 1.0}), "pinned voice"),
            (lambda p: p["close"].update(quote="2 credits"), "zero-credit"),
            (lambda p: p["interludes"][2].update(after=3), "increasing"),
            (lambda p: p["interludes"][-1].update(after=len(p["chapters"])), "increasing"),
            (lambda p: p["interludes"][0].pop("title"), "title and reference"),
            (lambda p: p["hook"].update(beats=[]), "beats"),
            (lambda p: p["chapters"][-1]["subchapters"].reverse(), "subchapters"),
            (lambda p: p["chapters"][-1]["subchapters"][-1].update(at=480), "subchapters"),
            (lambda p: p.update(hook=cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")["hook"]),
             "hook and close need beats"),
        )
        for mutate, text in cases:
            bad = copy.deepcopy(plan)
            mutate(bad)
            self.assertTrue(any(text in x for x in cl.plan_problems(bad)), text)
        v1 = cl.load(ROOT / "migration/production/bible/compilations/arc-02-noah-complete-compilation.json")
        self.assertEqual(cl.plan_problems(v1), [])          # v1 plans are unchanged
        self.assertNotIn("criteria", v1)

    def test_e306_description_has_interludes_and_inner_chapters_every_few_minutes(self):
        plan = cl.load(GENESIS)
        segs, t = [], 0.0
        kinds = ["hook", "interlude"] + ["short"] * 3 + ["interlude", "short", "interlude"] + ["short"] * 4 + ["interlude", "long",
                                                                                                             "interlude", "long", "close"]
        lens = {"hook": 34.0, "interlude": 80.0, "short": 100.0, "long": 480.0, "close": 94.0}
        titles = iter(it["title"] for it in plan["interludes"])
        for k in kinds:
            segs.append({"kind": k, "start": t, "end": t + lens[k], "seconds": lens[k],
                         **({"chapter": next(titles)} if k == "interlude" else {})})
            t += lens[k]
        text, rows = cl.description(plan, {"segments": segs})
        names = [r[1] for r in rows]
        self.assertEqual(names[0], plan["chapter_zero"])
        self.assertEqual(names[1], "In the Beginning")
        self.assertIn("Out of the Ark", names)
        self.assertEqual(names[-1], plan["chapter_last"])
        gaps = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
        self.assertTrue(all(10 <= g <= 330 for g in gaps), gaps)   # YouTube's 10 s rule; a timestamp at least every ~5 min
        self.assertIn("about 37 minutes", text)
        self.assertNotIn("{", text)
        self.assertIn("https://www.youtube.com/watch?v=KwFjnZ20yGA", text)

    def test_e306_frozen_v2_criteria_and_its_gate_track(self):
        self.assertEqual(pg.sha256_file(pg.CRITERIA_FILES[pg.COMPILATION_V2]), pg.FROZEN_CRITERIA_SHA256[pg.COMPILATION_V2])
        self.assertEqual(pg.sha256_file(pg.CRITERIA_FILES[pg.COMPILATION]), pg.FROZEN_CRITERIA_SHA256[pg.COMPILATION])
        archetype, dims, track = pg.DEFECT_TRACKS[pg.COMPILATION_V2]
        self.assertEqual((archetype, track), (pg.COMPILATION_ARCHETYPE, "compilation"))
        self.assertEqual(dims["originality"], ["original_keeper_share"])
        self.assertNotIn(pg.COMPILATION_V2, pg.STANDARD_VERSIONS)
        crit = json.loads(pg.CRITERIA_FILES[pg.COMPILATION_V2].read_text())
        self.assertEqual(crit["technical"]["original_keeper_share_min"], cl.ORIGINAL_SHARE_MIN)
        self.assertEqual(set(crit["rows"]), {n for v in dims.values() for n in v})
        for v in (cl.CRITERIA, cl.CRITERIA_V2):
            self.assertEqual(ROOT / cl.CRITERIA_FILES[v], pg.CRITERIA_FILES[v])

    @unittest.skipUnless(FFMPEG, "ffmpeg")
    def test_e306_a_beat_moves_for_its_whole_length_and_qa_measures_the_new_share(self):
        plan = cl.load(GENESIS)
        k = {"beats": [plan["hook"]["beats"][0], plan["close"]["beats"][1]]}
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for i in cl.beat_ids("hook", k):
                ff("-f", "lavfi", "-i", "sine=f=220:r=24000:d=6", t / f"{i}.wav")
            out = t / "hook.mp4"
            spoken, beats = cl.render_beats("hook", k, t, out, ("THE KEEPER", "In the Beginning", "Genesis 1 (KJV)"))
            self.assertEqual(beats, 2)
            self.assertAlmostEqual(spoken, 12.0, delta=0.1)
            self.assertAlmostEqual(cl.duration(out), spoken + 2 * 2 * cl.BEAT, delta=0.25)
            log = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", out, "-vf", "scale=320:180,freezedetect=n=0.001:d=2",
                          "-f", "null", "-"]).stderr
            self.assertNotIn("freeze_start", log)   # the camera move lasts the whole beat (no still hold after it ends)

    def test_e306_v2_qa_rows(self):
        plan = cl.load(GENESIS)
        src = [{"short": cid, "sha256": "a" * 64, "seconds": 1.0} for cid in map(cl.chapter_id, plan["chapters"])]
        segs, order = [], ["hook", "interlude"] + ["short"] * 3 + ["interlude", "short", "interlude"] + ["short"] * 4 + [
            "interlude", "long", "interlude", "long", "close"]
        ch = iter(plan["chapters"])
        for k in order:
            if k in ("short", "long"):
                c = next(ch)
                segs.append({"kind": k, "name": cl.chapter_id(c), "seconds": 1.0, "end_s": c["end_s"],
                             "source_sha256": "a" * 64, "chapter": c["title"]})
            else:
                segs.append({"kind": k, "name": k, "seconds": 1.4, "spoken_seconds": 0.5, "beats": 1})
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            master = t / f"{plan['id']}.mp4"
            total = sum(s["seconds"] for s in segs)
            ff("-f", "lavfi", "-i", f"color=s=1920x1080:r=30:d={total}", "-f", "lavfi", "-i", f"sine=f=300:r=48000:d={total}",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-af", "volume=-12dB", "-c:a", "aac", "-shortest", master)
            cl.save(t / "timeline.json", {"output_sha256": cl.sha256(master), "segments": segs})
            cl.save(t / "sources.json", src)
            f = t / "plan.json"
            f.write_text(json.dumps(plan))
            cl.qa(f, t)
            qa = cl.load(t / "qa.json")
            self.assertEqual(qa["criteria_version"], cl.CRITERIA_V2)
            self.assertTrue(qa["checks"]["canonical_order"])
            self.assertTrue(qa["checks"]["no_padding"])
            self.assertTrue(qa["checks"]["original_keeper_share"])
            self.assertAlmostEqual(qa["measured"]["keeper_share"], 7 * 1.4 / total, delta=0.02)
            segs[1]["seconds"] = 1.9             # a Keeper segment longer than its lines and beats: padding
            cl.save(t / "timeline.json", {"output_sha256": cl.sha256(master), "segments": segs})
            cl.qa(f, t)
            self.assertFalse(cl.load(t / "qa.json")["checks"]["no_padding"])


def review_doc(**kw):
    issues = ["0:10 a caption touches the card edge", "3:00 mild AI artifact"]
    base = {"model": "claude-session-reviewer", "output_sha256": SHA, "issues": issues,
            "defects": [{"issue": 0, "category": "d", "resolved": False}, {"issue": 1, "category": "info", "resolved": False}],
            "publish_decision": {"decision": "publish", "by": "claude-session-reviewer", "note": "watched and heard it"},
            "evidence": ["watched the master", "listened to the joins"]}
    base.update(kw)
    return base


class ReviewTrackTests(unittest.TestCase):
    def test_defect_gate_rules(self):
        self.assertEqual(oq.compilation_problems(review_doc(), SHA), [])   # a score floor is not part of this track
        bad = review_doc(defects=[{"issue": 0, "category": "a", "resolved": False}, {"issue": 1, "category": "info", "resolved": False}])
        self.assertIn("REVIEW_DEFECT_UNRESOLVED", oq.compilation_problems(bad, SHA))
        ok = review_doc(defects=[{"issue": 0, "category": "b", "resolved": True}, {"issue": 1, "category": "info", "resolved": False}])
        self.assertEqual(oq.compilation_problems(ok, SHA), [])
        for kw, code in ((dict(model="gemini-3.8-flash"), "REVIEW_MODEL_NOT_DESIGNATED"),
                         (dict(output_sha256="b" * 64), "REVIEW_NOT_FOR_THIS_FILE"),
                         (dict(publish_decision={"decision": "hold", "by": "claude-session-reviewer", "note": "x"}), "REVIEW_DECISION_MISSING"),
                         (dict(defects=[{"issue": 0, "category": "d", "resolved": True}]), "REVIEW_DEFECTS_INVALID")):
            self.assertIn(code, oq.compilation_problems(review_doc(**kw), SHA))

    def pilot(self, root, review=None):
        d = Path(root) / "pilot-016"
        (d / "out").mkdir(parents=True)
        (d / "inspection").mkdir()
        (d / "script.json").write_text(json.dumps({"pilot_id": "pilot-016", "archetype": pg.COMPILATION_ARCHETYPE}))
        (d / "out/manifest.json").write_text(json.dumps({"output_sha256": SHA, "output_seconds": 600}))
        if review is not None:
            (d / "inspection/claude_review.json").write_text(json.dumps(review))
        return d

    def test_long_review_routes_to_the_defect_gate(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.pilot(t)
            lr.main(str(d))
            self.assertEqual(json.loads((d / "out/review.json").read_text())["status"], "AWAITING_REVIEW")
            d = self.pilot(t + "/x", review_doc())
            lr.main(str(d))
            r = json.loads((d / "out/review.json").read_text())
            self.assertEqual((r["status"], r["track"]), ("PASS", "compilation"))
            self.assertEqual(oq.compilation_problems({**r["watched_review"], "output_sha256": SHA}, SHA), [])

    def gate_items(self, review):
        return {i["item"]: i["state"] for i in pg.compilation_review_items(review, SHA)}

    def test_gate_review_items(self):
        self.assertEqual(set(self.gate_items(None).values()), {"UNKNOWN"})
        passed = {"status": "PASS", "output_sha256": SHA, "watched_review": {k: v for k, v in review_doc().items() if k != "output_sha256"}}
        self.assertEqual(set(self.gate_items(passed).values()), {"PASS"})
        unresolved = copy.deepcopy(passed)
        unresolved["watched_review"]["defects"][0] = {"issue": 0, "category": "e", "resolved": False}
        self.assertEqual(self.gate_items(unresolved)["no_unresolved_a_b_e"], "FAIL")

    def test_other_tracks_are_unchanged(self):
        self.assertNotIn(pg.COMPILATION, pg.STANDARD_VERSIONS)
        self.assertIn(pg.STORY_V5, pg.STANDARD_VERSIONS)
        self.assertEqual(pg.score_hard_keys(pg.STORY_V5), ("minutes",))
        self.assertTrue(oq.check({"status": "PASS", "model": "claude-session-reviewer", "overall": 9.4,
                                  "output_sha256": SHA}, SHA, oq.LONG_REVIEWERS))   # the 9.5 floor still refuses

    def test_frozen_criteria_hash(self):
        self.assertEqual(pg.sha256_file(pg.CRITERIA_FILES[pg.COMPILATION]), pg.FROZEN_CRITERIA_SHA256[pg.COMPILATION])


class PavoOwnAudioRoute(unittest.TestCase):
    """Owner 2026-11-03: a Keeper clip is used in full with Pavo's own audio unless the key says otherwise."""
    def test_the_route_is_explicit_then_the_plan_then_the_recorded_remux_then_the_old_plans_then_pavo(self):
        key = {}
        self.assertEqual(cl.key_route({"id": "new"}, key), "pavo")
        self.assertEqual(cl.key_route({"id": "arc-02-noah-compilation"}, key), "ours")      # built before: its digests hold
        self.assertEqual(cl.key_route({"id": "new"}, {"remux": {"audio_route": "ours"}}), "ours")
        self.assertEqual(cl.key_route({"id": "new", "pavo_audio": "ours"}, key), "ours")
        self.assertEqual(cl.key_route({"id": "arc-02-noah-compilation"}, {"pavo_audio": "pavo"}), "pavo")
        self.assertEqual(cl.key_route({"id": "new", "pavo_audio": "ours"}, {"pavo_audio": "pavo"}), "pavo")
        with self.assertRaisesRegex(SystemExit, "PAVO_AUDIO_ROUTE_INVALID"):
            cl.key_route({"id": "new"}, {"pavo_audio": "theirs"})
        for name in ("arc-02-noah-compilation", "arc-02-noah-complete-compilation"):
            plan = cl.load(HERE / "compilations" / f"{name}.json")
            self.assertEqual({cl.key_route(plan, plan[k]) for k in ("hook", "close")}, {"ours"})

    @unittest.skipUnless(FFMPEG, "ffmpeg required")
    def test_the_pavo_route_plays_the_whole_clip_with_its_own_track_and_trims_only_when_set(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=4", "-f", "lavfi", "-i", "sine=f=500:r=48000:d=4",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", t / "pavo.mp4")
            ff("-f", "lavfi", "-i", "sine=f=200:r=24000:d=1.5", t / "k.wav")
            cl.render_keeper(t / "pavo.mp4", t / "k.wav", t / "full.mp4", None, "pavo")
            cl.render_keeper(t / "pavo.mp4", t / "k.wav", t / "cut.mp4", 3.0, "pavo")
            self.assertAlmostEqual(cl.duration(t / "full.mp4"), 4.0 + 2 * cl.BEAT, delta=0.15)   # in full, a still beat each end
            self.assertAlmostEqual(cl.duration(t / "cut.mp4"), 3.0 + cl.BEAT, delta=0.15)        # trimmed only when explicit
            lufs, peak = cl.loudness(t / "full.mp4")
            self.assertTrue(cl.LUFS_BAND[0] - 1.5 <= lufs <= cl.LUFS_BAND[1] + 1.0, lufs)         # the same gain as every segment
            self.assertLessEqual(peak, cl.TRUE_PEAK_MAX)


if __name__ == "__main__":
    unittest.main()
