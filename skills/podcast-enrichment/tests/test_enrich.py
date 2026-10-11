import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('enrich', Path(__file__).parents[1]/'scripts/enrich.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root/'cover.png').write_bytes(b'fixture-cover')
        (self.root/'audio.mp3').write_bytes(b'fixture-audio')
        self.data = dict(title='Test episode',show_title='Show',summary='Summary',description='Description',show_notes='One\n\nTwo',launch_copy='Copy all\nlines',language='en',ai_disclosure='Voice provenance unknown.',cover_path='cover.png',audio_path='audio.mp3',duration=20,segments=[dict(id='s1',start=0,end=10,text='First line'),dict(id='s2',start=10,end=20,text='Unique final paragraph')],chapters=[dict(start=0,title='First',summary='Opening',source_segment_ids=['s1'])],reading_transcript=[dict(text='First line. Unique final paragraph.',source_segment_ids=['s1','s2'])],resources=[],metadata=dict(reading_language='en',reading_mode='edited',corrections=[]))
    def build(self):
        source=self.root/'content.json';source.write_text(json.dumps(self.data))
        return m.build(self.data,self.root,self.root/'preview/episode.html',source)
    def test_full_transcript_and_real_manifest(self):
        manifest=self.build();page=(self.root/'preview/episode.html').read_text()
        self.assertIn('Unique final paragraph',page)
        self.assertEqual(page.count('data-source-id='),2)
        self.assertIn('Unique final paragraph',(self.root/'preview/transcript.txt').read_text())
        self.assertIn('Unique final paragraph',(self.root/'preview/reading-transcript.txt').read_text())
        self.assertFalse(manifest['validation']['experience_ready'])
        for item in manifest['artifacts']: self.assertEqual(item['sha256'],m.digest(self.root/item['path']))
    def test_xss_in_all_text_surfaces(self):
        attack='</textarea><script>alert("injected")</script><img src=x onerror=alert(1)>'
        self.data['title']=attack;self.data['segments'][1]['text']=attack
        self.data['show_notes']=attack;self.data['launch_copy']=attack
        self.data['reading_transcript'][0]['text']=attack
        self.build();page=(self.root/'preview/episode.html').read_text()
        self.assertNotIn('<script>alert(',page)
        self.assertNotIn('<img src=x',page)
        self.assertIn('&lt;script&gt;alert',page)
        self.assertEqual((self.root/'preview/show-notes.txt').read_text(),attack)
    def test_javascript_url_rejected(self):
        self.data['resources']=[dict(title='Attack',url='javascript:alert(1)')]
        with self.assertRaises(ValueError):self.build()
    def test_traversal_and_absolute_paths(self):
        for unsafe in ('../audio.mp3','/tmp/audio.mp3','nested/../../audio.mp3','..\\audio.mp3'):
            with self.subTest(unsafe=unsafe):
                self.data['audio_path']=unsafe
                with self.assertRaises(ValueError):self.build()
    def test_symlink_inside_and_outside_rejected(self):
        (self.root/'alias.mp3').symlink_to(self.root/'audio.mp3')
        self.data['audio_path']='alias.mp3'
        with self.assertRaises(ValueError):self.build()
        (self.root/'alias.mp3').unlink();(self.root/'alias.mp3').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):self.build()
    def test_missing_artifact(self):
        (self.root/'cover.png').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):self.build()
    def test_partial_reading_and_unknown_refs(self):
        for refs in (['s1'],['s1','missing']):
            self.data['reading_transcript'][0]['source_segment_ids']=refs
            with self.assertRaises(ValueError):self.build()
    def test_language_and_correction_evidence(self):
        self.data['metadata']['reading_language']='zh'
        with self.assertRaisesRegex(ValueError,'translation'):self.build()
        self.data['metadata']['reading_mode']='translation'
        self.data['metadata']['corrections']=[dict(source_segment_id='missing',original='one',corrected='two',reason='reason')]
        with self.assertRaisesRegex(ValueError,'source'):self.build()
    def test_timeline(self):
        for value in (-1,float('nan'),float('inf'),True,25):
            self.data['segments'][1]['end']=value
            with self.assertRaises(ValueError):self.build()
    def test_output_symlink_and_input_collision(self):
        (self.root/'preview').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):self.build()
        (self.root/'preview').unlink()
        self.data['assets']=[dict(title='Content',path='content.json',kind='text')]
        source=self.root/'content.json';source.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):m.build(self.data,self.root,self.root/'../escape.html',source)
        (self.root/'source.html').write_text('source')
        self.data['assets']=[dict(title='Source',path='source.html',kind='download')]
        with self.assertRaisesRegex(ValueError,'collides'):m.build(self.data,self.root,self.root/'source.html',source)
    def test_no_fabricated_verified_status(self):
        self.build();page=(self.root/'preview/episode.html').read_text()
        self.assertIn('本地预览 · 待核验',page)
        self.assertNotIn('代理已核验',page)
        self.assertNotIn('@@',page)
    def test_canonical_integer_ids(self):
        self.data['segments'][0]['id']=0;self.data['segments'][1]['id']=1
        self.data['chapters'][0]['source_segment_ids']=[0]
        self.data['reading_transcript'][0]['source_segment_ids']=[0,1]
        self.build()
        self.data['segments'][1]['id']='0'
        with self.assertRaisesRegex(ValueError,'duplicate'):self.build()
    def test_extra_text_fully_rendered(self):
        extra='Later material\n' * 200
        (self.root/'extra.txt').write_text(extra)
        self.data['assets']=[dict(title='Complete extra',path='extra.txt',kind='text')]
        self.build();page=(self.root/'preview/episode.html').read_text()
        self.assertEqual(page.count('Later material'),200)

if __name__=='__main__':unittest.main()
