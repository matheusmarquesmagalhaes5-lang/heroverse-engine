"""Free defect scan: a detector only (WARN / INFO), CPU on the runner, no provider, no secret, never an approval."""
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = load('defect_scan', 'migration/production/bible/defect_scan.py')
WORKFLOW = (ROOT / '.github/workflows/defect-scan.yml').read_text()


class Speech(unittest.TestCase):
    def test_a_proper_name_spelled_differently_but_sounding_the_same_is_heard(self):
        # Babel calibration: small.en wrote 'Beybell' for the script's 'Babel.' (06:51, owner-approved master)
        self.assertEqual(D.soundex('Babel'), D.soundex('Beybell'))
        self.assertTrue(D.same_word('babel', 'beybell'))
        self.assertTrue(D.same_word('haran', 'heron'))
        self.assertFalse(D.same_word('brick', 'stone'))
        self.assertEqual(D.misses(['go', 'to', 'babel'], ['go', 'to', 'beybell']), [])

    def test_only_a_miss_every_decode_shares_is_a_warning(self):
        s = {'text': 'And they said one to another, Go to, let us make brick', 'start': 137.5, 'end': 142.3}
        slip = D.classify_speech(37, s, {'small.en': 'and they said one to another go to', 'medium.en': 'And they said one to another, Go to, let us make brick'})
        self.assertEqual([f['level'] for f in slip], ['INFO'])
        both = D.classify_speech(37, s, {'small.en': 'and they said one to another go to let us make stone',
                                         'medium.en': 'And they said one to another, Go to, let us make stone'})
        self.assertEqual([(f['level'], f['class']) for f in both], [('WARN', 'mispronunciation')])
        cut = D.classify_speech(37, s, {'small.en': 'and they said one to another go to', 'medium.en': 'and they said one to another go to'})
        self.assertEqual([(f['level'], f['class']) for f in cut], [('WARN', 'speech_cut')])

    def test_a_short_sentence_is_decoded_in_a_window_long_enough_for_whisper(self):
        samples = [0.0] * (16000 * 20)
        clip = D.window(samples, 10.0, 11.0)
        self.assertGreaterEqual(len(clip) / 16000, D.WINDOW_MIN - 0.01)
        self.assertEqual(len(D.window(samples, 2.0, 9.0)), int(16000 * (7 + 2 * D.WINDOW_PAD)))

    def test_only_sentences_the_full_pass_missed_are_rechecked(self):
        sents = [{'text': 'a b', 'start': 0.0, 'end': 1}, {'text': 'c d', 'start': 1.0, 'end': 2}, {'text': 'e', 'start': None, 'end': None}]
        cmp_ = {'garbled': [{'sentence': 1}], 'missing': [{'sentence': 2}], 'sentence_coverage': {0: 1.0, 1: 0.5, 2: 0.0}}
        self.assertEqual(D.candidates(sents, cmp_), [1])   # sentence 2 has no timing to cut a window from


class Loudness(unittest.TestCase):
    def log(self, values, step=0.1):
        return '\n'.join(f'[Parsed_ebur128_0 @ 0x1] t: {k * step:.4f}  TARGET:-23 LUFS    M:{v:.1f} S:{v:.1f}     I: -14.0 LUFS       LRA:   3.0 LU'
                         for k, v in enumerate(values))

    def test_the_framelog_is_parsed(self):
        rows = D.parse_framelog(self.log([-120.7, -20.0]))
        self.assertEqual(rows, [(0.0, -120.7, -120.7), (0.1, -20.0, -20.0)])

    def test_a_sudden_jump_mid_programme_warns_and_fades_from_silence_do_not(self):
        steady = [-16.0] * 100 + [-5.0] * 100 + [-16.0] * 100
        found = D.loudness_jumps(D.parse_framelog(self.log(steady)), 30.0)
        self.assertEqual([f['class'] for f in found], ['loudness_jump', 'loudness_jump'])
        self.assertTrue(all(f['level'] == 'WARN' for f in found))
        fade = [-70.0] * 100 + [-16.0] * 200
        self.assertEqual(D.loudness_jumps(D.parse_framelog(self.log(fade)), 30.0), [])
        gentle = [-16.0 + k * 0.02 for k in range(300)]
        self.assertEqual(D.loudness_jumps(D.parse_framelog(self.log(gentle)), 30.0), [])
        self.assertLess(D.max_jump(D.parse_framelog(self.log(gentle)), 30.0), 1.0)


class Picture(unittest.TestCase):
    def test_a_flash_frame_warns_and_a_cut_does_not(self):
        diffs = [(0.0, 0.0, 0.0)] + [(1.0, 1.0, 1.5)] * 50
        diffs[20] = (40.0, 38.0, 2.0)     # frame 20 unlike both neighbours, which match: a glitch
        diffs[30] = (45.0, 1.0, 45.0)     # a hard cut: the next frame matches the new shot
        found = D.flash_frames(diffs, 30.0)
        self.assertEqual([(f['class'], f['level'], f['t']) for f in found], [('visual_glitch', 'WARN', round(20 / 30, 2))])


class Mix(unittest.TestCase):
    def test_music_over_the_voice_of_one_sentence_warns(self):
        import numpy as np
        rate = 1000
        t = np.arange(rate * 4) / rate
        voice = 0.5 * np.sin(2 * np.pi * 50 * t)
        music = 0.05 * np.sin(2 * np.pi * 7 * t)
        music[2 * rate:] = 0.6 * np.sin(2 * np.pi * 7 * t[2 * rate:])   # the second sentence drowns
        sents = [{'text': 'one', 'start': 0.0, 'end': 2.0}, {'text': 'two', 'start': 2.0, 'end': 4.0}]
        heard = [{'t': 'one', 'start': 0.2, 'end': 1.8}, {'t': 'two', 'start': 2.2, 'end': 3.8}]
        found, stats = D.clash(voice, music, sents, heard, rate)
        self.assertEqual([(f['level'], f['t']) for f in found], [('WARN', 2.0)])
        self.assertEqual(stats['sentences'], 2)
        self.assertGreater(stats['rows'][0]['margin_db'], D.CLASH_INFO_DB)


class DetectorOnly(unittest.TestCase):
    def test_the_scan_never_approves_never_scores_and_holds_no_secret(self):
        src = (ROOT / 'migration/production/bible/defect_scan.py').read_text()
        for word in ('APPROVAL.json', 'prepublish_gate', 'machine_verdict', 'claude_review.json'):
            self.assertNotIn(word, re.sub(r'""".*?"""', '', src, flags=re.S), word)
        self.assertNotIn('secrets.', WORKFLOW)
        self.assertNotIn('upload-release', WORKFLOW)
        self.assertNotIn('gh release upload', WORKFLOW)
        self.assertIn('workflow_dispatch', WORKFLOW)
        self.assertNotIn('schedule:', WORKFLOW)
        self.assertRegex(WORKFLOW, r'permissions:\n  contents: read\n')
        self.assertNotIn('contents: write', WORKFLOW)

    def test_every_finding_is_warn_or_info_in_a_known_class(self):
        self.assertEqual(set(D.CLASSES), {'mispronunciation', 'garbled_word', 'speech_cut', 'loudness_jump',
                                          'music_voice_clash', 'visual_glitch', 'sync'})
        with self.assertRaises(AssertionError):
            D.finding(0, 'visual_glitch', 'FAIL', 'x')

    def test_the_workflow_verifies_the_same_pinned_files_the_module_names(self):
        L = D.lr
        self.assertIn(L.ASR['revision'], WORKFLOW)
        self.assertIn(L.ASR['files']['model.bin'], WORKFLOW)
        self.assertIn(D.SECOND_ASR['revision'], WORKFLOW)
        self.assertIn(D.SECOND_ASR['files']['model.bin'], WORKFLOW)
        self.assertIn(D.DEMUCS['weights'], WORKFLOW)
        self.assertIn(D.DEMUCS['weights_sha256'], WORKFLOW)
        self.assertIn(D.DEMUCS['package'], WORKFLOW)

    def test_the_master_is_hash_checked_and_removed(self):
        self.assertIn('sha256sum -c -', WORKFLOW)
        self.assertIn('rm -f -- "$RUNNER_TEMP/master.mp4"', WORKFLOW)


if __name__ == '__main__':
    unittest.main()
