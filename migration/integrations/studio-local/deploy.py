#!/usr/bin/env python3
"""Install or update the Studio runner on the owner's PC from the public repository at one commit (or branch).
Only the runner's own files are written; profile/, ledger.json, out/ and logs/ stay as they are.

usage (PowerShell, in C:\\HeroVerse\\studio-runner):  .venv\\Scripts\\python deploy.py REF
"""
import hashlib
from pathlib import Path
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/matheusmagah-cpu/heroverse-engine/{ref}/{path}"
HERE = Path(__file__).resolve().parent
RUNNER = "migration/integrations/studio-local/"
FILES = {RUNNER + n: HERE / n for n in ("runner.py", "studio_core.py", "selectors.json", "deploy.py",
                                        "test_studio_core.py", "README.md")}


def main(ref):
    for path, dest in FILES.items():
        with urllib.request.urlopen(RAW.format(ref=ref, path=path), timeout=60) as r:
            data = r.read()
        tmp = dest.with_suffix(dest.suffix + ".new")
        tmp.write_bytes(data)
        tmp.replace(dest)
        print(f"{hashlib.sha256(data).hexdigest()[:12]} {len(data):>8} {path}")
    print(f"DEPLOYED {ref}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
