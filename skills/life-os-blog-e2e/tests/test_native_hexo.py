"""Optional native Hexo regressions. No install, network, or production writes."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from test_blog_e2e import Base, ARTICLE, SLUG, write, be

MODULES = Path(os.environ.get('BLOG_E2E_TEST_HEXO_MODULES', str(Path.cwd() / 'node_modules')))


@unittest.skipUnless((MODULES / 'hexo/bin/hexo').is_file() and shutil.which('node'),
                     'native Hexo not installed; set BLOG_E2E_TEST_HEXO_MODULES (never install in tests)')
class TestNativeHexo(Base):
    def native_site(self):
        (self.e.repo / 'node_modules').symlink_to(MODULES, target_is_directory=True)
        write(self.e.repo / 'package.json', json.dumps({'hexo': {'version': '7.3.0'}, 'dependencies': {
            'hexo': '*', 'hexo-renderer-ejs': '*', 'hexo-renderer-marked': '*'}}))
        write(self.e.repo / '_config.yml', 'title: Fixture\nurl: https://blog.example.test\n'
              'theme: fixture\npermalink: :year/:month/:day/:title/\nfuture: true\n')
        write(self.e.repo / 'themes/fixture/layout/post.ejs', '<html><h1><%= page.title %></h1>'
              '<img src="<%= page.banner_img %>"><article><%- page.content %></article></html>')
        self.cmd = [shutil.which('node'), str(self.e.repo / 'node_modules/hexo/bin/hexo'),
                    'generate', '--force', '--bail']
        cfg = json.loads(self.e.cfg_path.read_text())
        cfg['build_cmd'] = self.cmd
        write(self.e.cfg_path, json.dumps(cfg))
        return self.cmd

    def actual_builder(self):
        fake = self.e.fake_run
        def run(argv, cwd=None, timeout=120, env=None):
            if argv == self.cmd:
                self.e.calls.append(list(argv))
                return self.e._real_run(argv, cwd=cwd, timeout=timeout, env=env)
            return fake(argv, cwd=cwd, timeout=timeout, env=env)
        return mock.patch.object(be, 'run_cmd', run)

    def test_real_hexo_false_returns_zero_but_no_article_and_guard_rejects_it(self):
        rid = self.e.to_enhance()
        text = ARTICLE.replace('subtitle:', 'published: false\nsubtitle:')
        self.e.stage(rid, 'enhance', text)
        self.native_site()
        write(self.e.repo / f'source/_posts/2026-10-20-{SLUG}.md', text)
        p = subprocess.run(self.cmd, cwd=self.e.repo, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(be.generated_candidates(self.e.repo / 'public', SLUG), [])
        with self.actual_builder():
            self.assertEqual(self.e.cli('publish', '--run', rid, '--publish')[1]['error'], 'article_not_publishable')
        self.assertEqual(self.e.pushes, 0)
        self.assertFalse(any(c == self.cmd for c in self.e.calls))

    def test_real_hexo_true_renders_article_images_and_fresh_repeat_without_clean(self):
        rid = self.e.to_enhance()
        self.native_site()
        self.e.stage(rid, 'enhance', ARTICLE.replace('subtitle:', 'published: true\nsubtitle:'))
        self.e.approve(rid)
        with self.actual_builder():
            code, out = self.e.cli('publish', '--run', rid, '--publish')
        self.assertEqual(code, 0, out)
        code, parity = self.e.cli("render-check", "--run", rid, "--site-dir", str(self.e.repo))
        self.assertEqual((code, parity["status"]), (0, "render_verified"))
        cfg = be.load_config()
        run = self.e.state(rid)
        text = (self.e.blogs / run['article']['path']).read_text()
        assets = be.referenced_assets(cfg, text, SLUG)
        evidence = be.verify_generated(cfg, run, text, assets)
        self.assertEqual(evidence['probes'], 2)
        self.assertEqual(len(evidence['assets']), 2)
        before = be.generated_snapshot(self.e.repo / 'public', SLUG)
        p = subprocess.run(self.cmd, cwd=self.e.repo, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        repeated = be.verify_generated(cfg, run, text, assets, before=before)
        self.assertEqual(repeated['html_sha256'], evidence['html_sha256'])
        self.assertEqual(self.e.pushes, 1)  # only the fixture's local bare remote
