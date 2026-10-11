import copy,importlib.util,json,pathlib,subprocess,tempfile,unittest,wave
import numpy as np
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/render_routes.py';spec=importlib.util.spec_from_file_location('render_routes',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RouteTests(unittest.TestCase):
 def edl(self):return {'source_total_samples':4800,'sample_rate_hz':48000,'crossfade_samples':24,'cuts':[{'start_sample':1200,'end_sample':1600}],'tracks':[{'id':'one'}]}
 def test_invalid_sample_edl_rejected(self):
  for change in ['decimal','bool','overlap','short','entire','bad_id','duplicate','rate']:
   e=self.edl()
   if change=='decimal':e['cuts'][0]['start_sample']=1200.5
   elif change=='bool':e['crossfade_samples']=True
   elif change=='overlap':e['cuts'].append({'start_sample':1500,'end_sample':1800})
   elif change=='short':e['cuts'][0]['start_sample']=24
   elif change=='entire':e['cuts']=[{'start_sample':0,'end_sample':4800}]
   elif change=='bad_id':e['tracks'][0]['id']='../escape'
   elif change=='duplicate':e['tracks']*=2
   else:e['sample_rate_hz']=44100
   with self.subTest(change=change),self.assertRaises(ValueError):m.geometry(e)
 def wav(self,p,n=4800,rate=48000,zero=False):
  t=np.arange(n);a=np.zeros((n,2),dtype='<i2') if zero else np.stack(((np.sin(t/13)*9000).astype('<i2'),(np.cos(t/17)*12000).astype('<i2')),axis=1)
  with wave.open(str(p),'wb') as w:w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes(a.tobytes())
 def test_three_routes_same_edl_actual_readback_and_retained_pcm(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);e=self.edl();e['tracks']=[]
   for i in range(3):
    p=root/f'input{i}.wav';self.wav(p,zero=i==2);e['tracks'].append({'id':f'route{i}','path':str(p),'sha256':m.sha(p)})
   p=root/'edl.json';p.write_text(json.dumps(e));r=m.run(p,root/'out')
   self.assertEqual(r['status'],'review_required');self.assertEqual(r['expected_output_samples'],4376);self.assertFalse(r['editorial_approved'])
   self.assertEqual([x['frames'] for x in r['routes']],[4376]*3);self.assertTrue(all(x['retained_proof']['retained_pcm_exact'] for x in r['routes']));self.assertEqual(r['routes'][2]['float_sample_peak'],0)
   with self.assertRaises(FileExistsError):m.run(p,root/'out')
 def test_mismatched_route_length_and_hash_fail_before_render(self):
  for change in ['length','rate','hash']:
   with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td);e=self.edl();e['tracks']=[]
    for i in range(2):
     p=root/f'input{i}.wav';self.wav(p,n=4799 if i==1 and change=='length' else 4800,rate=44100 if i==1 and change=='rate' else 48000);e['tracks'].append({'id':f'route{i}','path':str(p),'sha256':m.sha(p) if not(i==1 and change=='hash') else '0'*64})
    p=root/'edl.json';p.write_text(json.dumps(e));r=m.run(p,root/'out');self.assertEqual(r['status'],'failed');self.assertFalse(list((root/'out').glob('*.wav')))
 def test_retained_compare_detects_displacement(self):
  e=self.edl();ranges,fade,total,expected=m.geometry(e);source=np.arange(total,dtype='<f4')[:,None]
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'raw.f32';m.render_float(source,ranges,fade,p);out=np.fromfile(p,dtype='<f4').reshape(-1,1);maps=m.mapping.build_mapping(ranges,fade);self.assertTrue(m.verify_retained(source,out,maps)['retained_pcm_exact']);out[0]=source[1]
   with self.assertRaises(ValueError):m.verify_retained(source,out,maps)
 def test_pcm32_and_float64_rejected_before_any_render(self):
  for codec in ['pcm_s32le','pcm_f64le']:
   with self.subTest(codec=codec),tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td);raw=root/'raw';p=root/'high.wav'
    if codec=='pcm_s32le':np.full(4800,1073741827,dtype='<i4').tofile(raw);fmt='s32le'
    else:np.full(4800,.5000000001,dtype='<f8').tofile(raw);fmt='f64le'
    subprocess.run(['ffmpeg','-v','error','-f',fmt,'-ar','48000','-ac','1','-i',str(raw),'-c:a',codec,str(p)],capture_output=True,check=True)
    e=self.edl();e['cuts']=[];e['crossfade_samples']=0;e['tracks']=[{'id':'high','path':str(p),'sha256':m.sha(p)}];plan=root/'edl.json';plan.write_text(json.dumps(e));r=m.run(plan,root/'out');self.assertEqual(r['status'],'failed');self.assertIn('precision',r['error']);self.assertFalse(list((root/'out').glob('*.wav')))
 def test_pcm24_low_bits_preserved_with_no_cuts(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);raw=root/'raw';p=root/'input.wav';values=np.full(4800,4194307,dtype='<i4');(values*256).astype('<i4').tofile(raw)
   subprocess.run(['ffmpeg','-v','error','-f','s32le','-ar','48000','-ac','1','-i',str(raw),'-c:a','pcm_s24le',str(p)],capture_output=True,check=True)
   e=self.edl();e['cuts']=[];e['crossfade_samples']=0;e['tracks']=[{'id':'low','path':str(p),'sha256':m.sha(p)}];plan=root/'edl.json';plan.write_text(json.dumps(e));r=m.run(plan,root/'out');self.assertEqual(r['status'],'review_required')
   readback=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'out/low.wav'),'-f','s32le','-c:a','pcm_s32le','-']);self.assertTrue(np.array_equal(np.frombuffer(readback,dtype='<i4'),values*256))
if __name__=='__main__':unittest.main()
