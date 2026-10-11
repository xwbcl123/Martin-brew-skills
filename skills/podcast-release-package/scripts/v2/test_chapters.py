import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('chapters',Path(__file__).with_name('chapters.py'));c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class ChaptersTests(unittest.TestCase):
 def test_id3_roundtrip_preserves_audio_and_detects_change(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);a=d/'base.mp3';b=d/'chapters.mp3'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','libmp3lame',str(a)],check=True)
   chapters=[{'start':0,'title':'开始 & 中文'},{'start':.5,'title':'第二章'}]
   r=c.embed(a,b,chapters);self.assertEqual(len(r['chapters']),2);self.assertEqual(c.pcm(a),c.pcm(b))
   with self.assertRaises(ValueError):c.embed(a,b,chapters)
   with self.assertRaises(ValueError):c.verify(a,b,[{'start':0,'title':'changed'}])
   b.write_bytes(b.read_bytes()[:-1]+b'x')
   with self.assertRaises(ValueError):c.verify(a,b,chapters)
 def test_invalid_inputs(self):
  for rows in [[],[{'start':True,'title':'x'}],[{'start':0,'title':'x'},{'start':0,'title':'y'}],[{'start':0,'title':'x\0y'}]]:
   with self.assertRaises(ValueError):c.expected(rows,1)
if __name__=='__main__':unittest.main()
