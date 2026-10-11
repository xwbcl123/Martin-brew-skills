import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('calibration', Path(__file__).parents[1] / 'scripts/calibration.py')
c = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(c)

class CalibrationTests(unittest.TestCase):
    def test_real_loop(self):
        fixture = json.loads((Path(__file__).parent/'fixtures/cursor-repeat-361.json').read_text())
        result = c.detect_anomalies(fixture, 2060.98)
        self.assertTrue(any(f.get('count') == 361 for f in result['flags']))
        self.assertFalse(result['publication_blocked'])

    def test_normal_and_timing(self):
        rows = [{'start':0,'end':2,'text':'我们谈谈 Cursor'}, {'start':2,'end':5,'text':'孩子学习的方式'}]
        self.assertEqual(c.detect_anomalies(rows,5)['flags'], [])
        rows[1]['end'] = 9
        self.assertEqual(c.detect_anomalies(rows,5)['flags'][0]['kind'], 'timeline')
        self.assertEqual(c.detect_anomalies([],30)['flags'][0]['kind'], 'coverage_gap')

    def test_short_cycle(self):
        rows = [{'start':i,'end':i+1,'text':['嗯','啊'][i%2]} for i in range(20)]
        self.assertTrue(any(f['kind']=='repeated_cycle' for f in c.detect_anomalies(rows,20)['flags']))

    def test_glossary_conflicts_boundaries(self):
        g=c.parse_glossary('- F = Felix\n- Andy = Andrew\n- Andy = Andrej\n- Cursor\n')
        self.assertTrue(g['entries'][0]['short_alias'])
        self.assertTrue(g['entries'][1]['conflict'])
        r=c.relevant_terms(g,'Felix 使用 Cursor')
        self.assertEqual([e['alias'] for e in r['candidates']], ['Cursor'])
        self.assertFalse(r['automatic_replacement'])

    def test_user_and_votes(self):
        binding={k:'a' for k in c.BINDING_KEYS}; term={'id':'t1','current':'Old','bindings':binding}
        doc={'bindings':binding,'decisions':[{'term_id':'t1','decision':'edit','text':'New'}]}
        with self.assertRaises(ValueError): c.import_user_decisions(doc,binding,[term],'agent','preview')
        decision=c.import_user_decisions(doc,binding,[term],'human','user-message')[0]
        self.assertEqual(c.reconcile(term,[],'autonomous',decision)['text'],'New')
        self.assertEqual(c.reconcile(term,[],'interactive')['status'],'awaiting_user')
        vote={'model_id':'model1','reviewed_by_kind':'agent','independent':True,'request_sha256':'x','source_ref':'file','raw_response':{'answer':'New'},'choice':'New'}
        vote['response_sha256']=c.digest(vote['raw_response'])
        self.assertEqual(c.reconcile(term,[vote],'autonomous')['degraded'],'single_model')
        with self.assertRaises(ValueError): c.reconcile(term,[vote,vote],'autonomous')
        with self.assertRaises(ValueError): c.reconcile(term,[vote],'interactive')
        with self.assertRaises(ValueError): c.import_user_decisions(doc,{**binding,'audio_sha256':'b'},[term],'human','user')
        doc['decisions'] *= 2
        with self.assertRaises(ValueError): c.import_user_decisions(doc,binding,[term],'human','user')

    def test_ranges(self):
        auth={'source_sha256':'x','source_kind':'final_delivery','source_ref':'user','external_snippet_asr_authorized':True,'ranges':[{'start':0,'end':60},{'start':70,'end':130},{'start':140,'end':200}]}
        self.assertEqual(len(c.validate_ranges(auth,'x',300)),3)
        with self.assertRaises(ValueError): c.validate_ranges(auth,'changed',300)
        auth['ranges'].append({'start':220,'end':221})
        with self.assertRaises(ValueError): c.validate_ranges(auth,'x',300)
        auth['ranges']=[{'start':0,'end':40}]
        with self.assertRaises(ValueError): c.validate_ranges(auth,'x',40)

    def test_runkey(self):
        self.assertEqual(c.run_key('terms',{'source':'x'}),c.run_key('terms',{'source':'x'}))
        with self.assertRaises(ValueError): c.run_key('terms',{'output_sha256':'x'})

    def test_extract_and_empty_fallback_offset(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/'final.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=4',str(source)],check=True)
            auth={'source_sha256':c.sha(source),'source_kind':'final_delivery','source_ref':'explicit-user-test','external_snippet_asr_authorized':True,'ranges':[{'start':1,'end':2}]}
            manifest=c.extract_snippets(source,auth,root/'clips')
            calls=[]
            def fake(model,payload):
                calls.append(model)
                self.assertNotIn('Whisper',payload['contents'][0]['parts'][0]['text'])
                if len(calls)==1:return {'candidates':[]}
                return {'candidates':[{'content':{'parts':[{'text':'{"segments":[{"start":0,"end":0.8,"text":"测试"}]}'}]}}]}
            result=c.gemini_transcribe(manifest,root/'asr',transport=fake)
            self.assertEqual(result['attempts'][0]['error'],'empty_response')
            self.assertEqual(result['attempts'][1]['segments'][0]['start'],1)
            self.assertEqual(result['attempts'][1]['segments'][0]['relative_start'],0)
            self.assertTrue((root/'asr/snippet-000-gemini-3.5-transcribe.json').exists())
            manifest['snippets'][0]['start']=0
            with self.assertRaises(ValueError):c.gemini_transcribe(manifest,root/'bad',transport=fake)

if __name__=='__main__':unittest.main()
