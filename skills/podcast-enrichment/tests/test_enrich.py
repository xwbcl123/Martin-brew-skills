import copy
import importlib.util
import json
import os
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
    def test_english_controls_and_fallback(self):
        for language in ('en', 'EN-us', 'fr'):
            with self.subTest(language=language):
                self.data['language'] = language
                self.data['metadata']['reading_language'] = language
                self.build(); page = (self.root/'preview/episode.html').read_text()
                for label in ('Episode navigation', 'About this episode', 'Playback speed',
                              'Select a chapter to listen', 'Copy full notes', 'Copy full launch copy',
                              'Transcript versions', 'Edited reading transcript', 'Aligned transcript',
                              'Search transcripts', 'Search both full transcripts', 'Download reading transcript',
                              'Download aligned transcript', 'Download audio', 'Download chapters',
                              'Full text copied and verified', 'Clipboard could not be verified',
                              'Reading transcript: ${reading} matches', 'Jumped to ',
                              'Local preview · Pending verification', 'No external links provided.',
                              'Confirm that you reviewed these choices first.'):
                    self.assertIn(label, page)
                # No author Chinese in this fixture: all remaining Chinese would be UI leakage.
                self.assertFalse(__import__('re').search(r'[\u3400-\u9fff]', page))

    def test_chinese_ui_compatibility(self):
        for language in ('zh', 'zh-CN', 'ZH_hant'):
            self.data['language'] = language
            self.data['metadata']['reading_language'] = language
            self.build(); page = (self.root/'preview/episode.html').read_text()
            for label in ('本集导航', '播放速度', '复制完整笔记', '全文搜索', '整理阅读稿',
                          '本地预览 · 待核验', '已复制并校验完整文案', '音频逐段稿'):
                self.assertIn(label, page)

    def test_english_ui_preserves_chinese_author_content_and_escapes(self):
        text = '节目笔记 播放速度 整理阅读稿 已复制并校验完整文案 </textarea><script>alert(1)</script> @@TITLE@@'
        self.data.update(title=text, summary=text, description=text, show_notes=text,
                         launch_copy=text, status={'label': '本地预览 · 待核验'})
        self.data['reading_transcript'][0]['text'] = text
        self.data['segments'][0]['text'] = text
        self.data['chapters'][0].update(title=text, summary=text)
        self.build(); page = (self.root/'preview/episode.html').read_text()
        self.assertIn('Playback speed', page)
        self.assertIn(m.esc(text), page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('本地预览 · 待核验', page)  # Explicit author status is not translated.
        for name in ('show-notes.txt', 'launch-copy.txt', 'reading-transcript.txt'):
            self.assertEqual((self.root/'preview'/name).read_text(), text)
        self.assertEqual(self.data['title'], text)

    def test_terminology_controls_localized_without_changing_terms(self):
        text = '确认当前用词 <script>alert(1)</script>'
        self.data['terminology_review'] = dict(
            bindings=dict(episode_key='test', audio_sha256=m.digest(self.root/'audio.mp3'),
                          timeline_sha256='a'*64, glossary_sha256='b'*64,
                          content_sha256=m.terminology_content_hash(self.data)),
            terms=[dict(id='t1', current=text, alternatives=['稍后再看'], start=1, end=2,
                        reason='我的选择')])
        self.build(); page = (self.root/'preview/episode.html').read_text()
        for label in ('Review a few terms together', 'My choice', 'Review later',
                      'Confirm current wording', 'Use wording below', 'Export my decisions'):
            self.assertIn(label, page)
        self.assertIn(m.esc(text), page)
        self.assertIn('稍后再看', page)
        self.assertIn('<p>我的选择</p>', page)
        self.assertNotIn('<script>alert(1)</script>', page)

    def test_translated_reading_label_in_english_ui(self):
        self.data['metadata'].update(reading_language='zh', reading_mode='translation')
        self.build(); page = (self.root/'preview/episode.html').read_text()
        self.assertIn('Chinese translated reading transcript', page)
        self.assertNotIn('中文译写阅读稿', page)

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
        self.assertIn('Local preview · Pending verification',page)
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


class BrandTests(EnrichmentTests):
    """Brand text is content data: optional, paired, escaped, filled from the personal config only for new unsealed candidates."""
    def setUp(self):
        super().setUp()
        import os
        self.cfg = self.root / 'cfg.json'
        self.cfg.write_text(json.dumps({'shows': {'12345': {'author': 'Example Host', 'brand_name': 'Example <Brand>', 'brand_tagline': 'Say "hi"'}, '23456': {'author': 'Other', 'brand_name': 'Quiet', 'brand_tagline': ''}}}))
        self.old = os.environ.get('PODCAST_CONFIG'); os.environ['PODCAST_CONFIG'] = str(self.cfg)
        def restore():
            if self.old is None: os.environ.pop('PODCAST_CONFIG', None)
            else: os.environ['PODCAST_CONFIG'] = self.old
        self.addCleanup(restore)
        self.content = self.root / 'content.json'
    def write(self): self.content.write_text(json.dumps(self.data))
    def test_default_render_is_neutral(self):
        self.build(); page = (self.root / 'preview/episode.html').read_text()
        self.assertNotIn('Martin', page); self.assertNotIn('COMPLEXITY', page); self.assertNotIn('complexity', page)
    def test_brand_fields_must_be_paired_and_typed(self):
        for patch in ({'brand_name': 'X'}, {'brand_tagline': 'x'}, {'brand_name': 5, 'brand_tagline': 'x'}, {'brand_name': 'X', 'brand_tagline': None}, {'brand_name': ' ', 'brand_tagline': 'x'}):
            with self.subTest(patch=patch):
                data = copy.deepcopy(self.data); data.update(patch)
                with self.assertRaises(ValueError): m.validate(data, self.root)
    def test_brand_is_escaped(self):
        self.data.update(brand_name='<script>alert(1)</script>', brand_tagline='"><img src=x onerror=1>'); self.build()
        page = (self.root / 'preview/episode.html').read_text()
        self.assertNotIn('<script>alert(1)', page); self.assertNotIn('<img src=x onerror', page); self.assertIn('&lt;script&gt;alert(1)', page)
    def backfill_build(self, show_id='12345'):
        changed = m.apply_show_brand(self.data, self.root, self.content, show_id)
        return changed, m.build(self.data, self.root, self.root / 'preview/episode.html', self.content, rewrite_content=changed)
    def cli(self, *extra):
        import subprocess, sys
        return subprocess.run([sys.executable, '-B', str(Path(m.__file__)), 'build', '--content', str(self.content), '--package-root', str(self.root),
                               '--output', str(self.root / 'preview/episode.html'), *extra], capture_output=True, text=True, env={**os.environ})
    def tree_digest(self):
        return {str(p.relative_to(self.root)): m.digest(p) for p in sorted(self.root.rglob('*')) if p.is_file() and not p.is_symlink()}
    def test_backfill_from_config_writes_content_and_show_id(self):
        self.write(); changed, manifest = self.backfill_build()
        self.assertTrue(changed); saved = json.loads(self.content.read_text())
        self.assertEqual((saved['brand_name'], saved['brand_tagline'], saved['metadata']['show_id']), ('Example <Brand>', 'Say "hi"', '12345'))
        page = (self.root / 'preview/episode.html').read_text(); self.assertIn('Example &lt;Brand&gt;', page)
        self.assertEqual(m.digest(self.content), manifest['content_sha256'])
        self.assertEqual([p.name for p in self.root.glob('.content.*')], [])
    def test_backfill_is_in_memory_until_build_has_passed_every_precondition(self):
        self.write(); before = m.digest(self.content)
        self.assertTrue(m.apply_show_brand(self.data, self.root, self.content, '12345')); self.assertEqual(before, m.digest(self.content))
        with self.assertRaises(ValueError): m.build(self.data, self.root, self.root / 'preview/episode.txt', self.content, rewrite_content=True)  # invalid output
        self.assertEqual(before, m.digest(self.content)); self.assertFalse((self.root / 'preview').exists() and any((self.root / 'preview').iterdir()))
    def test_explicit_empty_tagline_is_kept_and_complete_brand_not_overwritten(self):
        self.data.update(brand_name='Mine', brand_tagline=''); self.write()
        self.assertFalse(m.apply_show_brand(self.data, self.root, self.content, '12345'))
        self.assertEqual((self.data['brand_name'], self.data['brand_tagline']), ('Mine', '')); self.assertEqual(json.loads(self.content.read_text())['brand_name'], 'Mine')
    def test_empty_tagline_from_config_stays_empty(self):
        self.write(); m.apply_show_brand(self.data, self.root, self.content, '23456'); self.assertEqual(self.data['brand_tagline'], '')
    def test_every_build_of_a_sealed_package_is_refused_and_changes_nothing(self):
        self.write()
        m.build(self.data, self.root, self.root / 'preview/episode.html', self.content)  # an unsealed build first
        (self.root / 'seal.json').write_text('{}'); before = self.tree_digest()
        for extra in ((), ('--show-id', '12345')):
            with self.subTest(extra=extra):
                result = self.cli(*extra); self.assertEqual(result.returncode, 2); self.assertIn('sealed', result.stderr); self.assertEqual(before, self.tree_digest())
        self.data.update(brand_name='Full', brand_tagline='Brand'); self.write(); before = self.tree_digest()
        result = self.cli('--show-id', '12345'); self.assertEqual(result.returncode, 2); self.assertEqual(before, self.tree_digest())
        with self.assertRaisesRegex(ValueError, 'sealed'): m.build(self.data, self.root, self.root / 'preview/episode.html', self.content)
        self.assertEqual(before, self.tree_digest())
    def test_validate_still_works_on_a_sealed_package(self):
        self.write(); (self.root / 'seal.json').write_text('{}'); self.assertIn('experience_ready', m.validate(self.data, self.root))
    def test_unknown_show_or_conflicting_show_id_fails_without_writing(self):
        self.write(); before = m.digest(self.content)
        with self.assertRaisesRegex(ValueError, 'no brand'): m.apply_show_brand(self.data, self.root, self.content, '99999')
        self.data['metadata']['show_id'] = '23456'
        with self.assertRaisesRegex(ValueError, 'differs'): m.apply_show_brand(self.data, self.root, self.content, '12345')
        self.assertEqual(before, m.digest(self.content))
    def test_symlinked_content_is_refused(self):
        real = self.root / 'real.json'; real.write_text(json.dumps(self.data)); self.content.symlink_to(real)
        with self.assertRaises(ValueError): m.apply_show_brand(self.data, self.root, self.content, '12345')
    def test_a_planted_temporary_symlink_cannot_redirect_the_write(self):
        outside = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__('shutil').rmtree(outside, ignore_errors=True)); sentinel = outside / 'sentinel'; sentinel.write_text('keep')
        (self.root / 'content.json.tmp').symlink_to(sentinel); (self.root / '.content.tmp').symlink_to(sentinel)
        self.write(); self.backfill_build()
        self.assertEqual(sentinel.read_text(), 'keep'); self.assertEqual(json.loads(self.content.read_text())['brand_name'], 'Example <Brand>')
    def test_hardlinked_outputs_never_write_through_to_inputs(self):
        (self.root / 'preview').mkdir(); audio = self.root / 'audio.mp3'; before = m.digest(audio)
        os.link(audio, self.root / 'preview' / 'transcript.txt');
        self.write(); self.backfill_build()
        self.assertEqual(before, m.digest(audio)); self.assertNotEqual(m.digest(self.root / 'preview' / 'transcript.txt'), before)
        self.assertEqual(os.stat(audio).st_nlink, 1)
    def test_directory_placeholder_fails_before_any_write(self):
        self.write(); (self.root / 'preview' / 'aligned-transcript.json').mkdir(parents=True); before = m.digest(self.content)
        m.apply_show_brand(self.data, self.root, self.content, '12345')
        with self.assertRaises(ValueError): m.build(self.data, self.root, self.root / 'preview/episode.html', self.content, rewrite_content=True)
        self.assertEqual(before, m.digest(self.content)); self.assertFalse((self.root / 'preview' / 'episode.html').exists())
    def test_symlink_output_target_fails_before_any_write(self):
        self.write(); (self.root / 'preview').mkdir(); outside = self.root / 'elsewhere.txt'; outside.write_text('keep'); (self.root / 'preview' / 'transcript.txt').symlink_to(outside)
        before = m.digest(self.content); m.apply_show_brand(self.data, self.root, self.content, '12345')
        with self.assertRaises(ValueError): m.build(self.data, self.root, self.root / 'preview/episode.html', self.content, rewrite_content=True)
        self.assertEqual(before, m.digest(self.content)); self.assertEqual(outside.read_text(), 'keep')
    def test_render_and_validate_do_not_read_host_config(self):
        import os
        self.data.update(brand_name='Frozen', brand_tagline='In content'); self.build(); first = (self.root / 'preview/episode.html').read_text()
        os.environ['PODCAST_CONFIG'] = str(self.root / 'missing.json'); self.build()
        self.assertEqual(first, (self.root / 'preview/episode.html').read_text())
    def test_metadata_show_id_type(self):
        self.data['metadata']['show_id'] = 12345
        with self.assertRaises(ValueError): m.validate(self.data, self.root)


if __name__=='__main__':unittest.main()
