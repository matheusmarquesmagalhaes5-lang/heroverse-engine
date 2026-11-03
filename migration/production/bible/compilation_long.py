#!/usr/bin/env python3
"""The "complete story" compilation long of an arc (owner, 2026-11-01; DECISIONS.md "Strategy reset", E251).

Nothing is generated here. The long is assembled from the arc's already-public Shorts: each Short's accepted master
(episode record `output_sha256`, release asset `bible-<id>-sha256-<sha>.mp4`, sha256 checked) framed for 16:9
(1920x1080: the 9:16 video centred over a blurred, darkened, scaled copy; the Short's burned captions are kept),
one chapter card before each story, and a new Keeper hook and close (two Pavo clips made at a fresh exact zero-credit
quote, committed with their zero-cost record; their audio is our own Kokoro line). Every segment fades in and out
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
PLAN_VERSION = "bible-compilation-plan-v1"
MANIFEST_VERSION = "bible-compilation-manifest-v1"
CRITERIA = "compilation-qa-criteria-v1"
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
        end = c.get("end_s")   # E254: cut the Short's own series CTA ("the full story is in the long video", "part N tomorrow")
        if end is not None and not (type(end) in (int, float) and 10 <= end < float(ep.get("seconds") or 0)):
            bad.append(f"{cid} end_s must be a number from 10 s up to the Short's length")
    if parts != sorted(parts) or len(set(parts)) != len(parts) or any(b - a != 1 for a, b in zip(parts, parts[1:])):
        bad.append("shorts are not consecutive parts in canonical order")
    for key in ("hook", "close"):
        k = plan.get(key) or {}
        if "voiceover" in k:   # E281: the Keeper's Kokoro voice-over on an approved still (no Pavo clip for this segment)
            bad += voiceover_problems(key, k, root)
            continue
        if not all(isinstance(k.get(f), str) and k[f] for f in ("text", "video", "audio", "video_sha256", "audio_sha256",
                                                                   "conversation_id", "quote")):
            bad.append(key + " Keeper clip record incomplete")
            continue
        if k["quote"] != "0 credits (exact, fresh)":
            bad.append(key + " clip was not made at an exact zero-credit quote")
        for f in ("video", "audio"):
            p = Path(root) / k[f]
            if not p.is_file() or sha256(p) != k[f + "_sha256"]:
                bad.append(f"{key} {f} missing or changed")
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
    p = Path(root) / str(v.get("still", ""))
    if not p.is_file() or sha256(p) != v.get("still_sha256"):
        out.append(f"{key} still missing or changed")
    else:
        approved = Path(root) / "migration/production/bible/stills" / f"{v.get('approved_still')}.json"
        if not approved.is_file() or load(approved).get("status") != "APPROVED" \
                or load(approved).get("sha256") != v["still_sha256"]:
            out.append(f"{key} still is not an approved still of that sha256")
    return out


def keeper_record(k):
    """The manifest's record of a Keeper segment: the Pavo clip's job and hashes, or the voice-over's still and Pavo attempt."""
    if "voiceover" in k:
        return {"quote": k["quote"], "voice_over": {f: k["voiceover"][f] for f in ("approved_still", "still_sha256", "voice_id", "speed")},
                "pavo_attempt": k["pavo_attempt"]}
    return {f: k[f] for f in ("conversation_id", "quote", "video_sha256", "audio_sha256")}


def has_voiceover(plan):
    return any("voiceover" in (plan.get(key) or {}) for key in ("hook", "close"))


def voice_script(plan_path, work):
    """WORK/voice-script.json for pilot_render.py voice: the voice-over lines of the plan (segment id = hook / close)."""
    plan = load(plan_path)
    refuse(plan_problems(plan))
    segs = [{"id": key, "text": plan[key]["text"], "pause_after": 0.0} for key in ("hook", "close") if "voiceover" in plan[key]]
    save(Path(work) / "voice-script.json", {"voice": {"voice_id": VOICE_ID, "speed": 1.0}, "segments": segs})


def voice_cut(plan_path, work, voice_dir):
    """The Kokoro lines of WORK/voice.wav cut at their own sentence times into VOICE_DIR/<hook|close>.wav."""
    plan = load(plan_path)
    tl = load(Path(work) / "timeline.json")
    Path(voice_dir).mkdir(parents=True, exist_ok=True)
    for key in ("hook", "close"):
        if "voiceover" not in plan[key]:
            continue
        mine = [x for x in tl["sentences"] if x["segment"] == key]
        if not mine:
            raise SystemExit(f"VOICE_LINE_MISSING {key}")
        a, b = mine[0]["start"], mine[-1]["end"]
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", Path(work) / "voice.wav",
             "-c:a", "pcm_s16le", Path(voice_dir) / f"{key}.wav"])


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


def render_long(src, out, end=None, card=None):
    """A public 16:9 long as a chapter: no blurred framing (it already is 1920x1080), same card, fades and gain."""
    d = duration(src) if end is None else min(duration(src), float(end))
    v, a = fades(d)
    files = []
    for n, t in enumerate(card or ()):
        p = Path(f"{Path(out).with_suffix('')}.card{n}.txt")
        p.write_text(t)
        files.append(p)
    graph = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
             f"{card_overlay(card, files)},{v}[v];"
             f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(src)},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-t", f"{d:.3f}", *ENC, out])
    for p in files:
        p.unlink()


def render_keeper(video, audio, out):
    """Keeper clip at 16:9 with a still beat (BEAT) at each end: first/last frame held, our own line starts after the
    first beat; its audio is our Kokoro wav, so nothing depends on the clip's own sound."""
    d = duration(video) + 2 * BEAT
    v, a = fades(d)
    graph = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,tpad=start_mode=clone:start_duration={BEAT}:"
             f"stop_mode=clone:stop_duration={BEAT},{v}[v];"
             f"[1:a]aresample=48000,aformat=channel_layouts=stereo,{gain_filter(audio)},adelay={int(BEAT * 1000)}:all=1,"
             f"apad=whole_dur={d:.3f},{a}[a]")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-i", audio, "-filter_complex", graph, "-map", "[v]",
         "-map", "[a]", "-t", f"{d:.3f}", *ENC, out])


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


def render_key(plan, key, voice_dir, out):
    k = plan[key]
    if "voiceover" in k:
        wav = Path(voice_dir or "") / f"{key}.wav"
        if not wav.is_file():
            raise SystemExit(f"VOICE_LINE_MISSING {key} (compilation_long.py voice-cut first)")
        render_keeper_still(ROOT / k["voiceover"]["still"], wav, out)
    else:
        render_keeper(ROOT / k["video"], ROOT / k["audio"], out)


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
    plan = load(plan_path)
    refuse(plan_problems(plan))
    src_dir, out = Path(src_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    segs, rows = [], []

    def add(kind, name, path, **extra):
        segs.append(path)
        rows.append({"kind": kind, "name": name, "seconds": round(duration(path), 3), **extra})

    seg = out / "segments"
    seg.mkdir(exist_ok=True)
    render_key(plan, "hook", voice_dir, seg / "00-hook.mp4")
    add("hook", "hook", seg / "00-hook.mp4")
    verified = []
    for k, (sid, asset, sha, ep) in enumerate(sources(plan), 1):
        master = src_dir / asset
        if not master.is_file() or sha256(master) != sha:
            raise SystemExit(f"SOURCE_SHA256_MISMATCH {sid}")
        verified.append({"short": sid, "asset": asset, "sha256": sha, "video_id": ep["video_id"], "seconds": ep["seconds"]})
        c = plan["chapters"][k - 1]
        card = (f"PART {k} OF {len(plan['chapters'])}", c["title"], c["reference"] + " (KJV)")
        kind = "long" if is_long(c) else "short"
        (render_long if is_long(c) else render_short)(master, seg / f"{k:02d}b-short.mp4", c.get("end_s"), card)
        add(kind, sid, seg / f"{k:02d}b-short.mp4", source_sha256=sha, chapter=c["title"],
            **({"end_s": c["end_s"]} if c.get("end_s") else {}))
    render_key(plan, "close", voice_dir, seg / "99-close.mp4")
    add("close", "close", seg / "99-close.mp4")
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
    save(out / "sources.json", verified)
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", master, "-vf",
         f"fps=20/{duration(master):.3f},scale=480:270,tile=5x4", "-frames:v", "1", "-q:v", "3", out / "sheet.jpg"])
    print(json.dumps({"output_sha256": sha, "byte_size": master.stat().st_size, "seconds": round(duration(master), 3)}))


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
    checks = {
        "full_decode_without_errors": dec.returncode == 0 and not dec.stderr.strip(),
        "video_format_1920x1080_30fps": (probe["width"], probe["height"]) == (W, H) and abs(fps(probe["avg_frame_rate"]) - FPS) < FPS_TOLERANCE,
        "duration_is_sum_of_segments": abs(dur - expected) < 1.0,
        "no_padding": dur <= sum(s["seconds"] for s in src) + 30 + len(src) * (CARD + 1.0),
        "integrated_lufs_band": LUFS_BAND[0] <= lufs <= LUFS_BAND[1],
        "true_peak_ceiling": peak <= TRUE_PEAK_MAX,
        "sources_are_the_public_masters_by_sha": [s["short"] for s in src] == [chapter_id(c) for c in plan["chapters"]]
        and all(len(s["sha256"]) == 64 for s in src) and [r["source_sha256"] for r in shorts] == [s["sha256"] for s in src],
        "canonical_order": [r["kind"] for r in tl["segments"]] == ["hook"] + ["long" if is_long(c) else "short" for c in plan["chapters"]] + ["close"]
        and [r.get("chapter") for r in shorts] == [c["title"] for c in plan["chapters"]],   # E258: card over each Short
        "keeper_clips_zero_credit": all(plan[key]["quote"] in ("0 credits (exact, fresh)", VOICEOVER_QUOTE) for key in ("hook", "close")),
        "music_and_voice_owned": True,   # the Shorts' own recorded sources (Kokoro voice, owned music) and our Kokoro hook/close
    }
    doc = {"version": "compilation-qa-v1", "criteria_version": CRITERIA,
           "criteria_sha256": sha256(ROOT / "migration/production/qa_criteria_compilation_v1.json"),
           "output_sha256": sha, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
           "measured": {"seconds": round(dur, 3), "lufs": lufs, "true_peak_dbfs": peak, "frame_rate": probe["avg_frame_rate"]}}
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
    stories = [(r["start"], plan["chapters"][i]["title"]) for i, r in enumerate(x for x in segs if x["kind"] in ("short", "long"))]
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
    segs = [{"kind": "hook", "text": plan["hook"]["text"]}]
    for c in plan["chapters"]:
        p = Path(root) / "migration/production/bible/plans" / f"{chapter_id(c)}.json"
        lines = []
        if p.is_file() and not is_long(c):
            lines = [s["line"] for s in load(p).get("shots", []) if isinstance(s.get("line"), str) and s["line"].strip()]
        segs.append({"kind": "long" if is_long(c) else "short", "short": chapter_id(c), "text": " ".join(lines) or c["title"]})
    segs.append({"kind": "close", "text": plan["close"]["text"]})
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
    script = {"version": "bible-compilation-script-v1", "pilot_id": plan["pilot"], "archetype": ARCHETYPE, "series": SERIES,
              "episode": plan["id"], "working_title": plan["title"], "criteria_version": CRITERIA,
              "shorts": [chapter_id(c) for c in plan["chapters"]],
              "hook": {"text": plan["hook"]["text"]}, "close": {"text": plan["close"]["text"]},
              "segments": script_segments(plan, root)}   # E258: three_stage critique reads the whole spoken text
    manifest = {"version": MANIFEST_VERSION, "pilot_id": plan["pilot"], "compilation": plan["id"], "output_sha256": sha,
                "output_seconds": round(dur, 3), "criteria_version": CRITERIA, "burned_captions": "kept from the Shorts",
                "sources": load(out / "sources.json"), "segments": manifest_tl["segments"], "chapters": rows,
                "keeper_clips": {k: keeper_record(plan[k]) for k in ("hook", "close")}}
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
    elif cmd == "verify" and len(argv) in (3, 4):
        print(json.dumps(verify(*argv[2:])))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
