#!/usr/bin/env python3
"""Assemble a reviewable v2 candidate from existing verified stage artifacts."""
import argparse
import importlib.util
import json
from pathlib import Path
import package as contract

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


EPISODE_TYPES = ('full', 'bonus', 'trailer')


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a non-empty string')
    return value


def resolve_author(show_id, author=None):
    """Author comes from the personal shows[show_id] entry; an explicit value must agree with it. Never inferred otherwise."""
    entry = _podcast_cfg().get('shows', {}).get(str(show_id), {})
    configured = entry.get('author')
    if author is not None and configured is not None and author != configured:
        raise ValueError(f'--author {author!r} conflicts with the configured author for show {show_id}')
    resolved = author if author is not None else configured
    if not resolved:
        raise ValueError(f'no author for show {show_id}: pass --author or add shows[{str(show_id)!r}].author to the podcast-skills config')
    return resolved


def assemble(root, source, source_kind, show_id, episode_key, revision, image_url, number, srt_source=None, explicit_cue_id=None, *, author, origin_tool, declaration_source, srt_declaration_source=None, season=1, episode_type='full'):
    author = _text(author, 'author'); origin_tool = _text(origin_tool, 'origin_tool'); declaration_source = _text(declaration_source, 'declaration_source')
    srt_declaration_source = _text(srt_declaration_source if srt_declaration_source is not None else declaration_source, 'srt_declaration_source')
    if isinstance(season, bool) or not isinstance(season, int) or season < 0: raise ValueError('season must be a non-negative integer')
    if episode_type not in EPISODE_TYPES: raise ValueError('episode_type must be one of ' + ', '.join(EPISODE_TYPES))
    root=Path(root).absolute()
    if any(p.is_symlink() for p in [root,*root.parents]):
        raise ValueError('package root may not be a symlink')
    root=root.resolve()
    source=Path(source).resolve(strict=True)
    if (root/'seal.json').exists():
        raise ValueError('sealed candidates are immutable; create a new revision')
    targets=[root/'release'/n for n in ['episode.srt','episode.vtt','audio-qc.json']]+[root/'payload.json',root/'episode.json',root/'transcription/derived-verification.json']
    for p in targets:
        if p.resolve()==source or any(q.is_symlink() for q in [p,*p.parents] if q.is_relative_to(root)) or not p.resolve().is_relative_to(root):
            raise ValueError('unsafe generated destination: '+str(p))
    content=contract.read(contract.safe(root,'content.json'))
    content_show=(content.get('metadata') or {}).get('show_id')
    if content_show is not None and str(content_show)!=str(show_id):
        raise ValueError('content metadata show_id differs from --show-id')
    aligned_path=root/'transcription/aligned-corrected.json'
    ledger_path=root/'transcription/corrections-corrected.json'
    if not aligned_path.exists(): aligned_path=root/'transcription/aligned.json'
    if not ledger_path.exists(): ledger_path=root/'transcription/corrections.json'
    aligned_path=contract.safe(root,str(aligned_path.relative_to(root)))
    ledger_path=contract.safe(root,str(ledger_path.relative_to(root)))
    aligned=contract.read(aligned_path)
    derived=aligned.get('provenance_kind')=='sample_edit_derived_transcription'
    if derived and srt_source is not None:
        raise ValueError('supplied-SRT mode cannot replace sample-edit lineage; preserve the edit-derived validation branch')
    audio=contract.safe(root,content['audio_path'])
    protected={source,audio,aligned_path,ledger_path,root/'content.json',root/content['cover_path']}
    if any(p.resolve() in protected for p in targets):
        raise ValueError('generated output collides with source artifact')
    ah=contract.sha(audio)
    report=contract.read(audio.parent/'report.json')
    if srt_source is not None:
        srt_source=Path(srt_source).resolve(strict=True)
        packaged_srt=contract.safe(root,'source-evidence/filmora-supplied.srt')
        input_path=contract.safe(root,'source-evidence/filmora-input-report.json')
        boundary_path=contract.safe(root,'qc/acoustic-boundaries.json')
        discrepancy_path=contract.safe(root,'qc/asr-discrepancy.json')
        raw_path=contract.safe(root,'transcription/raw.json')
        if contract.sha(srt_source) != contract.sha(packaged_srt):
            raise ValueError('supplied SRT differs from packaged source-evidence copy')
        if explicit_cue_id is not None:
            cues=[cue for cue in contract.parse_srt(packaged_srt) if cue['id']==explicit_cue_id]
            if len(cues)!=1:
                raise ValueError('explicit-content evidence cue is absent or ambiguous in supplied SRT')
            explicit_evidence={'kind':'user_supplied_srt_cue','artifact_role':'supplied_srt_source','cue_id':explicit_cue_id,'cue_text':cues[0]['text']}
        else:
            explicit_evidence=None
        provenance=aligned.get('alignment_provenance',{})
        if provenance.get('source_kind') != 'user_supplied_final_cut_srt' or provenance.get('source_sha256') != contract.sha(packaged_srt):
            raise ValueError('aligned transcript does not identify the packaged user-supplied SRT')
        input_report=contract.read(input_path)
        boundary=contract.read(boundary_path)
        discrepancy=contract.read(discrepancy_path)
        checks=[x for x in boundary.get('checks',[]) if x.get('boundary')=='intro_body' and x.get('pass') is True and x.get('lag_samples')==0]
        if len(checks)!=1:
            raise ValueError('a unique verified intro/body boundary is required to create SRT lineage')
        lineage={
            'kind':'user_supplied_final_cut_srt',
            'episode_key':episode_key,
            'source_srt_path':'source-evidence/filmora-supplied.srt',
            'source_srt_sha256':contract.sha(packaged_srt),
            'source_srt_bytes':packaged_srt.stat().st_size,
            'source_wav_sha256':contract.sha(source),
            'filmora_input_report_path':'source-evidence/filmora-input-report.json',
            'filmora_input_report_sha256':contract.sha(input_path),
            'acoustic_boundaries_path':'qc/acoustic-boundaries.json',
            'acoustic_boundaries_sha256':contract.sha(boundary_path),
            'asr_discrepancy_path':'qc/asr-discrepancy.json',
            'asr_discrepancy_sha256':contract.sha(discrepancy_path),
            'delivery_audio_sha256':ah,
            'raw_asr_sha256':contract.sha(raw_path),
            'sample_rate':boundary['sample_rate'],
            'offset_samples':checks[0]['expected_global_boundary_sample'],
            'cue_count':len(contract.parse_srt(packaged_srt))
        }
        lineage_path=root/'transcription/srt-alignment-lineage.json'
        if lineage_path.exists():
            if contract.read(lineage_path)!=lineage:
                raise ValueError('existing SRT alignment lineage differs from current source evidence')
        else:
            contract.atomic(lineage_path,lineage)
        aligned['provenance_kind']='user_supplied_srt_time_shift'
        aligned['srt_alignment_lineage_path']='transcription/srt-alignment-lineage.json'
        aligned_path.write_text(json.dumps(aligned,ensure_ascii=False,indent=2)+'\n')
    if explicit_cue_id is not None and srt_source is None:
        raise ValueError('explicit-content cue evidence currently requires a supplied SRT source')
    if explicit_cue_id is None:
        explicit_evidence=None
    lineage=None
    if derived:
        lineage_path=contract.safe(root,aligned['edit_lineage_path']); lineage=contract.read(lineage_path)
        helper=contract.CONTRACT.parents[2]/'podcast-transcription/scripts/edit_derived.py'
        spec=importlib.util.spec_from_file_location('assemble_edit_derived',helper); verifier=importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        verified=verifier.verify(root,lineage,aligned,contract.read(ledger_path),root/'transcription/raw.json',audio)
        verified.update(stage='edit-derived-transcription-verification',aligned_sha256=contract.sha(aligned_path),ledger_sha256=contract.sha(ledger_path),lineage_sha256=contract.sha(lineage_path),implementation_sha256=contract.implementation_hash())
        contract.atomic(root/'transcription/derived-verification.json',verified)
    (root/'release').mkdir(exist_ok=True)
    for vtt in [False,True]:
        (root/'release'/('episode.vtt' if vtt else 'episode.srt')).write_text(contract.subtitle(aligned['segments'],vtt))
    qc={'audio_sha256':ah,**report['metrics'],'stage_report_sha256':contract.sha(audio.parent/'report.json')}
    (root/'release/audio-qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2)+'\n')
    publication = {'publication_transcript':dict(contract.READING_PUBLICATION)}
    provider_metadata={'author':author,'explicit':explicit_cue_id is not None,'type':episode_type,'season':season,'number':number,'image_url':image_url}
    if explicit_evidence is not None: provider_metadata['explicit_evidence']=explicit_evidence
    payload={'title':content['title'],'summary':content['summary'],'description':contract.description(content),'author':provider_metadata['author'],'explicit':provider_metadata['explicit'],'type':provider_metadata['type'],'season':provider_metadata['season'],'number':provider_metadata['number'],'image_url':provider_metadata['image_url'],'transcript_text':contract.publication_text(publication,content,aligned['segments'])}
    (root/'payload.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    artifacts={}
    def add(role,path,timed=False,audio_hash=None):
        p=contract.safe(root,str(Path(path).relative_to(root)))
        rec={'path':str(p.relative_to(root)),'sha256':contract.sha(p),'bytes':p.stat().st_size,'parents':[]}
        if timed: rec.update(audio_sha256=audio_hash or ah,parents=['derived_source_delivery'] if audio_hash and audio_hash!=ah else ['delivery_audio'])
        artifacts[role]=rec
    add('delivery_audio',audio)
    add('aligned_transcript',aligned_path,True)
    add('correction_ledger',ledger_path,True)
    for role,name in [('raw_asr_json','raw.json'),('raw_asr_txt','raw.txt'),('raw_srt','raw.srt'),('raw_vtt','raw.vtt')]:
        add(role,root/'transcription'/name,True,lineage['source_audio_sha256'] if derived else None)
    if derived:
        add('edit_lineage',lineage_path)
        add('derived_transcription_report',root/'transcription/derived-verification.json',True)
        for role,evidence in lineage['evidence'].items(): add('derived_'+role,root/evidence['path'])
    else: add('asr_report',root/'transcription/report.json',True)
    add('subtitles_srt',root/'release/episode.srt',True)
    add('subtitles_vtt',root/'release/episode.vtt',True)
    add('audio_qc',root/'release/audio-qc.json')
    add('media_report',audio.parent/'report.json')
    add('enrichment',root/'content.json',True)
    add('artwork',root/content['cover_path'])
    add('preview',root/'preview/episode.html')
    add('enrichment_manifest',root/'preview/enrichment-manifest.json')
    add('transistor_payload',root/'payload.json')
    add('publication_transcript',root/'preview/reading-transcript.txt')
    if srt_source is not None:
        for role,path in [
            ('supplied_srt_source',packaged_srt),
            ('filmora_input_report',root/'source-evidence/filmora-input-report.json'),
            ('acoustic_boundary_report',root/'qc/acoustic-boundaries.json'),
            ('asr_discrepancy_report',root/'qc/asr-discrepancy.json'),
            ('srt_alignment_lineage',root/'transcription/srt-alignment-lineage.json')]:
            add(role,path)
    for role,name in [
        ('reading_edition_correction_evidence','source-evidence/reading-edition-review-evidence.json'),
        ('cover_artwork_base','source-evidence/cover-artwork-base.png'),
        ('cover_artwork_asset_receipt','source-evidence/cover-artwork-asset-receipt.md'),
        ('cover_artwork_provenance','source-evidence/cover-artwork-provenance.json'),
        ('r2_cover_upload_manifest','source-evidence/r2-cover-upload-manifest.json')]:
        if (root/name).is_file(): add(role,root/name)
    em=contract.read(root/'preview/enrichment-manifest.json')
    for i,a in enumerate(em['artifacts']+em['source_assets']):
        if a['path'] not in {v['path'] for v in artifacts.values()}:add('linked_'+str(i),root/a['path'])
    source=Path(source).resolve()
    source_record={'path':str(source),'sha256':contract.sha(source),'bytes':source.stat().st_size,'kind':'supplied_finished_wav' if source.suffix.lower()=='.wav' and source_kind=='imported_finished' else source_kind,'origin_tool':origin_tool,'declaration_source':declaration_source}
    rights={'policy':'user_directed_publication','distribution_authority':'explicit','unresolved_concrete_risks':[]}
    for dimension in ['content','voice','music','generator_terms']:
        rights[dimension]={'status':'unknown','source':'User supplied finished recording and explicitly requested publication; no separate ownership or licensing assertion supplied.','limitations':'No full audio listening or legal ownership verification claimed.'}
    rights['voice']['kind']='synthetic' if source_kind=='generated_finished' else 'unknown'
    sources=[source_record]
    if srt_source is not None:
        sources.append({'kind':'supplied_finished_srt','path':'source-evidence/filmora-supplied.srt','original_path':str(srt_source),'sha256':contract.sha(packaged_srt),'bytes':packaged_srt.stat().st_size,'declaration_source':srt_declaration_source})
    ep={'contract_version':'2.0','episode_key':episode_key,'package_revision':revision,'source_kind':source_kind,'review_mode':'delegated_release','show_id':str(show_id),'profile_ref':'podcast_mp3','sources':sources,'artifacts':artifacts,'provider_metadata':provider_metadata,'rights':rights,'reviews':['reviews/content.json','reviews/experience.json','reviews/implementation.json']}
    ep.update(publication)
    (root/'episode.json').write_text(json.dumps(ep,ensure_ascii=False,indent=2)+'\n')
    return {'package':str(root),'payload_sha256':contract.canonical(payload),'audio_sha256':ah,'review_context_sha256':contract.review_context(ep),'artifact_bindings':{r:artifacts[r]['sha256'] for r in ['delivery_audio','enrichment','preview','artwork']}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--source-kind',choices=['raw_recording','imported_finished','generated_finished'],required=True)
    p.add_argument('--show-id',required=True)
    p.add_argument('--episode-key',required=True)
    p.add_argument('--revision',type=int,required=True)
    p.add_argument('--image-url',required=True)
    p.add_argument('--number',type=int,required=True)
    p.add_argument('--srt-source',type=Path)
    p.add_argument('--explicit-cue-id',type=int,help='Zero-based cue ID in the supplied SRT that supports the provider explicit flag')
    p.add_argument('--author',help='Defaults to shows[<show-id>].author in the podcast-skills config; an explicit value must agree with it')
    p.add_argument('--season',type=int,default=1,help='Non-negative season number (default 1)')
    p.add_argument('--episode-type',choices=EPISODE_TYPES,default='full')
    p.add_argument('--origin-tool',required=True,help='How the supplied recording was produced (for example the editor/export used); recorded in sources[]')
    p.add_argument('--declaration-source',required=True,help='Reference to the original user declaration of this source (message/record id or path#anchor)')
    p.add_argument('--srt-declaration-source',help='Declaration reference for the supplied SRT when it differs from --declaration-source')
    a=p.parse_args()
    try: author=resolve_author(a.show_id,a.author)
    except ValueError as error: raise SystemExit(str(error))
    print(json.dumps(assemble(a.package,a.source,a.source_kind,a.show_id,a.episode_key,a.revision,a.image_url,a.number,a.srt_source,a.explicit_cue_id,author=author,origin_tool=a.origin_tool,declaration_source=a.declaration_source,srt_declaration_source=a.srt_declaration_source,season=a.season,episode_type=a.episode_type),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
