import importlib.util,pathlib,unittest,tempfile,subprocess,json,hashlib,wave
s=importlib.util.spec_from_file_location('edit',pathlib.Path(__file__).parents[1]/'scripts/final_edit.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class CandidateTests(unittest.TestCase):
 def words(self):
  return {'source_sample_rate':48000,'source_total_samples':48000,'source_analysis_sha256':'0'*64,'clock_mapping_word_boundaries_verified':False,'words':[{'id':'a','text':'嗯','start_sample':0,'end_sample':4800,'cut_protected':True},{'id':'b','text':'我','start_sample':4800,'end_sample':9600},{'id':'c','text':'觉得','start_sample':9600,'end_sample':14400},{'id':'d','text':'呃','start_sample':14400,'end_sample':19200},{'id':'e','text':'好','start_sample':19000,'end_sample':24000}]}
 def test_inline_fillers_get_context_and_remain_kept_without_cut(self):
  r=m.word_candidates(self.words());self.assertEqual(len(r['candidates']),2);self.assertEqual(r['candidates'][0]['context_text'],'嗯我觉得呃好');self.assertTrue(r['candidates'][0]['cut_protected']);self.assertTrue(any('overlapping' in s for s in r['candidates'][1]['review_reasons']));self.assertTrue(all(c['proposed_cut_interval'] is None and c['decision']=='keep_pending_review' for c in r['candidates']));self.assertFalse(r['source_clock_mapping_verified'])
 def test_invalid_word_clocks_rejected_and_unlocated_substantive_retained(self):
  for change in ['boolean','reverse','unsorted','duplicate','overflow']:
   r=self.words()
   if change=='boolean':r['words'][0]['start_sample']=False
   elif change=='reverse':r['words'][0]['end_sample']=-1
   elif change=='unsorted':r['words']=list(reversed(r['words']))
   elif change=='duplicate':r['words'][1]['id']='a'
   else:r['words'][-1]['end_sample']=48001
   with self.subTest(change=change),self.assertRaises(ValueError):m.word_candidates(r)
  r=self.words();r['unlocated_entries']=[{'raw_word':{'text':'缺失'}},{'raw_word':{'text':' '}}];self.assertEqual(len(m.word_candidates(r)['substantive_unlocated_entries']),1)
 def test_verification_and_protection_flags_require_booleans(self):
  for field in ['clock_mapping_word_boundaries_verified','cut_protected']:
   for value in ['false',1,None]:
    r=self.words()
    if field=='cut_protected':r['words'][0][field]=value
    else:r[field]=value
    with self.subTest(field=field,value=value),self.assertRaises(ValueError):m.word_candidates(r)
 def test_snapshot_hash_matches_parsed_words_despite_input_replacement(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'words.json';old=json.dumps(self.words()).encode();new=self.words();new['words'][0]['text']='正常';new=json.dumps(new).encode();p.write_bytes(old);read=pathlib.Path.read_bytes
   def mutate(path):
    snapshot=read(path)
    if path==p:path.write_bytes(new)
    return snapshot
   with patch.object(pathlib.Path,'read_bytes',mutate):r=m.word_candidate_snapshot(p)
   self.assertEqual(r['candidates'][0]['text'],'嗯');self.assertEqual(r['inputs']['words_sha256'],hashlib.sha256(old).hexdigest());self.assertEqual(p.read_bytes(),new)
 def test_semantic_filler_preserved(self):
  r=m.candidates({'segments':[{'id':0,'start':0,'end':1,'text':'嗯，我觉得可以。'},{'id':1,'start':1,'end':2,'text':'嗯'}]},[{'start':3,'end':5}]); self.assertEqual(len(r['candidates']),2); self.assertFalse(r['automatic_deletion']); self.assertTrue(all(s['decision']=='keep_pending_review' for s in r['candidates']))
 def test_invalid_times(self):
  with self.assertRaises(ValueError): m.candidates({'segments':[]},[{'start':5,'end':2}])
 def test_observed_silence_and_renderer(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d); audio=d/'source.wav'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','2','-c:a','pcm_s16le',str(audio)],check=True)
   intervals=m.detect_silences(audio); self.assertEqual(len(intervals),1); self.assertGreaterEqual(intervals[0]['end'],1.99)
   sha=hashlib.sha256(audio.read_bytes()).hexdigest()
   edl={'schema_version':'1.0','episode_id':'fixture','stage':'S07-buffered-edl','status':'review_required','run_key':'0'*64,'timebase':{},'source_audio':{'path':str(audio),'sha256':sha,'total_samples':96000},'adjudication_sha256':'0'*64,'policy_sha256':'0'*64,'crossfade_samples':0,'cuts':[],'summary':{},'approved':False,'publish_authorized':False}
   (d/'edl.json').write_text(json.dumps(edl)); m.render(d/'edl.json',d/'out.wav',d/'report.json')
   report=json.loads((d/'report.json').read_text()); self.assertEqual(report['duration_accounting']['error_samples'],0); self.assertFalse(report['publish_authorized'])
if __name__=='__main__': unittest.main()
