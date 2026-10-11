import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('plan_artwork', Path(__file__).resolve().parents[1] / 'scripts/plan_artwork.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ArtworkProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.brief = {'show_id': 'other-123', 'show_name': 'Another Podcast', 'asset_type': 'show', 'composition': 'A book discussed at a table', 'copy': ['Another Podcast'], 'source_refs': ['approved-brand.md']}
        self.profile = {'schema_version': '1.0', 'profile_id': 'other-show', 'revision': 'v1', 'show_id': 'other-123', 'brand': 'Another Podcast', 'shared': {'palette': {'ink': '#252525'}}, 'styles': {'etching': {'id': 'etch', 'name': 'Etching', 'medium': 'ink etching', 'composition_rule': 'one focal object'}}, 'asset_rules': {'show': {'hierarchy': 'large name'}}}
    def write(self):
        path = self.root / 'profile.json'
        path.write_text(json.dumps(self.profile))
        return path
    def test_dynamic_style_and_show(self):
        output = module.plan(self.brief, self.write())
        self.assertEqual(output['candidates'][0]['style_id'], 'etch')
        self.assertNotIn('Geek', output['candidates'][0]['prompt'])
        self.assertFalse(output['publication_authorized'])
    def test_neutral_fallback(self):
        output = module.plan(self.brief)
        self.assertEqual(output['profile_resolution'], 'neutral-fallback')
        self.assertNotIn('Martin', output['candidates'][0]['prompt'])
    def test_missing_explicit_never_falls_back(self):
        with self.assertRaises(FileNotFoundError): module.plan(self.brief, self.root / 'missing.yaml')
    def test_wrong_show_rejected(self):
        self.profile['show_id'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'show_id'): module.plan(self.brief, self.write())
    def test_hash_mismatch_rejected(self):
        (self.root / 'ref.png').write_bytes(b'fake')
        (self.root / 'manifest.json').write_text(json.dumps([{'path': 'ref.png', 'sha256': '0'*64}]))
        self.profile['reference_manifest'] = 'manifest.json'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): module.plan(self.brief, self.write())
    def test_escaping_reference_rejected(self):
        self.profile['composition_prompt'] = '../escape.md'
        with self.assertRaisesRegex(ValueError, 'escaping'): module.plan(self.brief, self.write())
    def test_missing_source_rejected(self):
        self.brief['source_refs'] = []
        with self.assertRaisesRegex(ValueError, 'source_refs'): module.plan(self.brief)
    def test_unknown_style_rejected(self):
        self.brief['style_keys'] = ['A']
        with self.assertRaisesRegex(ValueError, 'style_keys'): module.plan(self.brief, self.write())

    def test_registered_profile_automatic(self):
        profile = self.write()
        registry = self.root / 'registry.json'
        registry.write_text(json.dumps({'schema_version': '1.0', 'profiles': [{'show_id': 'other-123', 'profile_ref': profile.name}]}))
        output = module.plan(self.brief, registry_path=registry)
        self.assertEqual(output['profile_resolution'], 'registry-profile')
        self.assertEqual(output['candidates'][0]['style_id'], 'etch')
    def test_registered_invalid_not_fallback(self):
        registry = self.root / 'registry.json'
        registry.write_text(json.dumps({'schema_version': '1.0', 'profiles': [{'show_id': 'other-123', 'profile_ref': 'missing.json'}]}))
        with self.assertRaises(FileNotFoundError): module.plan(self.brief, registry_path=registry)
    def test_design_system_fallback(self):
        self.brief['design_system'] = {'shared': {'palette': {'purple': '#552288'}}}
        self.brief['design_system_source_refs'] = ['brand-approved.md']
        output = module.plan(self.brief)
        self.assertEqual(output['profile_resolution'], 'design-system-fallback')
        self.assertEqual(output['temporary_profile']['shared']['palette']['purple'], '#552288')
    def test_design_system_requires_provenance(self):
        self.brief['design_system'] = {'shared': {'palette': {'purple': '#552288'}}}
        with self.assertRaisesRegex(ValueError, 'source references'): module.plan(self.brief)
    def run_cli(self, *argv):
        import subprocess, sys
        return subprocess.run([sys.executable, '-B', str(Path(module.__file__)), *argv], capture_output=True, text=True, env={**os.environ, 'PODCAST_CONFIG': str(self.root / 'empty.json')})
    def prepare_cli(self):
        (self.root / 'empty.json').write_text('{}')
        self.profile.update(reference_manifest='manifest.json', composition_prompt='composition.txt')
        (self.root / 'ref.png').write_bytes(b'ref'); (self.root / 'composition.txt').write_text('guide')
        import hashlib
        (self.root / 'manifest.json').write_text(json.dumps([{'path': 'ref.png', 'sha256': hashlib.sha256(b'ref').hexdigest()}]))
        for style in self.profile['styles'].values(): style['primary_reference'] = 'ref.png'
        profile = self.write(); brief = self.root / 'brief.json'; brief.write_text(json.dumps(self.brief)); return brief, profile
    def test_output_never_overwrites_any_input(self):
        brief, profile = self.prepare_cli()
        for victim in (brief, profile, self.root / 'manifest.json', self.root / 'composition.txt', self.root / 'ref.png'):
            before = victim.read_bytes()
            with self.subTest(victim=victim.name):
                result = self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(victim), '--overwrite')
                self.assertNotEqual(result.returncode, 0); self.assertIn('overwrite an input', result.stderr); self.assertEqual(before, victim.read_bytes())
    def test_output_symlink_or_hardlink_to_an_input_is_refused(self):
        brief, profile = self.prepare_cli(); before = profile.read_bytes()
        link = self.root / 'plan-link.json'; link.symlink_to(profile)
        self.assertNotEqual(self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(link), '--overwrite').returncode, 0)
        hard = self.root / 'plan-hard.json'; os.link(profile, hard)
        result = self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(hard), '--overwrite')
        self.assertNotEqual(result.returncode, 0); self.assertEqual(before, profile.read_bytes()); self.assertEqual(before, hard.read_bytes())
    def test_new_output_is_created_and_existing_plan_needs_overwrite(self):
        brief, profile = self.prepare_cli(); out = self.root / 'plans' / 'plan.json'
        first = self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(out)); self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(out.read_text())['profile_resolution'], 'explicit-profile')
        self.assertNotEqual(self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(out)).returncode, 0)
        self.assertEqual(self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(out), '--overwrite').returncode, 0)
        self.assertEqual([p.name for p in self.root.glob('plans/.plan.*')], [])
    def test_explicit_profile_is_not_broken_by_an_unused_bad_default_registry(self):
        brief, profile = self.prepare_cli(); out = self.root / 'plan-ok.json'
        import subprocess, sys
        result = subprocess.run([sys.executable, '-B', str(Path(module.__file__)), '--brief', str(brief), '--profile', str(profile), '--output', str(out)],
                                capture_output=True, text=True, env={**os.environ, 'PODCAST_CONFIG': str(self.root / 'does-not-exist.json')})
        self.assertEqual(result.returncode, 0, result.stderr)
    def test_registry_used_for_resolution_is_protected_from_being_overwritten(self):
        brief, profile = self.prepare_cli(); registry = self.root / 'registry.json'
        registry.write_text(json.dumps({'schema_version': '1.0', 'profiles': [{'show_id': 'other-123', 'profile_ref': profile.name}]})); before = registry.read_bytes()
        result = self.run_cli('--brief', str(brief), '--profile-registry', str(registry), '--output', str(registry), '--overwrite')
        self.assertNotEqual(result.returncode, 0); self.assertEqual(before, registry.read_bytes())
    def test_output_directory_symlink_is_refused(self):
        brief, profile = self.prepare_cli(); real = self.root / 'real-dir'; real.mkdir(); (self.root / 'linked-dir').symlink_to(real)
        result = self.run_cli('--brief', str(brief), '--profile', str(profile), '--output', str(self.root / 'linked-dir' / 'plan.json'))
        self.assertNotEqual(result.returncode, 0); self.assertEqual(list(real.iterdir()), [])
    def test_relative_registry_in_environment_is_rejected(self):
        saved = os.environ.get('PODCAST_ARTWORK_PROFILE_REGISTRY'); os.environ['PODCAST_ARTWORK_PROFILE_REGISTRY'] = 'relative-registry.json'
        try:
            with self.assertRaisesRegex(ValueError, 'absolute'): module.discover_registry()
        finally:
            if saved is None: os.environ.pop('PODCAST_ARTWORK_PROFILE_REGISTRY', None)
            else: os.environ['PODCAST_ARTWORK_PROFILE_REGISTRY'] = saved
    def test_registry_is_explicit_only_never_discovered_from_cwd(self):
        nested = self.root / 'a' / 'b' / 'notes' / 'brand'; nested.mkdir(parents=True)
        (nested / 'artwork-profiles.json').write_text(json.dumps({'schema_version': '1.0', 'profiles': []}))
        empty = self.root / 'c.json'; empty.write_text('{}')
        old_cwd = os.getcwd(); saved = {k: os.environ.get(k) for k in ('PODCAST_CONFIG', 'PODCAST_ARTWORK_PROFILE_REGISTRY')}
        try:
            os.chdir(self.root); os.environ['PODCAST_CONFIG'] = str(empty); os.environ.pop('PODCAST_ARTWORK_PROFILE_REGISTRY', None)
            self.assertIsNone(module.discover_registry())
            reg = self.root / 'reg.json'; reg.write_text('{}')
            cfg = self.root / 'c2.json'; cfg.write_text(json.dumps({'artwork_registry': str(reg)}))
            os.environ['PODCAST_CONFIG'] = str(cfg); self.assertEqual(module.discover_registry(), reg.resolve())
            other = self.root / 'env.json'; other.write_text('{}'); os.environ['PODCAST_ARTWORK_PROFILE_REGISTRY'] = str(other)
            self.assertEqual(module.discover_registry(), other.resolve())
        finally:
            os.chdir(old_cwd)
            for k, v in saved.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v


if __name__ == '__main__': unittest.main()
