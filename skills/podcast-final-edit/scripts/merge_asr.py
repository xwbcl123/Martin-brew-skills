#!/usr/bin/env python3
"""Merge overlap-bounded ASR evidence into review words on a source sample clock.

Keeps request-local speaker IDs, protects chunk seams, and preserves raw events.
Does not certify accuracy or emit edit decisions.
"""
from __future__ import annotations
import argparse,decimal,difflib,hashlib,json,math,pathlib,re,wave
D=decimal.Decimal

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def normalized(text):return re.sub(r'[^\w\u4e00-\u9fff]','',text).lower()

def finite_number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def final_evidence(event,raw_events,expected_ms):
 payload=event.get('payload');duration=payload.get('audio_info',{}).get('duration') if isinstance(payload,dict) else None
 if event.get('error_code') or event.get('message_type')!=9 or not event.get('flags',0)&2 or not isinstance(payload,dict) or payload.get('code') not in (None,0,20000000):raise ValueError('invalid final provider status/termination')
 if not finite_number(duration) or abs(duration-expected_ms)>2:raise ValueError('invalid final provider duration')
 terminals=[row for row in raw_events if row.get('flags',0)&2]
 if len(terminals)!=1 or terminals[0]!=event:raise ValueError('final response does not match unique raw terminal event')
 result=payload.get('result',{});utterances=result.get('utterances',[])
 if not result.get('text') or not utterances or not all(u.get('definite') for u in utterances):raise ValueError('partial provider result')
 return result

def geometry(plan,source_total):
 records=plan['records'];total=plan['source_total_frames'];rate=plan['sample_rate_hz']
 if rate!=16000 or not records or source_total<1:raise ValueError('invalid analysis/source geometry')
 if abs(source_total-total*3)>2:raise ValueError('48k source/16k analysis length mismatch')
 cursor=0
 for r in records:
  if not 0<=r['start']<=r['core_start']<r['core_end']<=r['end']<=total or r['core_start']!=cursor:raise ValueError('core range gap/overlap or invalid context')
  cursor=r['core_end']
 if cursor!=total:raise ValueError('source core coverage incomplete')
 return records

def select_words(records,results,source_total,guard_seconds=1):
 if len(records)!=len(results):raise ValueError('missing provider result')
 guards=[{'start_sample':max(0,r['core_start']*3-round(guard_seconds*48000)),'end_sample':min(source_total,r['core_start']*3+round(guard_seconds*48000)),'reason':'request boundary; overlap reconciliation is estimated'} for r in records[1:]]
 rows=[];unlocated=[];all_by_request=[];corrections=[]
 for block,(spec,result) in enumerate(zip(records,results)):
  local=[]
  for ui,u in enumerate(result['utterances']):
   for wi,w in enumerate(u.get('words',[])):
    text=w['text']
    if not finite_number(w.get('start_time')) or not finite_number(w.get('end_time')):raise ValueError('invalid numeric word timestamp')
    start=D(str(w['start_time']));end=D(str(w['end_time']))
    if not start.is_finite() or not end.is_finite():raise ValueError('nonfinite word timestamp')
    identity={'request_index':block,'utterance_index':ui,'word_index':wi,'raw_word':w}
    if start<0 or end<0:
     unlocated.append(identity);continue
    if end<start or end>(D(spec['end']-spec['start'])/16)+2:raise ValueError('invalid word duration')
    ss=spec['start']*3+int((start*48).to_integral_value(rounding=decimal.ROUND_HALF_EVEN));ee=spec['start']*3+int((end*48).to_integral_value(rounding=decimal.ROUND_HALF_EVEN))
    mid=(D(spec['start'])+(start+end)*8)
    entry={**identity,'id':f'V{block:03d}-{ui:04d}-{wi:04d}','text':text,'start_sample':ss,'end_sample':ee,'speaker':'unknown','provider_speaker_scoped':f"request-{block}:"+str(u.get('additions',{}).get('speaker_id','unknown')),'accuracy':'asr_estimated'}
    local.append(entry)
    if D(spec['core_start'])<=mid<D(spec['core_end']) and text.strip():
     if ee>source_total:
      if block!=len(records)-1 or ee-source_total>96:raise ValueError('word exceeds source playback end')
      corrections.append({'word_id':entry['id'],'field':'end_sample','before':ee,'after':source_total,'reason':'terminal ASR quantization <=2ms; raw provider word unchanged'});entry['end_sample']=source_total
     if not 0<=ss<=entry['end_sample']<=source_total:
      unlocated.append({**identity,'reason':'estimated word start lies beyond actual source playback end'});continue
     entry['cut_protected']=ss==entry['end_sample'] or any(ss<g['end_sample'] and entry['end_sample']>g['start_sample'] for g in guards)
     rows.append(entry)
  all_by_request.append(local)
 rows.sort(key=lambda w:(w['start_sample'],w['end_sample'],w['id']))
 if not rows:raise ValueError('no source words selected')
 overlap_checks=[]
 for i,(left,right) in enumerate(zip(records,records[1:])):
  lo=max(left['start'],right['start'])*3;hi=min(left['end'],right['end'])*3
  l=''.join(w['text'] for w in all_by_request[i] if lo<=(w['start_sample']+w['end_sample'])/2<hi);r=''.join(w['text'] for w in all_by_request[i+1] if lo<=(w['start_sample']+w['end_sample'])/2<hi)
  ratio=difflib.SequenceMatcher(None,normalized(l),normalized(r),autojunk=False).ratio()
  overlap_checks.append({'left_request':i,'right_request':i+1,'range_samples':[lo,hi],'left_text':l,'right_text':r,'normalized_character_agreement':ratio,'agreement_is_accuracy':False,'seam_cut_protected':True})
 return {'words':rows,'unlocated_entries':unlocated,'chunk_seam_protected_ranges':guards,'overlap_checks':overlap_checks,'corrections':corrections}

def merge(plan_path,output,source_total):
 plan=json.loads(plan_path.read_text());records=geometry(plan,source_total);results=[];proof=[];source=None
 for r in records:
  directory=(plan_path.parent/r['directory']).resolve()
  if not directory.is_relative_to(plan_path.parent.resolve()):raise ValueError('request directory escapes plan')
  report=directory/'report.json';meta=json.loads(report.read_text());candidate=pathlib.Path(meta['source']['path'])
  if source is None:source=candidate
  if candidate!=source or meta['status']!='recognized' or meta['source']['sha256']!=plan['source_sha256'] or meta['source']['start_sample']!=r['start'] or meta['source']['end_sample']!=r['end']:raise ValueError('request identity mismatch')
  if meta.get('handshake')!='accepted' or not meta.get('terminal_response_received') or meta.get('audio_frames_sent')!=r['end']-r['start']:raise ValueError('incomplete provider execution')
  with wave.open(str(source)) as w:
   w.setpos(r['start']);pcm=w.readframes(r['end']-r['start'])
  if len(pcm)!=(r['end']-r['start'])*2 or hashlib.sha256(pcm).hexdigest()!=meta['source'].get('selected_pcm_sha256'):raise ValueError('selected PCM does not match live source range')
  if not meta.get('output_hashes') or 'final.json' not in meta['output_hashes'] or 'responses.jsonl' not in meta['output_hashes']:raise ValueError('request outputs missing')
  for name,digest in meta['output_hashes'].items():
   path=(directory/name).resolve()
   if not path.is_relative_to(directory) or sha(path)!=digest:raise ValueError('ASR output hash mismatch')
  raw_events=[]
  with (directory/'responses.jsonl').open() as f:
   for line in f:
    row=json.loads(line);payload=row.get('payload')
    if row.get('error_code') or isinstance(payload,dict) and payload.get('code') not in (None,0,20000000):raise ValueError('provider error exists in raw response stream')
    raw_events.append(row)
  event=json.loads((directory/'final.json').read_text())
  result=final_evidence(event,raw_events,(r['end']-r['start'])/16)
  results.append(result);proof.append({'directory':r['directory'],'report_sha256':sha(report),'final_sha256':sha(directory/'final.json')})
 if sha(source)!=plan['source_sha256']:raise ValueError('analysis audio changed')
 with wave.open(str(source)) as w:
  if w.getnframes()!=plan['source_total_frames'] or w.getframerate()!=16000 or w.getnchannels()!=1 or w.getsampwidth()!=2:raise ValueError('analysis source geometry changed')
 merged=select_words(records,results,source_total)
 output.mkdir(parents=True,exist_ok=False)
 words={'schema_version':'1.0','stage':'full_raw_cloud_asr_review_words','source_analysis_sha256':plan['source_sha256'],'source_sample_rate':48000,'source_total_samples':source_total,'analysis_total_samples':plan['source_total_frames'],'analysis_resampling_tail_difference_source_samples':source_total-plan['source_total_frames']*3,'source_time_accuracy':'asr_estimated','clock_mapping_word_boundaries_verified':False,'automatic_deletion_approved':False,**merged}
 (output/'words.json').write_text(json.dumps(words,ensure_ascii=False,indent=2)+'\n')
 (output/'raw-selected-text.txt').write_text(''.join(w['text'] for w in merged['words'])+'\n')
 report={'stage':'merge_payg_overlap_evidence','plan_sha256':sha(plan_path),'tool_sha256':sha(pathlib.Path(__file__)),'request_proof':proof,'request_count':len(records),'selected_word_count':len(merged['words']),'filler_counts':{x:sum(w['text']==x for w in merged['words']) for x in ['呃','嗯','uh','um']},'substantive_unlocated_count':sum(bool(w['raw_word']['text'].strip()) for w in merged['unlocated_entries']),'low_overlap_agreement_count':sum(r['normalized_character_agreement']<.9 for r in merged['overlap_checks']),'verbatim_completeness_verified':False,'semantic_listening_approved':False,'outputs':{name:sha(output/name) for name in ['words.json','raw-selected-text.txt']}}
 (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--source-total-samples',type=int,required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);a=p.parse_args();r=merge(a.plan,a.output_dir,a.source_total_samples);print(json.dumps({k:r[k] for k in ['request_count','selected_word_count','filler_counts','substantive_unlocated_count','low_overlap_agreement_count']},ensure_ascii=False))
if __name__=='__main__':main()
