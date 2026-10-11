import copy,importlib.util,json,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/merge_asr.py';spec=importlib.util.spec_from_file_location('merge_asr',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MergeTests(unittest.TestCase):
 def plan(self):
  return {'source_total_frames':64000,'sample_rate_hz':16000,'records':[{'start':0,'end':32000,'core_start':0,'core_end':16000},{'start':0,'end':64000,'core_start':16000,'core_end':64000}]}
 def result(self):
  return {'utterances':[{'additions':{'speaker_id':'0'},'words':[{'text':'好','start_time':500,'end_time':700},{'text':'嗯','start_time':1500,'end_time':1700},{'text':' ','start_time':-1,'end_time':-1}]}]}
 def test_cores_complete_tail_rounding_and_gaps_rejected(self):
  plan=self.plan();self.assertEqual(len(m.geometry(plan,192001)),2)
  plan['records'][1]['core_start']+=1
  with self.assertRaises(ValueError):m.geometry(plan,192001)
  with self.assertRaises(ValueError):m.geometry(self.plan(),192010)
 def test_overlap_ownership_preserves_words_once_and_request_scoped_speakers(self):
  plan=self.plan();r=m.select_words(plan['records'],[self.result(),self.result()],192001)
  self.assertEqual([x['text'] for x in r['words']],['好','嗯']);self.assertEqual([x['start_sample'] for x in r['words']],[24000,72000]);self.assertEqual(r['words'][0]['provider_speaker_scoped'],'request-0:0');self.assertEqual(r['words'][1]['provider_speaker_scoped'],'request-1:0');self.assertTrue(all(w['cut_protected'] for w in r['words']));self.assertEqual(r['overlap_checks'][0]['normalized_character_agreement'],1)
 def test_substantive_negative_time_evidence_retained(self):
  a=self.result();a['utterances'][0]['words'][-1]['text']='缺失';r=m.select_words(self.plan()['records'],[a,self.result()],192000);self.assertEqual(r['unlocated_entries'][0]['raw_word']['text'],'缺失')
 def test_bad_durations_and_missing_responses_refused(self):
  with self.assertRaises(ValueError):m.select_words(self.plan()['records'],[self.result()],192000)
  a=self.result();a['utterances'][0]['words'][0]['end_time']=3000
  with self.assertRaises(ValueError):m.select_words(self.plan()['records'],[a,self.result()],192000)
 def test_tail_correction_never_emits_reverse_or_unprotected_empty_ranges(self):
  spec=[{'start':0,'end':16000,'core_start':0,'core_end':16000}]
  a=self.result();a['utterances'][0]['words']=[{'text':'尾','start_time':999.97,'end_time':999.98},{'text':'字','start_time':999.96,'end_time':1000.01}]
  r=m.select_words(spec,[a],47998)
  self.assertEqual(len(r['unlocated_entries']),1);self.assertEqual(r['unlocated_entries'][0]['raw_word']['text'],'尾')
  self.assertEqual([r['words'][0][x] for x in ['start_sample','end_sample']],[47998,47998]);self.assertTrue(r['words'][0]['cut_protected'])
 def test_final_error_and_detached_or_multiple_terminal_events_rejected(self):
  event={'message_type':9,'flags':3,'payload':{'audio_info':{'duration':1000},'result':{'text':'好','utterances':[{'definite':True}]}}}
  self.assertEqual(m.final_evidence(event,[event],1000)['text'],'好')
  for mutation in ['error_code','payload_code','nan','infinity','boolean','detached','multiple','empty_utterances']:
   final=copy.deepcopy(event);raw=[copy.deepcopy(event)]
   if mutation=='error_code':final['error_code']=45000292
   elif mutation=='payload_code':final['payload']['code']=45000292
   elif mutation in ['nan','infinity','boolean']:final['payload']['audio_info']['duration']={'nan':float('nan'),'infinity':float('inf'),'boolean':True}[mutation]
   elif mutation=='detached':raw=[]
   elif mutation=='multiple':raw.append(copy.deepcopy(event))
   else:final['payload']['result']['utterances']=[]
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):m.final_evidence(final,raw,1000)
if __name__=='__main__':unittest.main()
