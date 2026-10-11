#!/usr/bin/env python3
"""Thin v2 stage planner/runner. Plan is read-only; prepared inputs stay explicit."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, tempfile
P=pathlib.Path
SKILLS=P(__file__).resolve().parents[3]
CONTRACT=SKILLS/'podcast-release-package/references/v2/stage-contracts.json'
SOURCES=('raw_recording','imported_finished','generated_finished')
REQUIRED={'intake':['audio'],'inspect_finished':['audio'],'final_edit':['edl'],'mastering':['audio'],'delivery':['audio'],'transcription':['audio'],'enrichment':['transcript','content'],'preview':['content'],'package':['package'],'publish':['package','authorization']}

def sha(path):
    h=hashlib.sha256()
    with P(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def canonical(data): return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def graph(source_kind):
    if source_kind not in SOURCES: raise ValueError('unsupported source_kind')
    data=json.loads(CONTRACT.read_text()); dag=data['stages']
    if source_kind=='raw_recording': dag['delivery']=[data['raw_delivery_parent']]; dag.pop('inspect_finished')
    else:
        for stage in ('intake','final_edit','mastering'): dag.pop(stage)
    return dag

def closure(dag,target):
    if target not in dag: raise ValueError('stage not applicable to source_kind: '+target)
    result=[]; visiting=set()
    def visit(s):
        if s in visiting: raise ValueError('cyclic stage contract')
        if s in result: return
        visiting.add(s)
        for parent in dag[s]: visit(parent)
        visiting.remove(s); result.append(s)
    visit(target); return result

def changed_artifacts(previous,current):
    """Values are actual paths; compare observed bytes, not timestamps."""
    return {role for role in set(previous)|set(current) if role not in previous or role not in current or sha(previous[role])!=sha(current[role])}

def invalidate(changed,source_kind='imported_finished'):
    dag=graph(source_kind)
    origins={'audio':'delivery','delivery_audio':'delivery','edl':'final_edit','transcript':'transcription','content':'enrichment','show_notes':'enrichment','chapters':'enrichment','cover':'enrichment','preview':'preview','package':'package','authorization':'publish'}
    affected=set()
    for role in changed:
        origin=origins.get(role)
        if origin in dag: affected.add(origin)
    while True:
        expanded=affected|{stage for stage,parents in dag.items() if any(p in affected for p in parents)}
        if expanded==affected: return [s for s in dag if s in affected]
        affected=expanded

def module(skill,script): return str(SKILLS/skill/'scripts'/script)

def plan(request):
    if request.get('contract_version')!='2.0': raise ValueError('contract_version must be 2.0')
    dag=graph(request['source_kind']); stages=closure(dag,request['target_stage']); entry=request['entry_stage']
    if entry not in stages: raise ValueError('entry_stage must be an applicable ancestor of target_stage')
    stages=stages[stages.index(entry):]
    root=P(request['package_root']).absolute(); inputs={k:str(P(v).absolute()) for k,v in request.get('inputs',{}).items()}
    for key,path in inputs.items():
        if key=='package':
            if not P(path).is_dir(): raise ValueError('package directory missing')
        elif not P(path).is_file(): raise ValueError('input file missing: '+key)
    if not root.is_dir(): raise ValueError('package_root directory missing')
    options=request.get('options',{}); steps=[]; available=dict(inputs)
    # All relevant explicit input hashes bind the run directory; no dates or review time.
    hashes={key:sha(value) if P(value).is_file() else sha(P(value)/'episode.json') for key,value in inputs.items()}
    if 'content' in inputs:
        content=json.loads(P(inputs['content']).read_text())
        paths=[content[k] for k in ('audio_path','cover_path') if k in content]+[a['path'] for k in ('assets','audit_links') for a in content.get(k,[])]
        hashes['content']=canonical({'content':hashes['content'],'assets':{path:sha(root/path) for path in paths}})
    identity={'request':request,'inputs':hashes,'contract_sha256':sha(CONTRACT),'implementation':sha(P(__file__))}
    run_key=canonical(identity); work=root/'workflow'/'runs'/run_key[:20]; tokens=dict(hashes)
    for stage in stages:
        missing=[k for k in REQUIRED[stage] if k not in available]
        if missing: raise ValueError(stage+' missing required_inputs: '+','.join(missing))
        relevant_options=options if stage in ('mastering','delivery','transcription') else {}
        stage_key=canonical({'stage':stage,'source_kind':request['source_kind'],'inputs':{k:tokens[k] for k in REQUIRED[stage]+(['model'] if stage=='transcription' and 'model' in tokens else [])},'options':relevant_options,'contract_sha256':identity['contract_sha256'],'orchestrator':identity['implementation']})
        out=root/'workflow'/'stages'/stage/stage_key[:20]; command=None
        if stage in ('intake','inspect_finished'):
            # probe only happens in build, never during planning.
            command=['ffprobe','-v','error','-select_streams','a:0','-show_streams','-show_format','-of','json',available['audio']]
        elif stage=='final_edit':
            command=[sys.executable,module('podcast-final-edit','final_edit.py'),'render-review','--edl',available['edl'],'--output',str(out/'review.wav'),'--report',str(out/'render-report.json')]; available['audio']=str(out/'review.wav'); tokens['audio']=stage_key
        elif stage in ('mastering','delivery'):
            mode=options.get(stage+'_mode','loudness_only' if stage=='mastering' else 'encode_only')
            if stage=='delivery' and request['source_kind']=='raw_recording' and 'mastering' in stages:
                # Mastering already produces compliant delivery MP3; avoid duplicate encoding.
                command=None
            else:
                command=[sys.executable,module('podcast-mastering','mastering.py'),'--input',available['audio'],'--output-dir',str(out/'media'),'--mode',mode]
                if 'peak_headroom' in options: command+=['--peak-headroom',str(options['peak_headroom'])]
                available['audio']=str(out/'media/delivery.mp3'); tokens['audio']=stage_key
        elif stage=='transcription':
            command=[sys.executable,module('podcast-transcription','transcription.py'),'--delivery',available['audio'],'--output-dir',str(out/'asr')]
            if 'model' in available: command+=['--model',available['model']]
            if 'threads' in options: command+=['--threads',str(options['threads'])]
            available['transcript']=str(out/'asr/aligned.json'); tokens['transcript']=stage_key
        elif stage=='enrichment':
            command=[sys.executable,module('podcast-enrichment','enrich.py'),'validate','--content',available['content'],'--package-root',str(root)]
        elif stage=='preview':
            command=[sys.executable,module('podcast-enrichment','enrich.py'),'build','--content',available['content'],'--package-root',str(root),'--output',str(out/'preview/index.html')]
        elif stage=='package':
            command=[sys.executable,module('podcast-release-package','v2/package.py'),'seal','--package',available['package']]
        elif stage=='publish':
            command=[sys.executable,module('podcast-transistor-publish','publish.py'),'--package',available['package'],'--authorization',available['authorization'],'--state-dir',str(root/'publish-state'),'--mode','publish']
            if 'artwork_verification' in available: command+=['--artwork-verification',available['artwork_verification']]
        steps.append({'stage':stage,'command':command,'output_dir':str(out),'stage_key':stage_key,'external_mutation':stage=='publish','required_inputs':REQUIRED[stage]})
    return {'contract_version':'2.0','run_key':run_key,'identity':identity,'stages':stages,'steps':steps,'work_dir':str(work),'outputs':available,'execution_status':'planned','media_executed':False}

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    with os.fdopen(fd,'w') as f: json.dump(value,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def build(request):
    result=plan(request); work=P(result['work_dir']); work.mkdir(parents=True,exist_ok=True)
    lock=P(request['package_root']).absolute()/'workflow'/'.build.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.write(fd,str(os.getpid()).encode()); os.close(fd); atomic(work/'plan.json',result)
        for step in result['steps']:
            out=P(step['output_dir']); out.mkdir(parents=True,exist_ok=True); report_path=out/'stage-report.json'
            # Never skip publishing on local status: controller reconciles remote state.
            if report_path.exists() and step['stage'] in ('preview',):
                old=json.loads(report_path.read_text())
                if old['status']=='succeeded' and old.get('artifacts') and all(P(p).is_file() and sha(p)==h for p,h in old['artifacts'].items()): continue
                raise ValueError('stage checkpoint changed or incomplete; use new request/output revision')
            report={'stage':step['stage'],'command':step['command'],'run_key':result['run_key'],'stage_key':step['stage_key'],'status':'running'}; atomic(report_path,report)
            if step['command']:
                process=subprocess.run(step['command'],capture_output=True,text=True)
                (out/'stdout.log').write_text(process.stdout); (out/'stderr.log').write_text(process.stderr)
                report['exit_code']=process.returncode
                # A successful compute invocation may truthfully report failed QC.
                module_report=out/('asr/report.json' if step['stage']=='transcription' else 'media/report.json')
                qc=json.loads(module_report.read_text()).get('qc_status') if module_report.exists() else None
                report['status']='succeeded' if process.returncode==0 and qc!='fail' else 'failed'
            else: report['status']='succeeded'; (out/'alias.json').write_text(json.dumps({'audio':result['outputs'].get('audio')}))
            report['artifacts']={str(p):sha(p) for p in out.rglob('*') if p.is_file() and p!=report_path}; atomic(report_path,report)
            if report['status']!='succeeded': raise ValueError('stage failed: '+step['stage']+'; '+str(report_path))
        result['execution_status']='succeeded'; result['media_executed']=any(s in result['stages'] for s in ('mastering','delivery','transcription','final_edit')); atomic(work/'result.json',result); return result
    finally: lock.unlink(missing_ok=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--request',required=True,type=P); ap.add_argument('--mode',choices=['plan','build'],default='plan'); a=ap.parse_args()
    try: print(json.dumps((plan if a.mode=='plan' else build)(json.loads(a.request.read_text())),ensure_ascii=False,indent=2))
    except (ValueError,KeyError,OSError) as e: print(json.dumps({'status':'failed','error':str(e)}),file=sys.stderr); return 2
    return 0
if __name__=='__main__': sys.exit(main())
