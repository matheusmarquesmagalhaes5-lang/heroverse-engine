"""The Google Flow runner's rules, without a browser (tested in the repository on every PR).

Owner, 2026-11-05: "quero tudo no automatico.. faça um MCP não oficial.. use meu computador e faça." He accepted the
account risk (Google's terms forbid automated use; a suspension would reach the same Google account as YouTube).
Free daily credits only: nothing is bought, no plan or trial is started.

Local ledger (C:\\HeroVerse\\flow\\ledger.json), checked field by field; a malformed ledger fails closed:
  {"version", "quotes": {quote_id: {...}}, "jobs": {job_id: {...}}, "days": {YYYY-MM-DD: {"generations", "credits"}},
   "cooldown_until", "cooldown_reason", "project_url"}
A job is written SUBMITTING before the Generate click. A submission whose acknowledgement is not seen is UNCERTAIN and
is never retried: it is reconciled by reading the project (flow_job). While any job is not terminal, no new job starts.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

VERSION = "flow-ledger-v1"
FREE_DAILY_CREDITS = 50           # Flow's free plan, per day, not cumulative (2026-11-05)
DAILY_CAP = 4                     # generations a day by default (FLOW_DAILY_CAP may lower or raise it, never past credits)
QUOTE_TTL = timedelta(minutes=15)
COOLDOWN = timedelta(hours=24)
MIN_GAP = timedelta(minutes=3)    # between two submissions (a person's pace)
MAX_INGREDIENTS = 3
JOB_ID = re.compile(r"^flow-[0-9]{8}-[0-9]{6}-[a-z0-9]{4}$")
QUOTE_ID = re.compile(r"^q-[0-9]{8}-[0-9]{6}-[a-z0-9]{4}$")
TERMINAL = ("COMPLETED", "FAILED", "DOWNLOADED")
OPEN = ("SUBMITTING", "UNCERTAIN", "SUBMITTED", "RUNNING")

# model key -> what the UI shows and what the model allows (read 2026-11-05 from the owner's analysis)
MODELS = {
    "veo-3.1-lite": {"label": re.compile(r"(?i)veo\s*3\.1\W*lite"), "durations": (8,), "resolutions": ("720p",),
                     "expected_cost": 10},
    "omni-flash-1.2": {"label": re.compile(r"(?i)omni\W*flash\W*1\.2"), "durations": (4, 5, 6, 7, 8),
                       "resolutions": ("720p",), "expected_cost_per_s": 3},
}
ASPECTS = ("16:9", "9:16")
MODES = ("text", "ingredients", "frames")

# Series rules (PROMPT_GUIDE "Pavo silent-clip standard"): silent acting, our Kokoro narration over it
SILENCE = "No talking, no lip movement, no dialogue."
SILENT_TAIL = ("Silent acting only: nobody speaks, every mouth stays closed, no lip movement, no dialogue, no singing. "
               "No text, no captions, no logos, no watermark.")
CENTRED = re.compile(r"(?i)\bcent(?:red|ered) in the frame\b")
SPEECH = re.compile(
    r"(?i)\b(speak\w*|spoke\w*|talk(?:s|ed|ing)?|says?|said|saying|whisper\w*|sing\w*|sung|chant\w*|recit\w*|"
    r"lip[- ]?sync\w*|lips? (?:moving|move|moves|part|parts|parting|open\w*)|mouth (?:moving|moves|move|open\w*)|"
    r"opens? (?:his|her|its) mouth|open mouth|shout\w*|yell\w*|call(?:s|ing)? out|mutter\w*|murmur\w*|"
    r"preach\w*|conversation|mouthing)\b")
NEGATED = re.compile(r"(?i)\b(?:no|without|never|not) (?:talking|speaking|singing|dialogue|lip[- ]?movement|lip[- ]?sync\w*|"
                     r"mouth movement)\b|\bnobody (?:speaks|talks|sings)\b")
GOD = re.compile(r"(?i)\b(god|the lord|lord god|jehovah|yahweh|the almighty|the creator)\b")
GOD_FACE = re.compile(r"(?i)\b(god'?s? (?:face|eyes|smile|beard|head)|face of (?:god|the lord)|(?:god|the lord) "
                      r"(?:as an? (?:old )?man|with a (?:face|beard)|smiling|looking))\b")
GOD_SAFE = re.compile(r"(?i)\b(never shown|no face|faceless|unseen|as (?:light|a voice|wind|fire)|only (?:light|rays))\b")

# What a page says when it stops us (lower case). Any of them: stop at once, 24 h cool-down, report.
CHALLENGE_HINTS = ("unusual activity", "unusual traffic", "verify you are human", "verify it's you", "verify it’s you",
                   "are you a robot", "not a robot", "captcha", "security check", "suspicious activity")
LIMIT_HINTS = ("come back tomorrow", "try again tomorrow", "out of credits", "not enough credits", "no credits left",
               "daily limit", "you've reached your limit", "you have reached your limit", "quota exceeded",
               "too many requests", "try again later")
LOGIN_HINTS = ("sign in to continue", "choose an account", "to continue to", "2-step verification",
               "two-step verification", "enter your password", "use your google account")
# offers that are never clicked
PAID_HINTS = ("start trial", "free trial", "start free trial", "subscribe", "buy credits", "add credits",
              "purchase", "get google ai pro", "upgrade to", "get ultra")
CREDITS_RE = re.compile(r"(?i)(\d{1,5})\s*(?:ai\s+)?credits?\b")
CREDITS_LEFT_RE = re.compile(r"(?i)(?:(\d{1,5})\s*(?:ai\s+)?credits?\s*(?:left|remaining|available))|"
                             r"(?:(?:ai\s+)?credits?\s*(?:left|remaining|available)?\s*[:\-]?\s*(\d{1,5}))")
URL_KEYS = ("project_url", "media_url", "baseline", "page_url")


class FlowStop(Exception):
    """A refusal or a stop. code is stable (tests and the MCP layer read it); detail is safe to print."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code} {detail}".strip())
        self.code = code
        self.detail = detail


def now_utc():
    return datetime.now(timezone.utc)


def iso(t):
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_time(value, field):
    if value is None:
        return None
    try:
        t = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise FlowStop("LEDGER_UNREADABLE", f"{field} is not an ISO time") from None
    if t.tzinfo is None:
        raise FlowStop("LEDGER_UNREADABLE", f"{field} has no time zone")
    return t


def day_of(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%d")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def new_id(prefix, t, salt):
    return f"{prefix}-{t.astimezone(timezone.utc):%Y%m%d-%H%M%S}-{sha256(salt.encode())[:4]}"


# ---------- ledger ----------

def empty_ledger():
    return {"version": VERSION, "quotes": {}, "jobs": {}, "days": {}, "cooldown_until": None, "cooldown_reason": None,
            "project_url": None}


def load_ledger(path):
    p = Path(path)
    if not p.exists():
        return empty_ledger()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise FlowStop("LEDGER_UNREADABLE", "not JSON") from None
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise FlowStop("LEDGER_UNREADABLE", "not a flow-ledger-v1 object")
    for key in ("quotes", "jobs", "days"):
        if not isinstance(data.get(key), dict):
            raise FlowStop("LEDGER_UNREADABLE", f"{key} is not an object")
    for day, row in data["days"].items():
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or not isinstance(row, dict) \
                or any(type(row.get(k, 0)) is not int or row.get(k, 0) < 0 for k in ("generations", "credits")):
            raise FlowStop("LEDGER_UNREADABLE", f"days.{day}")
    for jid, job in data["jobs"].items():
        if not isinstance(job, dict) or job.get("state") not in OPEN + TERMINAL:
            raise FlowStop("LEDGER_UNREADABLE", f"jobs.{jid}.state")
        parse_time(job.get("submitted_at"), f"jobs.{jid}.submitted_at")
    parse_time(data.get("cooldown_until"), "cooldown_until")
    data.setdefault("project_url", None)
    data.setdefault("cooldown_reason", None)
    return data


def save_ledger(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def daily_cap():
    env = os.environ.get("FLOW_DAILY_CAP", "").strip()
    try:
        value = int(env) if env else DAILY_CAP
    except ValueError:
        return DAILY_CAP
    return value if 0 <= value else DAILY_CAP


def today_usage(ledger, now):
    row = ledger["days"].get(day_of(now)) or {}
    return int(row.get("generations", 0)), int(row.get("credits", 0))


# ---------- page text ----------

def blocked(text):
    """('CHALLENGE' | 'LIMIT' | 'LOGIN', hint) for a page text, or None."""
    low = (text or "").lower()
    for kind, hints in (("CHALLENGE", CHALLENGE_HINTS), ("LIMIT", LIMIT_HINTS), ("LOGIN", LOGIN_HINTS)):
        for h in hints:
            if h in low:
                return kind, h
    return None


def start_cooldown(ledger, kind, hint, now):
    ledger["cooldown_until"] = iso(now + COOLDOWN)
    ledger["cooldown_reason"] = f"{kind}: {hint}"
    return ledger


def check_cooldown(ledger, now):
    until = parse_time(ledger.get("cooldown_until"), "cooldown_until")
    if until is not None and now < until:
        raise FlowStop("COOLDOWN", f"until={iso(until)} reason={ledger.get('cooldown_reason')}")


def parse_credits_left(text):
    """The credits left as the account menu shows them, or None when no single unambiguous number is there."""
    found = set()
    for m in CREDITS_LEFT_RE.finditer(text or ""):
        found.add(int(m.group(1) or m.group(2)))
    return found.pop() if len(found) == 1 else None


def parse_cost(text):
    """The credit cost shown next to a model or a Generate button ("10 credits"), or None (none, or ambiguous)."""
    found = {int(m.group(1)) for m in CREDITS_RE.finditer(text or "")}
    return found.pop() if len(found) == 1 else None


# ---------- parameters and prompt ----------

def check_params(params):
    model = MODELS.get(params.get("model"))
    if model is None:
        raise FlowStop("MODEL_NOT_ALLOWED", str(params.get("model")))
    if params.get("seconds") not in model["durations"]:
        raise FlowStop("DURATION_NOT_ALLOWED", f"{params.get('seconds')} not in {model['durations']}")
    if params.get("resolution") not in model["resolutions"]:
        raise FlowStop("RESOLUTION_NOT_ALLOWED", str(params.get("resolution")))
    if params.get("aspect") not in ASPECTS:
        raise FlowStop("ASPECT_NOT_ALLOWED", str(params.get("aspect")))
    if params.get("mode", "text") not in MODES:
        raise FlowStop("MODE_NOT_ALLOWED", str(params.get("mode")))
    if params.get("outputs", 1) != 1:
        raise FlowStop("OUTPUTS_NOT_ONE", "one output per prompt only")
    ingredients = params.get("ingredients") or []
    if params.get("mode", "text") == "ingredients" and not 1 <= len(ingredients) <= MAX_INGREDIENTS:
        raise FlowStop("INGREDIENTS_COUNT", f"{len(ingredients)} (1-{MAX_INGREDIENTS})")
    if params.get("mode", "text") == "text" and ingredients:
        raise FlowStop("INGREDIENTS_NEED_MODE", "ingredients need mode=ingredients")
    if params.get("character") and params.get("mode") not in ("ingredients", "frames"):
        raise FlowStop("CHARACTER_NEEDS_REFERENCE", "a named character needs our approved still or sheet as ingredient")
    return params


def quote_key(params):
    """What a quote covers: the same model, length, resolution, aspect, mode, ingredients (by digest) and outputs."""
    keep = {k: params.get(k) for k in ("model", "seconds", "resolution", "aspect", "mode", "outputs")}
    keep["mode"] = keep["mode"] or "text"
    keep["outputs"] = keep["outputs"] or 1
    keep["ingredients"] = sorted(params.get("ingredient_sha256") or [])
    return sha256(json.dumps(keep, sort_keys=True).encode())


def prompt_problems(prompt):
    out = []
    text = (prompt or "").strip()
    if not text:
        return ["PROMPT_EMPTY"]
    if len(text) > 2000:
        out.append("PROMPT_TOO_LONG")
    if not CENTRED.search(text):
        out.append("PROMPT_NOT_CENTRED (say 'centred in the frame')")
    m = SPEECH.search(NEGATED.sub(" ", text))
    if m:
        out.append(f"PROMPT_ASKS_SPEECH ('{m.group(0)}': clips are silent acting; our narration goes over them)")
    if GOD_FACE.search(text):
        out.append("PROMPT_GOD_FACE (God is never shown with a face)")
    elif GOD.search(text) and not GOD_SAFE.search(text):
        out.append("PROMPT_GOD_UNGUARDED (name how God is shown without a face: as light, unseen, never shown)")
    return out


def full_prompt(prompt):
    text = prompt.strip()
    if SILENCE not in text:
        text += " " + SILENCE
    return text + " " + SILENT_TAIL


# ---------- quote, generate, reconcile ----------

def record_quote(ledger, params, cost, credits_left, plan, now):
    check_params(params)
    if type(cost) is not int or cost <= 0:
        raise FlowStop("QUOTE_UNREADABLE", "the UI showed no single credit cost")
    qid = new_id("q", now, quote_key(params) + iso(now))
    ledger["quotes"][qid] = {"at": iso(now), "key": quote_key(params), "cost": cost, "credits_left": credits_left,
                             "plan": plan, "used_by": None,
                             "params": {k: params.get(k) for k in ("model", "seconds", "resolution", "aspect", "mode",
                                                                   "outputs")}}
    # keep the last 50 quotes
    if len(ledger["quotes"]) > 50:
        ledger["quotes"] = dict(sorted(ledger["quotes"].items(), key=lambda kv: kv[1]["at"])[-50:])
    return qid


def open_jobs(ledger):
    return sorted(j for j, job in ledger["jobs"].items() if job["state"] in OPEN)


def check_generate(ledger, quote_id, params, prompt, now, live_cost=None, live_credits_left=None):
    """Raise unless a generation may start now. Order: cool-down, quote, open jobs, pace, cap, free credits, prompt."""
    check_cooldown(ledger, now)
    check_params(params)
    if not quote_id:
        raise FlowStop("QUOTE_REQUIRED", "call flow_quote first")
    quote = ledger["quotes"].get(quote_id)
    if quote is None:
        raise FlowStop("QUOTE_REQUIRED", f"unknown quote {quote_id}")
    if quote.get("used_by"):
        raise FlowStop("QUOTE_USED", f"{quote_id} already used by {quote['used_by']}")
    at = parse_time(quote["at"], f"quotes.{quote_id}.at")
    if now - at > QUOTE_TTL or now < at:
        raise FlowStop("QUOTE_STALE", f"{quote_id} at {quote['at']} (fresh means under {QUOTE_TTL})")
    if quote["key"] != quote_key(params):
        raise FlowStop("QUOTE_MISMATCH", "the quote was for other model/length/resolution/aspect/mode/ingredients")
    if live_cost is not None and live_cost != quote["cost"]:
        raise FlowStop("QUOTE_CHANGED", f"quoted {quote['cost']}, the UI now shows {live_cost}")
    pending = open_jobs(ledger)
    if pending:
        raise FlowStop("JOB_NOT_RECONCILED", f"{','.join(pending)} (read it with flow_job first; never resubmit)")
    sent = [parse_time(j["submitted_at"], "submitted_at") for j in ledger["jobs"].values() if j.get("submitted_at")]
    if sent and now - max(sent) < MIN_GAP:
        raise FlowStop("WAIT_MIN_GAP", f"last submission {iso(max(sent))}")
    done, spent = today_usage(ledger, now)
    cap = daily_cap()
    if done + 1 > cap:
        raise FlowStop("DAILY_CAP", f"generations={done} cap={cap} day={day_of(now)}")
    cost = quote["cost"]
    left = live_credits_left if live_credits_left is not None else quote.get("credits_left")
    if type(left) is not int:
        raise FlowStop("CREDITS_UNREADABLE", "today's free credits were not read")
    if cost > left:
        raise FlowStop("CREDITS_SHORT", f"cost={cost} left={left}")
    if spent + cost > FREE_DAILY_CREDITS:
        raise FlowStop("FREE_CREDITS_EXCEEDED", f"spent today={spent} cost={cost} free={FREE_DAILY_CREDITS}")
    problems = prompt_problems(prompt)
    if problems:
        raise FlowStop("PROMPT_REFUSED", "; ".join(problems))
    return quote


def mark_submitting(ledger, quote_id, params, prompt, now):
    """Before the Generate click: the job exists, the quote is spent, the day counts it (whatever happens next)."""
    quote = ledger["quotes"][quote_id]
    jid = new_id("flow", now, quote_id + prompt)
    if jid in ledger["jobs"]:
        raise FlowStop("JOB_EXISTS", jid)
    ledger["jobs"][jid] = {"state": "SUBMITTING", "submitted_at": iso(now), "quote_id": quote_id,
                           "cost": quote["cost"], "params": quote["params"], "character": params.get("character"),
                           "ingredient_sha256": params.get("ingredient_sha256") or [],
                           "prompt": prompt.strip(), "prompt_sent": full_prompt(prompt),
                           "prompt_sha256": sha256(full_prompt(prompt).encode())}
    quote["used_by"] = jid
    row = ledger["days"].setdefault(day_of(now), {"generations": 0, "credits": 0})
    row["generations"] += 1
    row["credits"] += quote["cost"]
    return jid


def mark_acknowledged(ledger, jid, seen):
    """After the click: the UI showed the new job (SUBMITTED) or not (UNCERTAIN, never retried)."""
    ledger["jobs"][jid]["state"] = "SUBMITTED" if seen else "UNCERTAIN"
    return ledger["jobs"][jid]["state"]


def reconcile(ledger, jid, observed, now):
    """A read of the project. observed: RUNNING | COMPLETED | FAILED | ABSENT. An UNCERTAIN job that is ABSENT stays
    UNCERTAIN (it may still appear); nothing here ever resubmits."""
    job = ledger["jobs"].get(jid)
    if job is None:
        raise FlowStop("JOB_UNKNOWN", jid)
    if job["state"] in TERMINAL:
        return job["state"]
    if observed in ("RUNNING", "COMPLETED", "FAILED"):
        job["state"] = observed
        job["read_at"] = iso(now)
    return job["state"]


def mark_downloaded(ledger, jid, path, data, probe):
    job = ledger["jobs"][jid]
    if job["state"] not in ("COMPLETED", "DOWNLOADED"):
        raise FlowStop("JOB_NOT_COMPLETED", f"{jid} is {job['state']}")
    job.update(state="DOWNLOADED", file=str(path), sha256=sha256(data), bytes=len(data), probe=probe)
    return job


# ---------- public copy ----------

def sanitize(ledger):
    """The repository copy: no URLs, project ids, cookies, tokens, emails or account names; only our ids, states,
    times, credits, prompts and file digests."""
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() if k not in URL_KEYS and k != "file"}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, str):
            return re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", re.sub(r"https?://\S+", "<url>", obj))
        return obj
    out = clean({k: v for k, v in ledger.items() if k != "project_url"})
    for jid, job in ledger.get("jobs", {}).items():
        if job.get("file"):
            out["jobs"][jid]["file_name"] = Path(str(job["file"]).replace("\\", "/")).name
    out["note"] = "Sanitized copy of the PC ledger: no cookies, tokens, URLs or account identifiers."
    return out
