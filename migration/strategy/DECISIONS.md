# HeroVerse: current decisions

`../SYSTEM.md` is the single operating contract. This page records current generic policy only; execution and the
next concrete action live in `../evidence/handoff/CURRENT.md`. Historical decisions remain in Git history and their
original evidence. This page is not a historical task queue or a second production ledger.

## Current policy

- Deliver the English KJV Bible series in story order: Short09, Short10, Short11, then the next planned Short and
  the existing arc-01 long. Preserve valid construction and original accepted audio where it is reachable.
- Owner, 2026-10-31 ("faça o que for mais entregue o que eu pedi.. como vai fazer voce escolhe.. só não mexe nas do
  pavo"): the accepted Short09 master exists only in a prior executor's private package and its review route is
  closed, so Short09 is rebuilt through the repository's own episode route from sources the repository, its releases
  and workflows can reach. The plan's structure, voices and timing are kept; unreachable accepted audio is regenerated
  only on the same pinned Kokoro voices and settings. Existing Pavo clips are never regenerated, recut in content or
  replaced; they are used as stored (release asset or saved provider ID read by GET). New visuals other than the hook,
  speaking characters and the Keeper's close are animated FLUX stills or licensed footage, each with a second option.
- Owner, 2026-11-03 ("eu autorizo você fazer tudo pelo meu PC"): a Studio runner on the owner's PC
  (`C:\HeroVerse\studio-runner`, own Chrome profile, Playwright, `integrations/studio-local/`) does Studio tasks the Data API
  cannot, starting with each Short's Related video. The cloud only writes jobs (`channel/studio_jobs.json`, built by
  `channel/related_map.py`); the runner reads them from origin/main, acts one video at a time (at most 30 a run), verifies
  after reload and returns receipts as data-only PRs (`evidence/studio/`). Invoked on demand only: no scheduled task, service
  or startup entry on the PC (the owner may add a schedule himself). Cookies stay on the PC; the owner signs in once with
  `runner.py login`. The owner's everyday Chrome is never touched.
- Build within the 9.5 quality parameters before final review. Review the actual complete audio/video, retain
  grounded defects and require overall ≥9.5 before a new upload. Never manufacture scores or approvals.
- Bible Shorts use the existing episode route and `publish-episode.yml`. Longs use their existing build/handoff and
  `approve.yml` → `prepublish_gate.py` → `publish.yml`. An upload completes only after public/processed readback.
- Native Gemini audio/video review for Short09 is authorized by the owner. Record the real model, exact file and
  sampling/coverage. Actual session reviews likewise identify the performer and what was heard and seen.
- Pavo is first for the hook and speaking Keeper/characters when its zero-cost and media checks qualify.
  The authorized silent Keeper Plan B retains the original narration and requires its own still-mouth evidence.
- Appropriate other visuals may use licensed/public-domain footage and GPT-generated stills with cinematic
  motion. Retain truthful rights/provenance and distinguish camera motion from acted motion.
- No new spending or paid fallback. Use current cost/capacity evidence and existing ledgers; reconcile uncertain
  provider jobs instead of repeating them.
- Owner, 2026-10-31 (Buzzy track): to get flow, a Short may be produced as a whole by Buzzy (prepaid annual
  plan, its cheapest adequate model, credits managed to last the year), with Pavo only for the hook and the
  Keeper's close. The owner set the 9.5 floor for image-only videos; for this Buzzy track the bar is "coherent,
  a minimum of appearance and a good layer of originality". Concretely: our own KJV script, narration, Keeper
  commentary and captions are the originality layer (never Buzzy's agent rewriting the script); hard refusals stay
  (KJV text exact, God never shown as a figure, nothing modern, no on-screen AI text or watermark, AI disclosure,
  technical/loudness checks); the audiovisual review floor for this track is 8.0 overall with every item >= 7.
  The 9.5 floor and the frozen QA stay unchanged for the existing image/Pavo track and for longs.
- Owner, 2026-10-31 (correction): Pavo generates VIDEO only for the hook, character-specific spoken lines and the
  Keeper's closing lines, nothing else; plus the one exception the owner named: the episode's THUMBNAIL image may
  be made in Pavo, built from the mined package rules (character close-up, emotion, few words) to be striking and
  irresistible. No other Pavo images (scene stills, probes) and no Pavo video elsewhere: its quota is kept for
  those. Every other visual is an image not generated in Pavo: public images (`public_sources.py`) first, then
  Buzzy's lowest-credit image model as support, then FLUX when available.
- Owner, 2026-10-31: Pavo is the main video source ("temos o pavo como principal"). Buzzy (annual plan already
  paid, connected as the claude.ai connector `https://mcp.buzzy.now/mcp`) is support only, when Pavo, FLUX
  stills and licensed footage cannot cover a shot, and always with the lowest-credit model that meets the shot
  ("utilize no modelo de menor gasto"). Read the balance before and after each generation, record model, credits
  and purpose in `evidence/buzzy/ledger.json`, and never buy credits or upgrade. Not new spending: prepaid credits.
- Keep the shared executor lease, heartbeat, durable requests and current supervisors. Do not add a scheduler,
  parallel ledger or generic approval system to continue an existing delivery.
- Restore two daily Shorts only when completed masters sustain it; preserve the long and the existing reserve
  target. Re-anchor missed dates to actual qualifications and readback. No count or revenue promise replaces quality.
- Ads and the digital product remain on hold.

## Evidence-led changes

Keep measurements in the existing evidence/learning records with their source, observation time, comparison age
and limits. A sparse sample is inconclusive. A strategic change needs the existing high-confidence evidence
standard; change one supported attribute and measure its result. Proven defects and policy failures are fixed
immediately without waiting for an audience experiment. Frozen criteria are not edited to improve a result.

Update the relevant current guide when a valid owner decision changes behavior. Remove the superseded instruction
instead of appending its contradiction. Keep receipts, source approvals, revocations, QA and idempotency history;
a record is not obsolete merely because it is old.

## Buzzy track: defect-finder review and the posting flow (owner, 2026-11-01; E250)

Owner: "já tem vídeo pra publicar.. tem uma meta.. e tem que ser atingida". His bar for a Buzzy video is "algo
coerente... um mínimo de aparência e uma camada de originalidade boa". The owner approved this final design: for a
plan/record with `"track": "buzzy"` the Gemini native review is a defect finder (eyes and ears only; its prompt drops
the 9.5 floor and score anchors and lists, with timecodes and a category, only: [a] speech cut off mid-word or
mid-sentence; [b] a scene that does not match its line or breaks story order; [c] audio errors; [d] captions out of
sync or unreadable; [e] policy problems; [f] broken or glitched clips; mild AI artifacts are `[info]`; it still returns
the rubric scores, as information). Publication does not gate on scores: `publish_episode.review_problems` requires the
same file sha, a designated reviewer, an issues list, `review.publish_decision` = `publish` by
`claude-session-reviewer` with a note, and `review.defects` classifying every issue; an unresolved [a], [b] or [e]
defect is refused. The Buzzy-shot ledger check, policy and frozen QA are unchanged. The image/Pavo track and every long
keep the 9.5 prompt and floor.

Hard limits of the flow, in the owner's words: "o que não pode é ter fala cortada sem sentido ou o vídeo sem
sentido.. tem que estar bom!" (1) no line of speech cut off mid-word or mid-sentence; (2) every scene makes sense
with the line it carries, in story order. They are the only reasons for the single fix round.

His posting flow, in his words: "precisamos de fluxo de postagem.. não precisa ficar nesse preciosismo.. faz algo bom
e sem papagaiada.. as duas ferramentas fazem vídeos bons já.. só edita.. deixa coerente.. camada de originalidade é
autenticidade e posta." Operating flow for every Short:

1. KJV script and plan.
2. Buzzy clips on the cheapest model at >= 720p, plus Pavo for the hook and the Keeper close (exact 0-credit quote).
3. One edit with `episode.yml`.
4. One Gemini native review, used only to catch defects against the buzzy floor; no regeneration loops.
5. Publish at the next slot.

At most one fix round, and only for a real defect (a broken clip, an audio error, a policy problem). No rework for
cosmetic AI artifacts.

Pacing rule (owner, 2026-11-01): "Referente ao ritmo você mesmo acelera ou desacelera o vídeo criado mediante cada
cena.. não precisa ficar fazendo e refazendo.. trabalha com o que tem.. não quero retrabalho.. faça bem os prompts e
vamos pra cima." A clip too long or too short for its line is retimed in the edit or trimmed, never regenerated;
quality effort goes into writing good prompts the first time. Existing support: `short_engine.speed` slows a clip up
to `MAX_SLOW` 1.3x to fill its span (never loops), a shot may carry an explicit `speed` (1.0-1.3, `explicit_speed`),
`src_start` trims the clip's start, `hold` freezes a talking clip's last frame (<= `HOLD_MAX` 1.3 s). Speeding a clip
up beyond 1.0 is done by trimming (`src_start`/shorter span); a 0.75x-1.5x speed-up range is not built.

## 2026-11-01 — Strategy reset: Shorts, longs and TikTok toward YPP, on automatic

Owner, 2026-11-01: "Resolva o que falta e já refaça a estratégia de longos e shorts e TIKTOK para alcançar a meta e
deixa lá no automático."

Measured on 2026-11-01 (daily report 09:41 UTC):
- 300 / 1,000 subscribers;
- 27.9 / 4,000 public long watch hours;
- 2,447 Shorts views in 90 days.

The best recent Bible Shorts reached 157-532 views each, held 72-85% of their length on average and gained 2-8
subscribers each. The prayer longs averaged 2-9 minutes viewed per view and received no traffic from Shorts. At this
rate 4,000 hours by day 30 (16/11) is not reachable; the YPP hours window is 365 days, so it is a target to accumulate,
not a cliff. Subscribers come from Shorts volume and consistency. Hours come only from longs with long average view
duration.

**Shorts**
- The Buzzy posting flow (above) is the only Short route: one Bible story per Short, in canonical order (genesis-10,
  genesis-11, then the next arc).
- Cadence: 1 Short a day at 23:30 UTC, automated; 2 a day (13:30 too) once the measured token cost of one automated
  Short fits the weekly budget twice daily.
- Each Short's pinned comment and description point to its arc's long.

**Longs (redesigned)**
- A long is the "complete story" of an arc, assembled from that arc's already-published Shorts: their accepted masters
  in order, framed for 16:9 with a blurred fill, joined by short Keeper bridges and one chapter card per story.
  Nothing is regenerated. Target length is 15-30 minutes.
- A second, sleep-oriented edit of the same material runs about 60 minutes: slower pacing, no hook music, a calm Keeper
  intro. The prayer longs' 8-9 minute average views show this audience watches long calm content.
- The long reuses the Short track's defect-finder review (no cut speech, no incoherent scene, policy). It still
  publishes only through approve.yml -> prepublish_gate.py -> publish.yml.
- Changing the long review from the 9.5 score floor to that defect gate is owner-directed here and is implemented as
  its own code change with tests before the first compilation long.
- First compilation: arc-02 (Noah: genesis-06 to genesis-09, all public).

**TikTok**
- tiktok.yml already mirrors every public Short through Buffer's free channel (8 posts SENT); it stays automatic, with
  no new spending.

**Automation**
- The 4 old clocks are disabled.
- One daily production session (fresh session, cheaper model) runs the Short flow end to end for the next plan and
  publishes at 23:30 UTC. Gemini's Free Tier proof is read on the owner's PC through Desktop Commander. If the PC or a
  provider is unavailable, the session stops and tells the owner; it does not invent evidence.
- Longs are built when an arc's Shorts are all public.

## 2026-11-01 — Quality, authenticity, originality and critical insight remain pillars (Shorts and longs)

Owner, 2026-11-01: "A gente mudou um pouco, né? Mas a qualidade ainda precisa ser um pilar... tem que entrar aí a
questão da autenticidade, originalidade e crítica. Não pode esquecer disso de jeito nenhum, nem no longo e nem no
short." And for the long: "o longo vai ter hook novo... e o fechamento tem que ser novo também... narração, tudo lá no
pavo... gerado pronto para só conectar no final e conectar no início... por isso que eu quero a mineração, para saber
como que vai ser o melhor início."

Every Short and every long carries the Keeper's own layer: an interpretive or critical insight (why the story matters,
what readers miss in the text, an honest question), stated as commentary and kept distinct from KJV scripture. A
script whose hook and close only summarize the passage is not ready.

A compilation long gets its own new hook and new close: Keeper Pavo video (exact 0-credit quote), made for 16:9 and
splice-ready at head and tail. The hook follows the opening structure measured from winning long Bible-story videos
(vidIQ mining, logged). Joins must be clean (no cut speech, no pop, consistent loudness).

## 2026-11-01 — Compilation long: hook, close and quality layer (owner, via coordinator)

The arc-02 compilation (Shorts genesis-06 to genesis-09, Noah) gets a NEW Keeper hook and close written for the long,
spoken by the Keeper in Pavo clips (fresh exact 0-credit quote, our Kokoro line, 16:9, still beat at each end),
and its hook is written on the structure measured in `evidence/vidiq/20261101/compilation-hook-mining.json`
(question that puts the viewer in the story, the stakes, the promise and scope, one marked critical insight).
Authenticity, originality and critical insight are mandatory in the long and in the Shorts: the Keeper's voice adds an
interpretive layer (what people miss in the text, an honest question) in KJV-faithful commentary clearly marked apart
from scripture. The review track is the defect gate (E251), implemented as `compilation-qa-criteria-v1`.

## 2026-11-01 — Token economy: more Shorts with the same tokens

Measured: 71.1M tokens in the first ~19 h of the week (budget 239M = half of the 478M weekly cap), a projection of
~630M, which is over budget. Most of it came from the long-context coordinator session and its agents, not from Shorts.
The owner asked to sustain the whole week and post more Shorts without spending more tokens. The goal is unchanged.

- Shorts: 3 slots a day (13:30, 18:30, 23:30 UTC). The production routine (Sonnet, fresh session, 06:43 and 16:43 UTC)
  makes a batch of 2 Shorts per run. Plans, clip submission, the lease and one Free Tier proof (valid 1 h) are shared,
  so the fixed cost of a run is paid once for 2 Shorts. Up to 4 a day are produced against 3 slots, and the surplus
  builds runway. The quality pillars (Keeper's interpretive and critical layer, coherent edit, no cut speech) are
  unchanged.
- Longs: compilation of each completed arc, built by Actions (no tokens). 3 Shorts a day completes arcs faster, so
  there are more longs for the same tokens.
- Clocks:
  - the coordinator's 4-hourly clock is off;
  - the Haiku light clock runs every 3 h and wakes the coordinator only on a failure;
  - the analysis runs every 2 days;
  - the vidIQ mining runs weekly (Monday).
  GitHub Actions (heartbeat, reconcile, TikTok, links) carry the mechanical work at zero tokens.
- Coordinator: answers the owner and failures only, with no recurring work in the long-context session.

## 2026-11-01 — Resource plan: no tool runs out, quality at the peaks

The owner asked for a measured budget per tool, free tools first, no tool overloaded, video where it matters and
images animated cinematically elsewhere. Balances measured today:
- Buzzy: 41,994 credits (header, 14:10 UTC). Seedance 2.0 mini at 720p costs ~58 credits a clip (234 for 4 clips).
  The credits are treated as a finite stock.
- Pavo: 1,474 credits, 0 daily free. Used only with an exact 0-credit quote, unchanged.
- vidIQ: 3,179 credits (2,959 renewable, reset 2026-11-18).
- Cloudflare FLUX: ~44 free images a day through `scene-stills.yml`. It runs in Actions, so it costs no Claude tokens.

Per Short (3 a day):
- Peaks in video. The 3–4 key action moments (climax, the KJV line, the turn) are Buzzy image-to-video, Seedance mini
  720p. The cap is 240 credits a Short, so 3 Shorts a day use ≤720, which lasts ≥58 days (past the YPP window). The
  balance is read in the owner's browser before and after each batch and written to the Buzzy ledger, so the cost is
  measured, not estimated.
- Pavo for 1–2 shots: the hook and/or the Keeper's close (direction and voice), at a 0-credit quote only.
- Every other shot is a free still animated cinematically in the edit (push-in, pan, parallax, light), with no
  generation cost:
  - stills come first from FLUX in Actions;
  - the owner's PC tools (AI Studio image generation, ChatGPT desktop app) are used only for a hero still FLUX cannot
    make, because driving a desktop UI costs Claude tokens.
- No regeneration for cosmetic artifacts. Retime, trim or replace with an animated still.

Longs: compilations of the public Shorts (Actions, no generation), plus the new Pavo hook and close at a 0-credit quote.

Mining: weekly (Monday), thorough, at most 900 vidIQ credits a run, so the balance lasts to the 18/11 reset. It uses
the validated-structure rule (≥6 winners from ≥4 channels, weak contrasts). The channel's own Shorts and longs are
read free from YouTube analytics (goal-report). Its findings change the Short and long formats only with that
validated evidence, and the authenticity, originality and critical layer (the Keeper's interpretation) is never
traded away for reach.

## 2026-11-01 — Comment replies on YouTube and TikTok, without rework

Owner: every comment answered by reading what the person wrote and replying to that, so the person sees a direct
answer, not a generic one. The mechanics already exist and stay:
- YouTube: `comment-replies.yml` (heartbeat, 6 a day) queues new comments and posts the decided replies (20 a day).
- TikTok: the local runner on the owner's PC (`migration/integrations/tiktok-local`, text-only, no screenshots).
- Both pass the same gate (`reply_policy.py`).

The missing piece was the writer, which was the retired 4-hourly clock. From now on, each production run (twice a day)
writes the decisions for the comments still undecided:
- reply in the commenter's language, 1–2 sentences, answering their exact point;
- be honest when they question the scripture: KJV quoted word for word, scenes dramatized;
- quote a verse only through the checked `verse` field;
- SKIP spam, hate and provocation (never argue);
- deliver them in its own PR.
TikTok runs only while the runner reports LOGGED_IN; the owner logs in by hand once (`runner.py login`).

## 2026-11-01 — Long-first, Shorts cut from the long

Owner, 2026-11-01: "Faça os longos e do longo faça os cortes para os Shorts e vá postando a partir do longo. É muito
mais fácil cortar uma imagem que já está enquadrada para o longo para um Short do que o inverso (a tela quebra).
Depois da compilação atual do Noé, ao invés de fazer Shorts, faça os longos e, dos longos, faça alguns cortes
COERENTES para postar como Shorts."

- After the current Noah compilation, each story (or arc) is made as a 16:9 long of about 8–12 minutes: plan track
  `buzzy-long`, built by the existing episode route at 1920x1080 with burned 16:9 captions; the caption-free master
  and the sentence/shot timeline are kept, bound to the master's sha256.
- Every picture keeps its subject in the centre 9:16 column (PROMPT_GUIDE "Long-first"), so the cut does not break.
- The Shorts are coherent cuts of that long (`short_cuts.py`): each starts and ends between sentences (no cut speech),
  lasts 20–179 s, and is a unit (recommended: hook line → beat → KJV line or the Keeper's insight). Each cut is its
  own file with its own native defect review and the session reviewer's decision; it links its parent long.
- The long publishes through approve.yml → prepublish_gate.py → publish.yml on its own defect-gated track
  (buzzy-long-qa-criteria-v1: the owner's defect finder, not the 9.5 floor). The 9.5 story-long track, the Short
  route, the compilation and every frozen QA file are unchanged. Implemented in E259.

## 2026-11-01 — Buzzy must last a full year; Pavo carries the hook, the speech and the close

Owner: the Buzzy credits are a one-year stock, so 600 credits a long makes no sense. He asked for a viral hook, some
character lines and the close made in Pavo, and images for the rest. This entry supersedes the Buzzy numbers in the
"Resource plan" and "long-first" entries.

- Buzzy budget: 41,994 credits (measured 2026-11-01) over 365 days is ~115 a day. The ceiling is 100 a day on average
  (~36,500 a year), so ~5,000 stay in reserve.
- Per long-first long:
  - Pavo, at an exact 0-credit quote: the viral hook, the speaking-character lines, and the Keeper's close.
  - Images: every other shot is a FLUX still (free, in Actions) animated cinematically in the edit.
  - Buzzy: at most 2 clips (≤120 credits), and only for a non-speaking action peak that an animated still cannot carry.
    Zero is the default.
- Cuts (the Shorts) come from the long and cost no Buzzy credit.
- The ledger records the balance read before and after every Buzzy use. If the running average goes over 100 a day,
  the next longs use no Buzzy until it is back under.

## 2026-11-01 — Every long and every Short is built for emotion and virality, from the mining

Owner: the structure must be extremely viral, tied directly to the mining, with a lot of emotion in every long and
every Short. These rules apply the validated Short beat map (structures/bible-story-short.json, status validated) and
the long's mined opening (evidence/vidiq/20261101/compilation-hook-mining.json) to emotion, in every plan:

- Long opening (0–30 s): two stacked "What if…" questions put the viewer in the character's place, then the stakes,
  then the promise. No calm scene-setting and no title card.
- Each story chapter of a long, and each Short cut, follows the validated beat map:
  - cold open on the spoken conflict;
  - stake and an open question;
  - three escalation steps, each showing a felt human cost and ending on a small hook;
  - the climax;
  - the Keeper's honest, personal question. That question is the critical and authenticity layer.
- Emotion is planned, not hoped for:
  - Every escalation step has one close-up face still with a named emotion (fear, grief, awe, resolve, mercy), the
    face "centred in the frame".
  - Pavo lines carry a delivery direction (urgent, trembling, broken, defiant).
  - The music rises through the escalation and drops to near silence for one beat before the KJV climax line, then
    swells.
- Cuts: each Short cut holds one emotional peak (an escalation step into the climax, or the Keeper's question) and
  opens on its strongest line within the first 2 s.
- Honesty is unchanged: KJV quoted exactly, scenes dramatized, no fear-bait, no fabricated prophecy (three_stage
  critique).
- The weekly mining measures these emotional devices in winners against weak contrasts. A device changes only with
  validated evidence: ≥6 winners from ≥4 channels.

## 2026-11-01 — Stills: ChatGPT (owner's PC) replaces FLUX; fewer stills, animated cinematically

Owner: "Troca ele, acha outro. Não podemos depender dele" (Cloudflare FLUX). Another consumer used up the free
allocation (10,000 neurons) before the project made a single image (scene-stills run 41339130885, E260 detail cf4006).
His next instructions: "Usa o GPT como programa. Pavo não": Pavo stays for video only (the hook, the speaking lines and
the close), so its quota is never spent on stills. He also asked for fewer images, each animated very well, because
very short cuts would not work.

Still sources, in this order:
1. Primary: the ChatGPT image runner on the owner's PC (migration/integrations/chatgpt-local).
   - It generates 16:9 images with the approved character references and records each one.
   - Its own rules apply: one request at a time, 3 min between requests, 30 a day.
   - The owner signs in once with `runner.py login`.
   - The account risk noted in its README is the owner's, by his explicit request.
   - Candidates are approved by PR, like every still.
2. FLUX (scene-stills.yml), only as a bonus when it has allocation. It is never a dependency.
3. Buzzy images (about 6 credits each), last, inside the ≤100-a-day average.

Pacing: a 10-min long uses about 25–30 stills, and each still carries 15–20 s of cinematic animation:
- 2.5D depth parallax;
- eased push-in, pull-back, pan and tilt;
- atmosphere layers (dust, embers, mist, rain, water shimmer, light rays).
These are built in the edit at zero cost. No fast cutting.

## 2026-11-01 — Cinematic still animation: the move follows the need (owner)

The owner, on the long-first longs of few stills (about 25–30, each 15–20 s on screen, so the picture is not cut fast):
"it cannot be rigid; it has to animate according to need; make it really well". Every approved still had received the
same centred push-in. Decision (E261): `motion.py`'s cinematic engine directs each still from its beat, the prompt's
emotion, its spoken span and the picture (face, saliency, Depth Anything V2 depth, sky, water, fire), with keyframed,
eased moves (push, pull, pans, tilts, a pan that lands on a face, drift, 2.5D parallax, a hold before the KJV line) and
procedural atmosphere, never the same move twice in a row, the subject inside the centre 9:16 band for the Short cuts,
bit-exact, at zero cost on the Actions CPU. A plan may override the move and atmosphere per shot; the chosen move and its
reason are recorded for the reviewer. The Short route keeps its push-in. The watched long remains the judge.

## 2026-11-01 — Mining scope: viral structures from any niche, adapted to ours

Owner: viral, consistent structures are not limited to our niche, because structure is general. The daily intelligence
mines them across niches and adapts them to the KJV Bible story. This extends the 2026-11-01 "Daily intelligence"
mining; it replaces nothing and keeps the same daily vidIQ budget (≤150 credits) and the same validation rule.

- Two pools, labelled in the evidence:
  - in-niche: KJV / Bible-story longs and Shorts;
  - cross-niche: the top outliers of storytelling, documentary, history, true-story and emotional narrative channels.
  Each pool keeps its own counts.
- From cross-niche winners, mine only the structure. Their topic, wording and visuals are never copied. The
  structure covers:
  - hook type in the first 2 s / 30 s;
  - open loops and payoffs;
  - escalation rhythm;
  - pattern interrupts;
  - emotional peaks and their devices;
  - ending/loop and CTA;
  - title/thumbnail promise and the payoff that matches it.
- A cross-niche structure becomes a rule only when:
  - it is validated in its own pool (≥6 winners from ≥4 channels, no channel above 1/3, breakout ≥50, ≥6 weak
    contrasts);
  - it is adapted to our format without breaking the pillars: exact KJV, the Keeper's critical layer, honesty, no
    fear-bait;
  - it wins as a labelled one-day test in our own data (daily intelligence).
  Until then it is a test, never a rule.
- One source of truth: findings go into structures/ and the "Daily intelligence" entries only, so there are never two
  conflicting instructions.

## 2026-11-02 — Inteligência Viva governs; deadline; automation, tokens and model routing (owner)

The owner decided:
- Goal: YPP (1,000 subscribers + 4,000 public long watch hours), target by 2026-11-15, maximum 2026-12-01. No other
  agent may change this deadline.
- The daily mining is renamed **Inteligência Viva**. Every day it builds a data-driven strategy toward the deadline:
  binding constraint, weakest factor, ranked levers with success/kill thresholds, and a review of yesterday's tests.
  It writes `migration/strategy/live-plan.json`. Production executes that plan automatically and reports any
  action it could not apply, with the reason. Volume is one lever, not the strategy.
- Everything is automated. A long in progress never waits for a schedule: the light clock fires the production
  routine to continue when a stage finishes.
- Token economy, measured with `migration/ops/token_budget.py`:
  - Inteligência Viva reads the budget and fits the day's quantities inside it.
  - Every run checks the budget before heavy work.
- Heavy work goes to free external compute first, when it gives the same quality. In order:
  1. GitHub Actions workflows: build, render, review, publish;
  2. the owner's PC: the ChatGPT app for stills, the local scripts;
  3. free-tier APIs: Gemini native review;
  4. the existing provider quotas: Pavo only at a 0-credit quote, Buzzy within ≤100 a day.
  Claude tokens are spent on judgment, not on compute or polling.
- Model routing, the cheapest model that keeps quality for the action:
  - Haiku: mechanical checks, clocks, status reads;
  - Sonnet: production, cuts, comments, Inteligência Viva, reviews;
  - Opus: only coordination decisions and hard diagnosis that need it, kept short.
  Sub-agents are given the model that fits their task.
- No rework, and no drop in quality. Valid work is reused, and a defect is fixed at the stage responsible for it.

## 2026-11-02 — Parallel distribution through our own channels, done the right way (owner)

Goal: more qualified viewers on the longs, which means watch hours and subscribers, without spam risk and at zero
Claude tokens per post.
- Own channels only, automated, and posted after each video is public:
  - Telegram channel: a bot posts through the free Bot API from a GitHub Actions step. The secret
    `TELEGRAM_BOT_TOKEN` is created by the owner; agents never see it.
  - Facebook Page Reels and Pinterest: through the existing Buffer free mirror, which may reuse an already-public
    YouTube Short.
  - WhatsApp Channel: no official posting API. It runs as a daily batch on the owner's PC through the desktop app;
    a challenge or login stops it, as with every other tool.
- The post text is built from a template with no LLM: the exact KJV verse, the Keeper's line from the approved
  script, the YouTube link, and one honest question. Every post is in English and has no clickbait.
- Third-party groups get no automation and no link blasts. Posts go only where self-promotion is allowed, written
  value-first, and posted manually from a prepared text. Church and ministry partnerships are preferred.
- Measurement: Inteligência Viva reads the YouTube external traffic sources and their average view duration.
  It keeps a source that brings watch time and subscribers, and drops one that brings empty clicks.
- A paid community (membership or a paid channel) is considered only after there is a proven, engaged audience,
  and on the owner's decision.

## 2026-11-02 — Inteligência Viva

Measured: 300 subs (+2.7/day, 7 d); public long hours 27.9 (own estimate; +~2.1/day, estimate); 385 long views in total,
average ~4.3 min per view (estimate). Needed for 11-15: 54 subs/day and 306 h/day; for 12-01: 24 subs/day and 137 h/day.
Hours bind. Neither date is reachable at the current pace; the deadline is unchanged.
Weakest factor: long impressions (~600 per long); Shorts sent 0 views to longs.
Market (vidIQ, in-niche, 11-02): small channels reach 20-57K views with a 'Why...' title and the Genesis chapters; a
20-min Bible long got 35.5K views at 3.9K subs; Noah Shorts win with a paradox title. Cross-niche: no valid data today.
Strategy (live-plan.json): (1) demand-backed 15-20 min long, (2) Short -> long funnel, (3) title/thumbnail A/B,
(4) 1 Short a day. flood-ends-long publishes at the first 13:30/23:30 UTC after the gate (preferred 13:30; low confidence).
No structure was validated. vidIQ: 45 credits (10 wasted on off-topic queries), 25 more pending a video_watch job.

## 2026-11-02 — Inteligência Viva (second run)

Measured: unchanged since the first run (subs 300/1,000; long hours 27.9/4,000 own estimate; hours bind). No new daily report, no experiment readable yet. Cross-niche pool mined (8 emotional-narrative long winners, breakout 40-126): dominated by one cowboy-romance cluster, no weak contrasts, so NOT validated; only the title mechanic (emotional turn + withheld reveal) is carried as a title-B test. 2h+ lengths are not copied. vidIQ today: 80/150 credits. Strategy and deadline unchanged (live-plan.json).

## 2026-11-02 — Battle plan to YPP: clear moments, triggers and actions (coordinator, owner's order)

The binding constraint is long watch hours: 27.9 of 4,000 (estimated), +2.1 h/day. More of the same output cannot
close that gap. Hours scale with minutes watched per viewer and with sessions, so the plan uses levers that multiply
hours. Inteligência Viva evaluates each checkpoint every day in its entry and live-plan. Production executes the
actions. Nothing here loosens a gate or a pillar.

Levers, ranked by hours per unit of capacity:
1. **Long compilations from approved media (zero generation cost).** Arc marathons of 40–90 min built through the
   compilation track (E251): the full Noah story Genesis 5–9, then Creation→Fall→Cain, Abraham, and so on. One
   viewer session gives 20–60 min instead of 3–6, and they are the best end-screen target for every Short and long.
2. **One new long per story, 15–20 min**, packaged as a question (live-plan A/B). It feeds the next compilation.
3. **Funnel everything into the longest video:**
   - every Short, cut, pinned comment, end screen and playlist points to the newest compilation or long;
   - every long ends on the next long;
   - one series playlist per arc.
4. **External qualified traffic**: own Facebook Page (Reels and the long), Telegram and WhatsApp channels, and
   value-first posts in groups that allow it. This is measured by external-source watch time.
5. **Packaging refresh of every under-performing video**: title and thumbnail only, never the accepted media.

Moments (UTC). Each has a trigger and an action.
- **M1 — 2026-11-02/03:**
  - flood-ends-long published at the live-plan slot;
  - 2 cuts plus 1 Short a day with funnel links;
  - Facebook Page receives the long.
  - Trigger: the long is not public by 11-03 23:30 → it is the only priority in the next production run.
- **M2 — 2026-11-04:** the first arc compilation, "The Complete Story of Noah (Genesis 5–9) KJV", 40–60 min, is
  built from the approved G06–G09 media, the Noah compilation and flood-ends-long, and published. Every live Short's
  pinned comment and related video then points to it.
- **M3 — 2026-11-05 checkpoint (48 h data):**
  - long CTR <2% → swap to title B or a new thumbnail;
  - average view duration <3 min → shorten the hook and move the strongest beat to the first 30 s;
  - long views from Shorts = 0 → move the funnel to end screens and playlist.
- **M4 — 2026-11-06 to 11-10:** one new story long a day (Genesis 11 onward), plus a second compilation (Creation →
  Cain) by 11-08. External distribution runs daily.
- **M5 — 2026-11-10 checkpoint:**
  - project the date the hours are reached, from the measured 3-day hours per day;
  - if it lands after 12-01, scale whichever lever measured the most hours per capacity unit (compilations,
    lengths or distribution) and drop the weakest.
- **M6 — 2026-11-15 and 2026-12-01:** deadline reviews, with honest measured numbers against the goal.

Each Inteligência Viva entry reports: the current moment, its triggers (hit or not), and the action taken.

### Pavo: generate, compare, use the best — never discard and regenerate (owner, 2026-11-02)
- The owner's finding: Pavo clips are almost always good and already meet our standard. Producing a clip and not
  using it is waste.
- Each talking line gets at most 2 generations, in 1 round (E264). Claude compares the generated clips side by side
  and approves the best one by real review (approve-shot). Selection replaces regeneration.
- A minor imperfection (a small lip offset, a pause, a frame) is fixed in the EDIT and the montage: trim, hold, speed,
  cut point, B-roll over the weak part. It is never regenerated.
- The still-motion voice-over fallback applies only when NO clip is usable. Usable means the wrong audio or line, no
  face, a broken render, or a policy problem.
- Nothing here loosens a gate. Review and the native review stay; the change is choose-and-edit instead of
  regenerate.
- Inteligência Viva and production plan to avoid rework: every generation planned must be one that gets used.

### YouTube bonus programs and Shorts cadence (owner, 2026-11-02)
- Bonuses are separate from the plan and change nothing in it. The plan stays focused on the YPP goal and the
  deadline.
- Join a YouTube bonus or program from inside Studio the day it appears. The first one is the Shorts bonus: 16 Shorts
  a month, join by 11-15. On 11-02 it was not yet shown for HeroVerse in Studio.
- Inteligência Viva only watches for these offers and reports them.
- Shorts cadence (owner rule): **4 Shorts a day**:
  - 2–3 story Shorts: cuts from the long, or a bridge when no cut exists;
  - plus 1 **Keeper reflection** Short in split screen, about 30 s: the long's moment plays in the top half and the
    Keeper's reflection is in the bottom half.
  - Keeper reflection bottom half = Pavo talking Keeper, 2–4 clips, owner rule (the reflection is cut at sentence
    edges into 2–4 segments, each with its own approved Pavo talking clip, joined with short crossfades; never a
    still motion; the top half keeps the long's clip). The lip-sync and audio-match flags are informative for a talking
    clip; only a hard defect (wrong words, no face, a broken render, a policy problem) excludes it (E266).
  Slots are chosen by Inteligência Viva; the count is fixed by the owner.

### Never stop: automation and fallback ladder (owner, 2026-11-02)
- **Who moves it:**
  - Inteligência Viva (05:17) plans.
  - Production (06:43 and 16:43) executes.
  - The light clock (every 3 h) continues: it fires production when a run has ended and the long or a failure is
    pending, and it merges green data-only PRs.
  - No step waits for the coordinator or the owner.
- **Short buffer:** keep at least 2 days of Shorts scheduled ahead on YouTube, using cuts first and bridge Shorts
  second. A day without a Short can then happen only if production is down for more than 48 h.
- **Fallback ladder:** when a source fails, take the next step instead of stopping. The quality bar stays the same.
  - stills: ChatGPT app → close, wait 5 min, reopen (×3) → FLUX → Buzzy image within ≤100/day;
  - Keeper speaking line: Pavo talking Keeper → Keeper voice-over on reviewed still motion of an approved Keeper
    still (no Pavo needed);
  - hook: Pavo → the strongest approved still with motion and the hook line;
  - a long blocked >24 h at one stage → publish cuts and a compilation from approved media meanwhile, so hours and
    Shorts keep flowing;
  - PC offline → everything that needs no PC goes on: cuts, compilations, publishing, comments, packaging.
- **Each failure** gets a root cause and an antidote in ERRORS.json, so the same stop cannot happen twice.
2026-11-02 owner: native review provider = local ASR + AV measures + Claude visual review; Gemini dropped as required provider

## 2026-11-02 — flood-ends-long: Pavo talking video for the Keeper lines (owner order)

Owner: the Keeper lines (k-insight, k-bow, k-close), the hook and any character line use Pavo talking video; the owner
watched the clips and judges the lip sync perfect, so the automatic lip-sync / audio-match flags are not a reason to
drop a clip. Only a truly broken clip (wrong words, no face, broken render) is excluded.
Executor 2026-11-02: the older generations (runs 41423359803, 41436544195) kept no bytes in their artifacts and had
FACE_NOT_FOUND from the full-body framing; new chest-up generations (shot-probe 41534197400, 2 for k-bow, 1 each for
the others) are recorded in `evidence/shots/flood-ends-long/`. k-insight and k-close came back with no flags and were
reviewed by frames (approvable). k-bow: both generations carry only AUDIO_NOT_OUR_LINE (needs the pinned-ASR
speech-check). Not swapped into `shots/flood-ends-long.json` yet: the Pavo sources would make `episode_preflight`
report PROBE_REQUIRED (needs >= 6 direct generations a line) against the E264 cap of 2, and the current fallback
approvals keep the preflight passing. Pending owner decision: let an approved clean probed clip satisfy the probe rule.
Executor 2026-11-02 (E271): applied by the rule above. A shot whose clip is approved (approve-shot, bound to the request
digest and clip sha256) owes no probe and no rate in `episode_preflight`; a shot with no approved clip keeps PROBE_REQUIRED
under the E264 cap. k-insight and k-close are approved on the chest-up Pavo clips (frames viewed, no flags). k-bow: the pinned
medium.en speech-check heard neither generation say the line (SPEECH_WORDS_NOT_EXACT: garbled and dropped words), so it is
a hard SHOT_WORDS_NOT_OUR_LINE and keeps the approved Kokoro voice-over on still motion; no third generation (E264). The long's
compose has no per-shot transition setting (crossfade_seconds 0.0), so the Pavo clips join by cut.
Executor 2026-11-02 (E272, owner order for flood-ends-long): the HOOK, the speaking lines and the Keeper lines are Pavo talking
video, joined to their neighbours by a short picture crossfade, never a hard jump. `plan_check.keeper_hook` lets a long-first
(16:9) plan open on a talking Keeper hook (first shot only; every other Keeper rule is unchanged). The long's compose
(`episode_build.LONG_XFADE` 0.3 s, `short_engine.transitions`) blends the picture into and out of each talking shot inside the
silence next to his words, so no word is cut, faded or overlapped; the Shorts keep cuts only (hookify block-shorts-fade-wipe).
God's voice (s-voice) stays a scene: God is never shown with a face, and Genesis 8-9 has no other on-screen speaker.

## 2026-11-03 — Inteligência Viva (extra run, owner request)
- Moment M2 (Noah compilation due 11-04); M1 closing as flood-ends-long goes public. No trigger fired. Goal numbers carried over from 11-02 (subs 301 measured; long hours 27.9 estimated; hours bind). No vidIQ credits used.
- live-plan: 4 Shorts/day (2-3 cuts or bridges + 1 Keeper reflection v2), slots 05:30/13:30/18:30/23:30 UTC (05:30 and 18:30 are unmeasured exploration), next long Genesis 10-11 (script runway 0), compilation 11-04.

## 2026-11-03 — flood-ends-long: the held version is released as it is (owner order)

Owner, 2026-11-03: "Pode soltar aquele longo… faça os recortes… a partir de agora não erre mais." On 2026-11-03 the owner released
the held version as is: pilot-017 (YouTube 1m-NUJhkdMY, approved by approve.yml run 41521201681 and uploaded by publish.yml run
41524618475, unscheduled by channel-privacy run 41536206003) goes public without waiting for the Pavo-talking rebuild. It is removed
from `channel/hold-plan.json` (the prayer-long hold stays). Route: `channel-privacy.yml` mode `release` (`release-plan.json`),
which uploads nothing and approves nothing: it refuses unless the video is still the ledger's upload of the pilot's exact file,
is out of the hold plan and `publication_binding.py` still passes; it reads the status back and records the release in the ledger.
publish.yml cannot do it: a resumed upload never changes privacy. The rebuild with Pavo clips (E271/E272) stays a separate,
later version and does not block this one. The cuts (Shorts) follow once it is public.

Executor 2026-11-03 (E275, flood-ends-long cuts): the owner-released long 1m-NUJhkdMY is public (channel-privacy release run 41558453690). Three
cuts (dove 66 s, rainbow 73 s, door 40 s) were rendered by short-cuts.yml and each reviewed by local-review.yml on its own sha256. A first dove
cut was refused before publish: it began 0.1 s before the first word, under the 0.25 s fade-in; the cut was re-made 0.25 s clear of speech and
`short_cuts.check` now refuses `CUT_FADE_OVERLAPS_SPEECH`. The first door cut opened on nine seconds of a dark still, so it was re-made to open on
the Keeper's lit "Most miss this" line. Both earlier masters stay on record (evidence branches) and were never published.

## 2026-11-03 — Inteligência Viva
- Moment M1 closing, M2 due 11-04. Trigger "long not public by 11-03 23:30": not hit (flood-ends-long public since 01:15Z, measured via vidIQ; 1 view; duration 8:22, shorter than the 15-20 min planned).
- No new daily report (latest 11-02 18:48): goal numbers carried over (subs 301 measured; long hours 27.9 estimated; hours bind). Deadlines unchanged (11-15, max 12-01).
- Action: funnel links and Facebook post of the long today; Noah compilation is production's next build; later longs target 12-15 min. Experiments unread until the M3 checkpoint 11-05. vidIQ used: 5 credits.

## 2026-11-03 — Coordinator continuation (01:45 UTC): genesis-10 bridge Short, Noah compilation length, Keeper reflection v2
- Bridge Short genesis-10 (9:16): the ChatGPT desktop scripts take `-plan`, `-aspect`, `-branch`, `-run` (repo copy in
  `migration/integrations/chatgpt-local/desktop-app/`, flood defaults unchanged; 9:16 centre-crop to 1080x1920). 18 stills in
  the ONE chat "HeroVerse — stills", no usage-limit message, no restart needed; s-voice and s-ararat were re-made without the
  ark in the prompt (E122 needs reference images the desktop route cannot attach). All 18 approved, 17 scene shots approved as
  still-motion sources. Pavo talking Keeper (k-insight, k-close): 4 generations, all `AUDIO_NOT_OUR_LINE` (E264), so both
  shots stay on the Keeper voice-over over reviewed still motion. Master 170.97 s, -14.5 LUFS; `local-review.yml` 41583119894;
  record written with the true basis (audio by transcript and measures, not by ear). Not published: the thumbnail
  (`THUMB_NOT_APPROVED`) needs a Noah close-up made with the approved references, and the owner rules forbid Pavo for stills.
- Noah compilation (M2) length: the public Genesis material (Shorts genesis-01..09 = 14.7 min, plus flood-ends-long 8.4 min) is
  23 min, below the 40 min marathon line. No padding and no inflated title: ship "The Complete Story of Noah (Genesis 5-9) KJV"
  at its true length (about 19 min: Shorts genesis-06..09, flood-ends-long, a new Keeper hook and close). `compilation_long.py`
  now accepts a public 16:9 long as a chapter (PR #695, test `test_a_public_long_is_a_chapter`). Not built yet: the new Pavo
  hook and close (2 generations each, best used) and the plan file.
- Keeper reflection v2 #1 from flood-ends-long (`reflections/flood-ends-long-1.json`): three Pavo talking segments approved
  (k-r1 reworded after 2 flagged generations; k-r2 reworded for the 165 wpm pace gate; k-r3 as first approved). The first render
  heard the long's own voice under the Keeper and doubled the Keeper in the top half, so the top clip is now scenes only with the
  long's audio muted. The second master (sha256 f4553a09…) is not claimed at the 9.5 floor (one scene held ~16 s on top,
  audio not heard by ear, a recognizer repeat at "bow"/"carried"): no review, not published, evidence kept.
- E276: `test_gemini_short_review` counted cuts as corpus Shorts and turned every PR check red once the cuts were published.

## 2026-11-03 — Token budget: the hard lock lifted, allocations redistributed (owner order)

- Owner, 2026-11-03: "Pode tirar a trava de tokens. Só você distribuir melhor tudo." The Shorts allocation had blocked
  new work at 63.5M of 61.5M while clocks (1.1M of 43M) and reviews/PRs (7.7M of 52M) sat almost unused.
- `project_share` 0.5 → 0.9 of the calibrated weekly cap (478M): 430.2M. 10% stays free so the account's own weekly
  limit never stops the routines (a hit there would stop everything, which the owner's "never stop" rule forbids).
- Cadence for the plan now follows the battle plan: 7 longs/compilations and 28 Shorts (4/day) a week, 7 clock and 7
  mining runs, 10 PR cycles. Rebuilt with `token_budget.py plan --write`: long 83.3M, Shorts 147.2M, clocks 51.5M,
  reviews/PRs 62.1M, reserve 86.0M. The hook still enforces the total and each allocation; the coordinator re-balances
  again by PR if one activity runs dry while others sit idle.

## 2026-11-03 — genesis-10-short Pavo Keeper clips: pinned-ASR check (executor, Claude)

- Owner rule (Pavo lip sync "perfect", flags are not a reason to drop, at most 2 generations a line, never regenerate)
  applied to the 4 clips of shot-probe 41574608645. `episode_build.py speech-check` (medium.en, model.bin sha256 11b22077…,
  YAMNet, Keeper and Adam references) ran on each; sidecars are in `evidence/shots/genesis-10-short/speech/`.
- Words (strict, WER 0): k-insight g1 "Most missed this, was missed it. Noah saw dry ground and still God who waited. Was
  the God and still dopend it." (garbled); k-insight g2 "...the God who shut the door was the God who STILL opened it."
  (one inserted word in the middle, no trim can remove it); k-close g1 "...part 11 tomorrow, the living of the rainbow."
  and g2 "...part 11, Tau and Rainbow, but the rain, Viggo." (wrong). All four are SPEECH_WORDS_NOT_EXACT (and the voice
  cosine is within 0.02 of Adam's, VOICE_NOT_CONSISTENT). The flag was right on all four: nothing to approve, no trim fixes it.
  The Kokoro voice-over fallback (#710) stays for k-insight and k-close; no third generation (E264).
- AUDIO_NOT_OUR_LINE audit over every probe record (82 clips, 14 flagged): ASR measured on 9 of the 14: 1 exact (flood-ends
  k-hook g1, corr 0.687, approved with trim_out_s), 8 wrong words (corr up to 0.80); 5 never measured. The envelope
  correlation is therefore not shown to be a false-positive generator, and it cannot be the authority anyway: corr 0.769 and
  0.802 clips said the wrong words. The gate already makes the pinned ASR the authority (E266: `approve-shot` accepts the
  flag only with a sidecar whose words are exact for the same clip and trim). No gate or tolerance changed.

## 2026-11-03 — No repeated footage or speech between Shorts of one long (owner rule)

Owner, verbatim: "Não pode ter trechos repetidos nos shorts… esses recortes são recortes novos." No two Shorts of the same
long (cuts and Keeper reflection top clips) repeat footage or speech. Only the 0.25 s fade tail (silence in both) may be
shared. `short_cuts.check` refuses `CUT_OVERLAPS_ANOTHER`, `reflection_shorts.check` refuses `CLIP_OVERLAPS_ANOTHER` (E279).
flood-ends-long: reflection 1's top clip moves from 435.31-456.47 s (inside the rainbow cut) to the unused 44.88-66.08 s
("And God remembered Noah… Remembered"); altar (338.47 s) stays: door ends 338.64 s, door's last word ends 338.39 s and
altar's first word starts 338.74 s, so the shared 0.17 s is fade over silence, not repeated speech.

Reflection 1 re-render (run 41630141252, sha256 f36a801c6ba4bff8..., top clip 44.88-66.08 s, 21.2 s): not reviewed and not scheduled. The pinned
ASR (faster-whisper small.en, word timings, run locally on the exact master) hears extra speech after each Keeper line: "you mealy"
(5.84-6.26 s), a second "own bow" (11.02-11.42 s), "for carried" (16.74-17.74 s); volumedetect shows speech-level energy there (about -10 to
-14 dB), so these are in the clips' audio, not recognizer noise. The 9.5 audio claim stays pending. The fix belongs in the render (trim each
clip at its last required word), not in the gate. Also: the top still (the ark on the sea, 21 s) does not show the rainbow the lines name.

## 2026-11-03 — Pavo for the hook, the character lines and the Keeper; one prompt builder; daily lessons (owner order)

Owner, verbatim in substance: "You are not doing the HOOK in Pavo, nor the CHARACTERS' lines; only the Keeper at the end.
Do them in Pavo." "Pavo does EXACTLY what you tell it. The failure is the prompt's organization." "What Pavo generates
WILL be used. Organize it at EDIT time." "Learn every day, so there is no rework." (E290)
- Every new long-first long and bridge Short: the hook, each on-screen character line and every Keeper line are Pavo
  talking shots (`plan_check --strict`: HOOK_NOT_PAVO, CHARACTER_LINE_NOT_PAVO, KEEPER_LINE_NOT_PAVO). God is never
  shown: a hook that quotes God is said by the Keeper or a character. Published plans are grandfathered by id.
- Prompts come only from `pavo_prompt.build` in the owner's fixed order (PROMPT_GUIDE "Pavo talking-shot prompt
  standard"); our exact Kokoro line goes in with a 0.3 s silence pad; a Keeper line is checked for pace before any probe.
- Edit-time use (OPERATIONS "Editing rule"): trim, crossfade and retime fix a usable generation; TALK_ATTEMPTS stays 1.
- `strategy/pavo_lessons.md`: dated, evidence-linked lessons; production reads it, Inteligência Viva appends daily.

## 2026-11-03 — Pavo clips in full with Pavo's own audio; Kokoro only over the stills (owner order)

Owner, verbatim: "Quero com o áudio do pavo também.. quero o vídeo do pavo na íntegra. A narração feita vai ser pras imagens..
aproveitar tudo que o pavo pode oferecer dentro das capacidades." This reverses E287's default (our WAV over Pavo's picture).
- `pavo_audio` is a per-shot setting; `"pavo"` is the DEFAULT on every track (long compose, reflection, compilation, bridge
  Shorts). `"ours"` stays only as an explicit option and for approvals recorded under it (their digests do not move; the two
  compilation plans built before the order are grandfathered by id). Kokoro narration is only over still and scene shots.
- In full: the clip is the bytes Pavo returned; `trim_out_s` applies only when set explicitly. The E272 crossfade stays at
  the boundaries, picture only, never over speech. The audio is matched to the narration (integrated LUFS within +-1 dB, true
  peak under -1.5 dBTP).
- Checks: the visual gates stay (face, mouth sync against Pavo's own track, artifacts). `AUDIO_NOT_OUR_LINE` and
  `SPEECH_WORDS_NOT_EXACT` stop refusing a Pavo-audio shot; the ASR text is a review note. The KJV-exact pillar (CLAUDE.md,
  SYSTEM) keeps one exception: a direct KJV quotation whose heard words differ gets `WARN_KJV_WORDS` in the review notes and
  the reviewer decides (a warning, not an automatic refusal).
- Not a defect, so no ERRORS entry. A clip made under E287's default has only OUR audio kept (the raw track was dropped); the
  pre-remux probe assets (Pavo's track kept) are the only source of its own audio.

## 2026-11-03 — Flood reflection 1 held at 9.3; what the next reflection must have (coordinator)

Reflection 1 on our audio (three clips, master 08276e85, reflection-shorts run 41660551928, local-review 41661153948) was reviewed honestly at 9.3
(pacing 9.0: a 16.2 s held still; audio 9.0) and is NOT published; nothing below 9.5 is published and flood reflection 1 stops here. Rules:
- Every long's plan reserves one reflection top window of 20-30 s with 3 or more shots (no still held over ~8 s), outside the cuts' ranges
  (`long.reflection_window {start, end}`; long_plan_check warns REFLECTION_WINDOW_NOT_RESERVED for a long without one and refuses a malformed one, E291).
- Close the inter-clip silences of a reflection to 0.3 s at most.
- Re-measure sync after any retime.
- The reflection pace is judged after the render's own retime (`plan_check.reflection_retime`, E288); the stored clips are re-judged on our audio by `shot-remux.yml`.

## 2026-11-03 — M2 Keeper hook and close: one new generation per line, on the current template (coordinator, E292)

The two stored generations a line of arc-02-noah-compilation-keeper (probe 41629339290, hand-written prompt, 22- and 23-word lines) pass sync on our
audio (shot-remux 41670811661) but Pavo's OWN track says the wrong words (speech-check 41636192512: "Noah's Shading and Sip", "gut El Lassi"), and the
owner's order is Pavo's own audio, the clip in full. The fix is the prompt and the line, not our audio or a wrong-words publish:
- `episode_build.stored_generation_problems` (E292) still refuses a shot-probe of a line with stored generations, with one more exception: when
  EVERY stored generation was built with a prompt template older than `pavo_prompt.VERSION` (the record's `request.audio.tail_pad` carries the
  version of a standard talking shot; a hand-written prompt carries none), the line takes EXACTLY ONE new generation (`older_template_shots`,
  `generate_clips(max_generations=1)`: no second generation for a visual defect). One generation per template version after that.
- The two Keeper shots now carry `pavo` fields (prompt = `pavo_prompt.build`), lines shortened to 16 and 17 words as the Keeper's own wording, not KJV:
  hook "What if obeying God meant building a ship with no rain in sight? Here is Noah's whole story."; close "Noah obeyed before one drop fell. What is
  God asking of you, that you cannot yet see?". plan_check strict (E277 pace included) passes.
- The compilation uses the clips in full with their own audio (`pavo_audio` "pavo", #782); the ours-route remux approvals stay as evidence only.

## 2026-11-04 — Inteligência Viva
- Moment M2 (Noah compilation scheduled 16:00Z); M3 read 11-05. Triggers: none of M1/M2 hit; early M3 signal: the long has 5 views (measured, vidIQ) and Shorts send ~0 to longs, so the "views from Shorts = 0" rule is expected on 11-05.
- Goal (subs measured live 310; long hours 27.9 own estimate from the 11-03 report): gap 690 subs / 3,972 h; needs 62.7 subs and 361 h per day for 11-15, 25.6 and 147 for 12-01; pace ~2.9 subs/day (measured) and ~2 h/day (estimate). Hours bind.
- Action: compilation today; link it in the first description line and pinned comment of every Short; Babel long continues. vidIQ used 15 credits (3,084 before); 2 of the 3 calls (outliers) returned the same off-topic list whatever the query: do not repeat that call form, use the 11-02 form.

## 2026-11-04 — Owner's standing rule for Pavo talking lines: no per-line consultation (owner order, E296)
- Owner, in chat 2026-11-04 ~06:20Z: "Eu já te dei as regras.. não precisa ficar me consultando.. as regras são fixas."
  His fixed rules: Pavo speaks the hook, every character line and every Keeper line; "não existe esse negócio do clipe não
  passar… a questão é o prompt… sempre fazer o prompt modelado [no que passou]"; "Quero com o áudio do pavo também.. quero
  o vídeo do pavo na íntegra. A narração feita vai ser pras imagens"; quality ≥9.5, no rework, no spending.
- Codified in `migration/channel/owner_regen.json` `standing_rule` and `episode_build.standing_rule_verdict`: a talking line
  whose stored generations ALL failed on words, sync or NO_VIDEO takes ONE new generation per prompt revision, with
  `pavo_audio: "pavo"`, a changed `pavo_prompt.build` prompt (E293 template, modelled on the passing prompts) and a recorded
  `pavo_prompt.py lesson` naming the shot and the revision; at most 3 extra generations per line in all, inside the daily
  free Pavo quota (0 credits by exact quote). At the cap it stops and reports. A probe of a talking line whose plan says
  `pavo_audio: "ours"` is refused (the error that discarded Pavo's audio in probe 41743247133). Executors decide inside
  these rules and do not ask the owner per line.

## 2026-11-04 — Babel k-restrain becomes Keeper narration after the Pavo cap (coordinator, under the owner's fixed rules)
- The owner's standing rule (E296) gave k-restrain 3 extra Pavo generations, one per prompt revision; all failed (probe
  41795895378 garbled ending; 41800469765 repeated words and a dropped sentence; 41804402265 FACE_NOT_FOUND). At the cap
  the line stops. Coordinator decision (the owner said not to consult him): k-restrain is a normal narration beat in the
  Keeper's Kokoro voice over the existing approved still s-babble (the scattering moment), no new image and no new Pavo
  generation. The talking shot k-restrain is removed from `plans/genesis-10-11-long.json`; its line ("He said nothing would
  be restrained from them. So after water, He chose distance.") opens s-babble. b-tower keeps its approved clip.
- The long's voice preflight runs in Actions (`preflight.yml`: the existing `episode_build.py preflight --voice --refs
  --write` with the pinned Kokoro runtime), since no Kokoro is installed locally.

## 2026-11-04 — Use 100% of the weekly Claude cap, landing at the reset (owner)

Owner, 2026-11-04: "preciso que você analise aí e faça uma gestão para que a gente consiga utilizar os 100% bater no
dia lá que tem a renovação, na verdade no horário que tem a renovação... organiza aí entre os seus modelos".
- `token_budget.json` `project_share` 0.9 -> 0.97: 3% headroom so the account limit never stops the routines at the
  very end. The goal is ~100% exactly at the weekly reset (Saturday 19:00 UTC), never earlier: hitting the cap early
  stops every routine until the reset.
- `token_budget.py pace` compares the remaining budget with the hours to the reset and the real burn rate (last 6 h and
  24 h) and says AHEAD (the hour the budget would run out), ON_PACE or BEHIND (spare tokens), with a per-model split.
- Work is routed by model tier, and tier and optional work move with the pace verdict; see `../OPERATIONS.md`
  "Model routing and weekly pacing". Quality is never lowered to pace.
- `token_plan.json` was rebalanced for the rest of the week toward the Babel long and the next long, with a small reserve.

## 2026-11-04 — Viral structure mining (Inteligência Viva, owner order)

Owner, 2026-11-04: map the viral structure behind breakout videos and turn it into production specs. Full map, evidence table
with links and counts: `../structures/viral-structure-2026-11-04.md`; data and pool labels: `../evidence/vidiq/2026-11-04/`.
vidIQ 125 credits (3,069 -> 2,944; 140 of 150/day with the 15 earlier today; ledger updated). No manifold, no new generation.

What the evidence says (counts are over mapped videos; CTR/retention of other channels are not observable):
- "Monetized in 7-10 days": no verifiable case. The one with numbers used a 5-year-old account and its own transcript
  contradicts the title; the rest are course sellers or unreadable. Routes unchanged: 1,000 subs + 4,000 public long hours,
  or 1,000 subs + 10M public Shorts views in 90 days (Shorts-feed hours do not count). The 500-sub early-access tier is fan
  funding only. vidIQ reports the thresholds double on 2027-02-01 (not confirmed on YouTube's page).
- Breakout sample: 15 Bible videos (8 Shorts, 7 longs) from 15 channels, 7 cross-niche from 7, 21 weak contrasts. Inside the
  video the pattern is real but does not separate winners from weak (3/6 Bible long winners have no hook). The separators are the
  package and the length: "Full Story"/question title 5/6 vs label titles 6/7 of the weak; face + 1-3 word thumbnail 6/6;
  13:10-27:54 min 6/6 vs 5/7 weak under 10 min. Shorts winners open on stakes/question/event 4/4; 6/8 run <=90 s, while the
  10-26 audit had 5/6 at 170-179 s: length is not a proven driver.
- Route: the Shorts route needs ~370K views/day to land by 12-01 (we have 2,668 in 90 days): not reachable. Hours need 3,971 h:
  one breakout long (one FaYEXkK6RsA-class video, 397K views in 27 days, would exceed it) or session-length compilations (8,000
  views at 30 min = 4,000 h). The deadline stays 2026-11-15 target, 2026-12-01 max.

Rules for Inteligência Viva and production (none edits a frozen QA file or gate):
1. **Long hook** (first 60 s): a scene at its most dangerous moment or one identity-reversal sentence in 0-25 s, no stacked abstract
   "What if" questions; the title promise in one sentence by ~50 s; a "we must go back" return device when a cold open is used,
   closed within ~60 s; one forward hook by ~1:30 paid in the second half. The 11-01 hook rule was modelled on a 1,100-view video;
   superseded by this one.
2. **Long title**: a "Full Story"/"Complete Story" element OR a question OR "the most [superlative] ... in the Bible", with the
   protagonist in the first 40 characters; reference and "(KJV)" after the pipe; never a chapter label, "Part N", an episode number
   or "audio reading" as the title. Title the Creation-to-Cain compilation on the Adam and Eve demand (a question about why God
   sent them out + the Genesis 1-4 range).
3. **Long thumbnail**: one face or a pair at ~40% of the frame in strong emotion or action; at most 4 baked-in words (the name or
   the title question); one story object; high contrast; text complements the title. One attribute per Studio Test & Compare.
4. **Long length and cadence**: new story longs 13-20 min (floor 13:00), compilations 40-60 min; a turn or open loop at least every
   3 min and never a gap above 5 min; 2-3 marked insight lines per 10 min; comment-question CTA only in the last 30 s; no subscribe
   plea before the payoff; the last 20 s name the next story. The Babel build (8.1 min) is below the floor: coordinator decision
   under the frozen gates, not changed here.
5. **Short template (variant A, 60-90 s)**: 0-3 s one spoken line (<=14 words) that states the stake or paradox of the title and never
   refers to a previous part; 3-10 s who and what is at risk; 10-55 s two or three escalations each ending unresolved; 55-68 s payoff
   with one exact KJV line; 68-75 s one answerable comment question, last clause able to lead back into line 1. Title = hook line
   first; no label-only titles. Test: 1 of the 4 daily Shorts as variant A for 7 days; success median views >= 2x the variant-B
   median of the same days, kill <= 1x; sparse data stays inconclusive. The 170-s bridge stays variant B with its first line fixed.
6. **Cadence**: 4 Shorts/day (owner rule) and one long per story/one compilation per arc are unchanged; the evidence shows no
   cadence effect, the change is the content of each slot. Re-package the oldest published longs (title and thumbnail only, never
   the accepted media), one attribute per test, read 7-day views and CTR in Studio.
7. Content limits: two Bible Shorts winners use non-canonical material (2 Enoch, giants at the ark) and one may be re-cut film;
   KJV-only and original media stay. Pattern only, never wording or visuals.

Limits: 5 of the 6 requested cross-niche maps (10 credits were left under the cap); two winners have no captions; the weak sample
is 24 days old and Genesis-5 heavy; Tamil and Hindi transcripts were translated by Claude.

## 2026-11-04 — Tools market research

Owner asked for a deep survey of connectors, plugins and skills. Result: `../evidence/research/TOOLS-MARKET-2026-11-04.md` (research evidence, not a directing document; research only; nothing installed or connected,
no spending). The account's own catalog holds no enabled plugins and only generic skills; the useful assets are already wired (Gemini native review,
Playwright Studio runner, Analytics API reports, vidIQ, manifold). Top picks: finish the Gemini calibration as the listening defect finder, add UTMOS and
per-sentence WER to `local_review.py`, extend Analytics API funnel fields, run a MuseTalk/LatentSync lip-sync bake-off on free Kaggle GPU, use the
unused vidIQ thumbnail/title scorers. Rejected: community FFmpeg and YouTube MCP wrappers, paid lip-sync services, `claude-code-action` on an API key.
Models are defect finders, never a copied score; the human or authorized session review stays the approval.

## 2026-11-04 — Gemini free tier may train on what we send: owner accepts

Asked "Gemini grátis: a faixa grátis pode usar o que enviamos para treinar os modelos, inclusive vídeos antes de publicar. Aceita?"
(~21:50Z), the owner answered "Sim". Recorded as the owner's acceptance: free-tier Gemini may be used on unpublished masters, still
only under the Free Tier proof, the no-spend rule and the exact-media binding. Gemini remains a defect detector for the session
review (`native-review.yml` `defect_scan`, timestamped mispronunciation/garbled/loudness/music-voice/sync/visual defects); it never
approves and no score is copied to other media.

## 2026-11-04 — Pavo clips are silent; the narration goes over them (owner order, E301)
- Owner, in chat 2026-11-04 ~22:50Z: "Pode continuar fazendo com pavo mais coloca só vídeos sem narração.. e coloca a
  narração por fora..". Pavo stays our video engine, but its clips are silent action/acting clips: nobody speaks on camera,
  no lip-sync; every spoken word (Keeper lines, character KJV lines, narration) is our Kokoro audio laid over the picture.
  Pavo's own audio is never used. This replaces the talking-shot / Pavo-audio route (the 2026-11-03 "Pavo clips in full with
  Pavo's own audio" order and the E296 standing rule's `pavo_audio: "pavo"`) for NEW plans; approvals and plans already made
  under those routes keep their records, and `owner_regen.json` is not edited.
- Why: Pavo's own speech garbled the KJV words in 3 longs and the talking shots failed repeatedly (E287, E290, E292, E293,
  E295, E296); the picture was the part Pavo does well. E301.
- Codified: shot fields `pavo_mode` "silent", `pavo_audio` "none", `pavo` {action, setting, mood, wardrobe?, view?, camera?};
  `pavo_prompt.build` fills `TEMPLATE_SILENT` (`pavo-silent-v1`); `plan_check` refuses a prompt that asks for speech or
  lip-sync, a character's line over a frontal face, Pavo audio, a plain still, God; the E290 coverage is met by a silent
  Pavo clip of the character under the line; `episode_build` sends no audio, strips Pavo's track, checks `MOUTH_TALKING` and
  the face (profile and open-mouth notes are reviewer WARNs); shot-probe allows silent shots, one generation per line per
  prompt revision. PROMPT_GUIDE "Pavo silent-clip standard" is the spec; OPERATIONS has the note.


## 2026-11-05 — Inteligência Viva
- Moment M3 (48 h checkpoint). Triggers HIT, all on thin samples: views from Shorts = 0; CTR <2% (Noah-begins 1.79% on 280 impressions, Flood Ends 0% on 47); AVD <3 min (Noah-begins 176 s, 16 views). Actions: title-only repackage of X2LPFriRn3M and 1m-NUJhkdMY; funnel moved to end screen, playlist, first description line and pinned comment; next long gets the strongest beat in the first 30 s.
- Goal: subs 354 (measured live; +44 in ~28 h, 6.6/day over 11 d), long hours 30.2 (own estimate). Gap 646 subs / 3,970 h. Needs 64.6 subs and 397 h/day for 11-15; 24.8 and 152.7 for 12-01. Hours bind; subs can reach 1,000 by ~11-21 only if the one-day pace holds (estimate). Weakest factor: long impressions (47-280 per Bible long, measured).
- Findings: the Noah compilation is 18:03, not the planned 40-60 min, and the Babel long is 8:04 (floor 13:00): both logged, the 11-08 compilation must state its real length (>=30 min target). In-niche search: KJV hours winners are 1-5 h audio read-alongs (Blessfully 153K subs, Psalms 5.0 h 5.7M views); old, not our scale, one search, not added to the map.
- Lessons (non-Pavo): publish.yml dispatched twice reconciled to one video (idempotent), but the long went public ~75 min before its slot, so set publish_at on the first dispatch; faster-whisper alignment IndexError is intermittent (E302, fixed by #861/#862); a compilation is not "done" at a shorter length than its plan. No new Pavo lesson.
- vidIQ 10 credits (2,944 before, ledger updated).

## 2026-11-05 — Keeper lip-sync with our audio (owner order)
- Owner, 2026-11-05, verbatim: "No guardião eu quero lixo sync pra ele falar.. verifique algo gratuito e de qualidade" (lip-sync; "lixo" is the typo for "lipsync").
- Scope, same day (coordinator relaying the owner): the hook, character-speech moments and Keeper closing are all Pavo video; lip-sync of our Kokoro audio is for the Keeper always and for character lines when needed; "good enough to publish", not perfect; the owner accepts AI lip-sync never looks exactly human, so the best free model's result is used and a slightly imperfect mouth is no reason to reject or regenerate: the gates only rule out clearly broken output (wrong mouth or noticeable lag or a frozen face = the unchanged SyncNet window and 2.7 floor; no face; visible artifacts). The owner's PC (MX330, 2 GB VRAM, 8 GB RAM) cannot run the models: cloud and free only.
- Decision: the Keeper speaks on camera again, but the words are ours: a Pavo silent frontal Keeper clip plus a lip-sync of our Kokoro line. Model MuseTalk 1.5 (code MIT, weights usable commercially) on the free GitHub Actions CPU (`lipsync.yml`, 2-4.7 min of runner per second of picture, 8 s clip or less); LatentSync is the GPU upgrade (insightface detector is research-only, must be swapped), Wav2Lip rejected (non-commercial). No new spending.
- First measures (`evidence/lipsync/20261105`): SyncNet offset 0, confidence 3.1 and 3.3 on two Keeper lines (7 s and 5 s) (control with no lip-sync: offset -13, 0.6), gates pass with a thin margin, Pavo-native lips read 6.8-8.6; lower face is a soft 256 px patch. Nobody has watched and heard it yet: not approved, no score.
- Codified: plan field `lipsync` (plan_check LIPSYNC_*), `keeper_lipsync.py` + tests, `lipsync.yml`, PROMPT_GUIDE "Keeper lip-sync (our audio)", OPERATIONS note. Wired (E304): `episode_build.py lipsync-record` turns a lipsync.yml result into a probe record; approve-shot and the build use the lip-synced clip only with its proof (this clip, its stored silent source, the Kokoro line by PCM sha256, SyncNet/face gates unchanged, no flag); every clip without one keeps MOUTH_TALKING; the compose lays it at normal speed from the first word. `lipsync.yml` episode mode (`plan` + `shot` + the stored silent clip's sha256) takes the line `lines` writes, runs `lipsync-record`, and its record job (main only) uploads the clip and pushes the record on `claude/lipsync-<episode>-<run>` for the real review.

## 2026-11-05 — Inteligência Viva (extra run, owner request)
- Moment M3 continuing (M4 starts 11-06). Triggers still HIT (views from Shorts 0; CTR <2%; AVD <3 min, thin samples). Actions: titles of X2LPFriRn3M/1m-NUJhkdMY, funnel text, Abraham long script first.
- Goal: subs 372 (measured live, +62 in ~34 h, 8.3/day over 11 d); long hours 30.2 (own estimate). Gap 628 subs / 3,970 h; needs 62.8 and 397 h/day for 11-15, 24.2 and 152.7 for 12-01. Hours bind; deadline unchanged.
- H1 (read-along) tested against the accumulation rule with a 25-result search plus two more (evidence/vidiq/2026-11-05/h1-h2-pool.json): 10 winners from 9 channels, 12 weak contrasts. Result: static read-alongs from channels under ~3K subs get 8-710 views, so the pure read-along is KILLED for us; the 'Full Movie' book/arc compilation with chapter timestamps (PicVersion 4:40, 657K views on 12.1K subs) is the surviving form and becomes H2, priority 1, built from approved media only, real length stated (>=30 min).
- Lessons (non-Pavo): do not repeat the over-specific search form 'bible stories compilation hours genesis KJV scrolling text' (empty, 5 credits wasted); a lever that wins on big channels is not evidence for a 372-sub channel, so test it at zero cost first.
- vidIQ 20 credits this run (30 of 150 today; 2,914 left).

## 2026-11-05 — Same-story still reuse (owner order)
- Owner, 2026-11-05, verbatim: "Se não for abaixar a qualidade e ajudar a chegar na meta com precisão, pode fazer." Same day, verbatim: "sempre tem que promover coisas novas... a camada de autenticidade, originalidade e crítica não pode faltar... tem que estar inserindo em grande parte."
- Decision: an APPROVED still of another plan of the same story (same book with overlapping verses, or the same `story_id`) may be reframed 16:9 <-> 9:16 into a NEW still record of this plan (`derived_from` source id + sha256, `crop` box, its own sha256), approved by the same `scene_stills.py approve` after a real look at the reframed image (`--checked`, bound to the derivative's sha256); the source's approval is never copied. Refusals in `plan_check` (REUSE_*): other story, source not approved or changed, chain, same plan, off-scene, crop invalid or off-centre, low resolution counted in the source's generated pixels (>= the normal route's 576x1024 for 9:16), God with a face, no review.
- Cap and originality (owner rule above and YouTube YPP's "reused content" policy): reframed stills are at most a third of a plan's stills (REUSE_SHARE_TOO_HIGH), never under the narration line their source carried (REUSE_SAME_LINE), and the plan keeps its own Keeper shot and insight line with no story/insight line copied (REUSE_NO_ORIGINAL_LAYER).
- First application, genesis-12-short (17 stills, cap 5): 6 good matches outside the line rule were reframed and looked at (behold, gathered, top kept the subject; babel, foundation, unfinished cut it). All 6 come from ChatGPT 1672x941 images resized to 1920x1080: a 9:16 crop holds 529x941 generated pixels, below the normal route, and measured softer than every approved 9:16 Short still (Laplacian variance 22-36 vs 53-plus). Quality would drop, so none was approved; all 17 stay on the normal stills route. The rule pays off on sources generated at higher resolution (for example 2560x1440 or more).
