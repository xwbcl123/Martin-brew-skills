"""Guards the shared personal-config block that every consumer script embeds verbatim, and its behaviour."""
import json
import os
import re
import site
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
MARK_BEGIN = '# BEGIN ' + 'podcast-config'
MARK_END = '# END ' + 'podcast-config'
CONSUMERS = [
    'podcast-enrichment/scripts/enrich.py',
    'podcast-enrichment/scripts/plan_artwork.py',
    'podcast-production-workflow/scripts/run_whisper_raw.py',
    'podcast-production-workflow/scripts/validate_benchmark_protocol.py',
    'podcast-release-package/scripts/v2/assemble.py',
    'podcast-topic-planning/scripts/validate_profile.py',
    'podcast-transcription/scripts/transcription.py',
    'podcast-transistor-publish/scripts/publish.py',
]


def block_of(relative):
    text = (SKILLS / relative).read_text(encoding='utf-8')
    match = re.search('^' + re.escape(MARK_BEGIN) + '.*?^' + re.escape(MARK_END), text, re.S | re.M)
    assert match, relative
    return match.group(0)


def load_block():
    namespace = {}
    exec(compile(block_of(CONSUMERS[0]), 'podcast-config', 'exec'), namespace)
    return namespace


class ConfigCopyTests(unittest.TestCase):
    def test_the_consumer_list_is_complete(self):
        found = sorted(str(p.relative_to(SKILLS)) for p in SKILLS.glob('podcast-*/scripts/**/*.py')
                       if '__pycache__' not in p.parts and 'tests' not in p.parts and not p.name.startswith('test_')
                       and re.search('^' + re.escape(MARK_BEGIN), p.read_text(encoding='utf-8'), re.M))
        self.assertEqual(found, sorted(CONSUMERS))

    def test_every_copy_is_byte_identical(self):
        first = block_of(CONSUMERS[0])
        for relative in CONSUMERS[1:]:
            with self.subTest(path=relative):
                self.assertEqual(first, block_of(relative))

    def test_importing_a_consumer_never_reads_or_requires_the_config(self):
        with tempfile.TemporaryDirectory() as home:
            env = {'HOME': home, 'PATH': '/usr/bin:/bin', 'PYTHONUSERBASE': site.getuserbase(), 'PODCAST_CONFIG': str(Path(home) / 'does-not-exist.json'),
                   'PYTHONDONTWRITEBYTECODE': '1'}
            code = ("import importlib.util,sys;s=importlib.util.spec_from_file_location('m',sys.argv[1]);m=importlib.util.module_from_spec(s);"
                    "sys.path.insert(0,sys.argv[2]);s.loader.exec_module(m)")
            for relative in CONSUMERS:
                path = SKILLS / relative
                with self.subTest(path=relative):
                    result = subprocess.run([sys.executable, '-B', '-c', code, str(path), str(path.parent)], env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr[-400:])

    def test_example_config_matches_the_known_keys(self):
        example = json.loads((SKILLS / 'podcast-release-package/references/config.example.json').read_text())
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / 'c.json'; cfg.write_text(json.dumps(example))
            os.environ['PODCAST_CONFIG'] = str(cfg)
            try:
                loaded = load_block()['_podcast_cfg']()
            finally:
                os.environ.pop('PODCAST_CONFIG', None)
        self.assertEqual(set(loaded), set(example))


class ConfigBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_block(); self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.saved = {k: os.environ.get(k) for k in ('PODCAST_CONFIG', 'WHISPER_CLI', 'WHISPER_MODEL', 'PODCAST_WORKSPACE', 'TRANSISTOR_CLI', 'HOME')}
        for k in self.saved: os.environ.pop(k, None)
        os.environ['HOME'] = str(self.root)
        self.addCleanup(self.restore)

    def restore(self):
        for k, v in self.saved.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v

    def config(self, value, name='c.json'):
        path = self.root / name; path.write_text(value if isinstance(value, str) else json.dumps(value)); os.environ['PODCAST_CONFIG'] = str(path); return path

    def tool(self, directory, name, executable=True):
        path = self.root / directory / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('#!/bin/sh\necho "$0"\n'); path.chmod(0o755 if executable else 0o644); return path

    def test_missing_default_file_is_empty_but_explicit_missing_file_errors(self):
        self.assertEqual(self.ns['_podcast_cfg']()['shows'], {})
        os.environ['PODCAST_CONFIG'] = str(self.root / 'nope.json')
        with self.assertRaisesRegex(SystemExit, 'missing file'): self.ns['_podcast_cfg']()

    def test_config_selector_must_be_non_empty_and_absolute(self):
        for bad in ('', '   ', 'relative.json', './c.json'):
            with self.subTest(bad=bad):
                self.ns['_podcast_cfg'].__defaults__[0].clear(); os.environ['PODCAST_CONFIG'] = bad
                with self.assertRaisesRegex(SystemExit, 'absolute'): self.ns['_podcast_cfg']()

    def test_default_location_under_home(self):
        d = self.root / '.config/podcast-skills'; d.mkdir(parents=True); (d / 'config.json').write_text(json.dumps({'language': 'zh'}))
        self.assertEqual(self.ns['_podcast_cfg']()['language'], 'zh')

    def test_rejects_malformed_and_unknown_and_wrong_types(self):
        for bad in ('{', '[]', {'surprise': 'x'}, {'whisper_cli': ''}, {'whisper_cli': 5}, {'whisper_cli': 'relative/path'}, {'shows': []},
                    {'shows': {'abc': {}}}, {'shows': {'1': {'extra': 'x'}}}, {'shows': {'1': {'author': ''}}}, {'shows': {'1': {'brand_tagline': 5}}},
                    {'author': 'x'}, {'approved_by': 'x'}, {'show_id': '1'}, {'authorization': 'x'}):
            with self.subTest(bad=bad):
                self.ns['_podcast_cfg'].__defaults__[0].clear(); self.config(bad)
                with self.assertRaises(SystemExit): self.ns['_podcast_cfg']()

    def test_priority_cli_then_env_then_config(self):
        self.config({'whisper_cli': '/cfg/whisper'})
        pick = self.ns['_podcast_pick']
        self.assertEqual(pick(None, 'WHISPER_CLI', 'whisper_cli'), '/cfg/whisper')
        os.environ['WHISPER_CLI'] = '/env/whisper'; self.assertEqual(pick(None, 'WHISPER_CLI', 'whisper_cli'), '/env/whisper')
        self.assertEqual(pick('/cli/whisper', 'WHISPER_CLI', 'whisper_cli'), '/cli/whisper')

    def test_blank_provided_values_are_errors_not_unset(self):
        self.config({'whisper_cli': str(self.tool('cfg', 'w'))})
        for cli, env in (('', None), ('  ', None), (None, ''), (None, ' ')):
            with self.subTest(cli=cli, env=env):
                os.environ.pop('WHISPER_CLI', None)
                if env is not None: os.environ['WHISPER_CLI'] = env
                with self.assertRaisesRegex(SystemExit, 'empty value'): self.ns['_podcast_tool'](cli, 'WHISPER_CLI', 'whisper_cli', 'sh')

    def test_explicit_tool_must_be_an_absolute_executable_and_never_falls_back_to_path(self):
        self.config({})
        with self.assertRaisesRegex(SystemExit, 'not an executable'): self.ns['_podcast_tool'](str(self.root / 'missing'), 'WHISPER_CLI', 'whisper_cli', 'sh')
        plain = self.tool('bin', 'plain', executable=False)
        with self.assertRaisesRegex(SystemExit, 'not an executable'): self.ns['_podcast_tool'](str(plain), 'WHISPER_CLI', 'whisper_cli', 'sh')
        real = self.tool('bin', 'whisper'); self.assertEqual(self.ns['_podcast_tool'](str(real), 'WHISPER_CLI', 'whisper_cli', 'definitely-not-installed'), str(real))

    def test_relative_explicit_value_is_rejected_even_when_cwd_and_path_have_the_same_name(self):
        self.config({}); cwd_tool = self.tool('cwd', 'probe-tool'); other = self.tool('pathdir', 'probe-tool')
        old_cwd, old_path = os.getcwd(), os.environ['PATH']
        try:
            os.chdir(cwd_tool.parent); os.environ['PATH'] = f'{other.parent}:{old_path}'
            with self.assertRaisesRegex(SystemExit, 'absolute'): self.ns['_podcast_tool']('probe-tool', 'WHISPER_CLI', 'whisper_cli', 'probe-tool')
            os.environ['WHISPER_CLI'] = 'probe-tool'
            with self.assertRaisesRegex(SystemExit, 'absolute'): self.ns['_podcast_tool'](None, 'WHISPER_CLI', 'whisper_cli', 'probe-tool')
        finally:
            os.chdir(old_cwd); os.environ['PATH'] = old_path

    def test_unset_tool_uses_path_lookup_returning_an_absolute_path_or_gives_actionable_error(self):
        self.config({})
        found = self.ns['_podcast_tool'](None, 'WHISPER_CLI', 'whisper_cli', 'sh'); self.assertTrue(os.path.isabs(found))
        with self.assertRaisesRegex(SystemExit, 'not found'): self.ns['_podcast_tool'](None, 'WHISPER_CLI', 'whisper_cli', 'definitely-not-installed')

    def test_model_resolution(self):
        model = self.root / 'models' / 'ggml-large-v3-q5_0.bin'; model.parent.mkdir(); model.write_bytes(b'm')
        self.config({'workspace': str(self.root)})
        self.assertEqual(self.ns['_podcast_model'](None), str(model))
        self.config({}, 'c2.json')
        with self.assertRaisesRegex(SystemExit, 'no Whisper model'): self.ns['_podcast_model'](None)
        with self.assertRaisesRegex(SystemExit, 'does not exist'): self.ns['_podcast_model'](str(self.root / 'x.bin'))
        with self.assertRaisesRegex(SystemExit, 'absolute'): self.ns['_podcast_model']('relative.bin')
        os.environ['PODCAST_WORKSPACE'] = 'relative-workspace'
        with self.assertRaisesRegex(SystemExit, 'absolute'): self.ns['_podcast_model'](None)

    def test_no_identity_or_approval_environment_variables_are_read(self):
        source = block_of(CONSUMERS[0])
        for forbidden in ('PODCAST_AUTHOR', 'PODCAST_SHOW_ID', 'APPROVED_BY', 'AUTHORIZATION'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
