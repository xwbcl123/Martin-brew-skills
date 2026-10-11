import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_publish as fixture
sys.modules['publish']=fixture.pub
spec=importlib.util.spec_from_file_location('updater',Path(__file__).resolve().parents[1]/'scripts/update_existing.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
pub=fixture.pub
class Provider(fixture.MockProvider):
 def fetch(self,url):return b"image", "image/png"
 def call(self,args):
  if args[1]!='update':return super().call(args)
  self.calls.append(args)
  if '--dry-run' in args:
   if self.timeout=='tamper':Path(args[args.index('--fields-file')+1]).write_text('{}')
   return {'dry_run':True}
  if self.timeout!='noapply':self.remote['attributes'].update(pub.read(args[args.index('--fields-file')+1]))
  if self.timeout in ('update','noapply'):raise pub.ProviderFailure('unknown PATCH')
  return {'data':copy.deepcopy(self.remote)}
class UpdateTests(unittest.TestCase):
 def setUp(self):
  fixture.PublishTests.setUp(self)
  old=self.root/'old';shutil.copytree(self.package,old)
  self.before={'data':{'id':'123','relationships':{'show':{'data':{'id':'12345'}}},'attributes':{**self.payload,'status':'published','published_at':'2026-09-01T00:00:00Z','audio_processing':False,'media_url':'https://example.test/audio.mp3'}}}
  pub.persist(self.root/'before.json',self.before)
  self.payload['description']='New listener paragraph'
  pub.persist(self.package/'payload.json',self.payload)
  a=self.m['artifacts']['transistor_payload'];a.update(sha256=pub.digest_file(self.package/'payload.json'),bytes=(self.package/'payload.json').stat().st_size)
  pub.persist(self.package/'episode.json',self.m)
  self.a.update(remote_id='123',allowed_operations=['readback','update_existing'],manifest_sha256=pub.digest_file(self.package/'episode.json'),payload_sha256=pub.digest_bytes(pub.canonical(self.payload)),baseline={'manifest_path':str(old/'episode.json'),'manifest_sha256':pub.digest_file(old/'episode.json'),'snapshot_path':str(self.root/'before.json'),'snapshot_sha256':pub.digest_file(self.root/'before.json')})
  self.a['cli_identity']={'commit':'fixture-cli','runtime_sha256':'f'*64};self.a['baseline']['remote_image_sha256']=pub.digest_bytes(b'image')
  pub.persist(self.auth,self.a);self.provider=Provider(self.payload);self.provider.remote=copy.deepcopy(self.before['data'])
  self.gitpatch=patch.object(up,'cli_identity',return_value=self.a['cli_identity']);self.gitpatch.start();self.addCleanup(self.gitpatch.stop)
 def tearDown(self):self.tmp.cleanup()
 def validator(self,package):return fixture.PublishTests.validator(self,package)
 def controller(self):return up.UpdateController(self.package,self.auth,self.root/'update-state',self.provider,self.validator,1,0)
 def mutations(self):return [a for a in self.provider.calls if a[1] in ('update','upload','publish','create') and '--dry-run' not in a]
 def test_update_file_input_then_noop_same_id(self):
  r=self.controller().run();self.assertEqual(r['remote_id'],'123');self.assertEqual(r['status'],'updated_verified');self.assertEqual([a[1] for a in self.mutations()],['update'])
  args=self.mutations()[0];self.assertIn('--fields-file',args);self.assertNotIn('--set',args)
  self.assertIn(args+['--dry-run'],self.provider.calls)
  self.assertEqual(self.controller().run()['status'],'already_updated_noop');self.assertEqual(len(self.mutations()),1)
 def test_timeout_after_apply_reconciles_no_retry(self):
  self.provider.timeout='update';r=self.controller().run();self.assertEqual(r['status'],'updated_verified');self.assertEqual(len(self.mutations()),1)
 def test_timeout_without_apply_never_retries(self):
  self.provider.timeout='noapply'
  for _ in range(2):
   with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual(len(self.mutations()),1)
 def test_wrong_show_date_audio_zero_mutations(self):
  for field,value in [('published_at','other'),('title','other'),('status','draft')]:
   self.provider.remote=copy.deepcopy(self.before['data']);self.provider.remote['attributes'][field]=value
   with self.assertRaises(pub.Blocked):self.controller().run()
  self.provider.remote=copy.deepcopy(self.before['data']);self.provider.remote['relationships']['show']['data']['id']='99'
  with self.assertRaises(pub.Blocked):self.controller().run()
  self.provider.remote=copy.deepcopy(self.before['data']);self.provider.media_bytes=b'wrong audio'
  with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual(self.mutations(),[])
 def test_concurrent_transcript_artwork_rejected(self):
  for field in ('transcript_text','image_url'):
   self.provider.remote=copy.deepcopy(self.before['data']);self.provider.remote['attributes'][field]='changed'
   with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual(self.mutations(),[])
 def test_cli_drift_rejected(self):
  with patch.object(up,'cli_identity',return_value={'commit':'wrong','runtime_sha256':'e'*64}):
   with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual(self.mutations(),[])
 def test_changed_artwork_then_noop(self):
  self.payload['image_url']='https://example.test/new.png'
  (self.package/'new.png').write_bytes(b'new-image')
  self.m['artifacts']['artwork']={'path':'new.png','sha256':pub.digest_bytes(b'new-image'),'bytes':9}
  pub.persist(self.package/'payload.json',self.payload)
  self.m['artifacts']['transistor_payload'].update(sha256=pub.digest_file(self.package/'payload.json'),bytes=(self.package/'payload.json').stat().st_size)
  pub.persist(self.package/'episode.json',self.m)
  self.a.update(manifest_sha256=pub.digest_file(self.package/'episode.json'),payload_sha256=pub.digest_bytes(pub.canonical(self.payload)))
  pub.persist(self.auth,self.a)
  self.provider.fetch=lambda url:(b'new-image' if url.endswith('/new.png') else b'image','image/png')
  self.assertEqual(self.controller().run()['status'],'updated_verified')
  self.assertEqual(self.controller().run()['status'],'already_updated_noop')
  self.assertEqual(len(self.mutations()),1)
 def test_authority_change_cannot_resume_state(self):
  self.provider.timeout='noapply'
  with self.assertRaises(pub.Blocked):self.controller().run()
  self.a['authorization_id']='different-authority';pub.persist(self.auth,self.a)
  with self.assertRaisesRegex(pub.Blocked,'State binds'):self.controller().run()
  self.assertEqual(len(self.mutations()),1)
 def test_field_tamper_after_dryrun_zero_mutations(self):
  self.provider.timeout='tamper'
  with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual(self.mutations(),[])

 def media_fixture(self):
  # Bytes stand in for an ID3-only revision. PCM evidence and the chapter probe
  # are explicit test doubles; no codec or network claim is made by this fixture.
  new_audio=b'mocked audio fixture with replacement chapter tags'
  (self.package/'audio.mp3').write_bytes(new_audio)
  art=self.m['artifacts']['delivery_audio'];art.update(sha256=pub.digest_bytes(new_audio),bytes=len(new_audio))
  expected=[{'start_ms':0,'end_ms':1000,'title':'Opening'}]
  pub.persist(self.package/'lineage.json',{'chapters':expected})
  self.m['artifacts']['audio_metadata_lineage']={'path':'lineage.json','sha256':pub.digest_file(self.package/'lineage.json'),'bytes':(self.package/'lineage.json').stat().st_size,'parents':[]}
  pub.persist(self.package/'episode.json',self.m)
  self.a.update(manifest_sha256=pub.digest_file(self.package/'episode.json'),release_audio_sha256=pub.digest_bytes(new_audio),allowed_operations=['readback','update_existing','upload','replace_media'])
  pub.persist(self.auth,self.a)
  observed=self.root/'mock-remote-chapters.json';pub.persist(observed,[])
  helpers=self.root/'mock-chapter-probe';helpers.mkdir()
  (helpers/'chapters.py').write_text('import json\nfrom pathlib import Path\ndef read_chapters(url):\n return json.loads(Path('+repr(str(observed))+').read_text())\n')
  probe_patch=patch.object(pub,'VALIDATOR',helpers/'package.py');probe_patch.start();self.addCleanup(probe_patch.stop)
  outer=self
  class MediaProvider(Provider):
   def __init__(self):
    super().__init__(outer.payload);self.remote=copy.deepcopy(outer.before['data'])
    self.pause_before_patch=False;self.processing=False;self.bad_media=False;self.bad_chapters=False
    self.patch_used_persisted_url=False
   def fetch_media(self,url,expected_bytes,source_path=None):
    result=super().fetch_media(url,expected_bytes,source_path)
    if self.media_bytes in (b'mocked audio fixture',new_audio):
     result['exact_pcm']={'source':{'sha256':'same-acoustic-track','frames':1000},'remote':{'sha256':'same-acoustic-track','frames':1000}}
    return result
   def call(self,args):
    if args[1]=='update' and '--dry-run' in args and self.pause_before_patch:
     self.pause_before_patch=False
     raise pub.Blocked('mock interruption after durable upload receipt')
    if args[1]=='update' and '--dry-run' not in args:
     fieldfile=Path(args[args.index('--fields-file')+1]);fields=pub.read(fieldfile)
     durable=pub.read(fieldfile.parent/'state.json')
     self.patch_used_persisted_url=fields['audio_url']==durable['audio_url']=='https://uploads.transistor.fm/unique.mp3'
     result=super().call(args)
     self.remote['attributes'].update(media_url='https://media.transistor.fm/new-tags.mp3',audio_processing=self.processing)
     self.media_bytes=b'wrong unrelated audio' if self.bad_media else new_audio
     pub.persist(observed,[] if self.bad_chapters else expected)
     return {'data':copy.deepcopy(self.remote)}
    return super().call(args)
  self.provider=MediaProvider()
  return expected

 def test_replace_media_upload_patch_and_persisted_url(self):
  expected=self.media_fixture()
  result=self.controller().run()
  self.assertEqual(result['status'],'updated_verified');self.assertEqual(result['remote_id'],'123')
  self.assertEqual([a[1] for a in self.mutations()],['upload','update'])
  self.assertTrue(self.provider.patch_used_persisted_url)
  self.assertEqual(result['chapters']['embedded'],expected)
  for args in self.mutations():self.assertIn(args+['--dry-run'],self.provider.calls)
  self.assertEqual(self.controller().run()['status'],'already_updated_noop')
  self.assertEqual(len(self.mutations()),2)

 def test_replace_media_requires_both_additional_operations(self):
  self.media_fixture()
  for missing in ('upload','replace_media'):
   pub.persist(self.auth,{**self.a,'allowed_operations':[x for x in self.a['allowed_operations'] if x!=missing]})
   with self.assertRaisesRegex(pub.Blocked,'Media replacement not authorized'):self.controller().run()
  self.assertEqual(self.provider.calls,[])

 def test_replace_media_unknown_upload_never_retries_across_runs(self):
  self.media_fixture();self.provider.timeout='upload'
  with self.assertRaises(pub.ProviderFailure):self.controller().run()
  self.provider.timeout=None
  for _ in range(2):
   with self.assertRaisesRegex(pub.Blocked,'Upload outcome unknown'):self.controller().run()
  self.assertEqual([a[1] for a in self.mutations()],['upload'])
  state=pub.read(next((self.root/'update-state').glob('*/state.json')))
  self.assertEqual(state['pending'],'upload');self.assertNotIn('audio_url',state)

 def test_replace_media_resumes_known_upload_without_reupload(self):
  self.media_fixture();self.provider.pause_before_patch=True
  with self.assertRaisesRegex(pub.Blocked,'mock interruption'):self.controller().run()
  state=pub.read(next((self.root/'update-state').glob('*/state.json')))
  self.assertEqual(state['audio_url'],'https://uploads.transistor.fm/unique.mp3');self.assertIsNone(state['pending'])
  self.assertEqual(self.controller().run()['status'],'updated_verified')
  self.assertTrue(self.provider.patch_used_persisted_url)
  self.assertEqual([a[1] for a in self.mutations()],['upload','update'])

 def test_replace_media_processing_pending_never_verified_or_repatched(self):
  self.media_fixture();self.provider.processing=True
  for _ in range(2):
   with self.assertRaisesRegex(pub.Blocked,'processing is pending'):self.controller().run()
  statefile=next((self.root/'update-state').glob('*/state.json'));state=pub.read(statefile)
  self.assertEqual(state['pending'],'update_existing');self.assertNotEqual(state.get('status'),'updated_verified')
  self.assertFalse((statefile.parent/'receipt.json').exists())
  self.assertEqual([a[1] for a in self.mutations()],['upload','update'])
  self.provider.remote['attributes']['audio_processing']=False
  self.assertEqual(self.controller().run()['status'],'updated_reconciled')
  self.assertEqual(len(self.mutations()),2)

 def test_replace_media_wrong_new_audio_never_verified_or_repatched(self):
  self.media_fixture();self.provider.bad_media=True
  for _ in range(2):
   with self.assertRaisesRegex(pub.Blocked,'audio identity mismatch'):self.controller().run()
  statefile=next((self.root/'update-state').glob('*/state.json'));state=pub.read(statefile)
  self.assertEqual(state['pending'],'update_existing');self.assertNotEqual(state.get('status'),'updated_verified')
  self.assertFalse((statefile.parent/'receipt.json').exists())
  self.assertEqual([a[1] for a in self.mutations()],['upload','update'])

 def test_replace_media_remote_chapter_mismatch_never_verified(self):
  self.media_fixture();self.provider.bad_chapters=True
  for _ in range(2):
   with self.assertRaisesRegex(pub.Blocked,'Remote embedded chapters mismatch'):self.controller().run()
  statefile=next((self.root/'update-state').glob('*/state.json'));state=pub.read(statefile)
  self.assertEqual(state['pending'],'update_existing');self.assertNotEqual(state.get('status'),'updated_verified')
  self.assertFalse((statefile.parent/'receipt.json').exists())
  self.assertEqual([a[1] for a in self.mutations()],['upload','update'])
if __name__=='__main__':unittest.main()

class ReadingComparisonTests(unittest.TestCase):
 def test_transport_and_blank_lines_only(self):
  m={'publication_transcript':{'version':1,'source':'reading_transcript'}};expected='甲段。\n\n乙段。'
  for actual,method in [(expected,'exact'),('\ufeff甲段。\r\n\r\n乙段。','exact'),(expected+'\n','terminal_newline'),('甲段。\n乙段。','blank_line_normalization'),('甲段。\n \n\n乙段。\n\n','blank_line_normalization')]:
   self.assertEqual(up.transcript_match(actual,expected,m),method)
  for actual in ['甲段。乙段。','甲段。\n\n丙段。','甲段。','甲 段。\n\n乙段。',' 甲段。\n\n乙段。']:
   self.assertIsNone(up.transcript_match(actual,expected,m))
  self.assertIsNone(up.transcript_match('甲段。\n乙段。',expected,{}))

class ReadingUpdateTests(unittest.TestCase):
 tearDown=UpdateTests.tearDown
 validator=UpdateTests.validator
 controller=UpdateTests.controller
 mutations=UpdateTests.mutations
 def setUp(self):
  UpdateTests.setUp(self)
  self.m['publication_transcript']={'version':1,'source':'reading_transcript'}
  self.payload['transcript_text']='第一段整理阅读稿。\n\n第二段整理阅读稿。'
  pub.persist(self.package/'payload.json',self.payload)
  self.m['artifacts']['transistor_payload'].update(sha256=pub.digest_file(self.package/'payload.json'),bytes=(self.package/'payload.json').stat().st_size)
  pub.persist(self.package/'episode.json',self.m)
  self.a.update(manifest_sha256=pub.digest_file(self.package/'episode.json'),payload_sha256=pub.digest_bytes(pub.canonical(self.payload)))
  pub.persist(self.auth,self.a)
 def test_blank_line_normalization_then_identity_noop(self):
  call=self.provider.call
  def normalize(args):
   result=call(args)
   if args[1]=='update' and '--dry-run' not in args:self.provider.remote['attributes']['transcript_text']=self.payload['transcript_text'].replace('\n\n','\n')
   return result
  self.provider.call=normalize
  r=self.controller().run();self.assertEqual(r['transcript_verification']['comparison'],'blank_line_normalization')
  self.assertEqual(self.controller().run()['status'],'already_updated_noop')
  self.assertEqual([a[1] for a in self.mutations()],['update'])
 def test_changed_words_after_patch_never_retried(self):
  call=self.provider.call
  def corrupt(args):
   result=call(args)
   if args[1]=='update' and '--dry-run' not in args:self.provider.remote['attributes']['transcript_text']='Changed words'
   return result
  self.provider.call=corrupt
  for _ in range(2):
   with self.assertRaises(pub.Blocked):self.controller().run()
  self.assertEqual([a[1] for a in self.mutations()],['update'])


class CliIdentityLayoutTests(unittest.TestCase):
 """cli_identity locates the CLI source checkout explicitly; the executable must live inside it."""
 def make_repo(self, root, dirty=False):
  repo=root/'cli'; (repo/'src').mkdir(parents=True); (repo/'.venv/bin').mkdir(parents=True)
  (repo/'src/a.py').write_text('x=1\n'); (repo/'pyproject.toml').write_text('[project]\nname="t"\n'); (repo/'.venv/bin/transistor').write_text('#!/bin/sh\n')
  git=lambda *a: subprocess.run(['git','-C',str(repo),*a],check=True,capture_output=True)
  git('init','-q'); git('add','-A'); git('-c','user.name=t','-c','user.email=t@example.test','commit','-qm','init')
  if dirty: (repo/'src/a.py').write_text('x=2\n')
  return repo
 def identity(self, repo, cli):
  empty=Path(tempfile.mkdtemp())/'c.json'; empty.write_text('{}')
  with patch.object(up,'CLI_REPO',repo), patch.object(pub,'CLI',str(cli)), patch.dict(os.environ,{'PODCAST_CONFIG':str(empty)}):
   return up.cli_identity()
 def test_supported_layout_yields_commit_and_runtime_hash(self):
  with tempfile.TemporaryDirectory() as t:
   repo=self.make_repo(Path(t)); ident=self.identity(repo,repo/'.venv/bin/transistor')
   self.assertEqual(len(ident['commit']),40); self.assertEqual(len(ident['runtime_sha256']),64)
 def test_repo_from_config_when_flag_absent(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); repo=self.make_repo(root); cfg=root/'c.json'; cfg.write_text(json.dumps({'transistor_cli_repo':str(repo)}))
   with patch.object(up,'CLI_REPO',None), patch.object(pub,'CLI',str(repo/'.venv/bin/transistor')), patch.dict(os.environ,{'PODCAST_CONFIG':str(cfg)}):
    self.assertEqual(len(up.cli_identity()['commit']),40)
 def test_missing_repo_is_blocked_not_guessed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); repo=self.make_repo(root); empty=root/'e.json'; empty.write_text('{}')
   with patch.object(up,'CLI_REPO',None), patch.object(pub,'CLI',str(repo/'.venv/bin/transistor')), patch.dict(os.environ,{'PODCAST_CONFIG':str(empty)}):
    with self.assertRaises(pub.Blocked): up.cli_identity()
 def test_executable_outside_repo_is_unsupported(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); repo=self.make_repo(root); other=root/'bin'; other.mkdir(); (other/'transistor').write_text('#!/bin/sh\n')
   with self.assertRaises(pub.Blocked): self.identity(repo,other/'transistor')
 def test_repo_without_src_is_unsupported(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); bare=root/'bare'; (bare/'.git').mkdir(parents=True); (bare/'bin').mkdir()
   with self.assertRaises(pub.Blocked): self.identity(bare,bare/'bin/transistor')
 def test_dirty_worktree_is_blocked(self):
  with tempfile.TemporaryDirectory() as t:
   repo=self.make_repo(Path(t),dirty=True)
   with self.assertRaises(pub.Blocked): self.identity(repo,repo/'.venv/bin/transistor')
 def test_symlinked_executable_pointing_outside_the_checkout_is_unsupported(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); repo=self.make_repo(root); outside=root/'elsewhere'; outside.mkdir(); (outside/'real').write_text('#!/bin/sh\n'); (outside/'real').chmod(0o755)
   link=repo/'.venv/bin/linked'; link.symlink_to(outside/'real')
   with self.assertRaises(pub.Blocked): self.identity(repo,link)
 def test_relative_cli_value_is_rejected_before_any_identity_check(self):
  with tempfile.TemporaryDirectory() as t:
   empty=Path(t)/'c.json'; empty.write_text('{}')
   with patch.dict(os.environ,{'PODCAST_CONFIG':str(empty),'TRANSISTOR_CLI':'transistor'}):
    with patch.object(pub,'CLI',None):
     with self.assertRaises(SystemExit): pub.cli_path()
 def test_relative_checkout_value_is_blocked_not_resolved_against_cwd(self):
  with tempfile.TemporaryDirectory() as t:
   repo=self.make_repo(Path(t)); old=os.getcwd()
   try:
    os.chdir(repo.parent)
    with self.assertRaises(pub.Blocked): self.identity(Path('cli'),repo/'.venv/bin/transistor')
   finally: os.chdir(old)
