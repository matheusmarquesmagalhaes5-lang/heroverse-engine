"""Guards of the unofficial Google Flow runner: quote required, daily cap, free credits, cool-down, idempotency,
series prompt rules and the sanitized public ledger. No browser, no network."""
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_core as core  # noqa: E402

PARAMS = {"model": "veo-3.1-lite", "seconds": 8, "resolution": "720p", "aspect": "16:9", "mode": "text",
          "outputs": 1}
PROMPT = "The Keeper, an old scribe, sits by a small fire at night, centred in the frame, his mouth closed."
T0 = core.datetime(2026, 11, 5, 15, 0, tzinfo=core.timezone.utc)


def quoted(ledger=None, at=T0, cost=10, left=50, params=PARAMS):
    ledger = ledger or core.empty_ledger()
    return ledger, core.record_quote(ledger, dict(params), cost, left, "free", at)


class Quote(unittest.TestCase):
    def test_generate_without_quote_is_refused(self):
        ledger = core.empty_ledger()
        for qid in (None, "", "q-20261105-150000-abcd"):
            with self.assertRaises(core.FlowStop) as e:
                core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
            self.assertEqual(e.exception.code, "QUOTE_REQUIRED")

    def test_stale_quote_is_refused(self):
        ledger, qid = quoted()
        core.check_generate(ledger, qid, PARAMS, PROMPT, T0 + timedelta(minutes=14))
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0 + timedelta(minutes=16))
        self.assertEqual(e.exception.code, "QUOTE_STALE")

    def test_quote_for_another_setting_is_refused(self):
        ledger, qid = quoted()
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, dict(PARAMS, aspect="9:16"), PROMPT, T0)
        self.assertEqual(e.exception.code, "QUOTE_MISMATCH")

    def test_live_cost_change_is_refused(self):
        ledger, qid = quoted()
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0, live_cost=20, live_credits_left=50)
        self.assertEqual(e.exception.code, "QUOTE_CHANGED")

    def test_quote_is_used_once(self):
        ledger, qid = quoted()
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        core.mark_acknowledged(ledger, jid, True)
        core.reconcile(ledger, jid, "COMPLETED", T0)
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0 + timedelta(minutes=5))
        self.assertEqual(e.exception.code, "QUOTE_USED")

    def test_unreadable_cost_is_no_quote(self):
        with self.assertRaises(core.FlowStop) as e:
            quoted(cost=None)
        self.assertEqual(e.exception.code, "QUOTE_UNREADABLE")
        self.assertIsNone(core.parse_cost("Veo 3.1 - Lite"))
        self.assertIsNone(core.parse_cost("10 credits or 20 credits"))
        self.assertEqual(core.parse_cost("Veo 3.1 - Lite  10 credits"), 10)

    def test_only_one_output_and_allowed_models(self):
        for bad, code in (({"outputs": 2}, "OUTPUTS_NOT_ONE"), ({"model": "veo-3.1-quality"}, "MODEL_NOT_ALLOWED"),
                          ({"seconds": 6}, "DURATION_NOT_ALLOWED"), ({"resolution": "1080p"}, "RESOLUTION_NOT_ALLOWED")):
            with self.assertRaises(core.FlowStop) as e:
                core.check_params(dict(PARAMS, **bad))
            self.assertEqual(e.exception.code, code)


class Credits(unittest.TestCase):
    def test_cost_beyond_credits_left_is_refused(self):
        ledger, qid = quoted(left=8)
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(e.exception.code, "CREDITS_SHORT")

    def test_unread_credits_are_refused(self):
        ledger, qid = quoted(left=None)
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(e.exception.code, "CREDITS_UNREADABLE")

    def test_never_more_than_the_free_daily_credits(self):
        # a balance above 50 (e.g. paid credits) still never lets us spend more than 50 in a day
        ledger = core.empty_ledger()
        ledger["days"][core.day_of(T0)] = {"generations": 1, "credits": 45}
        ledger, qid = quoted(ledger, left=500)
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(e.exception.code, "FREE_CREDITS_EXCEEDED")

    def test_credits_left_parsing(self):
        self.assertEqual(core.parse_credits_left("AI credits: 50"), 50)
        self.assertEqual(core.parse_credits_left("40 credits left"), 40)
        self.assertIsNone(core.parse_credits_left("Flow"))


class DailyCap(unittest.TestCase):
    def test_fifth_generation_of_the_day_is_refused(self):
        ledger = core.empty_ledger()
        ledger["days"][core.day_of(T0)] = {"generations": 4, "credits": 12}
        ledger, qid = quoted(ledger, cost=3)
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(e.exception.code, "DAILY_CAP")

    def test_next_day_is_free_again(self):
        ledger = core.empty_ledger()
        ledger["days"][core.day_of(T0 - timedelta(days=1))] = {"generations": 4, "credits": 40}
        ledger, qid = quoted(ledger)
        core.check_generate(ledger, qid, PARAMS, PROMPT, T0)

    def test_owner_may_lower_the_cap(self):
        ledger, qid = quoted()
        with mock.patch.dict(os.environ, {"FLOW_DAILY_CAP": "0"}):
            with self.assertRaises(core.FlowStop) as e:
                core.check_generate(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(e.exception.code, "DAILY_CAP")

    def test_submission_counts_before_the_click(self):
        ledger, qid = quoted()
        core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(core.today_usage(ledger, T0), (1, 10))


class Cooldown(unittest.TestCase):
    def test_block_texts(self):
        self.assertEqual(core.blocked("We noticed unusual activity")[0], "CHALLENGE")
        self.assertEqual(core.blocked("Please complete the CAPTCHA")[0], "CHALLENGE")
        self.assertEqual(core.blocked("You're out of credits. Come back tomorrow")[0], "LIMIT")
        self.assertEqual(core.blocked("2-Step Verification")[0], "LOGIN")
        self.assertIsNone(core.blocked("Create a scene with Veo"))

    def test_cooldown_lasts_24_hours(self):
        ledger, qid = quoted()
        core.start_cooldown(ledger, "CHALLENGE", "unusual activity", T0)
        for later in (timedelta(minutes=1), timedelta(hours=23, minutes=59)):
            with self.assertRaises(core.FlowStop) as e:
                core.check_generate(ledger, qid, PARAMS, PROMPT, T0 + later)
            self.assertEqual(e.exception.code, "COOLDOWN")
        ledger2, qid2 = quoted(ledger, at=T0 + timedelta(hours=24, minutes=1))
        core.check_generate(ledger2, qid2, PARAMS, PROMPT, T0 + timedelta(hours=24, minutes=2))


class Idempotency(unittest.TestCase):
    def test_uncertain_submission_blocks_and_is_never_retried(self):
        ledger, qid = quoted()
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        self.assertEqual(core.mark_acknowledged(ledger, jid, False), "UNCERTAIN")
        ledger, qid2 = quoted(ledger, at=T0 + timedelta(minutes=10))
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid2, PARAMS, PROMPT, T0 + timedelta(minutes=10))
        self.assertEqual(e.exception.code, "JOB_NOT_RECONCILED")
        # a read that does not find it keeps it UNCERTAIN; a read that finds it reconciles it
        self.assertEqual(core.reconcile(ledger, jid, "ABSENT", T0), "UNCERTAIN")
        self.assertEqual(core.reconcile(ledger, jid, "COMPLETED", T0), "COMPLETED")
        core.check_generate(ledger, qid2, PARAMS, PROMPT, T0 + timedelta(minutes=10))

    def test_running_job_blocks_a_new_one(self):
        ledger, qid = quoted()
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        core.mark_acknowledged(ledger, jid, True)
        ledger, qid2 = quoted(ledger, at=T0 + timedelta(minutes=5))
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid2, PARAMS, PROMPT, T0 + timedelta(minutes=5))
        self.assertEqual(e.exception.code, "JOB_NOT_RECONCILED")

    def test_pace_between_submissions(self):
        ledger, qid = quoted()
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        core.reconcile(ledger, jid, "FAILED", T0)
        ledger, qid2 = quoted(ledger, at=T0 + timedelta(minutes=1))
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid2, PARAMS, PROMPT, T0 + timedelta(minutes=1))
        self.assertEqual(e.exception.code, "WAIT_MIN_GAP")

    def test_terminal_job_is_not_reopened(self):
        ledger, qid = quoted()
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        core.reconcile(ledger, jid, "FAILED", T0)
        self.assertEqual(core.reconcile(ledger, jid, "RUNNING", T0), "FAILED")

    def test_ledger_round_trip_and_malformed_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "ledger.json"
            ledger, qid = quoted()
            core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
            core.save_ledger(path, ledger)
            self.assertEqual(core.load_ledger(path), ledger)
            path.write_text("{not json")
            with self.assertRaises(core.FlowStop) as e:
                core.load_ledger(path)
            self.assertEqual(e.exception.code, "LEDGER_UNREADABLE")


class Prompt(unittest.TestCase):
    def test_series_rules(self):
        self.assertEqual(core.prompt_problems(PROMPT + " No talking, no lip movement, no dialogue."), [])
        self.assertTrue(any(p.startswith("PROMPT_NOT_CENTRED") for p in core.prompt_problems("A man by a fire.")))
        self.assertTrue(any(p.startswith("PROMPT_ASKS_SPEECH")
                            for p in core.prompt_problems(PROMPT + " He speaks to the camera.")))
        self.assertTrue(any(p.startswith("PROMPT_GOD_FACE")
                            for p in core.prompt_problems("The face of God above the clouds, centred in the frame.")))
        self.assertTrue(any(p.startswith("PROMPT_GOD_UNGUARDED")
                            for p in core.prompt_problems("God over the waters, centred in the frame.")))
        self.assertEqual(core.prompt_problems("God shown only as light over the waters, never shown with a face, "
                                              "centred in the frame."), [])

    def test_refused_prompt_stops_generation(self):
        ledger, qid = quoted()
        with self.assertRaises(core.FlowStop) as e:
            core.check_generate(ledger, qid, PARAMS, "He talks to Noah.", T0)
        self.assertEqual(e.exception.code, "PROMPT_REFUSED")

    def test_sent_prompt_is_silent(self):
        sent = core.full_prompt(PROMPT)
        self.assertIn(core.SILENCE, sent)
        self.assertIn("mouth stays closed", sent)

    def test_silence_matches_the_pavo_standard(self):
        root = Path(__file__).resolve().parents[2]
        text = (root / "production/bible/pavo_prompt.py").read_text(encoding="utf-8")
        self.assertIn('SILENCE = "%s"' % core.SILENCE, text)

    def test_character_needs_a_reference(self):
        with self.assertRaises(core.FlowStop) as e:
            core.check_params(dict(PARAMS, character="keeper"))
        self.assertEqual(e.exception.code, "CHARACTER_NEEDS_REFERENCE")
        core.check_params(dict(PARAMS, character="keeper", mode="ingredients", ingredients=["k.jpg"]))


class Sanitize(unittest.TestCase):
    def test_public_copy_has_no_urls_or_identifiers(self):
        ledger, qid = quoted()
        ledger["project_url"] = "https://labs.google/fx/tools/flow/project/abc-123"
        jid = core.mark_submitting(ledger, qid, PARAMS, PROMPT, T0)
        ledger["jobs"][jid].update(baseline=["https://storage.example/x.mp4?sig=1"],
                                   media_url="https://storage.example/y.mp4?token=2", file=r"C:\HeroVerse\flow\a.mp4")
        ledger["cooldown_reason"] = "LOGIN: owner@example.com"
        out = json.dumps(core.sanitize(ledger))
        for leak in ("labs.google", "storage.example", "token=", "sig=", "owner@example.com", "C:"):
            self.assertNotIn(leak, out)
        self.assertIn("a.mp4", out)
        self.assertIn(jid, out)


if __name__ == "__main__":
    unittest.main()
