#!/usr/bin/env python3
"""E290: the one builder of every Pavo talking-shot prompt (PROMPT_GUIDE "Pavo talking-shot prompt standard").

Owner, 2026-11-03: "Pavo does EXACTLY what you tell it. The failure is the prompt's organization." A talking shot (the
Keeper, or a human character speaking a KJV line) gives structured fields in its plan shot, `"pavo": {...}`, and its
`prompt` is what `build` composes from them, in one fixed order:

  1. reference binding   "Image 1 is <the narrator | the character's name>."
  2. style               the series' style line (STYLE)
  3. framing             chest-up, face large, centred, static camera (KEEPER_FRAMING_16X9 for the Keeper)
  4. identity            the character bible's look word for word, plus one wardrobe variant word for word
  5. setting and light   the shot's `setting` sentence; a scene also states its period's setting sentence
  6. action              speaks the words of the audio clip; lips move only while the voice speaks; mouth closed and
                         still before the first word and after the last; no extra words, no humming, no mouthing after
  7. emotion             one adjective and one gaze direction (the Keeper always looks straight into the camera)
  8. negatives           no text, no logos, no second person, no hand over the mouth, no head turn away; a scene
                         also states its period's exclusion sentence

Fields: {"emotion": "grave", "setting": "Night in the open desert, ... behind him.", "wardrobe": "fire",
         "gaze": "straight into the camera"}  (wardrobe: a key of the speaker's characters.json `wardrobe`, required for
the Keeper; gaze: one of GAZES, the Keeper's is fixed).

The input audio of such a shot is our exact Kokoro line with TAIL_PAD seconds of clean digital silence after the last
word (episode_build.lines_step, `tail_pad`), the line the tail mumbles were seen after. Production reads LESSONS before
writing any Pavo request: `build` refuses while the file is missing or malformed.

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

VERSION = "pavo-talk-v1"
LESSONS = ROOT / "migration/strategy/pavo_lessons.md"
STYLE = "Painterly cinematic realism with Old-Master light, one warm grade, cinema camera, fine film grain."
FRAMING = ("Close-up from the chest up, {pron} face large in the centre of the frame, static camera, the speaker "
           "centred in the frame.")
ACTION = ("{Subj} speaks the words of the audio clip, {pron} lips moving in sync with the voice; {pron} lips move only "
          "while the voice speaks, {pron} mouth closed and still before the first word and after the last word, no "
          "extra words, no humming, no mouthing after the line.")
EMOTION = "{Subj} holds {pron} head level and looks {gaze}, with a {emotion} look."
NEGATIVES = "No text, no logos, no second person, no hand over the mouth, no head turn away."
GAZES = ("straight into the camera", "just past the camera", "up toward the sky", "down toward the ground")
KEEPER_GAZE = "straight into the camera"
KEEPER_SETTINGS = {   # the Keeper's own place and light for each wardrobe variant (his look and wardrobe: characters.json)
    "fire": "Night in the open desert, the campfire's warm flicker on his face, deep blue darkness and stars behind him.",
    "study": "Night in the lamp-lit room, warm lamplight on his face, deep shadow behind him."}
TAIL_PAD = 0.30            # seconds of digital silence after the last word of the input audio
TAIL_PAD_MARGIN = 0.05     # the padded line stays at least this much shorter than the clip (mux_ours cuts at the picture)
FIELDS = ("emotion", "setting", "wardrobe", "gaze")
ADJECTIVE = re.compile(r"^[a-z]+(?:-[a-z]+)?$")
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
    if not isinstance(f.get("emotion"), str) or not ADJECTIVE.fullmatch(f["emotion"]):
        out.append(f"PAVO_FIELDS_INVALID {sid} (`emotion` is one lower-case adjective, e.g. \"grave\")")
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
    """The prompt of a standard talking shot, from its `pavo` fields, in the fixed order of this module."""
    import plan_check
    chars = chars if chars is not None else ch.registry()
    lessons()
    bad = field_problems(shot, chars, plan)
    if bad:
        raise SystemExit(bad[0])
    f, who = shot["pavo"], speaker(shot)
    c = chars[who]
    pron = c.get("pronoun", "his")
    subj = SUBJECT.get(pron, "He")
    label = "the narrator" if who == ch.NARRATOR else c.get("name", who)
    identity = f"{label[0].upper()}{label[1:]}, {c['look']}"
    if f.get("wardrobe"):
        identity += f", {c['wardrobe'][f['wardrobe']]}"
    setting = f["setting"].strip()
    negatives = NEGATIVES
    if shot.get("kind") == "scene":
        per = plan_check.period(plan)
        if per:
            setting += " " + per["setting"]
            negatives += " " + per["exclude"]
    parts = [f"Image 1 is {label}.", STYLE, FRAMING.format(pron=pron), identity + ".", setting,
             ACTION.format(Subj=subj, pron=pron),
             EMOTION.format(Subj=subj, pron=pron, gaze=f.get("gaze", KEEPER_GAZE), emotion=f["emotion"]), negatives]
    return " ".join(parts)


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
