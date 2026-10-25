"""Real silent media tests exercise intake, not listening acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'startup.py'


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'new-user-home'
        self.home.mkdir()
        self.episode = self.root / 'episode'
        self.episode.mkdir()
        self.config = self.root / 'config.json'
        self.env = dict(os.environ, HOME=str(self.home))
        for k in list(self.env):
            if any(s in k for s in ('TOKEN', 'API_KEY', 'SECRET', 'PODCAST', 'WHISPER')):
                self.env.pop(k)

    def run_cli(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                           cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertNotIn('Traceback', p.stderr + p.stdout)
        return p.returncode, json.loads(p.stdout)

    def setup_config(self):
        tool = shutil.which('ffmpeg') or sys.executable
        return self.run_cli('setup', '--config', self.config, '--workspace', 'workspace',
                            '--language', 'en', '--whisper-cli', tool,
                            '--whisper-model', 'model.bin')

    def media(self, layout='stereo'):
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('FFmpeg/ffprobe required for real geometry tests')
        source = self.episode / 'source.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'anullsrc=r=48000:cl=' + layout, '-t', '0.1', str(source)], check=True)
        self.setup_config()
        (self.root / 'model.bin').write_bytes(b'test availability only')
        self.metadata()
        return source

    def metadata(self, roles=None, intent='finished audio; transcription only', wfp=''):
        roles = roles if roles is not None else ['Alice: absolute stream 0, audio-relative index 0, left',
                          'Bob: absolute stream 0, audio-relative index 0, right']
        (self.episode / '_meta.md').write_text(
            '# Episode handoff\n- Episode: New show / ep1\n- Original media: source.wav\n'
            '- Edit intent: ' + intent + '\n- Rough-cut WFP: ' + wfp +
            '\n- Speakers:\n' + ''.join('  - ' + r + '\n' for r in roles), encoding='utf-8')

    def check(self, *extra):
        return self.run_cli('check', '--episode-dir', self.episode, '--config', self.config,
                            '--mode', 'local', *extra)

    def test_setup_minimal_and_no_overwrite(self):
        self.assertEqual(self.setup_config()[0], 0)
        data = json.loads(self.config.read_text())
        self.assertEqual(set(data), {'workspace', 'language', 'whisper_cli', 'whisper_model'})
        self.assertEqual(data['workspace'], str((self.root / 'workspace').resolve()))
        before = self.config.read_bytes()
        self.assertEqual(self.setup_config()[0], 2)
        self.assertEqual(before, self.config.read_bytes())

    def test_missing_inputs_batch(self):
        code, report = self.check()
        codes = {i['code'] for i in report['issues']}
        self.assertEqual(code, 2)
        self.assertTrue({'missing_or_invalid_config', 'missing_meta', 'missing_original_media',
                         'missing_rough-cut_wfp', 'missing_speakers', 'missing_whisper_model'} <= codes)

    def test_local_real_geometry_not_acceptance(self):
        self.media()
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['audio_review'], 'unverified')
        self.assertEqual(report['local_acceptance'], 'unverified')
        self.assertFalse(report['publish_authorized'])
        source = next(f for f in report['files'] if f['kind'] == 'source')
        self.assertEqual(source['audio_streams'][0]['channels'], 2)
        self.assertEqual(source['audio_streams'][0]['sample_rate'], '48000')
        self.assertEqual(len(source['sha256']), 64)
        self.assertEqual(report['next_stage'], 'transcription_and_audio_review')

    def test_conflict_and_out_of_range_batch(self):
        self.media()
        self.metadata(['Alice: absolute stream 0, audio-relative index 0, left',
                       'Bob: absolute stream 0, audio-relative index 0, left',
                       'Chris: absolute stream 9, audio-relative index 2, right'])
        _, report = self.check()
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue({'role_conflict', 'role_stream_mismatch'} <= {i['code'] for i in report['issues']})

    def test_publish_does_not_authorize(self):
        self.media()
        _, report = self.run_cli('check', '--episode-dir', self.episode, '--config', self.config, '--mode', 'publish')
        self.assertFalse(report['publish_authorized'])
        self.assertIn('missing_target_show_id', [i['code'] for i in report['issues']])
        self.assertIn('publication_identity_unverified', [i['code'] for i in report['pending_checks']])

    def test_publish_complete_intake_proceeds_without_new_user_gate(self):
        self.media()
        meta = self.episode / '_meta.md'
        meta.write_text(meta.read_text() + '- Target show ID: 123\n')
        code, report = self.run_cli('check', '--episode-dir', self.episode, '--config', self.config, '--mode', 'publish')
        self.assertEqual(code, 0, report)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(report['issues'], [])
        self.assertEqual(report['next_stage'], 'transcription_and_audio_review')
        self.assertFalse(report['publish_authorized'])
        self.assertTrue({'publication_identity_unverified', 'publication_authority_unverified'} <= {i['code'] for i in report['pending_checks']})

    def test_protect_source_meta_config_and_existing_report(self):
        source = self.media()
        for path in (source, self.config, self.episode / '_meta.md'):
            before = path.read_bytes()
            self.assertEqual(self.check('--output', path)[0], 2)
            self.assertEqual(before, path.read_bytes())
        out = self.root / 'report.json'
        self.assertEqual(self.check('--output', out)[0], 0)
        self.assertEqual(json.loads(out.read_text())['status'], 'ready')
        before = out.read_bytes()
        self.assertEqual(self.check('--output', out)[0], 2)
        self.assertEqual(before, out.read_bytes())
        alias = self.root / 'alias'
        os.link(source, alias)
        self.assertEqual(self.check('--output', alias)[0], 2)

    def test_unknown_config_no_value_leak(self):
        self.config.write_text('{"api_key":"DO_NOT_ECHO"}')
        _, report = self.check()
        self.assertIn('unknown_config_keys', [i['code'] for i in report['issues']])
        self.assertNotIn('DO_NOT_ECHO', json.dumps(report))

    def test_unsupported_meta_and_bad_json(self):
        (self.episode / '_meta.md').write_text('unrecognized format')
        self.config.write_text('[]')
        _, report = self.check()
        self.assertIn('unsupported_template', [i['code'] for i in report['issues']])
        self.assertIn('missing_or_invalid_config', [i['code'] for i in report['issues']])

    def test_wfp_inventory_is_explicitly_unverified(self):
        self.media()
        with zipfile.ZipFile(self.episode / 'cut.wfp', 'w') as z:
            z.writestr('project.json', '{}')
        self.metadata(intent='preserve my rough-cut deletions', wfp='cut.wfp')
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(report['issues'], [])
        self.assertEqual(len(report['roles']), 2)
        self.assertEqual(report['readiness_scope'], 'ready_to_start_validate_wfp_structure')
        self.assertIn('wfp_semantics_unverified', [c['code'] for c in report['pending_checks']])
        self.assertEqual(report['wfp']['source_references'], 'unverified')
        self.assertEqual(report['wfp']['unknown_dsp'], 'unverified')
        self.assertEqual(report['next_stage'], 'validate_wfp_structure')

    def test_finished_mono_without_speakers_or_wfp(self):
        self.media(layout='mono')
        (self.episode / '_meta.md').write_text(
            '# Episode handoff\n- Episode: New show / final\n'
            '- Original media: source.wav\n- Edit intent: finished audio; transcription only\n')
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(report['issues'], [])
        self.assertEqual(report['roles'], [])
        self.assertNotIn('wfp', report)
        self.assertEqual(report['next_stage'], 'transcription_and_audio_review')
        self.assertEqual(report['audio_review'], 'unverified')
        self.assertEqual(report['local_acceptance'], 'unverified')

    def test_dual_mono_verification_is_agent_pending_work(self):
        self.media()
        with zipfile.ZipFile(self.episode / 'cut.wfp', 'w') as z:
            z.writestr('project.json', '{}')
        self.metadata(['Host: absolute stream 0, audio-relative index 0, dual mono'],
                      'preserve my rough-cut deletions', 'cut.wfp')
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['issues'], [])
        self.assertIn('dual_mono_unverified', [c['code'] for c in report['pending_checks']])
        self.assertEqual(report['next_stage'], 'validate_wfp_structure')

    def test_rough_cut_still_requires_speakers(self):
        self.media()
        self.metadata([], 'preserve rough-cut deletions')
        _, report = self.check()
        self.assertEqual(report['status'], 'needs_input')
        self.assertIn('missing_speakers', [i['code'] for i in report['issues']])

    def test_all_config_paths_must_be_absolute(self):
        self.media()
        baseline = json.loads(self.config.read_text())
        for key in ('workspace', 'whisper_cli', 'whisper_model', 'transistor_cli',
                    'transistor_cli_repo', 'artwork_registry', 'planning_profiles_dir'):
            with self.subTest(key=key):
                self.config.write_text(json.dumps(dict(baseline, **{key: 'relative-private-value'})))
                code, report = self.check()
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'blocked')
                self.assertIn('relative_config_path', [i['code'] for i in report['issues']])
                self.assertNotIn('relative-private-value', json.dumps(report))

    def test_valid_show_config(self):
        self.media()
        cfg = json.loads(self.config.read_text())
        cfg['shows'] = {'00123': {'author': 'New Host', 'brand_name': 'New Show', 'brand_tagline': ''}, '2': {}}
        self.config.write_text(json.dumps(cfg))
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertNotIn('New Host', json.dumps(report))

    def test_invalid_show_config(self):
        self.media()
        baseline = json.loads(self.config.read_text())
        for shows in ([], {'abc': {}}, {'1': []}, {'1': {'extra': 'PRIVATE'}},
                      {'1': {'author': ''}}, {'1': {'author': 5}},
                      {'1': {'brand_name': ' '}}, {'1': {'brand_tagline': 5}}):
            with self.subTest(shows=shows):
                self.config.write_text(json.dumps(dict(baseline, shows=shows)))
                code, report = self.check()
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any(i['code'].startswith('invalid_show') for i in report['issues']))
                self.assertNotIn('PRIVATE', json.dumps(report))

    def test_duplicate_meta_fields_block_without_selecting_any(self):
        self.media()
        meta = self.episode / '_meta.md'
        meta.write_text(meta.read_text() + '- Episode: conflicting episode\n'
                        '- Original media: missing-private-source.wav\n'
                        '- Original media: source.wav\n'
                        '- Edit intent: preserve rough-cut deletions\n')
        code, report = self.check()
        self.assertEqual(code, 2)
        self.assertEqual(report['status'], 'blocked')
        duplicates = [i for i in report['issues'] if i['code'] == 'duplicate_meta_fields']
        self.assertEqual(len(duplicates), 1)
        self.assertIn('Original media', duplicates[0]['action'])
        self.assertNotIn('missing-private-source', json.dumps(report))
        self.assertFalse(any(f['kind'] == 'source' for f in report['files']))
        self.assertEqual(report['next_stage'], 'resolve_intake')

    def test_placeholder_multisource_and_bad_wfp(self):
        self.media()
        self.metadata(['<speaker>: absolute stream <N>, audio-relative index <M>, left'],
                      'preserve rough-cut', 'bad.wfp')
        meta = self.episode / '_meta.md'
        meta.write_text(meta.read_text().replace('source.wav', 'source.wav; missing.wav'))
        (self.episode / 'bad.wfp').write_text('not a zip')
        _, report = self.check()
        codes = {i['code'] for i in report['issues']}
        self.assertTrue({'invalid_role', 'ambiguous_sources', 'missing_source', 'invalid_wfp'} <= codes)


if __name__ == '__main__':
    unittest.main()
