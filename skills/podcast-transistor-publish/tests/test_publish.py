import copy
import importlib.util
import json
import io
import subprocess
import shutil
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / 'scripts/publish.py'
spec = importlib.util.spec_from_file_location('publisher', PATH)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def lock_child(key, queue):
    try:
        with pub.episode_lock(key):
            queue.put('acquired')
    except pub.Blocked:
        queue.put('blocked')


class MockProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.remote = None
        self.timeout = None
        self.lose_created = False
        self.stay_draft = False
        self.mismatch = None
        self.media_bytes = b'mocked audio fixture'

    def fetch_media(self, url, expected_bytes, source_path=None):
        return {'sha256': pub.digest_bytes(self.media_bytes), 'bytes': len(self.media_bytes), 'mime': 'audio/mpeg'}

    @property
    def mutations(self):
        return [a for a in self.calls if a[1] in ('upload', 'create', 'publish') and '--dry-run' not in a]

    def call(self, args):
        self.calls.append(args)
        op = args[1]
        if '--dry-run' in args:
            return {'dry_run': True}
        if op == 'upload':
            if self.timeout == op:
                raise pub.ProviderFailure('mock unknown upload')
            return {'audio_url': 'https://uploads.transistor.fm/unique.mp3'}
        if op == 'create':
            self.remote = {'id': '123', 'relationships': {'show': {'data': {'id': '82408'}}},
                           'attributes': {**self.payload, 'status': 'draft', 'audio_processing': False,
                                          'audio_url': 'https://uploads.transistor.fm/unique.mp3'}}
            if self.mismatch:
                self.remote['attributes'][self.mismatch] = 'unexpected'
            if self.timeout == op:
                if self.lose_created:
                    self.remote = None
                raise pub.ProviderFailure('mock create timeout')
            return {'data': copy.deepcopy(self.remote)}
        if op == 'publish':
            if not self.stay_draft:
                self.remote['attributes']['status'] = 'published'
            if self.timeout == op:
                raise pub.ProviderFailure('mock publish timeout')
            return {'data': copy.deepcopy(self.remote)}
        if op == 'get':
            return {'data': copy.deepcopy(self.remote)}
        if op == 'list':
            return {'data': [copy.deepcopy(self.remote)] if self.remote else []}
        raise AssertionError(args)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.package = self.root / 'pkg'
        self.package.mkdir()
        self.payload = dict(title='Fixture title', summary='Summary', description='AI synthetic voice disclosed',
                            author='Martin', explicit=False, type='full', number=1, season=1,
                            image_url='https://example.test/cover.png', transcript_text='Exact transcript')
        (self.package / 'audio.mp3').write_bytes(b'mocked audio fixture')
        pub.persist(self.package / 'payload.json', self.payload)
        def artifact(name):
            p = self.package / name
            return {'path': name, 'sha256': pub.digest_file(p), 'bytes': p.stat().st_size, 'parents': []}
        self.m = {'contract_version': '2.0', 'review_mode': 'delegated_release', 'episode_key': self.tmp.name,
                  'show_id': '82408', 'package_revision': 2,
                  'artifacts': {'delivery_audio': artifact('audio.mp3'), 'transistor_payload': artifact('payload.json')}}
        pub.persist(self.package / 'episode.json', self.m)
        pub.persist(self.package / 'seal.json', {'fixture_only': True})
        self.runtime = self.root / 'runtime.py'
        self.runtime.write_text('original runtime')
        self.runtime_patch = patch.object(pub, 'validation_runtime_files', return_value=[self.runtime])
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.auth = self.root / 'authority.json'
        self.a = {'contract_version': '2.0', 'actor': 'user', 'revoked': False, 'authorization_id': 'fixture-auth',
                  'source_ref': 'test:original-user-message', 'original_user_quote': 'Publish this fixture.',
                  'source_ref_kind': 'original_user_message', 'episode_key': self.m['episode_key'], 'show_id': '82408',
                  'package_revision': 2, 'manifest_sha256': pub.digest_file(self.package / 'episode.json'),
                  'release_audio_sha256': pub.digest_file(self.package / 'audio.mp3'),
                  'payload_sha256': pub.digest_bytes(pub.canonical(self.payload)),
                  'allowed_operations': sorted(pub.OPS)}
        pub.persist(self.auth, self.a)
        self.provider = MockProvider(self.payload)
        self.validator_calls = 0

    def tearDown(self):
        self.tmp.cleanup()

    def validator(self, package):
        self.validator_calls += 1
        return {'valid': True, 'audio_sha256': pub.digest_file(package / 'audio.mp3'),
                'payload_sha256': pub.digest_bytes(pub.canonical(pub.read(package / 'payload.json')))}

    def controller(self):
        return pub.Controller(self.package, self.auth, self.root / 'state', self.provider, self.validator, 1, 0)

    def test_success_fresh_and_dry_runs(self):
        result = self.controller().run('publish')
        self.assertEqual(result['status'], 'published_verified')
        self.assertEqual([a[1] for a in self.provider.mutations], ['upload', 'create', 'publish'])
        self.assertEqual(self.validator_calls, 1)
        for mutation in self.provider.mutations:
            i = self.provider.calls.index(mutation)
            self.assertEqual(self.provider.calls[i - 1], mutation + ['--dry-run'])

    def test_missing_authority_zero_calls(self):
        self.auth.unlink()
        with self.assertRaises(OSError):
            self.controller().run('publish')
        self.assertEqual(self.provider.calls, [])

    def test_wrong_bindings_zero_mutations(self):
        for key, value in [('show_id', '70870'), ('payload_sha256', 'wrong'), ('release_audio_sha256', 'wrong'),
                           ('manifest_sha256', 'wrong'), ('episode_key', 'other'), ('package_revision', 3),
                           ('revoked', True), ('source_ref_kind', 'paraphrase'), ('allowed_operations', ['readback'])]:
            with self.subTest(key=key):
                pub.persist(self.auth, {**self.a, key: value})
                with self.assertRaises(pub.Blocked):
                    self.controller().run('publish')
                self.assertEqual(self.provider.mutations, [])

    def test_v1_agent_draft_rejected(self):
        for version, mode in [('1.0', 'delegated_release'), ('2.0', 'agent_draft')]:
            pub.persist(self.package / 'episode.json', {**self.m, 'contract_version': version, 'review_mode': mode})
            with self.assertRaises(pub.Blocked):
                self.controller().run('publish')
        self.assertEqual(self.provider.calls, [])

    def test_lock_across_processes(self):
        ctx = multiprocessing.get_context('fork')
        queue = ctx.Queue()
        with pub.episode_lock(self.m['episode_key']):
            child = ctx.Process(target=lock_child, args=(self.m['episode_key'], queue))
            child.start()
            child.join(5)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(queue.get(timeout=1), 'blocked')

    def test_upload_timeout_not_retried(self):
        self.provider.timeout = 'upload'
        with self.assertRaises(pub.ProviderFailure):
            self.controller().run('publish')
        with self.assertRaisesRegex(pub.Blocked, 'upload outcome unknown'):
            self.controller().run('publish')
        self.assertEqual(len(self.provider.mutations), 1)

    def test_create_timeout_reconciles_causal_audio_url(self):
        self.provider.timeout = 'create'
        self.assertEqual(self.controller().run('publish')['status'], 'published_verified')
        self.assertEqual(sum(a[1] == 'create' for a in self.provider.mutations), 1)

    def test_create_timeout_no_match_stays_blocked(self):
        self.provider.timeout = 'create'
        self.provider.lose_created = True
        for _ in range(2):
            with self.assertRaisesRegex(pub.Blocked, 'cannot be uniquely identified'):
                self.controller().run('publish')
        self.assertEqual(sum(a[1] == 'create' for a in self.provider.mutations), 1)

    def test_publish_timeout_reconciles(self):
        self.provider.timeout = 'publish'
        self.assertEqual(self.controller().run('publish')['status'], 'published_verified')
        self.assertEqual(sum(a[1] == 'publish' for a in self.provider.mutations), 1)

    def test_publish_timeout_draft_no_retry(self):
        self.provider.timeout = 'publish'
        self.provider.stay_draft = True
        for _ in range(2):
            with self.assertRaisesRegex(pub.Blocked, 'publish outcome unconfirmed'):
                self.controller().run('publish')
        self.assertEqual(sum(a[1] == 'publish' for a in self.provider.mutations), 1)

    def test_already_published_noop(self):
        self.controller().run('publish')
        self.provider.calls.clear()
        self.assertEqual(self.controller().run('publish')['status'], 'already_published_noop')
        self.assertEqual(self.provider.mutations, [])
        self.assertEqual(self.provider.calls[0], ['episodes', 'get', '123'])

    def test_metadata_image_transcript_mismatch_blocks_publish(self):
        for key in ('image_url', 'description', 'transcript_text'):
            with self.subTest(key=key):
                self.provider = MockProvider(self.payload)
                self.provider.mismatch = key
                controller = self.controller()
                controller.state_root = self.root / ('state-' + key)
                with self.assertRaisesRegex(pub.Blocked, 'payload mismatch: ' + key):
                    controller.run('publish')
                self.assertFalse(any(a[1] == 'publish' for a in self.provider.mutations))

    def test_changed_package_after_dryrun_blocks_mutation(self):
        original = self.provider.call
        def call(args):
            result = original(args)
            if args[1] == 'upload' and '--dry-run' in args:
                (self.package / 'audio.mp3').write_bytes(b'changed')
            return result
        self.provider.call = call
        with self.assertRaises(pub.Blocked):
            self.controller().run('publish')
        self.assertEqual(self.provider.mutations, [])

    def test_existing_remote_wrong_audio_zero_mutations(self):
        self.provider.call(['episodes', 'create'])
        self.provider.calls.clear()
        self.provider.media_bytes = b'completely different podcast audio'
        pub.persist(self.auth, {**self.a, 'remote_id': '123'})
        with self.assertRaisesRegex(pub.Blocked, 'audio identity mismatch'):
            self.controller().run('publish')
        self.assertEqual(self.provider.mutations, [])

    def test_new_draft_wrong_remote_audio_never_publishes(self):
        self.provider.media_bytes = b'other audio despite same metadata'
        with self.assertRaisesRegex(pub.Blocked, 'audio identity mismatch'):
            self.controller().run('publish')
        self.assertEqual([a[1] for a in self.provider.mutations], ['upload', 'create'])

    def test_already_published_wrong_remote_audio_not_noop(self):
        self.controller().run('publish')
        self.provider.calls.clear()
        self.provider.media_bytes = b'changed after publish'
        with self.assertRaisesRegex(pub.Blocked, 'audio identity mismatch'):
            self.controller().run('publish')
        self.assertEqual(self.provider.mutations, [])

    def test_shared_validator_requires_seal(self):
        with patch.object(pub.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=b'{"valid":true}')) as run:
            pub.validate_release(self.package)
        self.assertIn('--require-seal', run.call_args.args[0])
        with patch.object(pub.subprocess, 'run', return_value=SimpleNamespace(returncode=2, stdout=b'{"valid":false}')):
            with self.assertRaisesRegex(pub.Blocked, 'release validation failed'):
                pub.validate_release(self.package)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg required')
    def test_real_mp3_tags_preserve_exact_pcm_but_different_audio_fails(self):
        source = self.root / 'source.mp3'
        tagged = self.root / 'tagged.mp3'
        other = self.root / 'other.mp3'
        for frequency, path in [(440, source), (660, other)]:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                            f'sine=frequency={frequency}:duration=1', '-c:a', 'libmp3lame', str(path)], check=True)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), '-c:a', 'copy',
                        '-metadata', 'title=Different ID3 metadata', str(tagged)], check=True)
        self.assertNotEqual(pub.digest_file(source), pub.digest_file(tagged))
        class Response(io.BytesIO):
            url = 'https://media.transistor.fm/fixture.mp3'
            headers = SimpleNamespace(get_content_type=lambda: 'audio/mpeg')
        with patch.object(pub, 'urlopen', return_value=Response(tagged.read_bytes())):
            evidence = pub.CLIProvider().fetch_media(Response.url, source.stat().st_size, source)
        self.assertEqual(evidence['exact_pcm']['source'], evidence['exact_pcm']['remote'])
        self.assertEqual(evidence['exact_pcm']['source']['sample_rate'], 44100)
        with patch.object(pub, 'urlopen', return_value=Response(other.read_bytes())):
            with self.assertRaisesRegex(pub.Blocked, 'decoded PCM differs'):
                pub.CLIProvider().fetch_media(Response.url, source.stat().st_size, source)

    def test_cli_http_timeout_and_sanitized_error(self):
        response = SimpleNamespace(returncode=6, stdout=b'', stderr=json.dumps({'error': {
            'code': 'network_error', 'exit_code': 6, 'status': 504,
            'message': 'https://secret.test/upload?token=NEVER_LOG',
            'details': {'api_key': 'NEVER_LOG'}}}).encode())
        with patch.object(pub.subprocess, 'run', return_value=response) as run:
            with self.assertRaises(pub.ProviderFailure) as raised:
                pub.CLIProvider(http_timeout=300).call(['episodes', 'upload', 'fixture.mp3'])
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index('--timeout') + 1], '300')
        self.assertEqual(argv[argv.index('--max-retries') + 1], '0')
        self.assertGreater(run.call_args.kwargs['timeout'], 300)
        self.assertEqual(raised.exception.diagnostics,
                         {'returncode': 6, 'code': 'network_error', 'exit_code': 6, 'http_status': 504})
        self.assertNotIn('NEVER_LOG', str(raised.exception) + json.dumps(raised.exception.diagnostics))

    def test_cache_hash_closure_invalidates_each_dependency(self):
        extra = self.package / 'extra.bin'
        extra.write_bytes(b'original artifact')
        review = self.package / 'review.json'
        shot = self.package / 'shot.png'
        shot.write_bytes(b'screenshot')
        pub.persist(review, {'decision': 'approved', 'screenshots': [{'path': shot.name, 'sha256': pub.digest_file(shot)}]})
        source = self.root / 'original.wav'
        source.write_bytes(b'original source')
        derived = self.package / 'derived-source.wav'
        derived.write_bytes(b'derived source')
        lineage = self.package / 'lineage.json'
        pub.persist(lineage, {'evidence': {'source': {'path': derived.name, 'sha256': pub.digest_file(derived)}}})
        self.m['artifacts'].update(extra={'path': extra.name, 'sha256': pub.digest_file(extra)},
                                   edit_lineage={'path': lineage.name, 'sha256': pub.digest_file(lineage)})
        self.m['reviews'] = [review.name]
        self.m['sources'] = [{'path': str(source), 'sha256': pub.digest_file(source)}]
        pub.persist(self.package / 'episode.json', self.m)
        self.a['manifest_sha256'] = pub.digest_file(self.package / 'episode.json')
        pub.persist(self.auth, self.a)
        for changed in [extra, review, shot, source, derived, self.runtime, self.package / 'seal.json']:
            with self.subTest(changed=changed.name):
                old = changed.read_bytes()
                controller = self.controller()
                self.validator_calls = 0
                controller.fresh()
                controller.fresh()
                self.assertEqual(self.validator_calls, 1)
                # Preserve valid JSON where the closure must parse a review.
                changed.write_bytes(b'{"decision":"rejected","screenshots":[]}' if changed == review else old + b' ')
                original_validator = controller.validator
                def rejecting(package):
                    result = original_validator(package)
                    result['valid'] = False
                    return result
                controller.validator = rejecting
                with self.assertRaises(pub.Blocked):
                    controller.fresh()
                self.assertEqual(self.validator_calls, 2)
                changed.write_bytes(old)

    def test_validation_changed_during_full_run_not_cached(self):
        controller = self.controller()
        original_validator = controller.validator
        def changing(package):
            result = original_validator(package)
            self.runtime.write_text('changed during validation')
            return result
        controller.validator = changing
        with self.assertRaisesRegex(pub.Blocked, 'inputs changed during full verification'):
            controller.fresh()
        self.assertIsNone(controller._validation_cache)

    def test_cached_full_validation_never_bypasses_auth_revocation(self):
        controller = self.controller()
        controller.fresh()
        pub.persist(self.auth, {**self.a, 'revoked': True})
        with self.assertRaisesRegex(pub.Blocked, 'revoked'):
            controller.fresh()
        self.assertEqual(self.provider.mutations, [])

    def transformed_fixture(self):
        art = self.package / 'cover.png'
        art.write_bytes(b'fixture original image')
        self.m['artifacts']['artwork'] = {'path': art.name, 'sha256': pub.digest_file(art), 'bytes': art.stat().st_size, 'parents': []}
        pub.persist(self.package / 'episode.json', self.m)
        self.a['manifest_sha256'] = pub.digest_file(self.package / 'episode.json')
        pub.persist(self.auth, self.a)
        original = self.provider.call
        def call(args):
            result = original(args)
            if args[1] == 'create' and '--dry-run' not in args:
                attrs = self.provider.remote['attributes']
                attrs['image_url'] = 'https://img.transistorcdn.com/converted.webp'
                attrs['media_url'] = attrs.pop('audio_url')
                attrs.pop('transcript_text')
                attrs['transcripts'] = [{'format': 'txt', 'url': 'https://share.transistor.fm/test/transcript.txt'}]
                return {'data': copy.deepcopy(self.provider.remote)}
            return result
        self.provider.call = call
        def fetch(url):
            if url.endswith('.txt'):
                return self.payload['transcript_text'].encode(), 'text/plain'
            return b'fixture transformed image', 'image/webp'
        self.provider.fetch = fetch
        proof = {'contract_version': '2.0', 'episode_key': self.m['episode_key'], 'show_id': '82408',
                 'package_revision': 2, 'remote_id': '123', 'source_image_url': self.payload['image_url'],
                 'source_image_sha256': pub.digest_file(art), 'remote_image_url': 'https://img.transistorcdn.com/converted.webp',
                 'remote_image_sha256': pub.digest_bytes(b'fixture transformed image'),
                 'verification_method': 'independent_visual_review', 'verified': True,
                 'reviewer_id': 'fixture-independent-reviewer', 'source_ref': 'fixture:review'}
        path = self.root / 'art-review.json'
        pub.persist(path, proof)
        return path

    def test_transformed_art_waits_for_receipt_then_resumes_same_id(self):
        proof = self.transformed_fixture()
        with self.assertRaisesRegex(pub.Blocked, 'independent artwork verification required'):
            self.controller().run('publish')
        self.assertEqual([a[1] for a in self.provider.mutations], ['upload', 'create'])
        controller = self.controller()
        controller.artwork_verification = proof
        self.assertEqual(controller.run('publish')['status'], 'published_verified')
        self.assertEqual([a[1] for a in self.provider.mutations], ['upload', 'create', 'publish'])

    def test_transformed_art_changed_hash_blocks(self):
        proof = self.transformed_fixture()
        data = pub.read(proof)
        data['remote_image_sha256'] = 'wrong'
        pub.persist(proof, data)
        controller = self.controller()
        controller.artwork_verification = proof
        with self.assertRaisesRegex(pub.Blocked, 'remote content changed'):
            controller.run('publish')
        self.assertFalse(any(a[1] == 'publish' for a in self.provider.mutations))

    def test_remote_transcript_mismatch_blocks(self):
        proof = self.transformed_fixture()
        original = self.provider.fetch
        self.provider.fetch = lambda url: (b'wrong transcript', 'text/plain') if url.endswith('.txt') else original(url)
        controller = self.controller()
        controller.artwork_verification = proof
        with self.assertRaisesRegex(pub.Blocked, 'payload mismatch: transcript_text'):
            controller.run('publish')
        self.assertFalse(any(a[1] == 'publish' for a in self.provider.mutations))

    def test_plan_no_provider_calls(self):
        self.assertEqual(self.controller().run('plan')['status'], 'plan')
        self.assertEqual(self.provider.calls, [])


if __name__ == '__main__':
    unittest.main()

class ReadingPublishTests(unittest.TestCase):
 tearDown=PublishTests.tearDown
 validator=PublishTests.validator
 controller=PublishTests.controller
 def setUp(self):
  PublishTests.setUp(self)
  self.m['publication_transcript']={'version':1,'source':'reading_transcript'}
  self.payload['transcript_text']='First paragraph.\n\n第二自然段。'
  pub.persist(self.package/'payload.json',self.payload)
  self.m['artifacts']['transistor_payload'].update(sha256=pub.digest_file(self.package/'payload.json'),bytes=(self.package/'payload.json').stat().st_size)
  pub.persist(self.package/'episode.json',self.m)
  self.a.update(manifest_sha256=pub.digest_file(self.package/'episode.json'),payload_sha256=pub.digest_bytes(pub.canonical(self.payload)))
  pub.persist(self.auth,self.a)
 def modify_created(self,value):
  call=self.provider.call
  def modified(args):
   result=call(args)
   if args[1]=='create' and '--dry-run' not in args:self.provider.remote['attributes']['transcript_text']=value
   return result
  self.provider.call=modified
 def test_first_publish_reading_blank_lines_and_receipt(self):
  self.modify_created(self.payload['transcript_text'].replace('\n\n','\n'))
  result=self.controller().run('publish')
  self.assertEqual(result['status'],'published_verified')
  self.assertEqual(result['transcript_verification']['comparison'],'blank_line_normalization')
  self.assertEqual(self.controller().run('publish')['status'],'already_published_noop')
  self.assertEqual([a[1] for a in self.provider.mutations],['upload','create','publish'])
 def test_first_publish_reading_changed_words_rejected(self):
  self.modify_created('Different text')
  with self.assertRaises(pub.Blocked):self.controller().run('publish')
  self.assertNotIn('publish',[a[1] for a in self.provider.mutations])
