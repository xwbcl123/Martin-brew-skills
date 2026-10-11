#!/usr/bin/env python3
"""Conservative review candidates and unchanged sample EDL renderer adapter."""
import argparse,hashlib,json,math,pathlib,re,subprocess,sys
P=pathlib.Path
ROOT=P(__file__).resolve().parents[2]
POLICY={'version':'candidate-policy-2.0','filler_tokens':['um','uh','erm','嗯','呃'],'control_phrases':['重新录','这段删掉','重来一遍','start recording','cut that'],'silence_min_seconds':1.5,'automatic_deletion':False,'preserve':['emotion','breath','semantic filler','speaker hesitation','context']}

def candidates(transcript,silences=None):
    rows=[]
    for s in transcript['segments']:
        start,end=float(s['start']),float(s['end']); text=s['text'].strip()
        if not math.isfinite(start+end) or start<0 or end<start: raise ValueError('invalid transcript time')
        normalized=text.lower().strip(' .,!?:;。，！？、')
        category='filler' if normalized in POLICY['filler_tokens'] else 'control' if any(p in normalized for p in POLICY['control_phrases']) else None
        if category: rows.append({'id':'segment-'+str(s['id']),'start':start,'end':end,'text':text,'category':category,'decision':'keep_pending_review','reason':'lexical evidence only; surrounding semantics and emotion not evaluated','context_required':True})
    for i,s in enumerate(silences or []):
        start,end=float(s['start']),float(s['end'])
        if not math.isfinite(start+end) or start<0 or end<start: raise ValueError('invalid silence time')
        if end-start>=POLICY['silence_min_seconds']: rows.append({'id':'silence-'+str(i),'start':start,'end':end,'category':'silence','decision':'keep_pending_review','reason':'may contain breath or meaningful pause','context_required':True})
    return {'schema_version':'2.0','stage':'rough_cut_candidates','audio_sha256':transcript.get('audio_sha256'),'policy':POLICY,'candidates':rows,'publish_authorized':False,'review_required':True,'automatic_deletion':False}

def detect_silences(audio):
    result=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(audio),'-af','silencedetect=noise=-40dB:d='+str(POLICY['silence_min_seconds']),'-f','null','-'],capture_output=True,text=True,check=True)
    intervals=[]; start=None
    for line in result.stderr.splitlines():
        found=re.search(r'silence_start: ([0-9.]+)',line)
        if found: start=float(found.group(1))
        found=re.search(r'silence_end: ([0-9.]+)',line)
        if found and start is not None:
            intervals.append({'start':start,'end':float(found.group(1))}); start=None
    return intervals

def word_candidates(words):
    """Expose fillers inside utterances without turning ASR estimates into cuts."""
    rate=words['source_sample_rate'];total=words['source_total_samples'];items=words['words'];rows=[]
    verified=words.get('clock_mapping_word_boundaries_verified',False)
    if type(verified)!=bool:raise ValueError('clock mapping verification must be boolean')
    if type(rate)!=int or rate!=48000 or type(total)!=int or total<=0:raise ValueError('invalid source sample clock')
    ids=set();last=-1
    for i,w in enumerate(items):
        a,b=w['start_sample'],w['end_sample']
        if type(w.get('cut_protected',False))!=bool:raise ValueError('word protection must be boolean')
        if type(a)!=int or type(b)!=int or not 0<=a<=b<=total or a<last or w['id'] in ids:raise ValueError('invalid/unsorted/duplicate word evidence')
        ids.add(w['id']);last=a
    for i,w in enumerate(items):
        text=w['text'].strip();normalized=text.lower().strip(' .,!?:;。，！？、')
        if normalized not in POLICY['filler_tokens']:continue
        context=items[max(0,i-8):min(len(items),i+9)]
        reasons=['ASR coordinates are estimates; acoustic boundaries and contextual listening required','semantic/emotional/affirmative use unresolved']
        if w.get('cut_protected') or w['start_sample']==w['end_sample']:reasons.append('chunk seam or unusable interval protected')
        if any(v['id']!=w['id'] and v['start_sample']<w['end_sample'] and v['end_sample']>w['start_sample'] for v in context):reasons.append('overlapping speech evidence; speaker separation unverified')
        rows.append({'id':'word-'+w['id'],'word_evidence_id':w['id'],'start_sample':w['start_sample'],'end_sample':w['end_sample'],'text':w['text'],'category':'filler','speaker':w.get('speaker','unknown'),'provider_speaker_scoped':w.get('provider_speaker_scoped'),'decision':'keep_pending_review','cut_protected':bool(w.get('cut_protected')) or w['start_sample']==w['end_sample'],'review_reasons':reasons,'context_word_ids':[v['id'] for v in context],'context_text':''.join(v['text'] for v in context),'proposed_cut_interval':None})
    return {'schema_version':'3.0','stage':'verbatim_word_review_candidates','source_analysis_sha256':words['source_analysis_sha256'],'source_sample_rate':rate,'source_total_samples':total,'source_clock_mapping_verified':verified,'policy':POLICY,'candidates':rows,'substantive_unlocated_entries':[w for w in words.get('unlocated_entries',[]) if w['raw_word']['text'].strip()],'review_required':True,'automatic_deletion':False,'publish_authorized':False}

def word_candidate_snapshot(path):
    snapshot=path.read_bytes();data=word_candidates(json.loads(snapshot));data['inputs']={'words_sha256':hashlib.sha256(snapshot).hexdigest()};return data

def render(edl,output,report):
    # The v1 renderer validates its own exact sample EDL schema/source hash;
    # no approval is synthesized and its output remains review-only.
    return subprocess.run([sys.executable,str(ROOT/'podcast-production-workflow/scripts/render_sample_edl.py'),'--edl',str(edl),'--output',str(output),'--report',str(report)],check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='command',required=True)
    c=sub.add_parser('candidates'); c.add_argument('--transcript',type=P,required=True); c.add_argument('--silences',type=P); c.add_argument('--audio',type=P,help='Observe silence from this same-timeline audio'); c.add_argument('--output',type=P,required=True)
    wc=sub.add_parser('word-candidates');wc.add_argument('--words',type=P,required=True);wc.add_argument('--output',type=P,required=True)
    r=sub.add_parser('render-review'); r.add_argument('--edl',type=P,required=True); r.add_argument('--output',type=P,required=True); r.add_argument('--report',type=P,required=True)
    a=ap.parse_args()
    if a.command=='render-review': render(a.edl,a.output,a.report); return
    if a.command=='word-candidates':
        data=word_candidate_snapshot(a.words)
        with a.output.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
        print(json.dumps({'output':str(a.output),'candidate_count':len(data['candidates']),'review_required':True}));return
    transcript=json.loads(a.transcript.read_text())
    if a.audio and a.silences: ap.error('choose --audio or --silences')
    if a.audio and hashlib.sha256(a.audio.read_bytes()).hexdigest()!=transcript.get('audio_sha256'): raise ValueError('audio hash does not match aligned transcript')
    data=candidates(transcript,detect_silences(a.audio) if a.audio else json.loads(a.silences.read_text()) if a.silences else None)
    data['inputs']={'transcript_sha256':hashlib.sha256(a.transcript.read_bytes()).hexdigest(),'silences_sha256':hashlib.sha256(a.silences.read_bytes()).hexdigest() if a.silences else None}
    with a.output.open('x') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps({'output':str(a.output),'candidate_count':len(data['candidates']),'review_required':True}))
if __name__=='__main__': main()
