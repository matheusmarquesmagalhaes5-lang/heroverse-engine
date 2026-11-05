#!/usr/bin/env python3
"""Install or update the Flow runner on the owner's PC from the public repository at one commit (or branch).
Only the runner's own files are written; profile/, logs/ and C:\\HeroVerse\\flow\\ (ledger, clips) stay as they are.

usage (PowerShell, in C:\\HeroVerse\\flow-runner):  .venv\\Scripts\\python deploy.py REF
"""
import hashlib
from pathlib import Path
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/matheusmagah-cpu/heroverse-engine/{ref}/{path}"
HERE = Path(__file__).resolve().parent
SRC = "migration/integrations/flow/"
NAMES = ("runner.py", "flow_core.py", "mcp_server.py", "selectors.json", "deploy.py", "test_flow_core.py", "README.md")


def main(ref):
    for name in NAMES:
        with urllib.request.urlopen(RAW.format(ref=ref, path=SRC + name), timeout=60) as r:
            data = r.read()
        tmp = HERE / (name + ".new")
        tmp.write_bytes(data)
        tmp.replace(HERE / name)
        print(f"{hashlib.sha256(data).hexdigest()[:12]} {len(data):>7} {name}")
    print(f"DEPLOYED {ref}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
