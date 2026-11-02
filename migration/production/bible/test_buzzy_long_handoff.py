"""E270: a long's schedule.json is bound by its handoff; the publication time goes in publish.yml's publish_at."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buzzy_long  # noqa: E402


def test_e270_the_handoff_binds_schedule_json_so_the_time_is_a_publish_input():
    src = Path(buzzy_long.__file__).read_text()
    assert '"schedule.json", "out/manifest.json"' in src
    d = Path(__file__).resolve().parents[1] / "pilot-017"
    if d.is_dir():
        sched = json.loads((d / "schedule.json").read_text())
        assert sched.get("publish_at") is None
