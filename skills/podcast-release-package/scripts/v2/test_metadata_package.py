"""Metadata-only release boundary tests with real synthetic MP3 and chapter frames.

Fixture reviews are synthetic assertions, never user/visual acceptance. Only the
sample-edit verifier dispatch test mocks its heavy PCM-edit proof; ID3 verification,
media decoding, renderer and remaining release validation always run for real.
"""
import copy
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

import test_package as fixtures

pkg = fixtures.pkg
renderer = fixtures.renderer
chapters = fixtures.module('metadata_test_chapters', fixtures.HERE / 'chapters.py')


class MetadataPackageTests(unittest.TestCase):
    # Borrow setup/helpers explicitly; no inherited legacy tests or duplicated discovery.
    write = fixtures.PackageBoundaryTests.write
    tearDown = fixtures.PackageBoundaryTests.tearDown
    assertRejected = fixtures.PackageBoundaryTests.assertRejected

    @classmethod
    def setUpClass(cls):
        fixtures.PackageBoundaryTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        fixtures.PackageBoundaryTests.tearDownClass.__func__(cls)

    def setUp(self):
        self.base_ah = None
        fixtures.PackageBoundaryTests.setUp(self)
        self.base_ah = self.ah
        self.lineage = chapters.embed(self.root / 'audio.mp3', self.root / 'tagged.mp3', self.content['chapters'])
        self.lineage.update(base_audio_path='audio.mp3', chapter_input=copy.deepcopy(self.content['chapters']))
        self.write('metadata-lineage.json', self.lineage)
        self.names.update(delivery_audio='tagged.mp3', base_delivery_audio='audio.mp3',
                          audio_metadata_lineage='metadata-lineage.json')
        self.ah = pkg.sha(self.root / 'tagged.mp3')
        self.content['audio_path'] = 'tagged.mp3'
        self.content['public_content'] = {'version': 1, 'nodes': [
            {'type': 'paragraph', 'children': [{'type': 'text', 'text': 'Listener fixture & chapter.'}]},
            {'type': 'paragraph', 'children': [{'type': 'strong', 'children': [
                {'type': 'text', 'text': 'A useful point'}]}]}, {'type': 'chapters'}]}
        self.content['summary'] = renderer.public_summary(self.content)
        for path in ['aligned.json', 'corrections.json', 'qc.json']:
            value = pkg.read(self.root / path); value['audio_sha256'] = self.ah; self.write(path, value)
        self.rebuild()

    def refresh(self):
        fixtures.PackageBoundaryTests.refresh(self)
        if self.base_ah:
            for role in ['raw_asr_json', 'raw_asr_txt', 'base_delivery_audio']:
                if role in self.ep['artifacts']:
                    self.ep['artifacts'][role]['audio_sha256'] = self.base_ah
            self.write('episode.json', self.ep)
            for ref in self.ep['reviews']:
                receipt = pkg.read(self.root / ref)
                receipt['review_context_sha256'] = pkg.review_context(self.ep)
                self.write(ref, receipt)

    def rebuild(self):
        self.payload.update(description=pkg.description(self.content), summary=self.content['summary'])
        self.write('payload.json', self.payload); self.write('enrichment.json', self.content)
        manifest = renderer.build(self.content, self.root, self.root / 'preview/episode.html', self.root / 'enrichment.json')
        for index, artifact in enumerate(manifest['artifacts']):
            if artifact['path'] not in self.names.values():
                self.names['metadata_preview_download_' + str(index)] = artifact['path']
        self.refresh()

    def assertValid(self):
        result = pkg.validate(self.root, True)
        self.assertTrue(result['valid'], result)
        return result

    def test_modern_tag_only_release_real_media_and_raw_binding(self):
        result = self.assertValid()
        self.assertNotEqual(self.base_ah, self.ah)
        self.assertEqual(result['audio_metadata_verification']['pcm'], chapters.pcm(self.root / 'audio.mp3'))
        self.assertEqual(chapters.encoded_audio(self.root / 'audio.mp3'), chapters.encoded_audio(self.root / 'tagged.mp3'))
        self.assertFalse(result['audio_metadata_verification']['new_asr_performed'])
        self.assertEqual(self.ep['artifacts']['raw_asr_json']['audio_sha256'], self.base_ah)
        self.assertEqual(self.ep['artifacts']['aligned_transcript']['audio_sha256'], self.ah)
        self.assertIn('<strong>A useful point</strong>', self.payload['description'])
        self.assertEqual(self.payload['description'].count('本集章节'), 1)
        self.assertNotIn('Fixture notes', self.payload['description'])

    def test_lineage_report_stale_even_with_refreshed_artifacts_and_reviews(self):
        self.lineage['pcm']['sha256'] = '0' * 64
        self.write('metadata-lineage.json', self.lineage); self.refresh()
        self.assertRejected('ID3 lineage differs from fresh verification')

    def test_lineage_wrong_base_role_even_with_refreshed_artifacts(self):
        self.names['base_delivery_audio'] = 'tagged.mp3'
        self.refresh(); self.assertRejected('ID3 lineage binding mismatch')

    def test_lineage_wrong_tagged_hash_even_with_refreshed_artifacts(self):
        self.lineage['tagged_audio_sha256'] = self.base_ah
        self.write('metadata-lineage.json', self.lineage); self.refresh()
        self.assertRejected('ID3 lineage binding mismatch')

    def test_lineage_encoded_audio_mutation_is_not_tag_only(self):
        # Recreate the base with another real signal and rebind its metadata hash.
        base = self.root / 'audio.mp3'; base.unlink()
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=660:duration=3',
                        '-af', 'volume=2.0', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '192k', str(base)], check=True)
        self.base_ah = pkg.sha(base); self.lineage['base_audio_sha256'] = self.base_ah
        self.write('metadata-lineage.json', self.lineage); self.refresh()
        self.assertRejected('Encoded audio changed beyond ID3 metadata')

    def test_chapter_input_must_equal_enrichment_after_full_rebuild(self):
        self.content['chapters'][0]['title'] = 'Different public chapter'
        self.rebuild()
        self.assertRejected('embedded chapter input differs from enrichment')

    def test_chapter_report_cannot_claim_unembedded_title(self):
        self.lineage['chapter_input'][0]['title'] = 'Not embedded'
        self.lineage['chapters'][0]['title'] = 'Not embedded'
        self.write('metadata-lineage.json', self.lineage); self.refresh()
        self.assertRejected('Embedded chapters differ')

    def test_raw_asr_must_bind_base_not_new_tagged_hash(self):
        self.ep['artifacts']['raw_asr_json']['audio_sha256'] = self.ah
        self.write('episode.json', self.ep)
        for ref in self.ep['reviews']:
            receipt = pkg.read(self.root / ref); receipt['review_context_sha256'] = pkg.review_context(self.ep); self.write(ref, receipt)
        self.assertRejected('missing/stale audio lineage: raw_asr_json')

    def test_canonical_transcript_and_ledger_must_bind_tagged_hash(self):
        for path, expected in [('aligned.json', 'stale transcript binding'), ('corrections.json', 'correction ledger stale/invalid')]:
            with self.subTest(path=path):
                original = pkg.read(self.root / path)
                wrong = copy.deepcopy(original); wrong['audio_sha256'] = self.base_ah
                self.write(path, wrong); self.refresh(); self.assertRejected(expected)
                self.write(path, original); self.refresh()

    def test_sample_edit_dispatch_uses_base_audio_and_copied_rebound_hashes_mock_verifier(self):
        aligned = pkg.read(self.root / 'aligned.json')
        aligned.update(provenance_kind='sample_edit_derived_transcription', edit_lineage_path='edit-lineage.json')
        self.write('aligned.json', aligned)
        original_asr_audio_hash = 'c' * 64  # Distinct pre-edit source; proof supplied by the explicit mock.
        self.write('edit-lineage.json', {'source_audio_sha256': original_asr_audio_hash, 'evidence': {},
                                        'fixture': 'MOCK sample-edit verifier; no actual edit proof claimed'})
        self.names['edit_lineage'] = 'edit-lineage.json'; self.refresh()
        for role in ['raw_asr_json', 'raw_asr_txt']:
            self.ep['artifacts'][role]['audio_sha256'] = original_asr_audio_hash
        self.write('episode.json', self.ep)
        for ref in self.ep['reviews']:
            receipt = pkg.read(self.root / ref); receipt['review_context_sha256'] = pkg.review_context(self.ep); self.write(ref, receipt)
        verifier = Mock(return_value={'fixture_mock': True})
        original_spec = importlib.util.spec_from_file_location

        class MockDerivedLoader(importlib.abc.Loader):
            def create_module(self, spec):
                return None

            def exec_module(self, module):
                module.verify = verifier

        def route(name, path, *args, **kwargs):
            if name == 'v2_edit_derived_validator':
                return importlib.util.spec_from_loader(name, MockDerivedLoader())
            return original_spec(name, path, *args, **kwargs)

        with patch.object(pkg.importlib.util, 'spec_from_file_location', side_effect=route):
            result = self.assertValid()
        self.assertEqual(result['edit_derived_verification'], {'fixture_mock': True})
        verifier.assert_called_once()
        root, lineage, check_aligned, check_ledger, raw_path, base_audio = verifier.call_args.args
        self.assertEqual(root, self.root)
        self.assertEqual(base_audio, self.root / 'audio.mp3')
        self.assertEqual(raw_path, self.root / 'raw.json')
        self.assertEqual(check_aligned['audio_sha256'], self.base_ah)
        self.assertEqual(check_ledger['audio_sha256'], self.base_ah)
        self.assertEqual(lineage['source_audio_sha256'], original_asr_audio_hash)
        self.assertEqual(pkg.read(self.root / 'aligned.json')['audio_sha256'], self.ah)
        self.assertEqual(pkg.read(self.root / 'corrections.json')['audio_sha256'], self.ah)


if __name__ == '__main__':
    unittest.main()
