#!/usr/bin/env python3
"""Assemble a reviewable v2 candidate from existing verified stage artifacts."""
import argparse
import importlib.util
import json
from pathlib import Path
import package as contract

def assemble(root, source, source_kind, show_id, episode_key, revision, image_url, number, srt_source=None, explicit_cue_id=None):
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
    provider_metadata={'author':'Martin Lanse','explicit':explicit_cue_id is not None,'type':'full','season':1,'number':number,'image_url':image_url}
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
    source_record={'path':str(source),'sha256':contract.sha(source),'bytes':source.stat().st_size,'kind':'supplied_finished_wav' if source.suffix.lower()=='.wav' and source_kind=='imported_finished' else source_kind,'origin_tool':'Filmora export supplied by user','declaration_source':'user_authority_record.json#input'}
    rights={'policy':'user_directed_publication','distribution_authority':'explicit','unresolved_concrete_risks':[]}
    for dimension in ['content','voice','music','generator_terms']:
        rights[dimension]={'status':'unknown','source':'User supplied finished recording and explicitly requested publication; no separate ownership or licensing assertion supplied.','limitations':'No full audio listening or legal ownership verification claimed.'}
    rights['voice']['kind']='synthetic' if source_kind=='generated_finished' else 'unknown'
    sources=[source_record]
    if srt_source is not None:
        sources.append({'kind':'supplied_finished_srt','path':'source-evidence/filmora-supplied.srt','original_path':str(srt_source),'sha256':contract.sha(packaged_srt),'bytes':packaged_srt.stat().st_size,'declaration_source':'user_authority_record.json#input'})
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
    a=p.parse_args()
    print(json.dumps(assemble(a.package,a.source,a.source_kind,a.show_id,a.episode_key,a.revision,a.image_url,a.number,a.srt_source,a.explicit_cue_id),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
