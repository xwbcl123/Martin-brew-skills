#!/usr/bin/env python3
"""Explicitly authorized PAYG ASR on bounded 16 kHz PCM WAV ranges.

Preserves the provider event stream and final response. Never edits media,
normalizes transcript text, retries failed requests, or grants cut approval.
"""
from __future__ import annotations
import argparse,datetime,gzip,hashlib,json,math,os,pathlib,queue,struct,threading,time,uuid,wave

VERSION='1.0'
ENDPOINT='wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async'
RESOURCES={'hourly':'volc.seedasr.sauc.duration','concurrent':'volc.seedasr.sauc.concurrent'}

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def packet(kind,sequence,data,serialization):
 data=gzip.compress(data)
 return bytes([0x11,(kind<<4)|(3 if sequence<0 else 1),(serialization<<4)|1,0])+struct.pack('>iI',sequence,len(data))+data

def parse(raw):
 if not isinstance(raw,bytes) or len(raw)<8:raise ValueError('invalid binary ASR response')
 offset=(raw[0]&15)*4;kind=raw[1]>>4;flags=raw[1]&15;serialization=raw[2]>>4;compression=raw[2]&15
 if raw[0]>>4!=1 or offset<4 or offset>len(raw):raise ValueError('invalid protocol header')
 row={'message_type':kind,'flags':flags}
 def integer(signed=False):
  nonlocal offset
  if offset+4>len(raw):raise ValueError('truncated response integer')
  value=int.from_bytes(raw[offset:offset+4],'big',signed=signed);offset+=4;return value
 if kind==15:row['error_code']=integer()
 elif flags&1:row['sequence']=integer(True)
 length=integer()
 if offset+length!=len(raw):raise ValueError('response payload length mismatch')
 payload=raw[offset:]
 if compression==1:payload=gzip.decompress(payload)
 elif compression!=0:raise ValueError('unsupported compression')
 if serialization==1:row['payload']=json.loads(payload)
 elif serialization==0:row['payload']=payload.decode('utf-8')
 else:raise ValueError('unsupported serialization')
 return row

def validate_final(event,expected_ms):
 if event.get('error_code') or event.get('message_type')!=9 or not event['flags']&2:raise ValueError('terminal recognition response missing')
 payload=event['payload'];code=payload.get('code')
 if code not in (None,0,20000000):raise ValueError('provider final status rejected')
 duration=payload.get('audio_info',{}).get('duration')
 if not finite_number(expected_ms) or expected_ms<=0 or not finite_number(duration) or abs(duration-expected_ms)>2:raise ValueError('returned audio duration mismatch')
 result=payload.get('result',{});utterances=result.get('utterances',[])
 if not result.get('text') or not utterances or not all(u.get('definite') for u in utterances):raise ValueError('non-empty definite final recognition required')
 words=[w for u in utterances for w in u.get('words',[])];timed=[];unlocated=[];quantized=[]
 for w in words:
  s,e=w.get('start_time'),w.get('end_time')
  if not finite_number(s) or not finite_number(e):raise ValueError('word timestamp missing or nonfinite')
  if s<0 or e<0:
   unlocated.append(w);continue
  if e<s or s>expected_ms or e>expected_ms+2:raise ValueError('word timestamps outside audio')
  if e>expected_ms:quantized.append(w)
  timed.append(w)
 if not timed:raise ValueError('timed word evidence missing')
 return {'duration_ms':duration,'utterance_count':len(utterances),'timed_word_count':len(timed),'unlocated_whitespace_count':sum(not w['text'].strip() for w in unlocated),'substantive_unlocated_words':[w for w in unlocated if w['text'].strip()],'terminal_quantization_words':quantized,'cut_boundary_validation':False,'verbatim_completeness_verified':False}

def finite_number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def recognize(audio,output,start,end,billing,key_env,pace=.01,speakers=False,max_seconds=120):
 import websocket
 key=os.environ.get(key_env,'')
 if not key:raise ValueError('credential environment variable is empty')
 source_hash=sha(audio)
 with wave.open(str(audio),'rb') as w:
  if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=16000 or w.getcomptype()!='NONE':raise ValueError('audio must be PCM16 mono 16k WAV')
  total=w.getnframes();end=total if end is None else end
  if not 0<=start<end<=total or end-start>max_seconds*16000:raise ValueError('invalid or oversized source range')
  w.setpos(start);pcm=w.readframes(end-start)
 if len(pcm)!=(end-start)*2:raise ValueError('short input audio read')
 if sha(audio)!=source_hash:raise ValueError('source changed during PCM extraction')
 config={'user':{'uid':'podcast-calibration'},'audio':{'format':'pcm','codec':'raw','rate':16000,'bits':16,'channel':1},'request':{'model_name':'bigmodel','enable_ddc':False,'enable_itn':False,'enable_punc':False,'show_utterances':True,'enable_nonstream':True,'enable_speaker_info':speakers}}
 report={'stage':'payg_asr_bounded_range','stage_version':VERSION,'tool_sha256':sha(pathlib.Path(__file__)),'websocket_client_version':getattr(websocket,'__version__','fixture'),'status':'started','source':{'path':str(audio.resolve()),'sha256':source_hash,'sample_rate':16000,'total_frames':total,'start_sample':start,'end_sample':end,'selected_pcm_sha256':hashlib.sha256(pcm).hexdigest()},'endpoint':ENDPOINT,'resource_id':RESOURCES[billing],'credential_variable':key_env,'credential_recorded':False,'request_config':config,'request_id':str(uuid.uuid4()),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audio_frames_sent':0,'automatic_deletion_approved':False}
 output.mkdir(parents=True,exist_ok=False)
 def save():
  report['output_hashes']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='report.json'}
  (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 save();ws=None;receiver=None;stop=threading.Event();events=queue.Queue();log=None;terminal=None
 try:
  ws=websocket.create_connection(ENDPOINT,header={'X-Api-Key':key,'X-Api-Resource-Id':RESOURCES[billing],'X-Api-Request-Id':report['request_id']},timeout=45)
  report['handshake']='accepted';log=(output/'responses.jsonl').open('x',encoding='utf-8')
  def log_event(raw):
   row=parse(raw);serialized=json.dumps(row,ensure_ascii=False).replace(key,'[REDACTED]');row=json.loads(serialized);log.write(serialized+'\n');log.flush();return row
  ws.send_binary(packet(1,1,json.dumps(config).encode(),1));ack=log_event(ws.recv())
  if ack.get('error_code') or isinstance(ack.get('payload'),dict) and ack['payload'].get('code') not in (None,0,20000000):raise ValueError('provider initialization rejected: '+str(ack))
  ws.settimeout(90)
  def receive():
   try:
    while not stop.is_set():
     row=log_event(ws.recv());events.put(row)
     if row.get('error_code') or isinstance(row.get('payload'),dict) and row['payload'].get('code') not in (None,0,20000000) or row['flags']&2:stop.set();break
   except Exception as exc:events.put(exc);stop.set()
  receiver=threading.Thread(target=receive,daemon=True);receiver.start()
  chunks=(len(pcm)+6399)//6400
  for i in range(chunks):
   if stop.is_set():break
   data=pcm[i*6400:(i+1)*6400];seq=i+2;ws.send_binary(packet(2,-seq if i==chunks-1 else seq,data,0));report['audio_frames_sent']+=len(data)//2
   if pace:stop.wait(pace)
  deadline=time.monotonic()+max(90,(end-start)/16000*2)
  while time.monotonic()<deadline:
   try:event=events.get(timeout=min(1,max(.01,deadline-time.monotonic())))
   except queue.Empty:continue
   if isinstance(event,Exception):raise event
   if event.get('error_code') or isinstance(event.get('payload'),dict) and event['payload'].get('code') not in (None,0,20000000):raise ValueError('provider recognition rejected: '+str(event))
   if event['flags']&2:terminal=event;break
  if report['audio_frames_sent']!=end-start:raise ValueError('incomplete audio transmission')
  qc=validate_final(terminal or {},(end-start)/16)
  if sha(audio)!=source_hash:raise ValueError('source changed during recognition')
  (output/'final.json').write_text(json.dumps(terminal,ensure_ascii=False,indent=2)+'\n');report.update({'status':'recognized','qc':qc,'terminal_response_received':True})
 except Exception as exc:
  report['status']='failed';report['error']=str(exc).replace(key,'[REDACTED]')
 finally:
  stop.set()
  if ws:
   try:ws.close()
   except Exception:pass
  if receiver:receiver.join(timeout=5)
  if receiver and receiver.is_alive():report['status']='failed';report['error']='receiver did not terminate'
  if log:log.close()
  save()
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audio',type=pathlib.Path,required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);p.add_argument('--start-sample',type=int,default=0);p.add_argument('--end-sample',type=int);p.add_argument('--billing',choices=RESOURCES,default='hourly');p.add_argument('--key-env',default='VOLC_ASR_API_KEY');p.add_argument('--packet-pause',type=float,default=.01);p.add_argument('--speaker-info',action='store_true');p.add_argument('--max-seconds',type=int,default=120);a=p.parse_args()
 if a.packet_pause<0 or a.max_seconds<=0:p.error('invalid packet pause or duration bound')
 r=recognize(a.audio,a.output_dir,a.start_sample,a.end_sample,a.billing,a.key_env,a.packet_pause,a.speaker_info,a.max_seconds)
 print(json.dumps({'status':r['status'],'output_dir':str(a.output_dir),'audio_frames_sent':r['audio_frames_sent'],'qc':r.get('qc'),'error':r.get('error')},ensure_ascii=False));return 0 if r['status']=='recognized' else 1
if __name__=='__main__':raise SystemExit(main())
