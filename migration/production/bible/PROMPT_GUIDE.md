# Bible-story construction: build for 9.5

Use the current workflow in `../../SYSTEM.md`. This guide specifies how to construct the actual episode before
final review. Preserve valid sources and the accepted audio; correct a demonstrated defect in its source,
framing or sequence. An intended score is not a source approval or an audiovisual review.

Pavo is the current first route for the hook and speaking Keeper/characters, with a fresh exact zero-credit quote,
current shared capacity and approved references. Appropriate other visuals may use licensed/public-domain video
or GPT-generated stills with cinematic motion. Record the actual origin and rights. Camera movement alone does not
prove body action, fluid motion or lip-sync. Use the applicable format's existing checks, never a misidentified
provider or unrelated frozen profile. No new spending or unqualified paid fallback.

## Prompt structure

Describe five things in this order:

1. **Cinematography:** shot size and one camera move.
2. **Subject:** the concrete person or object actually shown.
3. **Action:** one dominant physical action.
4. **Context:** period, place, time, weather and light.
5. **Style and ambience:** the series' visual anchor and the intended feeling.

Duration and aspect belong in the tool fields. Write observable action rather than metaphors. Use positive
descriptions instead of lists of unwanted objects that can prime a model to draw them. Match the selected source
to the exact words and dramatic purpose; a stock description or prompt is not evidence of what the source shows.
Use cut transitions; a deliberate fade to black is reserved for an intentional ending, not every scene change.

## Identity, period and recurring objects

`production/characters/characters.json` is the character identity record. Every visible named character needs
APPROVED references; prompts retain the exact look and a valid wardrobe variant. Send the appropriate approved
references through the selected route and keep their hashes. New characters are qualified before use.
God is never a person, face, body or throne: exact KJV words play over the appropriate non-person scene.

Every scene uses its validated period setting and exclusions from `plan_check.py`. Inspect for actual modern
buildings, roads, clothing, equipment, symbols and writing. Anonymous figures may appear only as the permitted
rear/silhouette coverage; an unapproved face is not made acceptable by calling it anonymous.

The ark stays the same recurring prop, with its approved reference images. For current flood prompts, use
`plan_check.ARK_PHRASE` exactly:

> a giant long rectangular wooden crate of rough planks smeared pitch-black, with a flat plank roof and flat square ends, as tall at both ends as in the middle

Use the positive phrase within the shot's sentence; do not add alternate vessel names or negated mast/funnel
descriptions. Keep the flood period sentence and prop-reference proof required by the current source checks.
Inspect the actual geometry, scale and continuity. A correct prompt does not establish a correct image.

For image-first requests, inspect and approve the actual still before requesting motion. Keep its source hash in
the request. Describe the required motion/camera without redescribing an incompatible second composition.
Scene stills, source clips and thumbnails retain their own exact approvals and actual reviewer identities.

## Built for 9.5 before compose

Complete source/script checks before the full final compose, including free and imported edits. Resolve
construction defects in short contextual samples with the incoming/outgoing cuts, accepted sound and captions.

1. Inspect every selected source and its actual final-format crop. The intended subject stays visible, with
   sound anatomy, identity, period and texture; source descriptions alone do not qualify it.
2. The picture matches the exact spoken units and advances the dramatic purpose. Check observed action and
   continuity, including the acted climax; camera-only motion is classified honestly.
3. Construct readable, correctly timed captions and a clear mix using the existing Short engine parameters.
   Its output is 1080×1920 at 30 fps, with large captions and a mix targeted near −14 LUFS.
   KJV Scripture is set apart (E249): gold serif italic, with a "Genesis 7:9 · KJV" citation (from the line's
   `reference`) shown for the whole quotation; our own commentary stays in the normal white captions.
4. Inspect the composed picture and review the complete actual audio/video before publication. Contact sheets
   support the review; they cannot establish sound quality. Every demonstrated sub-floor defect is corrected.
5. Downloaded candidates pass `clip_check.py` before composition: decode, opening/ending, size, frame rate and the
   relevant visible-content checks. Reused sources retain their byte identity and valid approval.
6. Use cuts between scenes. Keep intentional dark transitions explicit; no accidental black flashes from fades
   or wipes. Do not hide a coverage gap with an unreviewed transition.
7. The final file passes `clip_check.py --composed` and its applicable technical checks. Record actual measured
   results against the file hash. A DRAFT render receipt is not final audiovisual or publication approval.
8. Every Scripture line is referenced and passes `kjv_check.py` against the pinned KJV text before new speech.
   Preserve an accepted existing voice track. Do not count unreferenced KJV quotation as original narration.
9. The current Short contract passes `publish_episode.short_problems`: measured 170–179 seconds from part 7,
   ≥40% original spoken words, an original insight of at least 20 words and a close naming the full story.
   The narration is recorded as scripture/story/insight/cta; known older published exceptions do not set new targets.

### Actual construction record

For every source interval, retain its real frame boundaries, exact spoken units, dramatic purpose, source hash,
observed figures/action, movement capability, approval evidence and remaining defect. Apply the eight dimensions in
`../../ops/CLAUDE_REVIEW.md` while constructing the source and its contextual sample. A target of 9.5 is not a
measured grade. Source approval and the final complete audiovisual review remain separate evidence.

Inspect first/middle/last frames for a crop or movement change and the corresponding contextual sample. Fix the
demonstrated source, framing or sequence before another complete final render. Reuse unchanged accepted work.
Never repeatedly submit an unchanged master to obtain a more favorable score.

For a private preserved edit, reconcile the plan with the actual bound timeline before acting on stale refusals.
Measured frame/PCM duration and narration estimates are different evidence. Keep the original audio/mix/captions,
true provenance and explicit unknowns. `episode_build.py import-edit` preserves those inputs without synthesizing
voice, retiming, extra gaps or a tail. Its receipt and construction samples remain DRAFT evidence until qualified.

## Long-first: the centre 9:16 safe area

Owner, 2026-11-01 (E259): after the Noah compilation the story is made as a 16:9 long first (plan `"track":
"buzzy-long"`, `"aspect_ratio": "16:9"`, about 8–12 minutes) and its Shorts are 9:16 centre cuts of it
(`short_cuts.py`). Every picture must survive that crop:

- The subject (the speaking face, the acting figure, the object the line names) stays inside the centre 9:16 column:
  the middle 56 % of the frame width (607 px of 1920 at full height). Wide establishing shots may fill the frame, but
  what the line is about stays in that column.
- Every scene, Keeper and still prompt says so in words: "centred in the frame" (`plan_check.SAFE_AREA_UNSTATED`
  otherwise), and names no off-centre framing — off-centre, rule of thirds, split screen, at the left/right edge or
  third (`SAFE_AREA_OFF_CENTRE`). FLUX stills of this track get the centre-column style (`scene_stills.LONG_FIRST_STYLE`).
- The words cannot prove the picture: the source review still looks at the actual 16:9 frame and its centre 9:16
  crop. A cut may move its window (`x`, 0–1) for one range; a subject that leaves the column is a [b] defect of the cut.
- The long's own captions are burned at 16:9 sizes (about 7 % of 1080 px, four words a card, `short_engine.caption_style`);
  the caption-free master is kept for the cuts, which get the Short's own caption style from the same sentences.

## Cinematic still animation

Owner, 2026-11-01 (E261, DECISIONS "Cinematic still animation"): "it cannot be rigid; it has to animate according to
need". A long-first long (`"track": "buzzy-long"`) holds about 25–30 approved stills of 15–20 s each; a scene shot may
run 4–20 s, and beyond 12 s it is an approved still. Each still is moved by `motion.py`'s cinematic engine
(`cinematic-v2`, CPU only, zero cost); a Short's still keeps its plain push-in.

How the director (`motion.direct`) chooses, per still, in plan order:

- **Beat**: hook (the first shot: a confident push or reveal that starts moving at the cut), escalation (pushes, pans,
  parallax, growing with the story), KJV line and climax (`hold_then_push`: the silence before the line held, then a
  slow push), Keeper insight (a gentle drift or parallax), aftermath (a settling pull back or tilt down). The climax is
  the shot ids named after "climax" in the plan's `beats`, else the last scripture shot of the last 45 %.
- **Emotion**: the prompt's mood sentence ("Mocking and uneasy.") — dread and tension creep (`build` easing), awe
  tilts up or reveals, grief pulls back, calm drifts, urgency pans and settles fast.
- **Words**: a camera the prompt names ("slow tilt up", "tracking shot") weighs in; sentences most prompts share
  (the style and world lines) are ignored.
- **Span**: the move is fitted to the shot's spoken span in the build's layout and lands on its last frame; a short
  span gets a smaller move and no hold.
- **Picture**: a face found off centre gets a pan that lands on it; a clear near/far depth (Depth Anything V2) favours
  parallax; fire, a torch, water in the lower frame, rain, mist, dust, light from above and darkness choose up to three
  atmosphere layers (`dust`, `embers`, `mist`, `rain`, `water_shimmer`, `god_rays`, `torch_flicker`, `film_grain`,
  `vignette`).
- **Sequence**: never the same move twice in a row; the same family (in, out, lateral, vertical) and the same lateral
  direction are avoided after each other, like an editor varying scale and direction.

Hard limits on every frame: the still always covers the frame (no edge), the subject box (face, else saliency) stays
inside the centre 9:16 band, sub-pixel motion from a 2x master, and the same input gives the same file. A move the room
cannot hold is made smaller; the report says so.

Override in the plan shot (it wins over the director; plan_check validates it):

```json
{"id": "s-12", "kind": "scene", "seconds": 18, "motion": "pan_to_subject", "atmosphere": ["mist", "vignette"]}
{"id": "s-13", "kind": "scene", "seconds": 16, "motion": {"move": "hold_then_push", "hold": 0.4, "ease": "in_out", "strength": 1.2}}
```

`motion` is one of `push_in`, `pull_back`, `pan_left`, `pan_right`, `tilt_up`, `tilt_down`, `pan_to_subject`, `drift`,
`parallax_2_5d`, `hold_then_push`, `hold`, or `{move, ease (in_out, settle, build, gentle), hold (0.1–0.5), strength
(0.4–1.5)}`; `atmosphere` lists at most three names (`[]` = none). A still of 12–20 s may not hold
(`MOTION_REQUIRED`), and two stills in a row may not name the same move (`MOTION_REPEATED`). Overrides are part of the
shot's request digest, so changing one needs a new approval. Every still's chosen move, easing, atmosphere, keyframes
and reason are in the build report (`shots.<id>.motion_direction`); `motion.py moves IMAGE OUT.jpg` shows every move
on a still for review. The moving picture is still judged by watching the long.

## BibleShort story grammar

The plan is `bible-plan-v2`, with narration records and ordered shots. `plan_check.sequence` gives the spoken
sequence: narration in the Keeper's pinned voice and each speaking character's own line/voice.

- **Opening (0–3%):** a spoken conflict starts at zero, through an approved character or God's exact KJV voice.
  The Keeper, a title card or unrelated atmosphere does not open the episode. Exception (E272, E290): a long-first
  long and a bridge Short (track `buzzy`) open on a Pavo talking shot, the Keeper or a speaking human character (below).
- **Stake/open loop (3–10%):** establish the danger, question or conflict clearly.
- **Escalation (10–60%):** rising story steps with a visual action and continuing question; cuts maintain momentum.
- **Climax (60–80%):** the decisive story moment is acted, with people on screen and a `climax:true` scene.
  If God's line delivers the turn over sky/light, the acted scene following it supplies the climax.
- **Payoff (80–85%):** show the outcome rather than adding another unfulfilled promise.
- **Keeper close (85–100%):** only after the last climax, for the original insight and CTA. He closes the story.
  Keeper and lesson shares are each ≤25%; the composition uses actual intervals, not a convenient word estimate.
  Aim for the existing shorter lesson target where the story supports it.

The current spoken-line route retains exact character/voice bindings and the existing limits in `plan_check.py`,
`voice_pace.py` and `episode_build.py`. A new regular plan is measured before dispatch; the measured full duration
decides its length, not a word-count estimate. Quotes are exact KJV and referenced; narration cannot invent a
character's dialogue. God's voice is pinned offscreen and the source is checked for visible faces.

A talking clip must match its exact audio, references and prompt, with passing speech and lip-sync evidence.
The regular route's existing line/clip retime rules apply before acceptance; an imported accepted master is not
stretched later to fit a replacement. Preserve actual failures and their measures. A good clip from another line
does not establish synchronization for this line.

**Pavo's audio is Pavo's, the clip is used in full (owner 2026-11-03, reverses E287's default: "Quero com o audio do pavo
tambem.. quero o video do pavo na integra. A narracao feita vai ser pras imagens.. aproveitar tudo que o pavo pode
oferecer").** `pavo_audio` is a per-shot setting: `"pavo"` is the DEFAULT for every track (long compose, reflection,
compilation, bridge Shorts); `"ours"` (E287, below) stays only as an explicit per-shot option and for approvals already
recorded under it (`pavo_audio.route_of` reads the recorded proof, so their digests do not move; compilation plans built
before the order are grandfathered by id in `compilation_long.OURS_BEFORE_2026_11_03`). Our Kokoro narration is used only
over still and scene shots (and over a voice-over Keeper segment).
- The request is unchanged (our exact line as input audio, `sound: false`, so request digests hold). The kept clip is the
  bytes Pavo returned: no mux, and `trim_out_s` is applied only when the shot/approval sets it explicitly. The clip's
  `audio` proof is `pavo_audio.pavo_proof` (route `pavo`, digest of ITS decoded track, LUFS, true peak, the narration's
  LUFS); `PAVO_AUDIO_IS_OURS` refuses our line mislabelled as Pavo's.
- Loudness: approve-shot records one gain that brings the clip's integrated LUFS within +-1 dB of the narration
  (`pavo_audio.match_gain`, `LOUDNESS_NOT_MATCHED` when the peaks leave no room) with a true-peak ceiling of -1.5 dBTP
  (`match_filter`: limiter); the compose lays the whole clip into the voice track at that gain (`speech.route "pavo"`:
  onset 0, end = the clip's audio; the slot of that shot in the layout is the clip's whole length). The Pavo request keeps
  the pre-approval seconds and input WAV (`layout.pavo_requests`), so the approval's request digest holds.
- Picture crossfades (E272) stay at the boundaries and are picture only, never over speech: a reflection crossfade shortens
  to the silence the clip's tail has, down to a plain cut, and is never a refusal for a Pavo-audio clip.
- Checks: the visual gates stay (face present, mouth sync against the track the clip carries, artifacts, still mouth).
  `AUDIO_NOT_OUR_LINE` and `SPEECH_WORDS_NOT_EXACT` are not refusals for a Pavo-audio shot: `speech-check` records the pinned
  ASR text as `review_notes` (copied to the approval). EXCEPTION, the KJV-exact pillar: for a shot whose line is a direct KJV
  quotation (a `scripture` item of the plan), a word difference (or no ASR text) is surfaced as `WARN_KJV_WORDS` in the review
  notes so the reviewer decides; it is a warning, never an automatic refusal.
- A line's second generation is still only for a VISUAL defect (a words difference never buys one).

**Explicit `"ours"` (E287, owner 2026-11-03: "Pavo does only what we send; the fault is ours").** Send the exact
Kokoro line as the request's input audio with `sound: false`, and keep only Pavo's picture: the clip is Pavo's video with
the request's own WAV as its audio (`pavo_audio.mux_ours`, PCM), never Pavo's returned track, which is a re-synthesis that
can re-time the line, add a tail or change a word. The words are the request's words, exact by construction, and the audio
digest equals the request's WAV (`pavo_audio.assert_ours`, recorded as the clip's `audio` proof). Do not judge words on
Pavo's track, do not run `speech-check` on such a clip, do not discard a good picture for its returned sound. Lip sync, the
face and the visual checks stay strict and run against our audio (`lipsync_check` on the kept clip). A clip is regenerated
only for a VISUAL defect (the face lost, a broken render, lips out of sync with our audio), never for the words.

## Pavo talking-shot prompt standard

Owner, 2026-11-03 (E290): "Pavo does EXACTLY what you tell it. The failure is the prompt's organization." What Pavo
generates is used, so the request is right before it is sent.

**Coverage (every `buzzy-long` long and every `buzzy` bridge Short; `plan_check --strict` and `episode_build`):**
- The FIRST shot (hook) is a Pavo talking shot: the Keeper chest-up or a speaking human character
  (`HOOK_NOT_PAVO`). God is never shown with a face, so a hook that quotes God is the Keeper saying it ("And God
  said…") or a human character speaking; God's voice over a sky is not a hook.
- Every on-screen line a human character speaks (a quoted KJV speech of Noah, Abraham…) is that character's own
  talking shot, alone on screen, APPROVED with kept references; never narration (`CHARACTER_LINE_NOT_PAVO`). A
  non-talking scene uses still motion or footage.
- Every Keeper line, the critical insight and the close, is a talking shot (`KEEPER_LINE_NOT_PAVO`). The voice-over is
  allowed only with `"pavo_fallback": {"run": "<shot-probe run>"}` whose record shows a hard (visual) flag on every
  generation of that shot (the DECISIONS ladder after a real failure; a words flag is not one since E287).
- Plans published before the rule (flood-ends-long, genesis-09-short, genesis-10-short) are grandfathered by id
  (`plan_check.PAVO_COVERAGE_GRANDFATHERED`, held frozen by a test).

**Prompt: one builder, modelled on the prompts that passed (E293).** Owner, 2026-11-03: "Always model the prompt on
the way it was done the time it passed." A talking shot carries `"pavo": {"emotion", "setting", "wardrobe", "gaze",
"mood"}` and its `prompt` is exactly `pavo_prompt.build`'s (`PAVO_PROMPT_NOT_STANDARD` otherwise; never hand-written).
The builder fills `pavo_prompt.TEMPLATE`, the passing prompt of record word for word (it reproduces flood k-insight,
k-close and k-hook, the M2 hook, reflection k-r1, genesis-09 k-close and genesis-10 k-insight byte for byte):

> Image 1 is the narrator. *STYLE* Close-up from the chest up, his face large in the centre of the frame, static
> camera. The narrator, *look*, *wardrobe*, centred in the frame holds his head level and looks straight into the
> camera and speaks the words of the audio clip, his lips moving in sync with the voice, a calm kind look. *setting*
> Tender and grave. No text, no logos.

A character reads "Image 1 is Noah. … Medium close-up, static camera. Noah, *look*, …" with its gaze, and a scene adds
its period setting and exclusion sentences after the mood sentence, before "No text, no logos." (the order of the
passing character prompts). Nothing else is added: no wording that no generation has used.

Modelled on passing prompts (71 Pavo talking generations of record, 45 PASS / 26 FAIL;
[evidence](../../evidence/pavo-prompt-analysis/20261103.json): approved, or SyncNet sync and face on our audio):

| Part | Passing wording (pass rate) | Failing or untested wording |
|---|---|---|
| framing, Keeper 16:9 / 1:1 | "Close-up from the chest up, his face large in the centre of the frame" (Keeper 22/31) | "Medium shot" 0/10, 16:9 "Medium close-up" 0/2 (seated, drawn full body, face lost) |
| framing, Keeper 9:16 and characters | "Medium close-up" (Keeper 7/8, character pictures 20/20 with the face, 16/20 in sync) | — |
| binding and action | "Image 1 is the narrator." … "speaks the words of the audio clip, his lips moving in sync with the voice" (every Kokoro-input request, bound by `bind_prompt`) | the native SOUND block 3/4 (words wrong once) |
| pose and gaze | 16:9/1:1 "centred in the frame holds his head level and looks straight into the camera and"; 9:16 "holds his head level, looks straight into the camera and" | v1's separate "He holds his head level…" sentence: never sent |
| emotion | one "a <look> look" clause + one "<Adjective> and <adjective>." mood (`PASSING_LOOKS`: calm kind / Tender and grave, gentle questioning / Warm and searching, grave, intent / Hushed and urgent, warm expectant / Warm and expectant, grave knowing / Tender and grave) | v1's one-adjective "with a grave look": never sent |
| negatives | "No text, no logos." | v1's "no second person, no hand over the mouth, no head turn away" and "lips move only while… no humming": never sent |
| scroll, campfire flicker on the face, head level, straight gaze | in every Keeper prompt, passing and failing: kept as sent | — |
| line length | 12-17 words 26/31 within the right framing (84 %) | 22-25 words 11/18 (61 %); above 25 never tried (`PAVO_LINE_WORDS`) |
| aspect | 9:16 7/8, 1:1 9/11 | 16:9 29/52: every face loss with the right framing was at 16:9 (4 of 16) |
| second figure, raised hands, busy garden | no lower rate (75 %, 91 %, 82 %) | — |
| pace, prompt length | no separation (≤ 2.75 w/s 75 % vs 73 %) | — |

The same request digest passed 3 of 4 (M2, shot-probe 41629339290) and failed 4 of 4 (41652099686): those four are
generation variance, not wording, and are why a visual defect still takes the one second generation below.

**Audio.** The input audio is our exact Kokoro line as `episode_build.lines_step` cuts it, with no added silence
(`pavo_prompt.TAIL_PAD` = 0: no passing generation had a pad; the E290 0.3 s pad was never sent). The kept clip
carries that same WAV (E287) and is cut at the last word in the edit (E273/E282); the request digest records
`tail_pad` (the builder version), so an approved legacy clip keeps its request.

**Pace before any probe.** A Keeper line whose clip retime (`talk_retime`) would speed it past E277's band within
E288's one 10 % slowing is refused (`PAVO_LINE_PACE`); a reflection keeps `REFLECTION_PACE`.

**Lessons.** `migration/strategy/pavo_lessons.md` is read before any Pavo request (`pavo_prompt.build` refuses a
missing or malformed file, `PAVO_LESSONS_INVALID`). `reflection_shorts.py scaffold` builds its segments the same way.

**Generation cap and fallback (E264, owner: no rework; E287).** A talking or voice-over shot plans `TALK_ATTEMPTS = 1`
generation and takes a second only when the first has a visual defect (`episode_build.visual_defect`; the ceiling every
budget fits is `TALK_ATTEMPTS_MAX = 2`), at most 1 shot-probe round (`TALK_PROBE_ROUNDS_MAX`; the dispatch
guard and `probe_ids` refuse `attempts` above 1 for it), so one shot costs at most 2 generations a run and three
talking shots at most 6 (`long_preflight.planned_units(..., worst=True)`). When a talking Keeper shot fails its
checks on both generations, the shot falls back to the Keeper voice-over on reviewed still motion of an approved
Keeper still (DECISIONS "Battle plan to YPP", the fallback ladder below). Never queue more generations for it.

**Keep every generation; hard and soft defects (E266, owner 2026-11-02: generate, compare, use the best).**
shot-probe uploads EVERY generation that has a video, with its flags and measures (`hard_flags`, `words_flags`,
`soft_flags`, `measures` in the record), so approve-shot chooses among them by the real review; a refused clip was
never kept before, so there was nothing to compare. A shot is a failed shot only when every generation has a hard flag.
- HARD (never approvable): `FACE_NOT_FOUND`, a broken render (clip_check flags, `NO_VIDEO`), `MOUTH_TALKING` on a
  voice-over Keeper, `GOD_SHOT_FACE`, a policy block, and a clip that does not say our words.
- WORDS (legacy and `"ours"` clips only; not a refusal on the default Pavo-audio route): `AUDIO_NOT_OUR_LINE` is an RMS-envelope measure on Pavo's returned track: it fires on a
  line Pavo re-timed as well as on other words. A clip of a probe record made under `pavo_audio: "ours"` carries our own
  audio, so it cannot raise it (a words flag there means the mux broke: `SHOT_AUDIO_NOT_OURS`). For a legacy clip it
  stays hard until `episode_build.py speech-check` shows the pinned ASR heard the clip say the line; then
  approve-shot accepts it (`accepted_flags` + `words`, bound to the clip's sha256).
- SOFT (visible, not a bar): `MOUTH_NOT_IN_SYNC`, `AUDIO_OFFSET`, a small offset fixed in the edit (trim, hold, cut
  point, B-roll). approve-shot records them as `accepted_flags`; the build ignores exactly those on that clip.
The review floor (>= 9.5), the native review and the speech checks are unchanged.

**Keeper framing at 16:9 (E266, E130 for every 16:9 plan).** At 16:9 a seated "Medium shot" or "Medium close-up" Keeper
is drawn full body and his face is too small for the landmarker (`FACE_NOT_FOUND`: arc-01 long, then all 10
flood-ends-long generations). A 16:9 talking or voice-over Keeper prompt says "Close-up from the chest up, his face
large in the centre of the frame" (`plan_check.KEEPER_FRAMING_16X9`) and no medium, full or wide framing
(`KEEPER_FRAMING_16X9`, checked by plan_check and long_plan_check).

Approved reused clips are selected by their exact hashes and the supported request/reuse binding. Check current
revocations, aspect, character identity, source coverage and the changed context. Reuse does not imply generation
and does not create a new review score. Whether repeated imagery harms the episode is judged in the complete result.

## Pavo silent-clip standard

Owner, 2026-11-04 ~22:50Z: "Pode continuar fazendo com pavo mais coloca só vídeos sem narração.. e coloca a narração por
fora..". Pavo stays our video engine, but its clips are SILENT acting clips: nobody speaks on camera, there is no lip-sync,
and every spoken word (Keeper line, a character's KJV line, narration) is our Kokoro audio laid over the picture ("por
fora"). This replaces the talking-shot / Pavo-audio route (E290-E296) for new plans; Pavo's own audio is never used.

**Fields.** A silent shot carries `"pavo_mode": "silent"`, `"pavo_audio": "none"` and `"pavo": {"action", "setting",
"mood", "wardrobe"?, "view"?, "camera"?}`; its `prompt` is exactly `pavo_prompt.build`'s (`PAVO_PROMPT_NOT_STANDARD`
otherwise). `action` is what the character does or how he reacts (looks, works, walks, kneels, gestures), lower case, no
full stop; `view` is `frontal` (default, the Keeper's established mouth-closed narration look), `three-quarter` or
`profile`; `camera` is `static camera` (default), `slow push-in` or `slow pan`. The builder fills
`pavo_prompt.TEMPLATE_SILENT` (`SILENT_VERSION` `pavo-silent-v1`; the talking `VERSION` does not move, approved digests carry it):

> Image 1 is *the narrator | Noah*. *STYLE* Close-up from the chest up, his face large in the centre of the frame |
> Medium close-up, static camera. *Name*, *look*, *wardrobe*, seen in profile, centred in the frame, *action*, his mouth
> closed. *setting* *Mood.* [*period setting, exclusion*] No talking, no lip movement, no dialogue. No text, no logos.

Framing, identity, setting, mood and period sentences are the passing talking prompt's (E293); only the speech clause is
replaced by an action and the silence sentence. The same character reference as Image 1 (the Keeper's `talk_refs` frame,
a character's approved refs); the character stays "centred in the frame"; no text or logos; God is never shown
(`PAVO_SILENT_GOD`, and `pavo_prompt.field_problems` refuses him as the speaker).

**Refusals** (`plan_check`, `pavo_prompt`, `episode_build.request`): `PAVO_SILENT_SPEECH` (the prompt or a field asks for
speech or lip-sync: speak, say, words, audio, lips moving, sing, shout...), `PAVO_SILENT_FRONTAL` (a CHARACTER's line is
voiced over a clip in which he is not visibly mouthing it: working, looking away, three-quarter or profile, never a
frontal face or a look into the lens), `PAVO_SILENT_AUDIO` (`pavo_audio` is `"none"`, never `"pavo"` or `"ours"`),
`PAVO_SILENT_FRAMES` (a silent clip is Pavo's video from the references, never a plain still, a first/last frame or a
window), `PAVO_SILENT_SECONDS` (a character's silent clip is 4-12 s; beyond that it would be a still).

**Coverage.** The E290 hook, character-line and Keeper-line gates are satisfied by a silent Pavo clip of that character
under the line (`plan_check.pavo_silent`); a plain still, a clip without the builder's fields, God's sky or a hand-written
prompt still fails them. A silent Keeper shot is a voice-over Keeper shot with the new template (his clip covers his line
and the gap, slowed at most `MAX_SLOW`, his words from the voice track); a silent character shot is a speaking scene
shot (`speaker` + `line` + `characters` [him] + `seconds`) whose line is his Kokoro voice (`characters.voice`).

**Checks.** Visual gates stay: clip checks (artifacts), the face (`FACE_NOT_FOUND`), and no speech-like mouth motion while
our line plays: `lipsync_check --still-mouth` measures the lip opening over the whole clip, a superset of the line's time, so
`MOUTH_TALKING` is a hard flag (`episode_build.silent_mouth_flags`). `MOUTH_NOT_CLOSED` (an acting mouth may breathe) and the
missing face of a `profile` view (the landmarker reads frontal faces) are NOT flags: they are `silent_warnings`
(`WARN_MOUTH_NOT_CLOSED`, `WARN_FACE_NOT_FOUND_PROFILE`) in the clip's measures for the reviewer's real look, which stays the
authority. No SyncNet, no `speech-check`, no words flag exist for a silent clip.

**Generation.** The request sends no audio and `sound: false`; Pavo's returned track is stripped at download. One generation
per line per prompt revision (`PROBE_SAME_PROMPT`; a second only for a visual defect inside the run, `TALK_ATTEMPTS_MAX`), one
probe round, at the exact zero-credit quote. Probe records keep the template version (`request.silent`), so a silent clip is
not "older" than the talking template. `PROBE_PAVO_AUDIO_OURS` never refuses a silent shot.

## Keeper lip-sync (our audio)

Owner, 2026-11-05: "No guardião eu quero lixo sync pra ele falar.. verifique algo gratuito e de qualidade" (lip-sync). Scope
(owner, same day): the hook, the character-speech moments and the Keeper closing are all Pavo video; lip-sync of our Kokoro
audio onto Pavo is for the Keeper ALWAYS and for a character's line WHEN NEEDED. Quality must be good, but the bar is "good
enough to publish", not perfect (owner: AI speech and lip-sync never look exactly human; use the best free model's result, a slightly imperfect mouth is no reason to reject or regenerate). The gates rule out only clearly broken output: wrong mouth or lag the viewer notices and a frozen face (the existing SyncNet window and floor, confidence 2.7, not raised), a missing face, visible artifacts (`clip_check`). The Keeper
SPEAKS on camera and every word is ours: the Keeper shot is a Pavo SILENT frontal clip (the standard above, `view`
"frontal", mouth closed) plus a lip-sync of our Kokoro line onto it. Pavo never hears the line, so it cannot garble it.
Research and numbers: `evidence/research/KEEPER-LIPSYNC-2026-11-05.md`.

- **Plan field.** `"lipsync": "musetalk-1.5"` on a silent Keeper shot (`pavo_mode` "silent", `pavo.view` frontal). `plan_check`
  refuses `LIPSYNC_MODEL` (any other model: Wav2Lip is non-commercial, LatentSync is the GPU route), `LIPSYNC_VIEW` (not
  frontal), `LIPSYNC_SPEAKER_ONLY` (God is never shown; a scene with no spoken line has no mouth) and `LIPSYNC_NEEDS_SILENT`. A
  lip-synced character line may face the camera (`PAVO_SILENT_FRONTAL` does not apply to it); a character line without
  `lipsync` keeps that refusal.
- **Make it.** The silent clip is probed and approved as always (`shot-probe.yml`, still-mouth evidence). Then `lipsync.yml`
  (dispatch; the clip by sha256 and our 44.1 kHz mono WAV by sha256) runs MuseTalk 1.5 at the pinned commit on the free Actions
  CPU: 2-4.7 minutes of runner per second of picture (runner speed varies 2x), so keep the clip to 8 s or less (16-37 min, far inside the 6 h job). Output: `keeper-lipsync.mp4` (our
  line bit-exact as the only audio), `report.json`, frame sheets.
- **Gates (unchanged thresholds, `keeper_lipsync.py` repeats none of them).** The silent source passes `--still-mouth`
  (`LIPSYNC_SOURCE_MOUTH_TALKING`, `LIPSYNC_SOURCE_FACE_NOT_FOUND`); the result passes `lipsync_check` (SyncNet offset in
  -3..0 and confidence >= 2.7, face in >= 80 % of frames, audio = our line), `clip_check`, `pavo_audio.assert_ours`, and the
  picture outlasts the spoken line (`LIPSYNC_LINE_CUT`). The same silent clip with the line over it is measured as the
  control. A flag stops the shot; nothing is relabeled.
- **What the measures do not say.** First tests: offset 0, confidence 3.1 (Pavo-native lips read 6.8-8.6): it passes with a
  thin margin and the lower face is a soft 256 px patch. Only a reviewer who watches and hears the clip decides whether it
  holds 9.5 in context (mouth shape through the beard, softness, teeth, the join at the edit); the SyncNet pass is a floor.
- **Not wired yet.** `episode_build` still treats a silent Keeper clip as a voice-over (`MOUTH_TALKING` is a hard flag on it):
  the lip-synced clip enters through its own review and an `approve-shot` that records the SyncNet gate in place of the
  still-mouth gate; that change is the next step if the owner accepts the look.

## Keeper voice-over: authorized Plan B

A Keeper shot may explicitly carry `voiceover:true`. It shows him silent, with his lips closed, while the accepted
narration plays as voice-over. The current Genesis09 plan permits this mode. A Keeper shot without that flag is a
talking shot and must pass its actual speech/lip-sync checks.

- Keep the approved look/wardrobe and the appropriate `talk_refs` frame. The prompt says his lips are closed and
  he is silent; it names no speech. He faces the lens with his head level and a static camera.
- This request sends no input audio and requests no speech. Strip incidental provider audio. The original voice
  track carries his words and captions unchanged.
- Use the approved still-mouth source and its matching evidence. The existing `lipsync_check.py --still-mouth`
  tests mouth motion, sustained opening and face coverage. Its recorded failures remain failures.
- The established checks include face coverage ≥80%, no talking-window motion above the existing threshold and
  no sustained open mouth after the allowed settling period. The implementation, calibration and exact tool
  version determine the result; never replace them with an asserted boolean.
- The regular build uses one unbroken source from its start, with at most the existing 1.3 slowdown and no loop.
  The line plus its actual gap/tail must fit the source coverage rule. Preserve the audio; a replacement needs
  its own actual visual coverage and contextual check.
- This mode keeps the same placement, ≤25% shares, story purpose and 9.5 source/final quality requirements.
  It is a legitimate presentation choice, not a passing label for a rejected talking clip.

The preflight's still-mouth probe requirement belongs to the exact prompt/reference. Reuse existing matching
qualified probes and approved footage; do not generate replacements merely because the next executor starts.

## Existing build and review order

For a regular episode: `plan_check.py --strict` → measured voice/timeline and references → source probes/review →
`approve-shot` or the supported source approval → current preflight/verify-preflight → `episode.yml` assembly →
composed technical checks → complete actual audiovisual review → episode record/check-record →
`publish-episode.yml` → public/processed receipt.

The source probe owns bounded generation, shared quota and zero quote. Assembly downloads only the approved bytes
and checks them again; it does not regenerate them. A failed probe is diagnosed before any authorized retry.
An imported edit resumes at its missing qualification and preserves accepted inputs through the existing import
route. Detailed command interfaces and shared execution are in `../../OPERATIONS.md`.
