# HeroVerse Google Flow runner (UNOFFICIAL)

Owner, 2026-11-05, after being told the risks: "quero tudo no automatico.. faça um MCP não oficial.. use meu
computador e faça." Google Flow (https://labs.google/fx/tools/flow) in the owner's own Google account, free plan only,
driven from his Windows PC (device "Matheus"). Modelled on the Pavo unofficial MCP (`../pavo/`) and the PC runners
(`../chatgpt-local/`, `../studio-local/`).

## Risks the owner accepted (2026-11-05)
- Google's terms forbid automated use of the service; the penalty can reach **suspension of his Google account, the
  same account as the YouTube channel**.
- A public report exists of a Flow account blocked after an automated agent used it.
- Commercial use of free-plan output is a grey area.

He accepted them. The runner keeps the exposure low: a normal user's pace (one job at a time, at most 4 a day, 3 min
apart), no evasion of any kind, and a full stop for 24 h at the first sign of trouble.

## Driver
**Playwright persistent context on the runner's OWN Chrome profile** (`C:\HeroVerse\flow-runner\profile`, the
installed Chrome, `channel="chrome"`), started minimized. The owner's everyday Chrome and profile are never opened,
copied or read. Chosen over a copy of his profile (would copy his whole browsing data; locked files; Google session
binding) and UIAutomation (fights his mouse and screen). The one-time sign-in uses a **plain** Chrome window on that
profile (`runner.py login`: no automation flags), where the owner signs in and accepts Flow's standard welcome screen
himself. Credentials are never typed or read by any script.

No bot-detection evasion: no stealth plugin, fingerprint or webdriver masking, proxy or CAPTCHA solving.

## Tools (MCP "heroverse-flow", stdio, PC user config) and CLI

| MCP tool | CLI (`.venv\Scripts\python runner.py ...`) | Does |
|---|---|---|
| `flow_status` | `status` | logged in, plan hint, credits left today, cool-down, today's generations and credits |
| `flow_quote` | `quote --model --seconds --resolution --aspect [--mode] [--ingredient F...]` | the exact credit cost of ONE output for this setting, read from the UI; a `quote_id` valid 15 min |
| `flow_generate` | `generate --quote Q --prompt FILE [same setting] [--character NAME]` | ONE generation; returns `job_id`, `retry_submission: false` |
| `flow_job` | `job JOB_ID` | reads the project: RUNNING / COMPLETED / FAILED, or still UNCERTAIN |
| `flow_download` | `download JOB_ID` | `C:\HeroVerse\flow\<job>.mp4`, sha256, ffprobe summary (audio present, mean dB) and 4 frames |
| — | `login`, `probe`, `export` | one-time sign-in window; which selectors match (read-only); the sanitized ledger |

The last stdout line of every command is `RESULT <json>`. Exit codes: 0 ok, 2 refused by a guard, 3 not logged in,
4 stopped by the page (24 h cool-down), 5 page element not found (`C:\HeroVerse\flow\debug\*.png`, local only),
6 Flow's welcome screen not accepted, 8 busy, 9 owner active.

Models allowed: `veo-3.1-lite` (8 s, 720p; 10 credits on 2026-11-05) and `omni-flash-1.2` (4-8 s, 720p; 3 credits/s).
Aspect 16:9 or 9:16, one output per prompt. Modes `text`, `ingredients` (1-3 of our approved stills or character
sheets, for character consistency) and `frames`.

## Guards (mirroring Pavo)
- **Quote required.** `flow_generate` needs a quote under 15 min old for exactly the same model, length, resolution,
  aspect, mode, ingredients (by sha256) and one output; each quote is used once. Right before the click the cost is
  read again from the UI: a different number refuses (`QUOTE_CHANGED`). An unreadable cost is no quote.
- **Free credits only.** The live credits left must cover the cost, and our own spend never passes 50 credits in a
  UTC day, whatever the balance shows. Nothing is bought; no upgrade, subscription, trial or credit purchase; menu
  entries with such words are never clicked.
- **Daily cap.** At most 4 generations a UTC day (`FLOW_DAILY_CAP` may set another number), 3 min apart. A
  submission counts before its click.
- **Idempotency.** The job is written `SUBMITTING` to the ledger before the Generate click. No acknowledgement seen
  means `UNCERTAIN`: never retried; `flow_job` reconciles it by reading the project. While any job is not terminal, no
  new job starts (`JOB_NOT_RECONCILED`). One `runner.lock` at a time.
- **Stop and cool-down.** A CAPTCHA, "unusual activity/traffic", "verify it's you", "come back tomorrow", out of
  credits, a login page or 2FA while the profile has a session: stop at once, `cooldown_until` = now + 24 h, report.
  Nothing is solved or worked around. Only the owner clears a cool-down, after looking (edit `cooldown_until`).
- **Owner first.** Before opening any window, `GetLastInputInfo` must show 120 s without input; otherwise
  `OWNER_ACTIVE` (wait and retry).
- **Series prompt rules** (`flow_core.prompt_problems`, PROMPT_GUIDE "Pavo silent-clip standard"): "centred in the
  frame" is required; any request for speech or lip movement is refused; God never shown with a face (a mention of
  God must say how: as light, unseen, never shown); a named `--character` needs our approved still or sheet as an
  ingredient. Every sent prompt ends with the silence sentence (`pavo_prompt.SILENCE`, kept equal by a test) and
  "Silent acting only: nobody speaks, every mouth stays closed...". Veo makes native audio and "Return silent videos"
  does not guarantee closed mouths, so the prompt asks for it and the pipeline strips the audio anyway (as with Pavo,
  the provider's audio is never used; our Kokoro narration goes over the picture).

## Ledger
`C:\HeroVerse\flow\ledger.json` (local, full: project URL, media URLs, baselines). The repository copy
`migration/evidence/flow/ledger.json` is `runner.py export`: our job and quote ids, states, times, costs, prompts,
file names and sha256 only. No cookies, tokens, URLs, emails or account identifiers.

## Media into production
A Flow clip is a candidate source like a Pavo clip: it enters a plan only through the normal source approval
(approve-shot with a real look at the actual video and the still-mouth check). Audio stripped (`ffmpeg -an`).

## How a session calls it
- **Claude Code on the PC:** the MCP tools above (registered once:
  `claude mcp add --scope user heroverse-flow -- C:\HeroVerse\flow-runner\.venv\Scripts\python.exe C:\HeroVerse\flow-runner\mcp_server.py`).
- **Cloud session through Desktop Commander** (device "Matheus"): `write_file` the prompt to
  `C:\HeroVerse\flow\prompts\<name>.txt` (create the folder once), then `start_process`
  `C:\HeroVerse\flow-runner\.venv\Scripts\python.exe C:\HeroVerse\flow-runner\runner.py <command> ...` and
  `read_process_output` until the `RESULT` line. Order: `status` → `quote` → `generate --quote <id>` → `job <id>`
  (every few minutes until COMPLETED) → `download <id>` → `read_file` the frames, then `runner.py export` into
  `migration/evidence/flow/ledger.json` by PR.
- **Install/update:** `C:\HeroVerse\flow-runner\.venv\Scripts\python.exe deploy.py <commit>` (venv: Python 3.13,
  playwright 1.64.1, mcp 2.3.0).

## Status (2026-11-05)
Installed on the PC at `C:\HeroVerse\flow-runner`, MCP registered, unit and stdio tests pass there. The runner's
profile is not signed in yet; `selectors.json` is written from Flow's visible labels and is **not calibrated on the
live signed-in page**. After the owner's one-time sign-in, the acceptance check is `runner.py probe`, then the first
real test (status → quote → one Veo 3.1 Lite 8 s 720p silent clip at ≤10 credits) with `--headed`.
