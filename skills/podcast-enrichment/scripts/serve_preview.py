#!/usr/bin/env python3
"""Loopback-only preview server with single byte ranges for native audio seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        path = Path(self.translate_path(self.path))
        header = self.headers.get('Range')
        if not header or not path.is_file(): return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
        if not match or not any(match.groups()) or size == 0:
            self.send_error(416, 'Unsupported byte range'); return None
        left,right = match.groups()
        if left:
            start = int(left); end = min(int(right),size-1) if right else size-1
        else:
            start = max(0,size-int(right)); end = size-1
        if start > end or start >= size:
            self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.send_header('Content-Length','0'); self.end_headers(); return None
        f = path.open('rb'); f.seek(start); self.remaining = end-start+1
        self.send_response(206); self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(self.remaining));self.send_header('Accept-Ranges','bytes');self.end_headers()
        return f

    def end_headers(self):
        if getattr(self, "remaining", None) is None: self.send_header('Accept-Ranges','bytes')
        super().end_headers()

    def copyfile(self, source, output):
        if self.remaining is None: return super().copyfile(source,output)
        remaining = self.remaining
        while remaining:
            chunk = source.read(min(1024*1024,remaining))
            if not chunk: break
            output.write(chunk); remaining -= len(chunk)

    def log_message(self, *args): pass

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--port',type=int,default=8769);a=p.parse_args()
    ThreadingHTTPServer(('127.0.0.1',a.port),partial(RangeHandler,directory=str(a.directory.resolve()))).serve_forever()
