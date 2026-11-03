#!/usr/bin/env python3
"""Build the YouTube Studio "related video" queue (migration/channel/studio_jobs.json).

The Data API cannot set a Short's "Vídeo relacionado" (migration/evidence/youtube-api/20261026-related-video-and-pin.json),
so the owner's-PC Studio runner (migration/integrations/studio-local) does it from this queue. This script is the cloud
half: it only decides WHICH video each Short points to, from repository files, and writes jobs. No secrets, no writes to
YouTube.

Rules (owner, 2026-11-03):
  - a cut (spec in production/bible/cuts/*.json) points to its source long (the spec's pilot);
  - an old "short:<pilot>" Short points to its recorded long_video_id;
  - any other Short points to the compilation that chapters it, else its arc's long (arcs.json), else the newest
    public long;
  - a video that is not public is skipped, and so is a target that is not public; longs get no job (the field is a
    Shorts field);
  - ALREADY_DONE Shorts (the three flood cuts, set by hand) get no job.

usage: related_map.py build [--out FILE] [--public-file JSON | --public-check]   (--public-check: YouTube oEmbed)
"""
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LEDGER = ROOT / "migration/publish/ledger.json"
ARCS = ROOT / "migration/production/bible/arcs.json"
CUTS = ROOT / "migration/production/bible/cuts"
COMPILATIONS = ROOT / "migration/production/bible/compilations"
OUT = HERE / "studio_jobs.json"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
ACTION = "related_video"
ALREADY_DONE = {"ESuoDa9sGng": "1m-NUJhkdMY", "v1ssTLntv8Y": "1m-NUJhkdMY", "qENUe7ZAu6k": "1m-NUJhkdMY"}


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def classify(entries):
    """{video_id: {kind: long|short|cut|short-old, key, uploaded_at, ...}} from the publish ledger entries."""
    videos = {}
    for key, e in entries.items():
        vid = e.get("video_id")
        if not vid:
            continue
        parts = key.split(":")
        if parts[0] == "short":
            kind, ref = "short-old", parts[1]
        elif parts[0] == "bible":
            kind, ref = ("cut" if parts[1].endswith("-cut") else "short"), parts[1]
        else:
            kind, ref = "long", parts[0]
        rec = {"kind": kind, "ref": ref, "uploaded_at": e.get("uploaded_at", ""), "long_video_id": e.get("long_video_id")}
        old = videos.get(vid)
        if old is None or rec["uploaded_at"] >= old["uploaded_at"]:
            videos[vid] = rec
    return videos


def load_cut_sources(cuts_dir):
    """{cut id: pilot of its source long}"""
    out = {}
    for p in sorted(Path(cuts_dir).glob("*.json")):
        spec = read_json(p, {})
        for c in spec.get("cuts", []):
            if spec.get("pilot") and c.get("id"):
                out[c["id"]] = spec["pilot"]
    return out


def load_compilations(comp_dir):
    """[(pilot, [short ids])]"""
    out = []
    for p in sorted(Path(comp_dir).glob("*.json")):
        d = read_json(p, {})
        if d.get("pilot"):
            out.append((d["pilot"], [c.get("short") for c in d.get("chapters", [])]))
    return out


def build(entries, arcs, cut_sources, compilations, public, already_done=ALREADY_DONE):
    """public: {video_id: title or None} of the videos that are public now. Returns (jobs, skipped)."""
    videos = classify(entries)
    pilot_video = {v["ref"]: vid for vid, v in videos.items() if v["kind"] == "long"}
    arc_long = {}
    for arc in arcs.get("arcs", []):
        pilot = (arc.get("long") or {}).get("pilot")
        for s in arc.get("shorts", []):
            arc_long[s] = pilot
    public_longs = sorted((v["uploaded_at"], vid) for vid, v in videos.items() if v["kind"] == "long" and vid in public)
    newest_long = public_longs[-1][1] if public_longs else None

    def target_for(vid, v):
        if v["kind"] == "short-old":
            return v["long_video_id"], "its source long"
        if v["kind"] == "cut":
            return pilot_video.get(cut_sources.get(v["ref"])), "cut of its source long"
        for pilot, shorts in sorted(compilations, reverse=True):   # M2: the newest compilation (highest pilot) that chapters it and is public
            t = pilot_video.get(pilot)
            if v["ref"] in shorts and t in public:
                return t, "chapter of the compilation"
        t = pilot_video.get(arc_long.get(v["ref"]))
        if t in public:
            return t, "the long of its arc"
        return newest_long, "newest public long"

    jobs, skipped = [], []
    for vid, v in sorted(videos.items(), key=lambda kv: kv[1]["uploaded_at"]):
        if v["kind"] == "long":
            continue
        if vid in already_done:
            skipped.append({"video_id": vid, "why": "ALREADY_DONE by hand", "target_video_id": already_done[vid]})
        elif vid not in public:
            skipped.append({"video_id": vid, "why": "NOT_PUBLIC"})
        else:
            target, why = target_for(vid, v)
            if not target or target == vid or not VIDEO_ID.match(target):
                skipped.append({"video_id": vid, "why": "NO_TARGET"})
            elif target not in public:
                skipped.append({"video_id": vid, "why": "TARGET_NOT_PUBLIC", "target_video_id": target})
            else:
                job = {"video_id": vid, "action": ACTION, "target_video_id": target,
                       "reason": f"{v['kind']} {v['ref']}: {why}"}
                if public.get(target):
                    job["target_title"] = public[target]
                jobs.append(job)
    return jobs, skipped


def oembed(video_id, timeout=20):
    """(is_public, title) from YouTube's unauthenticated oEmbed: 200 public; 401/403/404 private, scheduled or gone."""
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return True, json.loads(r.read()).get("title")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            return False, None
        raise


def main(argv):
    if not argv or argv[0] != "build":
        raise SystemExit(__doc__)
    out, pub_file, check = OUT, None, False
    it = iter(argv[1:])
    for a in it:
        if a == "--out":
            out = Path(next(it))
        elif a == "--public-file":
            pub_file = next(it)
        elif a == "--public-check":
            check = True
        else:
            raise SystemExit(__doc__)
    if bool(pub_file) == check:
        raise SystemExit("give exactly one of --public-file / --public-check")
    entries = read_json(LEDGER)["entries"]
    if pub_file:
        raw = read_json(pub_file)
        public = {k: None for k in raw} if isinstance(raw, list) else dict(raw)
    else:
        public = {}
        for vid in classify(entries):
            ok, title = oembed(vid)
            if ok:
                public[vid] = title
    jobs, skipped = build(entries, read_json(ARCS), load_cut_sources(CUTS), load_compilations(COMPILATIONS), public)
    doc = {"version": "studio-jobs-v1",
           "note": "Written by migration/channel/related_map.py; consumed by migration/integrations/studio-local/runner.py. "
                   "Add an entry for every newly scheduled Short (OPERATIONS.md Short route).",
           "jobs": jobs}
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"jobs={len(jobs)} skipped={len(skipped)}")
    for s in skipped:
        print("SKIP", json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
