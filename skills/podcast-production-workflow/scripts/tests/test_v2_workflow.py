import importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
P=pathlib.Path
s=importlib.util.spec_from_file_location('workflow_v2',P(__file__).parents[1]/'v2/workflow.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class WorkflowTests(unittest.TestCase):
 def request(self,d,entry='inspect_finished',target='transcription'):
  audio=d/'audio'; audio.write_bytes(b'fixture media not to decode')
  return {'contract_version':'2.0','entry_stage':entry,'target_stage':target,'source_kind':'imported_finished','inputs':{'audio':str(audio)},'package_root':str(d)}
 def test_finished_plan_has_no_edit_or_master_and_no_execution(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d)
   with patch.object(m.subprocess,'run',side_effect=AssertionError('plan executed subprocess')): result=m.plan(r)
   self.assertEqual(result['stages'],['inspect_finished','delivery','transcription']); self.assertFalse((d/'workflow').exists())
 def test_single_stage_missing_transcript_fails(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d,'enrichment','enrichment'); content=d/'content.json'; content.write_text('{}'); r['inputs']['content']=str(content)
   with self.assertRaisesRegex(ValueError,'transcript'): m.plan(r)
 def test_single_stage_does_not_run_upstream(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.request(P(d),'transcription','transcription'); self.assertEqual(m.plan(r)['stages'],['transcription'])
 def test_audio_invalidates_timeline_text_does_not(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); old=d/'old'; new=d/'new'; old.write_text('old'); new.write_text('new')
   changed=m.changed_artifacts({'audio':old},{'audio':new}); affected=m.invalidate(changed)
   self.assertIn('transcription',affected); self.assertIn('publish',affected)
   text=m.invalidate({'show_notes'}); self.assertIn('enrichment',text); self.assertNotIn('transcription',text); self.assertNotIn('delivery',text)
 def test_raw_routes_sample_edit_and_skips_second_delivery_encode(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d,'intake','delivery'); r['source_kind']='raw_recording'; edl=d/'edl'; edl.write_text('{}'); r['inputs']['edl']=str(edl)
   result=m.plan(r); self.assertEqual(result['stages'],['intake','final_edit','mastering','delivery']); self.assertIsNone(result['steps'][-1]['command'])
 def test_content_edit_preserves_transcription_cache_path(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d,target='preview'); content=d/'content.json'; content.write_text('{"show_notes":"one"}'); r['inputs']['content']=str(content)
   before=m.plan(r); content.write_text('{"show_notes":"two"}'); after=m.plan(r)
   b={s['stage']:s for s in before['steps']}; a={s['stage']:s for s in after['steps']}
   self.assertEqual(b['transcription']['output_dir'],a['transcription']['output_dir']); self.assertNotEqual(b['preview']['output_dir'],a['preview']['output_dir'])
 def test_build_inspection_writes_atomic_report(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d,target='inspect_finished')
   import subprocess
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=0.2','-f','wav','-y',r['inputs']['audio']],check=True)
   result=m.build(r); report=P(result['steps'][0]['output_dir'])/'stage-report.json'
   self.assertEqual(json.loads(report.read_text())['status'],'succeeded'); self.assertFalse((d/'workflow/.build.lock').exists())
 def test_publish_requires_authorization(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); r=self.request(d,'publish','publish'); (d/'episode.json').write_text('{}'); r['inputs']['package']=str(d)
   with self.assertRaisesRegex(ValueError,'authorization'): m.plan(r)
if __name__=='__main__': unittest.main()
