#!/usr/bin/env python3
"""Audience retention and traffic sources of our videos, so the Short -> long funnel is measured (owner, 2026-11-04).

goal_report.py already reads the YouTube Analytics API v2 (`youtubeanalytics.googleapis.com/v2/reports`) for watch
hours and a per-long traffic-source funnel. This adds, with the SAME credential (HERO_YT_AUTHORIZED_USER_JSON, scope
yt-analytics.readonly, token through market_panel.access_token) and no other service:
  - audience retention per video: the `elapsedVideoTimeRatio` report (audienceWatchRatio, relativeRetentionPerformance),
    kept as a 20-point curve plus the retention at 25 / 50 / 75 % and at the end;
  - traffic sources per video (`insightTrafficSourceType`: views, minutes, average view duration) grouped as
    Shorts feed (SHORTS), related (RELATED_VIDEO), browse (SUBSCRIBER, the API's name for Studio's Browse features),
    search (YT_SEARCH) and the rest; the raw types are always kept;
  - for each long: the RELATED_VIDEO referrers (`insightTrafficSourceDetail`) resolved to our own Shorts, and the top
    search terms, so "Short -> long" is counted from our Shorts, not only from the SHORTS source.
It writes daily-report/audience.json and appends "Audience retention and traffic sources" to daily-report/latest.md.
Read-only, bounded (MAX_CALLS Analytics queries, MAX_SECONDS), and it never fails the daily report: no data or any error
is NO_DATA / UNKNOWN with a reason, and the last good numbers are kept. No spend: Analytics API quota only.
usage: audience_report.py DAILY_REPORT_DIR [PUBLISH_LEDGER]
       audience_report.py --step-failed RC DAILY_REPORT_DIR
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reach_report as rr  # noqa: E402  (no-redirect opener, secret-free error reasons, video classification)

ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
HOST = "youtubeanalytics.googleapis.com"
HEADING = "## Audience retention and traffic sources (YouTube Analytics API; Short -> long funnel)"
DAYS = 90
MAX_CALLS, MAX_SECONDS, MAX_SHORTS, MAX_LONGS = 160, 120, 30, 10
SOURCE_METRICS = "views,estimatedMinutesWatched,averageViewDuration"
GROUPS = {"shorts_feed": ("SHORTS",), "related": ("RELATED_VIDEO",), "browse": ("SUBSCRIBER",),
          "search": ("YT_SEARCH",), "channel_pages": ("YT_CHANNEL", "YT_OTHER_PAGE"), "external": ("EXT_URL",),
          "playlist": ("PLAYLIST",), "end_screen_notification": ("END_SCREEN", "NOTIFICATION")}
CURVE_POINTS = 20


class Query:
    """The only network layer (tests pass a fake with .rows(...))."""
    def __init__(self, token, opener=None):
        self.token, self.opener, self.calls = token, opener or rr.make_opener(), 0

    def rows(self, start, end, metrics, dimensions, filters, sort=None, limit=None):
        q = {"ids": "channel==MINE", "startDate": start, "endDate": end, "metrics": metrics, "dimensions": dimensions,
             "filters": filters}
        if sort:
            q["sort"] = sort
        if limit:
            q["maxResults"] = limit
        url = ANALYTICS + "?" + urllib.parse.urlencode(q)
        if urllib.parse.urlsplit(url).hostname != HOST:
            raise ValueError("HOST_REFUSED")
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        req.add_unredirected_header("Authorization", "Bearer " + self.token)
        self.calls += 1
        with self.opener(req, timeout=30) as r:
            body = r.read(4_000_001)
        if len(body) > 4_000_000:
            raise ValueError("RESPONSE_CAP")
        return json.loads(body or b"{}").get("rows") or []


def retention(rows):
    """rows: [elapsedVideoTimeRatio, audienceWatchRatio, relativeRetentionPerformance] -> compact curve and checkpoints."""
    pts = sorted((float(r[0]), float(r[1]), None if r[2] is None else float(r[2])) for r in rows if len(r) >= 3)
    if not pts:
        return None

    def at(x):
        return round(min(pts, key=lambda p: abs(p[0] - x))[1], 4)
    step = max(len(pts) // CURVE_POINTS, 1)
    rel = [p[2] for p in pts if p[2] is not None]
    return {"points": len(pts), "curve": [[round(p[0], 3), round(p[1], 4)] for p in pts[step - 1::step]][:CURVE_POINTS],
            "at_25": at(0.25), "at_50": at(0.5), "at_75": at(0.75), "at_end": round(pts[-1][1], 4),
            "start": round(pts[0][1], 4), "relative_performance_mean": round(sum(rel) / len(rel), 3) if rel else None}


def sources(rows):
    """rows: [insightTrafficSourceType, views, minutes, averageViewDuration] -> raw types and the grouped shares."""
    raw = {r[0]: {"views": int(r[1]), "minutes": round(float(r[2]), 1), "avg_view_s": round(float(r[3]), 1)} for r in rows}
    total = sum(v["views"] for v in raw.values())
    grouped, named = {}, set()
    for g, types in GROUPS.items():
        v = sum(raw[t]["views"] for t in types if t in raw)
        named |= set(types)
        grouped[g] = {"views": v, "share": round(v / total, 3) if total else None}
    rest = sum(v["views"] for t, v in raw.items() if t not in named)
    grouped["other"] = {"views": rest, "share": round(rest / total, 3) if total else None}
    return {"views": total, "raw": raw, "grouped": grouped}


def referrers(rows, shorts):
    """RELATED_VIDEO detail rows [videoId, views, minutes] -> total, views from our own Shorts, the top referrers."""
    out = [{"video": r[0], "views": int(r[1]), "our_short": r[0] in shorts} for r in rows]
    return {"views": sum(x["views"] for x in out), "from_our_shorts": sum(x["views"] for x in out if x["our_short"]),
            "top": out[:10]}


def guarded(fn, state_calls, problems, label):
    """One Analytics query: (rows or None). A 400 for one video (no data for it) is noted and skipped; a quota,
    scope or network failure propagates and stops the run with its reason."""
    try:
        return fn()
    except urllib.error.HTTPError as e:
        if e.code == 400:
            problems.append(f"{label}: HTTP 400 (no data for this video or range)")
            return None
        raise


def run(query_factory, state, videos, now, clock=time.monotonic):
    """Mutates and returns state with status OK, NO_DATA or UNKNOWN; never raises."""
    state.update(version="audience-v1", at=now.isoformat(), days=DAYS)
    state.pop("reason", None)
    problems = state["problems"] = []
    start, end = (now.date() - timedelta(days=DAYS)).isoformat(), now.date().isoformat()
    state["range"] = [start, end]
    shorts = {v["id"] for v in videos if rr.kind_of(v) == "short"}
    longs = [v for v in videos if rr.kind_of(v) == "long"]
    newest = lambda vs: sorted(vs, key=lambda v: v.get("published") or "", reverse=True)   # noqa: E731
    chosen = [(v, "long") for v in newest(longs)[:MAX_LONGS]] + \
             [(v, "short") for v in newest([v for v in videos if v["id"] in shorts])[:MAX_SHORTS]]
    per = state.setdefault("per_video", {})
    try:
        q = query_factory()
        t0 = clock()
        for v, kind in chosen:
            if q.calls >= MAX_CALLS or clock() - t0 > MAX_SECONDS:
                problems.append("call or time cap reached; the remaining videos are read next run")
                break
            vid, f = v["id"], f"video=={v['id']}"
            row = {"title": (v.get("title") or vid)[:80], "kind": kind, "published": (v.get("published") or "")[:10]}
            ret = guarded(lambda: q.rows(start, end, "audienceWatchRatio,relativeRetentionPerformance",
                                         "elapsedVideoTimeRatio", f), q.calls, problems, f"{vid} retention")
            row["retention"] = retention(ret or [])
            src = guarded(lambda: q.rows(start, end, SOURCE_METRICS, "insightTrafficSourceType", f),
                          q.calls, problems, f"{vid} sources")
            row["sources"] = sources(src or []) if src else None
            if kind == "long" and src:
                rel = guarded(lambda: q.rows(start, end, "views,estimatedMinutesWatched", "insightTrafficSourceDetail",
                                             f + ";insightTrafficSourceType==RELATED_VIDEO", "-views", 25),
                              q.calls, problems, f"{vid} related")
                row["related"] = referrers(rel or [], shorts)
                sea = guarded(lambda: q.rows(start, end, "views,estimatedMinutesWatched", "insightTrafficSourceDetail",
                                             f + ";insightTrafficSourceType==YT_SEARCH", "-views", 10),
                              q.calls, problems, f"{vid} search")
                row["search_terms"] = [{"term": str(r[0])[:60], "views": int(r[1])} for r in (sea or [])]
            if row["retention"] or row["sources"]:
                per[vid] = row
        state["calls"] = q.calls
        state["status"] = "OK" if any(r.get("retention") or r.get("sources") for r in per.values()) else "NO_DATA"
    except Exception as e:  # noqa: BLE001
        state["status"], state["reason"] = "UNKNOWN", rr.reason(e)
    state["funnel"] = funnel(per)
    return state


def funnel(per):
    """Channel-level Short -> long: for each long, views from the Shorts feed and from our own Shorts as related
    referrers, against its total views; plus the average retention of Shorts."""
    longs, tot, feed, ours = [], 0, 0, 0
    for vid, r in per.items():
        if r.get("kind") != "long" or not r.get("sources"):
            continue
        v = r["sources"]["views"]
        s = r["sources"]["grouped"]["shorts_feed"]["views"]
        o = (r.get("related") or {}).get("from_our_shorts", 0)
        tot, feed, ours = tot + v, feed + s, ours + o
        longs.append({"video": vid, "title": r["title"], "views": v, "from_shorts_feed": s, "from_our_shorts_related": o,
                      "share": round((s + o) / v, 3) if v else None})
    ends = [r["retention"]["at_end"] for r in per.values() if r.get("kind") == "short" and r.get("retention")]
    return {"long_views": tot, "from_shorts_feed": feed, "from_our_shorts_related": ours,
            "share_from_shorts": round((feed + ours) / tot, 3) if tot else None, "longs": longs,
            "shorts_with_retention": len(ends), "shorts_mean_retention_at_end": round(sum(ends) / len(ends), 3) if ends else None,
            "note": "SHORTS source and RELATED_VIDEO referrers that are our Shorts can overlap; read them as bounds, not a sum"}


def pct(x):
    return "-" if x is None else f"{x * 100:.0f} %"


def section(s):
    md = ["", HEADING,
          "Source: YouTube Analytics API, last 90 days, same credential as the goal report. Retention is the share of the "
          "audience still watching at that point of the video (audienceWatchRatio). Browse = the API's SUBSCRIBER type."]
    if s["status"] == "UNKNOWN":
        md += ["| status | reason |", "|---|---|", f"| UNKNOWN | {s['reason']} |"]
    elif s["status"] == "NO_DATA":
        md.append("- **NO_DATA**: the API returned no retention or source rows yet for these videos.")
    f = s.get("funnel") or {}
    if f.get("longs") is not None and s.get("per_video"):
        md.append(f"- Short -> long: {f['long_views']:,} long views, {f['from_shorts_feed']:,} from the Shorts feed, "
                  f"{f['from_our_shorts_related']:,} from our own Shorts as related referrers "
                  f"(share {pct(f['share_from_shorts'])}); mean Short retention at the end {pct(f['shorts_mean_retention_at_end'])} "
                  f"over {f['shorts_with_retention']} Shorts.")
        md += ["", "| video | type | views | Shorts feed | related | browse | search | other | ret 25 / 50 / 75 / end |",
               "|---|---|---|---|---|---|---|---|---|"]
        for vid, r in sorted(s["per_video"].items(), key=lambda kv: (kv[1]["kind"], kv[1].get("published") or ""), reverse=True):
            g = ((r.get("sources") or {}).get("grouped")) or {}
            ret = r.get("retention")
            md.append(f"| {r['title'][:40].replace('|', '/')} ({vid}) | {r['kind']} | {(r.get('sources') or {}).get('views', '-')} | "
                      + " | ".join(pct((g.get(k) or {}).get("share")) for k in ("shorts_feed", "related", "browse", "search", "other"))
                      + " | " + (f"{pct(ret['at_25'])} / {pct(ret['at_50'])} / {pct(ret['at_75'])} / {pct(ret['at_end'])}" if ret else "-") + " |")
        for vid, r in s["per_video"].items():
            if r.get("related") and r["related"]["views"]:
                md.append(f"- {r['title'][:40]}: related referrers {r['related']['views']} views, "
                          f"{r['related']['from_our_shorts']} from our Shorts")
    if s.get("problems"):
        md.append("- Not read this run: " + "; ".join(s["problems"][:5]))
    return md


def main(out_dir, ledger_path=None, now=None, query_factory=None):
    now = now or datetime.now(timezone.utc)
    out = Path(out_dir)
    path = out / "audience.json"
    try:
        state = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    if query_factory is None:
        def query_factory():
            import market_panel as mp
            return Query(mp.access_token())
    s = run(query_factory, state, rr.latest_videos(out, ledger_path), now)
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    with open(out / "latest.md", "a") as f:
        f.write("\n".join(section(s)) + "\n")
    print(json.dumps({"audience": s["status"], "reason": s.get("reason"), "videos": len(s.get("per_video", {})),
                      "calls": s.get("calls")}))
    return s


def write_unknown(out, why):
    out = Path(out)
    path = out / "audience.json"
    try:
        ok = isinstance(json.loads(path.read_text()), dict)
    except (OSError, ValueError):
        ok = False
    if not ok:
        path.write_text(json.dumps({"version": "audience-v1", "status": "UNKNOWN", "reason": why}) + "\n")
    with open(out / "latest.md", "a") as f:
        f.write("\n".join(["", HEADING, "| status | reason |", "|---|---|", f"| UNKNOWN | {why} |"]) + "\n")
    print(json.dumps({"audience": "UNKNOWN", "reason": why}))


def cli(argv, main=main):
    """Whatever goes wrong, latest.md says UNKNOWN with the reason and the exit is 0 (the daily report goes on)."""
    try:
        if argv[:1] == ["--step-failed"]:
            rc = argv[1] if len(argv) > 1 and argv[1].isdigit() else "?"
            write_unknown(argv[2], f"STEP_FAILED exit {rc}" + (" (timed out)" if rc == "124" else "")
                          + ": audience_report.py did not finish; the rest of the daily report is unaffected")
            return 0
        main(*argv[:2])
    except Exception as e:  # noqa: BLE001
        try:
            write_unknown(argv[0] if argv else ".", f"CRASH {type(e).__name__}: audience_report.py failed; "
                          "the rest of the daily report is unaffected")
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:4]))
