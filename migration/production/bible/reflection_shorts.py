#!/usr/bin/env python3
"""The Keeper reflection split-screen Short (owner, 2026-11-02, DECISIONS.md "Shorts cadence": one a day).

About 30 s (20-40 s), 9:16 1080x1920, two halves of 1080x960:
  TOP     a moment of one of our own published longs, from the long's caption-free master, re-framed to fill, with
          its own audio ducked under the reflection (or muted);
  BOTTOM  an approved Keeper still (stills/<id>.json, shot k-*) moved by the cinematic engine (motion.py), while the
          Keeper's reflection on that moment is spoken in the pinned Kokoro voice (am_michael: episode_build.VOICE,
          the long's Keeper) and captioned in the series style.
No Pavo, no Buzzy, no paid tool: zero credits. Only the reflection is ours; the KJV is quoted only when the spec shows
it (`verse`, checked word for word by kjv_check). A spec (migration/production/bible/reflections/<long>-<n>.json,
bible-reflection-v1) names the long (published, by its master's sha256 in the publication ledger), the sentence-safe
clip, the reflection, the Keeper still, the title and the pinned comment that points to the long.

Its record (episodes/<id>.json, track keeper-reflection, `parent` = its long) carries no review. It is reviewed on its
own master at the standard Short floor (native-review.yml with plan = the spec, then the session reviewer's review in
the record); publish_episode.py applies the same rules at check-record and at the upload. Nothing is generated,
reviewed or published here.

usage: reflection_shorts.py check SPEC                       the spec against the long, the ledger and the still
       reflection_shorts.py voice-script SPEC OUT.json        the voice script pilot_render.py voice reads
       reflection_shorts.py render SPEC CLEAN_MASTER WORK OUT  WORK holds voice.wav and timeline.json; OUT/<id>.mp4/.json
       reflection_shorts.py record SPEC SHORT_JSON            a draft episodes/<id>.json (no review)
"""
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "migration" / "publish"))
sys.path.insert(0, str(ROOT / "migration" / "production"))
import buzzy_long  # noqa: E402
import compilation_long as cl  # noqa: E402
import kjv_check  # noqa: E402
import publish_episode as pe  # noqa: E402
import short_cuts  # noqa: E402
import short_engine  # noqa: E402

VERSION = "bible-reflection-v1"
TRACK = pe.REFLECTION_TRACK
LAYOUT = "keeper-reflection"
SPEC_PATH = re.compile(r"^migration/production/bible/reflections/([a-z0-9]+(?:-[a-z0-9]+)*)-([1-9][0-9]*)\.json$")
SLUG = short_cuts.SLUG
SECONDS = pe.REFLECTION_SECONDS    # 20-40 s: the clip's length is the Short's
WORDS = pe.REFLECTION_WORDS        # 20-80 words
WPM = 140                          # Kokoro narration measured on pilots 002-004 (script_check.WPM)
WPM_BAND = (115, 165)              # the accepted words-per-minute band of the narration (QA)
LEAD_IN = 0.3                      # pilot_render.LEAD_IN: silence at the head of voice.wav
SENTENCE_GAP = 0.18                # pilot_render.SENTENCE_GAP
VOICE_AT = 0.3                     # the voice starts this long after the clip: its first word at VOICE_AT + LEAD_IN
TAIL_MIN = 0.6                     # silence the Short keeps after the last word
FILL_MIN = 0.45                    # the voice fills at least this share of the clip (no dead air)
HALF = (short_engine.W, short_engine.H // 2)   # each half: 1080x960
DUCK = ("duck", "mute")
BANNED = re.compile(r"(?i)\b(shocking|they don'?t want you to know)\b")   # brand-profile.md "Words we ban"
STILLS = Path("migration/production/bible/stills")
SERIES = short_cuts.SERIES
CAPTION_STYLE = {"words": 3, "font": 92, "margin": 330, "scr": 60, "ref": 44, "ref_margin": 960,
                 "w": short_engine.W, "h": short_engine.H}   # bottom half, clear of the Shorts UI


def speech_sentences(text):
    """pilot_render.sentences: how the voice splits the text."""
    return [s.strip() for s in re.split(r"(?<=[.!?:;])\s+", text) if s.strip()]


def estimate(text):
    """(words, seconds the voice needs at the nominal pace, inside the Short from its start)."""
    words = len(text.split())
    gaps = SENTENCE_GAP * len(speech_sentences(text))
    return words, VOICE_AT + LEAD_IN + words / WPM * 60 + gaps


def long_video_id(spec, report, root=ROOT):
    """The video id of the exact master of this long in the publication ledger, or None."""
    ledger = cl.load(Path(root) / "migration/publish/ledger.json")
    entry = (ledger.get("entries") or {}).get(f"{spec.get('pilot')}:{report['composed']['output_sha256']}") or {}
    return entry.get("video_id") or None


def still_problems(still_id, root=ROOT):
    """The Keeper image: an APPROVED still of a Keeper shot (k-*), its file the approved bytes."""
    if not isinstance(still_id, str) or not SLUG.fullmatch(still_id):
        return ["KEEPER_IMAGE_ID"], None
    path = Path(root) / STILLS / f"{still_id}.json"
    try:
        rec = cl.load(path)
    except (OSError, ValueError):
        return [f"KEEPER_IMAGE_UNKNOWN {still_id}"], None
    img = Path(root) / str(rec.get("repo_path") or "")
    bad = []
    if rec.get("status") != "APPROVED" or not (rec.get("approved") or {}).get("score"):
        bad.append(f"KEEPER_IMAGE_NOT_APPROVED {still_id}")
    if not str(rec.get("shot") or "").startswith("k-"):
        bad.append(f"KEEPER_IMAGE_NOT_THE_KEEPER {still_id} (an approved still of a Keeper shot, k-*)")
    if Path(root).resolve() not in img.resolve().parents or not img.is_file():
        bad.append(f"KEEPER_IMAGE_FILE_MISSING {still_id}")
    elif cl.sha256(img) != rec.get("sha256"):
        bad.append(f"KEEPER_IMAGE_SHA256_MISMATCH {still_id}")
    return bad, (rec, img)


def check(spec, root=ROOT, spec_path=None):
    """{"problems": [...], "reflection": {...}} of one reflection spec."""
    bad, out = [], {}
    n = None
    if spec_path is not None:
        m = SPEC_PATH.fullmatch(spec_path)
        if not m or m.group(1) != spec.get("long") or spec.get("id") != f"{m.group(1)}-reflection-{m.group(2)}":
            bad.append("SPEC_PATH (reflections/<long>-<n>.json, id <long>-reflection-<n>)")
    if spec.get("version") != VERSION or spec.get("track") != TRACK or spec.get("layout") != LAYOUT:
        return {"problems": bad + [f"SPEC_VERSION (need {VERSION}, track {TRACK}, layout {LAYOUT})"], "reflection": out}
    for k in ("id", "long"):
        if not isinstance(spec.get(k), str) or not SLUG.fullmatch(spec[k]):
            return {"problems": bad + [f"SPEC_{k.upper()}"], "reflection": out}
    if spec["id"] == spec["long"]:
        return {"problems": bad + ["SPEC_ID (a new episode id)"], "reflection": out}
    report_re = rf"migration/evidence/episodes/{re.escape(spec['long'])}/report-[0-9]+\.json"
    if not isinstance(spec.get("report"), str) or not re.fullmatch(report_re, spec["report"]):
        return {"problems": bad + ["REPORT_PATH (the long's build report on main)"], "reflection": out}
    try:
        plan, report = short_cuts.sources(spec, root)
    except (OSError, ValueError) as exc:
        return {"problems": bad + [f"LONG_UNREADABLE {type(exc).__name__}"], "reflection": out}
    if not buzzy_long.long_first(plan):
        bad.append("LONG_NOT_LONG_FIRST (the plan's track is not buzzy-long)")
    bad += [f"REPORT {p}" for p in buzzy_long.report_problems(plan, report)]
    if (plan.get("long") or {}).get("pilot") != spec.get("pilot"):
        bad.append("PILOT (the spec's pilot is the long's)")
    if bad:
        return {"problems": bad, "reflection": out}
    try:
        video = long_video_id(spec, report, root)
    except (OSError, ValueError):
        video = None
    if not video:
        bad.append("LONG_NOT_PUBLISHED (no ledger entry <pilot>:<master sha256> with a video id: the clip comes from "
                   "an approved, published long)")
    # the clip: its sentences whole, 20-40 s
    clip = spec.get("clip") if isinstance(spec.get("clip"), dict) else {}
    start, end = clip.get("start"), clip.get("end")
    sentences = report["composed"]["sentences"]
    total = report["composed"]["seconds"]
    d = None
    if type(start) not in (int, float) or type(end) not in (int, float) or not 0 <= start < end <= total:
        bad.append(f"CLIP_RANGE (0 <= start < end <= {total})")
    else:
        d = end - start
        if not SECONDS[0] <= d <= SECONDS[1]:
            bad.append(f"CLIP_LENGTH {d:.2f} s ({SECONDS[0]:.0f}-{SECONDS[1]:.0f})")
        found, first, last = short_cuts.boundaries(sentences, start, end, total)
        bad += [f"CLIP_{p[4:]}" for p in found]
        if not found:
            out.update(first=first, last=last)
    x = clip.get("x", 0.5)
    if type(x) not in (int, float) or not 0.0 <= x <= 1.0:
        bad.append("CLIP_X (0-1, the window's centre across the frame)")
    if clip.get("audio", "duck") not in DUCK:
        bad.append(f"CLIP_AUDIO ({', '.join(DUCK)})")
    # the reflection: ours, 20-80 words, whole sentences, a voice that fits the clip
    text = (spec.get("reflection") or {}).get("text") if isinstance(spec.get("reflection"), dict) else None
    if not isinstance(text, str) or not text.strip():
        bad.append("REFLECTION_MISSING")
    else:
        words, need = estimate(text)
        out.update(words=words, voice_estimate=round(need, 2))
        if not WORDS[0] <= words <= WORDS[1]:
            bad.append(f"REFLECTION_LENGTH {words} words ({WORDS[0]}-{WORDS[1]})")
        if not text.strip()[-1] in ".!?":
            bad.append("REFLECTION_NOT_A_SENTENCE (ends on . ! or ?)")
        if BANNED.search(text):
            bad.append("REFLECTION_BANNED_WORDS (brand-profile.md)")
        if d is not None:
            if need + TAIL_MIN > d:
                bad.append(f"REFLECTION_TOO_LONG_FOR_CLIP {need:.1f} s of voice in {d:.1f} s (a {TAIL_MIN} s tail)")
            if (need - VOICE_AT - LEAD_IN) < FILL_MIN * d:
                bad.append(f"REFLECTION_TOO_SHORT_FOR_CLIP {need - VOICE_AT - LEAD_IN:.1f} s of voice in {d:.1f} s")
    # the verse, only if it is shown, exactly
    verse = spec.get("verse")
    if verse is not None:
        ok = (isinstance(verse, dict) and isinstance(verse.get("reference"), str) and isinstance(verse.get("text"), str)
              and type(verse.get("start")) in (int, float) and type(verse.get("end")) in (int, float)
              and 0 <= verse["start"] < verse["end"] and (d is None or verse["end"] <= d))
        if not ok:
            bad.append("VERSE_INVALID (reference, text, start < end inside the Short)")
        else:
            why = kjv_check.problem(verse["reference"], verse["text"])
            if why:
                bad.append(f"VERSE_NOT_KJV {why}")
    # the Keeper image and its motion
    found, got = still_problems(spec.get("keeper_image"), root)
    bad += found
    if spec.get("motion") is not None:
        import motion
        bad += motion.override_problems(spec["motion"])
    # the package
    for k in ("title", "description", "first_comment"):
        if not isinstance(spec.get(k), str) or not spec[k].strip():
            bad.append(f"{k.upper()}_MISSING")
    if isinstance(spec.get("title"), str) and not 0 < len(spec["title"]) <= pe.TITLE_MAX:
        bad.append("TITLE_LENGTH")
    if isinstance(spec.get("description"), str):
        bad += pe.description_problems(spec["description"])
        if not pe.CTA_TO_LONG.search(spec["description"]):
            bad.append("DESCRIPTION_NOT_TO_THE_LONG (it sends the viewer to the full story)")
    if video and isinstance(spec.get("first_comment"), str) and f"youtu.be/{video}" not in spec["first_comment"]:
        bad.append(f"FIRST_COMMENT_NOT_TO_THE_LONG (the pinned comment holds https://youtu.be/{video})")
    out.update(seconds=round(d, 3) if d is not None else None, long_video_id=video)
    return {"problems": bad, "reflection": out}


def voice_script(spec):
    """The voice script pilot_render.py voice reads: the reflection in the Keeper's pinned voice (episode_build.VOICE)."""
    import episode_build as eb
    return {"voice": dict(eb.VOICE), "segments": [{"id": "r00", "text": spec["reflection"]["text"].strip(),
                                                   "pause_after": 0.0}]}


def window(x, w=HALF[0], h=HALF[1]):
    """The top half's crop of a 16:9 frame: w:h of the full height, its centre at x of the width, then scaled to fill."""
    return (f"crop=ih*{w}/{h}:ih:(iw-ih*{w}/{h})*{min(max(float(x), 0.0), 1.0):.4f}:0,"
            f"scale={w}:{h}:flags=lanczos,setsar=1")


def captions(spec, lines):
    """ASS: the reflection's captions (bottom half) and, only when the spec shows it, the exact KJV verse (top)."""
    text = short_engine.build_ass(lines, dict(CAPTION_STYLE))
    verse = spec.get("verse")
    if verse:
        body = re.sub(r"[{}\\]", "", verse["text"])
        ref = short_engine.citation(verse["reference"])
        text += (f"Dialogue: 2,{short_engine.ass_time(verse['start'])},{short_engine.ass_time(verse['end'])},Scr,,60,60,"
                 f"1040,,{{\\an2\\fs50\\q0}}{body}\\N{{\\fs40\\i0}}{ref}\n")
    return text


def render(spec_path, clean, work, out_dir, root=ROOT):
    spec = cl.load(spec_path)
    result = check(spec, root)
    cl.refuse(result["problems"])
    plan, report = short_cuts.sources(spec, root)
    want = report["composed"]["clean"]["output_sha256"]
    if cl.sha256(clean) != want:
        raise SystemExit("CLEAN_MASTER_SHA256_MISMATCH")
    work, out = Path(work), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    voice, timeline = work / "voice.wav", cl.load(work / "timeline.json")
    spoken = timeline["sentences"]
    if not voice.is_file() or not spoken or timeline.get("voice_id") != "am_michael":
        raise SystemExit("VOICE_TRACK_MISSING (pilot_render.py voice with the pinned voice am_michael)")
    start, end = float(spec["clip"]["start"]), float(spec["clip"]["end"])
    d = end - start
    first_word, last_word = spoken[0]["start"] + VOICE_AT, spoken[-1]["end"] + VOICE_AT
    speech = last_word - first_word
    wpm = result["reflection"]["words"] / speech * 60
    if last_word + TAIL_MIN > d:
        raise SystemExit(f"VOICE_TOO_LONG_FOR_CLIP {last_word:.2f} s of voice in {d:.2f} s")
    if not WPM_BAND[0] <= wpm <= WPM_BAND[1]:
        raise SystemExit(f"VOICE_PACE {wpm:.0f} wpm ({WPM_BAND[0]}-{WPM_BAND[1]})")
    still_found, (still, img) = still_problems(spec["keeper_image"], root)
    cl.refuse(still_found)
    import motion
    frame = HALF
    an = motion.analyse_still(img, frame)
    direction = motion.decide({"id": still["id"], "prompt": still.get("prompt", ""), "motion": spec.get("motion"),
                               "atmosphere": ["film_grain", "vignette"]}, "keeper", 0.5, motion.mood_of(still.get("prompt", "")),
                              d, an, [], frame)
    lines = [dict(s, start=round(s["start"] + VOICE_AT, 3), end=round(s["end"] + VOICE_AT, 3)) for s in spoken]
    mp4 = out / f"{spec['id']}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        keeper = tmp / "keeper.mp4"
        motion.render_direction(img, keeper, d, direction, frame=frame)
        seg = tmp / "segment.mov"   # the exact range, re-encoded (frame-accurate), audio kept lossless
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", clean, "-t", f"{d:.3f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", "-ar", "48000", seg])
        ass = tmp / "captions.ass"
        ass.write_text(captions(spec, lines))
        # audio: the Keeper's voice, and the clip's own sound ducked under it (or muted); gain only to -14 LUFS after
        voice_chain = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(VOICE_AT * 1000)}|{int(VOICE_AT * 1000)},"
                       f"apad=whole_dur={d:.3f}")
        if spec["clip"].get("audio", "duck") == "mute":
            mix = f"{voice_chain}[mix]"
        else:
            mix = (f"{voice_chain},asplit[v1][v2];[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=-6dB[o];"
                   f"[o][v1]sidechaincompress=threshold=0.01:ratio=12:attack=15:release=400:makeup=1[od];"
                   f"[od][v2]amix=inputs=2:normalize=0:duration=longest[mix]")
        premix = tmp / "mix.wav"
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", seg, "-i", voice, "-filter_complex", mix, "-map", "[mix]",
                "-t", f"{d:.3f}", "-c:a", "pcm_s16le", premix])
        v, a = cl.fades(d)
        graph = (f"[0:v]{window(spec['clip'].get('x', 0.5))}[top];[1:v]scale={HALF[0]}:{HALF[1]},setsar=1[bot];"
                 f"[top][bot]vstack=inputs=2,subtitles={ass},{v}[v];"
                 f"[2:a]{cl.gain_filter(premix)},{a}[a]")
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", seg, "-i", keeper, "-i", premix, "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", *cl.ENC, mp4])
    lufs, peak = cl.loudness(mp4)
    probe = short_cuts.short_engine_probe(mp4)
    rec = {"version": "bible-reflection-short-v1", "id": spec["id"], "spec": str(spec_path),
           "parent": {"long": spec["long"], "pilot": spec["pilot"], "report": spec["report"],
                      "clean_master_sha256": want, "start": start, "end": end, "x": spec["clip"].get("x", 0.5),
                      "video_id": result["reflection"]["long_video_id"]},
           "keeper_image": {"id": still["id"], "sha256": still["sha256"]},
           "motion_direction": {k: direction[k] for k in ("move", "source", "ease", "strength", "atmosphere", "reason", "depth")},
           "voice": {"voice_id": timeline["voice_id"], "speed": timeline.get("speed"), "words": result["reflection"]["words"],
                     "first_word": round(first_word, 3), "last_word": round(last_word, 3), "wpm": round(wpm, 1)},
           "output_sha256": cl.sha256(mp4), "seconds": round(cl.duration(mp4), 3), "frame": [probe[0], probe[1]],
           "lufs": lufs, "true_peak_dbfs": peak, "sentences": lines,
           "checks": {"frame_1080x1920": probe == (short_engine.W, short_engine.H),
                      "lufs_band": cl.LUFS_BAND[0] <= lufs <= cl.LUFS_BAND[1], "true_peak_ceiling": peak <= cl.TRUE_PEAK_MAX,
                      "length": abs(cl.duration(mp4) - d) < 0.2 and SECONDS[0] <= cl.duration(mp4) <= SECONDS[1],
                      "voice_fits": last_word + TAIL_MIN <= d, "voice_pace": WPM_BAND[0] <= wpm <= WPM_BAND[1]}}
    cl.save(out / f"{spec['id']}.json", rec)
    print(json.dumps({k: rec[k] for k in ("id", "output_sha256", "seconds", "lufs")}, indent=1))
    if not all(rec["checks"].values()):
        raise SystemExit(f"REFLECTION_QA_FAILED {spec['id']} {rec['checks']}")
    return rec


def record(spec_path, short_json, root=ROOT):
    """A draft Short episode record of a rendered reflection (no review)."""
    spec, short = cl.load(spec_path), cl.load(short_json)
    cl.refuse(check(spec, root)["problems"])
    if short.get("id") != spec["id"] or short.get("parent", {}).get("long") != spec["long"]:
        raise SystemExit("REFLECTION_NOT_IN_SPEC")
    plan, _ = short_cuts.sources(spec, root)
    verse = spec.get("verse")
    rec = {"version": "bible-episode-v1", "id": spec["id"], "series": SERIES, "part": plan.get("part"),
           "passage": plan.get("passage"), "format": "short", "track": TRACK, "layout": LAYOUT,
           "parent": {k: short["parent"][k] for k in ("long", "pilot", "clean_master_sha256", "start", "end")},
           "keeper_image": short["keeper_image"], "output_sha256": short["output_sha256"], "seconds": short["seconds"],
           "frame": short["frame"], "narration": [{"kind": "insight", "text": spec["reflection"]["text"].strip()}],
           "scripture": [{"reference": verse["reference"], "text": verse["text"]}] if verse else [],
           "title": spec["title"], "description": spec["description"], "tags": spec.get("tags") or [], "category_id": "29",
           "first_comment": spec["first_comment"], "credits": {"vidiq": 0, "pavo": 0},
           **({"slot": spec["slot"]} if spec.get("slot") else {})}
    path = Path(root) / "migration/production/bible/episodes" / f"{spec['id']}.json"
    if path.exists() and cl.load(path).get("output_sha256") not in (None, rec["output_sha256"]):
        raise SystemExit("RECORD_EXISTS_FOR_ANOTHER_FILE (a new file is a new review; archive the old record first)")
    cl.save(path, rec)
    return path


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "check" and len(argv) == 3:
        result = check(cl.load(argv[2]), spec_path=argv[2])
        print(json.dumps(result, indent=1))
        return 1 if result["problems"] else 0
    if cmd == "voice-script" and len(argv) == 4:
        spec = cl.load(argv[2])
        cl.refuse(check(spec)["problems"])
        cl.save(argv[3], voice_script(spec))
    elif cmd == "render" and len(argv) == 6:
        render(*argv[2:6])
    elif cmd == "record" and len(argv) == 4:
        print(record(*argv[2:4]))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
