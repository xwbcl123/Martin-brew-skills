import copy,importlib.util,json,pathlib,tempfile,unittest,wave,array,subprocess,sys
P=pathlib.Path
s=importlib.util.spec_from_file_location('edit_derived',P(__file__).parents[1]/'scripts/edit_derived.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
ms=importlib.util.spec_from_file_location('derived_fixture_mastering',P(__file__).parents[2]/'podcast-mastering/scripts/mastering.py'); master=importlib.util.module_from_spec(ms); ms.loader.exec_module(master)
class DerivedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=P(self.tmp.name); self.source=self.root/'old'; self.source.mkdir(); self.dest=self.root/'new'; self.dest.mkdir()
  self.wav=self.source/'source.wav'; self.edited=self.dest/'edited.wav'; rate=44100
  samples=array.array('h',(i%30000-15000 for i in range(rate*4)))
  def wave_write(p,data):
   with wave.open(str(p),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(data.tobytes())
  wave_write(self.wav,samples); wave_write(self.edited,samples[:rate]+samples[2*rate:])
  self.raw={'result':{'language':'en'},'transcription':[{'offsets':{'from':i*1000,'to':(i+1)*1000},'text':f'words{i}'} for i in range(4)]}; m.write(self.source/'raw.json',self.raw)
  for ext in ['txt','srt','vtt']:(self.source/('raw.'+ext)).write_text('\n'.join(s['text'] for s in self.raw['transcription']))
  master.produce(self.wav,self.source/'media'); master.produce(self.edited,self.dest/'media'); self.old_delivery=self.source/'media/delivery.mp3'; self.delivery=self.dest/'media/delivery.mp3'
  oldsha=m.sha(self.old_delivery); self.ledger={'audio_sha256':oldsha,'raw_json_sha256':m.sha(self.source/'raw.json'),'corrections':[]}; m.write(self.source/'corrections.json',self.ledger)
  m.write(self.source/'aligned.json',{'audio_sha256':oldsha,'language':'en','segments':m.replay(self.raw,self.ledger)})
  edl={'sample_rate':rate,'remove_samples':[rate,2*rate],'removed_seconds':1,'range_semantics':'[start,end)','source_sha256':m.sha(self.wav),'fades_ms':0}; self.edl=self.dest/'edl.json'; m.write(self.edl,edl)
  self.oldreport=self.source/'media/report.json';self.newreport=self.dest/'media/report.json'
  self.out=self.dest/'transcription';m.produce(self.source,self.old_delivery,self.oldreport,self.edl,self.wav,self.edited,self.delivery,self.newreport,self.out)
 def tearDown(self):self.tmp.cleanup()
 def verify(self,lineage=None,aligned=None,ledger=None):return m.verify(self.dest,lineage or m.read(self.out/'edit-lineage.json'),aligned or m.read(self.out/'aligned.json'),ledger or m.read(self.out/'corrections.json'),self.out/'raw.json',self.delivery)
 def test_exact_mapping_and_original_raw_preserved(self):
  self.assertTrue(self.verify()['valid']); a=m.read(self.out/'aligned.json');self.assertEqual([s['id'] for s in a['segments']],[0,2,3]);self.assertEqual(a['segments'][1]['start'],1);self.assertEqual(m.sha(self.source/'raw.json'),m.sha(self.out/'raw.json'))
 def test_wrong_shift_rejected_even_with_corresponding_ledger(self):
  a=m.read(self.out/'aligned.json'); l=m.read(self.out/'corrections.json');a['segments'][1]['start']=1.1
  l['corrections'].append({'segment_id':2,'field':'start','before':1.0,'after':1.1,'reason':'tamper'})
  with self.assertRaisesRegex(ValueError,'timeline'):self.verify(aligned=a,ledger=l)
 def test_equal_duration_wrong_delivery_rejected(self):
  wrong=self.dest/'wrong.mp3';subprocess.run(['ffmpeg','-v','error','-i',str(self.edited),'-af','volume=0.5','-c:a','libmp3lame','-b:a','192k',str(wrong)],check=True)
  forged=m.read(self.newreport);forged['outputs']['delivery.mp3']['sha256']=m.sha(wrong)
  with self.assertRaisesRegex(ValueError,'deterministic'):m.verify_delivery_encoding(self.edited,wrong,forged)
 def test_float_pcm_not_claimed_exact(self):
  floatwave=self.dest/'float.wav';subprocess.run(['ffmpeg','-v','error','-i',str(self.wav),'-c:a','pcm_f32le',str(floatwave)],check=True)
  with self.assertRaisesRegex(ValueError,'integer PCM'):m.pcm_edit_check(floatwave,self.edited,m.read(self.edl))
 def test_assembler_keeps_raw_source_identity(self):
  package_path=P(__file__).parents[2]/'podcast-release-package/scripts/v2/package.py';spec=importlib.util.spec_from_file_location('derived_package_fixture',package_path);pkg=importlib.util.module_from_spec(spec);spec.loader.exec_module(pkg);sys.modules['package']=pkg
  spec=importlib.util.spec_from_file_location('derived_assembler_fixture',package_path.with_name('assemble.py'));asm=importlib.util.module_from_spec(spec);spec.loader.exec_module(asm)
  content={'audio_path':'media/delivery.mp3','cover_path':'cover.png','title':'Fixture','summary':'Fixture','description':'Fixture','show_notes':'Fixture','ai_disclosure':'Fixture only','chapters':[],'resources':[]};m.write(self.dest/'content.json',content);(self.dest/'cover.png').write_text('fixture placeholder not release artwork');(self.dest/'preview').mkdir();(self.dest/'preview/episode.html').write_text('fixture only');m.write(self.dest/'preview/enrichment-manifest.json',{'artifacts':[],'source_assets':[]})
  content['reading_transcript']=[{'text':s['text'],'source_segment_ids':[s['id']]} for s in m.read(self.out/'aligned.json')['segments']];m.write(self.dest/'content.json',content)
  (self.dest/'preview/reading-transcript.txt').write_text('\n\n'.join(p['text'] for p in content['reading_transcript']))
  asm.assemble(self.dest.resolve(),self.wav,'imported_finished','123','fixture',1,'https://example.test/fixture.png',1,author='Example Host',origin_tool='Fixture editor export',declaration_source='fixture-declaration')
  artifacts=m.read(self.dest/'episode.json')['artifacts'];self.assertEqual(artifacts['raw_asr_json']['audio_sha256'],m.sha(self.old_delivery));self.assertEqual(artifacts['aligned_transcript']['audio_sha256'],m.sha(self.delivery));self.assertIn('edit_lineage',artifacts);self.assertIn('derived_source_wave',artifacts);self.assertNotIn('asr_report',artifacts)
 def test_source_binding_tamper_rejected(self):
  d=m.read(self.out/'edit-lineage.json');d['source_audio_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'identity'):self.verify(lineage=d)
 def test_edl_wrong_cut_rejected(self):
  e=m.read(self.edl);e['remove_samples']=[88200,132300];m.write(self.edl,e);d=m.read(self.out/'edit-lineage.json');d['evidence']['edl']['sha256']=m.sha(self.edl)
  with self.assertRaisesRegex(ValueError,'removed IDs'):self.verify(lineage=d)
 def test_pcm_changes_outside_join_rejected(self):
  with wave.open(str(self.edited),'rb') as f:params=f.getparams();data=bytearray(f.readframes(f.getnframes()))
  data[100:102]=b'\x00\x00'
  with wave.open(str(self.edited),'wb') as f:f.setparams(params);f.writeframes(data)
  with self.assertRaisesRegex(ValueError,'retained PCM'):m.pcm_edit_check(self.wav,self.edited,m.read(self.edl))
if __name__=='__main__':unittest.main()
