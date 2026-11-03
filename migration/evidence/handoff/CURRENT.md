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
- 2026-11-02 review done through `local-review.yml` run 41510862169 (E268; audio judged by ASR transcript and measures,
  not by ear): `pilot-017/inspection/claude_review.json`, thumbnail A "THE WATER STOPPED" approved. `approve.yml`
  (run 41521201681) PASS; `publish.yml` run 41524618475 uploaded it PRIVATE and scheduled public at 2026-11-02T23:30Z:
  https://youtu.be/1m-NUJhkdMY (title is the plan's "The Flood Ends: The Raven, the Dove and the Rainbow (Genesis 8-9,
  KJV)", not live-plan title A; B test later). E270: schedule.json is handoff-bound; the time goes in publish_at.
  Next: verify it is public after 23:30Z, `arcs.json`, pinned comment, the cuts (raven/dove; rainbow covenant), the first
  Keeper reflection spec, bridge Short genesis-10 (needs 9:16 stills).
- 2026-11-02 owner: Gemini is dropped as a required provider (E268); native-review runs 41501277357/41502101074 ended
  provider INTERNAL and are superseded.
- The shared lease was taken and released (idle). No Short is scheduled from this delivery; the bridge Short still
  needs 9:16 stills from the ChatGPT desktop route.

- 2026-11-02 owner order: Pavo talking clips for the Keeper lines; held PR #682 keeps 1m-NUJhkdMY unpublished. Chest-up
  clips from shot-probe 41534197400: k-insight and k-close are approved in `shots/` (E271: an approved clip owes no
  probe; preflight PASS). k-bow failed the pinned ASR words check on both generations and stays on the Kokoro
  voice-over fallback; see DECISIONS. Next: `episode.yml` rebuild, then the review of the new master.

- 2026-11-03 owner order: "Pode soltar aquele longo": the held version of 1m-NUJhkdMY is released as it is (DECISIONS
  2026-11-03). It is out of `hold-plan.json`; `channel-privacy.yml` mode `release` (`release-plan.json`) makes it public and
  records the read-back. Then the cuts via `short-cuts.yml` (`cuts/flood-ends-long.json`), spaced across the day. The Pavo
  rebuild is a later separate version.

- 2026-11-03: 1m-NUJhkdMY is PUBLIC (channel-privacy `release` run 41558453690, read back public/processed; receipt
  `channel/release-receipt-41558453690.json`, ledger entry `released`). Cuts of it (`bible/cuts/flood-ends-long.json`,
  short-cuts run 41564529888): flood-ends-dove-cut 05:30Z, flood-ends-rainbow-cut 13:30Z, flood-ends-door-cut 18:30Z, each
  reviewed on its own hash (local-review) and published by `publish-episode.yml` with the long's link. Still to do for the
  long: pinned comment (first comment 403, see ledger), `arcs.json`, the Pavo rebuild is a later version.

- 2026-11-03 (Claude session, after the coordinator's 01:45 UTC decisions): `1m-NUJhkdMY` is public; the three cuts are
  scheduled by the coordinator (05:30, 13:30, 18:30 UTC). Bridge Short genesis-10 is BUILT and reviewed but NOT published:
  master sha256 `a1f99c4f…` (episode.yml run 41581203357, 170.97 s), record `episodes/genesis-10-short.json` (review 9.5, slot
  2026-11-03T23:30Z), blocked only by `THUMB_NOT_APPROVED` (needs a Noah close-up thumbnail spec + approved candidate; Pavo is
  not allowed for stills). Next: thumbs spec/candidate, `episode_build.py check-record`, `publish-episode.yml` at the free slot
  (23:30 UTC today, else 2026-11-04 13:30). Keeper reflection #1 rendered (run 41576620259) but not claimed at 9.5 (see DECISIONS).
  Noah compilation: `compilation_long.py` takes a public long as a chapter; the plan and a new Pavo hook/close are still to do
  (due 2026-11-04). The chat "HeroVerse — stills" is kept for the genesis-11 stills (delete it when those are done).

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
