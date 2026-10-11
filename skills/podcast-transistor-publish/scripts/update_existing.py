#!/usr/bin/env python3
"""Update one sealed, authorized existing episode without create/publish operations."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import publish as pub


CLI_REPO=None  # set from --transistor-cli-repo; else config transistor_cli_repo


def cli_identity():
    value=pub._podcast_pick(CLI_REPO,None,'transistor_cli_repo')
    if not value: raise pub.Blocked('Transistor CLI source checkout required: pass --transistor-cli-repo or set transistor_cli_repo in the podcast-skills config')
    value=os.path.expanduser(str(value))
    if not os.path.isabs(value): raise pub.Blocked('transistor_cli_repo must be an absolute path')
    repo=Path(os.path.realpath(value)); cli=Path(os.path.realpath(pub.cli_path()))
    if not (repo/'.git').exists() or not (repo/'src').is_dir() or not (repo/'pyproject.toml').is_file(): raise pub.Blocked('Unsupported Transistor CLI layout: transistor_cli_repo must be a Git checkout with src/ and pyproject.toml')
    try: cli.relative_to(repo)
    except ValueError: raise pub.Blocked('Unsupported Transistor CLI layout: the executable must live inside transistor_cli_repo (for example <repo>/.venv/bin/transistor)') from None
    if subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip(): raise pub.Blocked('CLI worktree must be clean')
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    paths=sorted((repo/'src').rglob('*.py'))+[repo/'pyproject.toml',cli]
    return {'commit':commit,'runtime_sha256':pub.digest_bytes(pub.canonical({str(p.relative_to(repo)):pub.digest_file(p) for p in paths}))}


def transcript(provider,attrs):
    if isinstance(attrs.get('transcript_text'),str): return attrs['transcript_text'].replace('\r\n','\n').replace('\r','\n')
    urls=[t['url'] for t in attrs.get('transcripts',[]) if t.get('format')=='txt' and t.get('url')]
    if len(urls)!=1: raise pub.Blocked('Transcript endpoint missing or ambiguous')
    body,mime=provider.fetch(pub.safe_url(urls[0]))
    if not mime.startswith('text/plain'): raise pub.Blocked('Transcript MIME mismatch')
    return body.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')


transcript_match = pub.transcript_match


class UpdateController(pub.Controller):
    required_operations = {'readback', 'update_existing'}

    def fresh(self):
        binding = super().fresh()
        if not str(self.a.get('remote_id','')).isdigit(): raise pub.Blocked('Exact remote_id required')
        self.cli_identity=cli_identity()
        if self.a.get('cli_identity') != self.cli_identity: raise pub.Blocked('CLI identity differs from authorization')
        baseline = self.a.get('baseline', {})
        for key in ('manifest_path','manifest_sha256','snapshot_path','snapshot_sha256'):
            if not baseline.get(key): raise pub.Blocked('Bound baseline required: '+key)
        bp, sp = Path(baseline['manifest_path']), Path(baseline['snapshot_path'])
        if bp.is_symlink() or sp.is_symlink() or pub.digest_file(bp) != baseline['manifest_sha256'] or pub.digest_file(sp) != baseline['snapshot_sha256']:
            raise pub.Blocked('Baseline changed')
        self.old_manifest = pub.read(bp); self.before = pub.read(sp)['data']
        old = self.old_manifest
        if old['episode_key'] != self.m['episode_key'] or old['show_id'] != self.m['show_id'] or str(self.before['id']) != self.a['remote_id'] or self.before['relationships']['show']['data']['id'] != self.m['show_id']:
            raise pub.Blocked('Baseline episode identity mismatch')
        art=old['artifacts']['delivery_audio']; self.old_audio=(bp.parent/art['path']).resolve()
        if not self.old_audio.is_relative_to(bp.parent.resolve()) or pub.digest_file(self.old_audio) != art['sha256']: raise pub.Blocked('Baseline audio changed')
        pa=old['artifacts']['transistor_payload']; pp=bp.parent/pa['path']
        if pub.digest_file(pp) != pa['sha256']: raise pub.Blocked('Baseline payload changed')
        self.old_payload=pub.read(pp)
        if self.before['attributes'].get('title') != self.old_payload['title'] or self.before['attributes'].get('status') != 'published': raise pub.Blocked('Baseline content/status mismatch')
        self.replace_media = pub.digest_file(self.old_audio) != binding['release_audio_sha256']
        if self.replace_media and not {'upload','replace_media'}.issubset(self.a['allowed_operations']): raise pub.Blocked('Media replacement not authorized')
        update_binding={**binding,'authorization_sha256':pub.digest_file(self.authorization_path),'cli_identity':self.cli_identity,'baseline':baseline,'remote_id':self.a['remote_id']}
        if hasattr(self,'update_binding') and self.update_binding != update_binding: raise pub.Blocked('Update authority/runtime/baseline changed during operation')
        self.update_binding=update_binding
        return binding

    def identity(self):
        r=self.get(self.a['remote_id']); a=r['attributes']; before=self.before['attributes']
        if r.get('relationships',{}).get('show',{}).get('data',{}).get('id') != self.m['show_id'] or a.get('status') != 'published' or a.get('published_at') != before.get('published_at'):
            raise pub.Blocked('Existing episode show/status/publication date changed')
        if a.get('title') not in (self.old_payload['title'],self.payload['title']): raise pub.Blocked('Existing episode content identity changed')
        def normalize(key,value):
            if key in ('number','season'): return str(value)
            if key=='explicit' and value in ('true','false'): return value=='true'
            return value
        for key in ('description','summary','author','number','season','explicit','type'):
            if normalize(key,a.get(key)) not in (normalize(key,before.get(key)),normalize(key,self.payload.get(key))):
                raise pub.Blocked('Concurrent episode field change: '+key)
        current_text=transcript(self.provider,a)
        if not any(transcript_match(current_text,value['transcript_text'],manifest) for value,manifest in [(self.old_payload,self.old_manifest),(self.payload,self.m)]): raise pub.Blocked('Concurrent transcript change')
        image_url=a['image_url']
        if image_url not in (before.get('image_url'),self.payload['image_url']): self.verify_artwork(r,image_url)
        image,mime=self.provider.fetch(pub.safe_url(image_url))
        image_hash=pub.digest_bytes(image)
        source_art=self.m['artifacts'].get('artwork',{})
        allowed_images={self.a['baseline'].get('remote_image_sha256'),source_art.get('sha256')}
        if image_hash not in allowed_images:
            self.verify_artwork(r,image_url)
            if not self.artwork_verification or image_hash!=pub.read(self.artwork_verification).get('remote_image_sha256'): raise pub.Blocked('Concurrent image content change')
        if not mime.startswith('image/'): raise pub.Blocked('Concurrent image MIME change')
        # Prove current media still has the authorized old acoustic content before each mutation.
        evidence=self.provider.fetch_media(pub.safe_url(a.get('media_url')),self.old_audio.stat().st_size,self.old_audio)
        exact=evidence['sha256']==pub.digest_file(self.old_audio) and evidence['bytes']==self.old_audio.stat().st_size
        pcm=evidence.get('exact_pcm',{})
        if not exact and (not pcm.get('source') or pcm.get('source') != pcm.get('remote')): raise pub.Blocked('Baseline audio identity failed')
        self.journal('identity','verified',remote_id=r['id'],source_path=str(self.old_audio),source_sha256=pub.digest_file(self.old_audio),remote_sha256=evidence['sha256'])
        return r

    def mutate(self,op,args):
        self.fresh(); self.identity()
        self.provider.call([*args,'--dry-run']); self.journal(op,'dry_run_verified')
        self.fresh(); self.identity()
        if pub.digest_file(self.snapshot)!=self.binding['release_audio_sha256']: raise pub.Blocked('Frozen input changed')
        if op == 'update_existing' and pub.digest_file(self.work/'update-fields.json') != self.fields_sha256: raise pub.Blocked('Update fields changed after dry-run')
        if cli_identity() != self.cli_identity: raise pub.Blocked('CLI changed before mutation')
        self.state['pending']=op; self.save(); self.journal(op,'attempted')
        try: return self.provider.call(args)
        except pub.ProviderFailure as e:
            self.journal(op,'reconcile_required',diagnostics=e.diagnostics); raise

    def chapters(self,remote):
        role=self.m['artifacts'].get('audio_metadata_lineage')
        if not role: return None
        lineage=pub.read(self.package/role['path'])
        helper=pub.VALIDATOR.with_name('chapters.py')
        spec=importlib.util.spec_from_file_location('remote_chapters',helper); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        observed=m.read_chapters(pub.safe_url(remote['attributes']['media_url']))
        if observed != lineage['chapters']: raise pub.Blocked('Remote embedded chapters mismatch')
        return {'embedded':observed,'formatted_description':remote['attributes'].get('formatted_description'),'placeholder_used':'{{chapters}}' in self.payload['description']}


    def ready(self,remote_id):
        r=super().ready(remote_id)
        if r['attributes'].get('status')!='published' or r['attributes'].get('published_at')!=self.before['attributes'].get('published_at'): raise pub.Blocked('Published status/date changed')
        self.chapter_evidence=self.chapters(r)
        return r

    def run(self,mode='update-existing'):
        self.fresh()
        with pub.episode_lock(self.m['episode_key']):
            self.fresh()
            if mode=='plan': return {'status':'plan','remote_id':self.a['remote_id'],'replace_media':self.replace_media,**self.binding}
            self.work=self.state_root/pub.digest_bytes(self.m['episode_key'].encode());self.work.mkdir(parents=True,exist_ok=True)
            self.state_path=self.work/'state.json';self.snapshot=self.work/'upload-input.mp3'
            self.state=pub.read(self.state_path) if self.state_path.exists() else {'binding':self.update_binding,'remote_id':self.a['remote_id'],'pending':None}
            if self.state.get('binding')!=self.update_binding or self.state.get('remote_id')!=self.a['remote_id']: raise pub.Blocked('State binds another candidate/episode')
            if not self.snapshot.exists(): shutil.copyfile(self.audio,self.snapshot)
            if pub.digest_file(self.snapshot)!=self.binding['release_audio_sha256']: raise pub.Blocked('Snapshot changed')
            self.save();pub.persist(self.work/'before.json',{'data':self.before})
            # An unknown upload can never be retried. An unknown PATCH is only reconciled by GET.
            if self.state.get('pending')=='upload': raise pub.Blocked('Upload outcome unknown; reconcile before any retry')
            if self.state.get('pending')=='update_existing':
                r=self.ready(self.a['remote_id']);self.state.update(pending=None,status='updated_verified');self.save()
                return self.receipt('updated_reconciled',r)
            self.identity()
            if self.state.get('status')=='updated_verified': return self.receipt('already_updated_noop',self.ready(self.a['remote_id']))
            # Detect exact desired state; chapter evidence prevents ID3 changes from being skipped by PCM equality.
            try:
                r=self.ready(self.a['remote_id'])
            except pub.Blocked: r=None
            if r:
                self.state.update(status='updated_verified');self.save();return self.receipt('already_updated_noop',r)
            if self.replace_media and not self.state.get('audio_url'):
                uploaded=self.mutate('upload',['episodes','upload',str(self.snapshot),'--content-type','audio/mpeg'])
                self.state.update(audio_url=pub.safe_url(uploaded.get('audio_url')),pending=None);self.save();self.journal('upload','verified',audio_sha256=self.binding['release_audio_sha256'])
            fields=dict(self.payload)
            if self.replace_media: fields['audio_url']=self.state['audio_url']
            fieldfile=self.work/'update-fields.json';pub.persist(fieldfile,fields)
            # Fixed file content is checked immediately before its use; no long text in argv.
            self.fields_sha256=pub.digest_file(fieldfile)
            try:
                response=self.mutate('update_existing',['episodes','update',self.a['remote_id'],'--fields-file',str(fieldfile),'--fields-file-sha256',self.fields_sha256])
                if str(response.get('data',{}).get('id'))!=self.a['remote_id']: raise pub.ProviderFailure('PATCH returned wrong or missing ID')
                self.journal('update_existing','response_received',remote_id=self.a['remote_id'],fields_sha256=self.fields_sha256)
            except pub.ProviderFailure:
                r=self.ready(self.a['remote_id'])
            else: r=self.ready(self.a['remote_id'])
            self.state.update(pending=None,status='updated_verified');self.save()
            return self.receipt('updated_verified',r)

    def receipt(self,status,remote):
        result=super().receipt(status,remote)
        result.update(operation='update_existing',published_at=remote['attributes'].get('published_at'),previous_published_at=self.before['attributes'].get('published_at'),previous_media_url=self.before['attributes'].get('media_url'),chapters=getattr(self,'chapter_evidence',None),cli_commit=self.cli_identity['commit'],cli_identity=self.cli_identity,baseline=self.a['baseline'])
        pub.persist(self.work/'after.json',{'data':remote});pub.persist(self.work/'receipt.json',result)
        pub.persist(self.work/'rollback-inputs.json',{'remote_id':self.a['remote_id'],'show_id':self.m['show_id'],'old_audio_path':str(self.old_audio),'old_audio_sha256':pub.digest_file(self.old_audio),'old_payload':self.old_payload,'method':'Upload exact old local audio then PATCH this ID; dry-run and durable journal required; never use CDN audio_url directly.'})
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('package','authorization','state-dir'):p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--mode',choices=['plan','update-existing'],default='plan');p.add_argument('--artwork-verification',type=Path)
    p.add_argument('--transistor-cli',help='transistor executable (default: $TRANSISTOR_CLI, config transistor_cli, else PATH)')
    p.add_argument('--transistor-cli-repo',type=Path,help='Git source checkout containing the CLI (default: config transistor_cli_repo)')
    a=p.parse_args()
    pub.CLI=pub._podcast_tool(a.transistor_cli,'TRANSISTOR_CLI','transistor_cli','transistor');CLI_REPO=a.transistor_cli_repo
    try:
        c=UpdateController(a.package,a.authorization,a.state_dir,artwork_verification=a.artwork_verification,poll_count=12,poll_seconds=5)
        print(json.dumps(c.run(a.mode),ensure_ascii=False,indent=2))
    except (pub.Blocked,pub.ProviderFailure) as e:
        print(json.dumps({'status':'blocked','reason':str(e)}));sys.exit(1)
