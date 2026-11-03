#!/usr/bin/env python3
"""Hide the Portuguese uploads of HeroVerse (owner instruction 2026-10-17:
the channel is English-only). Reversible: privacy -> private, nothing is
deleted; the receipt keeps each video's previous privacy so it can be undone.

  plan  : list every upload of the exact channel and classify language
  apply : set privacyStatus=private for the videos in a reviewed plan file
usage: channel_privacy.py plan OUT_JSON | apply PLAN_JSON OUT_RECEIPT | unschedule PLAN_JSON OUT_RECEIPT
       | release PLAN_JSON OUT_RECEIPT
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"
CHANNEL = "UCuMF6pJQkyMzaVoAxFL86yA"
PT_WORDS = re.compile(r"(?i)\b(você|voce|não|nao|deus|são|está|para|com|uma|mais|seu|sua|vida|quando|porque|"
                      r"liderança|lideranca|talento|sucesso|nunca|sempre|hoje|isso|como|ninguém|coração|fé)\b")
EN_WORDS = re.compile(r"(?i)\b(you|your|the|god|is|not|and|this|what|why|when|are|to|of|for)\b")


def token():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials.from_authorized_user_info(json.loads(os.environ["HERO_YT_AUTHORIZED_USER_JSON"]))
    creds.refresh(Request())
    return creds.token


def call(tok, method, endpoint, params, body=None):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def language(video):
    s = video["snippet"]
    declared = (s.get("defaultAudioLanguage") or s.get("defaultLanguage") or "").lower()
    text = s.get("title", "") + " " + s.get("description", "")[:300]
    pt, en = len(PT_WORDS.findall(text)), len(EN_WORDS.findall(text))
    if declared.startswith("pt") or (pt >= 2 and pt > en):
        return "pt"
    if declared.startswith("en") or en > pt:
        return "en"
    return "unknown"


def channel_uploads(get, parts):
    """Every upload of the exact channel, as videos.list items with `parts`; shared by plan() and
    captions_audit.py (review of #424). `get(endpoint, params)` returns the decoded answer. Returns (videos, calls),
    each call 1 Data API unit. Refuses any other channel (CHANNEL_IDENTITY_MISMATCH)."""
    me = get("channels", {"part": "id,contentDetails", "mine": "true"})["items"]
    if [c["id"] for c in me] != [CHANNEL]:
        raise SystemExit("CHANNEL_IDENTITY_MISMATCH")
    playlist = me[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page, calls = [], None, 1
    while True:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if page:
            params["pageToken"] = page
        res = get("playlistItems", params)
        calls += 1
        ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        page = res.get("nextPageToken")
        if not page:
            break
    videos = []
    for start in range(0, len(ids), 50):
        videos += get("videos", {"part": parts, "id": ",".join(ids[start:start + 50])}).get("items", [])
        calls += 1
    return videos, calls


def plan(out):
    tok = token()
    raw, _ = channel_uploads(lambda endpoint, params: call(tok, "GET", endpoint, params),
                             "snippet,status,statistics,contentDetails")
    videos = [{"video_id": v["id"], "title": v["snippet"]["title"], "published_at": v["snippet"]["publishedAt"],
               "privacy": v["status"]["privacyStatus"], "language": language(v),
               "declared_language": v["snippet"].get("defaultAudioLanguage") or v["snippet"].get("defaultLanguage"),
               "views": int(v.get("statistics", {}).get("viewCount", 0)), "duration": v["contentDetails"].get("duration")}
              for v in raw]
    to_hide = [v["video_id"] for v in videos if v["language"] == "pt" and v["privacy"] != "private"]
    record = {"version": "channel-privacy-plan-v1", "channel_id": CHANNEL, "uploads": len(videos),
              "by_language": {k: sum(v["language"] == k for v in videos) for k in ("pt", "en", "unknown")},
              "to_hide": to_hide, "videos": videos}
    Path(out).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: record[k] for k in ("uploads", "by_language")} | {"to_hide": len(to_hide)}))


def apply(plan_path, out):
    plan_record = json.loads(Path(plan_path).read_text())
    if plan_record["channel_id"] != CHANNEL:
        raise SystemExit("CHANNEL_IDENTITY_MISMATCH")
    tok = token()
    receipt = []
    limit = int(os.environ.get("MAX_CHANGES", "40"))  # 50 quota units per update
    for vid in plan_record["to_hide"]:
        if sum(r["result"] == "HIDDEN" for r in receipt) >= limit:
            break
        current = call(tok, "GET", "videos", {"part": "status,snippet", "id": vid})["items"]
        if current and current[0]["status"]["privacyStatus"] == "private":
            continue
        if not current or current[0]["snippet"]["channelId"] != CHANNEL:
            receipt.append({"video_id": vid, "result": "SKIPPED_NOT_OWNED_OR_MISSING"})
            continue
        status = current[0]["status"]
        before = status["privacyStatus"]
        if before == "private":
            receipt.append({"video_id": vid, "before": before, "result": "ALREADY_PRIVATE"})
            continue
        body = {"id": vid, "status": {"privacyStatus": "private", "embeddable": status.get("embeddable", True),
                                      "license": status.get("license", "youtube"),
                                      "publicStatsViewable": status.get("publicStatsViewable", True),
                                      "selfDeclaredMadeForKids": status.get("madeForKids", False)}}
        after = call(tok, "PUT", "videos", {"part": "status"}, body)["status"]["privacyStatus"]
        receipt.append({"video_id": vid, "before": before, "after": after, "result": "HIDDEN" if after == "private" else "UNEXPECTED"})
    Path(out).write_text(json.dumps({"version": "channel-privacy-receipt-v1", "channel_id": CHANNEL,
                                     "plan": Path(plan_path).name, "undo": "set each video back to its 'before' privacy",
                                     "changes": receipt}, indent=1) + "\n")
    print(json.dumps({"hidden": sum(r["result"] == "HIDDEN" for r in receipt), "total": len(receipt)}))


def unschedule(plan_path, out):
    """Owner hold: each listed video becomes private with no pending publishAt (a scheduled upload already is
    private, so apply() would skip it and it would still go public at its time). Reversible: the receipt keeps
    the old publishAt.
    A hold only stops what is not public yet (owner, 2026-10-26: the scheduled prayer longs): a video that is already
    public is never changed here (SKIPPED_ALREADY_PUBLIC; hiding a public video is apply() with its own reviewed
    plan), and one already private with no publishAt is left as it is (ALREADY_UNSCHEDULED, no write)."""
    plan_record = json.loads(Path(plan_path).read_text())
    if plan_record["channel_id"] != CHANNEL:
        raise SystemExit("CHANNEL_IDENTITY_MISMATCH")
    tok = token()
    receipt = []
    for vid in plan_record["to_unschedule"]:
        current = call(tok, "GET", "videos", {"part": "status,snippet", "id": vid})["items"]
        if not current or current[0]["snippet"]["channelId"] != CHANNEL:
            receipt.append({"video_id": vid, "result": "SKIPPED_NOT_OWNED_OR_MISSING"})
            continue
        status = current[0]["status"]
        before = {"privacy": status["privacyStatus"], "publishAt": status.get("publishAt")}
        if before["privacy"] == "public":
            receipt.append({"video_id": vid, "before": before, "result": "SKIPPED_ALREADY_PUBLIC"})
            continue
        if before["privacy"] == "private" and not before["publishAt"]:
            receipt.append({"video_id": vid, "before": before, "result": "ALREADY_UNSCHEDULED"})
            continue
        body = {"id": vid, "status": {"privacyStatus": "private", "embeddable": status.get("embeddable", True),
                                      "license": status.get("license", "youtube"),
                                      "publicStatsViewable": status.get("publicStatsViewable", True),
                                      "selfDeclaredMadeForKids": status.get("madeForKids", False)}}
        after = call(tok, "PUT", "videos", {"part": "status"}, body)["status"]
        ok = after["privacyStatus"] == "private" and not after.get("publishAt")
        receipt.append({"video_id": vid, "before": before, "after": {"privacy": after["privacyStatus"],
                        "publishAt": after.get("publishAt")}, "result": "UNSCHEDULED" if ok else "UNEXPECTED"})
    public = [r["video_id"] for r in receipt if r["result"] == "SKIPPED_ALREADY_PUBLIC"]
    Path(out).write_text(json.dumps({"version": "channel-unschedule-receipt-v1", "channel_id": CHANNEL,
                                     "plan": Path(plan_path).name, "undo": "set each video back to its 'before'",
                                     "already_public_not_changed": public,
                                     "changes": receipt}, indent=1) + "\n")
    for vid in public:   # a skip, never a hide: stated plainly in the log and as an Actions warning
        print(f"HELD_VIDEO_ALREADY_PUBLIC {vid}: it was public before this run; left public, not changed "
              f"(hiding it is channel_privacy.py apply with a reviewed plan)")
        print(f"::warning::HELD_VIDEO_ALREADY_PUBLIC {vid} was already public; the hold did not change it")
    print(json.dumps({"unscheduled": sum(r["result"] == "UNSCHEDULED" for r in receipt), "total": len(receipt),
                      "already_public_not_changed": public, "changes": receipt}))  # public ids and statuses only
    if any(r["result"] not in ("UNSCHEDULED", "ALREADY_UNSCHEDULED", "SKIPPED_ALREADY_PUBLIC") for r in receipt):
        raise SystemExit("UNSCHEDULE_INCOMPLETE")


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "migration/publish/ledger.json"
HOLD_PLAN = ROOT / "migration/channel/hold-plan.json"
PUBLICATION_HOLD = ROOT / "migration/ops/PUBLICATION_HOLD"


def release_problems(item, ledger, hold, binding=None):
    """Offline checks for one release entry (owner 2026-11-03: the held long goes public as it is). Fail closed:
    the video must be the upload the ledger recorded for the pilot's exact approved file, must no longer be in the
    hold plan, and the pilot's publication evidence (QA, APPROVAL, manifest, prepublish gate) must still bind that file."""
    vid, pilot = item.get("video_id"), item.get("pilot")
    if not vid or not re.fullmatch(r"pilot-\d{3}", pilot or ""):
        return ["RELEASE_ENTRY_INVALID"]
    problems = []
    if vid in (hold.get("to_unschedule") or []):
        problems.append("VIDEO_STILL_IN_HOLD_PLAN")
    try:
        sha = json.loads((ROOT / "migration/production" / pilot / "out/qa.json").read_text())["output_sha256"]
    except (OSError, ValueError, KeyError):
        return problems + ["QA_UNREADABLE"]
    if (ledger.get("entries", {}).get(f"{pilot}:{sha}") or {}).get("video_id") != vid:
        problems.append("VIDEO_NOT_THE_LEDGER_UPLOAD_OF_THIS_FILE")
    problems += (binding or publication_binding)(pilot)
    return problems


def publication_binding(pilot):
    """The same fail-closed revalidation publish.yml runs before an upload (publication_binding.py)."""
    done = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "migration/publish/publication_binding.py"),
                           str(ROOT / "migration/production" / pilot)], capture_output=True, text=True)
    return [] if done.returncode == 0 else ["PUBLICATION_BINDING_FAILED " + done.stdout.strip()[:300]]


def release(plan_path, out):
    """Release a held, already-uploaded and already-approved video: privacy -> public now (no publishAt).
    Never uploads, never approves, never changes a video that is already public. Reversible by hand: the receipt
    keeps the previous status. The ledger entry of the exact file records the release."""
    plan_record = json.loads(Path(plan_path).read_text())
    if plan_record["channel_id"] != CHANNEL:
        raise SystemExit("CHANNEL_IDENTITY_MISMATCH")
    if PUBLICATION_HOLD.exists():
        raise SystemExit("PUBLICATION_HOLD")
    ledger = json.loads(LEDGER.read_text())
    hold = json.loads(HOLD_PLAN.read_text())
    tok = token()
    receipt = []
    for item in plan_record["releases"]:
        vid = item.get("video_id")
        problems = release_problems(item, ledger, hold)
        if problems:
            receipt.append({"video_id": vid, "result": "REFUSED", "problems": problems})
            continue
        current = call(tok, "GET", "videos", {"part": "status,snippet", "id": vid})["items"]
        if not current or current[0]["snippet"]["channelId"] != CHANNEL:
            receipt.append({"video_id": vid, "result": "SKIPPED_NOT_OWNED_OR_MISSING"})
            continue
        status = current[0]["status"]
        before = {"privacy": status["privacyStatus"], "publishAt": status.get("publishAt"),
                  "uploadStatus": status.get("uploadStatus")}
        if before["privacy"] == "public":
            receipt.append({"video_id": vid, "before": before, "result": "ALREADY_PUBLIC"})
            continue
        if before["uploadStatus"] not in ("uploaded", "processed"):
            receipt.append({"video_id": vid, "before": before, "result": "REFUSED", "problems": ["UPLOAD_NOT_USABLE"]})
            continue
        body = {"id": vid, "status": {"privacyStatus": "public", "embeddable": status.get("embeddable", True),
                                      "license": status.get("license", "youtube"),
                                      "publicStatsViewable": status.get("publicStatsViewable", True),
                                      "selfDeclaredMadeForKids": status.get("madeForKids", False),
                                      "containsSyntheticMedia": status.get("containsSyntheticMedia", True)}}
        call(tok, "PUT", "videos", {"part": "status"}, body)
        read = call(tok, "GET", "videos", {"part": "status,snippet", "id": vid})["items"][0]["status"]   # the read-back
        ok = read["privacyStatus"] == "public"
        receipt.append({"video_id": vid, "before": before,
                        "after": {"privacy": read["privacyStatus"], "publishAt": read.get("publishAt"),
                                  "uploadStatus": read.get("uploadStatus")},
                        "verified_at": datetime.now(timezone.utc).isoformat(), "result": "RELEASED" if ok else "UNEXPECTED"})
        if ok:
            key = f"{item['pilot']}:" + json.loads((ROOT / "migration/production" / item["pilot"] / "out/qa.json").read_text())["output_sha256"]
            ledger["entries"][key]["released"] = {"at": receipt[-1]["verified_at"], "privacy": "public",
                                                  "receipt": Path(out).name, "plan": Path(plan_path).name}
            LEDGER.write_text(json.dumps(ledger, indent=1) + "\n")
    Path(out).write_text(json.dumps({"version": "channel-release-receipt-v1", "channel_id": CHANNEL,
                                     "plan": Path(plan_path).name, "reason": plan_record.get("reason"),
                                     "undo": "set the video back to its 'before' privacy (and publishAt)",
                                     "changes": receipt}, indent=1) + "\n")
    print(json.dumps({"released": sum(r["result"] == "RELEASED" for r in receipt), "total": len(receipt), "changes": receipt}))
    if any(r["result"] not in ("RELEASED", "ALREADY_PUBLIC") for r in receipt):
        raise SystemExit("RELEASE_INCOMPLETE")


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2])
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "unschedule":
        unschedule(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "release":
        release(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
