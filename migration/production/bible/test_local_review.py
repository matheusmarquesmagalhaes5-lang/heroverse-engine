"""Local native review (E268): audio heard + picture seen on the runner, no provider, no credentials, no network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = load('local_review', 'migration/production/bible/local_review.py')
N = L.nr
FLOOD = 'migration/production/bible/plans/flood-ends-long.json'
FLOOD_SHA = '9a2d0f24e74c7117eedcbdd73992fbc284efb9402b6f82dba98f096a64635692'
WORKFLOW = (ROOT / '.github/workflows/local-review.yml').read_text()


def words(text, start=0.0, step=0.4):
    out, t = [], start
    for w in text.split():
        out.append({'word': w, 'start': round(t, 2), 'end': round(t + step * 0.8, 2)})
        t += step
    return out


def measures(**over):
    m = {'probe': {'duration': 100.0, 'has_audio': True, 'has_video': True},
         'audio': {'loudness': {'integrated_lufs': -14.2, 'lra': 5.0, 'true_peak_dbtp': -1.6},
                   'clipping': {'peak_dbfs': -1.6, 'peak_count': 1}, 'silences': [], 'balance': {'voice_over_music_db': 9.0, 'quiet_sentences': []},
                   'first_word_start': 0.6, 'last_word_end': 95.0, 'speech_gaps': [], 'sentence_starts': {}, 'timing': [],
                   'compare': {'coverage': 0.99, 'expected_words': 100, 'missing': [], 'extra': [], 'garbled': [], 'sentence_coverage': {}}},
         'video': {'freezes': [], 'black': [], 'scene_changes': [10.0, 20.0],
                   'frames': {'caption_samples_speaking': 20, 'caption_like_speaking_ratio': 0.9, 'duplicate_runs': []},
                   'pacing': {'longest_starts_at': 0.0, 'longest_without_change': 12.0}}}
    for k, v in over.items():
        a, b = k.split('__')
        m[a][b] = v
    return m


class Switch(unittest.TestCase):
    def test_e268_a_single_external_provider_cannot_block_the_native_review(self):
        # flood-ends-long run 41502101074: Gemini NATIVE_READBACK_PROVIDER_FAILED (Free Tier proof from the owner's PC)
        self.assertEqual(N.DEFAULT_PROVIDER, 'local')
        self.assertEqual(L.DEFAULT_PROVIDER, 'local')
        self.assertFalse(N.GEMINI_REQUIRED)
        self.assertIn('def poll(', (ROOT / 'migration/production/bible/native_review.py').read_text())   # the old provider stays
        self.assertNotIn('secrets.', WORKFLOW)
        self.assertNotIn('GEMINI', WORKFLOW)
        self.assertNotIn('free_tier', WORKFLOW)
        self.assertNotIn('receipt_certificate', WORKFLOW)
        self.assertNotIn('owner_review_authorized', WORKFLOW)

    def test_the_workflow_takes_the_same_plan_and_sha_inputs_and_writes_the_same_artifact(self):
        old = (ROOT / '.github/workflows/native-review.yml').read_text()
        for key in ('plan:', 'sha256:'):
            self.assertIn(key, old)
            self.assertIn(key, WORKFLOW)
        self.assertIn('name: native-review-public-evidence', WORKFLOW)
        self.assertIn('name: local-review-frames', WORKFLOW)
        self.assertIn('retention-days: 90', WORKFLOW)
        self.assertIn('local_review.py analyze', WORKFLOW)
        self.assertRegex(WORKFLOW, r'(?m)^run-name: "local-review: plan=\$\{\{ inputs.plan \}\} sha256=\$\{\{ inputs.sha256 \}\}"$', )

    def test_the_runtime_and_the_model_are_pinned(self):
        self.assertIn('faster-whisper==1.2.1', WORKFLOW)
        self.assertIn(L.ASR['revision'], WORKFLOW)
        self.assertIn(L.ASR['files']['model.bin'], WORKFLOW)
        self.assertEqual(len(L.ASR['revision']), 40)
        self.assertTrue(all(re.fullmatch(r'[0-9a-f]{64}', h) for h in L.ASR['files'].values()))
        for use in re.findall(r'uses: (\S+)', WORKFLOW):
            self.assertRegex(use, r'@[0-9a-f]{40}$')
        self.assertRegex(WORKFLOW, r'github.ref == .refs/heads/main')


class Script(unittest.TestCase):
    SENTENCES = [{'text': 'And God said unto Noah, Go forth of the ark.', 'start': 0.5, 'end': 4.0},
                 {'text': 'Bring forth with thee every living thing.', 'start': 4.5, 'end': 8.0}]

    def heard(self, text):
        return L.flatten_heard([{'words': words(text, 0.5)}])

    def test_a_perfect_reading_matches_every_word(self):
        c = L.compare(self.SENTENCES, self.heard('And God said unto Noah go forth of the ark Bring forth with thee every living thing'))
        self.assertEqual(c['coverage'], 1.0)
        self.assertEqual((c['missing'], c['extra'], c['garbled']), ([], [], []))

    def test_missing_extra_and_garbled_words_are_reported_with_a_time(self):
        c = L.compare(self.SENTENCES, self.heard('And God said unto Noah go forth ark banana banana banana banana Bring forth with thee living thing'))
        self.assertLess(c['coverage'], 1.0)
        self.assertTrue(any(m['words'] == ['of'] or 'of' in m['words'] for m in c['missing']))
        self.assertTrue(any('every' in m['words'] for m in c['missing']))
        self.assertTrue(any(len(e['words']) >= 4 for e in c['extra']))
        self.assertTrue(all(isinstance(m['at'], float) for m in c['missing']))

    def test_a_near_spelling_is_heard_but_a_different_word_is_garbled(self):
        c = L.compare([{'text': 'The ark rested upon the mountains of Ararat'}], self.heard('The ark rested upon the mountains of Ararat'.replace('Ararat', 'Ararats')))
        self.assertEqual(c['coverage'], 1.0)
        c = L.compare([{'text': 'The ark rested upon the mountains of Ararat'}], self.heard('The ark rested upon the valley of Ararat'))
        self.assertEqual(c['garbled'][0]['expected'], 'mountains')

    def test_normalisation_ignores_case_curly_quotes_and_hyphens(self):
        self.assertEqual(L.norm_tokens('Thy sons\u2019 WIVES \u2014 go-forth!'), ['thy', 'sons', 'wives', 'go', 'forth'])

    def test_a_sentence_heard_late_is_flagged_against_its_caption_timeline(self):
        h = self.heard('And God said unto Noah go forth of the ark')
        for w in h:
            w['start'] += 1.5
            w['end'] += 1.5
        c = L.compare(self.SENTENCES[:1], h)
        t = L.sentence_timing(self.SENTENCES[:1], h, c)
        self.assertGreater(t[0]['start_offset'], 1.0)
        m = measures(audio__timing=t)
        self.assertTrue(any(cat == 'd' for _, cat, _ in L.defects(m, 100.0)))

    def test_silence_inside_one_sentence_is_a_defect_and_between_sentences_is_not(self):
        h = [{'t': 'a', 'start': 1.0, 'end': 1.3}, {'t': 'b', 'start': 3.5, 'end': 3.8}, {'t': 'c', 'start': 9.0, 'end': 9.3}]
        gaps = L.speech_gaps([{'text': 'a b', 'start': 0.8, 'end': 4.0}, {'text': 'c', 'start': 8.9, 'end': 9.5}], h)
        self.assertEqual([g['start'] for g in gaps], [1.3])

    def test_the_flood_master_is_compared_against_its_timed_report_sentences(self):
        ref = L.reference_for(FLOOD, FLOOD_SHA)
        self.assertIn('composed.sentences (timed)', ref['source'])
        self.assertTrue(ref['sentences'][0]['text'].startswith('Go forth of the ark'))
        self.assertIsNotNone(ref['sentences'][0]['end'])
        fallback = L.reference_for(FLOOD, 'f' * 64)
        self.assertIn('narration', fallback['source'])
        self.assertEqual(L.reference_for('migration/production/bible/compilations/none.json', 'f' * 64)['sentences'], [])


class Measures(unittest.TestCase):
    def test_ebur128_summary_is_parsed(self):
        text = '\n[Parsed_ebur128_0 @ 0x1] Summary:\n\n  Integrated loudness:\n    I:         -14.4 LUFS\n    Threshold: -24.4 LUFS\n\n  Loudness range:\n    LRA:         6.3 LU\n    LRA low:   -18.0 LUFS\n\n  True peak:\n    Peak:       -1.7 dBFS\n'
        self.assertEqual(L.parse_ebur128(text), {'integrated_lufs': -14.4, 'lra': 6.3, 'true_peak_dbtp': -1.7})

    def test_detectors_are_parsed(self):
        text = ('[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 12.5\n[freezedetect @ 0x1] lavfi.freezedetect.freeze_end: 17.5\n'
                '[blackdetect @ 0x2] black_start:10 black_end:12 black_duration:2\n[Parsed_showinfo_3 @ 0x3] n:   0 pts:   10 pts_time:5.5 pos:0\n')
        d = L.parse_detect(text)
        self.assertEqual(d['freezes'], [{'start': 12.5, 'end': 17.5}])
        self.assertEqual(d['black'], [{'start': 10.0, 'end': 12.0}])
        self.assertEqual(d['scene_changes'], [5.5])

    def test_a_clean_master_has_no_defect(self):
        self.assertEqual(L.defects(measures(), 100.0), [])

    def test_each_demonstrated_defect_class_is_found(self):
        cases = {
            'loudness': (measures(audio__loudness={'integrated_lufs': -20.0, 'lra': 4, 'true_peak_dbtp': -1.6}), 'c'),
            'true peak': (measures(audio__loudness={'integrated_lufs': -14.0, 'lra': 4, 'true_peak_dbtp': 0.3}), 'c'),
            'clipping': (measures(audio__clipping={'peak_dbfs': 0.0, 'peak_count': 40}), 'c'),
            'dropout': (measures(audio__silences=[{'start': 40.0, 'end': 42.0, 'seconds': 2.0}]), 'c'),
            'music': (measures(audio__balance={'voice_over_music_db': 1.5, 'quiet_sentences': []}), 'c'),
            'cut at the start': (measures(audio__first_word_start=0.0), 'a'),
            'cut at the end': (measures(audio__last_word_end=99.99), 'a'),
            'frozen': (measures(video__freezes=[{'start': 30.0, 'end': 36.0}]), 'f'),
            'black': (measures(video__black=[{'start': 50.0, 'end': 52.0}]), 'f'),
            'no captions': (measures(video__frames={'caption_samples_speaking': 30, 'caption_like_speaking_ratio': 0.0, 'duplicate_runs': []}), 'd'),
            'words missing': (measures(audio__compare={'coverage': 0.8, 'expected_words': 100, 'matched_words': 80,
                                                       'missing': [{'words': ['a', 'b', 'c', 'd'], 'sentence': 3, 'at': 20.0}],
                                                       'extra': [], 'garbled': [], 'sentence_coverage': {3: 0.5}}), 'a'),
        }
        for name, (m, cat) in cases.items():
            self.assertIn(cat, [c for _, c, _ in L.defects(m, 100.0)], name)

    def test_an_intended_fade_at_the_edges_is_not_a_dropout(self):
        m = measures(audio__silences=[{'start': 98.5, 'end': 100.0, 'seconds': 1.5}])
        self.assertEqual(L.defects(m, 100.0), [])


@unittest.skipUnless(subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0, 'ffmpeg')
class Whole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.master = t / 'm.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=640x360:r=25:d=8',
                        '-f', 'lavfi', '-i', 'color=c=black:s=640x360:r=25:d=2', '-f', 'lavfi', '-i', 'color=c=0x336699:s=640x360:r=25:d=5',
                        '-f', 'lavfi', '-i', 'sine=f=300:d=15', '-filter_complex', '[0][1][2]concat=n=3:v=1:a=0[v]',
                        '-map', '[v]', '-map', '3:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(cls.master)], check=True)
        cls.sha = hashlib.sha256(cls.master.read_bytes()).hexdigest()
        cls.i = {'plan': FLOOD, 'sha256': cls.sha}
        first = json.loads((ROOT / FLOOD).read_text())['narration'][0]['text']
        cls.fake = lambda d, s: [{'start': 0.6, 'end': 5.0, 'text': first[:40], 'words': words(' '.join(first.split()[:8]), 0.6)}]
        cls.p, cls.ev = L.analyze(cls.i, cls.master, t / 'model', t / 'out', '123', asr=cls.fake)
        cls.out = t / 'out'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_it_hears_sees_and_writes_the_native_review_shape(self):
        p = self.p
        self.assertEqual((p['version'], p['provider'], p['status']), ('native-review-public-v1', 'local', 'EVIDENCE_COMPLETE'))
        for key in ('plan', 'output_sha256', 'model', 'run_id', 'source_run_id', 'coverage', 'retry_count', 'production_approved',
                    'publication_ready', 'report_validated', 'scores', 'overall', 'criterion_issues', 'issues', 'limitations',
                    'owner_floor_met', 'every_criterion_at_least_9_5'):
            self.assertIn(key, p)
        self.assertEqual(set(p['scores']), set(N.RUBRIC))
        self.assertTrue(p['visual_review_required'])
        self.assertFalse(p['production_approved'] or p['publication_ready'])
        self.assertIsNone(p['overall'])
        self.assertTrue(p['transcript'] and p['frame_sheets'])
        self.assertTrue((self.out / 'frames' / 'sheet-001.jpg').is_file())
        self.assertTrue((self.out / 'public' / 'public-evidence.json').is_file())
        md = N.summary_markdown(p)   # the Gemini summary renderer reads this shape unchanged
        self.assertIn('Native review evidence', md)
        self.assertIn('transcript match', L.summary(p))

    def test_issues_use_the_timestamped_category_format_every_consumer_validates(self):
        self.assertTrue(self.p['issues'])
        for text in self.p['issues']:
            m = re.match(r'^(\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)(?:\s+|:\s+)', text)   # native_review.validate_report's rule
            self.assertIsNotNone(m, text)
            self.assertRegex(text, r'^\d\d:\d\d\.\d\d \[(a|b|c|d|f|info)\] \S')
        self.assertEqual(self.p['machine_verdict'], 'DEFECTS_FOUND')   # most of the script is not spoken in this fixture
        self.assertFalse(self.p['owner_floor_met'])

    def test_the_black_and_frozen_stretches_are_seen(self):
        v = self.p['measures']['video']
        self.assertTrue(v['black'])
        self.assertTrue(v['freezes'])
        self.assertTrue(any('[f]' in x for x in self.p['issues']))

    def test_the_public_file_holds_no_media_path_or_secret(self):
        text = (self.out / 'public' / 'public-evidence.json').read_text()
        self.assertNotIn(self.tmp.name, text)
        self.assertNotRegex(text, r'https?://')

    def test_a_wrong_master_hash_is_refused_before_anything_is_heard(self):
        with self.assertRaises(L.Refusal):
            L.analyze({'plan': FLOOD, 'sha256': '0' * 64}, self.master, '.', self.out, '1', asr=self.fake)

    def test_inputs_are_validated(self):
        ok = {'inputs': {'plan': FLOOD, 'sha256': 'a' * 64}}
        self.assertEqual(L.inputs(ok)['plan'], FLOOD)
        for bad in ({'plan': '../x.json', 'sha256': 'a' * 64}, {'plan': FLOOD, 'sha256': 'A' * 64},
                    {'plan': 'migration/production/bible/plans/nope-none.json', 'sha256': 'a' * 64}):
            with self.assertRaises(L.Refusal):
                L.inputs({'inputs': bad})


if __name__ == '__main__':
    unittest.main()
