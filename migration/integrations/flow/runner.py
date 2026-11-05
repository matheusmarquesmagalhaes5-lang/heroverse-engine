#!/usr/bin/env python3
"""HeroVerse Google Flow runner (UNOFFICIAL): on the owner's Windows PC, in the runner's OWN Chrome profile
(C:\\HeroVerse\\flow-runner\\profile), signed in once by the owner. His everyday Chrome is never opened or read.

  runner.py login                       opens a PLAIN Chrome window (no automation) on the runner's profile at Flow; the
                                        owner signs in and accepts Flow's welcome screen himself, then closes it
  runner.py status                      logged in, plan hint, credits left today, cool-down, today's usage
  runner.py quote --model M --seconds S --resolution R --aspect A [--mode text|ingredients|frames] [--ingredient F...]
                                        the exact credit cost read from the UI; nothing is submitted
  runner.py generate --quote Q --prompt FILE [same params] [--character NAME]
                                        ONE generation, only with a fresh matching quote and free credits; job id
  runner.py job JOB_ID                  reads the project: RUNNING / COMPLETED / FAILED / still UNCERTAIN
  runner.py download JOB_ID             saves C:\\HeroVerse\\flow\\<job>.mp4 with sha256, ffprobe and 4 frames
  runner.py export                      the sanitized ledger (no URLs, cookies, tokens or account identifiers)
  runner.py probe                       which selectors.json entries match on the Flow page; read-only

The last stdout line is `RESULT <json>`. Exit codes: 0 ok, 2 refused by a guard, 3 not logged in, 4 stopped by the page
(CAPTCHA, unusual activity, come back tomorrow, login or 2FA: 24 h cool-down), 5 page element not found, 6 Flow's
welcome screen not accepted yet, 8 runner busy, 9 owner active (wait and retry).
No CAPTCHA solving, fingerprint or webdriver masking, stealth plugin or proxy. Cookies and passwords are never read,
copied or logged: only the presence of Google's session cookie names.
"""
import argparse
import base64
import ctypes
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flow_core as core  # noqa: E402

DATA = Path(os.environ.get("FLOW_DATA", r"C:\HeroVerse\flow"))
LEDGER = DATA / "ledger.json"
PROFILE = Path(os.environ.get("FLOW_PROFILE") or HERE / "profile")
LOG = DATA / "logs" / "runner.log"
LOCK = HERE / "runner.lock"
SEL = json.loads((HERE / "selectors.json").read_text(encoding="utf-8"))
SESSION_COOKIES = {"SID", "__Secure-1PSID", "__Secure-3PSID"}      # names only
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
IDLE_MIN_S = 120
EXIT = {"OK": 0, "REFUSED": 2, "NOT_LOGGED_IN": 3, "BLOCKED": 4, "UI_UNKNOWN": 5, "WELCOME_PENDING": 6, "BUSY": 8,
        "OWNER_ACTIVE": 9}


class Stop(Exception):
    def __init__(self, state, msg, extra=None):
        super().__init__(msg)
        self.state = state
        self.extra = extra or {}


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{core.iso(core.now_utc())} {msg}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def pause(lo=2.0, hi=5.0):
    time.sleep(random.uniform(lo, hi))


def result(state, **data):
    print("RESULT " + json.dumps({"state": state, **data}, ensure_ascii=False), flush=True)
    return EXIT.get(state, 1)


class Lock:
    def __enter__(self):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
        except FileExistsError:
            raise Stop("BUSY", "RUNNER_BUSY (runner.lock: another run, or one that died; check before deleting)")
        return self

    def __exit__(self, *exc):
        LOCK.unlink(missing_ok=True)


def owner_idle_seconds():
    """Seconds since the owner's last keyboard/mouse input (Windows GetLastInputInfo); None elsewhere."""
    if os.name != "nt":
        return None

    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lii = LII()
    lii.cbSize = ctypes.sizeof(LII)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        return None
    return ((ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF) - lii.dwTime) / 1000.0


def require_idle():
    idle = owner_idle_seconds()
    if idle is not None and idle < IDLE_MIN_S:
        raise Stop("OWNER_ACTIVE", f"OWNER_ACTIVE idle={idle:.0f}s (< {IDLE_MIN_S}s): wait and retry; never fight his mouse")


# ---------- ledger ----------

def ledger():
    try:
        return core.load_ledger(LEDGER)
    except core.FlowStop as e:
        raise Stop("REFUSED", str(e))


def save(data):
    core.save_ledger(LEDGER, data)


def cooldown(data, kind, hint):
    core.start_cooldown(data, kind, hint, core.now_utc())
    save(data)
    log(f"COOLDOWN_STARTED {kind} '{hint}' until {data['cooldown_until']}")


# ---------- browser ----------

def browser(pw, headed):
    PROFILE.mkdir(exist_ok=True)
    args = [] if headed else ["--start-minimized"]
    return pw.chromium.launch_persistent_context(str(PROFILE), channel="chrome", headless=False, args=args,
                                                 viewport={"width": 1366, "height": 900}, locale="en-US",
                                                 accept_downloads=True)


def has_session(ctx):
    names = {c["name"] for c in ctx.cookies(["https://accounts.google.com", "https://labs.google"])}
    return bool(names & SESSION_COOKIES)


def first(scope, key, timeout=4000):
    for sel in SEL[key]:
        loc = scope.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:  # noqa: BLE001
            continue
    return None


def body_text(page):
    try:
        return page.title() + "\n" + page.inner_text("body", timeout=8000)
    except Exception:  # noqa: BLE001
        return ""


def debug_shot(page, tag):
    try:
        (DATA / "debug").mkdir(parents=True, exist_ok=True)
        path = DATA / "debug" / f"{tag}-{int(time.time())}.png"
        page.screenshot(path=str(path))
        return str(path)
    except Exception:  # noqa: BLE001
        return None


def guard_page(page, data, ctx, where):
    """Stop on a challenge, limit, login or 2FA page (24 h cool-down), or on Flow's unaccepted welcome screen."""
    url = page.url or ""
    text = body_text(page)
    hit = core.blocked(text)
    if "accounts.google.com" in url and hit is None:
        hit = ("LOGIN", "accounts.google.com")
    if hit:
        kind, hint = hit
        if kind == "LOGIN" and not has_session(ctx):
            raise Stop("NOT_LOGGED_IN", "NOT_LOGGED_IN (the owner signs in once: runner.py login)")
        cooldown(data, kind, hint)
        raise Stop("BLOCKED", f"{kind} at {where}: '{hint}' (24 h cool-down; nothing solved or worked around)",
                   {"debug": debug_shot(page, "blocked")})
    low = text.lower()
    if sum(h in low for h in SEL["welcome_text"]) >= 2 and not first(page, "prompt_box", 1500) \
            and not first(page, "new_project", 1500):
        raise Stop("WELCOME_PENDING", "Flow's welcome/terms screen is open: the owner accepts it once in runner.py login")
    return text


def open_flow(page, data, ctx):
    page.goto(SEL["flow_url"], wait_until="domcontentloaded", timeout=60000)
    pause(4, 7)
    return guard_page(page, data, ctx, "flow home")


def read_account(page):
    """(credits_left or None, plan hint) from the page, then from the account menu (closed again with Escape)."""
    text = body_text(page)
    left = core.parse_credits_left(text)
    menu_text = ""
    if left is None:
        btn = first(page, "account_button", 3000)
        if btn is not None:
            btn.click()
            pause(1.5, 3)
            menu_text = body_text(page)
            left = core.parse_credits_left(menu_text)
            page.keyboard.press("Escape")
            pause(0.5, 1)
    low = (text + menu_text).lower()
    plan = "paid?" if re.search(r"google ai (pro|ultra) (plan|member|subscriber)|your plan: (pro|ultra)", low) else "free"
    return left, plan


def ensure_project(page, data, ctx):
    if data.get("project_url"):
        page.goto(data["project_url"], wait_until="domcontentloaded", timeout=60000)
        pause(4, 7)
        guard_page(page, data, ctx, "project")
        return
    btn = first(page, "new_project")
    if btn is None:
        raise Stop("UI_UNKNOWN", "UI_UNKNOWN new_project", {"debug": debug_shot(page, "new-project")})
    btn.click()
    try:
        page.wait_for_url(re.compile(r"/project/"), timeout=30000)
    except Exception:  # noqa: BLE001
        raise Stop("UI_UNKNOWN", "UI_UNKNOWN project page", {"debug": debug_shot(page, "project")})
    pause(3, 5)
    data["project_url"] = page.url.split("?")[0]
    save(data)
    guard_page(page, data, ctx, "new project")


def pick(page, menu_key, want, exact_labels=None):
    """Open a menu and click the option whose text matches `want` (regex) or one of exact_labels; returns its text."""
    menu = first(page, menu_key)
    if menu is None:
        return None
    menu.click()
    pause(1, 2)
    for sel in SEL["option"]:
        for opt in page.locator(sel).all():
            try:
                t = opt.inner_text(timeout=1000)
            except Exception:  # noqa: BLE001
                continue
            if any(h in t.lower() for h in core.PAID_HINTS):
                continue        # never click a purchase, trial or upgrade entry
            if (want is not None and want.search(t)) or (exact_labels and any(l in t for l in exact_labels)):
                opt.click()
                pause(1, 2)
                return t
    page.keyboard.press("Escape")
    return None


def configure(page, params):
    """Set mode, model, outputs=1 and aspect; returns the cost the UI shows for this exact setting."""
    mode_label = SEL["mode_labels"][params.get("mode") or "text"]
    if pick(page, "mode_menu", None, [mode_label]) is None:
        raise Stop("UI_UNKNOWN", f"UI_UNKNOWN mode {mode_label}", {"debug": debug_shot(page, "mode")})
    settings = first(page, "settings_button", 3000)
    if settings is not None:
        settings.click()
        pause(1, 2)
    model_text = pick(page, "model_menu", core.MODELS[params["model"]]["label"])
    if model_text is None:
        raise Stop("UI_UNKNOWN", f"UI_UNKNOWN model {params['model']}", {"debug": debug_shot(page, "model")})
    if pick(page, "outputs_menu", re.compile(r"^\s*1\s*$")) is None:
        raise Stop("UI_UNKNOWN", "UI_UNKNOWN outputs per prompt = 1", {"debug": debug_shot(page, "outputs")})
    if pick(page, "aspect_menu", None, SEL["aspect_labels"][params["aspect"]]) is None:
        raise Stop("UI_UNKNOWN", f"UI_UNKNOWN aspect {params['aspect']}", {"debug": debug_shot(page, "aspect")})
    page.keyboard.press("Escape")
    pause(1, 2)
    cost = core.parse_cost(model_text)
    if cost is None:
        gen = first(page, "generate", 3000)
        if gen is not None:
            cost = core.parse_cost(gen.locator("xpath=..").inner_text(timeout=2000))
    if cost is None:
        raise Stop("REFUSED", "QUOTE_UNREADABLE (the UI shows no single credit cost for this setting)",
                   {"debug": debug_shot(page, "cost")})
    return cost


def videos(page):
    out = []
    for v in page.locator("video").all():
        try:
            src = v.get_attribute("src", timeout=1000) or v.locator("source").first.get_attribute("src", timeout=500)
        except Exception:  # noqa: BLE001
            src = None
        if src:
            out.append(src)
    return out


def upload_ingredients(page, files):
    if not files:
        return
    inp = page.locator(SEL["file_input"][0]).first
    try:
        inp.set_input_files([str(f) for f in files], timeout=15000)
    except Exception:  # noqa: BLE001
        raise Stop("UI_UNKNOWN", "UI_UNKNOWN ingredient upload", {"debug": debug_shot(page, "ingredients")})
    pause(6, 10)


# ---------- commands ----------

def params_of(a):
    files = [Path(f) for f in (a.ingredient or [])]
    for f in files:
        if not f.is_file() or f.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            raise Stop("REFUSED", f"INGREDIENT_INVALID {f.name}")
    p = {"model": a.model, "seconds": a.seconds, "resolution": a.resolution, "aspect": a.aspect,
         "mode": a.mode, "outputs": 1, "ingredients": [str(f) for f in files],
         "ingredient_sha256": [core.sha256(f.read_bytes()) for f in files], "character": getattr(a, "character", None)}
    try:
        core.check_params(p)
    except core.FlowStop as e:
        raise Stop("REFUSED", str(e))
    return p


def cmd_login(a):
    PROFILE.mkdir(exist_ok=True)
    subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", "--no-first-run", SEL["flow_url"]])
    log("LOGIN_WINDOW_OPEN: sign in to Google in this window, accept Flow's welcome screen (never a paid offer), "
        "then close the window")
    return result("OK", login_window=True)


def session(a, fn):
    from playwright.sync_api import sync_playwright
    require_idle()
    with Lock(), sync_playwright() as pw:
        ctx = browser(pw, a.headed)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            return fn(ctx, page)
        finally:
            ctx.close()


def cmd_status(a):
    data = ledger()
    now = core.now_utc()
    done, spent = core.today_usage(data, now)
    base = {"cooldown_until": data.get("cooldown_until"), "generations_today": done, "credits_spent_today": spent,
            "daily_cap": core.daily_cap(), "open_jobs": core.open_jobs(data)}

    if not any((PROFILE / d / "Network" / "Cookies").exists() for d in ("Default",)):
        # a profile nobody has signed in to: answer without opening a window
        return result("NOT_LOGGED_IN", logged_in=False, reason="NOT_LOGGED_IN (the owner signs in once: runner.py login)",
                      **base)

    def run(ctx, page):
        if not has_session(ctx):
            return result("NOT_LOGGED_IN", logged_in=False, **base)
        open_flow(page, data, ctx)
        left, plan = read_account(page)
        return result("OK", logged_in=True, plan=plan, credits_left=left, **base)
    return session(a, run)


def cmd_quote(a):
    data = ledger()
    try:
        core.check_cooldown(data, core.now_utc())
    except core.FlowStop as e:
        raise Stop("REFUSED", str(e))
    p = params_of(a)

    def run(ctx, page):
        if not has_session(ctx):
            raise Stop("NOT_LOGGED_IN", "NOT_LOGGED_IN")
        open_flow(page, data, ctx)
        left, plan = read_account(page)
        ensure_project(page, data, ctx)
        cost = configure(page, p)
        qid = core.record_quote(data, p, cost, left, plan, core.now_utc())
        save(data)
        log(f"QUOTE {qid} cost={cost} left={left} plan={plan}")
        return result("OK", quote_id=qid, cost=cost, credits_left=left, plan=plan,
                      valid_minutes=int(core.QUOTE_TTL.total_seconds() // 60))
    return session(a, run)


def cmd_generate(a):
    data = ledger()
    p = params_of(a)
    prompt = Path(a.prompt).read_text(encoding="utf-8")
    try:   # the offline part of the guard first: nothing opens when it would refuse anyway
        core.check_generate(data, a.quote, p, prompt, core.now_utc())
    except core.FlowStop as e:
        raise Stop("REFUSED", str(e))

    def run(ctx, page):
        if not has_session(ctx):
            raise Stop("NOT_LOGGED_IN", "NOT_LOGGED_IN")
        open_flow(page, data, ctx)
        left, _ = read_account(page)
        ensure_project(page, data, ctx)
        live = configure(page, p)
        try:
            core.check_generate(data, a.quote, p, prompt, core.now_utc(), live_cost=live, live_credits_left=left)
        except core.FlowStop as e:
            raise Stop("REFUSED", str(e))
        baseline = videos(page)
        upload_ingredients(page, p["ingredients"])
        box = first(page, "prompt_box")
        if box is None:
            raise Stop("UI_UNKNOWN", "UI_UNKNOWN prompt box", {"debug": debug_shot(page, "prompt")})
        box.click()
        box.fill(core.full_prompt(prompt))
        pause(2, 4)
        gen = first(page, "generate")
        if gen is None:
            raise Stop("UI_UNKNOWN", "UI_UNKNOWN generate button", {"debug": debug_shot(page, "generate")})
        jid = core.mark_submitting(data, a.quote, p, prompt, core.now_utc())
        data["jobs"][jid]["baseline"] = baseline           # local only (sanitize drops it)
        save(data)                                          # written BEFORE the click: never sent twice
        log(f"SUBMITTING {jid} quote={a.quote}")
        try:
            gen.click()
        except Exception:  # noqa: BLE001
            pass                                            # the click may still have landed: UNCERTAIN below
        seen = False
        for _ in range(15):
            time.sleep(2)
            hit = core.blocked(body_text(page))
            if hit:
                core.mark_acknowledged(data, jid, False)
                cooldown(data, *hit)
                raise Stop("BLOCKED", f"{hit[0]} after submit: '{hit[1]}' (job {jid} UNCERTAIN; 24 h cool-down)")
            if first(page, "progress", 500) is not None or len(videos(page)) > len(baseline):
                seen = True
                break
        state = core.mark_acknowledged(data, jid, seen)
        save(data)
        log(f"{state} {jid}")
        return result("OK", job_id=jid, job_state=state, retry_submission=False)
    return session(a, run)


def cmd_job(a):
    data = ledger()
    job = data["jobs"].get(a.job_id)
    if job is None:
        raise Stop("REFUSED", f"JOB_UNKNOWN {a.job_id}")
    if job["state"] in core.TERMINAL:
        return result("OK", job_id=a.job_id, job_state=job["state"])

    def run(ctx, page):
        if not has_session(ctx):
            raise Stop("NOT_LOGGED_IN", "NOT_LOGGED_IN")
        open_flow(page, data, ctx)
        ensure_project(page, data, ctx)
        pause(3, 6)
        now_srcs = videos(page)
        new = [s for s in now_srcs if s not in set(job.get("baseline") or [])]
        low = body_text(page).lower()
        if len(new) == 1:
            observed = "COMPLETED"
            job["media_url"] = new[0]                       # local only
        elif len(new) > 1:
            raise Stop("REFUSED", f"JOB_AMBIGUOUS {len(new)} new videos in the project (look at it by hand)")
        elif any(h in low for h in SEL["failed_text"]):
            observed = "FAILED"
        elif first(page, "progress", 1500) is not None:
            observed = "RUNNING"
        else:
            observed = "ABSENT"
        state = core.reconcile(data, a.job_id, observed, core.now_utc())
        save(data)
        log(f"JOB {a.job_id} observed={observed} state={state}")
        return result("OK", job_id=a.job_id, job_state=state, observed=observed)
    return session(a, run)


def probe_file(path):
    def run(cmd):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return p.stdout + p.stderr
    info = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                           "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", str(path)]))
    streams = info.get("streams", [])
    out = {"duration_s": round(float(info.get("format", {}).get("duration", 0)), 3),
           "video": [s for s in streams if s.get("codec_type") == "video"],
           "has_audio": any(s.get("codec_type") == "audio" for s in streams)}
    if out["has_audio"]:
        m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af",
                                                             "volumedetect", "-f", "null", "-"]))
        out["audio_mean_db"] = float(m.group(1)) if m else None
    frames = []
    for i, t in enumerate((1, 3, 5, 7)):
        f = path.with_name(f"{path.stem}-f{i + 1}.jpg")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(path), "-frames:v", "1",
             str(f)])
        if f.exists():
            frames.append(f.name)
    out["frames"] = frames
    return out


def cmd_download(a):
    data = ledger()
    job = data["jobs"].get(a.job_id)
    if job is None or job["state"] not in ("COMPLETED", "DOWNLOADED") or not job.get("media_url"):
        raise Stop("REFUSED", f"JOB_NOT_COMPLETED {a.job_id} (flow_job first)")

    def run(ctx, page):
        open_flow(page, data, ctx)
        ensure_project(page, data, ctx)
        b64 = page.evaluate("""async (src) => { const r = await fetch(src); if (!r.ok) return null;
            const b = new Uint8Array(await r.arrayBuffer()); let s = '';
            for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
            return btoa(s); }""", job["media_url"])
        if not b64:
            raise Stop("UI_UNKNOWN", "UI_UNKNOWN media fetch")
        blob = base64.b64decode(b64)
        if blob[4:8] != b"ftyp":
            raise Stop("REFUSED", "MEDIA_NOT_MP4")
        path = DATA / f"{a.job_id}.mp4"
        path.write_bytes(blob)
        rec = core.mark_downloaded(data, a.job_id, path, blob, probe_file(path))
        save(data)
        log(f"DOWNLOADED {a.job_id} {rec['sha256'][:12]} {rec['bytes']} bytes")
        return result("OK", job_id=a.job_id, file=str(path), sha256=rec["sha256"], bytes=rec["bytes"],
                      probe=rec["probe"])
    return session(a, run)


def cmd_export(a):
    print(json.dumps(core.sanitize(ledger()), indent=1, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_probe(a):
    data = ledger()

    def run(ctx, page):
        open_flow(page, data, ctx)
        found = {}
        for key, sels in SEL.items():
            if isinstance(sels, list) and key not in ("failed_text", "welcome_text"):
                found[key] = [s for s in sels if page.locator(s).count() > 0]
        buttons = []
        for b in page.locator("button").all()[:80]:
            try:
                label = (b.get_attribute("aria-label", timeout=300) or b.inner_text(timeout=300) or "").strip()
            except Exception:  # noqa: BLE001
                continue
            if label and "@" not in label:
                buttons.append(label[:60])
        return result("OK", found=found, buttons=buttons, debug=debug_shot(page, "probe"))
    return session(a, run)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--headed", action="store_true", help="show the runner's window (default: started minimized)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("status")
    sub.add_parser("export")
    sub.add_parser("probe")
    for name in ("quote", "generate"):
        s = sub.add_parser(name)
        s.add_argument("--model", default="veo-3.1-lite", choices=sorted(core.MODELS))
        s.add_argument("--seconds", type=int, default=8)
        s.add_argument("--resolution", default="720p")
        s.add_argument("--aspect", default="16:9", choices=core.ASPECTS)
        s.add_argument("--mode", default="text", choices=core.MODES)
        s.add_argument("--ingredient", nargs="*")
        s.add_argument("--character")
        if name == "generate":
            s.add_argument("--quote", required=True)
            s.add_argument("--prompt", required=True, help="a UTF-8 text file with the prompt")
    for name in ("job", "download"):
        sub.add_parser(name).add_argument("job_id")
    a = ap.parse_args(argv)
    fn = {"login": cmd_login, "status": cmd_status, "quote": cmd_quote, "generate": cmd_generate, "job": cmd_job,
          "download": cmd_download, "export": cmd_export, "probe": cmd_probe}[a.cmd]
    try:
        return fn(a)
    except Stop as e:
        log(f"STOP {e.state} {e}")
        return result(e.state, reason=str(e), **e.extra)


if __name__ == "__main__":
    sys.exit(main())
