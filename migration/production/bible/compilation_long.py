#!/usr/bin/env python3
"""The "complete story" compilation long of an arc (owner, 2026-11-01; DECISIONS.md "Strategy reset", E251).

Nothing is generated here. The long is assembled from the arc's already-public Shorts: each Short's accepted master
(episode record `output_sha256`, release asset `bible-<id>-sha256-<sha>.mp4`, sha256 checked) framed for 16:9
(1920x1080: the 9:16 video centred over a blurred, darkened, scaled copy; the Short's burned captions are kept),
one chapter card before each story, and a new Keeper hook and close (two Pavo clips made at a fresh exact zero-credit
quote, committed with their zero-cost record). Owner 2026-11-03: each Keeper clip is used in full with PAVO'S OWN audio
(`pavo_audio: "pavo"`, the default; `trim_out_s` only when the key sets it); our Kokoro line is the loudness reference
(`audio`) and stays the sound only of a voice-over Keeper segment, and `"ours"` (E287) is an explicit per-key option. Every segment fades in and out
(FADE) and is brought to LUFS by gain only, so a join has no pop and no cut speech.

usage: compilation_long.py inputs PLAN            asset name and sha256 of each source master, one per line
       compilation_long.py build PLAN SRC_DIR OUT_DIR [VOICE_DIR]   SRC_DIR holds the masters by asset name; VOICE_DIR the
                                                 Kokoro lines hook.wav / close.wav of a voice-over Keeper segment (E281)
       compilation_long.py voice-needed PLAN     exit 0 when a Keeper segment is a voice-over (needs Kokoro in CI)
       compilation_long.py voice-script PLAN WORK   WORK/voice-script.json for pilot_render.py voice
       compilation_long.py voice-cut PLAN WORK VOICE_DIR   cut the voice-over lines out of WORK/voice.wav
       compilation_long.py qa PLAN OUT_DIR              measure the master, write out/qa.json (criteria compilation-qa-criteria-v1)
       compilation_long.py materialize PLAN OUT_DIR     write the pilot's publication inputs (no review, no approval)
       compilation_long.py verify PILOT_DIR [VIDEO]
       compilation_long.py check PLAN           the plan's problems (schema, sources, stills, KJV of every quoted line)

compilation-qa-criteria-v2 (owner 2026-11-05: "sempre tem que promover coisas novas"; YPP refuses reused content): a plan
that declares it may carry `interludes`, new Keeper segments between the chapters, and a hook and close in the same form:
`beats`, each one our Kokoro line over an APPROVED 16:9 still (sha256) with its own slow camera move, every quoted line
checked against the KJV of its `reference`. The measured share of that new Keeper runtime must reach ORIGINAL_SHARE_MIN.
v1 plans and their renders are unchanged.
"""
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import pavo_audio  # noqa: E402  (owner 2026-11-03: a Keeper clip is used in full with Pavo's own audio by default)
PLAN_VERSION = "bible-compilation-plan-v1"
MANIFEST_VERSION = "bible-compilation-manifest-v1"
CRITERIA = "compilation-qa-criteria-v1"
CRITERIA_V2 = "compilation-qa-criteria-v2"   # interludes and beat-form Keeper segments (owner 2026-11-05, originality)
CRITERIA_FILES = {CRITERIA: "migration/production/qa_criteria_compilation_v1.json",
                  CRITERIA_V2: "migration/production/qa_criteria_compilation_v2.json"}
ORIGINAL_SHARE_MIN = 0.15       # v2: new Keeper runtime (hook + interludes + close) / whole master, measured
BEATS_QUOTE = "0 credits (no generation: Kokoro voice-over on approved stills)"
MOTIONS = ("in", "out", "left", "right")
ZOOM = 0.06                     # a beat's camera move: 6 % over the whole beat (never a still hold after the move ends)
BEATS_MAX = 12
LIPSYNC_CONF_MIN = 2.7          # lipsync_check.SYNC_CONF_MIN, the SyncNet floor every speaking face meets (E309)
LIPSYNC_OFFSET_MAX = 2          # |AV offset| in frames at 25 fps a lip-synced segment may keep (coordinator 2026-11-06)
SRC_DIR = None                  # build(): where the release assets (masters and lip-synced clips) were downloaded
MUSIC = "music.flac"            # E308: the owned bed (release asset original-rest-music.lossless.flac) next to the voice lines
MUSIC_SHA256 = "1a90714dce83ce5919230a420f56cd17d81d82437303b360244d0fe0f22bbd0c"   # episode.yml's pin
BED_LUFS = -30.0                # the bed's own loudness before ducking: 16 LU under the Keeper's -14 LUFS voice
ARCHETYPE = "bible-compilation-long"
SERIES = "compilation"          # not "bible": a compilation has no per-story approved character thumbnail
W, H, FPS = 1920, 1080, 30
LUFS = -14.0
LUFS_BAND = (-15.0, -13.0)
TRUE_PEAK_MAX = -1.0
FPS_TOLERANCE = 0.3             # E251: concat of 30 fps segments measured 29.93 fps average (run 41311828730), harmless
CARD = 2.5
FADE = 0.25
BEAT = 0.5                      # still beat at each end of a Keeper clip
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EPISODES = HERE / "episodes"
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def refuse(problems):
    if problems:
        raise SystemExit("COMPILATION_REFUSED " + "; ".join(problems))


def episode(short_id, episodes=EPISODES):
    return load(Path(episodes) / f"{short_id}.json")


def is_long(c):
    """A chapter is a public Short (key `short`) or, since 2026-11-03, a public 16:9 long (key `long`: id, pilot,
    video_id, sha256 of the accepted master, seconds). The long's master is the release asset <pilot>-sha256-<sha>.mp4."""
    return isinstance(c, dict) and "long" in c


def chapter_id(c):
    return c["long"]["id"] if is_long(c) else c["short"]


def chapter_record(c, episodes=EPISODES):
    """The episode-like record of a chapter: video_id, output_sha256, seconds (and part, for a Short)."""
    if is_long(c):
        l = c["long"]
        return {"format": "long", "video_id": l.get("video_id"), "output_sha256": l.get("sha256", ""),
                "seconds": l.get("seconds"), "pilot": l.get("pilot")}
    return episode(c["short"], episodes)


def chapter_url(c, episodes=EPISODES):
    vid = chapter_record(c, episodes)["video_id"]
    return f"https://www.youtube.com/watch?v={vid}" if is_long(c) else f"https://www.youtube.com/shorts/{vid}"


def plan_problems(plan, episodes=EPISODES, root=ROOT):
    """Everything that stops a build: schema, canonical order, public Shorts of one arc, the Keeper clips' record."""
    bad = []
    if plan.get("version") != PLAN_VERSION:
        bad.append("not a compilation plan")
    if not isinstance(plan.get("id"), str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", plan["id"]):
        bad.append("unsafe id")
    if not isinstance(plan.get("pilot"), str) or not re.fullmatch(r"pilot-\d{3}", plan["pilot"]):
        bad.append("pilot mapping missing")
    title = plan.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 100 or any(c in title for c in "<>"):
        bad.append("title must be 1-100 characters, no angle brackets")
    chapters = plan.get("chapters")
    if not isinstance(chapters, list) or not 2 <= len(chapters):
        return bad + ["chapters missing"]
    parts = []
    for c in chapters:
        try:
            ep = chapter_record(c, episodes)
            cid = chapter_id(c)
        except (OSError, ValueError, KeyError, TypeError):
            bad.append("unknown short " + str(c.get("short") if isinstance(c, dict) else c))
            continue
        if is_long(c):
            l = c["long"]
            if not (isinstance(l.get("id"), str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", l["id"])
                    and isinstance(l.get("pilot"), str) and re.fullmatch(r"pilot-\d{3}", l["pilot"])
                    and isinstance(l.get("video_id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", l["video_id"])
                    and re.fullmatch(r"[0-9a-f]{64}", str(l.get("sha256", "")))
                    and type(l.get("seconds")) in (int, float) and l["seconds"] > 10):
                bad.append(f"{cid} is not a public long with pilot, video_id, master sha256 and seconds")
            elif l.get("asset") is not None and l["asset"] != f"bible-{l['id']}-sha256-{l['sha256']}.mp4":
                bad.append(f"{cid} asset must be bible-<id>-sha256-<master sha256>.mp4 (the release master, not another file)")
        else:
            parts.append(ep.get("part"))
            if ep.get("format") != "short" or not ep.get("video_id") or not re.fullmatch(r"[0-9a-f]{64}", ep.get("output_sha256", "")):
                bad.append(f"{cid} is not a public Short with a master sha256")
        if not all(isinstance(c.get(k), str) and c[k].strip() for k in ("title", "reference")):
            bad.append(f"{cid} chapter needs title and reference")
        subs = c.get("subchapters")   # v2: inner chapters of a long chapter, seconds from the chapter's own start
        if subs is not None:
            limit = float(c.get("end_s") or ep.get("seconds") or 0)
            ats = [x.get("at") for x in subs] if isinstance(subs, list) and all(isinstance(x, dict) for x in subs) else None
            if not (ats and all(type(a) in (int, float) for a in ats) and ats == sorted(ats) and ats[0] >= 10
                    and ats[-1] <= limit - 10 and all(b - a >= 10 for a, b in zip(ats, ats[1:]))
                    and all(isinstance(x.get("title"), str) and 0 < len(x["title"]) <= 80 for x in subs)):
                bad.append(f"{cid} subchapters must be [{{at, title}}], 10 s apart, inside the chapter")
        for n, x in enumerate(c.get("patches") or [], 1):   # E309: a lip-synced picture over a speaking face, audio untouched
            limit = float(c.get("end_s") or ep.get("seconds") or 0)
            if not (isinstance(x, dict) and type(x.get("at")) in (int, float) and type(x.get("seconds")) in (int, float)
                    and 0 <= x["at"] and 0.5 <= x["seconds"] <= 30 and x["at"] + x["seconds"] <= limit):
                bad.append(f"{cid} patch {n} must be {{at, seconds}} inside the chapter")
                continue
            bad += lipsync_problems(f"{cid} patch {n}", x.get("lipsync"), root)
        end = c.get("end_s")   # E254: cut the Short's own series CTA ("the full story is in the long video", "part N tomorrow")
        if end is not None and not (type(end) in (int, float) and 10 <= end < float(ep.get("seconds") or 0)):
            bad.append(f"{cid} end_s must be a number from 10 s up to the Short's length")
    if parts != sorted(parts) or len(set(parts)) != len(parts) or any(b - a != 1 for a, b in zip(parts, parts[1:])):
        bad.append("shorts are not consecutive parts in canonical order")
    criteria = plan.get("criteria", CRITERIA)
    if criteria not in CRITERIA_FILES:
        bad.append("unknown criteria " + str(criteria))
    if criteria != CRITERIA_V2 and (plan.get("interludes") or any("beats" in (plan.get(k) or {}) for k in ("hook", "close"))):
        bad.append(f"interludes and beat-form Keeper segments need {CRITERIA_V2}")
    if criteria == CRITERIA_V2 and not all("beats" in (plan.get(k) or {}) for k in ("hook", "close")):
        bad.append(f"{CRITERIA_V2} measures every Keeper segment by its beats: hook and close need beats")
    bad += interlude_problems(plan, root)
    for key in ("hook", "close"):
        k = plan.get(key) or {}
        if "beats" in k:
            bad += beats_problems(key, k, root)
            continue
        if "voiceover" in k:   # E281: the Keeper's Kokoro voice-over on an approved still (no Pavo clip for this segment)
            bad += voiceover_problems(key, k, root)
            continue
        if not all(isinstance(k.get(f), str) and k[f] for f in ("text", "video", "audio", "video_sha256", "audio_sha256",
                                                                   "conversation_id", "quote")):
            bad.append(key + " Keeper clip record incomplete")
            continue
        if k["quote"] != "0 credits (exact, fresh)":
            bad.append(key + " clip was not made at an exact zero-credit quote")
        try:
            route = key_route(plan, k)
        except SystemExit as exc:
            bad.append(f"{key} {exc}")
            route = None
        t = k.get("trim_out_s")
        if t is not None and not (type(t) in (int, float) and 3 <= t <= 30):
            bad.append(key + " trim_out_s must be a number of seconds from 3 to 30")
        for f in ("video", "audio"):
            p = Path(root) / k[f]
            if not p.is_file() or sha256(p) != k[f + "_sha256"]:
                bad.append(f"{key} {f} missing or changed")
        if route == pavo_audio.PAVO and not any(b.startswith(key + " ") and "missing or changed" in b for b in bad):
            try:   # the clip's own track must exist and must not be our line laid over it (a clip mislabelled "pavo")
                pavo_audio.pavo_proof(Path(root) / k["video"], Path(root) / k["audio"])
            except (SystemExit, subprocess.CalledProcessError) as exc:
                bad.append(f"{key} video: {exc}")
    still = (plan.get("thumbnail") or {}).get("still")
    if still is not None:   # E292: a thumbnail from an approved still: the file, its sha256 and its approval record
        p = Path(root) / str((still or {}).get("path", ""))
        if not p.is_file() or sha256(p) != (still or {}).get("sha256"):
            bad.append("thumbnail still missing or changed")
        else:
            approved = Path(root) / "migration/production/bible/stills" / f"{still.get('approved_still')}.json"
            if not approved.is_file() or load(approved).get("status") != "APPROVED" or load(approved).get("sha256") != still["sha256"]:
                bad.append("thumbnail still is not an approved still of that sha256")
    return bad


OURS_BEFORE_2026_11_03 = ("arc-02-noah-compilation", "arc-02-noah-complete-compilation")   # built and approved on our audio


def key_route(plan, k):
    """The Keeper key's audio route: its explicit `pavo_audio`, else the plan's, else the route its recorded remux kept
    (an E288 remux made it "ours": that clip's digests do not move), else "ours" for the plans built before the owner's
    order of 2026-11-03 (their rendered digests must not move), else the default, "pavo"."""
    if k.get("pavo_audio") is None and plan.get("pavo_audio") is not None:
        k = dict(k, pavo_audio=plan["pavo_audio"])
    recorded = (k.get("remux") or {}).get("audio_route") or (pavo_audio.OURS if plan.get("id") in OURS_BEFORE_2026_11_03
                                                              else None)
    return pavo_audio.route_of(k, recorded)


VOICEOVER_QUOTE = "0 credits (no Pavo call: Kokoro voice-over on an approved still)"
VOICE_ID = "am_michael"   # episode_build.VOICE: the pinned engine voice


def voiceover_problems(key, k, root=ROOT):
    """The voice-over fallback (owner: when both Pavo generations of a Keeper line are wrong, the Kokoro voice-over over an
    approved still): the line, an approved 16:9 Keeper still by sha256, the pinned voice, and the record of the Pavo
    attempt that failed. Nothing is generated at this stage and nothing costs a credit."""
    v = k.get("voiceover")
    out = []
    if not (isinstance(k.get("text"), str) and k["text"].strip() and isinstance(v, dict)):
        return [key + " voice-over record incomplete"]
    if v.get("voice_id") != VOICE_ID or v.get("speed") != 1.0:
        out.append(f"{key} voice-over is not the pinned voice")
    if k.get("quote") != VOICEOVER_QUOTE:
        out.append(f"{key} voice-over quote must be the no-Pavo zero-credit statement")
    attempt = k.get("pavo_attempt")
    if not (isinstance(attempt, dict) and attempt.get("probe_run") and attempt.get("speech_check_run") and attempt.get("result")):
        out.append(f"{key} voice-over needs the record of the Pavo attempt that failed")
    return out + still_problems(key, v.get("still"), v.get("still_sha256"), v.get("approved_still"), root)


def still_problems(label, path, digest, approved_id, root=ROOT):
    """The file at `path` has `digest`, and the approved-still record `approved_id` approves exactly that digest."""
    p = Path(root) / str(path or "")
    if not path or not p.is_file() or sha256(p) != digest:
        return [f"{label} still missing or changed"]
    approved = Path(root) / "migration/production/bible/stills" / f"{approved_id}.json"
    if not (isinstance(approved_id, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", approved_id)) or not approved.is_file() \
            or load(approved).get("status") != "APPROVED" or load(approved).get("sha256") != digest:
        return [f"{label} still is not an approved still of that sha256"]
    return []


def kjv_problem(reference, text):
    import kjv_check   # noqa: E402  (the KJV word-for-word check every narrated quotation passes)
    return kjv_check.problem(reference, text)


def beats_problems(label, k, root=ROOT):
    """A v2 Keeper segment (hook, interlude or close): our Kokoro lines, one per beat, each over an approved 16:9 still
    with its own camera move; the pinned voice; nothing generated; the honest record of why it is not a lip-synced clip;
    every beat with a `reference` quotes that reference word for word (kjv_check)."""
    out = []
    beats = k.get("beats")
    if not (isinstance(beats, list) and 1 <= len(beats) <= BEATS_MAX):
        return [f"{label} needs 1-{BEATS_MAX} beats"]
    if k.get("quote") != BEATS_QUOTE:
        out.append(f"{label} quote must be the no-generation zero-credit statement")
    if k.get("voice") != {"voice_id": VOICE_ID, "speed": 1.0}:
        out.append(f"{label} voice is not the pinned voice")
    lip = k.get("lipsync")
    if not (isinstance(lip, dict) and type(lip.get("used")) is bool and isinstance(lip.get("reason"), str) and lip["reason"].strip()):
        out.append(f"{label} needs the lipsync record (used and the reason)")
    for j, b in enumerate(beats, 1):
        where = f"{label} beat {j}"
        if not isinstance(b, dict):
            out.append(where + " is not a record")
            continue
        text = b.get("text")
        if not (isinstance(text, str) and text.strip() and len(text) <= 900 and not any(c in text for c in "<>{}")):
            out.append(where + " text must be 1-900 characters")
        if b.get("motion") not in MOTIONS:
            out.append(f"{where} motion must be one of {', '.join(MOTIONS)}")
        still = b.get("still") if isinstance(b.get("still"), dict) else {}
        out += still_problems(where, still.get("path"), still.get("sha256"), still.get("approved_still"), root)
        if b.get("lipsync") is not None:
            out += lipsync_problems(where, b["lipsync"], root)
        elif keeper_face(still.get("approved_still"), root):   # E309: the Keeper's face never speaks without lip-sync
            out.append(f"{where} speaks over the Keeper's face without lip-sync (a lip-synced clip of this line is required)")
        ref = b.get("reference")
        if ref is not None:
            p = kjv_problem(ref, text) if isinstance(ref, str) and isinstance(text, str) else "reference must be text"
            if p:
                out.append(f"{where} {p}")
    return out


def keeper_face(approved_id, root=ROOT):
    """True when an approved still shows the Keeper (its approval names a Keeper reference record, ch-keeper*)."""
    f = Path(root) / "migration/production/bible/stills" / f"{approved_id}.json"
    if not (isinstance(approved_id, str) and f.is_file()):
        return False
    rec = load(f)
    return any(str((r or {}).get("record", "")).startswith("ch-keeper") for r in rec.get("references") or []) \
        or "-k-" in approved_id


def lipsync_problems(where, lip, root=ROOT):
    """E309: a lip-synced clip of a speaking face (lipsync.yml, MuseTalk 1.5): the release asset named by its sha256, the
    exact line it carries (repo WAV by sha256), the silent source it was made from, and the measured SyncNet of the
    reviewed clip at or above the floor with the offset inside LIPSYNC_OFFSET_MAX."""
    out = []
    if not isinstance(lip, dict):
        return [where + " lipsync record is not a record"]
    sha = str(lip.get("sha256", ""))
    if not (re.fullmatch(r"[0-9a-f]{64}", sha) and re.fullmatch(r"shot-genesis-[a-z0-9-]+-sha256-" + sha + r"\.mp4", str(lip.get("clip", "")))):
        out.append(where + " lipsync clip must be the release asset shot-...-sha256-<sha256>.mp4")
    for f in ("line", "source"):
        q = Path(root) / str(lip.get(f, ""))
        if not lip.get(f) or not q.is_file() or sha256(q) != lip.get(f + "_sha256"):
            out.append(f"{where} lipsync {f} missing or changed")
    sync = lip.get("sync") if isinstance(lip.get("sync"), dict) else {}
    conf, off = sync.get("conf"), sync.get("offset")
    if not (type(conf) in (int, float) and conf >= LIPSYNC_CONF_MIN and type(off) is int and abs(off) <= LIPSYNC_OFFSET_MAX):
        out.append(f"{where} lipsync SyncNet must be conf >= {LIPSYNC_CONF_MIN} and |offset| <= {LIPSYNC_OFFSET_MAX}")
    if not (type(lip.get("run_id")) is int and isinstance(lip.get("review"), str) and lip["review"].strip()):
        out.append(where + " lipsync needs its run id and the reviewer's note")
    return out


def lipsync_assets(plan):
    """[(asset, sha256)] of every lip-synced clip the plan uses: Keeper beats and chapter patches."""
    out = []
    for _, k in keeper_sections(plan) if all(plan.get(x) for x in ("hook", "close")) else []:
        out += [(b["lipsync"]["clip"], b["lipsync"]["sha256"]) for b in k.get("beats") or [] if isinstance(b.get("lipsync"), dict)]
    for c in plan.get("chapters") or []:
        out += [(x["lipsync"]["clip"], x["lipsync"]["sha256"]) for x in c.get("patches") or [] if isinstance(x.get("lipsync"), dict)]
    return out


def interlude_problems(plan, root=ROOT):
    """v2 interludes: [{after, title, reference, beats...}], `after` = how many chapters precede it (0 = right after the
    hook), strictly increasing, never after the last chapter (that is the close)."""
    items = plan.get("interludes")
    if items is None:
        return []
    n = len(plan.get("chapters") or [])
    if not isinstance(items, list) or not items:
        return ["interludes must be a non-empty list"]
    out, last = [], -1
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            out.append(f"interlude {i} is not a record")
            continue
        after = it.get("after")
        if not (type(after) is int and last < after < n):
            out.append(f"interlude {i} after must be a chapter count from 0 to {n - 1}, increasing")
        else:
            last = after
        if not all(isinstance(it.get(f), str) and it[f].strip() and len(it[f]) <= 80 for f in ("title", "reference")):
            out.append(f"interlude {i} needs title and reference")
        out += beats_problems(f"interlude {i}", it, root)
    return out


def keeper_sections(plan):
    """[(key, record)] of every Keeper segment in playing order's key form: hook, i1..iN, close."""
    return ([("hook", plan["hook"])] + [(f"i{n}", it) for n, it in enumerate(plan.get("interludes") or [], 1)]
            + [("close", plan["close"])])


def beat_ids(key, k):
    return [f"{key}-{j:02d}" for j in range(1, len(k["beats"]) + 1)]


def keeper_record(k):
    """The manifest's record of a Keeper segment: the Pavo clip's job and hashes, or the voice-over's still and Pavo attempt."""
    if "beats" in k:
        return {"quote": k["quote"], "voice": k["voice"], "lipsync": k["lipsync"],
                "beats": [{"still": b["still"]["approved_still"], "still_sha256": b["still"]["sha256"],
                           "reference": b.get("reference")} for b in k["beats"]]}
    if "voiceover" in k:
        return {"quote": k["quote"], "voice_over": {f: k["voiceover"][f] for f in ("approved_still", "still_sha256", "voice_id", "speed")},
                "pavo_attempt": k["pavo_attempt"]}
    return {f: k[f] for f in ("conversation_id", "quote", "video_sha256", "audio_sha256")}


def has_voiceover(plan):
    return (any("voiceover" in (plan.get(key) or {}) or "beats" in (plan.get(key) or {}) for key in ("hook", "close"))
            or bool(plan.get("interludes")))


def voice_script(plan_path, work):
    """WORK/voice-script.json for pilot_render.py voice: the voice-over lines of the plan (segment id = hook / close)."""
    plan = load(plan_path)
    refuse(plan_problems(plan))
    segs = [{"id": key, "text": plan[key]["text"], "pause_after": 0.0} for key in ("hook", "close") if "voiceover" in plan[key]]
    for key, k in keeper_sections(plan):
        if "beats" in k:
            segs += [{"id": i, "text": b["text"], "pause_after": 0.0} for i, b in zip(beat_ids(key, k), k["beats"])
                     if "lipsync" not in b]   # E309: a lip-synced beat speaks the exact line its clip carries
    save(Path(work) / "voice-script.json", {"voice": {"voice_id": VOICE_ID, "speed": 1.0}, "segments": segs})


def voice_cut(plan_path, work, voice_dir):
    """The Kokoro lines of WORK/voice.wav cut at their own sentence times into VOICE_DIR/<hook|close>.wav."""
    plan = load(plan_path)
    tl = load(Path(work) / "timeline.json")
    Path(voice_dir).mkdir(parents=True, exist_ok=True)
    lines = [key for key in ("hook", "close") if "voiceover" in plan[key]]
    for key, k in keeper_sections(plan):
        if "beats" in k:
            lines += [i for i, b in zip(beat_ids(key, k), k["beats"]) if "lipsync" not in b]
    offsets = {}
    for key in lines:
        mine = [x for x in tl["sentences"] if x["segment"] == key]
        if not mine:
            raise SystemExit(f"VOICE_LINE_MISSING {key}")
        a, b = mine[0]["start"], mine[-1]["end"]
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", Path(work) / "voice.wav",
             "-c:a", "pcm_s16le", Path(voice_dir) / f"{key}.wav"])
        offsets[key] = [{"text": x["text"], "start": round(x["start"] - a, 3), "end": round(x["end"] - a, 3)} for x in mine]
    save(Path(voice_dir) / "sentences.json", offsets)   # E307: each line's sentences, seconds from the cut's start


def sources(plan, episodes=EPISODES):
    """[(short id, asset name, sha256, record)] in the plan's canonical order."""
    out = []
    for c in plan["chapters"]:
        ep = chapter_record(c, episodes)
        asset = ((c["long"].get("asset") or f"{ep['pilot']}-sha256-{ep['output_sha256']}.mp4") if is_long(c)
                 else f"bible-{c['short']}-sha256-{ep['output_sha256']}.mp4")
        out.append((chapter_id(c), asset, ep["output_sha256"], ep))
    return out


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(f"COMMAND_FAILED {cmd[0]} {r.stderr[-600:]}")
    return r


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def loudness(path):
    """(integrated LUFS, true peak dBFS) of the file's audio (ffmpeg ebur128)."""
    err = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    if not i or not p:
        raise SystemExit("LOUDNESS_UNREADABLE")
    return float(i.group(1)), float(p.group(1))


def gain_filter(path):
    """Gain only (no compression): the segment's mean brought to LUFS, then a -1 dBFS ceiling."""
    lufs, _ = loudness(path)
    return f"volume={LUFS - lufs:.2f}dB,alimiter=limit=0.8:level=false"


def fades(d):
    return (f"fade=t=in:st=0:d={FADE},fade=t=out:st={max(d - FADE, 0):.3f}:d={FADE}",
            f"afade=t=in:st=0:d={FADE},afade=t=out:st={max(d - FADE, 0):.3f}:d={FADE}")


def card_overlay(card, files):
    """E258: the chapter card is drawn over the first CARD seconds of its Short (real picture and sound), never a
    separate black, silent, frozen segment that the whole-file signal scan rightly refuses as dead air."""
    if not card:
        return ""
    on = f"enable='between(t,0.2,{0.2 + CARD:.2f})'"
    dt = lambda p, size, y, col: (f",drawtext=fontfile={FONT}:textfile={p}:fontsize={size}:fontcolor={col}:"
                                  f"x=(w-text_w)/2:y={y}:borderw=3:bordercolor=black@0.85:{on}")
    return (f",drawbox=x=0:y=40:w=iw:h=250:color=black@0.45:t=fill:{on}" + dt(files[0], 40, 62, "0xd9b25f")
            + dt(files[1], 78, 112, "white") + dt(files[2], 44, 212, "0xc9d3e6"))


def render_short(src, out, end=None, card=None):
    d = duration(src) if end is None else min(duration(src), float(end))
    v, a = fades(d)
    files = []
    for n, t in enumerate(card or ()):
        p = Path(f"{Path(out).with_suffix('')}.card{n}.txt")
        p.write_text(t)
        files.append(p)
    graph = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,"
             f"eq=brightness=-0.28[bg];[b]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,setsar=1{card_overlay(card, files)},{v}[v];"
             f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(src)},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-t", f"{d:.3f}", *ENC, out])
    for p in files:
        p.unlink()


def render_long(src, out, end=None, card=None, patches=()):
    """A public 16:9 long as a chapter: no blurred framing (it already is 1920x1080), same card, fades and gain.
    E309: `patches` [(clip, at, seconds)] lay a lip-synced picture over a speaking face for its span; the chapter's own
    audio is never touched."""
    d = duration(src) if end is None else min(duration(src), float(end))
    v, a = fades(d)
    files = []
    for n, t in enumerate(card or ()):
        p = Path(f"{Path(out).with_suffix('')}.card{n}.txt")
        p.write_text(t)
        files.append(p)
    base = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}[b0];"
    for n, (_, at, secs) in enumerate(patches, 1):
        base += (f"[{n}:v]scale={W}:{H},setsar=1,fps={FPS},trim=duration={secs:.3f},setpts=PTS-STARTPTS+{at:.3f}/TB[p{n}];"
                 f"[b{n - 1}][p{n}]overlay=enable='between(t,{at:.3f},{at + secs:.3f})':eof_action=pass[b{n}];")
    graph = (base + f"[b{len(patches)}]null{card_overlay(card, files)},{v}[v];"
             f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(src)},{a}[a]")
    ins = [x for clip, _, _ in patches for x in ("-i", clip)]
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, *ins, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-t", f"{d:.3f}", *ENC, out])
    for p in files:
        p.unlink()


def render_keeper(video, audio, out, trim_out_s=None, route=pavo_audio.OURS):
    """Keeper clip at 16:9 with a still beat (BEAT) at each end: first/last frame held, our own line starts after the
    first beat; its audio is our Kokoro wav, so nothing depends on the clip's own sound. E292 (the edit fixes a minor
    imperfection, E273): `trim_out_s` cuts the clip at the end of our line (and its 0.3 s tail pad) and drops the closing
    still beat, so no 1.8 s of dead mix follows the Keeper (local-review flagged a dropout at 8.69-10.48 s).
    Owner 2026-11-03, route "pavo": the clip's OWN audio is the Keeper's voice (the whole clip unless `trim_out_s` is set),
    brought to LUFS by the same gain (the Kokoro `audio` is only the loudness reference of the narration)."""
    if route == pavo_audio.PAVO:
        return render_keeper_pavo(video, out, trim_out_s)
    if trim_out_s is not None:
        d = float(trim_out_s) + BEAT
        v, a = fades(d)
        graph = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,tpad=start_mode=clone:start_duration={BEAT},{v}[v];"
                 f"[1:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(audio)},adelay={int(BEAT * 1000)}:all=1,"
                 f"apad=whole_dur={d:.3f},{a}[a]")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-t", f"{float(trim_out_s):.3f}", "-i", video, "-i", audio,
             "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", *ENC, out])
        return
    d = duration(video) + 2 * BEAT
    v, a = fades(d)
    graph = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,tpad=start_mode=clone:start_duration={BEAT}:"
             f"stop_mode=clone:stop_duration={BEAT},{v}[v];"
             f"[1:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(audio)},adelay={int(BEAT * 1000)}:all=1,"
             f"apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-i", audio, "-filter_complex", graph, "-map", "[v]",
         "-map", "[a]", "-t", f"{d:.3f}", *ENC, out])


def render_keeper_pavo(video, out, trim_out_s=None):
    """The Keeper clip on the Pavo-audio route: its own track, in full, between a still beat at each end."""
    seconds = float(trim_out_s) if trim_out_s is not None else duration(video)
    d = seconds + (BEAT if trim_out_s is not None else 2 * BEAT)
    v, a = fades(d)
    pad = f"start_mode=clone:start_duration={BEAT}" + ("" if trim_out_s is not None else f":stop_mode=clone:stop_duration={BEAT}")
    graph = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,tpad={pad},{v}[v];"
             f"[0:a]atrim=duration={seconds:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
             f"{gain_filter(video)},adelay={int(BEAT * 1000)}:all=1,apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", *(["-t", f"{seconds:.3f}"] if trim_out_s is not None else []),
         "-i", video, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", *ENC, out])


def render_keeper_still(still, audio, out):
    """The voice-over fallback segment: the approved Keeper still with a slow push-in (a still beat at each end, as
    render_keeper) and our Kokoro line after the first beat; same audio chain, same fades."""
    d = duration(audio) + 2 * BEAT
    v, a = fades(d)
    frames = int(d * FPS) + 1
    graph = (f"[0:v]scale=3840:2160:flags=lanczos,zoompan=z='min(1.0+0.00045*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
             f"d=1:s={W}x{H}:fps={FPS},setsar=1,{v}[v];"
             f"[1:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(audio)},adelay={int(BEAT * 1000)}:all=1,"
             f"apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", still,
         "-i", audio, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-frames:v", str(frames), "-t", f"{d:.3f}",
         *ENC, out])


def motion_filter(motion, d):
    """A slow camera move over the whole beat (never a still hold after it ends): push in, pull out, or a pan at a
    fixed 1+ZOOM crop. Rendered from a 2x upscale so the move is sub-pixel smooth."""
    n = max(int(d * FPS), 1)
    z = {"in": f"1+{ZOOM}*on/{n}", "out": f"1+{ZOOM}-{ZOOM}*on/{n}"}.get(motion, f"1+{ZOOM}")
    x = {"left": f"(iw-iw/zoom)*(1-on/{n})", "right": f"(iw-iw/zoom)*on/{n}"}.get(motion, "iw/2-(iw/zoom/2)")
    return (f"scale=3840:2160:flags=lanczos,zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")


def render_beat(still, audio, out, motion, card=None):
    """One v2 Keeper beat: the approved still with its camera move, a still beat (BEAT) at each end of our line, the
    same audio chain and fades as every segment, and the section's card over its first beat (as over a chapter)."""
    d = duration(audio) + 2 * BEAT
    v, a = fades(d)
    files = []
    for n, t in enumerate(card or ()):
        p = Path(f"{Path(out).with_suffix('')}.card{n}.txt")
        p.write_text(t)
        files.append(p)
    graph = (f"[0:v]{motion_filter(motion, d)},setsar=1{card_overlay(card, files)},{v}[v];"
             f"[1:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(audio)},adelay={int(BEAT * 1000)}:all=1,"
             f"apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", still,
         "-i", audio, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-frames:v", str(int(d * FPS) + 1),
         "-t", f"{d:.3f}", *ENC, out])
    for p in files:
        p.unlink()
    return round(duration(audio), 3)


def music_bed(segment, music, offset, out):
    """E308: the owned music under a whole v2 Keeper segment, ducked by the voice (short_engine's mix), so the still beats
    between his lines are never dead air; the picture is copied, the segment keeps its fades and length."""
    d = duration(segment)
    _, a = fades(d)
    piece = Path(f"{Path(out).with_suffix('')}.bed.wav")   # the slice it plays, measured so the bed has one level everywhere
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-stream_loop", "-1", "-i", music, "-ss", f"{offset:.3f}", "-t", f"{d:.3f}",
         "-ac", "2", "-ar", "48000", piece])
    gain = BED_LUFS - loudness(piece)[0]
    piece.unlink()
    graph = (f"[0:a]asplit=2[v][vk];[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={offset:.3f}:duration={d:.3f},"
             f"asetpts=PTS-STARTPTS,volume={gain:.2f}dB[m];[m][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
             f"[v][md]amix=inputs=2:duration=first:normalize=0,{a},alimiter=limit=0.8:level=false[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", segment, "-stream_loop", "-1", "-i", music, "-filter_complex", graph,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-t", f"{d:.3f}", "-movflags", "+faststart", out])


def render_beat_clip(clip, out, motion, card=None):
    """E309: a lip-synced Keeper beat: the clip's picture (our line already on it, bit-exact, with its picture tail) after a
    still beat (BEAT), the same camera move, card, audio chain and fades as a still beat."""
    d = duration(clip) + BEAT
    v, a = fades(d)
    files = []
    for n, t in enumerate(card or ()):
        p = Path(f"{Path(out).with_suffix('')}.card{n}.txt")
        p.write_text(t)
        files.append(p)
    graph = (f"[0:v]fps={FPS},scale={W}:{H},tpad=start_mode=clone:start_duration={BEAT},{motion_filter(motion, d)},setsar=1"
             f"{card_overlay(card, files)},{v}[v];"
             f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(clip)},adelay={int(BEAT * 1000)}:all=1,"
             f"apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", clip, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-t", f"{d:.3f}", *ENC, out])
    for p in files:
        p.unlink()


def render_beats(key, k, voice_dir, out, card=None):
    """A v2 Keeper segment: its beats rendered one by one and joined (same encoder settings, stream copy).
    Returns the seconds of our spoken lines (the no_padding and original-share measures)."""
    parts, spoken, starts, t = [], 0.0, {}, 0.0
    for j, (i, b) in enumerate(zip(beat_ids(key, k), k["beats"])):
        part = Path(f"{Path(out).with_suffix('')}.{j:02d}.mp4")
        if "lipsync" in b:   # E309: the lip-synced clip of this exact line
            clip = Path(SRC_DIR or "") / b["lipsync"]["clip"]
            if not clip.is_file() or sha256(clip) != b["lipsync"]["sha256"]:
                raise SystemExit(f"LIPSYNC_CLIP_MISSING {i}")
            render_beat_clip(clip, part, b["motion"], card if j == 0 else None)
            spoken += round(duration(ROOT / b["lipsync"]["line"]), 3)
        else:
            wav = Path(voice_dir or "") / f"{i}.wav"
            if not wav.is_file():
                raise SystemExit(f"VOICE_LINE_MISSING {i} (compilation_long.py voice-cut first)")
            spoken += render_beat(ROOT / b["still"]["path"], wav, part, b["motion"], card if j == 0 else None)
        starts[i] = round(t + BEAT, 3)   # E307: where this beat's line starts inside the segment
        t += duration(part)
        parts.append(part)
    lst = Path(f"{Path(out).with_suffix('')}.txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    music = Path(voice_dir or "") / MUSIC
    joined = Path(f"{Path(out).with_suffix('')}.voice.mp4") if music.is_file() else Path(out)
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    for p in parts + [lst]:
        p.unlink()
    if music.is_file():
        if sha256(music) != MUSIC_SHA256:
            raise SystemExit("MUSIC_SHA256_MISMATCH")
        offset = (sum(map(ord, key)) * 37.0) % 180.0   # each Keeper segment starts the bed at its own place
        music_bed(joined, music, offset, out)
        joined.unlink()
    return round(spoken, 3), len(parts), starts


def render_key(plan, key, voice_dir, out):
    k = plan[key]
    if "beats" in k:
        return render_beats(key, k, voice_dir, out)
    if "voiceover" in k:
        wav = Path(voice_dir or "") / f"{key}.wav"
        if not wav.is_file():
            raise SystemExit(f"VOICE_LINE_MISSING {key} (compilation_long.py voice-cut first)")
        render_keeper_still(ROOT / k["voiceover"]["still"], wav, out)
    else:
        render_keeper(ROOT / k["video"], ROOT / k["audio"], out, k.get("trim_out_s"), key_route(plan, k))


def thumbnail(src, spec, out):
    """A 1280x720 frame of a Short's master: a 16:9 window of its vertical picture (spec: at, y fraction) plus our title."""
    ys = max(0.0, min(1.0, float(spec.get("y", 0.4))))
    t1, t2 = Path(str(out) + ".1.txt"), Path(str(out) + ".2.txt")
    t1.write_text(spec["line1"])
    t2.write_text(spec["line2"])
    if spec.get("still"):
        # E292 (owner: the bottom caption was weak): an APPROVED still, clean of any burned-in subtitle, with a stepped dark
        # foot (no frame of a video's own caption shows through it), bigger lines and a heavier outline
        vf = (f"crop=iw:iw*9/16:0:(ih-iw*9/16)*{ys:.3f},scale=1280:720:flags=lanczos,"
              f"drawbox=x=0:y=ih-300:w=iw:h=300:color=black@0.25:t=fill,"
              f"drawbox=x=0:y=ih-230:w=iw:h=230:color=black@0.35:t=fill,"
              f"drawbox=x=0:y=ih-170:w=iw:h=170:color=black@0.45:t=fill,"
              f"drawtext=fontfile={FONT}:textfile={t1}:fontsize=96:fontcolor=white:x=(w-text_w)/2:y=h-190:borderw=6:bordercolor=black,"
              f"drawtext=fontfile={FONT}:textfile={t2}:fontsize=54:fontcolor=0xf0c860:x=(w-text_w)/2:y=h-72:borderw=4:bordercolor=black")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", ROOT / spec["still"]["path"], "-frames:v", "1", "-vf", vf,
             "-q:v", "2", out])
        t1.unlink()
        t2.unlink()
        return
    vf = (f"crop=iw:iw*9/16:0:(ih-iw*9/16)*{ys:.3f},scale=1280:720:flags=lanczos,"
          f"drawbox=x=0:y=ih-190:w=iw:h=190:color=black@0.55:t=fill,"
          f"drawtext=fontfile={FONT}:textfile={t1}:fontsize=84:fontcolor=white:x=(w-text_w)/2:y=h-175:borderw=3:bordercolor=black,"
          f"drawtext=fontfile={FONT}:textfile={t2}:fontsize=52:fontcolor=0xd9b25f:x=(w-text_w)/2:y=h-72:borderw=2:bordercolor=black")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(spec["at"]), "-i", src, "-frames:v", "1", "-vf", vf,
         "-q:v", "2", out])
    t1.unlink()
    t2.unlink()


def fps(rate):
    num, _, den = str(rate).partition("/")
    return float(num) / float(den or 1) if float(den or 1) else 0.0


def clock(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def build(plan_path, src_dir, out_dir, voice_dir=None):
    global SRC_DIR
    plan = load(plan_path)
    refuse(plan_problems(plan))
    src_dir, out = Path(src_dir), Path(out_dir)
    SRC_DIR = src_dir
    for asset, sha in lipsync_assets(plan):
        if not (src_dir / asset).is_file() or sha256(src_dir / asset) != sha:
            raise SystemExit(f"SOURCE_SHA256_MISMATCH {asset}")
    out.mkdir(parents=True, exist_ok=True)
    segs, rows = [], []

    def add(kind, name, path, **extra):
        segs.append(path)
        rows.append({"kind": kind, "name": name, "seconds": round(duration(path), 3), **extra})

    seg = out / "segments"
    seg.mkdir(exist_ok=True)
    if plan.get("criteria") == CRITERIA_V2 and not (Path(voice_dir or "") / MUSIC).is_file():
        raise SystemExit(f"MUSIC_MISSING {MUSIC} (E308: the owned bed under the Keeper segments)")
    def keeper(kind, name, path, rendered):
        extra = {"spoken_seconds": rendered[0], "beats": rendered[1], "line_starts": rendered[2]} if isinstance(rendered, tuple) else {}
        add(kind, name, path, **extra)

    keeper("hook", "hook", seg / "00-hook.mp4", render_key(plan, "hook", voice_dir, seg / "00-hook.mp4"))
    between = {it["after"]: (n, it) for n, it in enumerate(plan.get("interludes") or [], 1)}

    def interlude(after):
        if after in between:
            n, it = between[after]
            path = seg / f"{after:02d}c-interlude.mp4"
            card = ("THE KEEPER", it["title"], it["reference"] + " (KJV)")
            keeper("interlude", f"i{n}", path, render_beats(f"i{n}", it, voice_dir, path, card))
            rows[-1]["chapter"] = it["title"]

    interlude(0)
    verified = []
    for k, (sid, asset, sha, ep) in enumerate(sources(plan), 1):
        master = src_dir / asset
        if not master.is_file() or sha256(master) != sha:
            raise SystemExit(f"SOURCE_SHA256_MISMATCH {sid}")
        verified.append({"short": sid, "asset": asset, "sha256": sha, "video_id": ep["video_id"], "seconds": ep["seconds"]})
        c = plan["chapters"][k - 1]
        card = (f"PART {k} OF {len(plan['chapters'])}", c["title"], c["reference"] + " (KJV)")
        kind = "long" if is_long(c) else "short"
        if is_long(c):
            patches = [(src_dir / x["lipsync"]["clip"], float(x["at"]), float(x["seconds"])) for x in c.get("patches") or []]
            render_long(master, seg / f"{k:02d}b-short.mp4", c.get("end_s"), card, patches)
        else:
            render_short(master, seg / f"{k:02d}b-short.mp4", c.get("end_s"), card)
        add(kind, sid, seg / f"{k:02d}b-short.mp4", source_sha256=sha, chapter=c["title"],
            **({"end_s": c["end_s"]} if c.get("end_s") else {}))
        interlude(k)
    keeper("close", "close", seg / "99-close.mp4", render_key(plan, "close", voice_dir, seg / "99-close.mp4"))
    lst = out / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs))
    master = out / f"{plan['id']}.mp4"
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
         "-movflags", "+faststart", master])
    t, timeline = 0.0, []
    for r in rows:
        r["start"] = round(t, 3)
        t += r["seconds"]
        r["end"] = round(t, 3)
        timeline.append(r)
    if plan["thumbnail"].get("still"):
        thumbnail(None, plan["thumbnail"], out / "thumbnail.jpg")
    else:
        thumb_src = next(v for v in verified if v["short"] == plan["thumbnail"]["short"])
        thumbnail(src_dir / thumb_src["asset"], plan["thumbnail"], out / "thumbnail.jpg")
    sha = sha256(master)
    save(out / "timeline.json", {"output_sha256": sha, "segments": timeline})
    save(out / "report.json", timed_reference(plan, timeline, sha, voice_dir))
    save(out / "sources.json", verified)
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", master, "-vf",
         f"fps=20/{duration(master):.3f},scale=480:270,tile=5x4", "-frames:v", "1", "-q:v", "3", out / "sheet.jpg"])
    print(json.dumps({"output_sha256": sha, "byte_size": master.stat().st_size, "seconds": round(duration(master), 3)}))


def source_sentences(source_sha256, root=ROOT):
    """The timed sentences of a source master from its own build report (composed.sentences), or None."""
    for f in sorted((Path(root) / "migration/evidence/episodes").glob("*/report-*.json")):
        try:
            c = load(f).get("composed") or {}
        except ValueError:
            continue
        if c.get("output_sha256") == source_sha256 and isinstance(c.get("sentences"), list) and c["sentences"]:
            return c["sentences"]
    return None


def timed_reference(plan, timeline, sha, voice_dir=None, root=ROOT):
    """E307: the master's own timed script, the shape local_review.reference_for and defect_scan read (composed.sentences
    of a report bound to output_sha256): every Keeper beat's sentences at their place (the line's start inside its
    segment + the sentence's offset in the cut line), and each chapter's sentences from its source's build report,
    shifted to the chapter's start and cut at its end_s. A chapter with no timed source report is listed as untimed."""
    offsets = load(Path(voice_dir) / "sentences.json") if voice_dir and (Path(voice_dir) / "sentences.json").is_file() else {}
    for key, k in keeper_sections(plan):   # E309: a lip-synced line's sentences, recorded with its clip
        for i, b in zip(beat_ids(key, k), k.get("beats") or []):
            if isinstance(b.get("lipsync"), dict) and b["lipsync"].get("sentences"):
                offsets[i] = b["lipsync"]["sentences"]
    sentences, untimed = [], []
    for r in timeline:
        if r.get("line_starts"):
            for i, at in r["line_starts"].items():
                for x in offsets.get(i, []):
                    sentences.append({"segment": i, "text": x["text"], "start": round(r["start"] + at + x["start"], 3),
                                      "end": round(r["start"] + at + x["end"], 3), "speaker": "keeper"})
                if i not in offsets:
                    untimed.append(i)
        elif r["kind"] in ("short", "long"):
            src = source_sentences(r["source_sha256"], root)
            if not src:
                untimed.append(r["name"])
                continue
            for x in src:
                if x.get("start") is None or x.get("end") is None or x["end"] > r["seconds"] - FADE:
                    continue
                sentences.append({"segment": r["name"], "text": x["text"], "start": round(r["start"] + x["start"], 3),
                                  "end": round(r["start"] + x["end"], 3), "speaker": x.get("speaker")})
        elif r["kind"] in ("hook", "close"):
            untimed.append(r["name"])
    return {"version": "compilation-report-v1", "source": "compilation_long.py build",
            "composed": {"output_sha256": sha, "sentences": sentences, "untimed_segments": untimed}}


def qa(plan_path, out_dir):
    plan, out = load(plan_path), Path(out_dir)
    master = out / f"{plan['id']}.mp4"
    sha = sha256(master)
    tl = load(out / "timeline.json")
    src = load(out / "sources.json")
    dec = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(master), "-f", "null", "-"], capture_output=True, text=True)
    probe = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,avg_frame_rate", "-of", "json", master]).stdout)["streams"][0]
    lufs, peak = loudness(master)
    dur = duration(master)
    expected = sum(r["seconds"] for r in tl["segments"])
    shorts = [r for r in tl["segments"] if r["kind"] in ("short", "long")]
    criteria = plan.get("criteria", CRITERIA)
    order = ["hook"] + ["interlude"] * any(it["after"] == 0 for it in plan.get("interludes") or [])
    for n, c in enumerate(plan["chapters"], 1):
        order += ["long" if is_long(c) else "short"] + ["interlude"] * any(it["after"] == n for it in plan.get("interludes") or [])
    order += ["close"]
    keeper = [r for r in tl["segments"] if r["kind"] in ("hook", "interlude", "close")]
    share = round(sum(r["seconds"] for r in keeper) / dur, 4) if dur else 0.0
    checks = {
        "full_decode_without_errors": dec.returncode == 0 and not dec.stderr.strip(),
        "video_format_1920x1080_30fps": (probe["width"], probe["height"]) == (W, H) and abs(fps(probe["avg_frame_rate"]) - FPS) < FPS_TOLERANCE,
        "duration_is_sum_of_segments": abs(dur - expected) < 1.0,
        "no_padding": dur <= sum(s["seconds"] for s in src) + 30 + len(src) * (CARD + 1.0),
        "integrated_lufs_band": LUFS_BAND[0] <= lufs <= LUFS_BAND[1],
        "true_peak_ceiling": peak <= TRUE_PEAK_MAX,
        "sources_are_the_public_masters_by_sha": [s["short"] for s in src] == [chapter_id(c) for c in plan["chapters"]]
        and all(len(s["sha256"]) == 64 for s in src) and [r["source_sha256"] for r in shorts] == [s["sha256"] for s in src],
        "canonical_order": [r["kind"] for r in tl["segments"]] == order
        and [r.get("chapter") for r in shorts] == [c["title"] for c in plan["chapters"]],   # E258: card over each Short
        "keeper_clips_zero_credit": all(k["quote"] in ("0 credits (exact, fresh)", VOICEOVER_QUOTE, BEATS_QUOTE)
                                        for _, k in keeper_sections(plan)),
        "music_and_voice_owned": True,   # the Shorts' own recorded sources (Kokoro voice, owned music) and our Kokoro hook/close
    }
    if criteria == CRITERIA_V2:
        # v2 no_padding: every segment is no longer than its own content (a chapter its source cut, a Keeper segment its
        # spoken lines plus the still beat at each end of every line), and the whole is the sum of the segments
        src_s = {s["short"]: s["seconds"] for s in src}
        checks["no_padding"] = all(
            (r["seconds"] <= min(float(src_s.get(r["name"]) or 0), float(r.get("end_s") or 1e9)) + 0.2) if r["kind"] in ("short", "long")
            else (r.get("spoken_seconds") is not None and r["seconds"] <= r["spoken_seconds"] + r["beats"] * (2 * BEAT) + 0.2)
            for r in tl["segments"])
        checks["original_keeper_share"] = share >= ORIGINAL_SHARE_MIN
    doc = {"version": "compilation-qa-v1", "criteria_version": criteria,
           "criteria_sha256": sha256(ROOT / CRITERIA_FILES[criteria]),
           "output_sha256": sha, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
           "measured": {"seconds": round(dur, 3), "lufs": lufs, "true_peak_dbfs": peak, "frame_rate": probe["avg_frame_rate"],
                        "keeper_seconds": round(sum(r["seconds"] for r in keeper), 3), "keeper_share": share}}
    save(out / "qa.json", doc)
    print(json.dumps({"status": doc["status"], "checks": {k: v for k, v in checks.items() if not v}, **doc["measured"]}))
    return 0 if doc["status"] == "PASS" else 1


CHAPTER_MIN = 10.0   # publication preflight: each description chapter is at least 10 s (migration/publish/preflight.py CHAPTERS)


def description(plan, tl):
    """The description's chapters. A Keeper hook or close shorter than CHAPTER_MIN seconds cannot be a chapter of its own
    (the preflight refuses it, and a title card shorter than that is no chapter): the hook is folded into the first
    story's chapter (which then starts at 0:00) and the close into the last story's, as the preflight's rule reads."""
    segs = tl["segments"]
    hook = next(r for r in segs if r["kind"] == "hook")
    titles = iter([c["title"] for c in plan["chapters"]])
    subs = iter([c.get("subchapters") or [] for c in plan["chapters"]])
    stories = []
    for r in segs:   # v2: an interlude is a chapter of its own; a long chapter may name its own inner chapters
        if r["kind"] in ("short", "long"):
            stories.append((r["start"], next(titles)))
            stories += [(r["start"] + s["at"], s["title"]) for s in next(subs)]
        elif r["kind"] == "interlude" and r["seconds"] >= CHAPTER_MIN:
            stories.append((r["start"], r["chapter"]))
    rows = [(0, plan["chapter_zero"])] + stories if hook["end"] - hook["start"] >= CHAPTER_MIN else [(0, stories[0][1])] + stories[1:]
    close = next(r for r in segs if r["kind"] == "close")
    if close["end"] - close["start"] >= CHAPTER_MIN:
        rows.append((close["start"], plan["chapter_last"]))
    chapters = "\n".join(f"{clock(t)} {name}" for t, name in rows)
    links = "\n".join(f"- {c['title']} ({c['reference']}): {chapter_url(c)}"
                      for c in plan["chapters"])
    return plan["description"].format(chapters=chapters, links=links), rows


def script_segments(plan, root=ROOT):
    """The spoken text in order: the Keeper's hook, each Short's planned lines (where its plan exists), the close."""
    def said(k):
        return " ".join(b["text"] for b in k["beats"]) if "beats" in k else k["text"]
    between = {it["after"]: it for it in plan.get("interludes") or []}
    segs = [{"kind": "hook", "text": said(plan["hook"])}]
    if 0 in between:
        segs.append({"kind": "interlude", "text": said(between[0])})
    for n, c in enumerate(plan["chapters"], 1):
        p = Path(root) / "migration/production/bible/plans" / f"{chapter_id(c)}.json"
        lines = []
        if p.is_file() and not is_long(c):
            lines = [s["line"] for s in load(p).get("shots", []) if isinstance(s.get("line"), str) and s["line"].strip()]
        segs.append({"kind": "long" if is_long(c) else "short", "short": chapter_id(c), "text": " ".join(lines) or c["title"]})
        if n in between:
            segs.append({"kind": "interlude", "text": said(between[n])})
    segs.append({"kind": "close", "text": said(plan["close"])})
    return segs


def materialize(plan_path, out_dir, root=ROOT):
    plan, out = load(plan_path), Path(out_dir)
    refuse(plan_problems(plan))
    manifest_tl = load(out / "timeline.json")
    sha = sha256(out / f"{plan['id']}.mp4")
    if manifest_tl["output_sha256"] != sha:
        raise SystemExit("TIMELINE_NOT_FOR_THIS_FILE")
    text, rows = description(plan, manifest_tl)
    d = Path(root) / "migration/production" / plan["pilot"]
    old = d / "out/manifest.json"
    if old.exists() and load(old).get("output_sha256") != sha:
        refuse(["pilot already contains a different master; archive it explicitly before replacement"])
    (d / "out").mkdir(parents=True, exist_ok=True)
    (d / "inspection").mkdir(parents=True, exist_ok=True)
    dur = duration(out / f"{plan['id']}.mp4")
    criteria = plan.get("criteria", CRITERIA)
    text_of = lambda k: " ".join(b["text"] for b in k["beats"]) if "beats" in k else k["text"]
    script = {"version": "bible-compilation-script-v1", "pilot_id": plan["pilot"], "archetype": ARCHETYPE, "series": SERIES,
              "episode": plan["id"], "working_title": plan["title"], "criteria_version": criteria,
              "shorts": [chapter_id(c) for c in plan["chapters"]],
              "hook": {"text": text_of(plan["hook"])}, "close": {"text": text_of(plan["close"])},
              "segments": script_segments(plan, root)}   # E258: three_stage critique reads the whole spoken text
    manifest = {"version": MANIFEST_VERSION, "pilot_id": plan["pilot"], "compilation": plan["id"], "output_sha256": sha,
                "output_seconds": round(dur, 3), "criteria_version": criteria, "burned_captions": "kept from the Shorts",
                "sources": load(out / "sources.json"), "segments": manifest_tl["segments"], "chapters": rows,
                "keeper_clips": {k: keeper_record(rec) for k, rec in keeper_sections(plan)}}
    package = {"version": "pilot-package-v1", "pilot_id": plan["pilot"], "series": SERIES, "episode": plan["id"],
               "title": plan["title"], "title_length": len(plan["title"]), "description": text, "tags": plan["tags"],
               "category_id": "29", "playlist": plan.get("playlist"), "default_language": "en", "made_for_kids": False,
               "privacy_on_upload": "private", "thumbnail": "thumbnail.jpg", "ai_generated_visuals": True,
               "altered_or_synthetic_disclosure": "Bible-story reconstruction with synthetic narration; synthetic disclosure on.",
               "first_comment": plan["first_comment"], "output_sha256": sha,
               "upload_performed": False, "publication_performed": False}
    save(d / "script.json", script)
    save(d / "schedule.json", {"publish_at": plan.get("publish_at"), "shorts_slots": []})
    save(d / "out/manifest.json", manifest)
    save(d / "out/timeline.json", manifest_tl)
    save(d / "out/package.json", package)
    (d / "inspection/thumbnail.jpg").write_bytes((out / "thumbnail.jpg").read_bytes())
    if (out / "qa.json").exists():
        (d / "out/qa.json").write_bytes((out / "qa.json").read_bytes())
    files = ("script.json", "schedule.json", "out/manifest.json", "out/timeline.json", "out/package.json", "inspection/thumbnail.jpg")
    save(d / "out/handoff.json", {"version": "compilation-handoff-v1", "pilot_id": plan["pilot"], "episode": plan["id"],
                                  "output_sha256": sha, "source_plan": {"file": str(Path(plan_path).resolve().relative_to(Path(root).resolve())),
                                                                        "sha256": sha256(plan_path)},
                                  "release_asset": f"{plan['pilot']}-sha256-{sha}.mp4",
                                  "files": {n: sha256(d / n) for n in files}, "review_status": "AWAITING_REVIEW",
                                  "approval_created": False})
    return d


def verify(pilot_dir, video=None, root=ROOT):
    """What a publication re-checks: the handoff's files unchanged, the plan unchanged, the video the manifest names."""
    d = Path(pilot_dir)
    b = load(d / "out/handoff.json")
    bad = []
    if b.get("version") != "compilation-handoff-v1" or b.get("pilot_id") != d.name:
        bad.append("mismatched compilation handoff")
    for n, digest in (b.get("files") or {}).items():
        if not (d / n).is_file() or sha256(d / n) != digest:
            bad.append("changed handoff file: " + n)
    plan_file = Path(root) / b["source_plan"]["file"]
    if not plan_file.is_file() or sha256(plan_file) != b["source_plan"]["sha256"]:
        bad.append("source plan changed")
    else:
        bad += plan_problems(load(plan_file))
    if load(d / "out/manifest.json").get("output_sha256") != b.get("output_sha256"):
        bad.append("manifest differs from handoff")
    if video is not None and sha256(video) != b.get("output_sha256"):
        bad.append("video differs from handoff")
    refuse(bad)
    return b


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "inputs" and len(argv) == 3:
        plan = load(argv[2])
        refuse(plan_problems(plan))
        for _, asset, sha, _ in sources(plan):
            print(asset, sha)
        for asset, sha in lipsync_assets(plan):   # E309: the lip-synced clips, downloaded and checked the same way
            print(asset, sha)
    elif cmd == "build" and len(argv) in (5, 6):
        build(*argv[2:])
    elif cmd == "voice-needed" and len(argv) == 3:
        return 0 if has_voiceover(load(argv[2])) else 1
    elif cmd == "voice-script" and len(argv) == 4:
        voice_script(*argv[2:])
    elif cmd == "voice-cut" and len(argv) == 5:
        voice_cut(*argv[2:])
    elif cmd == "qa" and len(argv) == 4:
        return qa(argv[2], argv[3])
    elif cmd == "materialize" and len(argv) == 4:
        print(materialize(argv[2], argv[3]))
    elif cmd == "check" and len(argv) == 3:
        problems = plan_problems(load(argv[2]))
        print("\n".join(problems) if problems else "PASS")
        return 1 if problems else 0
    elif cmd == "verify" and len(argv) in (3, 4):
        print(json.dumps(verify(*argv[2:])))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
