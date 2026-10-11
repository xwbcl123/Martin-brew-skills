#!/usr/bin/env python3
"""Derive transcript from a verified sample edit; never labels old raw ASR as new inference."""
import argparse, copy, hashlib, importlib.util, json, math, os, pathlib, shutil, subprocess, tempfile
from decimal import Decimal
P=pathlib.Path

def sha(path):
 h=hashlib.sha256()
 with P(path).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()

def read(path): return json.loads(P(path).read_text())
def write(path,data): P(path).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def safe(root,rel):
 root=P(root).resolve(); rel=P(rel)
 if rel.is_absolute() or '..' in rel.parts: raise ValueError('unsafe derived evidence path')
 p=root/rel
 if not p.is_file() or any(q.is_symlink() for q in [p,*p.parents] if q!=root and q.is_relative_to(root)): raise ValueError('missing/symlink derived evidence')
 return p

def replay(raw,ledger):
 rows=[]; ids={i for i,s in enumerate(raw['transcription']) if s.get('text','').strip()}
 if any(c.get('segment_id') not in ids for c in ledger['corrections']): raise ValueError('correction targets nonexistent raw segment')
 for i,s in enumerate(raw['transcription']):
  if not s.get('text','').strip(): continue
  v={'text':s['text'].strip(),'start':s['offsets']['from']/1000,'end':s['offsets']['to']/1000}
  for c in ledger['corrections']:
   if c.get('segment_id')==i:
    key=c.get('field')
    if key not in v or c.get('before')!=v[key] or not c.get('reason'): raise ValueError('invalid correction chain')
    v[key]=c['after']
  if not isinstance(v['text'],str): raise ValueError('invalid corrected text')
  if v['text'].strip(): rows.append({'id':i,**v,'speaker':'unknown'})
 return rows

def map_edit(segments,edl):
 rate=edl['sample_rate']; bounds=edl['remove_samples']
 if type(rate) is not int or rate<=0 or len(bounds)!=2 or any(type(x) is not int for x in bounds) or not 0<=bounds[0]<bounds[1] or edl.get('range_semantics')!='[start,end)': raise ValueError('invalid sample edit')
 start=Decimal(bounds[0])/Decimal(rate); end=Decimal(bounds[1])/Decimal(rate); delta=end-start
 if Decimal(str(edl['removed_seconds']))!=delta: raise ValueError('EDL seconds differ from sample count')
 result=[]; corrections=[]; removed=[]
 for s in segments:
  a,b=Decimal(str(s['start'])),Decimal(str(s['end']))
  if b<=start: result.append(copy.deepcopy(s))
  elif a>=end:
   item=copy.deepcopy(s)
   for field in ('start','end'):
    value=float(Decimal(str(s[field]))-delta); item[field]=value
    corrections.append({'segment_id':s['id'],'field':field,'before':s[field],'after':value,'reason':'sample edit timeline shift after removed interval','accuracy':'sample_edit_mapping','raw_preserved':True})
   result.append(item)
  elif a>=start and b<=end:
   removed.append(s['id']); corrections.append({'segment_id':s['id'],'field':'text','before':s['text'],'after':'','reason':'segment fully contained in explicitly removed privacy sample interval','raw_preserved':True})
  else: raise ValueError('sample cut crosses transcript segment; explicit boundary review required')
 return result,corrections,removed

def decoded(path,dest):
 info=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_streams','-of','json',str(path)],check=True,capture_output=True,text=True).stdout)['streams'][0]
 with P(dest).open('wb') as f: subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(path),'-map','0:a:0','-c:a','pcm_s32le','-f','s32le','-'],stdout=f,stderr=subprocess.PIPE,check=True)
 channels=int(info['channels']); return {'codec':info['codec_name'],'sample_rate':int(info['sample_rate']),'channels':channels,'sample_count':P(dest).stat().st_size//(4*channels)}

def pcm_edit_check(source,edited,edl):
 with tempfile.TemporaryDirectory(prefix='podcast-edit-verify-') as d:
  d=P(d); a=d/'source.pcm'; b=d/'edited.pcm'; src=decoded(source,a); dst=decoded(edited,b)
  rate=edl['sample_rate']; start,end=edl['remove_samples']; fade=math.ceil(float(edl.get('fades_ms',0))*rate/1000)
  if src['codec'] not in ('pcm_s16le','pcm_s24le','pcm_s32le') or dst['codec'] not in ('pcm_s16le','pcm_s24le','pcm_s32le'): raise ValueError('exact PCM branch requires integer PCM WAV')
  if src['sample_rate']!=rate or dst['sample_rate']!=rate or src['channels']!=dst['channels'] or dst['sample_count']!=src['sample_count']-(end-start) or end>src['sample_count']: raise ValueError('fresh PCM sample edit accounting mismatch')
  if not 0<=fade<=math.ceil(rate*.005): raise ValueError('unsupported fade tolerance')
  width=src['channels']*4
  def compare(so,do,n):
   with a.open('rb') as x,b.open('rb') as y:
    x.seek(so*width); y.seek(do*width); remaining=n*width
    while remaining:
     size=min(8*1024*1024,remaining)
     if x.read(size)!=y.read(size): raise ValueError('retained PCM differs outside declared join fade')
     remaining-=size
  compare(0,0,max(0,start-fade)); compare(end+fade,start+fade,max(0,src['sample_count']-end-fade))
  return {'source':src,'edited':dst,'retained_pcm_exact_outside_join_fade':True,'excluded_join_fade_samples_each_side':fade,'precision':'sample'}

def verify_delivery_encoding(wave_path,delivery_path,report):
    spec=importlib.util.spec_from_file_location('derived_mastering_reproduction',P(__file__).with_name('mastering.py') if P(__file__).with_name('mastering.py').exists() else P(__file__).resolve().parents[2]/'podcast-mastering/scripts/mastering.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    identity=report['identity']; profile=identity['profile']
    if identity.get('implementation')!=sha(P(module.__file__)) or identity.get('legacy_compute')!=sha(P(module.legacy.__file__)): raise ValueError('unsupported mastering implementation for exact reproduction')
    if identity.get('ffmpeg')!=module.run(['ffmpeg','-version']).stdout: raise ValueError('FFmpeg changed; exact reproduction unavailable')
    mode=identity['mode']
    if mode not in ('encode_only','loudness_only'): raise ValueError('unsupported mastering reproduction mode')
    with tempfile.TemporaryDirectory(prefix='verify-master-encoding-') as d:
        output=P(d)/'delivery.mp3'; before=module.probe(wave_path)
        rate=before['sample_rate'] if before['sample_rate'] in profile['sample_rates'] else profile['sample_rates'][0]
        argv=['ffmpeg','-v','info','-nostdin','-n','-i',wave_path,'-map','0:a:0','-vn']
        if mode=='loudness_only':
            peak=profile['max_true_peak_dbtp']-identity['peak_headroom']; measured,_=module.legacy.loudness(wave_path,profile['target_lufs'],peak,50)
            gain=profile['target_lufs']-measured['integrated_lufs']; limit=10**(peak/20)
            argv+=['-af',f'aresample=192000,volume={gain}dB,alimiter=limit={limit}:level=false:latency=true,aresample={rate}']
        argv+=['-ar',str(rate),'-c:a','libmp3lame','-b:a',str(identity['bitrate'])+'k',output]
        module.run(argv)
        if sha(output)!=sha(delivery_path): raise ValueError('delivery bytes differ from deterministic mastering reproduction')
    return {'method':'deterministic_ffmpeg_reencoding','audio_sha256':sha(delivery_path),'byte_identical':True}

def verify(root,lineage,aligned,ledger,raw_path,delivery_path):
 """Independent deterministic verification callable from the release validator."""
 if lineage.get('kind')!='sample_edit_derived_transcription' or lineage.get('new_asr_performed') is not False: raise ValueError('invalid edit-derived kind')
 paths={}
 for role,a in lineage['evidence'].items():
  p=safe(root,a['path'])
  if sha(p)!=a['sha256']: raise ValueError('derived evidence changed: '+role)
  paths[role]=p
 required={'source_raw','source_raw_txt','source_aligned','source_ledger','source_delivery','source_wave','edited_wave','edl','source_master_report','delivery_report'}
 if not required.issubset(paths): raise ValueError('incomplete edit-derived evidence')
 old=sha(paths['source_delivery']); new=sha(delivery_path)
 if lineage.get('source_audio_sha256')!=old or lineage.get('audio_sha256')!=new or aligned.get('audio_sha256')!=new or ledger.get('audio_sha256')!=new: raise ValueError('derived audio identity mismatch')
 if sha(raw_path)!=sha(paths['source_raw']) or ledger.get('raw_json_sha256')!=sha(raw_path): raise ValueError('derived raw identity mismatch')
 source_ledger=read(paths['source_ledger']); source_aligned=read(paths['source_aligned']); source_raw=read(paths['source_raw']); edl=read(paths['edl'])
 if source_ledger.get('audio_sha256')!=old or source_aligned.get('audio_sha256')!=old or source_ledger.get('raw_json_sha256')!=sha(paths['source_raw']): raise ValueError('source ASR lineage mismatch')
 if replay(source_raw,source_ledger)!=source_aligned['segments']: raise ValueError('source correction/aligned concordance failed')
 if source_raw.get('result',{}).get('language')!=source_aligned.get('language') or aligned.get('language')!=source_aligned.get('language'): raise ValueError('derived language mismatch')
 mapped,changes,removed=map_edit(source_aligned['segments'],edl)
 if lineage.get('removed_segment_ids')!=removed: raise ValueError('derived removed IDs mismatch')
 prefix=source_ledger['corrections']+changes
 if ledger['corrections'][:len(prefix)]!=prefix: raise ValueError('derived correction prefix mismatch')
 if replay(source_raw,ledger)!=aligned['segments']: raise ValueError('derived final raw/correction concordance failed')
 # Later lexical corrections may refine surviving words but cannot change the verified edit timeline.
 if [(s['id'],s['start'],s['end']) for s in aligned['segments']]!=[(s['id'],s['start'],s['end']) for s in mapped]: raise ValueError('derived timeline differs from exact sample mapping')
 src_report=read(paths['source_master_report']); dst_report=read(paths['delivery_report'])
 if edl.get('source_sha256')!=sha(paths['source_wave']) or src_report['identity']['audio_sha256']!=sha(paths['source_wave']) or dst_report['identity']['audio_sha256']!=sha(paths['edited_wave']): raise ValueError('master/edit input hash mismatch')
 for report,audio_hash in [(src_report,old),(dst_report,new)]:
  if report['outputs']['delivery.mp3']['sha256']!=audio_hash or report['input']['sample_count']!=report['output']['sample_count'] or report['input']['sample_rate']!=report['output']['sample_rate']: raise ValueError('delivery changed sample timeline')
 observed=pcm_edit_check(paths['source_wave'],paths['edited_wave'],edl)
 with tempfile.TemporaryDirectory(prefix='delivery-count-') as tmp:
  old_meta=decoded(paths['source_delivery'],P(tmp)/'old.pcm'); new_meta=decoded(delivery_path,P(tmp)/'new.pcm')
 if any(old_meta[k]!=observed['source'][k] or new_meta[k]!=observed['edited'][k] for k in ('sample_rate','channels','sample_count')): raise ValueError('fresh delivery decoding differs from sample timeline')
 if abs(aligned.get('duration',-1)-new_meta['sample_count']/new_meta['sample_rate'])>1e-9: raise ValueError('derived duration mismatch')
 encoding={'source':verify_delivery_encoding(paths['source_wave'],paths['source_delivery'],src_report),'edited':verify_delivery_encoding(paths['edited_wave'],delivery_path,dst_report)}
 return {'delivery_reproduction':encoding,'valid':True,'source_audio_sha256':old,'audio_sha256':new,'removed_segment_ids':removed,'segment_count':len(aligned['segments']),'pcm_verification':observed,'new_asr_performed':False}

def produce(source_transcription,source_delivery,source_master_report,edl_path,source_wave,edited_wave,delivery,delivery_report,output):
 output=P(output).resolve(); root=output.parent; output.mkdir(exist_ok=False)
 source_transcription=P(source_transcription); files={'source_raw':source_transcription/'raw.json','source_raw_txt':source_transcription/'raw.txt','source_aligned':source_transcription/'aligned.json','source_ledger':source_transcription/'corrections.json','source_delivery':P(source_delivery),'source_master_report':P(source_master_report),'edl':P(edl_path),'source_wave':P(source_wave),'edited_wave':P(edited_wave),'delivery_report':P(delivery_report)}
 evidence={}
 for role,path in files.items():
  suffix=path.suffix; dest=path.resolve() if path.resolve().is_relative_to(root.resolve()) else output/(role+suffix)
  if dest!=path.resolve(): shutil.copy2(path,dest)
  evidence[role]={'path':str(dest.relative_to(root)),'sha256':sha(dest),'bytes':dest.stat().st_size}
 for name in ('raw.json','raw.txt','raw.srt','raw.vtt'): shutil.copy2(source_transcription/name,output/name)
 raw=read(source_transcription/'raw.json'); source_aligned=read(source_transcription/'aligned.json'); old_ledger=read(source_transcription/'corrections.json'); edl=read(edl_path)
 segments,changes,removed=map_edit(source_aligned['segments'],edl); new=sha(delivery)
 meta=read(delivery_report)['output']
 lineage={'schema_version':'2.0','kind':'sample_edit_derived_transcription','new_asr_performed':False,'source_audio_sha256':sha(source_delivery),'audio_sha256':new,'removed_segment_ids':removed,'evidence':evidence,'limitations':['Raw ASR belongs to the unedited source audio and remains unchanged.','Canonical timing is derived by exact sample edit mapping; ASR word timing remains estimated.','No acceptance of the failed new full-length ASR.']}
 aligned={'schema_version':'2.0','provenance_kind':'sample_edit_derived_transcription','source_audio_sha256':sha(source_delivery),'audio_sha256':new,'language':source_aligned['language'],'duration':meta['sample_count']/meta['sample_rate'],'segments':segments,'edit_lineage_path':str((output/'edit-lineage.json').relative_to(root))}
 ledger={'schema_version':'2.0','audio_sha256':new,'source_audio_sha256':sha(source_delivery),'raw_json_sha256':sha(output/'raw.json'),'corrections':old_ledger['corrections']+changes,'policy':'source corrections followed by independently recomputable sample edit deletions and shifts'}
 write(output/'edit-lineage.json',lineage); write(output/'aligned.json',aligned); write(output/'corrections.json',ledger)
 print(json.dumps({'status':'canonical_provisional_pending_pcm_verification','segments':len(segments),'aligned':str(output/'aligned.json')}),flush=True)
 result=verify(root,lineage,aligned,ledger,output/'raw.json',delivery)
 result.update(schema_version='2.0',stage='edit-derived-transcription',qc_scope='source correction concordance and exact retained PCM/sample mapping; no new ASR',outputs={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in output.iterdir() if p.is_file()}); write(output/'report.json',result)
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for key in ('source-transcription','source-delivery','source-master-report','edl','source-wave','edited-wave','delivery','delivery-report','output-dir'): ap.add_argument('--'+key,required=True,type=P)
 a=ap.parse_args(); r=produce(a.source_transcription,a.source_delivery,a.source_master_report,a.edl,a.source_wave,a.edited_wave,a.delivery,a.delivery_report,a.output_dir); print(json.dumps({'report':str(a.output_dir/'report.json'),'sha256':sha(a.output_dir/'report.json'),'segments':r['segment_count']}))
if __name__=='__main__': main()
