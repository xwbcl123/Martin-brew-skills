import importlib.util,json,pathlib,subprocess,tempfile,unittest,wave,math,array
P=pathlib.Path
s=importlib.util.spec_from_file_location('mastering',P(__file__).parents[1]/'scripts/mastering.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class DeliveryTests(unittest.TestCase):
 def test_actual_codec_and_immutable_cache(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); src=d/'misleading.mp3'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=4','-ar','44100','-c:a','aac','-f','adts',str(src)],check=True)
   original=m.sha256(src); self.assertEqual(m.probe(src)['codec'],'aac')
   r=m.produce(src,d/'out',mode='loudness_only'); self.assertEqual(r['output']['codec'],'mp3'); self.assertEqual(r['qc_status'],'pass'); self.assertEqual(original,m.sha256(src)); self.assertEqual(m.produce(src,d/'out',mode='loudness_only')['run_key'],r['run_key'])
   (d/'out/delivery.mp3').write_bytes(b'changed')
   with self.assertRaises(ValueError): m.produce(src,d/'out',mode='loudness_only')
 def test_peak_limiter_method_and_fresh_measurement(self):
  with tempfile.TemporaryDirectory() as d:
   d=P(d); audio=d/'peaks.wav'; rate=44100
   values=array.array('h',(int(32767*(.95 if i%rate<80 else .12)*math.sin(2*math.pi*700*i/rate)) for i in range(rate*5)))
   with wave.open(str(audio),'wb') as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(values.tobytes())
   r=m.produce(audio,d/'out',mode='loudness_only')
   self.assertEqual(r['processing']['method'],'static_gain_oversampled_peak_limiter'); self.assertEqual(r['qc_status'],'pass'); self.assertLessEqual(r['metrics']['true_peak_dbtp'],r['identity']['profile']['max_true_peak_dbtp']); self.assertEqual(r['input']['sample_count'],r['output']['sample_count'])
 def test_missing_source_not_measured(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(FileNotFoundError): m.produce(P(d)/'absent',P(d)/'out')
if __name__=='__main__': unittest.main()
