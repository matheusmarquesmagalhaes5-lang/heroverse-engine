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
