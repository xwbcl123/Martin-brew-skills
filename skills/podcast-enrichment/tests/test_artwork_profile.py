import importlib.util
import json
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

if __name__ == '__main__': unittest.main()
