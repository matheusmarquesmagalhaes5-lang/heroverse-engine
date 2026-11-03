# vidIQ: research and evidence in the current Bible series

`../SYSTEM.md` governs the workflow, story order, quality and no-new-spending policy. vidIQ supports research and
learning for the English KJV Bible series. Its suggestions and estimates do not approve media or decide publication.

## Access, cost and continuity

Use the currently exposed authorized connector and its live tool descriptions. Verify the account/channel when
relevant; an old connection record, session name, balance or tool catalogue is not proof of current availability.
Use a read or job recovery only when its actual cost and current authorization permit it.

Keep the existing `evidence/vidiq/ledger.json` and configured research ceilings: at most 10 calls/day and the
recorded cycle budget, historically capped at 2,000 credits. Those are ceilings, not permission to spend a remaining
balance. No new paid call or generation follows merely from an unused allowance. Save/reuse completed results.
A previous per-call price or historical subscription allocation must not be treated as a current quote.

Recover an existing job by its saved ID through the supported read operation. A wrong-account/no-such-job result
is an access finding, not permission to regenerate or keep trying identifiers. Preserve uncertain outcomes and
their request identity; never submit another generation to reconstruct an available result.

Existing deny rules and publication boundaries remain in force. Channel writes, uploads and outward messages
use their authorized project paths, not a research tool's suggestion. Do not change account access or revoke a
connection merely because this guide describes a capability.

## Useful research

| Question | Evidence to use |
|---|---|
| How does the next fixed Bible story become a compelling episode? | Story-matched outliers, hooks, beat structure and audience questions; the series order remains fixed |
| Which packaging communicates the actual story? | Relevant title/thumbnail patterns, informative keyword estimates and the approved character presentation |
| What needs improvement after publication? | The real video's age-matched performance, retention and comments, with the source and observation time |
| Which structures are supported? | Current winners and weak contrasts, watched/heard evidence and measured attributes under MODELING_SPEC |
| Why did a previous job stop? | Saved job/readback records, exact account/capability and current cost evidence |

Use official channel/Analytics readback where available and identify cached/modelled third-party values accurately.
Earnings estimates, AI scores and keyword scores do not establish revenue, monetization readiness or a guaranteed
audience response. Deidentify audience comments; retain only necessary evidence and comply with the current source
and quotation rules.

The retained keyword validation `evidence/vidiq/validation-20261018.json` failed its preregistered correlation floor.
It remains a result of that sample; do not treat keyword scores as a validated tie-breaker or rerun a paid
experiment automatically. A different claim needs its own appropriate evidence.

## Fit into the existing learning loop

Choose the current delivery's concrete research question, inspect existing evidence and the ledger, then make
only an eligible necessary call. Keep raw results and the observation time in the existing evidence records.
Market opinions retain opportunity, comparables/status, evidence for and against, limitations, recommendation,
original relationship to the content, validation status and recorded cost under `market_evidence.py`.

`market_evidence_not_deciding` is informative: KNOWN/STALE/INVALID/UNKNOWN does not replace technical, source,
originality or audiovisual gates. No forecast changes a review score. The current publication can continue on
already-valid evidence; a scheduled research routine is not a new publication prerequisite.

Use available plugin skills for the question: channel audit, retention/new-upload review, packaging, comment
insights, relevant trend/idea research or job recovery. Installed skills do not establish account access or free
capacity. Run them within the existing supervisor and ledger, not a new scheduler. No standing weekly call count
requires spending. The daily learning loop changes one evidence-supported attribute at a time under SYSTEM.

## vidIQ Studio extension (2026-11-03 audit)

Read-only walk through the toolbar on `studio.youtube.com/video/qENUe7ZAu6k/edit` (a scheduled Short), executed
by Claude through Desktop Commander on the owner's PC. Nothing was saved, applied or generated; the one accidental
dirty state (opening the schedule picker enables Salvar) was reverted with "Desfazer alterações". The account is
on vidIQ's free tier: the AI panel says "You're out of credits" and every suggestion list is blurred behind
"Upgrade". Reading the screen costs vidIQ nothing but costs Claude tokens per screenshot, so use it sparingly.

| Tool | What it shows | Cost | Useful? |
|---|---|---|---|
| IQ (Optimize Score) | Overall 85; Title 84, Description 100, Tags 80. "Scheduled Post Time / best time to publish" row is locked | Free score; best time is paid | Low: heuristic SEO score, not validated (see the failed keyword validation above) |
| Analytics bars (Pre-publish forecast) | 14-day view range from 71,764 similar Shorts: 52-1,266 (typical ~240, performs well ~1.3K, breakout ~3.8K); tip 1 free ("opening 9 s static, add motion"), tips 2-3 locked. Also a sidebar Forecast card (typical ~224) | Free range and tip 1; the rest paid | Medium: a free pre-publish sanity band and a retention hint, a modelled estimate only |
| T (Title) | Title score plus AI title suggestions | Free quota exhausted (resets in about 13 h); more is paid | Low: the connector's `vidiq_score_title` / `vidiq_generate_titles` already cover it |
| Description | Score 100 plus AI suggestions | Same quota; paid | Low |
| Tag icon | Per-tag keyword score on our own tags (bible stories 72, bible story 70, noah 65, christian shorts 62, noahs ark 59, waiting on god 58, genesis 8 57, kjv bible 28) and 3 free suggested tags (kids bible stories 56, bible stories for kids 56, minno bible stories 55) | Own-tag scores free; 50 more suggestions paid | Low to medium: free but the scores are unvalidated; "kjv bible" is the weakest tag |
| Clock (Schedule Post) | Opens YouTube's own schedule picker; the vidIQ "optimal times to publish" chart under it is blurred | Paid ("Upgrade Now") | None on this plan: the channel-specific best time is NOT available free |
| Sparkle (AI) | "Out of credits" wall listing title, description, thumbnail, tags and best-time features | Credits | None; never spend |
| Flask (A/B Testing) | Tooltip only; no panel opened on a scheduled Short (likely long-form or published videos only, or paid) | Unknown | Unverified; do not rely on it |
| Gear | "Description suggestion preferences" form (topic, target keyword, emotion) that feeds the AI description generator | Settings for a paid feature | None |
| Preview Thumbnail | Mock YouTube home feed with our thumbnail and title among trending videos; the view counts are decorative | Free | Low for Shorts (auto-frame thumbnails); useful for the long-form thumbnail |
| Top mini-stats widget | Three unlabelled counters (156 / 66 / 978) and a live video view count | Free | Not interpreted; do not use as evidence |

What is new versus the connector (`vidiq_*` tools): the pre-publish forecast band and the free opening-motion tip
(the connector scores titles/thumbnails and reads published performance, it does not forecast an unpublished
video). Everything else duplicates the connector or sits behind a paywall. Best posting time, competitor tags and
A/B experiments are not free here.

### Recommendations (ranked)

1. **Use YouTube's native Test & Compare for long-form thumbnails and titles (free), not the vidIQ flask.** The
   flask showed no panel; Studio's own test uses real impressions and chooses by watch time share. Inteligência Viva
   queues one single-attribute test per long (SYSTEM's one change at a time) and reads the Studio result into the
   learning loop instead of any vidIQ score.
2. **Get the posting time from Analytics "When your viewers are on YouTube", not from vidIQ.** It is free and
   channel-specific, and the vidIQ clock is locked. A weekly Studio Analytics screenshot read (one crop, about one
   image) goes to Inteligência Viva to adjust `slots_utc` in `live-plan.json` (now 05:30, 13:30, 18:30, 23:30),
   moving at most one slot per week and logging the before/after view data.
3. **Read the pre-publish forecast on each scheduled Short, once, as a retention check.** Production applies the
   free tip (the 0.3-9.5 s static portrait should get slow motion) to the Keeper and bridge Shorts when the frame
   is still before publication; log the forecast band beside the real 14-day views to see whether the model is
   calibrated before trusting it. Drop the "kjv bible" tag (score 28) when tags are next edited, and do not
   spend credits on any panel above.
