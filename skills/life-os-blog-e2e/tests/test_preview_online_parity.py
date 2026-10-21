"""Production-parity and visible online acceptance, synthetic local fixtures only."""
import json
import shutil
from pathlib import Path
from test_blog_e2e import Base, ARTICLE, SLUG, write


class TestPreviewParity(Base):
    def built(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[0], 0)
        return rid

    def test_exact_isolated_site_passes_without_publication_side_effect(self):
        rid = self.built()
        site = self.e.tmp / 'isolated'
        shutil.copytree(self.e.repo, site, ignore=shutil.ignore_patterns('.git'))
        before = self.e.state(rid)
        code, out = self.e.cli('render-check', '--run', rid, '--site-dir', str(site))
        self.assertEqual((code, out['status']), (0, 'render_verified'))
        self.assertFalse(out['grants_publish'])
        self.assertEqual(self.e.state(rid), before)
        code, out = self.e.cli('preview', 'start', '--run', rid, '--site-dir', str(site))
        self.assertEqual(code, 0, out)
        self.assertEqual(out['render_evidence']['digest'], before['frozen']['digest'])
        self.assertTrue(self.e.cli('preview', 'stop')[1]['port_closed'])

    def test_derivative_metadata_override_is_not_production_parity(self):
        rid = self.built()
        post = next((self.e.repo / 'source/_posts').glob('*.md'))
        write(post, post.read_text().replace('subtitle:', 'published: true\nsubtitle:'))
        code, out = self.e.cli('render-check', '--run', rid, '--site-dir', str(self.e.repo))
        self.assertEqual((code, out['error']), (2, 'preview_source_mismatch'))
        self.assertEqual(self.e.cli('preview', 'start', '--run', rid)[1]['error'], 'preview_source_mismatch')

    def test_changed_candidate_cannot_reuse_previous_html(self):
        rid = self.built()
        self.e.stage(rid, 'enhance', ARTICLE + '\n\nA newly added substantial paragraph that must be visible in the rendered article.\n')
        text = (self.e.blogs / self.e.state(rid)['article']['path']).read_text()
        write(next((self.e.repo / 'source/_posts').glob('*.md')), text)
        self.assertEqual(self.e.cli('render-check', '--run', rid, '--site-dir', str(self.e.repo))[1]['error'], 'generated_body_mismatch')

    def test_unpublishable_source_cannot_pass_preview_parity(self):
        rid = self.e.to_enhance()
        self.e.stage(rid, 'enhance', ARTICLE.replace('subtitle:', 'published: false\nsubtitle:'))
        self.assertEqual(self.e.cli('render-check', '--run', rid, '--site-dir', str(self.e.repo))[1]['error'], 'article_not_publishable')


class TestOnlineAcceptance(Base):
    def fixture(self):
        rid = self.e.to_enhance()
        text = ARTICLE + '\n\nA later substantial paragraph proves the entire article, beyond the first two paragraphs, is live.\n'
        self.e.stage(rid, 'enhance', text)
        self.e.approve(rid)
        self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[0], 0)
        state = self.e.state(rid)
        base = 'https://blog.example.test'
        page = (self.e.repo / 'public' / state['published']['url_path'].strip('/') / 'index.html').read_bytes()
        self.page_url = base + state['published']['url_path']
        self.e.http[self.page_url] = (200, {}, page)
        for name in ('cover', 'panda'):
            self.e.http[f'{base}/img/posts/{SLUG}/{name}.webp'] = (200, {'Content-Type': 'image/webp'}, (self.e.blogs / f'50-assets/img/posts/{SLUG}/{name}.webp').read_bytes())
        cfg = json.loads(self.e.cfg_path.read_text())
        cfg['cf_deploy_readback_cmd'] = ['cf-readback', '{project}', '{commit}']
        write(self.e.cfg_path, json.dumps(cfg))
        return rid, page

    def test_all_visible_prose_and_images_match(self):
        rid, page = self.fixture()
        code, out = self.e.cli('verify-online', '--run', rid)
        self.assertEqual((code, out['status']), (0, 'verified'))
        self.assertEqual(out['page']['body_probes'], 3)

    def test_missing_later_paragraph_or_hidden_body_fails_even_with_200(self):
        rid, page = self.fixture()
        for bad in (page.replace(b'A later substantial', b'A missing substantial'), page.replace(b'<article>', b'<article hidden>')):
            self.e.http[self.page_url] = (200, {}, bad)
            self.assertEqual(self.e.cli('verify-online', '--run', rid)[1]['error'], 'online_verification_failed')

    def test_comment_only_image_reference_is_not_rendered_evidence(self):
        rid, page = self.fixture()
        self.e.http[self.page_url] = (200, {}, page.replace(b'<img ', b'<!-- <img ').replace(b'.webp">', b'.webp"> -->'))
        self.assertEqual(self.e.cli('verify-online', '--run', rid)[1]['error'], 'online_verification_failed')

    def test_wrong_mime_with_matching_bytes_is_rejected(self):
        rid, _ = self.fixture()
        u=f'https://blog.example.test/img/posts/{SLUG}/panda.webp'
        code, _, data = self.e.http[u]
        self.e.http[u] = (code, {'Content-Type': 'text/html'}, data)
        self.assertEqual(self.e.cli('verify-online', '--run', rid)[1]['error'], 'online_verification_failed')
