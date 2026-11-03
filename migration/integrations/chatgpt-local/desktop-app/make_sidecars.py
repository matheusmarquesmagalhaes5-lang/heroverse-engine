#!/usr/bin/env python3
"""Candidate sidecars for the ChatGPT desktop stills, from C:\\HeroVerse\\log.txt DONE lines and the stills records.
usage: make_sidecars.py LOG PLAN_ID RUN ASPECT   (writes stills/candidates/<still>-<run>-1.json next to each jpg)"""
import hashlib
import json
import re
import sys
from pathlib import Path

BIBLE = Path(__file__).resolve().parents[3] / "production/bible"


def main(log, plan, run, aspect):
    size = [1080, 1920] if aspect == "9:16" else [1920, 1080]
    shape = "9:16 vertical portrait" if aspect == "9:16" else "16:9 landscape"
    done = {}
    for m in re.finditer(r"DONE (\S+) png_sha256=([0-9a-f]{64}) png_size=(\d+) w=(\d+) h=(\d+)", Path(log).read_text(errors="ignore")):
        done[m.group(1)] = m.groups()[1:]
    for still, (sha, nbytes, w, h) in sorted(done.items()):
        if not still.startswith(plan + "-"):
            continue
        rec = json.loads((BIBLE / "stills" / f"{still}.json").read_text())
        cand = f"{still}-{run}-1"
        jpg = BIBLE / "stills/candidates" / f"{cand}.jpg"
        if not jpg.is_file():
            continue
        out = {"id": cand, "still": still, "episode": rec["episode"], "shot": rec["shot"], "run": run, "status": "DRAFT",
               "prompt": rec["prompt"], "sent_prompt": f"Create an image, {shape}, no text. " + rec["prompt"].replace("'", "\u2019"),
               "engine": "chatgpt-desktop", "models": ["chatgpt-images"],
               "generated_by": "ChatGPT Windows app on the owner's PC (Create image), one request at a time",
               "source": "chatgpt-desktop",
               "download": {"file": f"{still}.png", "sha256": sha, "size_bytes": int(nbytes), "pixels": [int(w), int(h)]},
               "references": [],
               "licence": {"note": "OpenAI Terms of Use: the user owns the Output; made at the owner's request in his own session (README Licence and account risk)"},
               "upscaler": f"System.Drawing HighQualityBicubic centre crop to {aspect} -> {size[0]}x{size[1]}, JPEG quality 93",
               "aspect_ratio": aspect, "size": size,
               "repo_path": f"migration/production/bible/stills/candidates/{cand}.jpg",
               "sha256": hashlib.sha256(jpg.read_bytes()).hexdigest()}
        (jpg.with_suffix(".json")).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
        print("sidecar", cand)


if __name__ == "__main__":
    main(*sys.argv[1:5])
