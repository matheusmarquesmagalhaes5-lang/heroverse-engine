#!/usr/bin/env python3
"""Size a scene-stills.yml dispatch to what is left of today's FLUX allocation (read-only; dispatches nothing).

Scheduled runs kept asking for a whole plan (17 shots x 2 candidates = 34 images) after the day's allocation was
partly used, so dispatch_guard refused the run with GUARD_CF_ALLOCATION_USED and the day made no still at all
(genesis-12-short, 2026-11-04/05). This helper reads the same count the guard reads (dispatch_guard.cf_images_today,
cf_daily_images) and prints the largest `shots`/`candidates` inputs that fit, in plan order, skipping shots whose
stills are already APPROVED. The guard stays the authority: it re-checks every dispatch, and nothing here changes it.

usage: stills_fit.py PLAN_JSON [--used N] [--candidates 1-3] [--exclude id,id] [--reserve N]
  --used N        images already used today (default: read by REST like the guard; needs GH_TOKEN)
  --candidates C  preferred candidates per still (default 2); falls back to 1 when that fits more shots
  --exclude       shot ids to leave out (e.g. shots the ChatGPT app route is already making)
  --reserve N     images to leave unused (default 0)
Prints JSON: {"fit": bool, "shots": "a,b", "candidates": C, "images": n, "remaining": r, "pending": [...], ...}
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "production" / "bible"))
import dispatch_guard  # noqa: E402  (the guard's own count and cap)
import plan_check  # noqa: E402  (FRAME_FIELDS, still_record)

DEFAULT_REPO = "matheusmagah-cpu/heroverse-engine"


def pending_shots(plan, stills_dir=None, exclude=()):
    """[(shot id, still count)] in plan order: shots with a frame still that is not APPROVED yet."""
    out = []
    for shot in plan.get("shots") or []:
        sid = shot.get("id")
        if sid in exclude:
            continue
        frames = [shot[f] for f in plan_check.FRAME_FIELDS if shot.get(f)]
        todo = [s for s in frames if (plan_check.still_record(s, stills_dir) or {}).get("status") != "APPROVED"]
        if todo:
            out.append((sid, len(frames)))   # scene-stills makes every frame of a named shot
    return out


def fit(pending, remaining, prefer=2):
    """The most shots (plan order) that fit `remaining` images; ties keep the preferred candidate count."""
    best = {"shots": [], "candidates": prefer, "images": 0}
    for c in sorted({prefer, 1}, key=lambda c: (c != prefer, -c)):
        chosen, n = [], 0
        for sid, frames in pending:
            if n + frames * c > remaining:
                break
            chosen.append(sid)
            n += frames * c
        if len(chosen) > len(best["shots"]):
            best = {"shots": chosen, "candidates": c, "images": n}
    return best


def used_today(today):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    return dispatch_guard.cf_images_today(lambda p: dispatch_guard.github(p, token, repo), today)


def main(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        raise SystemExit(__doc__)
    opts = dict(zip(argv[2::2], argv[3::2]))
    unknown = set(opts) - {"--used", "--candidates", "--exclude", "--reserve"}
    if unknown or len(argv[2:]) % 2:
        raise SystemExit(__doc__)
    prefer = int(opts.get("--candidates", 2))
    if prefer not in (1, 2, 3):
        raise SystemExit("candidates must be 1-3")
    plan = json.loads(Path(argv[1]).read_text())
    exclude = {x for x in opts.get("--exclude", "").split(",") if x}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        used = int(opts["--used"]) if "--used" in opts else used_today(today)
    except dispatch_guard.Refusal as e:
        print(json.dumps({"fit": False, "error": str(e)}))
        return 1
    cap = dispatch_guard.cf_daily_images()
    remaining = max(0, cap - used - int(opts.get("--reserve", 0)))
    pending = pending_shots(plan, exclude=exclude)
    best = fit(pending, remaining, prefer)
    left = [sid for sid, _ in pending if sid not in best["shots"]]
    print(json.dumps({"fit": bool(best["shots"]), "plan": argv[1], "shots": ",".join(best["shots"]),
                      "candidates": best["candidates"], "images": best["images"], "used_today": used,
                      "daily_allocation": cap, "remaining": remaining, "pending": [s for s, _ in pending],
                      "left_for_later": left, "day_utc": today}))
    return 0 if best["shots"] or not pending else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
