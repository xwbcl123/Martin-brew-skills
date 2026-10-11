"""Independent release-boundary regressions. Real synthetic media; fixture review receipts.

No private ASR or external API. Synthetic review assertions test gates and are never
evidence of actual semantic/visual approval. Mutations refresh artifact hashes and
fixture reviews deliberately, so rejection must enforce the underlying contract.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


HERE = Path(__file__).resolve().parent
pkg = module('independent_package', HERE / 'package.py')
renderer = module('independent_renderer', pkg.CONTRACT.parents[2] / 'podcast-enrichment/scripts/enrich.py')
sys.modules['package'] = pkg
assembler = module('independent_assembler', HERE / 'assemble.py')


class PackageBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_dir = tempfile.TemporaryDirectory(prefix='podcast-synthetic-media-')
        cls.audio = Path(cls.media_dir.name) / 'audio.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                        '-af', 'volume=2.0', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '192k', str(cls.audio)], check=True)
        log = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(cls.audio),
                              '-af', 'loudnorm=I=-16:TP=-1:print_format=json', '-f', 'null', '-'],
                             check=True, capture_output=True, text=True).stderr
        observed = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', log)[-1])
        cls.metrics = {'integrated_lufs': float(observed['input_i']), 'true_peak_dbtp': float(observed['input_tp'])}

    @classmethod
    def tearDownClass(cls):
        cls.media_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='podcast-package-fixture-')
        self.root = Path(self.tmp.name).resolve()
        shutil.copyfile(self.audio, self.root / 'audio.mp3')
        self.ah = pkg.sha(self.root / 'audio.mp3')
        Image.new('RGB', (1400, 1400), 'white').save(self.root / 'cover.png')
        # Actual images but synthetic screenshot assertions, explicitly fixture-only.
        Image.new('RGB', (1440, 900), 'white').save(self.root / 'desktop.png')
        Image.new('RGB', (390, 844), 'white').save(self.root / 'mobile.png')
        self.segments = [{'id': 0, 'start': 0.0, 'end': 3.0, 'text': 'Fixture source A', 'speaker': 'unknown'}]
        self.raw = {'result': {'language': 'en'}, 'transcription': [
            {'offsets': {'from': 0, 'to': 3000}, 'text': ' Fixture source A '}]}
        self.payload = {'title': 'Fixture', 'summary': 'Summary', 'description': 'Fixture description',
                        'transcript_text': 'Fixture source A', 'image_url': 'https://example.test/cover.png',
                        'author': 'Fixture', 'explicit': False, 'type': 'full', 'number': 1, 'season': 1}
        self.content = {'title': 'Fixture', 'show_title': 'Synthetic Test Show', 'summary': 'Summary',
                        'description': 'Fixture description', 'show_notes': 'Fixture notes', 'launch_copy': 'Fixture copy',
                        'language': 'en', 'ai_disclosure': 'Synthetic fixture only; no human recording.',
                        'segments': copy.deepcopy(self.segments), 'duration': 3.0,
                        'chapters': [{'start': 0, 'title': 'Fixture chapter', 'summary': 'Fixture chapter summary', 'source_segment_ids': [0]}],
                        'reading_transcript': [{'text': 'Fixture source A', 'source_segment_ids': [0]}],
                        'metadata': {'reading_language': 'en', 'reading_mode': 'edited', 'corrections': []},
                        'audio_path': 'audio.mp3', 'cover_path': 'cover.png', 'resources': [], 'assets': [], 'audit_links': []}
        self.names = {'delivery_audio': 'audio.mp3', 'aligned_transcript': 'aligned.json', 'raw_asr_json': 'raw.json',
                      'raw_asr_txt': 'raw.txt', 'subtitles_srt': 'subtitles.srt', 'subtitles_vtt': 'subtitles.vtt',
                      'correction_ledger': 'corrections.json', 'enrichment': 'enrichment.json', 'artwork': 'cover.png',
                      'preview': 'preview/episode.html', 'transistor_payload': 'payload.json', 'audio_qc': 'qc.json'}
        self.write('raw.json', self.raw)
        (self.root / 'raw.txt').write_text('Fixture source A\n')
        self.write('corrections.json', {'schema_version': '2.0', 'audio_sha256': self.ah,
                                       'raw_json_sha256': pkg.sha(self.root / 'raw.json'), 'corrections': []})
        self.write('aligned.json', {'audio_sha256': self.ah, 'language': 'en', 'duration': 3, 'segments': self.segments})
        self.write('qc.json', {'audio_sha256': self.ah, **self.metrics})
        self.payload['description'] = pkg.description(self.content)
        self.write('payload.json', self.payload)
        self.write('enrichment.json', self.content)
        (self.root / 'subtitles.srt').write_text('1\n00:00:00,000 --> 00:00:03,000\nFixture source A\n')
        (self.root / 'subtitles.vtt').write_text('WEBVTT\n\n1\n00:00:00.000 --> 00:00:03.000\nFixture source A\n')
        enrichment_manifest = renderer.build(self.content, self.root, self.root / 'preview/episode.html', self.root / 'enrichment.json')
        self.names['enrichment_manifest'] = 'preview/enrichment-manifest.json'
        for index, artifact in enumerate(enrichment_manifest['artifacts']):
            if artifact['path'] not in self.names.values():
                self.names['preview_download_' + str(index)] = artifact['path']
        self.ep = {'contract_version': '2.0', 'episode_key': 'synthetic-fixture', 'package_revision': 1,
                   'source_kind': 'imported_finished', 'review_mode': 'delegated_release', 'show_id': '12345',
                   'profile_ref': 'podcast_mp3', 'sources': [{'kind': 'synthetic-test'}], 'artifacts': {},
                   'provider_metadata': {k: self.payload[k] for k in ['author', 'explicit', 'type', 'season', 'number', 'image_url']},
                   'reviews': [kind + '-review.json' for kind in ['content', 'experience', 'implementation']],
                   'rights': {'policy': 'user_directed_publication', 'distribution_authority': 'explicit',
                              'unresolved_concrete_risks': [], **{dim: {'status': 'not_applicable', 'source': 'synthetic fixture'}
                                                               for dim in ['content', 'voice', 'music', 'generator_terms']}}}
        self.refresh()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data, ensure_ascii=False))

    def refresh(self):
        """Rebind deliberate fixture mutations; never hide a semantic issue behind stale hashes."""
        self.ep['artifacts'] = {role: {'path': name, 'sha256': pkg.sha(self.root / name),
                                      'bytes': (self.root / name).stat().st_size, 'audio_sha256': self.ah}
                                for role, name in self.names.items()}
        self.write('episode.json', self.ep)
        for kind in ['content', 'experience', 'implementation']:
            receipt = {'kind': kind, 'decision': 'approved', 'accepted_by_kind': 'agent_delegated', 'user_reviewed': False,
                       'reviewer_id': 'synthetic-fixture-only', 'evidence': 'Fixture assertion; NOT real content or visual approval.',
                       'artifact_bindings': {role: self.ep['artifacts'][role]['sha256']
                                             for role in ['delivery_audio', 'enrichment', 'preview', 'artwork']},
                       'payload_sha256': pkg.canonical(pkg.read(self.root / 'payload.json')),
                       'review_context_sha256': pkg.review_context(self.ep)}
            if kind == 'experience':
                receipt.update(checks={k: True for k in ['desktop_1440', 'mobile_390', 'play_pause', 'seek', 'chapter', 'search', 'copy']},
                               screenshots=[{'path': n, 'sha256': pkg.sha(self.root / n)} for n in ['desktop.png', 'mobile.png']])
            self.write(kind + '-review.json', receipt)

    def assertRejected(self, expected=None, sealed=False):
        result = pkg.validate(self.root, True, sealed)
        self.assertFalse(result['valid'], result)
        if expected:
            self.assertTrue(any(expected in e for e in result['errors']), result)

    def test_valid_real_media_fixture_and_seal(self):
        result = pkg.validate(self.root, True)
        self.assertTrue(result['valid'], result)
        command = subprocess.run([__import__('sys').executable, str(HERE / 'package.py'), 'seal', '--package', str(self.root)],
                                 capture_output=True, text=True)
        self.assertEqual(command.returncode, 0, command.stdout + command.stderr)
        self.assertTrue(pkg.validate(self.root, True, True)['valid'])

    def test_missing_seal(self):
        self.assertRejected('seal.json', sealed=True)

    def test_review_bytes_changed_after_seal(self):
        result = pkg.validate(self.root, True)
        self.assertTrue(result['valid'], result)
        result.update(manifest_sha256=pkg.sha(self.root / 'episode.json'), contract_bundle_sha256=pkg.bundle_hash(),
                      implementation_sha256=pkg.implementation_hash(),
                      review_hashes={ref: pkg.sha(self.root / ref) for ref in self.ep['reviews']})
        self.write('seal.json', result)
        receipt = pkg.read(self.root / 'content-review.json'); receipt['evidence'] = 'changed fixture evidence'
        self.write('content-review.json', receipt)
        self.assertRejected('seal missing/stale/invalid', sealed=True)

    def test_unrelated_preview(self):
        (self.root / 'preview/episode.html').write_text('<html>unrelated B</html>')
        self.refresh(); self.assertRejected('preview bytes differ')

    def test_changed_provider_description(self):
        self.payload['description'] = 'Unrelated provider description without show notes or disclosure'
        self.write('payload.json', self.payload); self.refresh(); self.assertRejected('description')

    def test_missing_download_inventory(self):
        role = next(k for k, v in self.names.items() if v == 'preview/transcript.txt')
        del self.names[role]
        self.refresh(); self.assertRejected('linked preview artifact missing/changed')

    def test_changed_download_after_render(self):
        (self.root / 'preview/reading-transcript.txt').write_text('Unrelated downloadable content')
        self.refresh(); self.assertRejected('linked preview artifact missing/changed')

    def test_missing_download_file(self):
        (self.root / 'preview/transcript.txt').unlink()
        self.assertRejected('missing artifact')

    def test_empty_raw_evidence(self):
        for role in ['raw_asr_json', 'raw_asr_txt', 'subtitles_srt', 'subtitles_vtt', 'correction_ledger']:
            with self.subTest(role=role):
                path = self.root / self.names[role]; before = path.read_bytes(); path.write_bytes(b'')
                self.refresh(); self.assertRejected(); path.write_bytes(before)

    def test_wrong_raw_text(self):
        (self.root / 'raw.txt').write_text('Unrelated transcript')
        self.refresh(); self.assertRejected('raw ASR text/json disagree')

    def test_unexplained_aligned_text(self):
        aligned = pkg.read(self.root / 'aligned.json'); aligned['segments'][0]['text'] = 'Unexplained edit'
        self.write('aligned.json', aligned); self.refresh(); self.assertRejected('raw correction provenance')

    def test_unexplained_aligned_timing(self):
        aligned = pkg.read(self.root / 'aligned.json'); aligned['segments'][0]['end'] = 2.5
        self.write('aligned.json', aligned); self.refresh(); self.assertRejected('raw correction provenance')

    def test_missing_raw_segment_coverage(self):
        self.raw['transcription'].append({'offsets': {'from': 1000, 'to': 2000}, 'text': 'Omitted segment'})
        self.write('raw.json', self.raw); (self.root / 'raw.txt').write_text('Fixture source A\nOmitted segment')
        self.refresh(); self.assertRejected('coverage mismatch')

    def test_stale_correction_ledger(self):
        ledger = pkg.read(self.root / 'corrections.json'); ledger['raw_json_sha256'] = '0' * 64
        self.write('corrections.json', ledger); self.refresh(); self.assertRejected('ledger stale/invalid')

    def test_invalid_correction_before(self):
        ledger = pkg.read(self.root / 'corrections.json')
        ledger['corrections'] = [{'segment_id': 0, 'field': 'text', 'before': 'Not the source', 'after': 'Fixture source A', 'reason': 'fixture'}]
        self.write('corrections.json', ledger); self.refresh(); self.assertRejected('invalid correction chain')

    def test_unrelated_correction_segment_rejected(self):
        ledger = pkg.read(self.root / 'corrections.json')
        ledger['corrections'] = [{'segment_id': 999, 'field': 'text', 'before': 'A', 'after': 'B', 'reason': 'fixture'}]
        self.write('corrections.json', ledger); self.refresh(); self.assertRejected()

    def test_valid_explained_correction_chain(self):
        ledger = pkg.read(self.root / 'corrections.json')
        ledger['corrections'] = [{'segment_id': 0, 'field': 'text', 'before': 'Fixture source A',
                                  'after': 'Fixture source B', 'reason': 'synthetic correction fixture'},
                                 {'segment_id': 0, 'field': 'text', 'before': 'Fixture source B',
                                  'after': 'Fixture source C', 'reason': 'second synthetic correction'}]
        self.write('corrections.json', ledger)
        aligned = pkg.read(self.root / 'aligned.json'); aligned['segments'][0]['text'] = 'Fixture source C'
        self.write('aligned.json', aligned)
        self.content['segments'][0]['text'] = 'Fixture source C'
        self.content['reading_transcript'][0]['text'] = 'Fixture source C'
        self.write('enrichment.json', self.content)
        self.payload['transcript_text'] = 'Fixture source C'; self.write('payload.json', self.payload)
        for name in ['subtitles.srt', 'subtitles.vtt']:
            path = self.root / name; path.write_text(path.read_text().replace('Fixture source A', 'Fixture source C'))
        renderer.build(self.content, self.root, self.root / 'preview/episode.html', self.root / 'enrichment.json')
        self.refresh()
        result = pkg.validate(self.root, True)
        self.assertTrue(result['valid'], result)

    def test_raw_aligned_language_disagreement(self):
        aligned = pkg.read(self.root / 'aligned.json'); aligned['language'] = 'zh'
        self.write('aligned.json', aligned); self.refresh(); self.assertRejected()

    def duplicate_deletion_fixture(self, explained):
        self.raw['transcription'].insert(0, {'offsets': {'from': 0, 'to': 0}, 'text': 'Fixture source A'})
        self.write('raw.json', self.raw)
        (self.root / 'raw.txt').write_text('Fixture source A\nFixture source A\n')
        ledger = pkg.read(self.root / 'corrections.json')
        ledger['raw_json_sha256'] = pkg.sha(self.root / 'raw.json')
        ledger['corrections'] = ([{'segment_id': 0, 'field': 'text', 'before': 'Fixture source A', 'after': '',
                                  'reason': 'Synthetic zero-duration ASR duplicate immediately repeated by source segment 1.'}]
                                 if explained else [])
        self.write('corrections.json', ledger)
        aligned = pkg.read(self.root / 'aligned.json'); aligned['segments'][0]['id'] = 1
        self.write('aligned.json', aligned)
        self.content['segments'][0]['id'] = 1
        self.content['chapters'][0]['source_segment_ids'] = [1]
        self.content['reading_transcript'][0]['source_segment_ids'] = [1]
        self.write('enrichment.json', self.content)
        renderer.build(self.content, self.root, self.root / 'preview/episode.html', self.root / 'enrichment.json')
        self.refresh()

    def test_explained_zero_duration_duplicate_deletion(self):
        self.duplicate_deletion_fixture(True)
        result = pkg.validate(self.root, True)
        self.assertTrue(result['valid'], result)

    def test_unexplained_duplicate_deletion(self):
        self.duplicate_deletion_fixture(False)
        self.assertRejected('coverage mismatch')

    def prepare_assembly(self):
        (self.root / 'transcription').mkdir()
        for source, target in [('aligned.json', 'aligned.json'), ('corrections.json', 'corrections.json'),
                               ('raw.json', 'raw.json'), ('raw.txt', 'raw.txt'),
                               ('subtitles.srt', 'raw.srt'), ('subtitles.vtt', 'raw.vtt')]:
            shutil.copyfile(self.root / source, self.root / 'transcription' / target)
        self.write('content.json', self.content)
        self.write('report.json', {'metrics': self.metrics})
        self.write('transcription/report.json', {'fixture': True})
        renderer.build(self.content, self.root, self.root / 'preview/episode.html', self.root / 'content.json')

    def run_assembly(self):
        return assembler.assemble(self.root, self.audio, 'imported_finished', '12345', 'fixture-assembled',
                                  1, 'https://example.test/cover.png', 1, author='Example Host',
                                  origin_tool='Fixture editor export supplied by user', declaration_source='fixture-declaration#input')

    def test_assemble_is_unapproved_and_unsealed(self):
        self.prepare_assembly(); result = self.run_assembly()
        self.assertEqual(result['audio_sha256'], self.ah)
        self.assertFalse((self.root / 'seal.json').exists())
        episode = pkg.read(self.root / 'episode.json')
        self.assertTrue(all(not (self.root / ref).exists() for ref in episode['reviews']))
        self.assertFalse(pkg.validate(self.root, True)['valid'])

    def test_assemble_records_caller_supplied_identity_source_and_series_fields(self):
        self.prepare_assembly()
        assembler.assemble(self.root, self.audio, 'imported_finished', '12345', 'fixture-assembled', 1, 'https://example.test/cover.png', 1,
                           author='Series Author', origin_tool='Some DAW export', declaration_source='msg-42', season=2, episode_type='bonus')
        episode = pkg.read(self.root / 'episode.json'); payload = pkg.read(self.root / 'payload.json')
        self.assertEqual(episode['provider_metadata']['author'], 'Series Author'); self.assertEqual(payload['author'], 'Series Author')
        self.assertEqual((episode['provider_metadata']['season'], episode['provider_metadata']['type']), (2, 'bonus'))
        self.assertEqual((payload['season'], payload['type']), (2, 'bonus'))
        self.assertEqual((episode['sources'][0]['origin_tool'], episode['sources'][0]['declaration_source']), ('Some DAW export', 'msg-42'))
        blob = json.dumps(episode)
        for stale in ('Filmora', 'tasks/sessions', 'original-user-authority', 'Martin'): self.assertNotIn(stale, blob.replace('filmora-supplied.srt', '').replace('filmora-input-report', ''))

    def test_assemble_requires_explicit_author_origin_and_declaration(self):
        self.prepare_assembly()
        base = dict(author='A', origin_tool='T', declaration_source='D')
        for missing in base:
            kwargs = {k: v for k, v in base.items() if k != missing}
            with self.subTest(missing=missing), self.assertRaises(TypeError):
                assembler.assemble(self.root, self.audio, 'imported_finished', '12345', 'k', 1, 'https://example.test/c.png', 1, **kwargs)
        for field in base:
            with self.subTest(blank=field), self.assertRaises(ValueError):
                assembler.assemble(self.root, self.audio, 'imported_finished', '12345', 'k', 1, 'https://example.test/c.png', 1, **{**base, field: '  '})
        for bad in ({'season': -1}, {'season': True}, {'episode_type': 'series'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                assembler.assemble(self.root, self.audio, 'imported_finished', '12345', 'k', 1, 'https://example.test/c.png', 1, **base, **bad)

    def test_assemble_rejects_content_for_another_show(self):
        self.prepare_assembly(); self.content.setdefault('metadata', {})['show_id'] = '23456'; self.write('content.json', self.content)
        with self.assertRaisesRegex(ValueError, 'differs'): self.run_assembly()

    def test_author_resolution_uses_config_and_never_guesses(self):
        cfg = self.root / 'cfg.json'; cfg.write_text(json.dumps({'shows': {'12345': {'author': 'Config Author'}}}))
        old = os.environ.get('PODCAST_CONFIG'); os.environ['PODCAST_CONFIG'] = str(cfg)
        try:
            self.assertEqual(assembler.resolve_author('12345'), 'Config Author')
            self.assertEqual(assembler.resolve_author('12345', 'Config Author'), 'Config Author')
            with self.assertRaisesRegex(ValueError, 'conflicts'): assembler.resolve_author('12345', 'Somebody Else')
            with self.assertRaisesRegex(ValueError, 'no author'): assembler.resolve_author('99999')
            self.assertEqual(assembler.resolve_author('99999', 'Explicit'), 'Explicit')
        finally:
            if old is None: os.environ.pop('PODCAST_CONFIG', None)
            else: os.environ['PODCAST_CONFIG'] = old

    def test_assemble_rejects_output_symlink_before_overwrite(self):
        self.prepare_assembly()
        with tempfile.TemporaryDirectory(prefix='podcast-outside-fixture-') as outside:
            sentinel = Path(outside) / 'untouched.json'; sentinel.write_text('sentinel')
            payload = self.root / 'payload.json'; payload.unlink(); payload.symlink_to(sentinel)
            with self.assertRaises((ValueError, OSError)):
                self.run_assembly()
            self.assertEqual(sentinel.read_text(), 'sentinel')

    def test_subtitle_timestamp_change(self):
        path = self.root / 'subtitles.srt'; path.write_text(path.read_text().replace('00:00:03,000', '00:00:02,000'))
        self.refresh(); self.assertRejected('canonical subtitle differs')

    def test_enrichment_not_canonical(self):
        self.content['segments'][0]['text'] = 'Other source'
        self.write('enrichment.json', self.content); self.refresh(); self.assertRejected('enrichment transcript differs')

    def test_audio_lineage_changed(self):
        self.ep['artifacts']['raw_asr_json']['audio_sha256'] = '0' * 64
        self.write('episode.json', self.ep); self.assertRejected('audio lineage')

    def test_falsely_passing_qc(self):
        path = self.root / 'audio.mp3'; path.unlink()
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                        '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '192k', str(path)], check=True)
        self.ah = pkg.sha(path)
        self.write('qc.json', {'audio_sha256': self.ah, 'integrated_lufs': -16, 'true_peak_dbtp': -2})
        self.refresh(); self.assertRejected('fresh measured loudness profile failed')


if __name__ == '__main__':
    unittest.main()
