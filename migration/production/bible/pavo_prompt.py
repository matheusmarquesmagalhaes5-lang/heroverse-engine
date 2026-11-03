#!/usr/bin/env python3
"""E290/E293: the one builder of every Pavo talking-shot prompt (PROMPT_GUIDE "Pavo talking-shot prompt standard").

Owner, 2026-11-03: "There is no scenario where the clip does not pass. The issue is the PROMPT. Analyze: when it passed,
what was the prompt? Always model the prompt on the way it was done the time it passed." So `build` writes the PASSING
prompt of record word for word (evidence/pavo-prompt-analysis/20261103.json: 71 talking generations, 45 passed), never a
wording no generation has used. A talking shot (the Keeper, or a human character speaking a KJV line) gives structured
fields in its plan shot, `"pavo": {...}`, and `build` fills the one template (TEMPLATE) that passed:

  Image 1 is <the narrator | Noah>. <STYLE> <framing>, static camera. <The narrator | Noah>, <look>, <wardrobe>,
  <pose> speaks the words of the audio clip, <his> lips moving in sync with the voice, a <emotion> look. <setting>
  <Mood>.[ <period setting> <period exclusion>] No text, no logos.

  framing   the Keeper at 16:9 and 1:1 "Close-up from the chest up, his face large in the centre of the frame" (22 of 31
            passed; the seated "Medium shot" 0 of 10 and a 16:9 "Medium close-up" 0 of 2 lost his face); the Keeper at
            9:16 and every character "Medium close-up" (7 of 8 Keeper; 20 of 20 character pictures kept the face)
  pose      16:9/1:1 "centred in the frame holds his head level and looks <gaze> and"; 9:16 "holds his head level, looks
            <gaze> and" (the exact clause of each aspect's passing prompts)
  emotion   a look of record (PASSING_LOOKS, its mood sentence by default) or a short look with an explicit `mood`

Fields: {"emotion": "calm kind", "setting": "Night in the open desert, ... behind him.", "wardrobe": "fire",
         "gaze": "straight into the camera", "mood": "Tender and grave"}  (wardrobe: a key of the speaker's
characters.json `wardrobe`, required for the Keeper; gaze: one of GAZES, the Keeper's is fixed; mood: optional for a
look of record). A line above LINE_WORDS_MAX words is refused (none of record passed or was tried above it).

The input audio of such a shot is our exact Kokoro line as lines_step cuts it (TAIL_PAD 0: every passing generation had
no added silence; the clip is cut at the last word, E273/E282, and carries our audio, E287). Production reads LESSONS
before writing any Pavo request: `build` refuses while the file is missing or malformed.

usage: pavo_prompt.py lessons                       the parsed lessons (JSON), exit 1 when the file is malformed
       pavo_prompt.py lesson DATE KIND TEXT EVIDENCE   append one lesson (KIND worked|failed|rule) under DATE
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "migration/production/characters"))
import characters as ch  # noqa: E402

VERSION = "pavo-talk-v2"
LESSONS = ROOT / "migration/strategy/pavo_lessons.md"
EVIDENCE = "migration/evidence/pavo-prompt-analysis/20261103.json"
STYLE = "Painterly cinematic realism with Old-Master light, one warm grade, cinema camera, fine film grain."
CHEST_UP = "Close-up from the chest up, {pron} face large in the centre of the frame"
MEDIUM_CLOSE_UP = "Medium close-up"
POSE = {"wide": "centred in the frame holds {pron} head level and looks {gaze} and",
        "9:16": "holds {pron} head level, looks {gaze} and"}
ACTION = "speaks the words of the audio clip, {pron} lips moving in sync with the voice"
NEGATIVES = "No text, no logos."
TEMPLATE = ("Image 1 is {label}. {style} {framing}, static camera. {Label}, {identity}, {pose} {action}, a {emotion} "
            "look. {setting} {mood}.{period} {negatives}")
# the looks of the passing Keeper prompts of record, each with the mood sentence it was sent with
PASSING_LOOKS = {"calm kind": "Tender and grave", "gentle questioning": "Warm and searching",
                 "grave, intent": "Hushed and urgent", "warm expectant": "Warm and expectant",
                 "grave knowing": "Tender and grave"}
GAZES = ("straight into the camera", "just past the camera", "up toward the sky", "down toward the ground")
KEEPER_GAZE = "straight into the camera"
KEEPER_SETTINGS = {   # the Keeper's own place and light for each wardrobe variant (his look and wardrobe: characters.json)
    "fire": "Night in the open desert, the campfire's warm flicker on his face, deep blue darkness and stars behind him.",
    "study": "Night in the lamp-lit room, warm lamplight on his face, deep shadow behind him."}
TAIL_PAD = 0.0             # seconds of silence added after the last word: none, as in every passing generation (E293)
TAIL_PAD_MARGIN = 0.05     # the padded line stays at least this much shorter than the clip (mux_ours cuts at the picture)
LINE_WORDS_MAX = 25        # the longest passing line of record (flood k-insight); 12-17 words passed 26 of 31
FIELDS = ("emotion", "setting", "wardrobe", "gaze", "mood")
LOOK = re.compile(r"^[a-z]+(?:-[a-z]+)?(?:,? [a-z]+(?:-[a-z]+)?){0,2}$")
MOOD = re.compile(r"^[A-Z][a-z]+ and [a-z]+$")
SUBJECT = {"his": "He", "her": "She", "its": "It"}
LESSON_DATE = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
LESSON_LINE = re.compile(r"^- \*\*(worked|failed|rule)\*\* (.+) Evidence: (.+)$")


def standard(shot):
    """The shot's prompt comes from the builder (it carries `pavo` fields)."""
    return isinstance(shot, dict) and isinstance(shot.get("pavo"), dict)


def speaker(shot):
    return ch.NARRATOR if shot.get("kind") == "keeper" else shot.get("speaker")


def tail_pad(speech_seconds, clip_seconds):
    """Seconds of silence appended to a standard shot's input audio: TAIL_PAD, never so much that the padded line
    reaches within TAIL_PAD_MARGIN of the clip's end (the kept clip's audio is the padded line, cut at the picture)."""
    return round(max(0.0, min(TAIL_PAD, clip_seconds - speech_seconds - TAIL_PAD_MARGIN)), 3)


def field_problems(shot, chars, plan=None):
    """[] or the reasons the shot's `pavo` fields cannot be built (PAVO_FIELDS_INVALID)."""
    f, sid, who = shot.get("pavo"), shot.get("id"), speaker(shot)
    if not isinstance(f, dict):
        return [f"PAVO_FIELDS_INVALID {sid} (a talking shot carries `pavo`: {', '.join(FIELDS)})"]
    out = []
    unknown = sorted(set(f) - set(FIELDS))
    if unknown:
        out.append(f"PAVO_FIELDS_INVALID {sid} (unknown field(s) {', '.join(unknown)})")
    c = chars.get(who) if isinstance(who, str) else None
    if not c or who == ch.GOD:
        return out + [f"PAVO_FIELDS_INVALID {sid} (speaker {who!r} is not a characters.json character: God is never shown)"]
    emotion, mood = f.get("emotion"), f.get("mood")
    if not isinstance(emotion, str) or not LOOK.fullmatch(emotion):
        out.append(f"PAVO_FIELDS_INVALID {sid} (`emotion` is a short lower-case look, e.g. \"calm kind\")")
    elif mood is None and emotion not in PASSING_LOOKS:
        out.append(f"PAVO_FIELDS_INVALID {sid} (`emotion` {emotion!r} is not a look of record ({', '.join(PASSING_LOOKS)}): "
                   "give its `mood` sentence too)")
    if mood is not None and (not isinstance(mood, str) or not MOOD.fullmatch(mood)):
        out.append(f"PAVO_FIELDS_INVALID {sid} (`mood` is \"<Adjective> and <adjective>\", e.g. \"Tender and grave\")")
    s = f.get("setting")
    if not isinstance(s, str) or not 20 <= len(s) <= 400 or not s.strip().endswith(".") or "Image" in s:
        out.append(f"PAVO_FIELDS_INVALID {sid} (`setting`: one or two sentences of place and light, 20-400 characters)")
    wardrobe = c.get("wardrobe") or {}
    if who == ch.NARRATOR and f.get("wardrobe") not in wardrobe:
        out.append(f"PAVO_FIELDS_INVALID {sid} (`wardrobe` is one of the Keeper's: {', '.join(sorted(wardrobe))})")
    elif f.get("wardrobe") is not None and f.get("wardrobe") not in wardrobe:
        out.append(f"PAVO_FIELDS_INVALID {sid} (`wardrobe` of {who}: {', '.join(sorted(wardrobe)) or 'none'})")
    gaze = f.get("gaze", KEEPER_GAZE)
    if gaze not in GAZES or (who == ch.NARRATOR and gaze != KEEPER_GAZE):
        out.append(f"PAVO_FIELDS_INVALID {sid} (`gaze` is one of {', '.join(GAZES)}; the Keeper looks {KEEPER_GAZE})")
    return out


def line_words(shot, plan):
    """The words of the shot's own line (a Keeper's narration lines, a character's `line`), [] when unknown."""
    if shot.get("kind") == "keeper":
        narration = (plan or {}).get("narration") or []
        text = " ".join(narration[i]["text"] for i in shot.get("lines") or []
                        if isinstance(i, int) and 0 <= i < len(narration) and isinstance(narration[i], dict)
                        and isinstance(narration[i].get("text"), str))
    else:
        text = shot.get("line") if isinstance(shot.get("line"), str) else ""
    return re.findall(r"[A-Za-z']+", text)


def lessons(path=None):
    """[{date, kind, text, evidence}] from the lessons file; SystemExit PAVO_LESSONS_INVALID when it is missing or a
    line breaks the structure (dated sections in order, each lesson a worked/failed/rule bullet with its evidence)."""
    path = Path(path) if path else LESSONS
    if not path.is_file():
        raise SystemExit(f"PAVO_LESSONS_INVALID {path.name} missing (production reads it before any Pavo request)")
    out, date, last = [], None, ""
    for n, line in enumerate(path.read_text().splitlines(), 1):
        m = LESSON_DATE.match(line)
        if m:
            if m.group(1) < last:
                raise SystemExit(f"PAVO_LESSONS_INVALID line {n}: dates go in order ({m.group(1)} after {last})")
            date = last = m.group(1)
            continue
        if line.startswith("- "):
            m = LESSON_LINE.match(line)
            if not m or date is None:
                raise SystemExit(f"PAVO_LESSONS_INVALID line {n}: '- **worked|failed|rule** <lesson> Evidence: <run id "
                                 "or path>' under a '## YYYY-MM-DD' heading")
            out.append({"date": date, "kind": m.group(1), "text": m.group(2), "evidence": m.group(3)})
    if not out:
        raise SystemExit(f"PAVO_LESSONS_INVALID {path.name} holds no lesson")
    return out


def build(shot, plan, chars=None):
    """The prompt of a standard talking shot: TEMPLATE, the passing prompt of record, filled from its `pavo` fields."""
    import plan_check
    chars = chars if chars is not None else ch.registry()
    lessons()
    bad = field_problems(shot, chars, plan)
    if bad:
        raise SystemExit(bad[0])
    words = line_words(shot, plan)
    if len(words) > LINE_WORDS_MAX:
        raise SystemExit(f"PAVO_LINE_WORDS {shot.get('id')} ({len(words)} words; no line above {LINE_WORDS_MAX} words "
                         f"passed or was tried, 12-17 words passed most often: {EVIDENCE})")
    f, who = shot["pavo"], speaker(shot)
    c = chars[who]
    pron = c.get("pronoun", "his")
    keeper = who == ch.NARRATOR
    aspect = (plan or {}).get("aspect_ratio", "9:16")
    label = "the narrator" if keeper else c.get("name", who)
    identity = c["look"] + (f", {c['wardrobe'][f['wardrobe']]}" if f.get("wardrobe") else "")
    framing = CHEST_UP.format(pron=pron) if keeper and aspect != "9:16" else MEDIUM_CLOSE_UP
    pose = POSE["9:16" if aspect == "9:16" else "wide"].format(pron=pron, gaze=f.get("gaze", KEEPER_GAZE))
    period = ""
    if shot.get("kind") == "scene":
        per = plan_check.period(plan)
        if per:
            period = f" {per['setting']} {per['exclude']}"
    return TEMPLATE.format(label=label, Label=label[0].upper() + label[1:], style=STYLE, framing=framing,
                           identity=identity, pose=pose, action=ACTION.format(pron=pron), emotion=f["emotion"],
                           setting=f["setting"].strip(), mood=f.get("mood") or PASSING_LOOKS[f["emotion"]],
                           period=period, negatives=NEGATIVES)


def append_lesson(date, kind, text, evidence, path=None):
    """Add one lesson under its date (a new '## DATE' section at the end when the date is new); the file is checked
    again after the write."""
    path = Path(path) if path else LESSONS
    lessons(path)
    line = f"- **{kind}** {text.strip()} Evidence: {evidence.strip()}"
    if not LESSON_LINE.match(line) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SystemExit("PAVO_LESSONS_INVALID the new lesson (DATE YYYY-MM-DD, KIND worked|failed|rule, TEXT, EVIDENCE)")
    body = path.read_text().rstrip("\n").split("\n")
    heads = [i for i, x in enumerate(body) if LESSON_DATE.match(x)]
    if heads and body[heads[-1]] == f"## {date}":
        body.append(line)
    else:
        body += ["", f"## {date}", line]
    path.write_text("\n".join(body) + "\n")
    return lessons(path)


def main(argv):
    if len(argv) == 2 and argv[1] == "lessons":
        print(json.dumps(lessons(), indent=1))
        return 0
    if len(argv) == 6 and argv[1] == "lesson":
        append_lesson(*argv[2:6])
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
