# HeroVerse: execution entry points

`SYSTEM.md` is the current operating contract. `evidence/handoff/CURRENT.md` is the continuation point.
This file maps that contract to existing code. Credentials stay in repository secrets; unfinished private media,
provider URLs and recovery keys stay outside public code, logs and handoffs.

## Bible Short

| Work | Existing entry point |
|---|---|
| Validate the planned story | `production/bible/plan_check.py --strict PLAN`; exact Scripture through `kjv_check.py` |
| Inspect and approve sources | `shot-probe.yml`, `episode_build.py approve-shot`, `shot_sources.py`, `scene_stills.py`; current request/media bindings and explicit reviewer identity |
| Preserve an existing edit | `episode_build.py import-edit BINDING ROOT WORK`; keeps the original PCM, final mix, captions and exact timeline without voice synthesis |
| Check the current regular build | `episode_build.py preflight PLAN --voice VOICE_PYTHON PREPARED_WORK --refs --write`, then `verify-preflight PLAN` |
| Assemble approved shots | `episode.yml` → `episode_build.py` → `short_engine.py`; no new generation inside assembly |
| Inspect a private draft | `episode_build.py render-imported WORK OUT` / `production/draft_render.py`; DRAFT only, not a publication qualification |
| Native audiovisual evidence | DEFAULT `local-review.yml` → `production/bible/local_review.py` (pinned ASR hears the audio, ffmpeg measures, timecoded frame sheets; no secret, no PC; E268); optional second opinion `native-review.yml` → `production/bible/native_review.py` (Gemini); actual complete master audio/video and saved result identity |
| Thumbnail | `production/bible/thumbs.py`: check/refs/finalize/sheet/approve; required for BibleShort part 9 onward |
| Check publication record | `episode_build.py check-record EPISODE_JSON [VIDEO]` → `episode_preflight.record_problems` → `publish_episode.problems` |
| Publish and reconcile | `publish-episode.yml` → `publish/publish_episode.py`; existing `publish/ledger.json`, episode record and `publish/receipts/` |
| Confirm completion | Read the same video's receipt/API state: public and processed; resume incomplete package work on that ID |

A regular build accepts only current preflight and approved source evidence. An imported edit is reconciled
against its own actual timeline and accepted audio; imports do not qualify sources or replace final review.
Before any publisher is called, the record must describe the actual passing review and qualified package.
`check-record` validates its implemented record checks; it does not perform perceptual review.

Related video (Studio-only, owner 2026-11-03): every newly scheduled Short gets an entry in `channel/studio_jobs.json`
(`migration/channel/related_map.py build --public-check` regenerates it; mapping rules in
`integrations/studio-local/README.md`). When the PC is online, production runs
`C:\HeroVerse\studio-runner\.venv\Scripts\python runner.py run` via Desktop Commander (on demand, no schedule on the PC);
the receipt arrives as a data-only `claude/studio-receipt-*` PR under `evidence/studio/`. If the PC is offline, the jobs wait
and nothing else blocks.

Private ingress must deliver the exact file to the existing episode publisher without publishing unfinished media
in a repository release or logging private URLs. Consult the workflow's current declared inputs and recorded
claims; do not invent an input name or a new approval format. The workflow remains `publish-episode.yml`.

## Story long

`production/bible/LONG_DESIGN.md` defines construction and its frozen profile. The implemented route is
`long_plan_check.py --strict` → long preflight → `long-build.yml` → `long_handoff.py`/technical evidence →
`production/long_review.py` → `approve.yml` → `publish/prepublish_gate.py` → `publish.yml`.
Use the exact allowed reviewer identities and evidence in `ops/CLAUDE_REVIEW.md`.
Only that workflow creates the long's `APPROVAL.json`. The Short uses its episode record and publisher instead.

Compilation long (owner, 2026-11-01; E251): an arc's complete story assembled from its public Shorts. Plan
`production/bible/compilations/<id>.json` → `compilation-build.yml` (`compilation_long.py`: masters by sha256, 16:9
over a blurred fill, chapter cards, the Keeper's new hook and close from Pavo clips at an exact zero-credit quote,
gain-only -14 LUFS, faded joins; QA `compilation-qa-criteria-v1`) → the Gemini native review as a defect finder →
`inspection/claude_review.json` with `defects` and a `publish_decision` by `claude-session-reviewer`
(`owner_quality_policy.compilation_problems`: no unresolved [a], [b] or [e]) → the same `approve.yml` →
`prepublish_gate.py` → `publish.yml`. The 9.5 track of the story longs is unchanged.

## Long-first and Short cuts

Owner, 2026-11-01 (DECISIONS.md "Long-first, Shorts cut from the long", E259): after the current Noah compilation the
story is made once as a 16:9 long, and the Shorts are coherent 9:16 cuts of it. Nothing below spends credits.

| Work | Existing entry point |
|---|---|
| Plan the long | `plans/<id>.json` (bible-plan-v2) with `"track": "buzzy-long"`, `"aspect_ratio": "16:9"`, 480–720 s measured, every prompt "centred in the frame" (PROMPT_GUIDE "Long-first"), and `long` = pilot, title, description with `{chapters}`, tags, first_comment, chapters on shot ids, thumbnail frame; `plan_check.py --strict` |
| Sources, preflight, build | the Short's own route: `shot-probe.yml` / `scene_stills.py` / `shot_sources.py` at 16:9, `episode_build.py preflight … --write`, `episode.yml` (1920x1080, 16:9 captions, owned music, -14 LUFS) |
| What the cuts need | `episode.yml` record job: master `bible-<id>-sha256-<sha>.mp4` and caption-free master `bible-<id>-clean-sha256-<sha>.mp4` in the release; `evidence/episodes/<id>/report-<run>.json` binds both hashes, the sentence timeline (`composed.sentences`) and the shot timeline (`composed.timeline`) |
| The long's pilot | merge the report, then `buzzy-long-pilot.yml` (plan, report) → `buzzy_long.py qa` (buzzy-long-qa-criteria-v1) + `materialize` → `<pilot>-sha256-<sha>.mp4` alias and the pilot on `claude/long-<id>-<run>` (PR) |
| Review and publish the long | `local-review.yml` (plan = the long's plan, sha256 = its master; defect finder; `native-review.yml` is optional); the session reviewer writes `inspection/claude_review.json` (defects, publish decision); thumbnail approved through `thumbs.py` (format long); then `approve.yml` → `prepublish_gate.py` → `publish.yml`, on the defect-gated buzzy-long track |
| Cut the Shorts | `cuts/<long>.json` (bible-cuts-v1, track buzzy-cut, pilot, report, cuts: id, start, end, optional x, title, description with "full story", tags, first_comment); `short_cuts.py check SPEC` refuses a cut inside speech, off sentence edges or outside 20–179 s; `short-cuts.yml` renders them (centre 9:16, Short captions, gain-only -14 LUFS, fades), puts `bible-<cut>-sha256-<sha>.mp4` in the release and draft `episodes/<cut>.json` (track buzzy-cut, parent long) on `claude/cuts-<long>-<run>` |
| Review and publish each cut | `local-review.yml` with plan = the cuts spec and the cut's own sha256 (never the long's score), the session reviewer's `review` (defects, publish decision) in its record, `episode_build.py check-record`, then `publish-episode.yml`; `arc_links.py` links each cut to its long through `parent.pilot` |

Long-first stills move by need (E261): `episode.yml` maps each approved still's depth (Depth Anything V2 Small, ONNX
on CPU, sha256-pinned; unreachable model: a depth proxy, recorded) and `episode_build.py generate` renders every still
with `motion.direct`'s move, fitted to its spoken span (about 15–60 s of CPU per 15–20 s shot at 1080p). The move and its reason
are in the report's `motion_direction`; a plan shot's `motion`/`atmosphere` overrides it (PROMPT_GUIDE "Cinematic
still animation").

The 9.5 story long (`approve.yml` on story-qa-criteria), the Short episode route, the compilation and every frozen
QA file keep their rules; the buzzy-long and buzzy-cut tracks apply only to their own criteria and records.

## Keeper reflection Short (one a day, about 30 s)

Owner, 2026-11-02 (DECISIONS.md "Shorts cadence"): 9:16 1080x1920 in two 1080x960 halves. TOP: a moment of one of our
own published longs (its caption-free master, re-framed to fill, its audio ducked under the reflection or muted).
BOTTOM (owner rule, same day): the Keeper really speaking, never a still motion. The reflection (ours, 20-80 words) is
split into 2-4 sentence-safe segments; each segment is an approved Pavo talking clip (about 10-12 s, the same machinery
as a long's Keeper lines), cropped to 1080x960 with the face centred and joined by 0.2 s crossfades. The audio is the
clips' own: our Kokoro line `am_michael` that Pavo lip-synced, exactly as in a long's talking shot. Captions in the series
style. KJV appears only if the spec shows it (`verse`, exact by `kjv_check`). `bible-reflection-v1` (a still moved by
`motion.py`) is retired: the checker refuses it.

How production makes one:

1. Spec `reflections/<long>-<n>.json` (`bible-reflection-v2`, id `<long>-reflection-<n>`): `long`, `pilot`, `report`,
   `clip` {start, end, x, audio duck/mute}, `plan` (`plans/<id>.json`), `segments` [{shot `k-r1`..`k-r4`, text}],
   optional `bottom` {y}, optional `verse`, `title`, `description` (public domain, AI, "full story"), `first_comment`
   (holds `https://youtu.be/<the long's video id>`).
2. `reflection_shorts.py scaffold SPEC` writes the probe plan: `bible-plan-v2`, `track: keeper-reflection`,
   `aspect_ratio: 1:1`, one talking Keeper shot per segment (the long's own Keeper prompt: his look, wardrobe, chest-up
   framing, `talk_refs` reference; only his expression differs). `plan_check.py --strict` judges it (`reflection_check`:
   2-4 talking Keeper shots, one insight line each, whole sentences, each line one 4-12 s clip can carry after the 10 %
   retime, 20-80 words; no voice-over, scene, share or Short length rule).
3. `shot-probe.yml` on the plan (all segments, `attempts: 1`): exact 0-credit quote, at most 2 generations a segment (E264),
   every generation kept with its flags (E266). Claude watches and hears each clip, then `episode_build.py approve-shot`
   (`shots/<id>.json`, by PR).
4. `reflection_shorts.py check SPEC` (also the first step of `reflection-shorts.yml`) refuses a long that is not long-first
   or not in `publish/ledger.json` under `<pilot>:<master sha256>`, a top clip outside 20-40 s or inside a spoken sentence,
   a plan that fails `plan_check`, segments that are not the plan's lines word for word, a segment without an approved
   Pavo clip (score >= 9.5, named reviewer, no retraction, 4-12 s, a probe record whose request carried exactly these
   words), a Keeper timeline that does not fit the top clip (clips + 0.6 s tail <= clip, last frame held at most 3 s,
   speech >= 45 % of the Short), a banned word, an inexact verse.
5. `reflection-shorts.yml` (dispatch on main, spec path): check, caption-free master by sha256, `fetch-clips` (the approved
   clips by their content-hash names, sha256 checked), `reflection_shorts.py render` (clips cropped, crossfaded, each
   placed so the crossfade runs in the previous clip's silent tail; a tail under 0.22 s refuses the render; 115-165 wpm;
   -14 LUFS gain, fades), `bible-<id>-sha256-<sha>.mp4` in the release, draft `episodes/<id>.json` (with `segments`) and the
   measures on `claude/reflection-<id>-<run>` (PR).
6. `local-review.yml` with plan = the spec and the Short's own sha256, then the session reviewer's `review` in the record
   after watching and hearing the Short (`overall` >= 9.5: track `keeper-reflection` keeps the standard Short floor; no
   Buzzy shot is asked of its parent), `episode_build.py check-record`, `publish-episode.yml`; `arc_links.py` links it to
   its long through `parent.pilot`.

Flags on a talking clip (E266, `episode_build.flag_split`; the owner judged the Pavo lip sync perfect, so the automatic
lip-sync and audio-match measures only inform): HARD (`FACE_NOT_FOUND`, `clip_check`, `NO_VIDEO`, `MOUTH_TALKING`,
`GOD_SHOT_FACE`) is never approved or shipped; WORDS (`AUDIO_NOT_OUR_LINE`) is approvable once Claude's review confirms the
words and `speech-check` (pinned faster-whisper) heard the line: `approve-shot` records `accepted_flags` + `words`, and a
clip whose ASR words differ stays a hard `SHOT_WORDS_NOT_OUR_LINE`; SOFT (`MOUTH_NOT_IN_SYNC`, `AUDIO_OFFSET`) never blocks,
the approval records it. `reflection_shorts.py check` repeats it per segment (`SEGMENT_CLIP_HARD_FLAG`,
`SEGMENT_CLIP_WORDS_UNPROVEN`, `SEGMENT_CLIP_WRONG_WORDS`). A Keeper segment that fails both generations falls back to the
DECISIONS ladder only for a long; a reflection without all its clips is not made that day (the cuts and bridge Shorts go on).

Pavo's audio is Pavo's, in full (owner 2026-11-03: "Quero com o audio do pavo tambem.. quero o video do pavo na integra. A
narracao feita vai ser pras imagens.. aproveitar tudo que o pavo pode oferecer dentro das capacidades"). This reverses E287's
default: `pavo_audio` is a per-shot setting whose DEFAULT is `"pavo"` on every track (long compose, reflection, compilation,
bridge Shorts). The kept clip is exactly what Pavo returned (no mux; `trim_out_s` only when the shot or approval sets it);
its `audio` proof records the digest of Pavo's own track and its LUFS/true peak. approve-shot records the one gain that
matches it to the narration within +-1 dB under a -1.5 dBTP limiter and the whole clip as its speech span; the compose
(`native_voice`, long_build) lays it into the voice track and lays the clip's whole length out as that shot's slot, while
the Pavo request keeps its pre-approval seconds and WAV (`layout.pavo_requests`). Kokoro narration stays on the still and
scene shots. Visual gates are unchanged (face, mouth sync against the clip's own track, artifacts); `AUDIO_NOT_OUR_LINE` and
`SPEECH_WORDS_NOT_EXACT` are no refusal for these shots: `speech-check` writes the ASR text to `review_notes`, and a direct KJV
quotation whose words differ carries `WARN_KJV_WORDS` for the reviewer (KJV-exact pillar; a warning, never automatic). A
stored clip is moved to this route by `shot-remux.yml` too (the route of the shot decides: the stored bytes are kept, only
re-judged; a stored clip that already has our line laid over it is refused, `PAVO_AUDIO_IS_OURS`: its original asset is the
legacy probe's). Explicit `"pavo_audio": "ours"` keeps E287 below; approvals recorded under it keep it.

Pavo's audio is ours (E287, now an explicit option; owner 2026-11-03: "o pavo nao tem vida propria... quem ta errado e voce"). On the Kokoro-input route
(`sound: false`, our exact line as the request's input audio) the clip we keep is Pavo's picture with the request's own WAV laid
over it (`pavo_audio.mux_ours`, PCM, bit-exact); Pavo's returned track is dropped and never judged. Words are the request's
words (exact by construction); `pavo_audio.assert_ours` proves the kept audio equals the request WAV and the probe record
carries it (`pavo_audio: "ours"`, per clip `audio` = sha256 + samples). `lipsync_check` measures the SyncNet offset and
confidence, the face and the clip checks against that same audio, thresholds unchanged. So `AUDIO_NOT_OUR_LINE` and
`SPEECH_WORDS_NOT_EXACT` cannot come from Pavo's track any more, no `speech-check` is owed for these clips, and
`approve-shot` refuses a clip of such a record without the proof (`SHOT_AUDIO_NOT_OURS`); `reflection_shorts` verifies the
digest on the approved bytes (`SEGMENT_AUDIO_NOT_OURS`). Pavo's own speech (`audio_route: pavo_native`) keeps its story QA v4
checks. Evidence: `evidence/pavo-audio-eval/20261103.json` (`pavo-audio-eval.yml`, 21 stored clips, nothing generated: 13 of
the 16 rejected only for words or audio hold sync with our audio). Legacy approvals (Pavo's track kept) keep the E266 rules.

**Editing rule: what Pavo generates is used (owner 2026-11-03, E290).** Under E287 (our WAV over Pavo's picture)
every generation with a visible face and sync within the `lipsync_check` thresholds is usable, and it is used. Its
small defects are fixed at EDIT time, never by a new generation: the tail is trimmed at the last word (`trim_out_s`,
E273/E282), the join is a picture crossfade inside the silence (E272; Shorts keep cuts), a clip set faster than the band
is retimed by at most 10 % (E286/E288). `TALK_ATTEMPTS` stays 1; a second generation only for a visual defect
`preflight.yml` (2026-11-04, dispatch on main, input `plan`): the long or Short preflight with the pinned Kokoro voice in Actions
(`episode_build.py preflight --voice --refs --write`), report on `claude/preflight-<episode>-<run>` for a PR; no local Kokoro.
**Owner standing rule (2026-11-04, E296, DECISIONS):** no per-line consultation. A talking line whose stored generations all
failed on words, sync or NO_VIDEO takes one `shot-probe` generation per prompt revision (changed `pavo_prompt.build` prompt +
`pavo_prompt.py lesson` naming the shot and its 12-hex revision, `episode_build.prompt_revision`), `pavo_audio: "pavo"`, at most
3 extra per line (`owner_regen.json` `standing_rule`); refusals PROBE_SAME_PROMPT, PROBE_STANDING_LESSON, PROBE_STANDING_CAP,
PROBE_STANDING_NOT_FAILED, PROBE_PAVO_AUDIO_OURS.
(`episode_build.visual_defect`). Prompts come only from `pavo_prompt.build` (PROMPT_GUIDE "Pavo talking-shot prompt
standard"); production reads `strategy/pavo_lessons.md` first, and Inteligência Viva appends each day's probe and
review outcomes with run ids (`pavo_prompt.py lesson DATE worked|failed|rule TEXT EVIDENCE`).

A clip stored before E287 (Pavo's track kept) is re-judged on our audio by `shot-remux.yml` (E288; plan + `shots` =
`shot:sha256-prefix` of uploaded clips in committed probe records; no Pavo call, no secret, nothing generated): the stored
picture by its sha256, the plan's request must still equal the one that made it, our regenerated Kokoro WAV laid over it
(`pavo_audio.mux_ours`), the strict `lipsync_check`/`clip_check` on that same audio, then the new clip (its own content-hash
asset) and a probe record (`pavo_audio: ours`, `audio` proof, `remux_of`) on branch `claude/shot-remux-<episode>-<run>`;
`approve-shot` then runs on that record like on any probed clip.

A reflection record has `track: keeper-reflection`, `layout: keeper-reflection`, `parent` {long, pilot, clean_master_sha256,
start, end}, `segments` [{shot, asset, clip_sha256}] and no review. A new file is a new review; the long's score is never
copied. Today only a long-first long with a caption-free master and sentence timeline can be the source (a compilation, as
the Noah one, keeps chapter cards and has no sentence timeline of its own).

## Sources and private provider work

Reuse approved matching material first. Existing source tools include `shot-probe.yml`, `scene-stills.yml`,
`production/bible/shot_sources.py`, `production/footage/`, the image tools and ffmpeg. The authorized GPT-still route
retains its real provenance; source/rights/identity/context checks still apply.

`pavo-private-audio.yml` supports the existing private exact-audio and first-frame requests. It uses the current
shared lease, quota, exact zero-credit quote, encrypted transfer and durable claim. A saved conversation ID is
reconciled by GET, never resubmitted because a caller timed out. A claim without a definitive result is unresolved.
Any bounded retry must satisfy the existing helper/workflow's recorded failure and eligibility checks; elapsed
time does not prove capacity. These paths return source evidence, not final audiovisual approval.

`local-review.yml` (owner 2026-11-02, E268) is the default native review for every track (buzzy-long, compilation, cuts,
keeper-reflection, Shorts): inputs `plan` and `sha256` only. It downloads the master from the release by sha256, hears the
whole audio with a pinned faster-whisper small.en against the script (report sentences, else the episode record or the
plan), measures loudness / true peak / clipping / silence / voice over music with ffmpeg, and writes a timecoded frame
sheet (1 frame / 2 s), black / frozen / duplicate-frame and scene-change evidence. Artifact `native-review-public-evidence`
(the `native-review-public-v1` shape, issues as `MM:SS [category] text`, rubric scores null: a machine measure is not a
score) and artifact `local-review-frames`. The session reviewer downloads both, views the sheets, reads the transcript
and writes `claude_review.json` / the record `review` from what it saw and heard. No secret, no PC, no Free Tier proof.

**Per-sentence WER and UTMOS in `local-review.yml` (2026-11-04, WARN only).** `local_review.py` now computes the word error
rate of each script sentence against the pinned ASR transcript (`measures.audio.wer`: substituted/missing/extra words, strict, near
spellings also counted) and, when the optional workflow step installed it, UTMOS22-strong naturalness on CPU
(`measures.audio.utmos`: MOS per heard sentence, at most 120 clips; pinned SpeechMOS commit and weights sha256, no secret). Findings
go to the public evidence key `warnings` as `MM:SS.ss [warn] ...`, never to `issues` or `machine_verdict`. Thresholds are
PROVISIONAL and uncalibrated (sentence WER > 0.30 on 4+ words, overall WER > 0.12, sentence UTMOS < 2.0, mean < 2.8; UTMOS on a mix
with music reads low). They stay WARNs until a run over the accepted masters is recorded in
`evidence/reviewer-calibration/` and the numbers are changed by a PR that cites it. A failed UTMOS step does not fail the review
(`utmos.status` is `NOT_RUN`). The session reviewer listens to every warned sentence; a warn is not a score.

`native-review.yml` (Gemini, optional second opinion) uses the existing operator certificate and configured provider credential without exposing the
credential to the caller. Verify current Free Tier eligibility before submission. Preserve upload/interaction IDs,
raw answers, exact model identity and media binding. Reconcile uncertain outcomes rather than repeating a POST.
Every run also writes non-sensitive score evidence (status, provider error codes, overall, per-criterion scores and
timed issues; no media, provider IDs or secrets) to its job summary and the 90-day `native-review-public-evidence`
artifact, so a later executor never needs another executor's private key to read a score (E233).
The runner never holds the master (E248): after a new run reaches `Persist upload state before inference`, the
caller downloads that run's `native-review-upload` artifact, decrypts it with the matching private key, and sends the
exact master bytes once to the receipt's `upload_url` (`X-Goog-Upload-Command: upload, finalize`, offset 0). Until
then the provider has no file and `Await exact-byte upload` can only time out. If a run timed out that way, upload
to its saved `upload_url` and dispatch `resume_before_inference=<run>` with a fresh Free Tier proof.

**Gemini listening defect scan for longs (owner 2026-11-04, DECISIONS "Gemini free tier").** Dispatch `native-review.yml` with
`defect_scan=true` (plan = the long's plan, sha256/byte_size of the exact master, as any native review). The prompt adds a
`defects` array: `{timestamp, category, heard_or_seen, note, confidence}`, category one of mispronunciation, garbled_word,
loudness_jump, music_voice_clash, sync, visual_glitch, speech_cut, other. `validate_defects` refuses a malformed, out-of-media
or uncategorised list; the public evidence (`native-review-public-evidence`, job summary) then carries `defect_scan: true`,
`scores_are_information_only: true` and the sanitized `defects`. It is a detector: the session reviewer must listen to each
timestamp and record the true reviewer in `claude_review.json`; scores are never copied and nothing is approved. The existing
duplicate-content guard still applies to an unchanged master that already had a native review; when the master is large or the
free quota is tight, dispatch per chapter segment (a separate file, so a separate sha256) and add the segment start to each
timestamp. Calibration (Babel master `0386d34a...`: 00:55 "mighty", 02:17-02:22 b-brick, 06:51 "babel"; one approved Short)
is run through this dispatch and recorded in `evidence/reviewer-calibration/long-defect-scan-calibration.json`; until that file
shows the known defects found, treat an empty or partial list as no evidence of absence.

## Automation map (2026-11-02)

Three Claude scheduled tasks (routines) run the loop; no other clock is added. Each routine's final answer reaches
the owner as a push notification; routines do not message the coordinator session.

| Routine | When | Model | Role |
|---|---|---|---|
| Inteligência Viva | daily 05:17 UTC | Sonnet | Measures the goal gap, mines the market, sets strategy and battle-plan moment; writes `strategy/live-plan.json` and a DECISIONS entry |
| Produção | 06:43 and 16:43 UTC | Sonnet | Executes live-plan and the battle plan: longs, compilations, cuts, Shorts with a 48 h buffer, comments; follows the fallback ladder and never stops |
| Relógio leve | every 3 h | Haiku | Heartbeat; Pavo/Buzzy spend watchdog (cancels a shot-probe over attempts × attempts_for); merges green data-only PRs (`migration/strategy`, `migration/evidence`); fires production when a long or a failure is pending |

Sources of truth (link, do not copy):

- Today's plan: `strategy/live-plan.json`.
- Moments, fallbacks and the Pavo choose-best rule: `strategy/DECISIONS.md`, "2026-11-02 — Battle plan to YPP".
- Current delivery: `evidence/handoff/CURRENT.md`. Root causes: `ops/ERRORS.json` (query with `ops/errors_query.py`).

Token rules: `ops/token_budget.py` (budget in `SYSTEM.md`), the `ops/read_guard.py` Read hook, `ops/ci_digest.py`
for runs, `ops/errors_query.py` for errors. Model routing: Haiku checks, Sonnet production and intelligence, Opus
only coordination.

Free compute first: GitHub Actions, the owner's PC (ChatGPT app stills in the single chat "HeroVerse — stills"),
Gemini free tier. Pavo only at 0-credit quotes, 1 generation per talking line and a 2nd only for a visual defect of the first (E264, E287); Buzzy at most 100/day.

Owner-only steps that need a login: Buffer, TikTok `runner.py login`, the Telegram bot token secret, YouTube Studio
related-video links.

## Existing automation and its limits

| Surface | Existing responsibility | Evidence of operation |
|---|---|---|
| `heartbeat.yml` / `ops/heartbeat.py` | Durable request dispatch, qualified plan handoff, build evidence discovery and existing package/mirror tasks | Current workflow runs, summaries and request acknowledgements |
| `ops/production_handoff.py` | Queue an eligible `episode.yml` or `long-build.yml` request in the existing request path | Current plan/preflight/order results and saved request claim |
| `ops/review_discovery.py` | Discover build evidence branches and exact commits/run IDs | Inventory; it does not itself view media or approve it |
| Existing ChatGPT / Claude supervisors | Continue production, source inspection and actual audiovisual review under one shared lease | Actual available executor and saved results; installed tools alone do not prove availability |
| Existing watchdog | Detect stale heartbeat, failed runs and missed delivery; respect the active lease | Current run and observed condition |
| Existing daily report/learning | `goal-report.yml`, `mining/live_intel.py`, learning records | Actual public video/readback and age-matched analytics |
| `arc-links.yml` | Link public Shorts and their public, processed long | `publish/arc_links_ledger.json` |
| `tiktok.yml` | Free Buffer mirror of an already-public YouTube Short | `publish/tiktok_ledger.json` |

Keep the existing clock configuration; no additional polling scheduler. A heartbeat success or QUEUE_EMPTY from a
pilot renderer does not prove that a Bible Short has been reviewed or published. Perceptual review requires an
available authorized executor. Describe a handoff or restart as complete only after observing the relevant run.

After publication, existing comment/reply tasks use their current authorization, policy checks and ledgers.
Studio-only tasks such as related-video selection, pinning or end screens remain pending until verified.
They do not justify a duplicate upload.

## Shared executor control

The operational ref `claude/shared-executor-control` carries coordination metadata in its commit message after
`HEROVERSE_EXECUTOR_LEASE_V1\n`. Its tree equals its parent's tree. It is not a production branch or merge candidate.

Fields: schema `heroverse-executor-lease-v1`, owner `codex`/`claude`/`autopilot`/null (`autopilot` = `ops/autopilot_lease.py`; it never authorises a Pavo effect), run_id, state active/idle, renewed_at,
expires_at, task, base_main_sha and next_action. Keep descriptions generic; never store private links or credentials.

1. Read the ref and exact head SHA. Missing/malformed control permits read-only diagnosis, not a second controller.
2. If another active lease is unexpired, observe read-only. Available tokens do not transfer ownership.
3. Before taking idle/expired control, reconcile saved provider/workflow IDs, claims and acknowledgements.
4. Acquire by creating a commit whose parent is exactly that observed head and whose tree is unchanged; expiry is
   at most 55 minutes later. Update the ref with expected SHA and force=false. Competing sibling commits must fail.
   Read back your new SHA before effects.
5. Renew before effects and at least every 10 minutes during long work, using the same compare-and-swap procedure.
   Stop new effects if ownership changes. An expired holder reacquires.
6. At a safe boundary, record the real result and next action in CURRENT and the existing evidence/receipt, then
   release with state idle, owner null and expiry now. Do not release while a specialist or unrecorded effect runs.
7. An uncertain write is reconciled by reading the same operation/ref. Never force, reset or delete the ref.

Switching hosts transfers supervision of existing work; it never permits replaying an uncertain operation.
If neither executor is available, already-started GitHub jobs keep their state but no chat agent is reasoning.

## Code changes and document ownership

Use the existing `claude/*` → PR → checks/reviews → squash process. The original PR Review Toolkit and applicable
security sweep record the real executor, exact head/base and findings. Keep `ops/ERRORS.json` and antidote tests;
code-review evidence is not media approval. Existing host guards remain active.
To check a run, use ci_digest.py; read full logs only when the digest is not enough.

One current home per subject:

- `SYSTEM.md`: operating contract; `evidence/handoff/CURRENT.md`: current continuation.
- This file: execution entry points and shared control.
- `production/bible/SERIES.md`, `PROMPT_GUIDE.md`, `LONG_DESIGN.md`: series, construction and long-specific design.
- `ops/CLAUDE_REVIEW.md`: actual audiovisual review; `ops/ERRORS.json`: regression evidence;
  `ops/RUNNER_WAKEUP.md`: runner mechanics when that execution surface is needed.
- `ops/AUTOPILOT.md`: the free, session-independent pipeline design (autopilot phases, fallbacks).
- `strategy/DECISIONS.md`: current generic policy; `MODELING_SPEC.md`, `VIDIQ.md`,
  `BEAT_THE_REFERENCE_RULE.md`: research/measurement details subject to SYSTEM and current no-spending policy.
- `STANDARD.md`: applicable rendering mechanics; historical audits and evidence are records, not another work queue.

## Model routing and weekly pacing

Owner 2026-11-04: use ~100% of the weekly Claude cap, landing at the reset (Saturday 19:00 UTC), never earlier
(`project_share` 0.97). Run `python3 migration/ops/token_budget.py pace` at the start of a routine and before spawning
heavy agents; it prints AHEAD / ON_PACE / BEHIND, the target tokens per hour and a per-model split.

| Work | Model |
| --- | --- |
| Coordinator, final audiovisual judgement, tricky design or diagnosis | Opus, kept short |
| Production, build, PR and CI agents, Inteligência Viva, reviews | Sonnet |
| Light clock, polling, status reads, mechanical file moves | Haiku |

- Never spawn Opus subagents for mechanical work; give each subagent the model that fits its task.
- AHEAD (would hit the cap before the reset): shift work down one model tier and slow optional work (extra Shorts,
  speculative research); keep the long in progress and its reviews.
- BEHIND (spare capacity): pull forward queued production (the next long's stills and plan, extra Shorts within the
  cadence cap in `token_plan.json`). Never lower quality or skip a review to use tokens.
- ON_PACE: keep the rhythm. Re-run `pace` after any large agent; the 24 h rate drives the verdict.

## Shared Claude Code / ChatGPT execution: token budget

The token budget (`SYSTEM.md` "Token budget") counts Claude Code only, from the local Claude transcripts. ChatGPT/Codex
executor usage is a different account and is not counted here; the project share (97%, owner 2026-11-04) of the weekly cap governs Claude Code, and Codex keeps its own limits.
