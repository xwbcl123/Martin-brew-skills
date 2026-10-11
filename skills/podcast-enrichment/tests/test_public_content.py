import copy
import json
import re
import unittest
import test_enrich
m = test_enrich.m


class PublicContentTests(unittest.TestCase):
    build = test_enrich.EnrichmentTests.build
    def setUp(self):
        test_enrich.EnrichmentTests.setUp(self)
        self.data['public_content']={'version':1,'nodes':[
            {'type':'paragraph','children':[{'type':'text','text':'一起听，'},{'type':'strong','children':[{'type':'text','text':'A & B'}]}]},
            {'type':'heading','level':2,'children':[{'type':'text','text':'这一集聊什么'}]},
            {'type':'list','ordered':False,'items':[[{'type':'em','children':[{'type':'text','text':'选择与判断'}]}]]},
            {'type':'erratum','children':[{'type':'text','text':'事后查证，发现搞错了：这里有一个修复步骤。'}]},
            {'type':'chapters'}, {'type':'resources'},
            {'type':'transcript','url':'https://example.org/transcript','label':'完整文字稿'}]}
    # Inherited legacy-specific assertions run in the legacy suite above.
    def test_public_render_and_no_legacy_noise(self):
        manifest=self.build();page=(self.root/'preview/episode.html').read_text()
        out=(self.root/'preview/description.html').read_text()
        self.assertEqual(out,m.public_html(self.data))
        self.assertIn('<strong>A &amp; B</strong>',out)
        self.assertIn('<em>选择与判断</em>',out)
        self.assertEqual(out.count('本集章节'),1)
        self.assertNotIn('Voice provenance unknown',page)
        self.assertNotIn('One<br>',page)
        self.assertEqual((self.root/'preview/summary.txt').read_text(),'一起听，A & B')
        for item in manifest['artifacts']:self.assertEqual(item['sha256'],m.digest(self.root/item['path']))
    def test_public_reject_unknown_and_injection(self):
        source=copy.deepcopy(self.data)
        bad=[{'type':'script','text':'alert(1)'},{'type':'paragraph','onclick':'x','children':[{'type':'text','text':'x'}]}, {'type':'paragraph','children':[{'type':'link','url':'javascript:alert(1)','children':[{'type':'text','text':'x'}]}]}, {'type':'heading','level':1,'children':[{'type':'text','text':'x'}]}]
        for node in bad:
            self.data=copy.deepcopy(source);self.data['public_content']['nodes'].append(node)
            with self.assertRaises(ValueError):m.public_html(self.data)
        for version in (2,True,'1'):
            self.data=copy.deepcopy(source);self.data['public_content']['version']=version
            with self.assertRaises(ValueError):m.public_html(self.data)
        self.data=source;self.data['public_content']['nodes'].append({'type':'chapters'})
        with self.assertRaises(ValueError):m.public_html(self.data)
    def test_public_literal_html_escaped_and_summary_unicode(self):
        self.data['public_content']['nodes'][0]['children']=[{'type':'text','text':'中&文'*100+'<script>alert(1)</script>'}]
        self.assertEqual(len(m.public_summary(self.data)),240)
        self.assertNotIn('<script>',m.public_html(self.data))
        self.assertIn('&lt;script&gt;',m.public_html(self.data))
    def terms(self):
        bindings=dict(episode_key='episode-1',audio_sha256=m.digest(self.root/'audio.mp3'),timeline_sha256='a'*64,content_sha256=m.terminology_content_hash(self.data),glossary_sha256='b'*64)
        self.data['terminology_review']={'bindings':bindings,'terms':[{'id':'t1','current':'Felix','alternatives':['Felx'],'start':1,'end':3,'reason':'这里的人名再听一遍。'}]}
        return {'version':1,'origin':'user_preview','attestation':'I reviewed these term decisions','bindings':copy.deepcopy(bindings),'decisions':[{'term_id':'t1','decision':'confirm','text':'Felix'}]}
    def test_terms_closed_safe_and_bound_import(self):
        exported=self.terms();self.build();page=(self.root/'preview/episode.html').read_text()
        self.assertRegex(page,r'<details[^>]+id="terminology-review"')
        self.assertNotIn(' open',re.search(r'<details[^>]+id="terminology-review"[^>]*>',page).group())
        self.assertEqual(m.import_terminology_decisions(self.data,exported)['provenance'],'user_preview_attestation')
        self.assertNotIn('human_confirmed',json.dumps(m.import_terminology_decisions(self.data,exported)))
        exported['decisions'][0].update(decision='edit',text='菲利克斯')
        self.assertEqual(m.import_terminology_decisions(self.data,exported)['decisions'][0]['text'],'菲利克斯')
    def test_terms_stale_duplicate_and_actor_rejected(self):
        source=self.terms()
        for field in source['bindings']:
            export=copy.deepcopy(source);export['bindings'][field]='wrong'
            with self.assertRaises(ValueError):m.import_terminology_decisions(self.data,export)
        export=copy.deepcopy(source);export['decisions']*=2
        with self.assertRaises(ValueError):m.import_terminology_decisions(self.data,export)
        export=copy.deepcopy(source);export['origin']='agent'
        with self.assertRaises(ValueError):m.import_terminology_decisions(self.data,export)
        export=copy.deepcopy(source);export['decisions'][0]['text']='other'
        with self.assertRaises(ValueError):m.import_terminology_decisions(self.data,export)
        self.data['title']='new title'
        with self.assertRaisesRegex(ValueError,'stale'):m.import_terminology_decisions(self.data,source)
    def test_terms_actual_audio_and_bounds(self):
        self.terms();(self.root/'audio.mp3').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'audio'):self.build()
        self.data['terminology_review']['terms'][0]['end']=30
        with self.assertRaisesRegex(ValueError,'timeline'):m.validate_terminology(self.data)

