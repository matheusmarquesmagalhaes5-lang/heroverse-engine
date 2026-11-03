# Pavo lessons: what worked, what failed (daily, evidence-linked)

Owner, 2026-11-03: "Learn every day, so there is no rework." Production reads this file before writing any Pavo request
(`pavo_prompt.build` refuses while it is missing or malformed). Inteligência Viva appends the day's probe and review
outcomes after each run, with run ids: `python3 migration/production/bible/pavo_prompt.py lesson DATE KIND TEXT EVIDENCE`.

Format (checked by `test_pavo_prompt.py`): one `## YYYY-MM-DD` section per day, dates in order; each lesson is one line
`- **worked|failed|rule** <one short lesson> Evidence: <run id, ERRORS id or path>`. A lesson is a measured outcome,
never an intention. A rule here never loosens a gate; SYSTEM, PROMPT_GUIDE and ERRORS stay the authority.

## 2026-11-02
- **failed** Seated "Medium shot" Keeper prompts at 16:9 drew him full body; the face was too small for the landmarker (FACE_NOT_FOUND on every generation). Evidence: E266, runs 41423359803 and 41436544195
- **worked** Chest-up framing ("Close-up from the chest up, his face large in the centre of the frame") gave k-insight and k-close clips with no flags. Evidence: shot-probe 41534197400, evidence/shots/flood-ends-long/41534197400.json
- **failed** A 23-word, three-sentence Keeper line (k-bow) came back with garbled and dropped words on both generations. Evidence: E272, shot-probe 41534197400

## 2026-11-03
- **failed** Tail mumbles: Pavo fills the clip time after our last word with extra speech ("you mealy", a second "own bow", "for carried"). Evidence: E282, reflection-shorts run 41630141252
- **failed** Word swaps and inserted words on Pavo's returned (re-synthesized) track, 4 of 4 genesis-10 Keeper clips. Evidence: shot-probe 41574608645, evidence/shots/genesis-10-short/speech/
- **worked** Our exact Kokoro WAV over Pavo's picture (E287): 13 of the 16 clips rejected only for words or audio hold SyncNet sync with our audio. Evidence: E287, PR #751, evidence/pavo-audio-eval/20261103.json
- **worked** Reflection 1 clips k-r1, k-r2 and k-r4 re-judged on our audio passed strict sync and face with no new generation. Evidence: shot-remux run 41654835246
- **failed** Pace was found only at render time (169 wpm, then 178 wpm with clips cut at the last word), after the clips were made. Evidence: E277, E286, reflection-shorts run 41643668889
- **failed** A small hooded firelit face was lost by the tracker at its default confidence (face share 0.71), a false hard flag on a good clip. Evidence: E273, shot-probe 41547308176
- **failed** Two Shorts of one long were planned on overlapping footage and speech (reflection top clip inside the rainbow cut). Evidence: E279
- **rule** The hook, every on-screen character line and every Keeper line are Pavo talking shots; prompts come only from `pavo_prompt.build`, with a 0.3 s silence pad after our line. Evidence: E290
- **rule** What Pavo generates is used: tails are trimmed at the last word (E273), joins crossfade inside silence (E272), a fast set is retimed by at most 10 % (E286); a second generation only for a visual defect. Evidence: E287, E290
- **rule** Close the silences between Keeper clips to 0.3 s at most: a clip's picture outlasts our line, so the joins leave 0.9-1.3 s of dead mix that reads as a dropout. Evidence: reflection-shorts run 41660551928, local-review 41661153948
- **rule** Re-measure sync (SyncNet and face) on the clips AFTER any retime (E286): the x0.92 slowing of reflection 1 was applied but only the unslowed clips were measured. Evidence: reflection-shorts run 41660551928, shot-remux run 41654835246
- **rule** A line that already has stored generations is judged with shot-remux on our audio, never probed again: M2 re-probed its Keeper hook and close (4 generations a line), then the stored clips k-hook (conf 5.8) and k-close (conf 6.0) passed strict sync and face with no flags. shot-probe now refuses it unless a visual-defect flag is on all stored generations. Evidence: E292, shot-remux run 41670811661, shot-probe 41629339290 and 41652099686
- **rule** Keeper prompts at 16:9 and 1:1 say "Close-up from the chest up, his face large in the centre of the frame" (22 of 31 passed); "Medium shot" lost the face 10 of 10 and a 16:9 "Medium close-up" 2 of 2; 9:16 and characters say "Medium close-up" (7 of 8, 20 of 20 faces). Evidence: E293, evidence/pavo-prompt-analysis/20261103.json
- **rule** Every Pavo talking prompt is pavo_prompt.TEMPLATE, the passing prompt of record word for word (reproduces flood k-insight/k-close/k-hook, M2 hook, k-r1, genesis-09 k-close); no wording that no generation used (v1's added clauses were never sent). Evidence: E293, evidence/pavo-prompt-analysis/20261103.json
- **rule** Emotion is one look of record with its mood sentence (calm kind / Tender and grave, gentle questioning / Warm and searching, grave, intent / Hushed and urgent, warm expectant / Warm and expectant); negatives stay "No text, no logos." Evidence: E293, pavo_prompt.PASSING_LOOKS
- **rule** Keeper lines of 12-17 words passed 26 of 31 and 22-25 words 11 of 18; write 12-17, never above 25 (PAVO_LINE_WORDS). Evidence: E293, evidence/pavo-prompt-analysis/20261103.json
- **rule** The input audio is our line as cut, no added silence (TAIL_PAD 0): no passing generation had a pad; the tail is cut in the edit and the clip carries our audio. Supersedes the 0.3 s pad rule above. Evidence: E293, E287, E273
- **failed** The identical M2 hook/close request passed 3 of 4 in one run and 0 of 4 in the next (two faces lost, two mouths 10-14 windows off): variance at one wording, so a visual defect keeps its one second generation. Evidence: shot-probe 41629339290 and 41652099686
- **rule** Owner 2026-11-03: Pavo clips in full with Pavo's own audio; Kokoro only over stills Evidence: owner order 2026-11-03, pavo_audio.py route pavo (default), supersedes E287's default
- **rule** A hand-written Keeper prompt is not the current template: a stored line may take ONE new generation on pavo_prompt.build when all its stored generations are older (record request.audio.tail_pad), never a second; the 22-23 word M2 lines came back with wrong words on Pavo's own track, so the lines were cut to 16-17 words first. Evidence: E292, speech-check 41636192512, DECISIONS 2026-11-03 M2 Keeper
- **failed** Pavo's own returned audio garbled the line in 5 of 7 Babel clips (builder KJV 'let us make brick' heard as 'let us be more more ghoulie'; Keeper insights with invented words); only the hook and one builder line came back exact. Words are judged by the pinned ASR before any clip is approved. Evidence: shot-probe run 41714272567, speech-check run 41729891998, evidence/shots/genesis-10-11-long/speech/
- **worked** The E293 template gave 8 of 8 first generations with a found face, no hard flag and SyncNet offset -1/-2 at confidence 7.4-9.7; builder clips kept the approved reference face in every frame. Evidence: shot-probe run 41714272567
- **rule** Per-shot pavo_audio ours (our Kokoro line over Pavo's picture, shot-remux, nothing generated) is used where the ASR shows Pavo's own track did not say the line; Pavo's own track stays where it said it exactly. Evidence: plans/genesis-10-11-long.json, OPERATIONS pavo_audio
