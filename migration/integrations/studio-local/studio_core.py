"""Rules of the Studio runner that need no browser: queue validation, what is still pending, receipts.
Tested offline by test_studio_core.py on every PR."""
from datetime import datetime, timezone
import json
import re

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
ACTIONS = ("related_video",)
MAX_JOBS = 30
DONE = ("DONE", "ALREADY")          # terminal outcomes: never repeated
OUTCOMES = DONE + ("FAILED", "SKIPPED_DRY_RUN")
REPO = "matheusmagah-cpu/heroverse-engine"
QUEUE_PATH = "migration/channel/studio_jobs.json"
RECEIPT_DIR = "migration/evidence/studio"


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def job_key(job):
    return (job["video_id"], job["action"], job["target_video_id"])


def job_problem(job):
    """Why a queue entry is unusable, or None."""
    if not isinstance(job, dict):
        return "NOT_AN_OBJECT"
    if job.get("action") not in ACTIONS:
        return "UNKNOWN_ACTION"
    for k in ("video_id", "target_video_id"):
        if not VIDEO_ID.match(str(job.get(k, ""))):
            return f"BAD_{k.upper()}"
    if job["video_id"] == job["target_video_id"]:
        return "SELF_TARGET"
    return None


def parse_queue(doc):
    """(valid jobs, [(job, problem)]) from the studio_jobs.json document; duplicates collapse to the last entry."""
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("studio_jobs.json: no jobs list")
    good, bad, seen = {}, [], {}
    for j in jobs:
        p = job_problem(j)
        if p:
            bad.append((j, p))
        else:
            good[(j["video_id"], j["action"])] = j     # one target per video and action: the newest entry wins
            seen[(j["video_id"], j["action"])] = True
    return list(good.values()), bad


def done_keys(receipts):
    """Keys of jobs a receipt (or the local ledger) records as finished."""
    out = set()
    for r in receipts:
        for res in r.get("results", []):
            if res.get("outcome") in DONE:
                out.add((res["video_id"], res["action"], res["target_video_id"]))
    return out


def pending(jobs, receipts, limit=MAX_JOBS):
    done = done_keys(receipts)
    return [j for j in jobs if job_key(j) not in done][:max(0, min(limit, MAX_JOBS))]


def result(job, outcome, detail="", at=None):
    if outcome not in OUTCOMES:
        raise ValueError(outcome)
    return {"video_id": job["video_id"], "action": job["action"], "target_video_id": job["target_video_id"],
            "outcome": outcome, "detail": detail[:300], "at": iso(at or now_utc())}


def merge_receipt(existing, results, runner_name="studio-runner", at=None):
    """The day's receipt document with new results appended. Never holds anything but ids, outcomes and short details."""
    doc = existing if isinstance(existing, dict) and isinstance(existing.get("results"), list) else \
        {"version": "studio-receipt-v1", "results": []}
    doc["executor"] = runner_name
    doc["updated_at"] = iso(at or now_utc())
    doc["results"] = doc["results"] + list(results)
    return doc


def receipt_path(at=None):
    return f"{RECEIPT_DIR}/{(at or now_utc()).strftime('%Y-%m-%d')}.json"


def text_matches(shown, target_id, target_title=None, hrefs=()):
    """Does the related-video field show the target? By video id in a link, else by exact normalised title."""
    if any(target_id in (h or "") for h in hrefs):
        return True
    if target_title:
        norm = lambda s: re.sub(r"\s+", " ", s or "").strip().casefold()  # noqa: E731
        return norm(target_title) in norm(shown)
    return False


def dump(doc):
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
