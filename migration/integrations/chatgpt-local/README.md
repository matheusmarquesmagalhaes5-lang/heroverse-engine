# ChatGPT image runner (owner's PC)

Owner, 2026-10-28: "Faça pelo computador mesmo o MCP": still images from ChatGPT in the owner's own account (no
per-image limit on his plan), with our approved character stills as references. chatgpt.com answers cloud IPs with
a Cloudflare challenge, so this runs on the owner's Windows PC (device "Matheus") and the cloud agents reach it
through Desktop Commander. There is no cloud backup: the free Gemini key's image limit is 0
(`evidence/gemini-image/20261028-free-tier.json`), so that route was not kept.

## Setup (once)
- Installed at `C:\HeroVerse\chatgpt-runner` (venv with Playwright and mcp, the installed Chrome).
- **The owner signs in once**, in the runner's own Chrome profile (never his everyday profile):
  `C:\HeroVerse\chatgpt-runner\.venv\Scripts\python.exe C:\HeroVerse\chatgpt-runner\runner.py login`
- For the bridge to push candidates to GitHub by itself (optional): `gh auth login --web --git-protocol https`.

## Commands (PowerShell, in `C:\HeroVerse\chatgpt-runner`)
| Command | Does |
|---|---|
| `.venv\Scripts\python deploy.py <commit>` | install/update from the public repository |
| `.venv\Scripts\python runner.py login` / `status` / `probe` | sign in once / LOGGED_IN or NOT_LOGGED_IN / which page elements are found |
| `.venv\Scripts\python runner.py image --prompt P.txt --ref A.jpg B.jpg --out out\x [--dry-run]` | ONE 16:9 image: refs uploaded, prompt sent, the full file downloaded, record written |
| `.venv\Scripts\python runner.py job jobs\<id>.json [--dry-run]` | the bridge: refs downloaded by URL, sha256-checked, then `image` into `out\<id>\` |
| `.venv\Scripts\python bridge.py push <id>` | the candidate and record to branch `claude/chatgpt-image-<id>` (needs gh) |
| `.venv\Scripts\python mcp_server.py` | stdio MCP: `chatgpt_status`, `chatgpt_image` (for a Claude session on the PC) |

Exit codes: 0 ok, 2 job invalid, 3 not logged in, 4 challenge, 5 usage limit, 6 no image / page changed,
7 gate (cap, gap, already done), 8 busy.

## Bridge (cloud agents)
1. In the repository: `python3 migration/integrations/chatgpt-local/bridge.py job <still record> "<subject>"
   <approved ref records...> --ref-commit <main sha>` prints the job (prompt = identity line + the still's prompt,
   refs by raw URL and sha256).
2. Desktop Commander: `create_directory C:\HeroVerse\chatgpt-runner\jobs` (once; write_file does not create
   folders), `write_file C:\HeroVerse\chatgpt-runner\jobs\<id>.json`, then `start_process`
   `...\python.exe ...\runner.py job ...\jobs\<id>.json`, and `read_process_output` until `IMAGE_SAVED` or a stop line.
3. Review: `read_file` the image (Desktop Commander shows it) and its record; the record is text, so it can be
   committed directly. The image reaches the repository with `bridge.py push <id>` (gh on the PC) as a DRAFT
   candidate; Claude's still review (`scene_stills.py approve`) decides, as for every still.

## Rules
One request at a time (`runner.lock`), 3-8 s between steps, 3 min between requests, 30 a day. A Cloudflare
challenge, a login page or a usage-limit message stops the run with its code and is reported; nothing is solved or
worked around (no captcha solving, fingerprint or webdriver masking, proxy). `ledger.json` marks a job SENDING
before the prompt goes, so a job is never sent twice. Cookies and passwords are never read, copied or logged: only
the presence of the session cookie's name.

## Licence and account risk
Each record cites OpenAI's Terms of Use: the user owns the Output ("you ... (b) own the Output. We hereby assign to
you all our right, title, and interest, if any, in and to Output"). The same terms forbid extracting Output
"automatically or programmatically"; this runner is a browser script in the owner's own session, run at his explicit
request, so the account risk (a warning or suspension) is his. The record says so (`licence.automation_note`).

## Desktop app route (primary since 2026-11-01)

Owner, 2026-11-01: "Usa o GPT como programa". The browser runner above meets a Cloudflare "Confirme que é humano"
challenge at chatgpt.com/auth/login, and no session ever solves a challenge. The ChatGPT Windows app
(`shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App`) is already signed in to the owner's Pro account and shows no
challenge. Verified 2026-11-01 16:20–16:28 BRT: one 16:9 image in about 1 min 40 s, downloaded at 1672x941, sha256
f5f9f375…e105.

Steps (Desktop Commander + `C:\HeroVerse\ui.ps1`; screen 1366x768; take one screenshot to confirm each layout before
trusting the coordinates):
1. Open or focus the app: `Start-Process "shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App"`. Owner, 2026-11-01: ONE
   chat for all the stills. Never open a new chat per image. Every image prompt goes into the chat "HeroVerse — stills"
   (the app shows it with an em dash; a hyphen or en dash is accepted too), and only after `select_chat.ps1` answers
   `OK` (see "Chat lock" below). No script creates a chat: when the guard cannot find that chat the run stops. Never
   delete the owner's other chats.
2. Put the prompt on the clipboard (`Set-Clipboard`). It starts with "Create an image, 16:9 landscape, no text." and
   then the still's exact plan prompt, which says "centred in the frame". Click the composer, `type '^v'`, then click
   the send arrow. Clear the clipboard with `Set-Clipboard ' '`.
3. Wait about 2 min, then take one screenshot to confirm the image. Its share icon (bottom-right of the image) leads to
   "Baixar", which opens "Salvar como". Paste the full path `C:\HeroVerse\gpt-images\<still id>.png`, then Enter.
4. Record the still exactly as the runner does (prompt, sha256, size, source "chatgpt-desktop", the licence line
   below), then upscale it to the plan's still size and take it through the still review (`scene_stills.py approve`).
   One image at a time, and at most 30 a day.
5. A login page, a usage-limit message or any challenge stops the run, which is reported. Nothing is worked around.

### Robust focus (2026-11-03)

The first click on the app only focuses it, and the owner's Chrome (or its ChatGPT extension) can take the foreground at any
time, so a send, a download click or a keystroke could land in another window (the Babel long's first builder prompt sat unsent in
the composer). `ui.ps1` (repo copy: `desktop-app/ui.ps1`) now does, before EVERY click, keystroke or scroll: find the ChatGPT window
handle, restore it if minimized, `AttachThreadInput` + `BringWindowToTop` + `SetForegroundWindow` + `SetFocus`, and verify with
`GetForegroundWindow`, up to 3 tries. If ChatGPT cannot be the foreground nothing is clicked or typed (`FOCUS_FAILED`, exit 9), and the
click/type/scroll checks again just before acting (`FOCUS_LOST`). `-nofocus` is only for the "Salvar como" dialog (typing the path),
never for clicks. If the foreground keeps changing within seconds the owner is using the PC: wait 5 minutes and retry; report
to the coordinator when it persists more than 30 minutes.

### Chat lock (E305, 2026-11-05)

Owner, 2026-11-05: a still was generated in the WRONG chat. `send2.ps1` clicked the composer at fixed coordinates,
pasted and pressed Enter without knowing which conversation was open. Rule: **every still goes to the one chat
"HeroVerse — stills", and that chat is identified before anything is pasted or sent.** `select_chat.ps1` (repo copy
`desktop-app/select_chat.ps1`, deployed to `C:\HeroVerse`) does it with Windows UI Automation:

1. `OWNER_ACTIVE` (exit 3): `GetLastInputInfo` shows input in the last 120 s that this route did not make (`ui.ps1`
   writes the tick of its own last action to `lastact.txt`). Nothing is clicked, typed or invoked.
2. Unless `-verifyOnly`: a UIA Invoke on the sidebar button named exactly for the chat. When the virtualized sidebar does
   not hold it, the app's own search palette (Ctrl+K, a new focused ComboBox) gets `stills` and the one row named exactly
   `<chat> ChatGPT Alt+<n>` is invoked. A prefix match ("HeroVerse: …") never counts; Enter is never pressed; a new
   chat is never created.
3. Verification, all required: the page document is named exactly for the chat; the sidebar row is selected (its
   `bg-primary-ghost-hover` class) or the conversation header shows that name; and the conversation, outside every
   input box, holds this project's prompt marker ("Create an image, 16:9 landscape, no text." or "…9:16 vertical
   portrait…"). Two sidebar rows with that name are ambiguous. Any failure is `WRONG_CHAT` (exit 4).

`send2.ps1` puts the prompt on the clipboard only after `OK`, and runs `select_chat.ps1 -verifyOnly` again after the
paste and before Enter (a failure leaves the draft unsent and untouched). `one2.ps1` phase 1 verifies before any
download click. `drive.ps1` STOPS the run (log line `STOP <still> WRONG_CHAT|OWNER_ACTIVE`, exit 2) instead of retrying.
PRIVACY: the owner uses the app for unrelated conversations; the guard prints only the stills name, booleans and
counts, and nothing of another conversation is copied, logged or committed. Test the guard alone (`select_chat.ps1`,
`-verifyOnly`, `-viaSearch`) only while the owner has been idle for at least 120 s; it never sends a prompt.
