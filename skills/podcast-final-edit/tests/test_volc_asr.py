import importlib.util,json,pathlib,struct,unittest,os,sys,tempfile,wave,types,threading
from unittest.mock import patch
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/volc_asr.py';spec=importlib.util.spec_from_file_location('volc_asr',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProtocolTests(unittest.TestCase):
 def event(self):
  return {'message_type':9,'flags':3,'payload':{'audio_info':{'duration':30000},'result':{'text':'嗯好','utterances':[{'definite':True,'words':[{'text':'嗯','start_time':100,'end_time':200},{'text':' ','start_time':-1,'end_time':-1},{'text':'好','start_time':29900,'end_time':30002}]}]}}}
 def test_binary_terminal_sequence_and_payload(self):
  payload=json.dumps(self.event()['payload']).encode();raw=m.packet(9,-7,payload,1);result=m.parse(raw);self.assertEqual(result['sequence'],-7);self.assertTrue(result['flags']&2);self.assertEqual(result['payload']['audio_info']['duration'],30000)
 def test_error_frame_and_truncated_payload(self):
  payload=json.dumps({'error':'quota exceeded'}).encode();raw=bytes([0x11,0xf0,0x10,0])+struct.pack('>II',45000292,len(payload))+payload;self.assertEqual(m.parse(raw)['error_code'],45000292)
  with self.assertRaises(ValueError):m.parse(raw[:-1])
 def test_whitespace_and_end_quantization_remain_raw(self):
  event=self.event();before=json.dumps(event,sort_keys=True);qc=m.validate_final(event,30000);self.assertEqual(qc['unlocated_whitespace_count'],1);self.assertEqual(len(qc['terminal_quantization_words']),1);self.assertEqual(before,json.dumps(event,sort_keys=True));self.assertFalse(qc['cut_boundary_validation'])
 def test_missing_terminal_wrong_duration_and_nondefinite_fail(self):
  for update in ['nonterminal','duration','partial','overflow','zero_words']:
   event=self.event()
   if update=='nonterminal':event['flags']=1
   elif update=='duration':event['payload']['audio_info']['duration']=29000
   elif update=='partial':event['payload']['result']['utterances'][0]['definite']=False
   elif update=='overflow':event['payload']['result']['utterances'][0]['words'][0]['end_time']=30003
   else:event['payload']['result']['utterances'][0]['words']=[]
   with self.subTest(update=update),self.assertRaises(ValueError):m.validate_final(event,30000)
 def test_negative_substantive_words_are_visible_review_blockers(self):
  event=self.event();event['payload']['result']['utterances'][0]['words'][1]['text']='机场';qc=m.validate_final(event,30000);self.assertEqual(qc['substantive_unlocated_words'][0]['text'],'机场')
 def test_nonfinite_and_boolean_time_values_rejected(self):
  for field in ['duration','start_time','end_time']:
   for value in [float('nan'),float('inf'),float('-inf'),True]:
    event=self.event()
    if field=='duration':event['payload']['audio_info']['duration']=value
    else:event['payload']['result']['utterances'][0]['words'][0][field]=value
    with self.subTest(field=field,value=value),self.assertRaises(ValueError):m.validate_final(event,30000)
class InitializationTests(unittest.TestCase):
 def test_source_change_during_extraction_never_connects(self):
  with tempfile.TemporaryDirectory() as td:
   audio=pathlib.Path(td)/'input.wav'
   with wave.open(str(audio),'wb') as w:
    w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0'*32000)
   from unittest.mock import Mock
   connect=Mock();fake=types.SimpleNamespace(create_connection=connect)
   with patch.dict(os.environ,{'TEST_ASR_KEY':'test'}),patch.dict(sys.modules,{'websocket':fake}),patch.object(m,'sha',side_effect=['before','after']):
    with self.assertRaisesRegex(ValueError,'source changed'):m.recognize(audio,pathlib.Path(td)/'attempt',0,None,'hourly','TEST_ASR_KEY')
   connect.assert_not_called()
 def test_source_change_during_recognition_keeps_failed_attempt(self):
  with tempfile.TemporaryDirectory() as td:
   audio=pathlib.Path(td)/'input.wav';output=pathlib.Path(td)/'attempt';audio_done=threading.Event()
   with wave.open(str(audio),'wb') as w:
    w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0'*32000)
   class Socket:
    def __init__(self):self.first=True
    def send_binary(self,b):
     if b[1]>>4==2 and b[1]&2:
      with audio.open('r+b') as f:f.seek(44);f.write(b'\x01\x00')
      audio_done.set()
    def recv(self):
     if self.first:self.first=False;return m.packet(9,1,b'{}',1)
     if not audio_done.wait(2):raise TimeoutError('fixture timeout')
     return m.packet(9,-6,json.dumps({'audio_info':{'duration':1000},'result':{'text':'好','utterances':[{'definite':True,'words':[{'text':'好','start_time':100,'end_time':200}]}]}}).encode(),1)
    def settimeout(self,t):pass
    def close(self):pass
   with patch.dict(os.environ,{'TEST_ASR_KEY':'fixture-secret'}),patch.dict(sys.modules,{'websocket':types.SimpleNamespace(create_connection=lambda *a,**k:Socket())}):
    report=m.recognize(audio,output,0,None,'hourly','TEST_ASR_KEY',pace=0)
   self.assertEqual(report['status'],'failed');self.assertIn('source changed',report['error']);self.assertFalse((output/'final.json').exists());self.assertTrue((output/'responses.jsonl').exists())
 def test_rejected_initialization_sends_no_audio_and_redacts_key(self):
  secret='FAKE-0001';sent=[]
  class RejectedSocket:
   def send_binary(self,b):sent.append(b)
   def recv(self):
    body=json.dumps({'error':secret+' quota rejected'}).encode()
    return bytes([0x11,0xf0,0x10,0])+struct.pack('>II',45000292,len(body))+body
   def close(self):pass
  fake=types.SimpleNamespace(create_connection=lambda *args,**kwargs:RejectedSocket())
  with tempfile.TemporaryDirectory() as td:
   audio=pathlib.Path(td)/'input.wav';output=pathlib.Path(td)/'attempt'
   with wave.open(str(audio),'wb') as w:
    w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0'*32000)
   with patch.dict(os.environ,{'TEST_ASR_KEY':secret}),patch.dict(sys.modules,{'websocket':fake}):
    report=m.recognize(audio,output,0,None,'hourly','TEST_ASR_KEY')
   self.assertEqual(report['status'],'failed');self.assertEqual(report['audio_frames_sent'],0);self.assertEqual(len(sent),1)
   for f in output.iterdir():self.assertNotIn(secret,f.read_text())
   self.assertFalse((output/'final.json').exists());self.assertTrue(report['output_hashes'])
if __name__=='__main__':unittest.main()
