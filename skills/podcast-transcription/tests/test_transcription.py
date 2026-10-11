import importlib.util,json,pathlib,subprocess,tempfile,unittest
P=pathlib.Path
s=importlib.util.spec_from_file_location('transcription',P(__file__).parents[1]/'scripts/transcription.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class TranscriptionTests(unittest.TestCase):
 def test_context_option_and_recovery_cannot_relabel_inference(self):
  for argv in [['--max-context'],['--max-context','-1'],['--max-context','0','-mc','0']]:
   with self.assertRaises(ValueError): m.context_option(argv)
  with tempfile.TemporaryDirectory() as d:
   d=P(d); audio=d/'delivery.wav'; model=d/'model'; model.write_text('fixture model')
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=2',str(audio)],check=True)
   cli=d/'whisper'; cli.write_text('''#!/usr/bin/env python3
import sys,json,pathlib
a=sys.argv
if '--detect-language' in a: print('auto-detected language: en (p = 0.98)'); sys.exit(0)
assert a[a.index('--max-context')+1]=='0'
p=a[a.index('-of')+1]
for ext in ['txt','srt','vtt']: pathlib.Path(p+'.'+ext).write_text('fixture output')
pathlib.Path(p+'.json').write_text(json.dumps({'result':{'language':'en'},'transcription':[{'offsets':{'from':0,'to':1500},'text':'Hello world.'}]}))
''');cli.chmod(0o755)
   out=d/'out'; r=m.transcribe(audio,out,model,cli,1,max_context_tokens=0)
   self.assertEqual(r['identity']['max_context_tokens'],0);self.assertEqual(r['argv'][-2:],['--max-context','0'])
   self.assertEqual(m.transcribe(audio,out,model,cli,1,max_context_tokens=0)['run_key'],r['run_key'])
   for value in [None,32]:
    with self.assertRaises(ValueError):m.transcribe(audio,out,model,cli,1,max_context_tokens=value)
   for value in [True,-1,1.5]:
    with self.assertRaises(ValueError):m.transcribe(audio,d/'invalid',model,cli,1,max_context_tokens=value)
   checkpoint=out/'execution-checkpoint.json'
   evidence={'evidence_kind':'execution_checkpoint','source_ref':'fixture completed inference','prior_argv':r['argv'],'checkpoint_sha256':m.media.sha256(checkpoint),**{k:r['identity'][k] for k in ['delivery_sha256','model_sha256','tool_sha256']},'artifacts':{n:m.media.sha256(out/n) for n in ['analysis.wav','raw.txt','raw.json','raw.srt','raw.vtt','language-detection.log','asr.log']}}
   ep=d/'evidence.json';ep.write_text(json.dumps(evidence))
   with self.assertRaisesRegex(ValueError,'text-context option mismatch'):m.transcribe(audio,d/'wrong-recovery',model,cli,1,out,ep,max_context_tokens=None)
   recovered=m.transcribe(audio,d/'recovery',model,cli,1,out,ep,max_context_tokens=0)
   self.assertFalse(recovered['recovery']['raw_rerun']);self.assertEqual(m.media.sha256(out/'raw.json'),m.media.sha256(d/'recovery/raw.json'))
   saved=json.loads(checkpoint.read_text());saved['identity']['max_context_tokens']=32;checkpoint.write_text(json.dumps(saved));evidence['checkpoint_sha256']=m.media.sha256(checkpoint);ep.write_text(json.dumps(evidence))
   with self.assertRaisesRegex(ValueError,'checkpoint mismatch: max_context_tokens'):m.transcribe(audio,d/'tampered-recovery',model,cli,1,out,ep,max_context_tokens=0)
 def test_duration_validation(self):
  with self.assertRaises(ValueError): m.align({'transcription':[{'offsets':{'from':0,'to':3000},'text':'oops'}]},2)
 def test_zero_span_duplicate_is_removed_with_ledger(self):
  raw={'transcription':[{'offsets':{'from':0,'to':1000},'text':'one'},{'offsets':{'from':1000,'to':1000},'text':'two'},{'offsets':{'from':1000,'to':1800},'text':'two'}]}; corrections=[]
  segments=m.align(raw,2,corrections); self.assertEqual([x['id'] for x in segments],[0,2]); self.assertEqual(corrections[0]['after'],''); self.assertEqual(corrections[0]['duplicate_of_segment_id'],2); self.assertEqual(raw['transcription'][1]['text'],'two')
  with self.assertRaises(ValueError): m.align(raw,2)
  raw['transcription'][1]['text']='distinct'
  with self.assertRaises(ValueError): m.align(raw,2,[])
 def test_explicit_timing_override_binding_and_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); evidence=d/'excerpt.json'; evidence.write_text('{"observed":"fixture"}')
   raw={'transcription':[{'offsets':{'from':0,'to':1000},'text':'before'},{'offsets':{'from':1000,'to':1000},'text':'meaningful'},{'offsets':{'from':1500,'to':2000},'text':'after'}]}
   payload={'audio_sha256':'a'*64,'raw_json_sha256':'b'*64,'reviewed_by_kind':'agent_delegated','source_ref':'test-fixture','corrections':[{'segment_id':1,'field':'end','before':1.0,'after':1.5,'reason':'observed in local excerpt','accuracy':'asr_estimated','evidence':[{'path':str(evidence),'sha256':m.media.sha256(evidence)}]}]}
   p=d/'timing.json'; p.write_text(json.dumps(payload)); overrides=m.load_timing_corrections(p,raw,'a'*64,'b'*64); ledger=[]; segments=m.align(raw,3,ledger,overrides)
   self.assertEqual(segments[1]['text'],'meaningful'); self.assertEqual(segments[1]['end'],1.5); self.assertEqual(ledger[0]['accuracy'],'asr_estimated')
   with self.assertRaises(ValueError): m.load_timing_corrections(p,raw,'c'*64,'b'*64)
   evidence.write_text('tampered')
   with self.assertRaises(ValueError): m.load_timing_corrections(p,raw,'a'*64,'b'*64)
 def test_terminal_quantization_only(self):
  corrections=[]; raw={'transcription':[{'offsets':{'from':0,'to':2127},'text':'End.'}]}; result=m.align(raw,2,corrections)
  self.assertEqual(result[0]['end'],2); self.assertEqual(corrections[0]['before'],2.127); self.assertTrue(corrections[0]['raw_preserved'])
  with self.assertRaises(ValueError): m.align({'transcription':[{'offsets':{'from':0,'to':2300},'text':'End.'}]},2,[])
  with self.assertRaises(ValueError): m.align({'transcription':[{'offsets':{'from':0,'to':2100},'text':'bad'},{'offsets':{'from':2100,'to':2120},'text':'end'}]},2,[])
 def test_detect_run_cache_identity(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); audio=d/'delivery.wav'; model=d/'model'; model.write_text('fixture model')
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=2',str(audio)],check=True)
   cli=d/'whisper'; cli.write_text('''#!/usr/bin/env python3
import sys,json,pathlib
a=sys.argv
if '--detect-language' in a: print('auto-detected language: en (p = 0.98)'); sys.exit(0)
assert a[a.index('-l')+1]=='en'
p=a[a.index('-of')+1]
for ext in ['txt','srt','vtt']: pathlib.Path(p+'.'+ext).write_text('fixture output')
pathlib.Path(p+'.json').write_text(json.dumps({'result':{'language':'en'},'transcription':[{'offsets':{'from':0,'to':1500},'text':'Hello world.'}]}))
'''); cli.chmod(0o755)
   r=m.transcribe(audio,d/'out',model,cli,1); self.assertEqual(r['language'],'en'); self.assertEqual(m.transcribe(audio,d/'out',model,cli,1)['run_key'],r['run_key'])
   forged=json.loads((d/'out/report.json').read_text());forged['identity']['max_context_tokens']=0;forged['argv']+=['--max-context','0'];forged['run_key']=m.media.digest(forged['identity'])
   m.media.write_json(d/'out/report.json',forged);(d/'out/report.sha256').write_text(m.media.sha256(d/'out/report.json')+'\n')
   with self.assertRaisesRegex(ValueError,'cache checkpoint identity mismatch: max_context_tokens'):m.transcribe(audio,d/'out',model,cli,1,max_context_tokens=0)
   m.media.write_json(d/'out/report.json',r);(d/'out/report.sha256').write_text(m.media.sha256(d/'out/report.json')+'\n')
   aligned=json.loads((d/'out/aligned.json').read_text()); self.assertEqual(aligned['segments'][0]['speaker'],'unknown')
   model.write_text('new model')
   with self.assertRaises(ValueError): m.transcribe(audio,d/'out',model,cli,1)
if __name__=='__main__': unittest.main()
