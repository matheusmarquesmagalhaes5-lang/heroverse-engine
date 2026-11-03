# Studio runner (owner's PC)

Owner, 2026-11-03: "eu autorizo você fazer tudo pelo meu PC". YouTube Studio tasks the Data API cannot do (first: a
Short's **Related video** / "Vídeo relacionado"; no API field exists, see `evidence/youtube-api/20261026-related-video-and-pin.json`)
run on the owner's Windows PC, in the runner's **own** Chrome profile (`C:\HeroVerse\studio-runner\profile`), with the
owner's residential IP. Google cookies never leave the PC and never enter the repository, a log, a receipt or a PR. The runner never
opens the owner's everyday Chrome and never types or reads credentials.

**On demand only.** No scheduled task, service or startup entry is installed. Production calls it through Desktop Commander
when the PC is online; the owner may run it by hand. Offline PC: jobs wait, nothing else blocks.

## Flow
1. Cloud: `migration/channel/related_map.py build --public-check` writes `migration/channel/studio_jobs.json`
   (`{video_id, action:"related_video", target_video_id, reason, target_title?}`). Mapping: a cut -> its source long; an old
   `short:<pilot>` Short -> its recorded long; any other Short -> its compilation chapter, else its arc's long, else the newest
   public long. Non-public videos and targets are skipped; longs get no job; the three hand-done flood cuts are skipped.
2. PC `runner.py run`: reads the queue and `migration/evidence/studio/*.json` from origin/main through the PC's logged-in `gh`;
   per pending job (one video at a time, at most 30, 30-90 s between videos) opens `studio.youtube.com/video/<id>/edit`,
   skips it if the field already shows the target (ALREADY), else picks the target in the picker, Saves, reloads and verifies
   (DONE). An unknown UI state saves `out\debug-*.png` locally and marks the job FAILED with the reason (retried by a later run).
3. Receipts: `migration/evidence/studio/<date>.json` (ids, outcomes, short details), pushed as a data-only
   `claude/studio-receipt-*` PR through `gh api`; the hourly clock auto-merges evidence-only PRs. If the push fails, results stay
   in `ledger.json` (`unsent`) and the next run sends them.

## Commands (PowerShell, in `C:\HeroVerse\studio-runner`)
| Command | Does |
|---|---|
| `.venv\Scripts\python deploy.py <commit or branch>` | install/update from the public repository |
| `.venv\Scripts\python runner.py status` | `LOGGED_IN` / `NOT_LOGGED_IN` (cookie names only) |
| `.venv\Scripts\python runner.py login` | visible Chrome window on studio.youtube.com; **the owner signs in once**; up to 15 min |
| `.venv\Scripts\python runner.py run [--dry-run] [--max N] [--headed]` | does the pending jobs (headless unless `--headed`); `--dry-run` only lists them |
| `.venv\Scripts\python runner.py probe <video id>` | which `selectors.json` entries match on one edit page; read-only |

Exit codes of `run`: 0 all done, 1 some FAILED, 2 receipt PR failed, 3 not logged in. `selectors.json` holds the page text and
selectors (English and Portuguese); the UI flow has not been exercised on the live Studio yet (no login on the PC), so the first
`probe` and a one-job `run --max 1 --headed` after login are the acceptance check.
