# HeroVerse: current continuation

Read `../../SYSTEM.md` for the operating contract and `../../OPERATIONS.md` ("Automation map (2026-11-02)") for
the routines and entry points. This is the only active public handoff. Media, private provider identifiers and
exact receipts stay out of it. Today's plan is `../../strategy/live-plan.json`; moments and fallbacks are in
`../../strategy/DECISIONS.md` ("2026-11-02 — Battle plan to YPP").

## Current delivery: flood-ends-long (Genesis 8-9, buzzy-long, plan `plans/flood-ends-long.json`)

- 30 stills approved as sources (#646, #649). ChatGPT stills are available: the 1 Nov limit applied only to the
  Codex/Work tab. All stills use ONE chat, "HeroVerse — stills" (if a limit or error appears: close the app, wait
  5 min, reopen, continue in the same chat).
- 2026-11-02 (fallback taken, no Pavo): the three Keeper shots are his Kokoro voice-over: k-insight and k-bow on still
  motion of stills that reuse the bytes of the approved Keeper stills (arc-01-long k-promise-2/3), k-close on a vetted
  hearth-fire clip. One Buzzy shot (E242, buzzy-long needs it): s-dove-out, 12 s clip, task
  gt_aui5o53NiZyHibkxaui8PLubsndUbmyY (a 10 s first clip was too short; both are in the ledger; balance before/after
  not readable in the session). Preflight PASS (E267).
- Built: `episode.yml` run 41484825424, report `evidence/episodes/flood-ends-long/report-41484825424.json` (501.83 s,
  -14.4 LUFS, sheet viewed). Pilot `buzzy-long-pilot.yml` run 41500348534: QA PASS; its PR carries pilot-017.
- BLOCKED at the native review: `native-review.yml` run 41501277357 (full master, Free Tier proof ok) and its single
  retry 41502101074 both ended provider INTERNAL with no model output; the one allowed retry is used. No audiovisual
  review exists, so no `claude_review.json`, no approval and no publication yet. Next: a native review of the same
  master that completes (a new executor/provider session able to hear it, or a later run once the provider recovers),
  then `claude_review.json` (defects + publish decision), thumbnail A/B from live-plan, `approve.yml` ->
  `prepublish_gate.py` -> `publish.yml` at 13:30 or 23:30 UTC, then the cuts.
- 2026-11-02 owner: Gemini is dropped as a required provider (E268). The native review is now `local-review.yml`
  (plan `plans/flood-ends-long.json`, sha256 `9a2d0f24e74c7117eedcbdd73992fbc284efb9402b6f82dba98f096a64635692`): pinned
  ASR + ffmpeg measures + timecoded frame sheets; the session reviewer then views the sheets (artifact
  `local-review-frames`), reads the transcript (artifact `native-review-public-evidence`) and writes `claude_review.json`.
- The shared lease was taken and released (idle). No Short is scheduled from this delivery; the bridge Short still
  needs 9:16 stills from the ChatGPT desktop route.

## Next moments

- M2 compilation "Complete Story of Noah (Genesis 5-9)" is due 2026-11-04.
- genesis-09-short is public (https://youtube.com/shorts/IYSxVKTikSs). The bridge Short genesis-10 continues only
  if stills exist; Short slots after the long is public. TikTok mirrors each public Short through `tiktok.yml`.

## Brand

The new avatar and banner ("the Keeper by the fire") are live on YouTube and on the Facebook Page
(id 61595804835184).

## Keep the established rules

Pavo only at a fresh exact zero-credit quote with GET-only reconciliation of saved jobs and no retry. God's words
stay exact KJV on Kokoro and God is never depicted. No source or final score is invented. The long uses its
separate route. The existing heartbeat and supervisors remain; no new clock. Update this handoff at the next
accepted boundary.
