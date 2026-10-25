#!/usr/bin/env python3
"""Transcribe final delivery locally with detected-language immutable raw evidence."""
import argparse, importlib.util, json, math, os, pathlib, re, shutil, subprocess, tempfile
P=pathlib.Path
ROOT=P(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('delivery_compute',ROOT/'podcast-mastering/scripts/mastering.py'); media=importlib.util.module_from_spec(spec); spec.loader.exec_module(media)

# BEGIN podcast-config (byte-identical in every consumer; guarded by podcast-release-package/scripts/test_config_copies.py)
def _podcast_cfg(_cache={}):
    """Personal defaults from $PODCAST_CONFIG or ~/.config/podcast-skills/config.json. Read lazily, once; never grants approval/authorization."""
    import json, os, re
    from pathlib import Path
    keys = {'workspace', 'whisper_cli', 'whisper_model', 'transistor_cli', 'transistor_cli_repo',
            'language', 'approver', 'artwork_registry', 'planning_profiles_dir'}
    plain = {'language', 'approver'}
    explicit = os.environ.get('PODCAST_CONFIG')
    if explicit is not None:
        if not explicit.strip() or not Path(explicit).expanduser().is_absolute():
            raise SystemExit('PODCAST_CONFIG must be a non-empty absolute path (unset it to use ~/.config/podcast-skills/config.json)')
        path = Path(explicit).expanduser()
    else:
        path = Path.home() / '.config' / 'podcast-skills' / 'config.json'
    if str(path) in _cache:
        return _cache[str(path)]
    if explicit is not None and not path.is_file():
        raise SystemExit(f'PODCAST_CONFIG points to a missing file: {path}')
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise SystemExit(f'invalid JSON in {path}: {exc}')
    if not isinstance(data, dict):
        raise SystemExit(f'{path}: top level must be an object')
    extra = sorted(set(data) - keys - {'shows'})
    if extra:
        raise SystemExit(f'{path}: unknown keys {extra}')
    for key in keys & set(data):
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f'{path}: {key} must be a non-empty string')
        if key not in plain and not Path(value).expanduser().is_absolute():
            raise SystemExit(f'{path}: {key} must be an absolute path')
    shows = data.setdefault('shows', {})
    if not isinstance(shows, dict):
        raise SystemExit(f'{path}: shows must be an object keyed by show id')
    for sid, entry in shows.items():
        if not re.fullmatch(r'[0-9]+', str(sid)) or not isinstance(entry, dict) or set(entry) - {'author', 'brand_name', 'brand_tagline'}:
            raise SystemExit(f'{path}: shows[{sid!r}] must be an object with only author/brand_name/brand_tagline')
        for field in ('author', 'brand_name'):
            if field in entry and (not isinstance(entry[field], str) or not entry[field].strip()):
                raise SystemExit(f'{path}: shows[{sid!r}].{field} must be a non-empty string')
        if 'brand_tagline' in entry and not isinstance(entry['brand_tagline'], str):
            raise SystemExit(f'{path}: shows[{sid!r}].brand_tagline must be a string')
    _cache[str(path)] = data
    return data


def _podcast_pick(cli, env_name, key):
    """Provided CLI value > provided environment variable > config file > None. A provided-but-blank value is an error, never "unset"."""
    import os
    for source, value in (('command line', cli), (f'${env_name}', os.environ.get(env_name) if env_name else None)):
        if value is not None:
            if not str(value).strip():
                raise SystemExit(f'{key}: empty value from the {source}; omit it to use the default')
            return value
    return _podcast_cfg().get(key)


def _podcast_tool(cli, env_name, key, command):
    """A provided tool path must be an absolute executable file and is used as-is (never re-resolved through PATH); `command` is only looked up when nothing was provided."""
    import os, shutil
    value = _podcast_pick(cli, env_name, key)
    if value is not None:
        value = os.path.expanduser(str(value))
        if not os.path.isabs(value):
            raise SystemExit(f'{key}: {value} must be an absolute path (relative values are never searched on PATH)')
        if not (os.path.isfile(value) and os.access(value, os.X_OK)):
            raise SystemExit(f'{key}: {value} is not an executable file (fix --{key.replace("_", "-")}, ${env_name or "PODCAST_CONFIG"} or the podcast-skills config)')
        return value
    found = shutil.which(command)
    if not found:
        raise SystemExit(f'{command} not found: pass --{key.replace("_", "-")}, set ${env_name or "PODCAST_CONFIG"} or add "{key}" to ~/.config/podcast-skills/config.json')
    return os.path.abspath(found)


def _podcast_model(cli):
    """Whisper model: CLI > $WHISPER_MODEL > config whisper_model > <workspace>/models/ggml-large-v3-q5_0.bin."""
    import os
    value = _podcast_pick(cli, 'WHISPER_MODEL', 'whisper_model')
    if value is None:
        workspace = _podcast_pick(None, 'PODCAST_WORKSPACE', 'workspace')
        if workspace is None:
            raise SystemExit('no Whisper model: pass --model, set $WHISPER_MODEL, or add whisper_model/workspace to ~/.config/podcast-skills/config.json')
        workspace = os.path.expanduser(str(workspace))
        if not os.path.isabs(workspace):
            raise SystemExit(f'workspace: {workspace} must be an absolute path')
        value = os.path.join(workspace, 'models', 'ggml-large-v3-q5_0.bin')
    value = os.path.expanduser(str(value))
    if not os.path.isabs(value):
        raise SystemExit(f'whisper_model: {value} must be an absolute path')
    if not os.path.isfile(value):
        raise SystemExit(f'Whisper model does not exist: {value}')
    return value
# END podcast-config

def align(data,duration,corrections=None,timing_overrides=None):
    segments=[]; previous=0.0
    raw_segments=data.get("transcription",[])
    overrides={(item["segment_id"],item["field"]):item for item in (timing_overrides or [])}
    for i,s in enumerate(raw_segments):
        start=float(s['offsets']['from'])/1000; end=float(s['offsets']['to'])/1000
        for field in ('start','end'):
            item=overrides.get((i,field))
            if item:
                before=start if field=='start' else end
                if before!=item['before'] or corrections is None: raise ValueError('timing correction before mismatch or ledger missing')
                if field=='start': start=item['after']
                else: end=item['after']
                corrections.append({**item,'raw_preserved':True})
        if not math.isfinite(start+end) or start<previous or end<start or start>=duration: raise ValueError('ASR segment outside final delivery timeline')
        if end==start:
            text=s['text'].strip(); match=None
            for j in (i-1,i+1):
                if 0<=j<len(raw_segments):
                    neighbor=raw_segments[j]; ns=float(neighbor['offsets']['from'])/1000; ne=float(neighbor['offsets']['to'])/1000
                    if text and neighbor['text'].strip()==text and math.isfinite(ns+ne) and ns<ne and (ne==start if j<i else ns==start): match=j; break
            if match is None or corrections is None: raise ValueError('zero-duration ASR segment requires an adjacent exact duplicate and correction ledger')
            corrections.append({'segment_id':i,'field':'text','before':text,'after':'','reason':'repeated zero-span ASR artifact; exact text survives in immediate positive-duration neighbor','duplicate_of_segment_id':match,'start':start,'end':end,'raw_preserved':True})
            continue
        if end>duration:
            if i!=len(raw_segments)-1 or end-duration>0.250: raise ValueError('nonterminal or excessive ASR end overflow')
            if corrections is not None: corrections.append({'segment_id':i,'field':'end','before':end,'after':duration,'reason':'terminal ASR timestamp quantization clipped to final decoded duration','delta_seconds':duration-end,'raw_preserved':True})
        text=s['text'].strip()
        if not text: continue
        segments.append({'id':i,'start':start,'end':min(end,duration),'text':text,'speaker':'unknown'}); previous=end
    if not segments: raise ValueError('ASR has no nonempty segments')
    return segments

def load_timing_corrections(path,raw,audio_sha256,raw_sha256):
    if not path: return []
    data=json.loads(P(path).read_text())
    if data.get('audio_sha256')!=audio_sha256 or data.get('raw_json_sha256')!=raw_sha256: raise ValueError('timing correction audio/raw binding mismatch')
    if data.get('reviewed_by_kind') not in ('agent_delegated','human') or not data.get('source_ref'): raise ValueError('timing correction requires identified review source')
    seen=set(); rows=data.get('corrections')
    if not isinstance(rows,list) or not rows: raise ValueError('timing corrections must be a nonempty list')
    for item in rows:
        key=(item.get('segment_id'),item.get('field'))
        if type(key[0]) is not int or not 0<=key[0]<len(raw['transcription']) or key[1] not in ('start','end') or key in seen: raise ValueError('invalid/duplicate timing correction target')
        seen.add(key)
        if any(isinstance(item.get(k),bool) or not isinstance(item.get(k),(int,float)) or not math.isfinite(item[k]) for k in ('before','after')): raise ValueError('timing correction must be finite numeric seconds')
        if not item.get('reason') or item.get('accuracy') not in ('asr_estimated','manual_estimated','sample_verified'): raise ValueError('timing correction must disclose reason and accuracy')
        if not isinstance(item.get('evidence'),list) or not item['evidence']: raise ValueError('timing correction needs hashed evidence')
        for evidence in item['evidence']:
            ep=P(evidence['path'])
            if not ep.is_absolute() or ep.is_symlink() or media.sha256(ep)!=evidence['sha256']: raise ValueError('timing evidence missing/changed')
    return [{**row,'reviewed_by_kind':data['reviewed_by_kind'],'source_ref':data['source_ref']} for row in rows]

def context_option(argv):
    """Read an explicitly recorded text-context limit without accepting duplicates."""
    found=[]
    for i,arg in enumerate(argv):
        if arg in ('--max-context','-mc'):
            if i+1>=len(argv) or not re.fullmatch(r'\d+',argv[i+1]): raise ValueError('invalid recorded max-context option')
            found.append(int(argv[i+1]))
    if len(found)>1: raise ValueError('duplicate recorded max-context option')
    return found[0] if found else None

def transcription_cache(output,identity):
    """Verify this stage's immutable artifacts independently of mastering QC."""
    report_path=output/'report.json'
    if (output/'report.sha256').read_text().strip()!=media.sha256(report_path): raise ValueError('transcription cache report integrity mismatch')
    report=json.loads(report_path.read_text())
    required={'analysis.wav','raw.txt','raw.json','raw.srt','raw.vtt','language-detection.log','asr.log','aligned.json','corrections.json'}
    if report.get('recovery'):
        required.add('recovery-evidence.json')
        if report['recovery']['evidence_kind']=='execution_checkpoint':required.add('execution-checkpoint.json')
    else:required.add('execution-checkpoint.json')
    if identity['timing_corrections_sha256']:required.add('timing-corrections-input.json')
    if report['identity']!=identity or set(report['outputs'])!=required: raise ValueError('immutable transcription output collision')
    for name,item in report['outputs'].items():
        if P(name).name!=name or (output/name).is_symlink() or media.artifact(output/name)!=item: raise ValueError('transcription cache artifact changed: '+name)
    if context_option(report['argv'])!=identity['max_context_tokens']:raise ValueError('transcription cache text-context mismatch')
    if report['run_key']!=media.digest(identity):raise ValueError('transcription cache run-key mismatch')
    if 'execution-checkpoint.json' in required:
        checkpoint=json.loads((output/'execution-checkpoint.json').read_text())
        for key in ('delivery_sha256','model_sha256','tool_sha256','ffmpeg','threads','analysis_format','language','max_context_tokens'):
            if checkpoint['identity'].get(key)!=identity.get(key):raise ValueError('transcription cache checkpoint identity mismatch: '+key)
        if checkpoint['argv']!=report['argv'] or context_option(checkpoint['argv'])!=identity['max_context_tokens']:raise ValueError('transcription cache checkpoint argv mismatch')
        if checkpoint['analysis_sha256']!=media.sha256(output/'analysis.wav'):raise ValueError('transcription cache checkpoint analysis mismatch')
    if report.get('recovery'):
        evidence=json.loads((output/'recovery-evidence.json').read_text())
        if media.sha256(output/'recovery-evidence.json')!=report['recovery']['evidence_sha256'] or evidence['prior_argv']!=report['argv']:raise ValueError('transcription cache recovery evidence mismatch')
        for key in ('delivery_sha256','model_sha256','tool_sha256'):
            if evidence.get(key)!=identity[key]:raise ValueError('transcription cache recovery identity mismatch: '+key)
        for name in ('analysis.wav','raw.txt','raw.json','raw.srt','raw.vtt','language-detection.log','asr.log'):
            if evidence['artifacts'].get(name)!=media.sha256(output/name):raise ValueError('transcription cache recovered artifact mismatch: '+name)
        if evidence['evidence_kind']=='execution_checkpoint' and evidence['checkpoint_sha256']!=media.sha256(output/'execution-checkpoint.json'):raise ValueError('transcription cache recovery checkpoint mismatch')
    return report

def language_from_detection(log):
    """Use the installed CLI's model capability report, never a filename guess."""
    english_only = re.search(r'^main: WARNING: model is not multilingual, ignoring language and translation options\s*$', log, re.M)
    if english_only:
        return 'en', 'english_only_model_reported_by_cli'
    match = re.search(r'auto-detected language:\s*([a-z]{2,3})(?:\s|\()', log, re.I)
    if not match:
        raise ValueError('local language detection failed; do not assume a language')
    return match.group(1).lower(), 'automatic_detection'

def transcribe(delivery,output,model,whisper=None,threads=8,resume_partial=None,resume_evidence=None,timing_corrections=None,max_context_tokens=None):
    delivery=P(delivery).resolve(); output=P(output).resolve(); model=P(model).resolve(); whisper=P(whisper or _podcast_tool(None,'WHISPER_CLI','whisper_cli','whisper-cli')).resolve()
    if threads<1: raise ValueError('threads must be positive')
    if max_context_tokens is not None and (type(max_context_tokens) is not int or max_context_tokens<0): raise ValueError('max-context-tokens must be a nonnegative integer or omitted')
    base_identity={'stage':'transcription-v2','implementation':media.sha256(P(__file__)),'media_implementation':media.sha256(P(media.__file__)),'delivery_sha256':media.sha256(delivery),'model_sha256':media.sha256(model),'tool_sha256':media.sha256(whisper),'ffmpeg':media.run(['ffmpeg','-version']).stdout,'threads':threads,'analysis_format':'pcm_s16le/16000/mono','outputs':['txt','json','srt','vtt']}
    base_identity['timing_corrections_sha256']=media.sha256(P(timing_corrections)) if timing_corrections else None
    base_identity['max_context_tokens']=max_context_tokens
    if output.exists():
        if timing_corrections: load_timing_corrections(timing_corrections,json.loads((output/'raw.json').read_text()),base_identity['delivery_sha256'],media.sha256(output/'raw.json'))
        old=json.loads((output/'report.json').read_text()); identity={**base_identity,'language':old['language']}
        cached=transcription_cache(output,identity)
        if cached: return cached
    output.parent.mkdir(parents=True,exist_ok=True); tmp=P(tempfile.mkdtemp(prefix='.'+output.name+'-',dir=output.parent))
    recovery=None
    if resume_partial:
        partial=P(resume_partial).resolve()
        if not resume_evidence: raise ValueError('resume requires explicit recorded evidence')
        evidence=json.loads(P(resume_evidence).read_text())
        if not evidence.get('source_ref') or not evidence.get('prior_argv') or evidence.get('evidence_kind') not in ('execution_checkpoint','operator_attested_recovery'): raise ValueError('resume evidence lacks provenance')
        if context_option(evidence['prior_argv'])!=max_context_tokens: raise ValueError('resume text-context option mismatch')
        for key in ('delivery_sha256','model_sha256','tool_sha256'):
            if evidence.get(key)!=base_identity[key]: raise ValueError('resume identity mismatch: '+key)
        for name in ('analysis.wav','raw.txt','raw.json','raw.srt','raw.vtt','language-detection.log','asr.log'):
            src=partial/name
            if src.is_symlink() or media.sha256(src)!=evidence.get('artifacts',{}).get(name): raise ValueError('resume artifact mismatch: '+name)
            shutil.copy2(src,tmp/name)
        checkpoint=None
        if evidence['evidence_kind']=='execution_checkpoint':
            checkpoint_path=partial/'execution-checkpoint.json'
            if checkpoint_path.is_symlink() or media.sha256(checkpoint_path)!=evidence.get('checkpoint_sha256'): raise ValueError('resume checkpoint hash mismatch')
            checkpoint=json.loads(checkpoint_path.read_text())
            for key in ('delivery_sha256','model_sha256','tool_sha256','ffmpeg','threads','analysis_format'):
                if checkpoint['identity'].get(key)!=base_identity[key]: raise ValueError('recorded checkpoint mismatch: '+key)
            if checkpoint['identity'].get('max_context_tokens')!=max_context_tokens: raise ValueError('recorded checkpoint mismatch: max_context_tokens')
            if checkpoint.get('argv')!=evidence['prior_argv'] or checkpoint.get('analysis_sha256')!=evidence['artifacts']['analysis.wav']: raise ValueError('checkpoint command/analysis mismatch')
            shutil.copy2(checkpoint_path,tmp/'execution-checkpoint.json')
        recovery={'evidence_kind':evidence['evidence_kind'],'source_ref':evidence['source_ref'],'evidence_sha256':media.sha256(P(resume_evidence)),'partial_path':str(partial),'inference_identity':checkpoint['identity'] if checkpoint else None,'raw_rerun':False,'limitations':['Preexisting run had no cryptographic execution checkpoint; supplied evidence is an operator attestation.'] if evidence['evidence_kind']=='operator_attested_recovery' else []}
        shutil.copy2(resume_evidence,tmp/'recovery-evidence.json')
    analysis_target=tmp/('redecoded.wav' if resume_partial else 'analysis.wav')
    media.run(['ffmpeg','-v','error','-nostdin','-n','-i',delivery,'-map','0:a:0','-ar','16000','-ac','1','-c:a','pcm_s16le',analysis_target])
    if resume_partial:
        if media.sha256(analysis_target)!=media.sha256(tmp/'analysis.wav'): raise ValueError('resume analysis audio does not match final delivery decode')
        analysis_target.unlink()
    duration=media.probe(delivery)['duration']
    detect=[str(whisper),'-m',str(model),'-f',str(tmp/'analysis.wav'),'-l','auto','--detect-language','-t',str(threads)]
    if resume_partial: log=(tmp/'language-detection.log').read_text()
    else:
        detected=media.run(detect); log=detected.stdout+detected.stderr; (tmp/'language-detection.log').write_text(log)
    language, language_strategy = language_from_detection(log)
    identity={**base_identity,'language':language}
    argv=[str(whisper),'-m',str(model),'-f',str(tmp/'analysis.wav'),'-of',str(tmp/'raw'),'-otxt','-osrt','-ovtt','-ojf','-l',language,'-t',str(threads)]
    if max_context_tokens is not None: argv.extend(['--max-context',str(max_context_tokens)])
    if resume_partial:
        argv=evidence['prior_argv']
    else:
        media.write_json(tmp/'execution-checkpoint.json',{'identity':identity,'argv':argv,'detection_argv':detect,'analysis_sha256':media.sha256(tmp/'analysis.wav')})
        result=media.run(argv); (tmp/'asr.log').write_text(result.stdout+result.stderr)
    for extension in ('txt','json','srt','vtt'):
        p=tmp/('raw.'+extension)
        if not p.is_file() or not p.read_text().strip(): raise ValueError('missing raw output: '+extension)
    raw=json.loads((tmp/'raw.json').read_text()); corrections=[]
    timing_overrides=load_timing_corrections(timing_corrections,raw,identity['delivery_sha256'],media.sha256(tmp/'raw.json'))
    segments=align(raw,duration,corrections,timing_overrides)
    if timing_corrections: shutil.copy2(timing_corrections,tmp/'timing-corrections-input.json')
    if raw.get('result',{}).get('language') not in (None,language): raise ValueError('formal ASR language differs from detection')
    media.write_json(tmp/'aligned.json',{'schema_version':'2.0','audio_sha256':identity['delivery_sha256'],'language':language,'duration':duration,'segments':segments})
    media.write_json(tmp/'corrections.json',{'schema_version':'2.0','audio_sha256':identity['delivery_sha256'],'raw_json_sha256':media.sha256(tmp/'raw.json'),'corrections':corrections,'policy':'append corrections to a new revision; preserve raw artifacts'})
    if media.sha256(delivery)!=identity['delivery_sha256'] or media.sha256(model)!=identity['model_sha256'] or media.sha256(whisper)!=identity['tool_sha256']: raise ValueError('ASR input identity changed during execution')
    report={'schema_version':'2.0','stage':'transcription','identity':identity,'run_key':media.digest(identity),'language':language,'language_strategy':language_strategy,'duration':duration,'recovery':recovery,'correction_count':len(corrections),'timing_correction_count':sum(c['field'] in ('start','end') for c in corrections),'zero_span_duplicate_count':sum(c['field']=='text' and c['after']=='' for c in corrections),'segment_count':len(segments),'qc_status':'pass','qc_scope':'structural timestamps and nonempty outputs; no semantic listening review','argv':argv,'detection_argv':detect,'limitations':['Speakers are unknown; no diarization performed.','ASR text requires semantic review.'],'outputs':{p.name:media.artifact(p) for p in tmp.iterdir()}}
    media.write_json(tmp/'report.json',report); (tmp/'report.sha256').write_text(media.sha256(tmp/'report.json')+'\n'); os.mkdir(output)
    try:
        for p in tmp.iterdir(): os.rename(p,output/p.name)
    finally: tmp.rmdir()
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--delivery',type=P,required=True); ap.add_argument('--output-dir',type=P,required=True); ap.add_argument('--model',type=P,help='Whisper ggml model (default: $WHISPER_MODEL, config whisper_model, else <workspace>/models/ggml-large-v3-q5_0.bin)'); ap.add_argument('--whisper-cli',type=P,help='whisper-cli executable (default: $WHISPER_CLI, config whisper_cli, else PATH)'); ap.add_argument('--threads',type=int,default=8); ap.add_argument('--resume-partial',type=P); ap.add_argument('--resume-evidence',type=P); ap.add_argument('--timing-corrections',type=P); ap.add_argument('--max-context-tokens',type=int,help='Explicit whisper-cli text-context limit; 0 disables carried text, omission keeps the tool default')
    a=ap.parse_args(); a.model=P(_podcast_model(a.model)); a.whisper_cli=P(_podcast_tool(a.whisper_cli,'WHISPER_CLI','whisper_cli','whisper-cli')); report=transcribe(a.delivery,a.output_dir,a.model,a.whisper_cli,a.threads,a.resume_partial,a.resume_evidence,a.timing_corrections,a.max_context_tokens); print(json.dumps({'report':str(a.output_dir/'report.json'),'report_sha256':media.sha256(a.output_dir/'report.json'),'run_key':report['run_key'],'language':report['language'],'qc_status':report['qc_status']}))
if __name__=='__main__': main()
