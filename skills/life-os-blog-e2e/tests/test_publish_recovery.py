"""Corrective publishing regression tests; local temporary repositories only."""
import html
import json
from pathlib import Path
from unittest import mock

from test_blog_e2e import Base, ARTICLE, SLUG, git, write, be


class TestPublishReadiness(Base):
    def test_false_does_not_break_drafting_but_blocks_freeze_validate_publish(self):
        rid = self.e.to_enhance()
        text = ARTICLE.replace('subtitle:', 'published: false\nsubtitle:')
        (code, out), _ = self.e.stage(rid, 'enhance', text)
        self.assertEqual(code, 0, out)  # published:false is legal while drafting
        src = self.e.blogs / self.e.state(rid)['article']['path']
        before = src.read_bytes()
        head = git(self.e.repo, 'rev-parse', 'HEAD')
        self.assertEqual(self.e.cli('freeze', '--run', rid)[1]['error'], 'article_not_publishable')
        self.assertIn('article_not_publishable', json.dumps(self.e.cli('validate', '--run', rid)))
        self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[1]['error'], 'article_not_publishable')
        self.assertEqual(src.read_bytes(), before)
        self.assertEqual(git(self.e.repo, 'rev-parse', 'HEAD'), head)
        self.assertFalse((self.e.tmp / 'state/runs' / rid / 'publish.json').exists())
        self.assertEqual(self.e.pushes, 0)

    def test_false_like_explicit_values_are_rejected_true_and_omitted_allowed(self):
        for field in ('published: false', 'published: False # draft', 'published: null',
                      'published: ~', 'published:', 'published: 0', 'published: "false"',
                      'published: off', 'published: no', '"published": false', "'published': false",
                      'published: true\npublished: false'):
            with self.subTest(field=field), self.assertRaises(be.Refuse):
                be.require_publishable(ARTICLE.replace('subtitle:', field + '\nsubtitle:'))
        for field in ('published: true', 'published: True # ready', 'published: TRUE'):
            be.require_publishable(ARTICLE.replace('subtitle:', field + '\nsubtitle:'))
        be.require_publishable(ARTICLE)

    def test_default_hexo_forces_fresh_output_and_bails_without_clean(self):
        cfg = be.load_config()
        self.assertEqual(cfg.build_cmd[-2:], ['--force', '--bail'])
        self.assertNotIn('clean', cfg.build_cmd)


class TestGeneratedArticle(Base):
    def prepare(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.page = self.e.repo / f'public/2026/10/20/{SLUG}/index.html'
        self.head = git(self.e.repo, 'rev-parse', 'HEAD')
        return rid

    def bad_build(self, mode):
        original = self.e.fake_run
        def run(argv, cwd=None, timeout=120, env=None):
            if argv[:3] != ['npx', '--no-install', 'hexo']:
                return original(argv, cwd=cwd, timeout=timeout, env=env)
            self.e.calls.append(list(argv))
            if mode in ('missing', 'stale'):
                return 0, '0 files generated', ''
            result = original(argv, cwd=cwd, timeout=timeout, env=env)
            text = self.page.read_text()
            if mode == 'title':
                text = text.replace('Pairi Daiza 一日', 'unrelated title')
            elif mode == 'body':
                text = text.replace('回家的路上大家都睡着了，只有我还醒着看着夕阳慢慢落下去。', 'older same-slug content')
            elif mode == 'placeholder':
                text = '<html><h1>Pairi Daiza 一日</h1><article>Coming soon</article></html>'
            elif mode == 'hidden':
                text = text.replace('<article>', '<script>').replace('</article>', '</script>')
            elif mode == 'ref':
                text = text.replace('<img ', '<!-- <img ').replace('.webp">', '.webp"> -->')
            elif mode == 'asset':
                write(self.e.repo / f'public/img/posts/{SLUG}/panda.webp', b'old wrong image')
            elif mode == 'missing_asset':
                (self.e.repo / f'public/img/posts/{SLUG}/panda.webp').unlink()
            elif mode == 'ambiguous':
                write(self.e.repo / f'public/other/{SLUG}/index.html', text)
            write(self.page, text)
            return result
        return mock.patch.object(be, 'run_cmd', run)

    def assert_blocked(self, rid, cause):
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual((code, out['error'], out['cause']), (5, 'generated_verification_failed', cause), out)
        self.assertEqual(self.e.pushes, 0)
        self.assertEqual(git(self.e.repo, 'rev-parse', 'HEAD'), self.head)
        journal = json.loads((self.e.tmp / 'state/runs' / rid / 'publish.json').read_text())
        self.assertEqual(journal['phases']['build']['state'], 'failed')
        self.assertEqual(journal['phases']['commit']['state'], 'pending')
        self.assertEqual(journal['phases']['push']['state'], 'pending')

    def test_rc_zero_without_article_cannot_commit_push_and_can_resume(self):
        rid = self.prepare()
        write(self.e.repo / 'public/unrelated/keep.txt', 'never delete unrelated output')
        with self.bad_build('missing'):
            self.assert_blocked(rid, 'generated_article_missing_or_ambiguous')
        self.assertEqual((self.e.repo / 'public/unrelated/keep.txt').read_text(), 'never delete unrelated output')
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        j = json.loads((self.e.tmp / 'state/runs' / rid / 'publish.json').read_text())
        self.assertEqual(j['phases']['build']['evidence']['probes'], 2)
        self.assertEqual(len(j['phases']['build']['evidence']['assets']), 2)
        self.assertEqual(self.e.pushes, 1)

    def test_untouched_even_matching_same_slug_html_is_stale(self):
        rid = self.prepare()
        write(self.page, '<html><h1>Pairi Daiza 一日</h1><article>' + ARTICLE + '</article></html>')
        before = self.page.read_bytes()
        with self.bad_build('stale'):
            self.assert_blocked(rid, 'generated_article_stale')
        self.assertEqual(self.page.read_bytes(), before)

    def test_fresh_title_only_placeholder_page_is_rejected(self):
        rid = self.prepare()
        with self.bad_build('placeholder'):
            self.assert_blocked(rid, 'generated_body_mismatch')

    def test_fresh_wrong_title_is_rejected(self):
        rid = self.prepare()
        with self.bad_build('title'):
            self.assert_blocked(rid, 'generated_title_mismatch')

    def test_old_body_with_same_title_and_slug_is_rejected(self):
        rid = self.prepare()
        with self.bad_build('body'):
            self.assert_blocked(rid, 'generated_body_mismatch')

    def test_text_hidden_in_script_does_not_count_as_article(self):
        rid = self.prepare()
        with self.bad_build('hidden'):
            self.assert_blocked(rid, 'generated_body_mismatch')

    def test_generated_image_bytes_must_match_approved_image(self):
        rid = self.prepare()
        with self.bad_build('asset'):
            self.assert_blocked(rid, 'generated_asset_missing_or_mismatch')

    def test_commented_out_image_is_not_a_real_reference(self):
        rid = self.prepare()
        with self.bad_build('ref'):
            self.assert_blocked(rid, 'generated_asset_reference_missing')

    def test_generated_image_file_must_actually_exist(self):
        rid = self.prepare()
        with self.bad_build('missing_asset'):
            self.assert_blocked(rid, 'generated_asset_missing_or_mismatch')

    def test_multiple_candidate_pages_fail_closed(self):
        rid = self.prepare()
        with self.bad_build('ambiguous'):
            self.assert_blocked(rid, 'generated_article_missing_or_ambiguous')

    def test_tampered_output_on_push_resume_requires_rebuild(self):
        rid = self.prepare()
        self.e.push_mode = 'fail'
        self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[0], 5)
        commit = git(self.e.repo, 'rev-parse', 'HEAD')
        write(self.page, '<html>tampered output</html>')
        self.e.push_mode = 'ok'
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual((code, out['cause']), (5, 'generated_evidence_changed'))
        self.assertEqual(self.e.pushes, 1)
        self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[0], 0)
        self.assertEqual(git(self.e.repo, 'rev-parse', 'HEAD'), commit)

    def test_markdown_probes_cover_late_edits_and_ignore_audit_comments(self):
        body = 'This is the first long substantial paragraph for this regression.\n\n' \
               'This is another substantial paragraph containing **formatted** and [linked](https://example.test) words.\n\n' \
               '<!-- /img/posts/a/manifest.json -->'
        probes = be.article_probes(body)
        self.assertEqual(len(probes), 2)
        self.assertIn('formattedandlinkedwords.', probes[1])

    def test_audit_sidecars_are_still_frozen_git_inputs_not_rendered_images(self):
        rid = self.e.to_enhance()
        sidecar = f'/img/posts/{SLUG}/provenance.json'
        write(self.e.blogs / ('50-assets' + sidecar), '{"provenance": "original formatting"}')
        self.e.stage(rid, 'enhance', ARTICLE + '\n<!-- audit: ' + sidecar + ' -->\n')
        self.e.approve(rid)
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        cfg = be.load_config()
        run = self.e.state(rid)
        text = (self.e.blogs / run['article']['path']).read_text()
        assets = be.referenced_assets(cfg, text, SLUG)
        self.assertIn(sidecar, assets)
        write(self.e.repo / ('public' + sidecar), '{\n  "provenance": "original formatting"\n}')
        evidence = be.verify_generated(cfg, run, text, assets)
        self.assertEqual(len(evidence['assets']), 2)
        self.assertEqual(git(self.e.repo, 'show', 'HEAD:source' + sidecar).strip(),
                         '{"provenance": "original formatting"}')
    def test_online_readback_checks_real_images_not_comment_only_json_sidecars(self):
        rid = self.e.to_enhance()
        sidecar = f'/img/posts/{SLUG}/audit.json'
        write(self.e.blogs / ('50-assets' + sidecar), '{"audit": "source format"}')
        self.e.stage(rid, 'enhance', ARTICLE + '\n<!-- audit: ' + sidecar + ' -->\n')
        self.e.approve(rid)
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        cfg = be.load_config()
        self.e.http[cfg.site_url + out['url_path']] = (200, {}, (self.e.repo / 'public' / out['url_path'].lstrip('/') / 'index.html').read_bytes())
        for u, local in be.referenced_assets(cfg, ARTICLE, SLUG).items():
            self.e.http[cfg.site_url + u] = (200, {'Content-Type': 'image/webp'}, local.read_bytes())
        code, result = self.e.cli('verify-online', '--run', rid)
        self.assertEqual((code, result['error'], result['public_ok']), (5, 'verification_partial', True))
        self.assertEqual(len(result['assets']), 2)
        self.assertNotIn(sidecar, [a['url'] for a in result['assets']])
        source = self.e.blogs / self.e.state(rid)['article']['path']
        write(source, source.read_text() + '\nchanged after publication\n')
        self.assertEqual(self.e.cli('verify-online', '--run', rid)[1]['error'], 'published_digest_changed')


class TestSuccessorGeneration(Base):
    def published(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        self.rid = rid
        self.rd = self.e.tmp / 'state/runs' / rid
        self.jp = self.rd / 'publish.json'
        self.old_bytes = self.jp.read_bytes()
        self.old = json.loads(self.old_bytes)
        self.old_result = self.e.state(rid)['published']
        self.old_apps = json.loads((self.rd / 'approvals.json').read_text())
        return rid

    def revise(self):
        text = ARTICLE.replace('subtitle:', 'published: true\nsubtitle:')
        (code, out), _ = self.e.stage(self.rid, 'enhance', text)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((self.rd / 'approvals.json').read_text())[0], self.old_apps[0])

    def publish_new(self):
        return self.e.cli('publish', '--run', self.rid, '--publish', '--new-generation')

    def assert_old_untouched(self):
        self.assertEqual(self.jp.read_bytes(), self.old_bytes)
        self.assertEqual(self.e.state(self.rid)['published'], self.old_result)
        self.assertFalse((self.rd / 'publish-history').exists())
        self.assertEqual(self.e.pushes, 1)

    def test_new_digest_without_new_approval_does_not_touch_old_result(self):
        self.published()
        self.revise()
        code, out = self.publish_new()
        self.assertEqual((code, out['error']), (2, 'approval_missing_or_stale'))
        self.assert_old_untouched()

    def test_legacy_published_false_done_with_null_url_gets_a_real_corrective_generation(self):
        self.rid = rid = self.e.to_enhance()
        text = ARTICLE.replace('subtitle:', 'published: false\nsubtitle:')
        self.e.stage(rid, 'enhance', text)
        # Seed the legacy bug in this temp repo only, with the two old missing
        # checks disabled. All approval messages here are gateway test fixtures.
        with mock.patch.object(be, 'require_publishable'), mock.patch.object(be, 'verify_generated',
                return_value={'url_path': None, 'legacy_bug_fixture': True}):
            self.e.approve(rid)
            code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        self.assertIsNone(out['url_path'])
        self.rd = self.e.tmp / 'state/runs' / rid
        self.jp = self.rd / 'publish.json'
        self.old_bytes = self.jp.read_bytes()
        self.old = json.loads(self.old_bytes)
        self.old_result = self.e.state(rid)['published']
        self.old_apps = json.loads((self.rd / 'approvals.json').read_text())
        self.revise()
        self.assertEqual(self.publish_new()[1]['error'], 'approval_missing_or_stale')
        self.assert_old_untouched()
        self.e.approve(rid, 901)
        code, out = self.publish_new()
        self.assertEqual(code, 0, out)
        self.assertIsNotNone(out['url_path'])
        history = self.rd / 'publish-history' / (self.old['publish_id'] + '.json')
        self.assertEqual(history.read_bytes(), self.old_bytes)
        self.assertIsNone(json.loads(history.read_text())['result']['url_path'])
        self.assertEqual(json.loads((self.rd / 'approvals.json').read_text())[0], self.old_apps[0])

    def test_explicit_new_generation_flag_required(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        self.assertEqual(self.e.cli('publish', '--run', self.rid, '--publish')[1]['error'], 'completed_digest_changed')
        self.assert_old_untouched()

    def test_same_digest_is_idempotent_even_with_successor_flag(self):
        self.published()
        code, out = self.publish_new()
        self.assertEqual((code, out['status']), (0, 'already_published'))
        self.assert_old_untouched()

    def test_old_used_gateway_message_cannot_approve_new_digest(self):
        self.published()
        self.revise()
        _, frozen = self.e.cli('freeze', '--run', self.rid)
        code, out = self.e.cli('approve', '--run', self.rid, '--digest', frozen['digest'],
                               '--session-id', 's1', '--message-id', '900')
        self.assertEqual((code, out['error']), (3, 'inbound_event_rejected'))
        self.assertEqual(self.publish_new()[1]['error'], 'approval_missing_or_stale')
        self.assert_old_untouched()

    def test_new_valid_gateway_approval_archives_exact_old_journal_and_pushes_only_post_change(self):
        self.published()
        self.revise()
        digest = self.e.approve(self.rid, 901)
        code, out = self.publish_new()
        self.assertEqual(code, 0, out)
        self.assertNotEqual(out['publish_id'], self.old['publish_id'])
        self.assertEqual(out['digest'], digest)
        hist = self.rd / 'publish-history' / (self.old['publish_id'] + '.json')
        self.assertEqual(hist.read_bytes(), self.old_bytes)
        new = json.loads(self.jp.read_text())
        self.assertEqual(new['predecessor']['journal_sha256'], be.sha_bytes(self.old_bytes))
        apps = json.loads((self.rd / 'approvals.json').read_text())
        self.assertEqual(apps[0], self.old_apps[0])
        self.assertEqual([a['state'] for a in apps], ['used', 'used'])
        self.assertEqual(git(self.e.repo, 'show', '--name-only', '--format=', 'HEAD').split(),
                         ['source/_posts/' + Path(out['published_rel']).name])
        self.assertEqual(self.publish_new()[1]['status'], 'already_published')
        self.assertEqual(self.e.pushes, 2)

    def test_successor_failed_build_can_resume_without_new_generation_or_new_approval(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        self.e.build_fail = True
        self.assertEqual(self.publish_new()[0], 5)
        pid = json.loads(self.jp.read_text())['publish_id']
        self.assertEqual((self.rd / 'publish-history' / (self.old['publish_id'] + '.json')).read_bytes(), self.old_bytes)
        self.assertEqual(self.e.state(self.rid)['published'], self.old_result)
        self.e.build_fail = False
        code, out = self.e.cli('publish', '--run', self.rid, '--publish')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['publish_id'], pid)
        self.assertEqual(self.e.pushes, 2)

    def test_archive_conflict_never_overwritten_and_no_approval_consumption(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        hist = self.rd / 'publish-history' / (self.old['publish_id'] + '.json')
        write(hist, b'conflicting evidence')
        code, out = self.publish_new()
        self.assertEqual((code, out['error']), (2, 'publish_history_conflict'))
        self.assertEqual(hist.read_bytes(), b'conflicting evidence')
        self.assertEqual(self.jp.read_bytes(), self.old_bytes)
        self.assertEqual(json.loads((self.rd / 'approvals.json').read_text())[-1]['state'], 'valid')
        self.assertEqual(self.e.pushes, 1)

    def test_crash_after_archive_before_atomic_successor_intent_is_retryable(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        real = be.write_json
        def crash(path, obj):
            if Path(path) == self.jp and obj.get('predecessor'):
                raise RuntimeError('injected interruption before successor intent')
            return real(path, obj)
        with mock.patch.object(be, 'write_json', crash):
            self.assertEqual(self.publish_new()[0], 1)
        self.assertEqual(self.jp.read_bytes(), self.old_bytes)
        self.assertEqual(json.loads((self.rd / 'approvals.json').read_text())[-1]['state'], 'valid')
        code, out = self.publish_new()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.e.pushes, 2)

    def test_crash_after_successor_intent_before_consumption_resumes_same_generation(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        real = be.write_json
        def crash(path, obj):
            if Path(path).name == 'approvals.json':
                raise RuntimeError('injected interruption before approval projection')
            return real(path, obj)
        with mock.patch.object(be, 'write_json', crash):
            self.assertEqual(self.publish_new()[0], 1)
        pid = json.loads(self.jp.read_text())['publish_id']
        code, out = self.e.cli('publish', '--run', self.rid, '--publish')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['publish_id'], pid)
        self.assertEqual(self.e.pushes, 2)

    def test_missing_frozen_body_is_rejected_before_history_write(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        rp = self.rd / 'run.json'
        run = json.loads(rp.read_text())
        run['frozen'].pop('body')
        write(rp, json.dumps(run))
        self.assertEqual(self.publish_new()[1]['error'], 'current_frozen_digest_required')
        self.assert_old_untouched()

    def test_incomplete_or_used_new_approval_is_rejected_before_history_write(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        ap = self.rd / 'approvals.json'
        original = json.loads(ap.read_text())
        for changes in ({'state': 'used', 'uses': 1}, {'state': 'revoked'}, {'uses': 1},
                        {'kind': 'one-use-chat-authorization'}, {'session_id': None}, {'message_id': None}):
            with self.subTest(changes=changes):
                apps = json.loads(json.dumps(original))
                apps[-1].update(changes)
                write(ap, json.dumps(apps))
                self.assertNotEqual(self.publish_new()[0], 0)
                self.assert_old_untouched()

    def test_gateway_unavailable_or_changed_is_rejected_before_history_write(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        ev = self.e.gw.pop(('s1', '901'))
        self.assertEqual(self.publish_new()[1]['error'], 'successor_gateway_approval_unverifiable')
        self.assert_old_untouched()
        ev['text'] += ' 但先别发'
        self.e.gw[('s1', '901')] = ev
        self.assertEqual(self.publish_new()[1]['error'], 'successor_gateway_approval_unverifiable')
        self.assert_old_untouched()

    def test_target_repository_change_refused_even_after_new_freeze_and_approval(self):
        self.published()
        self.revise()
        git(self.e.repo, 'checkout', '-qb', 'elsewhere')
        self.e.approve(self.rid, 901)
        self.assertEqual(self.publish_new()[1]['error'], 'successor_target_changed')
        self.assert_old_untouched()

    def test_revocation_and_history_tamper_stop_successor_resume(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        self.e.build_fail = True
        self.assertEqual(self.publish_new()[0], 5)
        new = json.loads(self.jp.read_text())
        self.e.cli('revoke', '--run', self.rid, '--approval', new['approval_id'])
        self.assertEqual(self.publish_new()[1]['error'], 'approval_revoked_or_invalid')
        hist = self.rd / new['predecessor']['history_path']
        write(hist, hist.read_bytes() + b' ')
        self.assertEqual(self.publish_new()[1]['error'], 'publish_history_unverified')
        self.assertEqual(self.e.pushes, 1)

    def test_concurrent_run_or_repository_lock_cannot_create_generation(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        for lock in (self.rd / '.lock', self.e.tmp / 'state/publish-repo.lock'):
            with be.file_lock(lock):
                self.assertEqual(self.publish_new()[1]['error'], 'locked')
            self.assert_old_untouched()

    def test_successor_exact_file_set_guard_rejects_extra_file_in_recovery_commit(self):
        self.published()
        self.revise()
        self.e.approve(self.rid, 901)
        self.e.push_mode = 'fail'
        self.assertEqual(self.publish_new()[0], 5)
        j = json.loads(self.jp.read_text())
        git(self.e.repo, 'reset', '-q', '--soft', 'HEAD~1')
        write(self.e.repo / 'extra.txt', 'not approved')
        git(self.e.repo, 'add', 'extra.txt')
        git(self.e.repo, 'commit', '-qm', 'forged corrective commit')
        j['phases']['commit']['commit'] = git(self.e.repo, 'rev-parse', 'HEAD').strip()
        write(self.jp, json.dumps(j))
        self.e.push_mode = 'ok'
        code, out = self.publish_new()
        self.assertEqual((code, out['error'], out['why']), (2, 'recovery_commit_unverified', 'file_set_differs'))
        self.assertEqual(self.e.pushes, 2)  # old success + corrective failed push; forged commit never pushed
