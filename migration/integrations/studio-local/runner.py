#!/usr/bin/env python3
"""HeroVerse Studio runner: runs on the owner's Windows PC (own Chrome profile, owner's residential IP) to do what the
YouTube Data API cannot, starting with a Short's "Related video" field. Invoked on demand (production through Desktop
Commander, or the owner); it installs no schedule, service or startup entry.

  runner.py status                 LOGGED_IN or NOT_LOGGED_IN (the Google cookie names' presence, never a value)
  runner.py login                  opens a visible Chrome window on the runner's own profile at studio.youtube.com; the
                                   owner signs in by hand, once; credentials are never typed or read; waits up to 15 min
  runner.py run [--dry-run] [--max N] [--headed]
                                   reads migration/channel/studio_jobs.json and migration/evidence/studio/ from origin/main
                                   (gh), does each pending job one video at a time (at most 30), writes the day's receipt
                                   and opens a data-only claude/studio-receipt-* PR through gh. --dry-run lists the pending
                                   jobs and does nothing else (no browser, no PR)
  runner.py probe VIDEO_ID         which selectors.json entries match on one of our edit pages; read-only

Per job: open studio.youtube.com/video/<id>/edit, skip if the field already shows the target (ALREADY), else choose the
target in the picker, Save, reload and verify (DONE). An unknown page state saves out/debug-*.png locally and the job is
FAILED with the reason; nothing is retried in the same run. Cookies never leave this PC and never enter a file, log or PR.
"""
import argparse
import base64
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
import studio_core as core  # noqa: E402

PROFILE = HERE / "profile"
LEDGER = HERE / "ledger.json"
LOG = HERE / "logs" / "runner.log"
LOCK = HERE / "runner.lock"
OUT = HERE / "out"
SELECTORS = json.loads((HERE / "selectors.json").read_text(encoding="utf-8"))
STUDIO = "https://studio.youtube.com"
LOGIN_COOKIES = {"SAPISID", "__Secure-3PSID", "SID"}   # names only


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = f"{core.iso(core.now_utc())} {msg}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def pause(lo, hi):
    time.sleep(random.uniform(lo, hi))


class Lock:
    def __enter__(self):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
        except FileExistsError:
            raise SystemExit("RUNNER_BUSY (runner.lock: another run, or a run that died; delete it after checking)")
        return self

    def __exit__(self, *exc):
        LOCK.unlink(missing_ok=True)


# ---------- gh (the PC's logged-in GitHub CLI) ----------

def gh(*args, input_text=None):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, input=input_text, timeout=120)
    if p.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {p.stderr.strip()[:300]}")
    return p.stdout


def gh_raw(path, ref="main"):
    return gh("api", f"repos/{core.REPO}/contents/{path}?ref={ref}", "-H", "Accept: application/vnd.github.raw")


def fetch_queue_and_receipts():
    queue = json.loads(gh_raw(core.QUEUE_PATH))
    receipts = []
    try:
        listing = json.loads(gh("api", f"repos/{core.REPO}/contents/{core.RECEIPT_DIR}?ref=main"))
    except RuntimeError:
        listing = []     # no receipts yet
    for f in listing:
        if f.get("name", "").endswith(".json"):
            try:
                receipts.append(json.loads(gh_raw(f["path"])))
            except (RuntimeError, ValueError):
                log(f"RECEIPT_UNREADABLE {f.get('name')}")
    return queue, receipts


def local_ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"results": []}


def push_receipt(results):
    """Data-only PR: migration/evidence/studio/<date>.json (merged with the day's file on main)."""
    path = core.receipt_path()
    sha, existing = None, None
    try:
        meta = json.loads(gh("api", f"repos/{core.REPO}/contents/{path}?ref=main"))
        sha = meta["sha"]
        existing = json.loads(gh_raw(path))
    except RuntimeError:
        pass
    doc = core.merge_receipt(existing, results)
    base = gh("api", f"repos/{core.REPO}/git/ref/heads/main", "--jq", ".object.sha").strip()
    branch = "claude/studio-receipt-" + core.now_utc().strftime("%Y%m%d-%H%M%S")
    gh("api", f"repos/{core.REPO}/git/refs", "-f", f"ref=refs/heads/{branch}", "-f", f"sha={base}")
    args = ["api", "-X", "PUT", f"repos/{core.REPO}/contents/{path}", "-f", f"message=Studio runner receipt {core.iso(core.now_utc())}",
            "-f", "content=" + base64.b64encode(core.dump(doc).encode()).decode(), "-f", f"branch={branch}"]
    if sha:
        args += ["-f", f"sha={sha}"]
    gh(*args)
    n_ok = sum(r["outcome"] in core.DONE for r in results)
    pr = json.loads(gh("api", f"repos/{core.REPO}/pulls", "-f", f"title=Studio runner receipt {core.now_utc():%Y-%m-%d}",
                       "-f", f"head={branch}", "-f", "base=main",
                       "-f", f"body=Data-only evidence from the owner's-PC Studio runner: {len(results)} results, {n_ok} done.\n\n"
                             "Only video ids, outcomes and short details; no cookies or credentials."))
    return pr.get("html_url")


# ---------- browser ----------

def browser(pw, headless):
    PROFILE.mkdir(exist_ok=True)
    return pw.chromium.launch_persistent_context(
        str(PROFILE), channel="chrome", headless=headless, viewport={"width": 1366, "height": 900}, locale="en-US")


def logged_in(ctx):
    names = {c["name"] for c in ctx.cookies("https://www.youtube.com", "https://accounts.google.com")}
    return bool(names & LOGIN_COOKIES)


def first(scope, key, timeout=3000):
    for sel in SELECTORS[key]:
        loc = scope.locator(sel)
        try:
            loc.first.wait_for(state="attached", timeout=timeout)
            return loc.first
        except Exception:  # noqa: BLE001
            continue
    return None


def by_text(scope, key, role=None, timeout=3000):
    for t in SELECTORS[key]:
        loc = scope.get_by_role(role, name=t) if role else scope.get_by_text(t, exact=True)
        try:
            loc.first.wait_for(state="visible", timeout=timeout)
            return loc.first
        except Exception:  # noqa: BLE001
            continue
    return None


class UiError(Exception):
    pass


def shot(page, video_id, why):
    OUT.mkdir(exist_ok=True)
    f = OUT / f"debug-{video_id}-{core.now_utc():%Y%m%d-%H%M%S}.png"
    try:
        page.screenshot(path=str(f), full_page=False)
    except Exception:  # noqa: BLE001
        return None
    log(f"DEBUG_SCREENSHOT {f.name} ({why})")
    return f.name


def open_edit(page, video_id):
    page.goto(f"{STUDIO}/video/{video_id}/edit", wait_until="domcontentloaded")
    if "accounts.google.com" in page.url or "ServiceLogin" in page.url:
        raise UiError("NOT_LOGGED_IN")
    if first(page, "page_ready", timeout=30000) is None:
        raise UiError("EDITOR_NOT_LOADED")
    pause(2, 4)


def related_section(page):
    sec = first(page, "related_section", timeout=2500)
    if sec is None:      # the section sits under "Show more"
        btn = by_text(page, "show_more_text", role="button", timeout=2500) or first(page, "show_more", timeout=2500)
        if btn is not None:
            btn.click()
            pause(1, 2)
        sec = first(page, "related_section", timeout=4000)
    if sec is None:
        raise UiError("RELATED_SECTION_NOT_FOUND")
    sec.scroll_into_view_if_needed()
    return sec


def shown(sec):
    """Text and links the field currently shows."""
    text = sec.inner_text(timeout=5000)
    hrefs = [a.get_attribute("href") or "" for a in sec.locator("a").all()]
    return text, hrefs


def field_has_target(page, job):
    text, hrefs = shown(related_section(page))
    return core.text_matches(text, job["target_video_id"], job.get("target_title"), hrefs)


def choose_target(page, job):
    sec = related_section(page)
    btn = by_text(sec, "related_select_button_text", role="button", timeout=3000)
    if btn is None:
        raise UiError("SELECT_BUTTON_NOT_FOUND")
    btn.click()
    dlg = first(page, "dialog", timeout=8000)
    if dlg is None:
        raise UiError("PICKER_DIALOG_NOT_FOUND")
    pause(2, 4)
    query = job.get("target_title") or job["target_video_id"]
    box = first(dlg, "dialog_search", timeout=3000)
    if box is not None:
        box.fill(query)
        box.press("Enter")
        pause(2, 4)
    row = None
    for sel in SELECTORS["dialog_item"]:
        for cand in dlg.locator(sel).all():
            try:
                text = cand.inner_text(timeout=1500)
                hrefs = [a.get_attribute("href") or "" for a in cand.locator("a").all()]
            except Exception:  # noqa: BLE001
                continue
            if core.text_matches(text, job["target_video_id"], job.get("target_title"), hrefs):
                row = cand
                break
        if row is not None:
            break
    if row is None:
        raise UiError("TARGET_NOT_IN_PICKER")
    row.click()
    pause(1, 3)
    confirm = by_text(dlg, "dialog_confirm_text", role="button", timeout=2000)
    if confirm is not None:
        confirm.click()
        pause(1, 3)


def save(page):
    btn = by_text(page, "save_text", role="button", timeout=3000) or first(page, "save_button", timeout=3000)
    if btn is None:
        raise UiError("SAVE_BUTTON_NOT_FOUND")
    if not btn.is_enabled():
        raise UiError("SAVE_DISABLED_NO_CHANGE_REGISTERED")
    btn.click()
    toast = None
    for _ in range(15):
        toast = by_text(page, "saved_toast_text", timeout=1000)
        if toast is not None or not btn.is_enabled():
            break
    pause(2, 4)


def do_job(page, job):
    """(outcome, detail) for one job. Raises UiError on an unknown state."""
    open_edit(page, job["video_id"])
    if field_has_target(page, job):
        return "ALREADY", "field already shows the target"
    choose_target(page, job)
    save(page)
    pause(3, 6)
    open_edit(page, job["video_id"])          # reload and read the stored value
    if not field_has_target(page, job):
        raise UiError("VERIFY_FAILED_FIELD_DOES_NOT_SHOW_TARGET")
    return "DONE", "saved; reload shows the target"


# ---------- commands ----------

def cmd_login(args):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = browser(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(STUDIO, wait_until="domcontentloaded")
        log("LOGIN_WINDOW_OPEN: sign in to the HeroVerse channel's Google account in this window (up to 15 min)")
        for _ in range(180):
            if logged_in(ctx) and page.url.startswith(STUDIO):
                log("LOGGED_IN")
                ctx.close()
                return 0
            time.sleep(5)
        log("LOGIN_TIMEOUT")
        ctx.close()
        return 1


def cmd_status(args):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = browser(pw, headless=True)
        ok = logged_in(ctx)
        ctx.close()
    print("LOGGED_IN" if ok else "NOT_LOGGED_IN")
    return 0 if ok else 1


def cmd_probe(args):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = browser(pw, headless=not args.headed)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            open_edit(page, args.video_id)
        except UiError as e:
            print(str(e))
            ctx.close()
            return 1
        for key in ("page_ready", "related_section", "show_more", "save_button"):
            print(f"{key}: {'FOUND' if first(page, key, timeout=1500) is not None else 'MISSING'}")
        ctx.close()
    return 0


def cmd_run(args):
    queue, remote_receipts = fetch_queue_and_receipts()
    jobs, bad = core.parse_queue(queue)
    for j, why in bad:
        log(f"JOB_INVALID {why}")
    todo = core.pending(jobs, remote_receipts + [local_ledger()], min(args.max, core.MAX_JOBS))
    log(f"QUEUE jobs={len(jobs)} pending_this_run={len(todo)}")
    if args.dry_run:
        for j in todo:
            print(f"WOULD {j['action']} {j['video_id']} -> {j['target_video_id']}  ({j.get('reason', '')})")
        return 0
    unsent = local_ledger().get("unsent", [])      # results of an earlier run whose receipt PR failed
    if not todo and not unsent:
        print("QUEUE_EMPTY")
        return 0
    from playwright.sync_api import sync_playwright
    results, nl = [], False
    with Lock(), sync_playwright() as pw:
        ctx = browser(pw, headless=not args.headed)
        try:
            if todo and not logged_in(ctx):
                log("NOT_LOGGED_IN: the owner must run `runner.py login` once")
                todo, nl = [], True
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            for i, job in enumerate(todo):
                if i:
                    pause(30, 90)             # human pace between videos
                try:
                    outcome, detail = do_job(page, job)
                except UiError as e:
                    if str(e) == "NOT_LOGGED_IN":
                        log("NOT_LOGGED_IN: session ended; stopping")
                        break
                    outcome, detail = "FAILED", str(e)
                    shot(page, job["video_id"], detail)
                except Exception as e:  # noqa: BLE001
                    outcome, detail = "FAILED", f"UNEXPECTED {type(e).__name__}: {str(e)[:200]}"
                    shot(page, job["video_id"], detail)
                results.append(core.result(job, outcome, detail))
                log(f"{outcome} {job['video_id']} -> {job['target_video_id']} {detail}")
                led = local_ledger()
                led["results"].append(results[-1])
                led.setdefault("unsent", []).append(results[-1])
                LEDGER.write_text(core.dump(led), encoding="utf-8")
        finally:
            ctx.close()
    send = local_ledger().get("unsent", [])
    if send:
        try:
            print("RECEIPT_PR", push_receipt(send))
            led = local_ledger()
            led["unsent"] = []
            LEDGER.write_text(core.dump(led), encoding="utf-8")
        except RuntimeError as e:
            log(f"RECEIPT_PUSH_FAILED (kept in ledger.json unsent; the next run sends them): {e}")
            return 2
    if nl:
        return 3
    return 0 if all(r["outcome"] in core.DONE for r in results) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("login").set_defaults(fn=cmd_login)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--max", type=int, default=core.MAX_JOBS)
    r.add_argument("--headed", action="store_true")
    r.set_defaults(fn=cmd_run)
    p = sub.add_parser("probe")
    p.add_argument("video_id")
    p.add_argument("--headed", action="store_true")
    p.set_defaults(fn=cmd_probe)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
