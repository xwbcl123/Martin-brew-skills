#!/usr/bin/env python3
"""Immutable shared integer-sample EDL rendering of decoded 48k audio routes.

Float PCM retains <=24-bit integer and native f32 source precision. Outputs are review-only, never editorial
approval. Non-transition PCM is compared against the actual decoded input.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,pathlib,re,subprocess,tempfile
import numpy as np
RATE=48000
P=pathlib.Path
renderer=P(__file__).resolve().parents[2]/'podcast-production-workflow/scripts/render_sample_edl.py'
spec=importlib.util.spec_from_file_location('sample_mapping',renderer);mapping=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapping)

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def integer(value,name):
 if type(value)!=int:raise ValueError(name+' must be an integer')
 return value

def geometry(edl):
 total=integer(edl['source_total_samples'],'total');fade=integer(edl['crossfade_samples'],'crossfade')
 if total<=0 or edl['sample_rate_hz']!=RATE or fade<0:raise ValueError('invalid source clock or crossfade')
 cuts=edl['cuts'];cursor=0;ranges=[]
 for cut in cuts:
  a=integer(cut['start_sample'],'cut start');b=integer(cut['end_sample'],'cut end')
  if not cursor<=a<b<=total:raise ValueError('invalid/unsorted/overlapping cut')
  if a>cursor:ranges.append((cursor,a))
  cursor=b
 if cursor<total:ranges.append((cursor,total))
 if not ranges:raise ValueError('EDL removes entire source')
 for i,(a,b) in enumerate(ranges):
  minimum=fade*((i>0)+(i<len(ranges)-1))
  if b-a<=minimum:raise ValueError('retained interval too short for crossfades')
 tracks=edl['tracks'];ids=[r['id'] for r in tracks]
 if not tracks or len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in ids):raise ValueError('invalid/duplicate track IDs')
 return ranges,fade,total,total-sum(c['end_sample']-c['start_sample'] for c in cuts)-fade*(len(ranges)-1)

def decode(track,destination):
 p=P(track['path']);digest=sha(p)
 if digest!=track['sha256']:raise ValueError('source hash mismatch')
 index=integer(track.get('stream_index',0),'stream index')
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))
 stream=next((s for s in probe['streams'] if s['index']==index),None)
 if not stream or stream.get('codec_type')!='audio' or int(stream['sample_rate'])!=RATE or stream['channels'] not in (1,2):raise ValueError('route must be 48k mono/stereo audio; no implicit resampling')
 bits=max(int(stream.get('bits_per_raw_sample') or 0),int(stream.get('bits_per_sample') or 0));fmt=stream.get('sample_fmt','');codec=stream.get('codec_name','')
 if fmt in ('dbl','dblp') or codec.startswith('pcm_f64') or fmt not in ('flt','fltp') and bits>24:raise ValueError('source precision exceeds exact f32 representation; use <=24-bit integer or native f32 PCM')
 if fmt in ('s32','s32p','s64','s64p') and not 0<bits<=24:raise ValueError('integer source precision unknown or exceeds 24 bits')
 subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(p),'-map',f'0:{index}','-c:a','pcm_f32le','-f','f32le','-n',str(destination)],capture_output=True,check=True)
 if sha(p)!=digest:raise ValueError('source changed during decode')
 channels=stream['channels'];size=destination.stat().st_size
 if size%(channels*4) or size==0:raise ValueError('incomplete float PCM decode')
 return np.memmap(destination,dtype='<f4',mode='r',shape=(size//(channels*4),channels)),stream

def render_float(source,ranges,fade,destination):
 peak=0.;cursor=0
 with destination.open('xb') as f:
  def write(a):
   nonlocal peak,cursor
   if not np.isfinite(a).all():raise ValueError('nonfinite source or rendered PCM')
   if a.size:peak=max(peak,float(np.max(np.abs(a))))
   f.write(np.asarray(a,dtype='<f4').tobytes());cursor+=len(a)
  for i,(a,b) in enumerate(ranges):
   if i and fade:
    weights=(np.arange(fade,dtype=np.float64)+.5)/fade;previous=ranges[i-1]
    write((source[previous[1]-fade:previous[1]].astype(np.float64)*(1-weights[:,None])+source[a:a+fade].astype(np.float64)*weights[:,None]).astype('<f4'))
   start=a+(fade if i else 0);end=b-(fade if i<len(ranges)-1 else 0)
   while start<end:
    stop=min(end,start+65536);write(source[start:stop]);start=stop
 return {'frames':cursor,'float_sample_peak':peak,'integer_quantization':False}

def verify_retained(source,output,maps):
 checked=0
 for m in maps['non_transition_mappings']:
  a,b=m['source_start_sample'],m['source_end_sample'];c=m['release_start_sample']
  for start in range(a,b,65536):
   n=min(65536,b-start)
   if not np.array_equal(source[start:start+n],output[c+start-a:c+start-a+n]):raise ValueError('retained PCM changed or moved off mapping')
   checked+=n
 return {'non_transition_frames_compared':checked,'retained_pcm_exact':True,'precision_scope':'canonical decoded f32 samples; high-precision integer/f64 sources rejected; no lossless-original claim for lossy sources','audible_join_defects_proven_absent':False}

def run(edl_path,output):
 edl_digest=sha(edl_path);edl=json.loads(edl_path.read_text());ranges,fade,total,expected=geometry(edl);maps=mapping.build_mapping(ranges,fade)
 output.mkdir(parents=True,exist_ok=False)
 report={'stage':'shared_route_review_render','status':'started','edl_sha256':edl_digest,'tool_sha256':sha(P(__file__)),'mapping_tool_sha256':sha(renderer),'source_total_samples':total,'expected_output_samples':expected,'removed_samples':total-sum(b-a for a,b in ranges),'crossfade_overlap_samples':fade*(len(ranges)-1),'mapping':maps,'routes':[],'editorial_approved':False,'publish_authorized':False,'human_join_audit_required':True}
 def save():
  report['output_hashes']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='report.json'}
  (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 save()
 try:
  # Decode every route and validate the actual clock before rendering any route.
  with tempfile.TemporaryDirectory(prefix='route-edl-') as td:
   temp=P(td);decoded=[]
   for i,track in enumerate(edl['tracks']):
    pcm,probe=decode(track,temp/f'input-{i}.f32');decoded.append((track,pcm,probe))
    if len(pcm)!=total:raise ValueError('route decoded sample count differs from shared source clock')
   for i,(track,pcm,probe) in enumerate(decoded):
    raw=temp/f'output-{i}.f32';qc=render_float(pcm,ranges,fade,raw)
    if qc['frames']!=expected:raise ValueError('rendered sample accounting mismatch')
    target=output/(track['id']+'.wav')
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac',str(pcm.shape[1]),'-i',str(raw),'-c:a','pcm_f32le','-n',str(target)],capture_output=True,check=True)
    route={'id':track['id'],'path':str(target.resolve()),'sha256':sha(target),'stream_index':track.get('stream_index',0),'source_path':str(P(track['path']).resolve()),'source_sha256':track['sha256'],'decoded_samples':len(pcm),'sample_rate_hz':RATE,'channels':pcm.shape[1],**qc}
    final_pcm,_=decode({'path':str(target),'sha256':route['sha256'],'stream_index':0},temp/f'readback-{i}.f32')
    if len(final_pcm)!=expected:raise ValueError('actual output decode count mismatch')
    route['retained_proof']=verify_retained(pcm,final_pcm,maps);report['routes'].append(route);save()
   if sha(edl_path)!=edl_digest or any(sha(P(t['path']))!=t['sha256'] for t in edl['tracks']):raise ValueError('inputs changed during rendering')
  report['status']='review_required';report['shared_route_sample_clock_verified']=True
 except Exception as exc:
  report['status']='failed';report['error']=str(exc)
 save();return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--edl',type=P,required=True);p.add_argument('--output-dir',type=P,required=True);a=p.parse_args();r=run(a.edl,a.output_dir);print(json.dumps({k:r.get(k) for k in ['status','expected_output_samples','shared_route_sample_clock_verified','error']},ensure_ascii=False));return 0 if r['status']=='review_required' else 1
if __name__=='__main__':raise SystemExit(main())
