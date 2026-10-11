import http.client
import importlib.util
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
spec=importlib.util.spec_from_file_location('preview_server',Path(__file__).resolve().parents[1]/'scripts/serve_preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RangeTests(unittest.TestCase):
 def test_real_http_audio_ranges(self):
  with tempfile.TemporaryDirectory() as t:
   (Path(t)/'a.mp3').write_bytes(b'0123456789');server=ThreadingHTTPServer(('127.0.0.1',0),partial(m.RangeHandler,directory=t));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    for value,status,body in [('bytes=2-5',206,b'2345'),('bytes=8-',206,b'89'),('bytes=-3',206,b'789'),('bytes=99-',416,b'')]:
     c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request('GET','/a.mp3',headers={'Range':value});r=c.getresponse();self.assertEqual(r.status,status);self.assertEqual(r.read(),body);c.close()
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
