#!/usr/bin/env python3
"""The Keeper reflection split-screen Short (owner, 2026-11-02, DECISIONS.md "Shorts cadence": one a day).

About 30 s (20-40 s), 9:16 1080x1920, two halves of 1080x960:
  TOP     a moment of one of our own published longs, from the long's caption-free master, re-framed to fill, with
          its own audio ducked under the reflection (or muted);
  BOTTOM  the Keeper REALLY SPEAKING the reflection (owner rule, 02/11: a Pavo talking Keeper, never a still motion):
          2-4 sentence-safe segments, each an approved Pavo talking clip of the same machinery as a long's Keeper
          lines (plans/<id>.json, track keeper-reflection, 1:1 chest-up talking Keeper shots; shot-probe.yml keeps every
          generation, E264 two a segment, E266 hard / words / soft flags; episode_build.py approve-shot after Claude's
          review of the actual clip, shots/<id>.json). The renderer joins the approved clips in order, cropped to
          1080x960 with the face centred, with short crossfades. The audio is the clips' own: our Kokoro line (am_michael,
          the long's Keeper) that Pavo lip-synced, exactly as a long's talking shot. Captions in the series style.
No new spend and no Pavo here: the clips already exist, approved. Only the reflection is ours; the KJV is quoted only
when the spec shows it (`verse`, checked word for word by kjv_check). A spec (migration/production/bible/reflections/
<long>-<n>.json, bible-reflection-v2) names the long (published, by its master's sha256 in the publication ledger), the
sentence-safe clip, the plan and its segments (text + shot), the title and the pinned comment that points to the long.
bible-reflection-v1 (a Keeper still moved by motion.py) is retired.

Its record (episodes/<id>.json, track keeper-reflection, `parent` = its long) carries no review. It is reviewed on its
own master at the standard Short floor (local-review.yml with plan = the spec, then the session reviewer's review in
the record, who watches and hears the clips); publish_episode.py applies the same rules at check-record and at the
upload. Nothing is generated, reviewed or published here.

usage: reflection_shorts.py scaffold SPEC                     plans/<id>.json for shot-probe.yml from the spec's segments
       reflection_shorts.py check SPEC                       the spec against the long, the ledger, the plan and its approved clips
       reflection_shorts.py fetch-clips SPEC WORK             the approved clips into WORK/clips/<shot>.mp4 (sha256 checked)
       reflection_shorts.py render SPEC CLEAN_MASTER WORK OUT  WORK holds clips/; OUT/<id>.mp4/.json
       reflection_shorts.py record SPEC SHORT_JSON            a draft episodes/<id>.json (no review)
"""
import json
import math
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
import pavo_audio  # noqa: E402
import plan_check  # noqa: E402
import characters as ch  # noqa: E402  (plan_check put characters/ on the path)
import publish_episode as pe  # noqa: E402
import short_cuts  # noqa: E402
import short_engine  # noqa: E402

VERSION = "bible-reflection-v2"
RETIRED = "bible-reflection-v1"     # a Keeper still moved by motion.py: the owner rule (02/11) is the Keeper really speaking
TRACK = pe.REFLECTION_TRACK
LAYOUT = "keeper-reflection"
SPEC_PATH = re.compile(r"^migration/production/bible/reflections/([a-z0-9]+(?:-[a-z0-9]+)*)-([1-9][0-9]*)\.json$")
SLUG = short_cuts.SLUG
SECONDS = pe.REFLECTION_SECONDS    # 20-40 s: the top clip's length is the Short's
WORDS = pe.REFLECTION_WORDS        # 20-80 words
SEGMENTS = (2, 4)                  # plan_check.REFLECTION_SEGMENTS: one approved Pavo talking clip each
WPM_BAND = (115, 165)              # the accepted words-per-minute band of the narration (QA)
VOICE_AT = 0.3                     # the first clip starts this long after the top clip
XFADE = 0.2                        # the crossfade between two clips: inside the previous clip's silent tail
RETIME_TARGET = plan_check.REFLECTION_RETIME_TARGET   # E286/E289: the pace a too-fast cut set is slowed to (inside WPM_BAND);
RETIME_MIN = plan_check.REFLECTION_RETIME_MIN         # ... by at most 10 %: ONE definition, the plan is judged by it too
XFADE_MIN = 0.08                   # E282: the shortest crossfade after a TRIMMED clip (its silent tail is what the trim left)
TAIL_MIN = 0.6                     # the Short keeps this long after the last clip ends
TAIL_MAX = 3.0                     # ... and no more (the last frame is held: no long frozen face)
TAIL_CLEAR = 0.02                  # the previous clip is silent this much longer than the crossfade (no word is faded)
PAD = 0.45                         # plan_check.TALK_PAD_TARGET: a clip is this much longer than its speech
FILL_MIN = 0.45                    # the Keeper speaks at least this share of the Short (no dead air)
SILENCE_DB = -38                   # silencedetect: the clip's speech starts / ends where it leaves this floor
HALF = (short_engine.W, short_engine.H // 2)   # each half: 1080x960
CLIP_SECONDS = (4.0, 12.0)         # plan_check.TALK_CLIP: a Pavo clip
DUCK = ("duck", "mute")
BANNED = re.compile(r"(?i)\b(shocking|they don'?t want you to know)\b")   # brand-profile.md "Words we ban"
PLANS = "migration/production/bible/plans"
SHOTS = "migration/production/bible/shots"
SERIES = short_cuts.SERIES
CAPTION_STYLE = {"words": 3, "font": 92, "margin": 330, "scr": 60, "ref": 44, "ref_margin": 960,
                 "w": short_engine.W, "h": short_engine.H}   # bottom half, clear of the Shorts UI


def speech_sentences(text):
    """pilot_render.sentences: how a text splits into sentences."""
    return [s.strip() for s in re.split(r"(?<=[.!?:;])\s+", text) if s.strip()]


def reflection_text(spec):
    """The whole reflection: the segments in order."""
    return " ".join(str(s.get("text", "")).strip() for s in spec.get("segments") or [] if isinstance(s, dict))


def long_video_id(spec, report, root=ROOT):
    """The video id of the exact master of this long in the publication ledger, or None."""
    ledger = cl.load(Path(root) / "migration/publish/ledger.json")
    entry = (ledger.get("entries") or {}).get(f"{spec.get('pilot')}:{report['composed']['output_sha256']}") or {}
    return entry.get("video_id") or None


def plan_path(spec):
    return f"{PLANS}/{spec.get('id')}.json"


def segment_problems(spec, root=ROOT):
    """(problems, [approved segment, ...]): the plan of the Keeper's segments (plan_check, track keeper-reflection) and, per
    segment, the Pavo talking clip approved for it (shots/<id>.json, written by approve-shot): the plan's own text, a
    clip whose request said exactly these words, a Claude review >= 9.5 on that clip, no retraction and no hard defect.
    The automatic lip-sync / audio-match flags are informative for a talking shot (owner, 02/11): MOUTH_NOT_IN_SYNC and
    AUDIO_OFFSET never block, AUDIO_NOT_OUR_LINE blocks only without the pinned ASR's proof that the clip says the words
    (episode_build.flag_split / accepted_flags, E266); no face, a broken render or a policy problem do block."""
    import episode_build as eb
    import plan_check
    bad, out = [], []
    segs = spec.get("segments")
    low, high = SEGMENTS
    if not isinstance(segs, list) or not low <= len(segs) <= high or not all(
            isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()
            and isinstance(s.get("shot"), str) and SLUG.fullmatch(s["shot"]) for s in segs):
        return [f"SEGMENTS ({low}-{high} segments, each {{shot, text}})"], out
    if len({s["shot"] for s in segs}) != len(segs):
        return ["SEGMENTS_SHOT_REPEATED (one approved clip per segment)"], out
    if spec.get("plan") != plan_path(spec):
        return [f"PLAN_PATH ({plan_path(spec)})"], out
    try:
        plan = cl.load(Path(root) / spec["plan"])
    except (OSError, ValueError):
        return [f"PLAN_UNREADABLE {spec['plan']}"], out
    if plan.get("episode") != spec["id"] or not plan_check.reflection(plan):
        return [f"PLAN_NOT_A_REFLECTION_PLAN (episode {spec['id']}, track {plan_check.REFLECTION_TRACK})"], out
    checked = plan_check.check(plan)
    bad += [f"PLAN {p}" for p in checked["problems"]]
    shots, lines = plan.get("shots") or [], plan.get("narration") or []
    if [s.get("id") for s in shots] != [s["shot"] for s in segs] or [str(x.get("text", "")).strip() for x in lines] \
            != [s["text"].strip() for s in segs]:
        bad.append("SEGMENT_NOT_IN_PLAN (the spec's segments are the plan's shots and narration lines, word for word, "
                   "in order)")
        return bad, out
    approvals = {}
    shots_file = Path(root) / SHOTS / f"{spec['id']}.json"
    if shots_file.is_file():
        approvals = cl.load(shots_file).get("shots") or {}
    revoked = eb.revocation_problems(spec["id"], {k: v for k, v in approvals.items() if k in {s["shot"] for s in segs}},
                                     shots_dir=Path(root) / SHOTS) if shots_file.is_file() else []
    bad += revoked
    for i, seg in enumerate(segs):
        sid, approved = seg["shot"], approvals.get(seg["shot"])
        if not isinstance(approved, dict):
            bad.append(f"SEGMENT_CLIP_NOT_APPROVED {sid} (shot-probe.yml on the plan, Claude's review of the actual clip, "
                       "episode_build.py approve-shot, by PR)")
            continue
        sha = approved.get("clip_sha256")
        asset = approved.get("asset") or ""
        if (not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha) or not eb.SHOT_ASSET.fullmatch(asset)
                or not asset.endswith(f"-sha256-{sha}.mp4")):
            bad.append(f"SEGMENT_CLIP_ASSET {sid} (a probed Pavo clip by its content-hash asset name)")
            continue
        if approved.get("source") not in (None, "pavo"):
            bad.append(f"SEGMENT_CLIP_NOT_PAVO {sid} (the bottom half is a Pavo talking Keeper: no footage, no still motion)")
            continue
        score = approved.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) \
                or score < eb.SHOT_REVIEW_MIN:
            bad.append(f"SEGMENT_CLIP_SCORE {sid} ({score!r} < {eb.SHOT_REVIEW_MIN}: Claude's review of the clip)")
        if not eb.reviewer_identity.valid(approved) or not str(approved.get("note") or "").strip():
            bad.append(f"SEGMENT_CLIP_REVIEW {sid} (a named reviewer and what the review saw and heard)")
        seconds = approved.get("clip_seconds")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not math.isfinite(seconds) \
                or not CLIP_SECONDS[0] <= seconds <= CLIP_SECONDS[1] + 0.2:
            bad.append(f"SEGMENT_CLIP_SECONDS {sid} ({seconds!r}: the measured seconds of a {CLIP_SECONDS[0]:.0f}-"
                       f"{CLIP_SECONDS[1]:.0f} s Pavo clip)")
            seconds = None
        # E282 (owner: a minor imperfection is fixed in the edit): the approved out point of a clip whose Pavo tail
        # mumbles after the last word; the clip is used cut there
        trim = approved.get("trim_out_s")
        if trim is not None:
            why = eb.trim_problem(trim, seconds) if seconds else "SHOT_TRIM_INVALID (no measured clip seconds)"
            if why:
                bad.append(f"SEGMENT_CLIP_TRIM {sid} {why}")
                trim = None
        # the clip's own record: the words its request carried, and its checks split by meaning (E266)
        try:
            record = cl.load(Path(root) / str(approved.get("probe_record") or ""))
            entry = (record.get("shots") or {})[sid]
            clip = next(c for c in entry.get("clips") or [] if c.get("clip_sha256") == sha)
        except (OSError, ValueError, KeyError, StopIteration, TypeError):
            bad.append(f"SEGMENT_PROBE_RECORD {sid} (the approval's shot-probe record, with this exact clip)")
            continue
        said = (((entry.get("request") or {}).get("audio") or {}).get("words")) or []
        if said != eb.spoken_words(seg["text"]):
            bad.append(f"SEGMENT_CLIP_WRONG_WORDS {sid} (the clip was made for other words than the segment's: a "
                       "hard defect, probe the new text)")
        pavo = (approved.get("audio") or {}).get("route") == pavo_audio.PAVO   # owner 2026-11-03: Pavo's own audio
        if trim is not None and not pavo:   # E282: the pinned ASR heard exactly the line on the clip as cut (speech-check --trim-out)
            side = Path(root) / "migration" / "evidence" / "shots" / spec["id"] / "speech" / f"{sha}.json"
            try:
                proof = cl.load(side)
            except (OSError, ValueError):
                proof = None
            if not isinstance(proof, dict) or proof.get("clip_sha256") != sha or proof.get("trim_out_s") != trim:
                bad.append(f"SEGMENT_TRIM_WORDS_UNPROVEN {sid} (episode_build.py speech-check with --trim-out {trim}: the "
                           "ASR's words on the trimmed media)")
            else:
                heard = eb.pavo_native.words_flags(proof.get("measures") or {}, " ".join(said))
                if heard:
                    bad.append(f"SEGMENT_TRIM_WORDS {sid} {','.join(heard)} (the pinned ASR does not hear exactly the line "
                               f"on the clip cut at {trim} s)")
        split = eb.flag_split(clip.get("flags"))
        if split["hard"]:
            bad.append(f"SEGMENT_CLIP_HARD_FLAG {sid} {','.join(split['hard'])} (no face, a broken render or a policy "
                       "problem: never shipped)")
        accepted = eb.accepted_flags(approved, sha)
        proof = approved.get("audio")   # E287: the clip's audio is OUR request audio (pavo_audio): the words are the request's
        if proof is not None and proof != clip.get("audio"):
            bad.append(f"SEGMENT_AUDIO_NOT_OURS {sid} (the approval's audio proof is not the probe record's for this clip)")
        elif proof is not None:
            split = dict(split, words=[])   # exact by construction; a broken mux is refused at approve-shot and the render
        if pavo:
            split = dict(split, words=[])   # Pavo's words are a review note (the speech sidecar), never a refusal
        if [f for f in split["words"] if f not in accepted]:
            bad.append(f"SEGMENT_CLIP_WORDS_UNPROVEN {sid} (AUDIO_NOT_OUR_LINE needs the pinned ASR's proof on this "
                       "clip: episode_build.py speech-check, then approve-shot)")
        out.append({"shot": sid, "asset": asset, "clip_sha256": sha, "seconds": trim if trim is not None else seconds,
                    "trim_out_s": trim, "text": seg["text"].strip(), "flags": split, "accepted_flags": accepted, "score": score,
                    **({"audio": proof} if proof is not None else {}),
                    **({"gain_db": (approved.get("speech") or {}).get("gain_db")} if pavo else {}),
                    **({"review_notes": approved["review_notes"]} if approved.get("review_notes") else {})})
    return bad, out


def timeline(segments):
    """(offsets, end): each clip's start inside the Short (the first at VOICE_AT, each next one `fade` (default XFADE)
    before the previous ends) and where the last one ends, from the clips' seconds (a trimmed clip's are its out point)."""
    offsets, at = [], VOICE_AT
    for s in segments:
        offsets.append(round(at, 3))
        at += s["seconds"] - s.get("fade", XFADE)
    return offsets, round(at + segments[-1].get("fade", XFADE), 3)


def adaptive_fade(c):
    """A clip whose crossfade shortens to the silence it has: a trimmed one (E282) and, owner 2026-11-03, a Pavo-audio clip
    used in full (its tail is Pavo's own): the picture blends, the crossfade never runs over a word, and it is never a refusal."""
    return c.get("trim_out_s") is not None or (c.get("audio") or {}).get("route") == pavo_audio.PAVO


def join_fades(segments, spans):
    """E282: the crossfade after each clip but the last, from the silence it keeps after its last word. A full clip keeps
    the gate: XFADE + TAIL_CLEAR of silence or the render refuses. A TRIMMED clip (cut inside the silence after the
    last word) has what the cut left, so its crossfade shortens to that silence less TAIL_CLEAR, and under XFADE_MIN
    it is a plain cut (0 s): the crossfade still never runs over a word."""
    fades = []
    for c, span in zip(segments[:-1], spans[:-1]):
        tail = span[3]
        if tail >= XFADE + TAIL_CLEAR:
            fades.append(XFADE)
        elif adaptive_fade(c) and tail - TAIL_CLEAR >= XFADE_MIN:
            fades.append(math.floor((tail - TAIL_CLEAR) * 1000) / 1000)
        elif adaptive_fade(c):
            fades.append(0.0)   # no silence to fade in (the Pavo mumble starts at once): a plain cut, nothing overlaps a word
        else:
            raise SystemExit(f"SEGMENT_TAIL_TOO_SHORT {c['shot']} {tail:.2f} s of silence after the last word "
                             f"(the crossfade needs {XFADE + TAIL_CLEAR:.2f} s)")
    return fades


def check(spec, root=ROOT, spec_path=None):
    """{"problems": [...], "reflection": {...}} of one reflection spec."""
    bad, out = [], {}
    if spec_path is not None:
        m = SPEC_PATH.fullmatch(spec_path)
        if not m or m.group(1) != spec.get("long") or spec.get("id") != f"{m.group(1)}-reflection-{m.group(2)}":
            bad.append("SPEC_PATH (reflections/<long>-<n>.json, id <long>-reflection-<n>)")
    if spec.get("version") == RETIRED:
        return {"problems": bad + [f"SPEC_VERSION_RETIRED ({RETIRED} moved a still; owner 02/11: the bottom half is the "
                                   f"Keeper really speaking, Pavo talking clips: {VERSION} with `segments`)"], "reflection": out}
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
    # the top clip: its sentences whole, 20-40 s
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
        bad += short_cuts.overlap_problems("CLIP_OVERLAPS_ANOTHER", [(spec["id"], start, end)],
                                           short_cuts.sibling_ranges(spec["long"], root, skip=spec["id"]))
        if not found:
            out.update(first=first, last=last)
    x = clip.get("x", 0.5)
    if type(x) not in (int, float) or not 0.0 <= x <= 1.0:
        bad.append("CLIP_X (0-1, the window's centre across the frame)")
    if clip.get("audio", "duck") not in DUCK:
        bad.append(f"CLIP_AUDIO ({', '.join(DUCK)})")
    if spec.get("keeper_image") is not None or spec.get("motion") is not None or spec.get("reflection") is not None:
        bad.append("SPEC_STILL_FIELDS (keeper_image, motion and reflection belong to the retired v1: the Keeper's words "
                   "are the `segments`)")
    bottom = spec.get("bottom", {"y": 0.5})
    if not isinstance(bottom, dict) or type(bottom.get("y", 0.5)) not in (int, float) or not 0.0 <= bottom.get("y", 0.5) <= 1.0:
        bad.append("BOTTOM_Y (bottom {y: 0-1}: where the 1080x960 window sits in the clip's height)")
    # the Keeper's segments: ours, 20-80 words in all, whole sentences, one approved Pavo talking clip each
    found, approved = segment_problems(spec, root)
    bad += found
    text = reflection_text(spec)
    words = len(text.split())
    out.update(words=words, segments=len(spec.get("segments") or []))
    if not WORDS[0] <= words <= WORDS[1]:
        bad.append(f"REFLECTION_LENGTH {words} words ({WORDS[0]}-{WORDS[1]})")
    for i, s in enumerate(spec.get("segments") or []):
        t = s.get("text") if isinstance(s, dict) else None
        if isinstance(t, str) and (not t.strip() or t.strip()[-1] not in ".!?"):
            bad.append(f"REFLECTION_NOT_A_SENTENCE segment {i} (each segment ends on . ! or ?: never cut inside a sentence)")
    if BANNED.search(text):
        bad.append("REFLECTION_BANNED_WORDS (brand-profile.md)")
    if len(approved) == len(spec.get("segments") or []) and approved and all(a["seconds"] for a in approved):
        offsets, bottom_end = timeline(approved)
        speech = sum(a["seconds"] - PAD for a in approved)
        out.update(offsets=offsets, bottom_end=bottom_end, speech_estimate=round(speech, 2))
        if d is not None:
            if bottom_end + TAIL_MIN > d:
                bad.append(f"REFLECTION_TOO_LONG_FOR_CLIP {bottom_end:.1f} s of Keeper clips in {d:.1f} s (a {TAIL_MIN} s tail)")
            elif d - bottom_end > TAIL_MAX:
                bad.append(f"REFLECTION_TOO_SHORT_FOR_CLIP {bottom_end:.1f} s of Keeper clips in {d:.1f} s (his last frame "
                           f"would be held over {TAIL_MAX:.0f} s: cut the top clip to about {bottom_end + 1.5:.0f} s)")
            if speech < FILL_MIN * d:
                bad.append(f"REFLECTION_TOO_SHORT_FOR_CLIP {speech:.1f} s of speech in {d:.1f} s")
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
    out.update(seconds=round(d, 3) if d is not None else None, long_video_id=video, clips=approved)
    return {"problems": bad, "reflection": out}


def window(x, w=HALF[0], h=HALF[1]):
    """The top half's crop of a 16:9 frame: w:h of the full height, its centre at x of the width, then scaled to fill."""
    return (f"crop=ih*{w}/{h}:ih:(iw-ih*{w}/{h})*{min(max(float(x), 0.0), 1.0):.4f}:0,"
            f"scale={w}:{h}:flags=lanczos,setsar=1")


def keeper_window(y, w=HALF[0], h=HALF[1], fps=30):
    """One Pavo clip of the bottom half: scaled to cover 1080x960 and cropped with the face centred across (y: where
    the window sits in the height left over, 0.5 = the middle of the 1:1 frame)."""
    y = min(max(float(y), 0.0), 1.0)
    return (f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w}:{h}:(iw-{w})/2:(ih-{h})*{y:.4f},setsar=1,format=yuv420p")


def bottom_graph(durations, y, total, fps=30, fades=None):
    """(filter chunks, output label): the clips (inputs 2..) in order, each cropped, joined by XFADE crossfades, the first
    held VOICE_AT, the last frame held to `total`."""
    parts = [f"[{i + 2}:v]{keeper_window(y, fps=fps)}[b{i}]" for i in range(len(durations))]
    cur, acc = "b0", durations[0]
    for i in range(1, len(durations)):
        fade = fades[i - 1] if fades else XFADE
        parts.append(f"[{cur}][b{i}]xfade=transition=fade:duration={fade}:offset={acc - fade:.3f}[x{i}]")
        cur, acc = f"x{i}", acc + durations[i] - fade
    hold = max(total - (VOICE_AT + acc), 0.0) + 1.0
    parts.append(f"[{cur}]tpad=start_mode=clone:start_duration={VOICE_AT},tpad=stop_mode=clone:stop_duration={hold:.3f},"
                 f"trim=duration={total:.3f},setpts=PTS-STARTPTS[bot]")
    return parts, "bot"


def retime_media(src, tempo, dst):
    """E286: the clip slowed to `tempo` (< 1) as one: picture and the Keeper's own voice stretched together (atempo keeps the
    pitch), so the lips stay on the words; re-encoded near-losslessly like trim_media."""
    cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-filter_complex",
            f"[0:v]setpts=PTS/{tempo}[v];[0:a]atempo={tempo}[a]", "-map", "[v]", "-map", "[a]", "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(dst)])
    return Path(dst)


def has_audio(path):
    return bool(cl.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of",
                        "csv=p=0", path]).stdout.strip())


def speech_span(path):
    """(first, last, seconds, tail): where the clip's speech starts and ends (silencedetect at SILENCE_DB), its length and
    the silence kept after the last word."""
    seconds = cl.duration(path)
    log = cl.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af",
                  f"silencedetect=noise={SILENCE_DB}dB:d=0.12", "-f", "null", "-"]).stderr
    starts = [float(v) for v in re.findall(r"silence_start: (-?[0-9.]+)", log)]
    ends = [float(v) for v in re.findall(r"silence_end: ([0-9.]+)", log)]
    first = ends[0] if starts and starts[0] <= 0.05 and ends else 0.0
    last = seconds
    if starts and (len(starts) > len(ends) or ends[-1] >= seconds - 0.1):   # the last silence runs to the end of the clip
        last = max(starts[-1], first)
    return round(first, 3), round(last, 3), round(seconds, 3), round(seconds - last, 3)


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


def spoken_lines(segments, offsets, spans):
    """Caption sentences: each segment's sentences share its measured speech span by their words."""
    lines = []
    for i, (seg, at, (first, last, _, _)) in enumerate(zip(segments, offsets, spans)):
        sentences = speech_sentences(seg["text"])
        total = sum(len(s.split()) for s in sentences) or 1
        t = at + first
        for s in sentences:
            span = (last - first) * len(s.split()) / total
            lines.append({"segment": f"r{i:02d}", "text": s, "start": round(t, 3), "end": round(t + span, 3)})
            t += span
        lines[-1]["end"] = round(at + last, 3)
    return lines


EMOTIONS = ("grave, intent", "gentle questioning", "warm expectant", "calm kind")   # looks of record (E293), one a segment


def scaffold(spec, root=ROOT):
    """The plan shot-probe.yml probes for a spec's segments (plans/<id>.json, track keeper-reflection, 1:1): one talking
    Keeper shot per segment, k-r1..k-r4, each prompt composed by pavo_prompt.build (E290) from structured fields: the
    long's own Keeper wardrobe and setting (the same look and reference as the long), only the emotion differing (a look
    of the passing prompts of record, pavo_prompt.PASSING_LOOKS, E293)."""
    import pavo_prompt
    plan_long, _ = short_cuts.sources(spec, root)
    keeper = next((s for s in plan_long.get("shots") or []
                   if s.get("kind") == "keeper" and not s.get("voiceover") and isinstance(s.get("prompt"), str)), None)
    if not keeper:
        raise SystemExit("LONG_HAS_NO_TALKING_KEEPER_PROMPT (the long's plan holds no talking Keeper shot to reuse)")
    wardrobe = (keeper.get("pavo") or {}).get("wardrobe") or next(
        (k for k, v in (ch.registry()[ch.NARRATOR].get("wardrobe") or {}).items() if v in keeper["prompt"]), "fire")
    setting = (keeper.get("pavo") or {}).get("setting") or pavo_prompt.KEEPER_SETTINGS[wardrobe]
    segs = spec["segments"]
    plan = {"source_policy": "pavo_speech_stock", "track": "keeper-reflection", "version": "bible-plan-v2",
            "episode": spec["id"], "part": plan_long.get("part") or 1, "aspect_ratio": "1:1",
            "story": f"The Keeper's reflection on {plan_long.get('passage')}, said to the camera in {len(segs)} segments "
                     f"(the bottom half of {spec['id']})",
            "narration": [{"kind": "insight", "text": s["text"].strip()} for s in segs], "shots": []}
    for i, seg in enumerate(segs):
        shot = {"kind": "keeper", "id": seg["shot"], "lines": [i], "audio_route": "kokoro",
                "pavo": {"emotion": EMOTIONS[i % len(EMOTIONS)], "setting": setting, "wardrobe": wardrobe}}
        shot["prompt"] = pavo_prompt.build(shot, plan)
        plan["shots"].append(shot)
    return plan


def fetch_clips(spec_path, work, root=ROOT, fetch=None):
    """The approved clips of the spec into WORK/clips/<shot>.mp4 by their content-hash asset names, sha256 checked."""
    import episode_build as eb
    spec = cl.load(spec_path)
    result = check(spec, root)
    cl.refuse(result["problems"])
    for c in result["reflection"]["clips"]:
        eb.fetch_shot_clip({"asset": c["asset"], "clip_sha256": c["clip_sha256"]}, Path(work) / "clips" / f"{c['shot']}.mp4",
                           **({"fetch": fetch} if fetch else {}))
    return [c["shot"] for c in result["reflection"]["clips"]]


def render(spec_path, clean, work, out_dir, root=ROOT):
    spec = cl.load(spec_path)
    import episode_build as eb
    result = check(spec, root)
    cl.refuse(result["problems"])
    plan, report = short_cuts.sources(spec, root)
    want = report["composed"]["clean"]["output_sha256"]
    if cl.sha256(clean) != want:
        raise SystemExit("CLEAN_MASTER_SHA256_MISMATCH")
    work, out = Path(work), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    start, end = float(spec["clip"]["start"]), float(spec["clip"]["end"])
    d = end - start
    segments = result["reflection"]["clips"]
    paths, spans = [], []
    for c in segments:
        path = work / "clips" / f"{c['shot']}.mp4"
        if not path.is_file() or cl.sha256(path) != c["clip_sha256"]:
            raise SystemExit(f"CLIP_FILE_MISSING {c['shot']} (reflection_shorts.py fetch-clips: the approved clip's exact bytes)")
        if c.get("audio") is not None:   # E287: its audio digest is the request's own, on the approved bytes
            pavo_audio.verify_any(path, c["audio"])
        if c.get("trim_out_s") is not None:   # E282: the clip is used as approved, cut right after the line's last word
            (work / "trimmed").mkdir(parents=True, exist_ok=True)
            path = eb.trim_media(path, c["trim_out_s"], work / "trimmed" / f"{c['shot']}.mp4")
        if not has_audio(path):
            raise SystemExit(f"CLIP_NO_AUDIO {c['shot']} (the clip carries the Keeper's voice: a silent clip is not a talking shot)")
        paths.append(path)
        spans.append(speech_span(path))
    seconds = [s[2] for s in spans]
    for c, s in zip(segments, seconds):
        if abs(s - c["seconds"]) > 0.15:
            raise SystemExit(f"CLIP_SECONDS_CHANGED {c['shot']} {s:.2f} s measured, {c['seconds']} s approved")
    tempo = 1.0
    wpm0 = result["reflection"]["words"] / sum(x[1] - x[0] for x in spans) * 60
    if wpm0 > WPM_BAND[1] and wpm0 > 0:   # E286: cut at their last words the clips are faster than the band: slow them all, within 10 %
        tempo = plan_check.reflection_retime(wpm0)   # E289: the very function the plan's pace was judged by
        if tempo < RETIME_MIN:
            raise SystemExit(f"VOICE_PACE {wpm0:.0f} wpm ({WPM_BAND[0]}-{WPM_BAND[1]}; a retime to {RETIME_TARGET} wpm "
                             f"needs x{tempo}, under x{RETIME_MIN})")
        (work / "retimed").mkdir(parents=True, exist_ok=True)
        paths = [retime_media(p, tempo, work / "retimed" / p.name) for p in paths]
        spans = [speech_span(p) for p in paths]
        seconds = [x[2] for x in spans]
    fades = join_fades(segments, spans)   # the crossfade never runs over his last word (E282: shorter after a trimmed clip)
    offsets, bottom_end = timeline([dict(c, seconds=s, fade=f) for c, s, f in zip(segments, seconds, fades + [XFADE])])
    if bottom_end + TAIL_MIN > d:
        raise SystemExit(f"CLIPS_TOO_LONG_FOR_CLIP {bottom_end:.2f} s of Keeper clips in {d:.2f} s")
    lines = spoken_lines(segments, offsets, spans)
    first_word, last_word = lines[0]["start"], lines[-1]["end"]
    speech = sum(s[1] - s[0] for s in spans)
    wpm = result["reflection"]["words"] / speech * 60
    if not WPM_BAND[0] <= wpm <= WPM_BAND[1]:
        raise SystemExit(f"VOICE_PACE {wpm:.0f} wpm ({WPM_BAND[0]}-{WPM_BAND[1]})")
    mp4 = out / f"{spec['id']}.mp4"
    n = len(segments)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        seg = tmp / "segment.mov"   # the exact range, re-encoded (frame-accurate), audio kept lossless
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", clean, "-t", f"{d:.3f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "pcm_s16le", "-ar", "48000", seg])
        ass = tmp / "captions.ass"
        ass.write_text(captions(spec, lines))
        # the Keeper's voice: the clips' own audio, each placed where its clip starts (the previous tail is silent there)
        inputs = [a for p in paths for a in ("-i", p)]
        chain = ";".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                         + (pavo_audio.match_filter(segments[i]["gain_db"]) + "," if segments[i].get("gain_db") is not None
                            and (segments[i].get("audio") or {}).get("route") == pavo_audio.PAVO else "")   # owner 2026-11-03
                         + f"adelay={int(round(offsets[i] * 1000))}|{int(round(offsets[i] * 1000))}[k{i}]" for i in range(n))
        voice = tmp / "voice.wav"
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex",
                f"{chain};" + "".join(f"[k{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,"
                f"apad=whole_dur={d:.3f}[voice]", "-map", "[voice]", "-t", f"{d:.3f}", "-c:a", "pcm_s16le", voice])
        # the clip's own sound ducked under him (or muted); gain only to -14 LUFS after
        voice_chain = "[1:a]aresample=48000,aformat=channel_layouts=stereo"
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
        bottom, label = bottom_graph(seconds, (spec.get("bottom") or {}).get("y", 0.5), d, fades=fades)
        graph = ";".join([f"[0:v]{window(spec['clip'].get('x', 0.5))}[top]", *bottom,
                          f"[top][{label}]vstack=inputs=2,subtitles={ass},{v}[v]",
                          f"[1:a]{cl.gain_filter(premix)},{a}[a]"])
        cl.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", seg, "-i", premix, *inputs_for_graph(paths), "-filter_complex",
                graph, "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", *cl.ENC, mp4])
    lufs, peak = cl.loudness(mp4)
    probe = short_cuts.short_engine_probe(mp4)
    rec = {"version": "bible-reflection-short-v2", "id": spec["id"], "spec": str(spec_path),
           "parent": {"long": spec["long"], "pilot": spec["pilot"], "report": spec["report"],
                      "clean_master_sha256": want, "start": start, "end": end, "x": spec["clip"].get("x", 0.5),
                      "video_id": result["reflection"]["long_video_id"]},
           "segments": [{"shot": c["shot"], "asset": c["asset"], "clip_sha256": c["clip_sha256"], "start": offsets[i],
                         "seconds": seconds[i], "speech": [spans[i][0], spans[i][1]],
                         **({"trim_out_s": c["trim_out_s"]} if c.get("trim_out_s") is not None else {}), "flags": c["flags"],
                         "accepted_flags": c["accepted_flags"], "review_score": c["score"]} for i, c in enumerate(segments)],
           "bottom": {"y": (spec.get("bottom") or {}).get("y", 0.5), "retime": tempo, "crossfade": XFADE, "crossfades": fades,
                      "frame": list(HALF)},
           "voice": {"source": "pavo-talking-clips", "words": result["reflection"]["words"],
                     "first_word": round(first_word, 3), "last_word": round(last_word, 3), "wpm": round(wpm, 1)},
           "output_sha256": cl.sha256(mp4), "seconds": round(cl.duration(mp4), 3), "frame": [probe[0], probe[1]],
           "lufs": lufs, "true_peak_dbfs": peak, "sentences": lines,
           "checks": {"frame_1080x1920": probe == (short_engine.W, short_engine.H),
                      "lufs_band": cl.LUFS_BAND[0] <= lufs <= cl.LUFS_BAND[1], "true_peak_ceiling": peak <= cl.TRUE_PEAK_MAX,
                      "length": abs(cl.duration(mp4) - d) < 0.2 and SECONDS[0] <= cl.duration(mp4) <= SECONDS[1],
                      "keeper_fits": bottom_end + TAIL_MIN <= d, "voice_pace": WPM_BAND[0] <= wpm <= WPM_BAND[1]}}
    cl.save(out / f"{spec['id']}.json", rec)
    print(json.dumps({k: rec[k] for k in ("id", "output_sha256", "seconds", "lufs")}, indent=1))
    if not all(rec["checks"].values()):
        raise SystemExit(f"REFLECTION_QA_FAILED {spec['id']} {rec['checks']}")
    return rec


def inputs_for_graph(paths):
    """The bottom clips as ffmpeg inputs 2..: the order the graph (bottom_graph) numbers them in."""
    return [a for p in paths for a in ("-i", p)]


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
           "segments": [{k: s[k] for k in ("shot", "asset", "clip_sha256")} for s in short["segments"]],
           "output_sha256": short["output_sha256"], "seconds": short["seconds"],
           "frame": short["frame"], "narration": [{"kind": "insight", "text": s["text"].strip()} for s in spec["segments"]],
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
    if cmd == "scaffold" and len(argv) == 3:
        spec = cl.load(argv[2])
        path = ROOT / plan_path(spec)
        if path.exists():
            raise SystemExit(f"PLAN_EXISTS {path.relative_to(ROOT)} (edit it, or archive it: probes and approvals are bound to it)")
        cl.save(path, scaffold(spec))
        print(path.relative_to(ROOT))
    elif cmd == "fetch-clips" and len(argv) == 4:
        print(json.dumps(fetch_clips(*argv[2:4])))
    elif cmd == "render" and len(argv) == 6:
        render(*argv[2:6])
    elif cmd == "record" and len(argv) == 4:
        print(record(*argv[2:4]))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
