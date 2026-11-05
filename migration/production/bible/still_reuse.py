#!/usr/bin/env python3
"""Same-story still reuse (owner, 2026-11-05: "Se não for abaixar a qualidade e ajudar a chegar na meta com precisão,
pode fazer."): an APPROVED still of another plan of the same story, reframed between 16:9 and 9:16, becomes a NEW
candidate of this plan's own still, reviewed and approved like any still (scene_stills.py approve ... --checked).

  candidates PLAN                     per scene shot with a `first_frame`, the APPROVED stills of other same-story plans
                                      that name what its still shows (plan_check.scene_match >= REUSE_MATCH_MIN), best
                                      first: nothing is written
  derive PLAN SHOT SOURCE RUN [--x X] [--y Y]
                                      the candidate <still>-<RUN>-1 in stills/candidates: the largest box at the plan's
                                      aspect inside SOURCE (centred, or at the given top-left), Lanczos to the plan's side
                                      (PIL), with derived_from {still, episode, sha256, prompt_sha256}, crop {box,
                                      source_size} and its own sha256. Refused, before any file, by the same
                                      plan_check.derived_still_problems and reuse_plan_problems the checker runs
                                      (REUSE_*: at most a third of the plan's stills, never under the source's line)

Nothing here approves: Claude looks at the reframed image itself and runs `scene_stills.py approve STILL CANDIDATE
--score S --note TEXT --reviewer MODEL --checked subject_centred_in_frame,quality_kept,no_god_face,matches_shot`, by PR.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_check  # noqa: E402
import scene_stills  # noqa: E402

UPSCALER = "PIL Lanczos crop to the plan's side (the same final resize as scene_stills.finalize)"


def plans(plans_dir=None):
    folder = Path(plans_dir or plan_check.REUSE_PLANS_DIR)
    for path in sorted(folder.glob("*.json")):
        try:
            yield json.loads(path.read_text())
        except ValueError:
            continue


def approved_stills(stills_dir=None):
    for path in sorted(Path(stills_dir or plan_check.STILLS_DIR).glob("*.json")):
        rec = json.loads(path.read_text())
        if rec.get("status") == "APPROVED" and not rec.get("derived_from") and isinstance(rec.get("prompt"), str):
            yield rec


def candidates(plan, stills_dir=None, plans_dir=None):
    """{shot id: [{still, episode, match}]}: same-story APPROVED stills of other plans for each framed scene shot."""
    others = {p.get("episode"): p for p in plans(plans_dir)
              if p.get("episode") != plan.get("episode") and plan_check.same_story(plan, p)}
    pool = [r for r in approved_stills(stills_dir) if r.get("episode") in others]
    out = {}
    for shot in plan.get("shots") or []:
        rec = plan_check.still_record(shot.get("first_frame"), stills_dir) if shot.get("first_frame") else None
        if shot.get("kind") != "scene" or not rec:
            continue
        rows = []
        for src in pool:
            m = plan_check.scene_match(rec.get("prompt"), plan, src["prompt"], others[src["episode"]])
            if m >= plan_check.REUSE_MATCH_MIN:
                rows.append({"still": src["id"], "episode": src["episode"], "match": round(m, 3)})
        out[shot["id"]] = sorted(rows, key=lambda r: -r["match"])
    return out


def box_for(source_size, aspect, x=None, y=None):
    """The largest [x, y, w, h] at ASPECT inside SOURCE_SIZE, centred unless a top-left is given."""
    sw, sh = source_size
    aw, ah = (int(v) for v in aspect.split(":"))
    w, h = (round(sh * aw / ah), sh) if sw / sh > aw / ah else (sw, round(sw * ah / aw))
    w, h = min(w, sw), min(h, sh)
    return [int((sw - w) // 2 if x is None else x), int((sh - h) // 2 if y is None else y), w, h]


def derive(plan, shot_id, source, run, x=None, y=None, stills_dir=None):
    from PIL import Image
    stills_dir = Path(stills_dir or plan_check.STILLS_DIR)
    if not scene_stills.RUN.fullmatch(str(run)):
        raise SystemExit(f"STILL_RUN_INVALID {run}")
    shot = next((s for s in plan.get("shots") or [] if s.get("id") == shot_id), None)
    if shot is None or shot.get("kind") != "scene" or not shot.get("first_frame"):
        raise SystemExit(f"STILL_SHOT_WITHOUT_FRAME {shot_id} (a scene shot of {plan.get('episode')} with first_frame)")
    still = shot["first_frame"]
    rec = plan_check.still_record(still, stills_dir)
    if not rec or rec.get("episode") != plan.get("episode") or rec.get("shot") != shot_id:
        raise SystemExit(f"STILL_RECORD_MISMATCH {still} (this plan's own record of {shot_id})")
    src = plan_check.still_record(source, stills_dir)
    if not src or src.get("status") != "APPROVED" or not src.get("repo_path"):
        raise SystemExit(f"REUSE_SOURCE_NOT_APPROVED {source}")
    aspect = scene_stills.aspect_of(plan)
    side = scene_stills.SIDES[aspect]
    src_path = plan_check.ROOT / src["repo_path"]
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        dims = list(im.size)
        box = box_for(dims, aspect, x, y)
        made = im.crop((box[0], box[1], box[0] + box[2], box[1] + box[3])).resize(side, Image.LANCZOS)
    cid = f"{still}-{run}-1"
    dst = stills_dir / "candidates" / f"{cid}.jpg"
    meta = {"id": cid, "still": still, "episode": plan.get("episode"), "shot": shot_id, "run": str(run),
            "status": "DRAFT", "prompt": rec.get("prompt"), "engine": "still-reuse", "source": "still-reuse",
            "derived_from": {"still": src["id"], "episode": src.get("episode"), "sha256": src.get("sha256"),
                             "repo_path": src["repo_path"],
                             "prompt_sha256": hashlib.sha256(src["prompt"].encode()).hexdigest()},
            "crop": {"box": box, "source_size": dims}, "references": [], "pavo": None, "upscaler": UPSCALER,
            "aspect_ratio": aspect, "size": list(side)}
    # refused before any file by the checker's own rule (the derivative's sha256 is not known yet: a placeholder)
    bad = plan_check.derived_still_problems(dict(rec, **meta, sha256="0" * 64), plan, stills_dir, approved=False)
    bad += plan_check.reuse_plan_problems(plan, stills_dir, pending={shot_id: src["id"]})   # the cap, the line
    if bad:
        raise SystemExit("; ".join(bad))
    dst.parent.mkdir(parents=True, exist_ok=True)
    made.save(dst, "JPEG", quality=92)
    meta.update(repo_path=scene_stills.rel(dst), sha256=scene_stills.sha256(dst))
    scene_stills.save(dst.with_suffix(".json"), meta)
    return meta


def main(argv):
    args = argv[1:]
    if len(args) == 2 and args[0] == "candidates":
        print(json.dumps(candidates(json.loads(Path(args[1]).read_text())), indent=1))
    elif len(args) in (5, 7, 9) and args[0] == "derive":
        opts = dict(zip(args[5::2], args[6::2]))
        if set(opts) - {"--x", "--y"}:
            raise SystemExit(__doc__)
        meta = derive(json.loads(Path(args[1]).read_text()), args[2], args[3], args[4],
                      x=int(opts["--x"]) if "--x" in opts else None, y=int(opts["--y"]) if "--y" in opts else None)
        print(json.dumps({"candidate": meta["id"], "crop": meta["crop"], "sha256": meta["sha256"]}))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
