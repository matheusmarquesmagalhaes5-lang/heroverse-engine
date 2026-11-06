#!/usr/bin/env python3
"""Claude Code token budget for this project: project_share (0.97, owner 2026-11-04) of the weekly cap, planned by real cost, enforced by a hook.

Sums assistant `usage` from ~/.claude/projects/*heroverse*/**/*.jsonl (subagents included) inside the current
weekly window, merges with the persisted ledger (max per session), and stops the session over budget.
Commands: status | pace | plan [--write] | costs [--write] | check [--action T] | record [--action T --actual N]
| route [--task T] | omni | omni-save RAW (OmniRoute free pool, owner 2026-11-06).
Offline, deterministic. There is no warn-only path: over the budget (or the activity's allocation) is exit 2.
See migration/SYSTEM.md "Token budget"."""
import json
import os
import re
import select
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIELDS = ("input_tokens", "cache_creation_input_tokens", "output_tokens", "cache_read_input_tokens")
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ACTIVITIES = ("long", "shorts", "clocks", "reviews_prs", "reserve")
# action type -> activity whose allocation it spends (tool_*/main_turn/pr_cycle are measured, never allocated)
ACTIVITY_OF = {"agent_long": "long", "agent_short": "shorts", "clock_daily": "clocks", "agent_mining": "clocks",
               "agent_review": "reviews_prs", "agent_plan_pr": "reviews_prs", "agent_other": "reviews_prs"}
BRIEFS = [("agent_review", r"^(code review|review pr)"), ("clock_daily", r"daily loop|daily analysis|\bclock\b"),
          ("agent_mining", r"\bmining\b|\bmine\b"),
          # 2026-11-05: tooling/calibration/research briefs often mention Shorts but are not Short production
          ("agent_other", r"\b(calibrat\w*|tool(s|ing)?|research|install\w*|adopt\w*)\b"), ("agent_short", r"\bshorts?\b"), ("agent_long", r"\blong\b"),
          ("agent_plan_pr", r"\bplan\b")]


def load_json(env, name, default=None):
    p = Path(os.environ.get(env) or HERE / name)
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        if default is None:
            raise
        return default


def load_config():
    return load_json("TOKEN_BUDGET_CONFIG", "token_budget.json")


def now_utc():
    v = os.environ.get("TOKEN_BUDGET_NOW")
    return datetime.fromisoformat(v.replace("Z", "+00:00")) if v else datetime.now(timezone.utc)


def window_start(now, cfg):
    """The most recent weekly reset at or before `now`."""
    hh, mm = map(int, cfg["reset"]["time_utc"].split(":"))
    day = DAYS.index(cfg["reset"]["weekday"].lower())
    start = now.astimezone(timezone.utc).replace(hour=hh, minute=mm, second=0, microsecond=0)
    start -= timedelta(days=(start.weekday() - day) % 7)
    if start > now:
        start -= timedelta(days=7)
    return start


def weighted(c, cfg):
    return (c.get("input_tokens", 0) + c.get("cache_creation_input_tokens", 0) + c.get("output_tokens", 0)
            + cfg["cache_read_weight"] * c.get("cache_read_input_tokens", 0))


def classify(prompt):
    """Brief type of an agent run, from its first prompt."""
    p = (prompt or "").strip().lower()
    for name, rx in BRIEFS:
        if re.search(rx, p):
            return name
    return "agent_other"


def prompt_text(o):
    c = (o.get("message") or {}).get("content")
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c or [] if isinstance(b, dict))


def read_transcript(f, start, end):
    """(first user prompt, {message id: (ts, counts, [tool_use ids by name])}, {tool_use id: result info})."""
    prompt, msgs, results = None, {}, {}
    with open(f, errors="ignore") as fh:
        for line in fh:
            try:
                o = json.loads(line)
                m = o.get("message")
                if o.get("type") == "user" and isinstance(m, dict):
                    if prompt is None:
                        prompt = prompt_text(o)
                    for b in m["content"] if isinstance(m.get("content"), list) else []:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            body = b.get("content")
                            results[b.get("tool_use_id")] = (len(json.dumps(body)), True and
                                                             any(isinstance(x, dict) and x.get("type") == "image" for x in body or []))
                    continue
                if o.get("type") != "assistant" or m.get("model") == "<synthetic>" or "usage" not in m:
                    continue
                ts = datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00"))
                if not (start <= ts < end):
                    continue
                u = m["usage"]
                v = {k: int(u.get(k) or 0) for k in FIELDS}
                tools = [(b.get("name", ""), b.get("id")) for b in m.get("content") or [] if isinstance(b, dict) and b.get("type") == "tool_use"]
                mid = m.get("id") or o.get("uuid")
                if mid not in msgs or sum(v.values()) > sum(msgs[mid][1].values()):
                    msgs[mid] = (ts, v, tools)
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
    return prompt, msgs, results


def transcripts(projects_dir, start):
    projects_dir = Path(projects_dir)
    for f in sorted(projects_dir.glob("*heroverse*/**/*.jsonl")):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) >= start:
                yield f, "/".join(f.relative_to(projects_dir).parts[1:]).removesuffix(".jsonl")
        except OSError:
            continue


def scan(projects_dir, start, end):
    """{session key: raw counts + activity} for assistant messages in [start, end). One message counts once."""
    out = {}
    for f, key in transcripts(projects_dir, start):
        try:
            prompt, msgs, _ = read_transcript(f, start, end)
        except OSError:
            continue
        s = out.setdefault(key, dict.fromkeys(FIELDS, 0))
        s["activity"] = ACTIVITY_OF[classify(prompt)] if "subagents/" in key else "reserve"
        for _, v, _ in msgs.values():
            for k in FIELDS:
                s[k] += v[k]
    return {k: v for k, v in out.items() if any(v[f] for f in FIELDS)}


def merge_max(a, b):
    """Merge two {session: counts} maps by max per field, so a restart that lost transcripts never lowers counts."""
    out = {k: dict(v) for k, v in a.items()}
    for key, v in b.items():
        cur = out.setdefault(key, dict.fromkeys(FIELDS, 0))
        for f in FIELDS:
            cur[f] = max(cur.get(f, 0), v.get(f, 0))
        cur["activity"] = v.get("activity") or cur.get("activity") or "reserve"
    return out


def ledger_path(start):
    d = Path(os.environ.get("TOKEN_BUDGET_LEDGER_DIR") or ROOT / "migration/evidence/tokens")
    return d / f"{start:%Y-%m-%d}.json"


def read_ledger(start):
    try:
        return json.loads(ledger_path(start).read_text())
    except (OSError, ValueError):
        return {}


def compute(cfg=None, now=None, use_cache=True):
    cfg = cfg or load_config()
    now = now or now_utc()
    start = window_start(now, cfg)
    cache = Path(os.environ.get("TOKEN_BUDGET_CACHE") or Path(tempfile.gettempdir()) / "heroverse-token-budget.json")
    if use_cache:
        try:
            c = json.loads(cache.read_text())
            if c["start"] == start.isoformat() and time.time() - c["at"] < cfg.get("cache_seconds", 60):
                return c["state"]
        except (OSError, ValueError, KeyError):
            pass
    projects = os.environ.get("TOKEN_BUDGET_PROJECTS_DIR") or Path.home() / ".claude/projects"
    led = read_ledger(start)
    sessions = merge_max(led.get("sessions", {}), scan(projects, start, now + timedelta(seconds=1)))
    by_activity = dict.fromkeys(ACTIVITIES, 0)
    for v in sessions.values():
        by_activity[v.get("activity", "reserve")] += weighted(v, cfg)
    used = sum(by_activity.values())
    budget = cfg["weekly_cap_tokens"] * cfg["project_share"]
    elapsed = max((now - start).total_seconds(), 1)
    state = {"window_start": start.isoformat(), "window_end": (start + timedelta(days=7)).isoformat(),
             "used": round(used), "budget": round(budget), "weekly_cap_tokens": cfg["weekly_cap_tokens"],
             "pct": round(100 * used / budget, 2), "projected_end_of_week": round(used * 7 * 86400 / elapsed),
             "by_activity": {k: round(v) for k, v in by_activity.items()}, "actions": led.get("actions", []),
             "sessions": sessions}
    if use_cache:
        try:
            cache.write_text(json.dumps({"start": start.isoformat(), "at": time.time(), "state": state}))
        except OSError:
            pass
    return state


def p90(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, -(-9 * len(xs) // 10) - 1)] if xs else 0


def cost_samples(cfg, projects_dir, start, end):
    """{action: [weighted tokens]}: main turn; each agent run by brief type; tool call by kind (the issuing turn's
    cost split over its tool calls); PR cycle (all agent runs that name the same PR)."""
    out, prs = {}, {}
    add = lambda a, x: out.setdefault(a, []).append(x)
    for f, key in transcripts(projects_dir, start):
        try:
            prompt, msgs, results = read_transcript(f, start, end)
        except OSError:
            continue
        if not msgs:
            continue
        sub = "subagents/" in key
        total = 0
        for _, v, tools in msgs.values():
            w = weighted(v, cfg)
            total += w
            if not sub:
                add("main_turn", w)
            for name, tid in tools:
                size, image = results.get(tid, (0, False))
                kind = ("Bash" if name == "Bash" else "mcp" if name.startswith("mcp__") else "agent" if name in ("Agent", "Task")
                        else "read_image" if name == "Read" and image else "read_large" if name == "Read" and size > 20000
                        else "read" if name == "Read" else "other")
                add("tool_" + kind.lower(), w / len(tools))
        if sub:
            add(classify(prompt), total)
            for n in set(re.findall(r"\bPR #?(\d{3,})", prompt or "")[:1]):
                prs[n] = prs.get(n, 0) + total
    out["pr_cycle"] = list(prs.values())
    return out


def build_costs(cfg, now, projects_dir):
    """Costs of the previous full weekly window (the last week that is complete)."""
    end = window_start(now, cfg)
    start = end - timedelta(days=7)
    acts = {}
    for a, xs in sorted(cost_samples(cfg, projects_dir, start, end).items()):
        if xs:
            acts[a] = {"n": len(xs), "mean": round(sum(xs) / len(xs)), "p90": round(p90(xs)), "activity": ACTIVITY_OF.get(a)}
    return {"_doc": "Weighted tokens per action (input + cache_creation + output + cache_read_weight * cache_read), from the "
                    "local transcripts of the window below; recomputed weekly with `token_budget.py costs --write`. "
                    "Agent run = whole subagent transcript, by brief type (first prompt). Tool call = cost of the issuing "
                    "turn / its tool calls. pr_cycle = all agent runs naming one PR. Main-session clock runs cannot be "
                    "told apart locally. Transcripts before 2026-10-27T13:22Z no longer exist.",
            "cache_read_weight": cfg["cache_read_weight"], "window_start": start.isoformat(), "window_end": end.isoformat(),
            "actions": acts}


def estimate(action, state, costs):
    """p90 of this week's recorded actuals (3 or more), else the table's p90, else 0 (unmeasured)."""
    got = [a["actual"] for a in state["actions"] if a["action"] == action]
    if len(got) >= 3:
        return p90(got)
    return costs.get("actions", {}).get(action, {}).get("p90", 0)


def build_plan(cfg, costs, plan):
    budget = cfg["weekly_cap_tokens"] * cfg["project_share"]
    c, a = plan["cadence"], costs["actions"]
    mean = lambda k: a.get(k, {}).get("mean", 0)
    want = {"long": c["long_per_week"] * mean("agent_long"), "shorts": c["shorts_per_week"] * mean("agent_short"),
            "clocks": c["clock_runs_per_week"] * mean("clock_daily") + c["mining_runs_per_week"] * mean("agent_mining"),
            "reviews_prs": c["pr_cycles_per_week"] * mean("pr_cycle")}
    room = budget * (1 - plan["reserve_share"])
    k = min(1.0, room / sum(want.values())) if sum(want.values()) else 1.0   # cadence unaffordable: scale down, say so
    alloc = {x: round(v * k) for x, v in want.items()}
    alloc["reserve"] = round(budget - sum(alloc.values()))
    return dict(plan, budget=round(budget), allocations=alloc, scaled_to_budget=round(k, 3))


def plan_text(s, plan):
    rows = [f"{'activity':12}{'allocation':>14}{'spent':>14}{'left':>14}"]
    for x in ACTIVITIES:
        al, sp = plan["allocations"][x], s["by_activity"][x]
        rows.append(f"{x:12}{al:>14,}{sp:>14,}{al - sp:>14,}")
    rows.append(f"{'total':12}{plan['budget']:>14,}{s['used']:>14,}{plan['budget'] - s['used']:>14,}")
    if plan.get("scaled_to_budget", 1) < 1:
        rows.append(f"cadence scaled to {plan['scaled_to_budget']} of its measured cost to fit the budget")
    return "\n".join(rows)


def status_text(s):
    return (f"week {s['window_start'][:16]}Z..{s['window_end'][:16]}Z\n"
            f"used {s['used']:,} of budget {s['budget']:,} ({s['pct']}%); budget is the project share of the estimated "
            f"weekly cap {s['weekly_cap_tokens']:,}\n"
            f"projected end of week {s['projected_end_of_week']:,}"
            + ("  (over budget)" if s["projected_end_of_week"] > s["budget"] else ""))


# recommended share of the hourly target by model tier: (opus, sonnet, haiku); see OPERATIONS "Model routing and weekly pacing"
MODEL_SPLIT = {"AHEAD": (0.05, 0.65, 0.30), "ON_PACE": (0.15, 0.70, 0.15), "BEHIND": (0.20, 0.70, 0.10)}
PACE_BAND = (0.85, 1.05)   # rate/target below 0.85 = BEHIND, above 1.05 = AHEAD


def message_records(projects_dir, start, end):
    """[(timestamp, weighted tokens)] for each assistant message in [start, end), from the local transcripts."""
    cfg, out = load_config(), []
    for f, _ in transcripts(projects_dir, start):
        try:
            _, msgs, _ = read_transcript(f, start, end)
        except OSError:
            continue
        out += [(ts, weighted(v, cfg)) for ts, v, _ in msgs.values()]
    return out


def pace(cfg, state, records, now):
    """Pace toward the weekly reset: use ~100% of the project budget at the reset, never earlier."""
    start = datetime.fromisoformat(state["window_start"])
    end = datetime.fromisoformat(state["window_end"])
    budget = cfg["weekly_cap_tokens"] * cfg["project_share"]
    remaining = budget - state["used"]
    hours_left = max((end - now).total_seconds() / 3600, 0.0)
    target = remaining / hours_left if hours_left else 0.0
    rate = {}
    for h in (6, 24):
        span = min(h, max((now - start).total_seconds() / 3600, 1e-9))   # a week younger than h hours: use its age
        rate[h] = sum(w for ts, w in records if ts > now - timedelta(hours=h)) / span
    basis = rate[24]
    ratio = basis / target if target > 0 else (float("inf") if basis > 0 else 1.0)
    hit_at = None
    if remaining <= 0:
        verdict, hit_at = "AHEAD", now
    elif basis * hours_left > remaining:
        hit_at = now + timedelta(hours=remaining / basis)
        verdict = "AHEAD" if ratio > PACE_BAND[1] else "ON_PACE"
    else:
        verdict = "BEHIND" if ratio < PACE_BAND[0] else "ON_PACE"
    spare = max(remaining - basis * hours_left, 0) if verdict == "BEHIND" else 0
    o, sn, hk = MODEL_SPLIT[verdict]
    split = {"opus": round(target * o), "sonnet": round(target * sn), "haiku": round(target * hk)}
    return {"verdict": verdict, "budget": round(budget), "used": state["used"], "remaining": round(remaining),
            "hours_left": round(hours_left, 1), "target_per_hour": round(target),
            "rate_6h": round(rate[6]), "rate_24h": round(rate[24]),
            "hit_cap_at": hit_at.strftime("%Y-%m-%dT%H:%MZ") if verdict == "AHEAD" and hit_at else None,
            "spare_tokens": round(spare), "split_per_hour": split, "reset": end.strftime("%Y-%m-%dT%H:%MZ")}


def pace_text(p):
    n = lambda x: f"{x / 1e6:.2f}M"
    rows = [f"pace {p['verdict']}: remaining {n(p['remaining'])} of {n(p['budget'])} in {p['hours_left']} h "
            f"(reset {p['reset']}); target {n(p['target_per_hour'])}/h",
            f"rate last 6 h {n(p['rate_6h'])}/h, last 24 h {n(p['rate_24h'])}/h"]
    if p["verdict"] == "AHEAD":
        rows.append(f"would hit the budget at {p['hit_cap_at']}, before the reset: shift work down a model tier, slow optional work")
    elif p["verdict"] == "BEHIND":
        rows.append(f"spare capacity {n(p['spare_tokens'])} can be added before the reset: pull forward queued production, never lower quality")
    else:
        rows.append("on pace: keep the current rhythm")
    s = p["split_per_hour"]
    rows.append(f"recommended per hour: opus {n(s['opus'])}, sonnet {n(s['sonnet'])}, haiku {n(s['haiku'])}")
    return "\n".join(rows)


# ---- OmniRoute pool and task routing (owner 2026-11-06: "administre os tokens agora junto com o omniroute") ----
# Two pools: the Claude weekly budget above, and the free OmniRoute combo on the owner's PC (C:\HeroVerse\
# claude-fallback.ps1). The PC writes a sanitized usage summary (migration/ops/omniroute_usage.mjs); `omni-save`
# re-sanitizes it into migration/evidence/omniroute/usage-YYYYMMDD.json; `route` decides where a task class runs.
# Quality-critical work never routes to OmniRoute; see OPERATIONS "Model routing and weekly pacing".
CRITICAL_TASKS = ("plan", "script", "kjv_text", "review", "gate", "publication", "code_pr", "approval", "generation",
                  "coordination")
OFFLOAD_TASKS = ("comment_draft", "log_summary", "evidence_summary", "research_notes", "translation_internal")
NOSPEND_TASKS = ("cut_approved_media", "scheduling")   # PC fallback only while Claude is exhausted or rate-limited
TASKS = CRITICAL_TASKS + OFFLOAD_TASKS + NOSPEND_TASKS
OMNI_STALE_HOURS = 26
OMNI_PROVIDER_FIELDS = {"connections": int, "quota_used": float, "quota_pct_remaining": float, "token_status": str,
                        "requests_24h": int, "errors_24h": int, "rate_limited_24h": int, "success_rate_pct_today": float,
                        "tokens_today": int, "exhausted": bool}
OMNI_WINDOW_FIELDS = {"used": float, "total": float, "remaining": float, "remaining_pct": float, "reset_at": str,
                      "unlimited": bool}
SECRET_RX = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|Bearer\s|[0-9a-fA-F]{32,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                       r"[0-9a-f]{12}|[^\s@\"]+@[^\s@\"]+\.[a-z]{2,}|AIza[0-9A-Za-z_-]{20,}|gsk_[A-Za-z0-9]{8,})")
NAME_RX = re.compile(r"^[a-z0-9][a-z0-9._-]{0,40}$")
FALLBACK_CMD = ("powershell -NoProfile -ExecutionPolicy Bypass -File C:\\HeroVerse\\claude-fallback.ps1 -p \"<task>\" "
                "(Desktop Commander, device Matheus; write the .ps1 with write_file, inline $ is stripped)")


def omni_dir():
    return Path(os.environ.get("TOKEN_BUDGET_OMNI_DIR") or ROOT / "migration/evidence/omniroute")


def _clean(v, kind):
    if v is None:
        return None
    if kind is bool:
        return bool(v) if isinstance(v, bool) else None
    if kind in (int, float):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return v[:40] if isinstance(v, str) and not SECRET_RX.search(v) else None


def sanitize_omni(raw):
    """Rebuild the PC summary from an allowlist: anything not named here (ids, accounts, keys) is dropped."""
    if not isinstance(raw, dict) or raw.get("schema") != "omniroute-usage-v1":
        raise ValueError("not an omniroute-usage-v1 summary")
    gen = datetime.fromisoformat(str(raw["generated_at"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    provs = {}
    for name, p in (raw.get("providers") or {}).items():
        if not isinstance(p, dict) or not NAME_RX.match(str(name)):
            continue
        q = {k: _clean(p.get(k), t) for k, t in OMNI_PROVIDER_FIELDS.items()}
        q["windows"] = {w: {k: _clean(v.get(k), t) for k, t in OMNI_WINDOW_FIELDS.items()}
                        for w, v in (p.get("windows") or {}).items() if isinstance(v, dict) and NAME_RX.match(str(w))}
        q["lockouts"] = [{"model": _clean(l.get("model"), str), "reason": _clean(l.get("reason"), str),
                          "remaining_s": _clean(l.get("remaining_s"), int)} for l in (p.get("lockouts") or [])[:20]
                         if isinstance(l, dict)]
        provs[name] = q
    tot = raw.get("totals_24h") or {}
    ft = raw.get("free_tier") or {}
    out = {"schema": "omniroute-usage-v1", "generated_at": gen.isoformat(timespec="seconds"),
           "combo": _clean(raw.get("combo"), str), "up": raw.get("up") is True,
           "errors": [e for e in (_clean(e, str) for e in (raw.get("errors") or [])[:20]) if e],
           "providers": provs,
           "totals_24h": {k: _clean(tot.get(k), int) for k in ("requests", "errors", "rate_limited")},
           "free_tier": {"steady_recurring_tokens_month": _clean(ft.get("steady_recurring_tokens_month"), int),
                         "model_count": _clean(ft.get("model_count"), int)},
           "alerts": [a for a in (_clean(a, str) if not str(a).startswith("PROVIDER_EXHAUSTED:") else str(a)[:200]
                                  for a in (raw.get("alerts") or [])[:10]) if a]}
    text = json.dumps(out, sort_keys=True)
    if SECRET_RX.search(text.replace(out["generated_at"], "")):
        raise ValueError("secret-like string survived sanitizing; refusing to save")
    return out


def omni_save(raw_path):
    out = sanitize_omni(json.loads(Path(raw_path).read_text()))
    d = omni_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"usage-{datetime.fromisoformat(out['generated_at']):%Y%m%d}.json"
    p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return p


def omni_latest(now):
    """(snapshot or None, state): state is OK, MISSING, STALE, DOWN or EXHAUSTED."""
    files = sorted(omni_dir().glob("usage-*.json"))
    if not files:
        return None, "MISSING"
    try:
        snap = json.loads(files[-1].read_text())
        age = (now - datetime.fromisoformat(snap["generated_at"])).total_seconds() / 3600
    except (OSError, ValueError, KeyError):
        return None, "MISSING"
    if age > OMNI_STALE_HOURS:
        return snap, "STALE"
    if not snap.get("up") or "OMNIROUTE_DOWN" in snap.get("alerts", []):
        return snap, "DOWN"
    if "FREE_QUOTAS_EXHAUSTED" in snap.get("alerts", []):
        return snap, "EXHAUSTED"
    return snap, "OK"


def omni_text(snap, state):
    if snap is None:
        return f"omniroute {state}: no usage snapshot in migration/evidence/omniroute/ (refresh it from the PC)"
    rows = [f"omniroute {state}: snapshot {snap['generated_at'][:16]}Z, combo {snap.get('combo')}, 24 h requests "
            f"{snap['totals_24h'].get('requests')}, errors {snap['totals_24h'].get('errors')}, 429s "
            f"{snap['totals_24h'].get('rate_limited')}"]
    for name, p in sorted(snap["providers"].items()):
        if not p.get("connections"):
            continue
        win = ", ".join(f"{w} {v.get('remaining')}/{v.get('total')}" for w, v in p.get("windows", {}).items()
                        if v.get("total"))
        rows.append(f"  {name}: {'EXHAUSTED' if p.get('exhausted') else 'ok'}, quota left "
                    f"{p.get('quota_pct_remaining')}%{', ' + win if win else ''}, 24 h {p.get('requests_24h')} req / "
                    f"{p.get('errors_24h')} err / {p.get('rate_limited_24h')} 429, locked models {len(p.get('lockouts') or [])}")
    alerts = list(snap.get("alerts") or []) + ([f"OMNIROUTE_{state}"] if state != "OK" else [])
    rows.append("alerts: " + (", ".join(dict.fromkeys(alerts)) if alerts else "none"))
    return "\n".join(rows)


def route_decision(task, verdict, claude_out, omni_state, pc="unknown"):
    """(route, reason). route: CLAUDE, OMNIROUTE_PC (claude-fallback.ps1 on the PC) or HOLD.
    claude_out = the project budget is spent or Claude is rate-limited. Unknown tasks count as critical."""
    omni_ok = omni_state == "OK" and pc != "offline"
    if task not in OFFLOAD_TASKS + NOSPEND_TASKS:
        if claude_out:
            return "HOLD", "quality-critical: never OmniRoute; it waits for Claude (limit window or the weekly reset)"
        return "CLAUDE", "quality-critical work stays on Claude"
    if claude_out:
        if omni_ok:
            return "OMNIROUTE_PC", "Claude exhausted/rate-limited: no-spend work continues on the PC through OmniRoute"
        return "HOLD", f"Claude exhausted/rate-limited and OmniRoute not usable ({omni_state}, PC {pc}): record as pending"
    if task in OFFLOAD_TASKS and verdict == "AHEAD":
        if omni_ok:
            return "OMNIROUTE_PC", "pace AHEAD: offload this low-risk, verifiable task to the free pool; Claude keeps critical work"
        return "CLAUDE", f"pace AHEAD but OmniRoute not usable ({omni_state}, PC {pc}): Claude, lowest model tier"
    if verdict == "AHEAD":
        return "CLAUDE", "pace AHEAD: production step stays on Claude at the lowest fitting tier; PC fallback only once Claude is out"
    return "CLAUDE", (f"pace {verdict}: keep it on Claude (owner wants ~100% used at the reset); "
                      "OmniRoute only if a Claude call fails")


def route_cmd(argv, cfg, projects):
    arg = lambda n: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else None
    now = now_utc()
    state = compute(cfg, now, use_cache=False)
    recs = message_records(projects, datetime.fromisoformat(state["window_start"]), now + timedelta(seconds=1))
    p = pace(cfg, state, recs, now)
    limited = "--claude-limited" in argv or os.environ.get("TOKEN_BUDGET_CLAUDE_LIMITED") == "1"
    claude_out = p["remaining"] <= 0 or limited
    pc = arg("--pc") or "unknown"
    snap, omni_state = omni_latest(now)
    tasks = [arg("--task")] if arg("--task") else list(TASKS)
    claude = "EXHAUSTED" if p["remaining"] <= 0 else "RATE_LIMITED" if limited else p["verdict"]
    rows = [f"claude {claude}: remaining {p['remaining'] / 1e6:.2f}M of {p['budget'] / 1e6:.2f}M, reset {p['reset']}, "
            f"spare {p['spare_tokens'] / 1e6:.2f}M; omniroute {omni_state}; pc {pc}"]
    result = {}
    for t in tasks:
        r, why = route_decision(t, p["verdict"], claude_out, omni_state, pc)
        result[t] = {"route": r, "reason": why}
        rows.append(f"{t}: {r} - {why}")
    if any(v["route"] == "OMNIROUTE_PC" for v in result.values()):
        rows.append("OMNIROUTE_PC = " + FALLBACK_CMD + "; first confirm list_devices shows Matheus online, else HOLD. "
                    "Its output passes the same checks (comment checks, PR, CI); it never approves, generates or publishes.")
    if "--json" in argv:
        print(json.dumps({"claude": claude, "omniroute": omni_state, "pc": pc, "routes": result}, indent=1))
    else:
        print("\n".join(rows))
    return 0


def hook_input():
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    try:
        if not select.select([sys.stdin], [], [], 0.5)[0]:
            return {}
        return json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return {}


def escape_allowed(data):
    """Over budget, the session may still report: `token_budget.py status` and `git status`, nothing else."""
    cmd = (data.get("tool_input") or {}).get("command", "") if data.get("tool_name") == "Bash" else ""
    cmd = cmd.strip()
    if not cmd or any(ch in cmd for ch in ";&|`$<>\n"):
        return False
    if cmd == "git status" or cmd.startswith("git status "):
        return True
    return cmd.startswith(("python3 -I -B migration/ops/token_budget.py status", "python3 migration/ops/token_budget.py status",
                           "python3 -I -B migration/ops/token_budget.py plan", "python3 migration/ops/token_budget.py plan"))


def hook_action(data):
    """The action a tool call spends: an agent run by the brief it carries, else the tool kind."""
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    if tool in ("Agent", "Task"):
        return classify(inp.get("prompt"))
    kind = "mcp" if tool.startswith("mcp__") else tool.lower() if tool in ("Bash", "Read") else None
    return "tool_" + kind if kind else None


def refusal(s, action, est, why):
    return (f"TOKEN_BUDGET_EXCEEDED: {why} (action {action or '-'}, estimate p90 {est:,}; project used {s['used']:,} of "
            f"{s['budget']:,} weighted tokens, {s['pct']}%, project share of the weekly cap; reset {s['window_end'][:16]}Z). "
            f"Stop; only `python3 -I -B migration/ops/token_budget.py status` and `git status` are allowed. "
            f"Report to the owner; do not work around it.")


def check(action=None, data=None):
    cfg = load_config()
    s = compute(cfg)
    data = data if data is not None else hook_input()
    action = action or hook_action(data)
    costs = load_json("TOKEN_BUDGET_COSTS", "token_costs.json", {"actions": {}})
    est = estimate(action, s, costs) if action else 0
    why = None
    if s["used"] + est >= s["budget"]:
        why = "the project budget would be crossed" if est else "the project budget is spent"
    elif action in ACTIVITY_OF:
        act = ACTIVITY_OF[action]
        alloc = load_json("TOKEN_BUDGET_PLAN", "token_plan.json", {"allocations": {}})["allocations"].get(act)
        # The project budget above is the inviolable cap (used + p90). An allocation is the plan's share: it
        # blocks once spent, never before the first action, or an allocation smaller than one p90 action
        # (long: 14.6M vs 49.2M) would forbid that activity for the whole week (E234).
        if alloc is not None and s["by_activity"][act] >= alloc:
            why = f"the {act} allocation ({alloc:,}, spent {s['by_activity'][act]:,}) is spent"
    if why and not (escape_allowed(data) or "token_budget.py status" in str(data.get("prompt", ""))):
        print(refusal(s, action, est, why), file=sys.stderr)
        return 2
    return 0


def record(action=None, actual=None):
    s = compute(use_cache=False)
    costs = load_json("TOKEN_BUDGET_COSTS", "token_costs.json", {"actions": {}})
    acts = list(s["actions"])
    if action and actual is not None:
        acts.append({"action": action, "estimate": estimate(action, s, costs), "actual": int(actual),
                     "at": now_utc().isoformat(timespec="seconds")})
    p = ledger_path(datetime.fromisoformat(s["window_start"]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"window_start": s["window_start"], "window_end": s["window_end"], "used": s["used"],
                             "budget": s["budget"], "weekly_cap_tokens": s["weekly_cap_tokens"],
                             "by_activity": s["by_activity"], "actions": acts, "sessions": s["sessions"]},
                            indent=1, sort_keys=True) + "\n")
    print(f"recorded {p}: {s['used']:,}/{s['budget']:,}")
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    arg = lambda n: argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else None
    try:
        cfg = load_config()
        projects = os.environ.get("TOKEN_BUDGET_PROJECTS_DIR") or Path.home() / ".claude/projects"
        if cmd == "status":
            print(status_text(compute(use_cache=False)))
        elif cmd == "pace":
            now = now_utc()
            state = compute(cfg, now, use_cache=False)
            recs = message_records(projects, datetime.fromisoformat(state["window_start"]), now + timedelta(seconds=1))
            print(pace_text(pace(cfg, state, recs, now)))
        elif cmd == "check":
            return check(arg("--action"))
        elif cmd == "record":
            return record(arg("--action"), arg("--actual"))
        elif cmd == "costs":
            costs = build_costs(cfg, now_utc(), projects)
            if "--write" in argv:
                (HERE / "token_costs.json").write_text(json.dumps(costs, indent=1) + "\n")
            print(json.dumps(costs["actions"], indent=1))
        elif cmd == "plan":
            plan = load_json("TOKEN_BUDGET_PLAN", "token_plan.json")
            if "--write" in argv:
                plan = build_plan(cfg, load_json("TOKEN_BUDGET_COSTS", "token_costs.json"), plan)
                (HERE / "token_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
            print(plan_text(compute(use_cache=False), plan))
        elif cmd == "route":
            return route_cmd(argv, cfg, projects)
        elif cmd == "omni":
            snap, st = omni_latest(now_utc())
            print(omni_text(snap, st))
        elif cmd == "omni-save":
            print(f"saved {omni_save(argv[2])}")
            snap, st = omni_latest(now_utc())
            print(omni_text(snap, st))
        else:
            print("usage: token_budget.py status|pace|plan|costs|check|record|route [--task T] [--pc online|offline] "
                  "[--claude-limited] [--json]|omni|omni-save RAW.json", file=sys.stderr)
            return 64
        return 0
    except Exception as e:   # a broken meter is said aloud (exit 1 = non-blocking) and never looks like a green budget
        print(f"TOKEN_BUDGET_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
