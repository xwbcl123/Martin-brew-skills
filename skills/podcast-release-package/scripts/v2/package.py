#!/usr/bin/env python3
"""Version 2 package integrity, delegated acceptance and sealing. No network writes."""
import argparse
import copy
import hashlib
import html
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
from decimal import Decimal

import jsonschema

CONTRACT = Path(__file__).resolve().parents[2] / 'references' / 'v2'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

PAYLOAD_FIELDS = {'title','summary','description','author','explicit','type','season','number','image_url','transcript_text'}

def safe(root, rel):
    root = Path(root).resolve()
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('unsafe package path: ' + str(rel))
    p = root / p
    if not p.resolve().is_relative_to(root) or any(q.is_symlink() for q in [p, *p.parents] if q != root and q.is_relative_to(root)):
        raise ValueError('symlink or containment violation: ' + str(rel))
    if not p.is_file():
        raise ValueError('missing artifact: ' + str(rel))
    return p

def read(path):
    return json.loads(Path(path).read_text())

def atomic(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.partial')
    with tmp.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def bundle_hash():
    files = sorted([*CONTRACT.glob('*.json'), CONTRACT/'contract.md'])
    return canonical({str(x.relative_to(CONTRACT)):sha(x) for x in files if x.is_file()})

def implementation_hash():
    skills = CONTRACT.parents[2]
    files = []
    for name in ['podcast-final-edit','podcast-mastering','podcast-transcription','podcast-enrichment','podcast-transistor-publish']:
        files += [p for p in (skills/name).rglob('*') if p.is_file() and p.suffix in ['.py','.html','.json','.css','.js'] and 'tests' not in p.parts]
    files += list((skills/'podcast-release-package'/'scripts'/'v2').glob('*.py'))
    files += list((skills/'podcast-production-workflow'/'scripts'/'v2').glob('*.py'))
    files += [skills/'podcast-production-workflow'/'scripts'/n for n in ['master_audio_local.py','render_sample_edl.py']]
    return canonical({str(p.relative_to(skills)):sha(p) for p in sorted(files)})

def review_context(ep):
    return canonical({'contract_version':ep['contract_version'],'episode_key':ep['episode_key'],'package_revision':ep['package_revision'],'source_kind':ep['source_kind'],'review_mode':ep['review_mode'],'show_id':ep['show_id'],'profile_ref':ep['profile_ref'],'artifacts':ep['artifacts'],'provider_metadata':ep.get('provider_metadata'),'rights':ep['rights'],'sources':ep['sources'],'publication_transcript':ep.get('publication_transcript'),'implementation_sha256':implementation_hash(),'contract_bundle_sha256':bundle_hash()})

def parse_srt(path):
    text = Path(path).read_bytes().decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    blocks = re.split(r'\n[ \t]*\n', text.strip())
    cues = []
    stamp = re.compile(r'^(\d{2,}):(\d{2}):(\d{2}),(\d{3})$')
    timing = re.compile(r'^(\d{2,}:\d{2}:\d{2},\d{3}) --> (\d{2,}:\d{2}:\d{2},\d{3})$')
    def seconds(value):
        m = stamp.fullmatch(value)
        if not m: raise ValueError('invalid supplied SRT timestamp')
        h, minute, sec, ms = (int(x) for x in m.groups())
        if minute >= 60 or sec >= 60: raise ValueError('invalid supplied SRT clock field')
        return Decimal(h*3600 + minute*60 + sec) + Decimal(ms)/Decimal(1000)
    for index, block in enumerate(blocks):
        lines = block.split('\n')
        if len(lines) < 3 or lines[0].strip() != str(index+1):
            raise ValueError('supplied SRT cues must be numbered sequentially from 1')
        m = timing.fullmatch(lines[1].strip())
        if not m: raise ValueError('invalid supplied SRT timing row')
        start, end = seconds(m.group(1)), seconds(m.group(2))
        body = '\n'.join(lines[2:]).strip()
        if not body or end <= start: raise ValueError('empty or nonpositive supplied SRT cue')
        cues.append({'id':index,'start':start,'end':end,'text':body})
    if not cues: raise ValueError('supplied SRT is empty')
    return cues

def verify_supplied_srt(root, ep, artifacts, aligned, ledger, raw_path, audio_hash):
    """Verify a user-supplied final-cut SRT as the canonical text/timing source."""
    required = ['supplied_srt_source','filmora_input_report','acoustic_boundary_report','asr_discrepancy_report','srt_alignment_lineage']
    missing = [r for r in required if r not in artifacts]
    if missing: raise ValueError('supplied SRT provenance roles missing: '+', '.join(missing))
    lineage_path = safe(root, artifacts['srt_alignment_lineage']['path'])
    lineage = read(lineage_path)
    jsonschema.validate(lineage, read(CONTRACT/'srt-alignment-lineage.schema.json'))
    src = [x for x in ep.get('sources',[]) if x.get('kind') == 'supplied_finished_srt']
    wav = [x for x in ep.get('sources',[]) if x.get('kind') == 'supplied_finished_wav']
    if len(src) != 1 or len(wav) != 1: raise ValueError('supplied SRT/WAV source identities must be unique')
    srt_path = safe(root, artifacts['supplied_srt_source']['path'])
    input_path = safe(root, artifacts['filmora_input_report']['path'])
    boundary_path = safe(root, artifacts['acoustic_boundary_report']['path'])
    discrepancy_path = safe(root, artifacts['asr_discrepancy_report']['path'])
    if src[0].get('path') != artifacts['supplied_srt_source']['path'] or src[0].get('sha256') != sha(srt_path) or src[0].get('bytes') != srt_path.stat().st_size:
        raise ValueError('supplied SRT episode source differs from packaged bytes')
    if wav[0].get('sha256') != lineage['source_wav_sha256']:
        raise ValueError('supplied WAV identity differs from SRT alignment lineage')
    evidence_paths = {'filmora_input_report':input_path,'acoustic_boundary_report':boundary_path,'asr_discrepancy_report':discrepancy_path}
    for role, path_key, hash_key in [
        ('filmora_input_report','filmora_input_report_path','filmora_input_report_sha256'),
        ('acoustic_boundary_report','acoustic_boundaries_path','acoustic_boundaries_sha256'),
        ('asr_discrepancy_report','asr_discrepancy_path','asr_discrepancy_sha256')]:
        if lineage[path_key] != artifacts[role]['path'] or lineage[hash_key] != sha(evidence_paths[role]):
            raise ValueError('SRT lineage evidence binding mismatch: '+role)
    if lineage['episode_key'] != ep['episode_key'] or lineage['delivery_audio_sha256'] != audio_hash or lineage['raw_asr_sha256'] != sha(raw_path):
        raise ValueError('SRT lineage episode/audio/ASR identity mismatch')
    if lineage['source_srt_path'] != artifacts['supplied_srt_source']['path'] or lineage['source_srt_sha256'] != sha(srt_path) or lineage['source_srt_bytes'] != srt_path.stat().st_size:
        raise ValueError('SRT lineage source binding mismatch')
    input_report = read(input_path)
    if input_report.get('episode_key') != ep['episode_key'] or input_report.get('source_audio',{}).get('sha256') != lineage['source_wav_sha256']:
        raise ValueError('Filmora input report source WAV mismatch')
    if input_report.get('source_subtitles',{}).get('sha256') != sha(srt_path) or input_report.get('source_subtitles',{}).get('bytes') != srt_path.stat().st_size:
        raise ValueError('Filmora input report source SRT mismatch')
    boundary = read(boundary_path)
    if boundary.get('delivery_sha256') != audio_hash or boundary.get('sample_rate') != lineage['sample_rate'] or boundary.get('composition_to_delivery_boundaries_verified') is not True:
        raise ValueError('acoustic boundary report does not bind the delivery timeline')
    body = [x for x in boundary.get('checks',[]) if x.get('boundary') == 'intro_body']
    if len(body) != 1 or body[0].get('pass') is not True or body[0].get('lag_samples') != 0 or body[0].get('expected_global_boundary_sample') != lineage['offset_samples']:
        raise ValueError('SRT offset does not match verified intro/body sample boundary')
    discrepancy = read(discrepancy_path)
    identities = discrepancy.get('identities',{})
    if identities.get('delivery_sha256') != audio_hash or identities.get('whisper_raw_json_sha256') != sha(raw_path) or identities.get('filmora_srt_sha256') != sha(srt_path):
        raise ValueError('ASR discrepancy evidence is stale for the declared SRT source')
    if aligned.get('provenance_kind') != 'user_supplied_srt_time_shift' or aligned.get('srt_alignment_lineage_path') != artifacts['srt_alignment_lineage']['path']:
        raise ValueError('aligned transcript does not declare supplied SRT lineage')
    p = aligned.get('alignment_provenance',{})
    offset_seconds = Decimal(lineage['offset_samples'])/Decimal(lineage['sample_rate'])
    if p.get('source_kind') != 'user_supplied_final_cut_srt' or p.get('source_sha256') != sha(srt_path) or p.get('offset_samples_at_48khz') != lineage['offset_samples'] or Decimal(str(p.get('offset_seconds'))) != offset_seconds or p.get('boundary_report_sha256') != sha(boundary_path):
        raise ValueError('aligned transcript provenance differs from supplied SRT lineage')
    d = ledger.get('derivation',{})
    if d.get('source_kind') != 'user_supplied_final_cut_srt' or d.get('source_sha256') != sha(srt_path) or d.get('cue_count') != lineage['cue_count'] or d.get('timeline_offset_samples') != lineage['offset_samples'] or d.get('boundary_report_sha256') != sha(boundary_path) or d.get('discrepancy_report_sha256') != sha(discrepancy_path):
        raise ValueError('correction ledger does not preserve supplied SRT derivation')
    if ledger.get('corrections') != []:
        raise ValueError('supplied SRT provenance mode requires an empty raw-ASR correction chain')
    cues = parse_srt(srt_path)
    if len(cues) != lineage['cue_count'] or len(cues) != len(aligned.get('segments',[])):
        raise ValueError('supplied SRT cue/aligned segment count mismatch')
    tolerance = Decimal(1)/Decimal(lineage['sample_rate'])
    for cue, segment in zip(cues, aligned['segments']):
        if segment.get('id') != cue['id'] or segment.get('source_segment_id') != cue['id'] or segment.get('text') != cue['text']:
            raise ValueError('aligned transcript text or source cue ID differs from supplied SRT')
        if abs(Decimal(str(segment.get('start'))) - (cue['start']+offset_seconds)) > tolerance or abs(Decimal(str(segment.get('end'))) - (cue['end']+offset_seconds)) > tolerance:
            raise ValueError('aligned transcript timing differs from supplied SRT plus verified sample offset')
    return {'valid':True,'kind':lineage['kind'],'cue_count':len(cues),'source_srt_sha256':sha(srt_path),'delivery_audio_sha256':audio_hash,'offset_samples':lineage['offset_samples'],'sample_rate':lineage['sample_rate'],'full_human_listening_review':False,'verbatim_completeness_verified':False}

READING_PUBLICATION = {'version': 1, 'source': 'reading_transcript'}

def publication_text(ep, content, segments):
    if 'publication_transcript' not in ep:
        return '\n'.join(s['text'].strip() for s in segments)
    marker = ep['publication_transcript']
    if not isinstance(marker, dict) or marker != READING_PUBLICATION or type(marker.get('version')) is not int:
        raise ValueError('unknown publication transcript contract')
    paragraphs = content.get('reading_transcript')
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError('reading publication requires full paragraphs')
    covered = []
    for paragraph in paragraphs:
        value = paragraph.get('text')
        refs = paragraph.get('source_segment_ids')
        if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
            raise ValueError('reading publication paragraph must be one nonempty line')
        if not isinstance(refs, list) or not refs:
            raise ValueError('reading publication source references missing')
        covered.extend(refs)
    expected = [s['id'] for s in segments]
    if covered != expected or any(type(a) is not type(b) for a,b in zip(covered, expected)):
        raise ValueError('reading publication requires ordered exactly-once source coverage')
    return '\n\n'.join(p['text'] for p in paragraphs)

def subtitle(segments, vtt=False):
    def stamp(t):
        ms = round(t*1000)
        h, rem = divmod(ms,3600000)
        m, rem = divmod(rem,60000)
        s, ms = divmod(rem,1000)
        return f'{h:02}:{m:02}:{s:02}{"." if vtt else ","}{ms:03}'
    chunks = [f'{i+1}\n{stamp(s["start"])} --> {stamp(s["end"])}\n{s["text"]}' for i,s in enumerate(segments)]
    return ('WEBVTT\n\n' if vtt else '')+'\n\n'.join(chunks)+'\n'

def description(content):
    if "public_content" in content:
        module_path = CONTRACT.parents[2]/"podcast-enrichment/scripts/enrich.py"
        spec = importlib.util.spec_from_file_location("public_content_renderer", module_path)
        renderer = importlib.util.module_from_spec(spec); spec.loader.exec_module(renderer)
        return renderer.public_html(content)
    def paras(s):
        return ''.join('<p>'+html.escape(x).replace('\n','<br>')+'</p>' for x in s.split('\n\n') if x.strip())
    chapters=''.join(f'<li>{int(c["start"])//60:02}:{int(c["start"])%60:02} {html.escape(c["title"])}</li>' for c in content['chapters'])
    sources=''.join('<li><a href="'+html.escape(r['url'],quote=True)+'">'+html.escape(r['title'])+'</a></li>' for r in content['resources'])
    return paras(content['description'])+'<h2>节目笔记</h2>'+paras(content['show_notes'])+'<h2>章节</h2><ul>'+chapters+'</ul><h2>相关资料</h2><ul>'+sources+'</ul>'+paras(content['ai_disclosure'])

def validate(root, release=False, require_seal=False):
    root = Path(root).resolve()
    errors = []
    result = {'valid': False, 'errors': errors, 'evidence_level': 'local_verified'}
    try:
        ep = read(safe(root, 'episode.json'))
        jsonschema.validate(ep, read(CONTRACT / 'episode.schema.json'))
        artifacts = ep['artifacts']
        for role, a in artifacts.items():
            path = safe(root, a['path'])
            if path.stat().st_size != a['bytes'] or sha(path) != a['sha256']:
                errors.append('artifact changed: ' + role)
        required = ['delivery_audio', 'aligned_transcript', 'raw_asr_json', 'raw_asr_txt', 'subtitles_srt', 'subtitles_vtt', 'correction_ledger', 'enrichment', 'enrichment_manifest', 'artwork', 'preview', 'transistor_payload', 'audio_qc']
        if release:
            errors += ['missing role: ' + r for r in required if r not in artifacts]
        if any(r not in artifacts for r in ['delivery_audio', 'transistor_payload']):
            raise ValueError('delivery_audio/transistor_payload missing')
        audio = safe(root, artifacts['delivery_audio']['path'])
        payload = read(safe(root, artifacts['transistor_payload']['path']))
        ah = sha(audio)
        ph = canonical(payload)
        result.update(audio_sha256=ah, payload_sha256=ph)
        if set(payload) != PAYLOAD_FIELDS:
            errors.append('provider payload fields do not match the exact release contract')
        if release:
            provider = ep.get('provider_metadata')
            if not isinstance(provider, dict):
                errors.append('declared provider metadata missing')
            else:
                for key in ['author','explicit','type','season','number','image_url']:
                    if key not in provider or payload.get(key) != provider.get(key):
                        errors.append('provider payload differs from declared metadata: '+key)
                if type(payload.get('explicit')) is not bool:
                    errors.append('provider explicit flag must be a boolean')
                if provider.get('explicit') is True:
                    evidence = provider.get('explicit_evidence', {})
                    role = evidence.get('artifact_role')
                    if evidence.get('kind') != 'user_supplied_srt_cue' or role != 'supplied_srt_source' or role not in artifacts:
                        errors.append('explicit provider flag lacks supplied-SRT cue evidence')
                    else:
                        cues = [c for c in parse_srt(safe(root, artifacts[role]['path'])) if c['id'] == evidence.get('cue_id')]
                        if len(cues) != 1 or cues[0]['text'] != evidence.get('cue_text'):
                            errors.append('explicit provider flag cue evidence differs from supplied SRT')
                elif provider.get('explicit_evidence') is not None:
                    errors.append('explicit-content evidence supplied while provider flag is false')
        if require_seal:
            seal = read(safe(root, 'seal.json'))
            review_hashes = {ref:sha(safe(root,ref)) for ref in ep['reviews']}
            if not seal.get('valid') or seal.get('manifest_sha256') != sha(root/'episode.json') or seal.get('audio_sha256') != ah or seal.get('payload_sha256') != ph or seal.get('contract_bundle_sha256') != bundle_hash() or seal.get('review_hashes') != review_hashes or seal.get('implementation_sha256') != implementation_hash():
                errors.append('seal missing/stale/invalid')
        if not payload.get('title') or not payload.get('description'):
            errors.append('empty release metadata')
        if release:
            profile = read(CONTRACT / 'profiles.json')['profiles'][ep['profile_ref']]
            probe = json.loads(subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(audio)], check=True, capture_output=True, text=True).stdout)
            streams = [s for s in probe['streams'] if s.get('codec_type') == 'audio']
            if len(streams) != 1:
                raise ValueError('one delivery audio stream required')
            stream = streams[0]
            duration = float(probe['format']['duration'])
            if stream['codec_name'] != 'mp3' or int(stream['sample_rate']) not in profile['sample_rates'] or int(stream.get('bit_rate',0)) < profile['min_bitrate_kbps'] * 1000:
                errors.append('delivery codec profile failed')
            qc = read(safe(root, artifacts['audio_qc']['path']))
            if qc.get('audio_sha256') != ah:
                errors.append('stale audio QC binding')
            for key in ['integrated_lufs','true_peak_dbtp']:
                if not isinstance(qc.get(key), (float,int)) or not math.isfinite(qc[key]):
                    errors.append('missing/nonfinite metric: ' + key)
            if not any('metric:' in e for e in errors):
                if abs(qc['integrated_lufs'] - profile['target_lufs']) > profile['tolerance_lu'] or qc['true_peak_dbtp'] > profile['max_true_peak_dbtp']:
                    errors.append('delivery loudness profile failed')
            measured = subprocess.run(['ffmpeg','-nostdin','-hide_banner','-nostats','-i',str(audio),'-af','loudnorm=I=-16:TP=-1:print_format=json','-f','null','-'],check=True,capture_output=True,text=True).stderr
            blocks = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', measured)
            if not blocks:
                raise ValueError('fresh loudness measurement missing')
            observed = json.loads(blocks[-1])
            li, tp = float(observed['input_i']), float(observed['input_tp'])
            result['observed_audio_metrics'] = {'integrated_lufs':li,'true_peak_dbtp':tp}
            if not math.isfinite(li) or not math.isfinite(tp) or abs(li-profile['target_lufs']) > profile['tolerance_lu'] or tp > profile['max_true_peak_dbtp']:
                errors.append('fresh measured loudness profile failed')
            if abs(li-qc['integrated_lufs']) > .05 or abs(tp-qc['true_peak_dbtp']) > .05:
                errors.append('reported QC differs from fresh measurement')
            from PIL import Image
            cover = safe(root, artifacts['artwork']['path'])
            with Image.open(cover) as im:
                if im.width != im.height or not profile['artwork_min_px'] <= im.width <= profile['artwork_max_px'] or im.mode != 'RGB' or cover.stat().st_size > profile['artwork_max_bytes']:
                    errors.append('artwork profile failed')
            if not str(payload.get('image_url','')).startswith('https://'):
                errors.append('public artwork URL required')
            aligned = read(safe(root, artifacts['aligned_transcript']['path']))
            srt_derived = aligned.get('provenance_kind') == 'user_supplied_srt_time_shift'
            if srt_derived and release:
                srt_required = ['supplied_srt_source','filmora_input_report','acoustic_boundary_report','asr_discrepancy_report','srt_alignment_lineage']
                errors += ['missing role: '+r for r in srt_required if r not in artifacts]
            base_audio = audio
            base_ah = ah
            metadata_lineage = None
            if 'audio_metadata_lineage' in artifacts:
                metadata_lineage = read(safe(root, artifacts['audio_metadata_lineage']['path']))
                base_audio = safe(root, metadata_lineage['base_audio_path'])
                base_ah = sha(base_audio)
                if artifacts.get('base_delivery_audio', {}).get('path') != metadata_lineage['base_audio_path'] or metadata_lineage.get('base_audio_sha256') != base_ah or metadata_lineage.get('tagged_audio_sha256') != ah:
                    raise ValueError('ID3 lineage binding mismatch')
                chapter_spec = importlib.util.spec_from_file_location('tag_only_verifier', Path(__file__).with_name('chapters.py'))
                chapter_module = importlib.util.module_from_spec(chapter_spec); chapter_spec.loader.exec_module(chapter_module)
                result['audio_metadata_verification'] = chapter_module.verify(base_audio, audio, metadata_lineage['chapter_input'])
                if result['audio_metadata_verification'] != {k:v for k,v in metadata_lineage.items() if k not in ('base_audio_path','chapter_input')}:
                    raise ValueError('ID3 lineage differs from fresh verification')
            derived = aligned.get('provenance_kind') == 'sample_edit_derived_transcription'
            edit_lineage = read(safe(root,aligned['edit_lineage_path'])) if derived else None
            if derived and ('edit_lineage' not in artifacts or artifacts['edit_lineage']['path'] != aligned['edit_lineage_path']):
                errors.append('edit-derived lineage artifact missing')
            if aligned.get('audio_sha256') != ah:
                errors.append('stale transcript binding')
            segments = aligned.get('segments', [])
            if not segments:
                errors.append('empty aligned transcript')
            last = 0
            for s in segments:
                if not (0 <= s['start'] <= s['end'] <= duration + 0.1) or s['start'] < last or not s.get('text','').strip():
                    errors.append('invalid transcript timing/text')
                    break
                last = s['start']
            text = '\n'.join(s['text'].strip() for s in segments)
            enrichment = read(safe(root, artifacts['enrichment']['path']))
            core = lambda rows: [{k:s.get(k) for k in ('id','start','end','text')} for s in rows]
            if core(enrichment.get('segments',[])) != core(segments):
                errors.append('enrichment transcript differs from bound aligned transcript')
            if enrichment.get('audio_path') != artifacts['delivery_audio']['path'] or enrichment.get('cover_path') != artifacts['artwork']['path']:
                errors.append('preview audio/artwork paths differ from selected artifacts')
            if enrichment.get('title') != payload.get('title') or enrichment.get('summary') != payload.get('summary'):
                errors.append('preview metadata differs from provider payload')
            if payload.get('description') != description(enrichment):
                errors.append('provider description differs from complete preview content')
            if metadata_lineage and metadata_lineage['chapter_input'] != enrichment['chapters']:
                errors.append('embedded chapter input differs from enrichment')
            for role in ['aligned_transcript','raw_asr_json','raw_asr_txt','subtitles_srt','subtitles_vtt','correction_ledger','enrichment']:
                expected_audio = (edit_lineage['source_audio_sha256'] if derived else base_ah) if role in ('raw_asr_json','raw_asr_txt') else ah
                if artifacts[role].get('audio_sha256') != expected_audio:
                    errors.append('missing/stale audio lineage: '+role)
            raw_path = safe(root,artifacts['raw_asr_json']['path'])
            raw = read(raw_path)
            raw_segments = raw.get('transcription',[])
            if not raw_segments:
                errors.append('raw ASR empty')
            raw_text = safe(root,artifacts['raw_asr_txt']['path']).read_text()
            compact = lambda value: re.sub(r'\s+','',value)
            if compact(raw_text) != compact(''.join(s['text'] for s in raw_segments)):
                errors.append('raw ASR text/json disagree')
            ledger = read(safe(root,artifacts['correction_ledger']['path']))
            if ledger.get('audio_sha256') != ah or ledger.get('raw_json_sha256') != sha(raw_path) or not isinstance(ledger.get('corrections'),list):
                errors.append('correction ledger stale/invalid')
            if derived:
                helper_path = CONTRACT.parents[2]/'podcast-transcription'/'scripts'/'edit_derived.py'
                derived_spec = importlib.util.spec_from_file_location('v2_edit_derived_validator',helper_path)
                derived_module = importlib.util.module_from_spec(derived_spec)
                derived_spec.loader.exec_module(derived_module)
                check_aligned, check_ledger = copy.deepcopy(aligned), copy.deepcopy(ledger)
                check_aligned['audio_sha256'] = base_ah; check_ledger['audio_sha256'] = base_ah
                result['edit_derived_verification'] = derived_module.verify(root,edit_lineage,check_aligned,check_ledger,raw_path,base_audio)
                indexed = {a['path']:a for a in artifacts.values()}
                for evidence in edit_lineage['evidence'].values():
                    if evidence['path'] not in indexed or indexed[evidence['path']]['sha256'] != evidence['sha256']:
                        errors.append('edit-derived evidence absent from package manifest: '+evidence['path'])
            raw_language = raw.get('result',{}).get('language')
            if not raw_language or aligned.get('language') != raw_language or enrichment.get('language') != raw_language:
                errors.append('ASR/aligned/enrichment language provenance mismatch')
            if srt_derived:
                result['supplied_srt_verification'] = verify_supplied_srt(root,ep,artifacts,aligned,ledger,raw_path,ah)
            else:
                raw_nonempty = [(i,s) for i,s in enumerate(raw_segments) if s.get('text','').strip()]
                raw_ids = {i for i,_ in raw_nonempty}
                if any(c.get('segment_id') not in raw_ids for c in ledger.get('corrections',[])):
                    errors.append('correction targets nonexistent raw segment')
                corrected_segments = []
                for i,rs in raw_nonempty:
                    expected_seg = {'text':rs['text'].strip(),'start':rs['offsets']['from']/1000,'end':rs['offsets']['to']/1000}
                    for c in ledger.get('corrections',[]):
                        if c.get('segment_id') == i:
                            field = c.get('field')
                            if field not in expected_seg or c.get('before') != expected_seg[field] or not c.get('reason'):
                                errors.append('invalid correction chain')
                            else:
                                expected_seg[field] = c.get('after')
                    if expected_seg['text'].strip():
                        corrected_segments.append((i,expected_seg))
                if len(corrected_segments) != len(segments):
                    errors.append('aligned/raw coverage mismatch')
                for (i,expected_seg),seg in zip(corrected_segments,segments):
                    if seg.get('id') != i or any(seg.get(k) != value for k,value in expected_seg.items()):
                        errors.append('aligned text/timing lacks raw correction provenance')
                        break
            for role,is_vtt in [('subtitles_srt',False),('subtitles_vtt',True)]:
                if safe(root,artifacts[role]['path']).read_text().replace('\r\n','\n').strip() != subtitle(segments,is_vtt).strip():
                    errors.append('canonical subtitle differs: '+role)
            module_path = CONTRACT.parents[2]/'podcast-enrichment'/'scripts'/'enrich.py'
            spec = importlib.util.spec_from_file_location('v2_enrichment_validator',module_path)
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            render_report = renderer.validate(enrichment,root)
            preview = safe(root,artifacts['preview']['path'])
            if preview.read_text() != renderer.render(enrichment,root,preview,render_report):
                errors.append('preview bytes differ from current grounded renderer output')
            em = read(safe(root,artifacts['enrichment_manifest']['path']))
            if em.get('content_sha256') != artifacts['enrichment']['sha256'] or em.get('audio_sha256') != ah or em.get('cover_sha256') != artifacts['artwork']['sha256']:
                errors.append('enrichment manifest stale')
            by_path = {a['path']:a for a in artifacts.values()}
            linked = em.get('artifacts',[])+em.get('source_assets',[])
            must = {'aligned-transcript.json','reading-transcript.json','transcript.txt','reading-transcript.txt','show-notes.txt','launch-copy.txt','chapters.json','summary.txt','description.txt','ai-disclosure.txt','content-metadata.json',preview.name}
            if not must.issubset({Path(a['path']).name for a in em.get('artifacts',[])}):
                errors.append('enrichment output inventory incomplete')
            for a in linked:
                if a['path'] not in by_path or by_path[a['path']]['sha256'] != a['sha256'] or sha(safe(root,a['path'])) != a['sha256']:
                    errors.append('linked preview artifact missing/changed: '+a['path'])
            expected_publication = publication_text(ep, enrichment, segments)
            if payload.get('transcript_text') != expected_publication:
                errors.append('provider transcript differs from declared complete publication text')
            if 'publication_transcript' in ep:
                publication = artifacts.get('publication_transcript')
                if not publication or publication['path'] != str(preview.parent.relative_to(root)/'reading-transcript.txt'):
                    errors.append('reading publication artifact missing or wrong path')
                elif safe(root,publication['path']).read_bytes() != expected_publication.encode('utf-8'):
                    errors.append('reading publication file differs from complete paragraphs')
            rights = ep['rights']
            if rights.get('policy') != 'user_directed_publication' or rights.get('distribution_authority') != 'explicit':
                errors.append('rights policy missing')
            for dim in ['content','voice','music','generator_terms']:
                d = rights.get(dim,{})
                if d.get('status') not in ['declared_by_user','verified','unknown','not_applicable'] or not d.get('source'):
                    errors.append('rights evidence missing: ' + dim)
            if rights.get('unresolved_concrete_risks') != []:
                errors.append('unresolved concrete rights risk')
            if ep['source_kind'] == 'generated_finished' and not any(x in payload['description'] for x in ['AI 生成','AI 合成']):
                errors.append('AI disclosure absent from provider payload')
            accepted = set()
            expected = {r: artifacts[r]['sha256'] for r in ['delivery_audio','enrichment','preview','artwork']}
            for ref in ep['reviews']:
                rv = read(safe(root, ref))
                kind = rv.get('kind')
                if rv.get('decision') != 'approved' or rv.get('accepted_by_kind') != 'agent_delegated' or rv.get('user_reviewed') is not False or not rv.get('reviewer_id') or not rv.get('evidence'):
                    errors.append('invalid review: ' + ref)
                    continue
                if rv.get('artifact_bindings') != expected or rv.get('payload_sha256') != ph:
                    errors.append('stale review: ' + ref)
                    continue
                if rv.get('review_context_sha256') != review_context(ep):
                    errors.append('stale implementation/rights/source review context: '+ref)
                if kind == 'experience':
                    coverage = rv.get('checks', {})
                    for k in ['desktop_1440','mobile_390','play_pause','seek','chapter','search','copy']:
                        if coverage.get(k) is not True:
                            errors.append('experience check missing: ' + k)
                    shots = rv.get('screenshots', [])
                    if len(shots) < 2:
                        errors.append('missing visual evidence')
                    for shot in shots:
                        if sha(safe(root, shot['path'])) != shot['sha256']:
                            errors.append('changed screenshot')
                accepted.add(kind)
            errors += ['missing independent review: ' + k for k in ['content','experience','implementation'] if k not in accepted]
    except Exception as e:
        errors.append(str(e))
    result['valid'] = not errors
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['validate','seal'])
    p.add_argument('--package',required=True,type=Path)
    p.add_argument('--release',action='store_true')
    p.add_argument('--require-seal',action='store_true')
    a = p.parse_args()
    r = validate(a.package, a.release or a.require_seal or a.command == 'seal', a.require_seal)
    if a.command == 'seal' and r['valid']:
        r['manifest_sha256'] = sha(a.package / 'episode.json')
        r['contract_bundle_sha256'] = bundle_hash()
        r['implementation_sha256'] = implementation_hash()
        r['review_hashes'] = {ref:sha(safe(a.package,ref)) for ref in read(a.package/'episode.json')['reviews']}
        out = a.package / 'seal.json'
        if out.exists() and read(out) != r:
            r['valid'] = False
            r['errors'].append('immutable seal differs')
        elif not out.exists():
            atomic(out,r)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r['valid'] else 1

if __name__ == '__main__':
    sys.exit(main())
