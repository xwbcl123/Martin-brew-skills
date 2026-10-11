#!/usr/bin/env python3
"""ID3-only chapter metadata; preserve every encoded audio byte and decoded sample."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def synchsafe(n):
    if not 0 <= n < 1 << 28: raise ValueError('ID3 size out of range')
    return bytes([(n >> 21) & 127, (n >> 14) & 127, (n >> 7) & 127, n & 127])


def encoded_audio(path):
    b = Path(path).read_bytes()
    if b[:3] == b'ID3':
        if len(b) < 10 or any(x & 128 for x in b[6:10]): raise ValueError('Invalid ID3 header')
        n = sum(v << shift for v, shift in zip(b[6:10], [21, 14, 7, 0]))
        end = 10 + n + (10 if b[3] == 4 and b[5] & 16 else 0)
        if end >= len(b): raise ValueError('ID3 consumes audio')
        b = b[end:]
    if b[-128:-125] == b'TAG': b = b[:-128]
    return b


def probe(path):
    return json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(path)],check=True,capture_output=True,text=True,timeout=90).stdout)


def pcm(path):
    s = [s for s in probe(path)['streams'] if s.get('codec_type') == 'audio']
    if len(s) != 1: raise ValueError('One audio stream required')
    p = subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(path),'-map','0:a:0','-c:a','pcm_f32le','-f','f32le','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    h = hashlib.sha256(); size = 0
    for b in iter(lambda:p.stdout.read(1024*1024),b''): h.update(b); size += len(b)
    p.stdout.close()
    if p.wait(): raise ValueError('PCM decode failed')
    return {'sha256':h.hexdigest(),'bytes':size,'sample_rate':int(s[0]['sample_rate']),'channels':int(s[0]['channels']),'frames':size//(4*int(s[0]['channels']))}


def expected(chapters, duration):
    out = []; previous = -1
    for i, c in enumerate(chapters):
        start = c['start']; title = c['title']
        if isinstance(start,bool) or not isinstance(start,(int,float)) or not math.isfinite(start) or not previous < start < duration or not isinstance(title,str) or not title.strip() or '\x00' in title: raise ValueError('Invalid chapter')
        end = chapters[i+1]['start'] if i+1 < len(chapters) else duration
        out.append({'start_ms':round(start*1000),'end_ms':round(end*1000),'title':title}); previous=start
    if not out or len(out) > 255: raise ValueError('Chapter count must be 1..255')
    return out


def read_chapters(path):
    return [{'start_ms':round(float(c['start_time'])*1000),'end_ms':round(float(c['end_time'])*1000),'title':c.get('tags',{}).get('title','')} for c in probe(path).get('chapters',[])]


def verify(base, tagged, chapters):
    duration = float(probe(base)['format']['duration']); wanted = expected(chapters,duration)
    if encoded_audio(base) != encoded_audio(tagged): raise ValueError('Encoded audio changed beyond ID3 metadata')
    if read_chapters(tagged) != wanted: raise ValueError('Embedded chapters differ')
    a,b = pcm(base),pcm(tagged)
    if a != b: raise ValueError('Decoded audio changed')
    return {'kind':'id3_only','base_audio_sha256':sha(base),'tagged_audio_sha256':sha(tagged),'encoded_audio_sha256':hashlib.sha256(encoded_audio(base)).hexdigest(),'pcm':a,'chapters':wanted,'new_asr_performed':False}


def embed(base, output, chapters):
    base,output = Path(base),Path(output)
    if output.exists() or output.is_symlink(): raise ValueError('Output must be a new file')
    wanted=expected(chapters,float(probe(base)['format']['duration']))
    def frame(name,data): return name.encode()+synchsafe(len(data))+b'\x00\x00'+data
    ids=[f'ch{i}'.encode() for i in range(len(wanted))]
    body=frame('CTOC',b'toc\x00\x03'+bytes([len(ids)])+b''.join(i+b'\x00' for i in ids))
    for eid,c in zip(ids,wanted):
        body+=frame('CHAP',eid+b'\x00'+struct.pack('>IIII',c['start_ms'],c['end_ms'],0xffffffff,0xffffffff)+frame('TIT2',b'\x03'+c['title'].encode()))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as f:f.write(b'ID3\x04\x00\x00'+synchsafe(len(body))+body+encoded_audio(base))
    return verify(base,output,chapters)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--chapters',required=True,type=Path);p.add_argument('--report',required=True,type=Path)
    a=p.parse_args();r=embed(a.base,a.output,json.loads(a.chapters.read_text()));a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
