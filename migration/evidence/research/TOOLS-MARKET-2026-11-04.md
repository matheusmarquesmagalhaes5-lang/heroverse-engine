# Tools market research, 2026-11-04

Owner request (2026-11-04): survey the connectors, plugins and skills that could help with the recurring pain points. This
page is research only. Nothing was installed, connected or suggested for install. It does not change SYSTEM.md. Adopting any
item below is a separate step under the normal rules (zero new spending, `claude/*` PR, tests, ERRORS.json where a defect is involved).

## How this was checked

| Label | Meaning |
|---|---|
| VERIFIED | Read on the official page/repo during this research (2026-11-04), or seen directly in this session's tool list |
| CLAIMED | Only seen in blogs, listings or search snippets; confirm before relying on it |
| UNCHECKED | Searched, nothing usable found |

Limits of this survey: the in-product registry search tools (SearchMcpRegistry, SuggestConnectors, ListConnectors) were not
available in this session, so the connector catalog was read from the tools already attached. `ListPlugins` returned no enabled
plugins; `ListSkills` returned only 11 generic skills (docs, google-workspace, computer-use, chrome-browser, built-in-browser,
deep-research, import-memory, morning, skill-creator, xlsx, pptx, pdf, docx). `SearchSkills` found nothing relevant. The
`SearchPlugins` directory returned community plugins (all `publisher.tier: community`, none Anthropic-verified).

## What the project already has (do not re-buy)

- Gemini native review: `native-review.yml`, `gemini-3.8-flash`, AI Studio free tier, optional second opinion; `shorts-gemini-calibration.yml` (pending qualification).
- Local review: `local-review.yml` (pinned ASR + ffmpeg measures + frame sheets). It does not listen by ear (CURRENT, Babel).
- Playwright-based Studio runner on the PC (`integrations/studio-local/`), plus `chatgpt-local`, `tiktok-local`, Pavo and Buzzy integrations.
- YouTube Analytics API in `mining/reach_report.py` and `goal_report.py`; vidIQ with a no-credit-spend rule (`VIDIQ.md`); `ops/test_token_budget.py`.
- Account connectors seen in this session: GitHub, vidIQ, Buzzy, Pavo (custom), Desktop Commander, manifold, TinyFish, Higgsfield
  (read-only: balance and listing; the connector says it cannot generate), Runway, adplane (ads, on hold), Claude Docs.

## Findings by pain point

1. **Listening to audio.** VERIFIED: Gemini audio understanding takes WAV/MP3/FLAC/AAC/OGG/Opus, 32 tokens per second,
   up to 9.5 h per prompt, with diarization, emotion and timestamped segment analysis (aistudio.google.com/docs/audio). VERIFIED:
   the pricing page lists a free tier for Gemini 3.8 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite and 3 Flash Preview, but does not
   break out free-tier limits per modality; check the live AI Studio quota. CLAIMED: free-tier prompts may be used by Google to
   improve products, so unpublished masters are a privacy question the owner should settle. The 2026 arXiv study (2604.08562)
   found Qwen2-Audio-7B is a poor absolute scorer of speech naturalness (31% accuracy) but decent in pairwise comparison
   (76%), and that UTMOS correlates far better with human ratings (LCC 0.842). Lesson: use models as defect finders and
   pairwise judges, and use UTMOS-class metrics for naturalness; never copy a model score as a 9.5.
2. **Lip-sync with our audio.** VERIFIED: LatentSync (bytedance, Apache-2.0, v1.6 June 2025) needs about 18 GB VRAM for 1.6 and
   8 GB for 1.5. CLAIMED: MuseTalk is MIT, 256x256 face region, runs in 4 GB FP16, needs OpenMMLab (painful setup). CLAIMED: InfiniteTalk
   (Wan2.1 14B base, ~28 GB weights) is too heavy for free hardware. GitHub-hosted runners have no GPU; the free GPU routes are Kaggle
   (CLAIMED about 30 GPU h/week, T4/P100, no official number) and Colab (CLAIMED 15-30 h, unpublished). Both are manual notebooks, not CI.
   Sync Labs, Hedra and Wav2Lip licensing: UNCHECKED, and the hosted ones are paid. Runway has a lip-sync feature (CLAIMED, UNCHECKED quota); treat as paid.
3. **Stills via the ChatGPT desktop app.** No free API substitute was found that beats the current route. The account's
   Higgsfield connector cannot generate (VERIFIED, connector text); Buzzy generation spends prepaid credits; Gemini image models in the
   AI Studio list are not free-tier (VERIFIED: Nano Banana image models have no free tier). Keep the existing runner; improve its receipts, not its engine.
4. **Studio-only actions.** VERIFIED: `@playwright/mcp` is Microsoft's official server (Apache-2.0, ~39k stars), with an
   `--extension` mode that attaches to the real logged-in Chrome and a `browser_run_code_unsafe` tool described as RCE-equivalent; it
   states it is not a security boundary. VERIFIED: YouTube's Terms bar access "using any automated means (such as robots, botnets or
   scrapers)" without YouTube's written permission, and bar manipulating metrics. The existing owner-authorized runner is already
   inside that risk; keep it low-volume, one video at a time, own channel only, own Chrome profile. Do not add the extension mode.
5. **Growth analytics and distribution.** No Google-published YouTube MCP exists (search found only community wrappers on PyPI,
   UNVERIFIED maintainers). Our own scripts on the official Analytics API are safer. Buffer free (CLAIMED: 3 channels, 10 queued posts each)
   is already allowed by CLAUDE.md for a public Short. Postiz (CLAIMED AGPL-3.0, self-hosted) needs a server and per-platform
   developer app reviews: more work than it saves today.
6. **Token and PR babysitting.** ccusage (MIT, local JSONL logs, CLAIMED popular, ryoppippi) reads only local logs. `claude-code-action`
   (anthropics) needs an API key or subscription token; an API key is new spend (paid, not recommended). The session already has PR
   subscription tools and the heartbeat.

## Ranked table

Impact/effort: H high, M medium, L low. "Cost" means new spending; all recommended rows are zero new spend.

| # | Tool | Type | Pain point | Cost | Source | Trust / risk | Effort | Impact |
|---|---|---|---|---|---|---|---|---|
| 1 | Gemini native audio+video review, finish calibration and extend to longs (chunked) | Model API (already wired) | 1 | Free tier (limits to read live) | aistudio.google.com/docs/audio, /docs/pricing (VERIFIED) | Google first party. Privacy of unpublished masters on free tier (CLAIMED); a model verdict is a defect finder, not an approval | L | H |
| 2 | UTMOS / UTMOSv2 + pinned-ASR word error rate as objective gates inside `local_review.py` | Open-source model | 1 | Free (CPU in Actions) | arXiv 2604.08562 (VERIFIED paper); repo versions to pin before use | Pin commit and weights hash; no credentials | M | H |
| 3 | Extend Analytics API scripts: retention curve, traffic sources, "Shorts feed" source and returning viewers per Short | Official API | 5 | Free (quota 10,000 units/day, CLAIMED) | developers.google.com/youtube/analytics | Official; needs the yt-analytics.readonly scope on the existing OAuth (secret stays in Actions) | M | H |
| 4 | MuseTalk 1.5 / LatentSync 1.5 lip-sync A/B on Kaggle for one failed Pavo line, our Kokoro audio | Open-source model | 2 | Free quota (CLAIMED) | github.com/bytedance/LatentSync (VERIFIED); MuseTalk CLAIMED | Real repo, weights from official repo only; output is unreviewed media; owner rule: never regenerate Pavo clips, so this is an alternative, not a replacement | H | H if it works |
| 5 | vidIQ connector, unused tools: `score_thumbnail`, `score_title`, `similar_thumbnails`, `outliers`, `video_watch` | Connector (in account) | 5 | In-plan; obey VIDIQ.md no-credit-spend rule | Tool list (VERIFIED present) | Known vendor; credit walls exist (VIDIQ.md) | L | M |
| 6 | Qwen3-Omni-30B-A3B or Audio Flamingo 3 as a second, independent open "listener" (pairwise and defect-finding only) | Open-source model | 1 | Free but needs 24 GB+ GPU or quantization (Kaggle uncertain) | arXiv 2507.08128 (VERIFIED paper); Apache-2.0 for Qwen3-Omni CLAIMED | Do not use for absolute scores (see finding 1) | H | M |
| 7 | `@playwright/mcp` in an isolated profile only to discover Studio selectors; keep the existing runner | Official MCP | 3, 4 | Free | github.com/microsoft/playwright-mcp (VERIFIED) | Never `--extension`, never `browser_run_code_unsafe`, never the everyday Chrome. YouTube ToS risk (VERIFIED text) | L | L-M |
| 8 | manifold `youtube_*`, `tiktok_*`, `instagram_*` transcripts/profiles for competitor mining; TinyFish search/fetch | Connectors (in account) | 5 | Prepaid credits per call: always `dry_run` and `max_credits`; otherwise paid, not recommended | Server instructions (VERIFIED) | Third-party data vendor; read only | L | M |
| 9 | Buffer free mirror for already-public Shorts (Facebook, Instagram, TikTok); defer Postiz | SaaS free plan | 5 | Free | buffer.com pricing (CLAIMED limits) | Needs account OAuth; allowed by CLAUDE.md | L | M |
| 10 | ccusage pinned version on the PC for local token use; keep `test_token_budget.py` | CLI | 6 | Free | github.com/ryoppippi/ccusage (CLAIMED) | npm supply chain: pin an exact version, run with no secrets | L | L |

Reviewed and not recommended:

| Tool | Reason |
|---|---|
| Community FFmpeg MCP servers (mrdainami, bitscorp, PedroMarianoAlmeida, others) | Several expose a generic `shell_run`; unknown maintainers; `ffmpeg` is already available through Bash. Risk without benefit |
| Community YouTube MCP wrappers on PyPI (youtube-studio-mcp, youtube-complete-mcp and similar) | Unverified maintainers, need OAuth refresh tokens; our own scripts on the official API are safer |
| TubeAlfred, AdvisorPPC, AdCopilot, SEO plugins in the directory | Remote third-party services over channel data, or built for websites and ad accounts (ads are on hold) |
| `watch-video`, Video Cleanup, Local Whisper plugins (community directory) | Overlap `local-review.yml`; hosted Whisper options need keys; install only if a gap is proven |
| `claude-code-action` with an API key | New spending; use only if a subscription-token path is confirmed |
| Sync Labs, Hedra, Runway lip-sync, InfiniteTalk hosted | Paid or unverified: paid, not recommended |
| adplane (Google/Meta/TikTok/Microsoft ads) | Ads are on hold |

## Top-10 recommendation with the first concrete step

1. **Gemini listening review (pain 1).** Run `shorts-gemini-calibration.yml` to qualification; then run `native-review.yml` on the
   Babel long master in chunks under the daily budget. Record the actual model identity. Treat the output as the listening defect
   list for the human/session reviewer. Decide the free-tier privacy question with the owner first.
2. **UTMOS + WER gate (pain 1).** Add a `naturalness` and `per-sentence WER` row to `local_review.py` output with pinned weights; flag
   sentences below a threshold set from the known-good Shorts. This targets the "mighty/miety" class of flags without a human.
3. **Analytics funnel (pain 5).** Add the Shorts-to-long funnel fields to `reach_report.py`: traffic source "Shorts feed", "end screen"
   and "suggested" for each long, plus subscribers gained per long. Test: report runs in Actions with no new secret.
4. **Lip-sync bake-off (pain 2).** One notebook on Kaggle: one 8 s Pavo line that garbled, Kokoro audio, MuseTalk 1.5 and LatentSync 1.5, 3 settings each;
   score with `lipsync_check.py` and a listening/viewing review. Owner approves any Pavo-related change first.
5. **vidIQ unused tools (pain 5).** For the next long thumbnail, use `score_thumbnail`/`similar_thumbnails`; for titles `score_title`.
   Check balance first; stop at the first credit wall.
6. **Second open listener (pain 1).** Only after 1 and 2 prove insufficient: try Qwen3-Omni quantized on Kaggle on pairwise A/B of two audio mixes.
7. **Studio selector discovery (pain 4).** In a throwaway profile on the PC, run `@playwright/mcp` against Studio only to record selectors
   for end screens and playlists; commit them as data to `studio-local`. No cookies leave the PC.
8. **Competitor mining (pain 5).** Use manifold `youtube_get_transcript` and `tiktok_search_videos` with `dry_run` and `max_credits`,
   recorded in the vidIQ/market ledger; abort when a call is not covered by free cache.
9. **Distribution (pain 5).** Keep Buffer free for the already-public Short only; check in the dashboard whether Facebook Reels and Instagram Reels
   are accepted on the free plan before relying on it. Revisit Postiz only when 3 channels are insufficient.
10. **Token view (pain 6).** `npx ccusage@<exact version> daily` on the PC, weekly, to compare with `test_token_budget.py` limits.

## Supply-chain and policy notes

- Every third-party item above is community or vendor code. Pin an exact version or commit SHA (the official marketplace README
  itself suggests pinning `sha`), download weights only from the official repo or model card, and run with no secrets in the process.
- Reports in 2026 describe malicious skills in a third-party skills marketplace and a trojanized Claude Code extension in an editor
  marketplace (CLAIMED, sources conflict). Prefer Anthropic's official directory, the Anthropic organization on GitHub, Google and Microsoft
  repos; treat the directory's `community` tier as unreviewed code.
- Tools that need account cookies or refresh tokens (Studio runner, YouTube MCP wrappers) stay on the PC or in Actions secrets only.
- Anthropic and YouTube terms: do not use a subscription token for anything outside Claude Code's own use; YouTube automation stays
  low-volume on the owner's own channel and never touches metrics.
