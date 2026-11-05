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

    def test_e269_the_asr_writes_numbers_as_digits_and_the_script_spells_them(self):
        h = L.flatten_heard([{'words': words('in the 600th year and 950 years 40 days the 17th day')}])
        self.assertEqual([w['t'] for w in h], 'in the six hundredth year and nine hundred fifty years forty days the seventeenth day'.split())
        c = L.compare([{'text': 'in the six hundredth year and nine hundred and fifty years forty days the seventeenth day'}], h)
        self.assertEqual((c['garbled'], c['coverage'] >= 0.9), ([], True))

    def test_e269_whisper_word_time_jitter_and_a_planned_cold_open_are_not_defects(self):
        t = [{'sentence': 1, 'timeline_start': 6.0, 'start_offset': -0.76, 'end_offset': -0.95}]
        a = dict(measures()['audio'], timing=t, first_word_start=0.0, sentence_starts={0: 0.0})
        m = measures(); m['audio'] = a
        self.assertEqual(L.defects(m, 100.0), [])
        self.assertTrue(any('frame 0 by plan' in x for _, _, x in L.informational(m)))
        m['audio']['compare'] = dict(a['compare'], garbled=[{'expected': 'bow', 'heard': 'bell', 'sentence': 3, 'at': 9.0}])
        self.assertEqual(L.defects(m, 100.0), [])
        self.assertTrue(any('bell' in x for _, _, x in L.informational(m)))
        m['audio']['timing'] = [dict(t[0], start_offset=1.3)]
        self.assertTrue(any(c == 'd' for _, c, _ in L.defects(m, 100.0)))

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


class WerAndUtmos(unittest.TestCase):
    """Per-sentence WER and UTMOS are WARN-only: they never become a defect, a verdict or a gate."""
    S = Script.SENTENCES

    def heard(self, text):
        return L.flatten_heard([{'words': words(text, 0.5)}])

    def test_a_perfect_reading_has_zero_wer_in_every_sentence(self):
        w = L.sentence_wer(self.S, self.heard('And God said unto Noah go forth of the ark Bring forth with thee every living thing'))
        self.assertEqual(w['overall']['wer'], 0.0)
        self.assertEqual([r['wer'] for r in w['sentences']], [0.0, 0.0])
        self.assertEqual(w['sentences'][0]['at'], 0.5)

    def test_substituted_missing_and_extra_words_are_counted_in_the_right_sentence(self):
        w = L.sentence_wer(self.S, self.heard('And God said unto Noah go forth of the banana Bring forth with thee every every living'))
        a, b = w['sentences']
        self.assertEqual((a['sub'], a['del'], a['ins']), (1, 0, 0))       # ark -> banana
        self.assertEqual((b['sub'], b['del'], b['ins']), (0, 1, 1))       # thing missing, one extra word
        self.assertEqual(w['overall']['errors'], 3)
        self.assertEqual(w['overall']['ref_words'], a['ref_words'] + b['ref_words'])

    def test_a_near_spelling_is_a_strict_substitution_and_is_counted_as_near(self):
        w = L.sentence_wer([{'text': 'Shinar was a plain'}], self.heard('Shinars was a plain'))
        self.assertEqual((w['sentences'][0]['sub'], w['sentences'][0]['near']), (1, 1))

    def test_a_sentence_missing_entirely_is_all_deletions_with_a_time(self):
        w = L.sentence_wer(self.S, self.heard('And God said unto Noah go forth of the ark'))
        self.assertEqual(w['sentences'][1]['wer'], 1.0)
        self.assertIsNotNone(w['sentences'][1]['at'])

    def test_wer_warns_above_the_provisional_thresholds_and_is_not_a_defect(self):
        bad = L.sentence_wer(self.S, self.heard('And God said unto Noah go forth of the banana Bring forth with thee every every living'))
        m = measures(audio__wer=bad)
        texts = [x for _, x in L.warnings_for(m)]
        self.assertTrue(any('overall word error rate' in x for x in texts))
        self.assertEqual(L.defects(m, 100.0), [])                     # a WARN is never a defect
        clean = measures(audio__wer=L.sentence_wer(self.S, self.heard('And God said unto Noah go forth of the ark Bring forth with thee every living thing')))
        self.assertEqual(L.warnings_for(clean), [])
        self.assertEqual(L.warnings_for(measures()), [])

    def test_short_sentences_do_not_warn_on_one_word(self):
        w = L.sentence_wer([{'text': 'Go forth now'}], self.heard('Go back now'))
        self.assertLess(w['sentences'][0]['ref_words'], L.WER_MIN_WORDS)
        self.assertEqual(L.warnings_for(measures(audio__wer=dict(w, overall={'ref_words': 100, 'errors': 0, 'wer': 0.0, 'near_matches': 0}))), [])

    def test_utmos_scores_the_heard_sentence_spans_with_the_injected_predictor(self):
        import numpy as np
        heard = self.heard('And God said unto Noah go forth of the ark Bring forth with thee every living thing')
        cmp_ = L.compare(self.S, heard)
        spans = L.sentence_spans(self.S, heard, cmp_)
        seen = []
        u = L.utmos_scores(np.zeros(16000 * 20, dtype='float32'), spans, lambda clips: (seen.append(len(clips)), [3.9, 1.4])[1])
        self.assertEqual((u['status'], u['clips'], seen), ('OK', 2, [2]))
        self.assertEqual(u['min'], 1.4)
        m = measures(audio__utmos=u)
        texts = [x for _, x in L.warnings_for(m)]
        self.assertEqual(sum('UTMOS naturalness 1.4' in x for x in texts), 1)
        self.assertEqual(L.utmos_scores(np.zeros(10, dtype='float32'), {}, lambda c: c)['status'], 'NO_CLIPS')

    def test_utmos_is_thinned_and_unavailable_tool_is_none_never_an_error(self):
        import numpy as np
        spans = {n: (n * 3.0, n * 3.0 + 2.0) for n in range(300)}
        u = L.utmos_scores(np.zeros(16000 * 1000, dtype='float32'), spans, lambda clips: [3.5] * len(clips))
        self.assertEqual(u['clips'], L.UTMOS_MAX_CLIPS)
        self.assertIsNone(L.load_utmos('/nonexistent/utmos'))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'code').mkdir()
            (Path(d) / L.UTMOS['weights']).write_bytes(b'not the pinned weights')
            self.assertIsNone(L.load_utmos(d))                       # hash mismatch: refused, not loaded

    def test_the_pins_are_in_the_workflow(self):
        self.assertEqual(len(L.UTMOS['commit']), 40)
        self.assertRegex(L.UTMOS['weights_sha256'], r'^[0-9a-f]{64}$')
        for text in (L.UTMOS['commit'], L.UTMOS['weights_sha256'], L.UTMOS['weights'], 'torch==2.5.1+cpu'):
            self.assertIn(text, WORKFLOW)
        step = WORKFLOW[WORKFLOW.index('Optional pinned UTMOS22'):WORKFLOW.index('Hear and see the whole master')]
        self.assertIn('continue-on-error: true', step)
        self.assertNotIn('secrets.', step)


class WholeWithMeasures(unittest.TestCase):
    def test_wer_and_utmos_reach_the_public_evidence_as_warnings_without_changing_the_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            master = t / 'm.mp4'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=320x180:r=10:d=12',
                            '-f', 'lavfi', '-i', 'sine=f=300:d=12', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                            '-shortest', str(master)], check=True)
            i = {'plan': FLOOD, 'sha256': hashlib.sha256(master.read_bytes()).hexdigest()}
            first = json.loads((ROOT / FLOOD).read_text())['narration'][0]['text']
            fake = lambda dd, s: [{'start': 0.6, 'end': 5.0, 'text': first[:30], 'words': words(' '.join(first.split()[:6]), 0.6)}]
            p, ev = L.analyze(i, master, t / 'model', t / 'out', '9', asr=fake, utmos_predict=lambda clips: [1.2] * len(clips))
            self.assertEqual(ev['measures']['audio']['utmos']['status'], 'OK')
            self.assertTrue(any('UTMOS' in w for w in p['warnings']))
            self.assertTrue(any('word error rate' in w for w in p['warnings']))
            for w in p['warnings']:
                self.assertRegex(w, r'^\d\d:\d\d\.\d\d \[warn\] \S')
            self.assertFalse(any('[warn]' in x for x in p['issues']))
            self.assertIn('provisional', p['warnings_note'])
            self.assertNotRegex((t / 'out/public/public-evidence.json').read_text(), r'https?://')
            p2, ev2 = L.analyze(i, master, t / 'model', t / 'out2', '9', asr=fake)
            self.assertEqual(ev2['measures']['audio']['utmos']['status'], 'NOT_RUN')
            self.assertEqual(p['machine_verdict'], p2['machine_verdict'])
            self.assertIn('WER', L.summary(p))


class FailureLocation(unittest.TestCase):
    def test_unexpected_failure_names_the_frame_not_the_path(self):
        import io, os, contextlib
        def boom(*a, **k):
            return [][0]
        old = L.inputs
        L.inputs = boom
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = L.main(['x', 'analyze'])
        finally:
            L.inputs = old
        self.assertEqual(rc, 1)
        text = out.getvalue()
        self.assertIn('LOCAL_REVIEW_ANALYZE_FAILED_IndexError', text)
        self.assertRegex(text, r'LOCAL_REVIEW_FAILED_AT boom:\d+|LOCAL_REVIEW_FAILED_AT test_local_review\.py:boom:\d+')
        self.assertNotIn('/', text)


class AsrRetry(unittest.TestCase):
    class Seg:
        start, end, text, words = 0.0, 1.0, ' hi ', []

    def model(self, fails):
        outer = self

        class M:
            calls = 0

            def transcribe(self, samples, **kw):
                M.calls += 1
                if M.calls <= fails:
                    def gen():
                        raise IndexError('list index out of range')
                        yield
                    return gen(), None
                return iter([outer.Seg()]), None
        return M()

    def test_a_failed_alignment_pass_is_repeated(self):
        m = self.model(2)
        self.assertEqual(L.run_asr(m, [0.0])[0]['text'], 'hi')
        self.assertEqual(type(m).calls, 3)

    def test_the_last_index_error_stays(self):
        m = self.model(3)
        with self.assertRaises(IndexError):
            L.run_asr(m, [0.0])
        self.assertEqual(type(m).calls, 3)

    def test_other_errors_are_not_retried(self):
        class M:
            calls = 0

            def transcribe(self, samples, **kw):
                M.calls += 1
                raise ValueError('x')
        with self.assertRaises(ValueError):
            L.run_asr(M(), [0.0])
        self.assertEqual(M.calls, 1)


if __name__ == '__main__':
    unittest.main()
