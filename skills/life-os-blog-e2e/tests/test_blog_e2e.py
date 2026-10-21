"""Invariant tests for blog_e2e.py. Real Git in temp dirs; build, preflight,
network and push-timeouts are simulated through the controller's two seams
(`run_cmd`, `http_get`). Nothing here touches production config, Telegram,
GitHub, Cloudflare or any real Blogs/Drive tree.

Run: python3 -I -m unittest discover -s tests -v   (from the Skill directory)
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import blog_e2e as be  # noqa: E402

CHAT, THREAD, USER = "-100111", "77", "42"
SLUG = "pairi-daiza-day"
ARTICLE = """---
title: "Pairi Daiza 一日"
subtitle: "亲子日记"
slug: pairi-daiza-day
date: 2026-10-20 21:00:00
categories:
  - [Life, Family]
index_img: /img/posts/pairi-daiza-day/cover.webp
banner_img: /img/posts/pairi-daiza-day/cover.webp
excerpt: 一天的记录
---

## 清晨出发

我们早上八点出发去了公园，孩子一路都很兴奋地看着窗外的风景。

![熊猫](/img/posts/pairi-daiza-day/panda.webp)

## 傍晚回家

回家的路上大家都睡着了，只有我还醒着看着夕阳慢慢落下去。
"""


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout


def write(p, text):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, "utf-8") if isinstance(text, str) else p.write_bytes(text)


class Env:
    def __init__(self, tmp):
        self.tmp = Path(tmp).resolve()
        self.blogs = self.tmp / "Blogs"
        self.drive = self.tmp / "Drive" / "Blogs"
        self.repo = self.tmp / "ma-blog"
        self.remote = self.tmp / "remote.git"
        self.drive.mkdir(parents=True)
        self.preflight_pass = True
        self.build_fail = False
        self.push_mode = "ok"  # ok | timeout_after_success | timeout_lost | fail
        self.calls = []
        self.pushes = 0
        self.http = {}
        self.cf_ok = True
        self._mk_blogs()
        self._mk_repo()
        self.cfg_path = self.tmp / "hermes-blog.json"
        write(self.cfg_path, json.dumps({
            "blogs_root": str(self.blogs), "drive_backup_root": str(self.drive), "publish_repo": str(self.repo),
            "chat_id": CHAT, "thread_id": THREAD, "allowed_user_ids": [USER], "site_url": "https://blog.example.test",
            "cf_profile": "p", "cf_project": "proj", "verify_attempts": 1, "verify_delay": 0,
            "state_dir": str(self.tmp / "state"), "gateway_events_cmd": ["gw-event", "{session_id}", "{message_id}"]}))
        self.gw = {}
        os.environ["BLOG_E2E_CONFIG"] = str(self.cfg_path)
        self._real_run, self._real_http = be.run_cmd, be.http_get
        be.run_cmd, be.http_get = self.fake_run, self.fake_http

    def close(self):
        be.run_cmd, be.http_get = self._real_run, self._real_http

    # ---- fixture trees
    def _mk_blogs(self):
        b = self.blogs
        write(b / "AGENTS.md", "# AGENTS\n## Read-First Files (in order)\n1. `.rules/blog-styling-guideline.md`\n"
              "2. `.rules/blog-categories.md`\n3. `.rules/hexo-frontmatter-spec.md`\n4. `.rules/project_prompt.md`\n"
              "5. `memory.md`（如存在）\n\n## Next\n")
        for r in ("blog-styling-guideline", "blog-categories", "hexo-frontmatter-spec", "project_prompt"):
            write(b / ".rules" / f"{r}.md", f"rule {r}\n")
        write(b / "00-admin/rules/rules-registry.yaml", """rules:
  - id: blog-categories
    path: ".rules/blog-categories.md"
    stages: [draft, enhance, publish]
    priority: 1
  - id: blog-styling
    path: ".rules/blog-styling-guideline.md"
    stages: [draft, enhance]
    priority: 2
  - id: hexo-frontmatter
    path: ".rules/hexo-frontmatter-spec.md"
    stages: [enhance, publish]
    priority: 1
  - id: project-prompt
    path: ".rules/project_prompt.md"
    stages: [research, draft, enhance, publish]
    priority: 3
""")
        write(b / "00-admin/rules/load-order.md", "load order\n")
        write(b / "00-admin/commands/README.md", "# commands\n")
        for n in ("visualize-post", "publish-ready", "preflight-check"):
            write(b / f"00-admin/commands/{n}.md", n + "\n")
        for n in ("experience", "learning", "insight"):
            write(b / f"00-admin/templates/pipelines/pipeline-{n}.md", f"pipeline {n}\n")
        write(b / "00-admin/templates/post-template.md", "tpl\n")
        for n in ("experience-retro", "learning-remix", "insight-foresight", "anti-ai-polish", "infographic-create",
                  "distribution-blog"):
            write(b / f"00-admin/skills/skill-{n}.md", f"skill {n}\n")
        for n in ("writing-style", "thinking-lenses", "anti-ai-rules"):
            write(b / f"00-admin/cognition/{n}.md", n + "\n")
        for n in ("glossary.yml", "enhance-rules.md", "image-policy.md"):
            write(b / f"00-admin/conventions/{n}", n + "\n")
        write(b / "00-admin/scripts/publish_preflight.py", "# stub; the seam answers\n")
        write(b / "40-notes/pairi-daiza-trip.md", "# Pairi Daiza trip notes\nPandas\n")
        write(b / ".gitignore", ".automation/\n")
        subprocess.run(["git", "init", "-q", "-b", "master", str(b)], check=True)
        git(b, "config", "user.email", "t@example.test")
        git(b, "config", "user.name", "T")
        git(b, "add", "-A")
        git(b, "commit", "-qm", "baseline")

    def _mk_repo(self):
        subprocess.run(["git", "init", "-q", "--bare", "-b", "master", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "master", str(self.repo)], check=True)
        git(self.repo, "config", "user.email", "t@example.test")
        git(self.repo, "config", "user.name", "T")
        write(self.repo / "source/_posts/.keep", "")
        write(self.repo / "_config.fluid.yml", "banner: old\n")
        write(self.repo / "image-credits.json", '{"old": 1}')
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-q", "origin", "master")

    # ---- seams
    def fake_run(self, argv, cwd=None, timeout=120, env=None):
        self.calls.append(list(argv))
        if argv[0] == "git":
            if "push" in argv:
                self.pushes += 1
                if self.push_mode == "timeout_lost":
                    raise be.RunTimeout("push timeout")
                if self.push_mode == "fail":
                    return 1, "", "remote rejected"
                rc = subprocess.run(argv, capture_output=True, text=True)
                if self.push_mode == "timeout_after_success":
                    raise be.RunTimeout("push timeout")
                return rc.returncode, rc.stdout, rc.stderr
            r = subprocess.run(argv, capture_output=True, text=True, cwd=cwd)
            return r.returncode, r.stdout, r.stderr
        if argv[0] == "cf-readback":
            return (0, "deployment active", "") if self.cf_ok else (1, "", "not found")
        if argv[0] == "gw-event":
            ev = self.gw.get((argv[1], argv[2]))
            return (0, json.dumps(ev), "") if ev else (1, "", "no such event")
        if any(str(a).endswith("publish_preflight.py") for a in argv):
            if self.preflight_pass:
                return 0, json.dumps({"passed": True, "failed_dimensions": []}), ""
            return 2, json.dumps({"passed": False, "failed_dimensions": ["结构与格式"]}), ""
        if argv[:3] == ["npx", "--no-install", "hexo"]:
            if self.build_fail:
                return 1, "", "hexo exploded"
            post = next((Path(cwd) / "source/_posts").glob("*pairi*.md"))
            fm, body = be.split_frontmatter(post.read_text("utf-8"))
            import html
            page = Path(cwd) / "public/2026/10/20" / SLUG
            refs = ''.join(f'<img src="{u}">' for u in be.referenced_assets(be.load_config(), post.read_text("utf-8"), SLUG))
            write(page / "index.html", f'<html><h1>{html.escape(fm["title"])}</h1><article>{html.escape(body)}{refs}</article></html>')
            for u, src in be.referenced_assets(be.load_config(), post.read_text("utf-8"), SLUG).items():
                write(Path(cwd) / "public" / u.lstrip('/'), src.read_bytes())
            write(Path(cwd) / "_config.fluid.yml", "banner: build-side-effect\n")  # must be restored
            write(Path(cwd) / "image-credits.json", '{"hexo generate": "rewrote me"}')  # root file, also restored
            return 0, "ok", ""
        if argv[0] == "ps":
            r = subprocess.run(argv, capture_output=True, text=True)
            return r.returncode, r.stdout, r.stderr
        raise AssertionError(f"unexpected command {argv}")

    def fake_http(self, url, timeout=20):
        return self.http.get(url, (404, {}, b""))

    # ---- CLI
    def cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = be.main(list(argv))
        return code, json.loads(buf.getvalue())

    def origin(self, mid, user=USER, chat=CHAT, thread=THREAD, kind="direct"):
        return ["--chat-id", chat, "--thread-id", thread, "--user-id", user, "--message-id", str(mid),
                "--message-kind", kind]

    def state(self, rid):
        return json.loads((self.tmp / "state/runs" / rid / "run.json").read_text("utf-8"))

    # ---- flows
    def intake(self, mid=1, text="帮我写一下周末带孩子去 Pairi Daiza 的经历", key=SLUG, extra=()):
        return self.cli("intake", *self.origin(mid), "--text", text, "--article-key", key, *extra)

    def stage(self, rid, stage, content, adapt=None):
        code, ctx = self.cli("stage-context", "--run", rid, "--stage", stage)
        assert code == 0, ctx
        run = self.state(rid)
        rel = be.expected_output(run, stage)
        write(self.blogs / rel, content)
        args = ["record-stage", "--run", rid, "--stage", stage, "--file", rel, "--context-id", ctx["context_id"]]
        if adapt:
            args += ["--adaptations", adapt]
        return self.cli(*args), ctx

    def to_enhance(self, mid=1):
        _, r = self.intake(mid)
        rid = self.rid = r["run_id"]
        write(self.blogs / "50-assets/img/posts" / SLUG / "cover.webp", b"cover-bytes")
        write(self.blogs / "50-assets/img/posts" / SLUG / "panda.webp", b"panda-bytes")
        write(self.blogs / "50-assets/img/posts" / SLUG / "temp-unreferenced.tmp.webp", b"tmp")
        assert self.stage(rid, "research", "# research\n")[0][0] == 0
        assert self.cli("set-pipeline", "--run", rid, "--pipeline", "experience")[0] == 0
        assert self.stage(rid, "draft", "# draft\n")[0][0] == 0
        assert self.cli("finalize", *self.origin(mid + 1), "--run", rid, "--revision", "2")[0] == 0
        assert self.stage(rid, "enhance", ARTICLE, adapt="A1-todo-count,A3-image-count")[0][0] == 0
        return rid

    def say(self, mid, digest, session="s1", rid=None, **over):
        """Register a gateway-recorded inbound approval message."""
        ev = {"session_id": session, "message_id": str(mid), "sender_id": USER, "chat_id": CHAT, "thread_id": THREAD,
              "kind": "direct", "text": f"批准发布 {rid or self.rid} {digest}"}
        ev.update(over)
        self.gw[(session, str(mid))] = ev

    def approve(self, rid, mid=900):
        code, fr = self.cli("freeze", "--run", rid)
        assert code == 0, fr
        self.say(mid, fr["digest"])
        code, ap = self.cli("approve", "--run", rid, "--digest", fr["digest"], "--session-id", "s1", "--message-id", str(mid))
        assert code == 0, ap
        return fr["digest"]

    def coord_manifest(self, name, man):
        p = self.tmp / "state/coordinator" / name
        write(p, json.dumps(man))
        return str(p)


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.e = Env(self._td.name)

    def tearDown(self):
        self.e.close()
        self._td.cleanup()


class TestOriginAndIntake(Base):
    def test_unauthorized_origin_creates_nothing(self):
        for kw in ({"user": "999"}, {"thread": "1"}, {"chat": "-1"}, {"kind": "forwarded"}):
            code, out = self.e.cli("intake", *self.e.origin(5, **kw), "--text", "写一篇很长的文章吧", "--article-key", "x-a")
            self.assertEqual(code, 3, kw)
            self.assertEqual(out["error"] in ("unauthorized_origin", "non_direct_message"), True)
        self.assertFalse((self.e.tmp / "state/runs").exists() and any((self.e.tmp / "state/runs").iterdir()))
        audit = (self.e.tmp / "state/audit.jsonl").read_text("utf-8")
        self.assertNotIn("写一篇", audit)  # audit never stores message content

    def test_duplicate_event_and_article_idempotent(self):
        c1, r1 = self.e.intake(mid=10)
        c2, r2 = self.e.intake(mid=10)
        c3, r3 = self.e.intake(mid=11, text="补充：孩子很喜欢熊猫区域")
        self.assertEqual((r1["status"], r2["status"], r3["status"]), ("accepted", "duplicate_event", "existing_article"))
        self.assertEqual(len({r1["run_id"], r2["run_id"], r3["run_id"]}), 1)
        self.assertEqual(len(self.e.state(r1["run_id"])["inputs"]), 2)  # replay added nothing

    def test_greeting_does_not_create_article(self):
        for t in ("你好", "hi", "status", "在吗？"):
            code, out = self.e.cli("intake", *self.e.origin(20), "--text", t)
            self.assertEqual((code, out["status"]), (0, "no_article"))
        self.assertFalse((self.e.tmp / "state/runs").exists() and any((self.e.tmp / "state/runs").iterdir()))

    def test_ambiguous_mention_requires_choice(self):
        write(self.e.blogs / "40-notes/pairi-daiza-photos.md", "# Pairi Daiza photos\n")
        code, out = self.e.cli("intake", *self.e.origin(30), "--text", "写写上次去的那个动物园的事情吧", "--mention", "Pairi Daiza")
        self.assertEqual((code, out["error"]), (4, "ambiguous_mention"))
        self.assertEqual(len(out["candidates"]), 2)
        chosen = out["candidates"][0]["path"]
        code, out = self.e.cli("intake", *self.e.origin(30), "--text", "写写上次去的那个动物园的事情吧",
                               "--mention", "Pairi Daiza", "--source-path", chosen, "--article-key", SLUG)
        self.assertEqual((code, out["status"]), (0, "accepted"))
        self.assertEqual(out["sources"][0]["path"], chosen)

    def test_single_mention_binds_and_urls_untrusted(self):
        code, out = self.e.cli("intake", *self.e.origin(31), "--text", "看看 https://evil.example/x 这个然后写一篇关于游玩的文章",
                               "--mention", "Pairi Daiza trip", "--article-key", SLUG)
        self.assertEqual(code, 0)
        self.assertEqual(out["untrusted_urls"], ["https://evil.example/x"])
        self.assertTrue(out["sources"][0]["path"].endswith("pairi-daiza-trip.md"))
        c, ctx = self.e.cli("claim", "--run", out["run_id"])
        self.assertEqual(ctx["status"], "claimed")
        self.assertEqual(self.e.cli("claim", "--run", out["run_id"])[1]["status"], "already_claimed")
        code, ctx = self.e.cli("stage-context", "--run", out["run_id"], "--stage", "research")
        self.assertIn("UNTRUSTED URLs", Path(ctx["bundle_path"]).read_text("utf-8"))

    def test_source_path_outside_roots_refused(self):
        outside = self.e.tmp / "outside.md"
        write(outside, "secret")
        code, out = self.e.cli("intake", *self.e.origin(32), "--text", "写一篇文章关于这个材料", "--source-path", str(outside))
        self.assertEqual((code, out["error"]), (2, "source_outside_allowed_roots"))

    def test_voice_provenance_and_followup_needs_explicit_mapping(self):
        audio = self.e.tmp / "v.ogg"
        write(audio, b"OggS")
        _, r = self.e.cli("intake", *self.e.origin(40), "--voice-ref", str(audio), "--text", "语音转写：今天去了动物园",
                          "--transcript-source", "hermes-stt", "--article-key", SLUG)
        inp = self.e.state(r["run_id"])["inputs"][0]
        self.assertEqual(inp["kind"], "voice")
        self.assertEqual(inp["voice"]["transcript_source"], "hermes-stt")
        self.assertEqual(len(inp["voice"]["audio_sha256"]), 64)
        code, out = self.e.cli("intake", *self.e.origin(41), "--text", "再补一句话进去吧")
        self.assertEqual(code, 0)  # no run/reply => new article, never the latest one
        self.assertNotEqual(out.get("run_id"), r["run_id"])
        code, out = self.e.cli("intake", *self.e.origin(42), "--text", "补充", "--reply-to", "999")
        self.assertEqual((code, out["error"]), (4, "unknown_reply_target"))
        self.e.cli("bind-reply", "--run", r["run_id"], "--message-id", "500")
        code, out = self.e.cli("intake", *self.e.origin(43), "--text", "补充", "--reply-to", "500")
        self.assertEqual((out["status"], out["run_id"]), ("followup_recorded", r["run_id"]))


class TestCoordinatorIntake(Base):
    def man(self, **kw):
        m = {"kind": "coordinator-intake", "origin_kind": "coordinator-chat", "nonce": "ci-1",
             "source_ref": "codex-chat 2026-10-20", "article_key": SLUG, "text": "素材：Pairi Daiza 一日游，孩子很开心",
             "voice_ref": None, "transcript_source": "tts-fixture"}
        m.update(kw)
        return self.e.coord_manifest(f"{m['nonce']}.json", m)

    def test_labelled_not_telegram_one_use_and_no_publish_grant(self):
        code, out = self.e.cli("intake-coordinator", "--manifest", self.man())
        self.assertEqual((code, out["status"], out["origin_kind"], out["grants_publish"]), (0, "accepted", "coordinator-chat", False))
        run = self.e.state(out["run_id"])
        inp = run["inputs"][0]
        self.assertEqual((inp["trust"], inp["origin_kind"], inp["source_ref"]), ("coordinator-control-plane", "coordinator-chat", "codex-chat 2026-10-20"))
        self.assertEqual(inp["user_id"], "coordinator")
        replay = self.e.cli("intake-coordinator", "--manifest", self.man())[1]
        self.assertEqual((replay["status"], replay["run_id"]), ("already_intaken", out["run_id"]))
        # drafting works, publishing still needs freeze + trusted approval
        rid = out["run_id"]
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["error"], "approval_missing_or_stale") if run["article"] else None
        self.assertEqual(self.e.cli("status", "--run", rid)[1]["origin_kind"], "coordinator-chat")

    def test_rejects_telegram_label_outside_dir_and_synthetic_voice_marked(self):
        self.assertEqual(self.e.cli("intake-coordinator", "--manifest", self.man(nonce="ci-2", origin_kind="telegram"))[1]["error"], "manifest_wrong_kind")
        outside = self.e.tmp / "x.json"
        write(outside, "{}")
        self.assertEqual(self.e.cli("intake-coordinator", "--manifest", str(outside))[0], 3)
        audio = self.e.tmp / "s.ogg"
        write(audio, b"OggS")
        out = self.e.cli("intake-coordinator", "--manifest", self.man(nonce="ci-3", article_key="syn-voice", voice_ref=str(audio)))[1]
        self.assertEqual(self.e.state(out["run_id"])["inputs"][0]["voice"]["transcript_source"], "synthetic:tts-fixture")


class TestCoordinatorFinalizeAndRetry(Base):
    def test_intake_failure_leaves_nonce_unspent_and_relative_source_works(self):
        m = {"kind": "coordinator-intake", "origin_kind": "coordinator-chat", "nonce": "ci-r", "source_ref": "codex-chat",
             "article_key": SLUG, "text": "素材：Pairi Daiza 一日游，孩子很开心", "source_paths": ["40-notes/missing.md"]}
        mp = self.e.coord_manifest("ci-r.json", m)
        code, out = self.e.cli("intake-coordinator", "--manifest", mp)
        self.assertEqual(code, 2)  # still a plain refusal, not "nonce reused"
        self.assertNotEqual(out["error"], "manifest_nonce_reused")
        m["source_paths"] = ["40-notes/pairi-daiza-trip.md"]  # relative to blogs_root
        mp = self.e.coord_manifest("ci-r.json", m)
        code, out = self.e.cli("intake-coordinator", "--manifest", mp)
        self.assertEqual((code, out["status"]), (0, "accepted"))
        again = self.e.cli("intake-coordinator", "--manifest", mp)[1]
        self.assertEqual((again["status"], again["run_id"]), ("already_intaken", out["run_id"]))

    def fin(self, rid, rev, **kw):
        m = {"kind": "coordinator-finalize", "origin_kind": "coordinator-chat", "nonce": "cf-1", "source_ref": "codex-chat",
             "run_id": rid, "revision": rev, "authorization_source": "coordinator chat: user asked for unattended E2E"}
        m.update(kw)
        return self.e.coord_manifest(f"{m['nonce']}.json", m)

    def drafted(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        self.e.stage(rid, "research", "# r\n")
        self.e.cli("set-pipeline", "--run", rid, "--pipeline", "experience")
        self.e.stage(rid, "draft", "# d\n")
        return rid

    def test_finalize_coordinator_enables_enhance_but_grants_no_publish(self):
        rid = self.drafted()
        self.assertEqual(self.e.cli("stage-context", "--run", rid, "--stage", "enhance")[1]["error"], "draft_not_finalized")
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 1, nonce="cf-0"))[1]["error"], "stale_draft_revision")
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 2, authorization_source=""))[1]["error"], "manifest_missing_field")
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 2, origin_kind="telegram"))[1]["error"], "manifest_wrong_kind")
        outside = self.e.tmp / "f.json"
        write(outside, "{}")
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", str(outside))[0], 3)
        code, out = self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 2))
        self.assertEqual((code, out["status"], out["grants_publish"]), (0, "finalized", False))
        fz = self.e.state(rid)["finalization"]
        self.assertEqual((fz["origin_kind"], fz["source_ref"]), ("coordinator-chat", "codex-chat"))
        self.assertEqual(self.e.cli("stage-context", "--run", rid, "--stage", "enhance")[0], 0)
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 2))[1]["status"], "already_finalized")
        other = self.fin(rid, 2, nonce="cf-1", run_id="r-000000000000")
        self.assertEqual(self.e.cli("finalize-coordinator", "--manifest", other)[0], 2)
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 2)  # still needs freeze + trusted approval
        self.assertEqual(self.e.cli("status", "--run", rid)[1]["approvals"], [])

    def test_draft_change_after_coordinator_finalize_clears_it(self):
        rid = self.drafted()
        self.e.cli("finalize-coordinator", "--manifest", self.fin(rid, 2))
        self.e.stage(rid, "draft", "# d v2\n")
        st = self.e.state(rid)
        self.assertEqual((st["finalized_draft_rev"], st["finalization"]), (None, None))


class TestStages(Base):
    def test_context_manifest_and_missing_required(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        code, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "research")
        self.assertEqual(code, 0)
        paths = {f["path"] for f in ctx["files"]}
        self.assertTrue({"AGENTS.md", ".rules/project_prompt.md", "00-admin/commands/README.md"} <= paths)
        self.assertEqual(len([p for p in paths if "pipeline-" in p]), 3)  # pipeline unchosen => all three
        self.assertIn(hash_of(self.e.blogs / "AGENTS.md"), json.dumps(ctx))
        (self.e.blogs / ".rules/project_prompt.md").unlink()
        code, out = self.e.cli("stage-context", "--run", rid, "--stage", "research")
        self.assertEqual((code, out["error"]), (2, "missing_required_context"))

    def test_draft_requires_pipeline_and_enhance_requires_finalize(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        self.e.stage(rid, "research", "# r\n")
        self.assertEqual(self.e.cli("stage-context", "--run", rid, "--stage", "draft")[1]["error"], "pipeline_required")
        self.e.cli("set-pipeline", "--run", rid, "--pipeline", "learning")
        self.e.stage(rid, "draft", "# d\n")
        self.assertEqual(self.e.cli("stage-context", "--run", rid, "--stage", "enhance")[1]["error"], "draft_not_finalized")
        self.assertEqual(self.e.cli("finalize", *self.e.origin(60), "--run", rid, "--revision", "1")[1]["error"], "stale_draft_revision")

    def test_record_requires_context_and_known_adaptation_and_exact_path(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "research")
        rel = be.expected_output(self.e.state(rid), "research")
        write(self.e.blogs / rel, "# r\n")
        base = ["record-stage", "--run", rid, "--stage", "research", "--file", rel]
        self.assertEqual(self.e.cli(*base, "--context-id", "deadbeef0000")[1]["error"], "stage_context_required")
        self.assertEqual(self.e.cli(*base, "--context-id", ctx["context_id"], "--adaptations", "A9-evil")[1]["error"], "unknown_adaptation")
        write(self.e.blogs / "05-research/other.md", "x")
        self.assertEqual(self.e.cli("record-stage", "--run", rid, "--stage", "research", "--file", "05-research/other.md",
                                    "--context-id", ctx["context_id"])[1]["error"], "unexpected_output_path")

    def test_exact_commit_excludes_unrelated_staged_changes(self):
        _, r = self.e.intake()
        write(self.e.blogs / "40-notes/unrelated.md", "staged by someone else")
        git(self.e.blogs, "add", "40-notes/unrelated.md")
        (code, out), _ = self.e.stage(r["run_id"], "research", "# research\n")
        self.assertEqual(code, 0, out)
        files = git(self.e.blogs, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(files, ["05-research/pairi-daiza-day-research.md"])
        self.assertIn("40-notes/unrelated.md", git(self.e.blogs, "diff", "--cached", "--name-only"))  # still staged, uncommitted
        msg = git(self.e.blogs, "log", "-1", "--format=%B")
        self.assertIn(f"Blog-E2E-Run: {r['run_id']}", msg)
        self.assertIn("Blog-E2E-Revision: 1", msg)

    def test_unchanged_rerecord_makes_no_commit_and_resume_pending(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        (c1, o1), ctx = self.e.stage(rid, "research", "# research\n")
        head = git(self.e.blogs, "rev-parse", "HEAD")
        rel = be.expected_output(self.e.state(rid), "research")
        c2, o2 = self.e.cli("record-stage", "--run", rid, "--stage", "research", "--file", rel, "--context-id", ctx["context_id"])
        self.assertEqual(o2["status"], "unchanged")
        self.assertEqual(head, git(self.e.blogs, "rev-parse", "HEAD"))
        # simulate crash after journal but before commit: pending record, then re-run commits it without a new revision
        write(self.e.blogs / rel, "# research v2\n")
        real = be.commit_exact
        be.commit_exact = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("crash"))
        try:
            with self.assertRaises(RuntimeError):
                be.record_stage(be.load_config(), be.Store(be.load_config()), self.e.state(rid), "research", rel,
                                context_id=ctx["context_id"], adaptations=[], note="")
        finally:
            be.commit_exact = real
        self.assertEqual(self.e.state(rid)["stages"]["research"][-1]["state"], "pending_commit")
        c3, o3 = self.e.cli("record-stage", "--run", rid, "--stage", "research", "--file", rel, "--context-id", ctx["context_id"])
        st = self.e.state(rid)
        self.assertEqual((o3["status"], len(st["stages"]["research"]), st["revision"]), ("recorded", 2, 2))

    def test_path_traversal_and_symlink_escape(self):
        _, r = self.e.intake()
        rid = r["run_id"]
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "research")
        base = ["record-stage", "--run", rid, "--stage", "research", "--context-id", ctx["context_id"], "--file"]
        write(self.e.tmp / "evil.md", "x")
        self.assertEqual(self.e.cli(*base, "../evil.md")[1]["error"], "path_outside_root")
        self.assertEqual(self.e.cli(*base, str(self.e.tmp / "evil.md"))[1]["error"], "path_outside_root")
        os.symlink(self.e.tmp / "evil.md", self.e.blogs / "05-research" / "pairi-daiza-day-research.md") if (self.e.blogs / "05-research").exists() else None
        (self.e.blogs / "05-research").mkdir(exist_ok=True)
        link = self.e.blogs / "05-research/pairi-daiza-day-research.md"
        if not link.exists() and not link.is_symlink():
            os.symlink(self.e.tmp / "evil.md", link)
        self.assertEqual(self.e.cli(*base, "05-research/pairi-daiza-day-research.md")[1]["error"], "symlink_in_path")

    def test_asset_ref_traversal_and_foreign_slug_refused(self):
        cfg = be.load_config()
        with self.assertRaises(be.Refuse) as c:
            be.referenced_assets(cfg, "![](/img/posts/pairi-daiza-day/../../../x.png)", SLUG)
        self.assertEqual(c.exception.reason, "asset_path_traversal")
        with self.assertRaises(be.Refuse) as c:
            be.referenced_assets(cfg, "![](/img/posts/other-post/a.png)", SLUG)
        self.assertEqual(c.exception.reason, "asset_foreign_slug")
        # external CDN URL containing /img/posts is not a local ref
        self.assertEqual(be.referenced_assets(cfg, "![](https://cdn.example/img/posts/zzz/a.png)", SLUG), {})

    def test_revise_binds_to_version_and_dedupes_message(self):
        rid = self.e.to_enhance()
        run = self.e.state(rid)
        rel = be.expected_output(run, "enhance")
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "enhance")
        write(self.e.blogs / rel, ARTICLE + "\n补一句。\n")
        args = ["revise", *self.e.origin(70), "--run", rid, "--stage", "enhance", "--file", rel,
                "--context-id", ctx["context_id"], "--text", "口述：加一句"]
        c, bad = self.e.cli(*args, "--base-revision", "1")
        self.assertEqual(bad["error"], "stale_base_revision")
        c, ok = self.e.cli(*args, "--base-revision", str(run["stages"]["enhance"][-1]["rev"]))
        self.assertEqual(ok["status"], "recorded")
        c, dup = self.e.cli(*args, "--base-revision", "99")
        self.assertEqual(dup["status"], "duplicate_event")
        self.assertTrue(list((self.e.tmp / "state/runs" / rid / "revisions").glob("*.diff")))


class TestApprovalAndPublish(Base):
    def test_publish_needs_explicit_flag_and_approval(self):
        rid = self.e.to_enhance()
        self.assertEqual(self.e.cli("publish", "--run", rid)[1]["error"], "explicit_publish_required")
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["error"], "approval_missing_or_stale")
        self.assertEqual(self.e.pushes, 0)

    def test_happy_path_exact_scope_and_unreferenced_excluded(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual(code, 0, out)
        files = set(git(self.e.repo, "show", "--name-only", "--format=", "HEAD").split())
        self.assertEqual(files, {"source/_posts/2026-10-20-pairi-daiza-day.md" if False else
                                 "source/_posts/" + Path(out["published_rel"]).name,
                                 "source/img/posts/pairi-daiza-day/cover.webp", "source/img/posts/pairi-daiza-day/panda.webp"})
        self.assertFalse((self.e.repo / "source/img/posts/pairi-daiza-day/temp-unreferenced.tmp.webp").exists())
        self.assertEqual(git(self.e.repo, "rev-parse", "HEAD"), git(self.e.remote, "rev-parse", "master"))
        self.assertEqual((self.e.repo / "_config.fluid.yml").read_text(), "banner: old\n")  # side effect restored
        self.assertEqual((self.e.repo / "image-credits.json").read_text(), '{"old": 1}')
        self.assertEqual(git(self.e.repo, "status", "--porcelain", "--untracked-files=no").strip(), "")
        self.assertTrue(git(self.e.blogs, "ls-files", out["published_rel"]).strip())  # formal copy committed in Blogs
        self.assertEqual(out["url_path"], f"/2026/10/20/{SLUG}/")
        # replay is a no-op
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["status"], "already_published")
        self.assertEqual(self.e.pushes, 1)

    def test_unknown_staged_change_in_publish_repo_refused_before_copy(self):
        rid = self.e.to_enhance()
        write(self.e.repo / "README.md", "someone's staged edit")
        git(self.e.repo, "add", "README.md")
        self.e.approve(rid)
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "unexpected_staged_changes"))
        self.assertFalse(list((self.e.repo / "source/_posts").glob("*pairi*")))  # nothing copied
        self.assertEqual(self.e.pushes, 0)
        git(self.e.repo, "reset", "-q")  # operator clears it; same journal resumes
        (self.e.repo / "README.md").unlink()
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)

    def test_dirty_target_files_never_overwritten(self):
        for kind in ("untracked_post", "dirty_asset"):
            self.tearDown()
            self.setUp()
            rid = self.e.to_enhance()
            if kind == "untracked_post":
                post = self.e.repo / "source/_posts" / f"2026-10-20-{SLUG}.md"
                write(post, "my hand-written draft")
            else:
                asset = self.e.repo / "source/img/posts" / SLUG / "cover.webp"
                write(asset, b"v1")
                git(self.e.repo, "add", "-A")
                git(self.e.repo, "commit", "-qm", "asset")
                git(self.e.repo, "push", "-q", "origin", "master")
                write(asset, b"uncommitted local edit")
            self.e.approve(rid)
            code, out = self.e.cli("publish", "--run", rid, "--publish")
            self.assertEqual((code, out["error"]), (2, "target_paths_dirty"), kind)
            if kind == "untracked_post":
                self.assertEqual(post.read_text(), "my hand-written draft")
            else:
                self.assertEqual(asset.read_bytes(), b"uncommitted local edit")
            self.assertEqual(self.e.pushes, 0)

    def test_recovery_commit_trusts_files_not_trailer(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.e.push_mode = "timeout_lost"
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 5)
        pid = json.loads((self.e.tmp / "state/runs" / rid / "publish.json").read_text())["publish_id"]
        # Forge: replace the real publish commit by one that carries the trailer but different content.
        git(self.e.repo, "reset", "-q", "--hard", "origin/master")
        post = next((self.e.repo / "source/_posts").glob("*pairi*"), None)
        write(self.e.repo / "source/_posts" / f"2026-10-20-{SLUG}.md", "FORGED CONTENT")
        git(self.e.repo, "add", "-A")
        git(self.e.repo, "commit", "-qm", f"forged\n\nBlog-E2E-Publish: {pid}")
        # journal says commit not done yet only if we rewind it; simulate crash before journal write
        write(self.e.repo / "source/_posts" / f"2026-10-20-{SLUG}.md", ARTICLE)  # worktree looks right; the commit is not
        for img, b in (("cover.webp", b"cover-bytes"), ("panda.webp", b"panda-bytes")):
            write(self.e.repo / "source/img/posts" / SLUG / img, b)
        jp = self.e.tmp / "state/runs" / rid / "publish.json"
        j = json.loads(jp.read_text())
        j["phases"]["commit"] = {"state": "pending"}
        j["phases"]["push"] = {"state": "pending"}
        j["phases"]["copy"] = {"state": "done"}
        j["phases"]["build"] = {"state": "done"}
        jp.write_text(json.dumps(j))
        self.e.push_mode = "ok"
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "recovery_commit_unverified"))
        self.assertEqual(self.e.pushes, 1)  # only the earlier timed-out attempt; forged commit not pushed

    def test_stale_approval_after_asset_byte_edit(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        write(self.e.blogs / "50-assets/img/posts" / SLUG / "panda.webp", b"panda-bytes-EDITED")
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "approval_missing_or_stale"))
        self.assertEqual(self.e.pushes, 0)
        self.assertEqual(git(self.e.repo, "rev-parse", "HEAD"), git(self.e.repo, "rev-parse", "origin/master"))

    def test_mutation_invalidates_approval_and_old_digest_cannot_approve(self):
        rid = self.e.to_enhance()
        digest = self.e.approve(rid)
        rel = be.expected_output(self.e.state(rid), "enhance")
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "enhance")
        write(self.e.blogs / rel, ARTICLE + "\n新增一段。\n")
        self.e.cli("record-stage", "--run", rid, "--stage", "enhance", "--file", rel, "--context-id", ctx["context_id"])
        st = self.e.cli("status", "--run", rid)[1]
        self.assertEqual([a["state"] for a in st["approvals"]], ["invalidated"])
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["error"], "approval_missing_or_stale")
        self.e.say(901, digest)
        code, out = self.e.cli("approve", "--run", rid, "--digest", digest, "--session-id", "s1", "--message-id", "901")
        self.assertEqual(out["error"], "not_frozen")

    def test_ordinary_approve_verified_against_gateway_event(self):
        rid = self.e.to_enhance()
        _, fr = self.e.cli("freeze", "--run", rid)
        d = fr["digest"]
        base = ["approve", "--run", rid, "--digest", d, "--session-id", "s1"]
        self.assertEqual(self.e.cli(*base, "--message-id", "none")[1]["error"], "inbound_event_not_found")  # self-asserted ids prove nothing
        cases = {"sender": {"sender_id": "999"}, "origin": {"thread_id": "1"}, "not_direct": {"kind": "forwarded"},
                 "not_direct2": {"kind": "quoted"}, "not_direct3": {"kind": "web"},
                 "approval_text": {"text": "好的"}}
        for i, text in enumerate([
                f"不要批准发布 {rid} {d}", f"请勿批准发布 {rid} {d}", f"批准发布 {rid} {d[:12]}", f"批准发布 {rid} {d[:63]}",
                f"批准发布 {rid} {d} 但先别发", f"> 批准发布 {rid} {d}", f"我没说 批准发布 {rid} {d}", f"批准发布  {rid} {d}",
                f" 批准发布 {rid} {d}\n", f"批准发布 {rid} {d.upper()}", f"批准发布 r-000000000000 {d}",
                f"批准发布 {d}", f"approve {rid} {d}", f"批准 {rid} {d}", f"批准发布 {rid} {'0' * 64}"]):
            cases[f"text_{i}"] = {"text": text}
        for i, (name, over) in enumerate(cases.items()):
            self.e.say(1000 + i, d, **over)
            code, out = self.e.cli(*base, "--message-id", str(1000 + i))
            self.assertEqual((code, out["error"]), (3, "inbound_event_rejected"), name)
        self.e.say(960, d, session="other")  # event exists but for a different session
        self.assertEqual(self.e.cli(*base, "--message-id", "960")[1]["error"], "inbound_event_not_found")
        self.e.say(970, "0" * 64)
        self.e.gw[("s1", "970")]["text"] = f"批准发布 {rid} {d}"
        self.assertEqual(self.e.cli("approve", "--run", rid, "--digest", "0" * 64, "--session-id", "s1", "--message-id", "970")[1]["error"],
                         "inbound_event_rejected")
        self.e.say(980, d)
        self.assertEqual(self.e.cli(*base, "--message-id", "980")[0], 0)
        again = self.e.cli(*base, "--message-id", "980")  # replayed event returns the original approval
        self.assertEqual((again[0], again[1]["approval_id"]), (0, self.e.cli("status", "--run", rid)[1]["approvals"][0]["id"]))
        self.assertEqual(len(self.e.cli("status", "--run", rid)[1]["approvals"]), 1)

    def test_ordinary_approve_fails_closed_without_event_interface(self):
        rid = self.e.to_enhance()
        _, fr = self.e.cli("freeze", "--run", rid)
        cfg = json.loads(self.e.cfg_path.read_text())
        cfg.pop("gateway_events_cmd")
        write(self.e.cfg_path, json.dumps(cfg))
        self.e.say(990, fr["digest"])
        code, out = self.e.cli("approve", "--run", rid, "--digest", fr["digest"], "--session-id", "s1", "--message-id", "990")
        self.assertEqual((code, out["error"]), (2, "approve_unverifiable_fail_closed"))
        self.assertEqual(self.e.cli("status", "--run", rid)[1]["approvals"], [])
        # event lookup that errors out also never approves
        cfg["gateway_events_cmd"] = ["gw-event", "{session_id}", "{message_id}"]
        write(self.e.cfg_path, json.dumps(cfg))
        self.assertEqual(self.e.cli("approve", "--run", rid, "--digest", fr["digest"], "--session-id", "s1", "--message-id", "1")[0], 3)

    def test_one_use_manifest_bound_to_digest_and_nonce(self):
        rid = self.e.to_enhance()
        _, fr = self.e.cli("freeze", "--run", rid)
        man = {"kind": "one-use-chat-authorization", "run_id": rid, "digest": fr["digest"], "actor_user_id": USER,
               "scope": "publish", "target": {"site_url": "https://blog.example.test", "slug": SLUG},
               "nonce": "n-1", "granted_at": "2026-10-20T21:00:00Z"}
        mp = self.e.coord_manifest("m.json", man)
        outside = self.e.tmp / "content-supplied.json"
        write(outside, json.dumps(man))
        self.assertEqual(self.e.cli("import-authorization", "--manifest", str(outside))[1]["error"], "manifest_outside_coordinator_dir")
        write(self.e.blogs / "40-notes/planted.json", json.dumps(man))
        self.assertEqual(self.e.cli("import-authorization", "--manifest", str(self.e.blogs / "40-notes/planted.json"))[0], 3)
        bad = dict(man, digest="f" * 64, nonce="n-2")
        self.assertEqual(self.e.cli("import-authorization", "--manifest", self.e.coord_manifest("bad.json", bad))[1]["error"], "digest_mismatch")
        wrong_target = dict(man, nonce="n-3", target={"site_url": "https://evil.test", "slug": SLUG})
        self.assertEqual(self.e.cli("import-authorization", "--manifest", self.e.coord_manifest("wt.json", wrong_target))[1]["error"], "approval_target_mismatch")
        stranger = dict(man, nonce="n-4", actor_user_id="999")
        self.assertEqual(self.e.cli("import-authorization", "--manifest", self.e.coord_manifest("st.json", stranger))[0], 3)
        self.assertEqual(self.e.cli("import-authorization", "--manifest", mp)[0], 0)
        self.assertEqual(self.e.cli("import-authorization", "--manifest", mp)[1]["status"], "already_imported")
        self.assertEqual(len(self.e.cli("status", "--run", rid)[1]["approvals"]), 1)
        reuse = dict(man, digest="a" * 64)  # same nonce, different content: no second approval
        self.assertEqual(self.e.cli("import-authorization", "--manifest", self.e.coord_manifest("re.json", reuse))[0], 2)
        self.assertEqual(self.e.cli("import-authorization", "--manifest",
                                    self.e.coord_manifest("empty.json", dict(man, nonce="n-9", target={})))[1]["error"], "approval_target_mismatch")
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        # approval is consumed: a later content change cannot reuse it
        self.assertEqual(self.e.state(rid)["status"], "pushed")

    def test_preflight_fail_blocks_and_cannot_be_suppressed(self):
        rid = self.e.to_enhance()
        self.e.preflight_pass = False
        self.assertEqual(self.e.cli("validate", "--run", rid)[1]["error"], "validation_failed")
        self.e.approve(rid)
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "validation_failed"))
        self.assertEqual(self.e.pushes, 0)
        self.assertFalse(any("--skip-checks" in a for c in self.e.calls for a in c))
        # fixing the preflight resumes the same journal (approval already consumed by this attempt only)
        self.e.preflight_pass = True
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)

    def test_todo_residue_fails_validation_even_if_preflight_passes(self):
        rid = self.e.to_enhance()
        rel = be.expected_output(self.e.state(rid), "enhance")
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "enhance")
        write(self.e.blogs / rel, ARTICLE + "\n[TODO: 补充]\n")
        self.e.cli("record-stage", "--run", rid, "--stage", "enhance", "--file", rel, "--context-id", ctx["context_id"])
        code, out = self.e.cli("validate", "--run", rid)
        self.assertEqual(code, 2)
        self.assertIn("todo_residue", json.dumps(out))

    def test_build_failure_then_resume_single_commit_single_push(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.e.build_fail = True
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (5, "build_failed"))
        self.assertEqual(self.e.pushes, 0)
        self.assertEqual(git(self.e.repo, "rev-parse", "HEAD"), git(self.e.repo, "rev-parse", "origin/master"))
        self.assertEqual((self.e.repo / "_config.fluid.yml").read_text(), "banner: old\n")
        self.e.build_fail = False
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.e.pushes, 1)
        self.assertEqual(git(self.e.repo, "rev-list", "--count", "origin/master").strip(), "2")  # init + exactly one publish

    def test_push_timeout_after_remote_success_does_not_double_publish(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.e.push_mode = "timeout_after_success"
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (5, "push_timeout_unknown"))
        self.assertEqual(git(self.e.repo, "rev-parse", "HEAD"), git(self.e.remote, "rev-parse", "master"))  # it did land
        self.e.push_mode = "ok"
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.e.pushes, 1)  # resume saw the commit on origin and did not push again
        self.assertEqual(git(self.e.repo, "rev-list", "--count", "HEAD").strip(), "2")

    def test_push_timeout_lost_retries_same_commit(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.e.push_mode = "timeout_lost"
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 5)
        head = git(self.e.repo, "rev-parse", "HEAD")
        self.e.push_mode = "ok"
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        self.assertEqual(head, git(self.e.remote, "rev-parse", "master"))
        self.assertEqual(git(self.e.repo, "rev-list", "--count", "HEAD").strip(), "2")

    def test_content_change_during_interrupted_publish_requires_new_approval(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        write(self.e.blogs / "50-assets/img/posts" / SLUG / "cover.webp", b"cover-CHANGED")
        self.e.build_fail = False
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "resume_digest_changed"))
        self.assertEqual(self.e.pushes, 0)

    def test_diverged_publish_repo_refused(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        other = self.e.tmp / "other"
        subprocess.run(["git", "clone", "-q", str(self.e.remote), str(other)], check=True)
        git(other, "config", "user.email", "a@b.c")
        git(other, "config", "user.name", "o")
        write(other / "x.txt", "remote work")
        git(other, "add", "-A")
        git(other, "commit", "-qm", "remote")
        git(other, "push", "-q", "origin", "master")
        write(self.e.repo / "local.txt", "local work")
        git(self.e.repo, "add", "-A")
        git(self.e.repo, "commit", "-qm", "local")
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "publish_repo_diverged"))
        self.assertEqual(self.e.pushes, 0)


class TestPublishFaultInjection(Base):
    def pub(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        return rid

    def journal(self, rid):
        return json.loads((self.e.tmp / "state/runs" / rid / "publish.json").read_text())

    def test_crash_between_intent_and_approval_projection(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        ap = self.e.tmp / "state/runs" / rid / "approvals.json"
        apps = json.loads(ap.read_text())
        apps[0].update(state="valid", uses=0)  # journal exists, approval write "lost"
        ap.write_text(json.dumps(apps))
        self.e.build_fail = False
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        self.assertEqual(json.loads(ap.read_text())[0]["state"], "used")
        self.assertEqual(self.e.pushes, 1)

    def test_journal_done_but_run_projection_lost_does_not_republish(self):
        rid = self.pub()
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        rp = self.e.tmp / "state/runs" / rid / "run.json"
        run = json.loads(rp.read_text())
        run["published"], run["status"] = None, "publishing"
        rp.write_text(json.dumps(run))
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["status"]), (0, "already_published"))
        self.assertIsNotNone(self.e.state(rid)["published"])
        self.assertEqual((self.e.pushes, git(self.e.repo, "rev-list", "--count", "HEAD").strip()), (1, "2"))

    def test_commit_result_lives_in_phase_so_resume_after_push_failure_works(self):
        rid = self.pub()
        self.e.push_mode = "fail"
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 5)
        j = self.journal(rid)
        self.assertEqual(j["phases"]["commit"]["state"], "done")
        self.assertNotIn("commit", j)  # no second copy of the field to fall out of sync
        self.assertIn("url_path", j["phases"]["build"])
        self.e.push_mode = "ok"
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        self.assertEqual(git(self.e.repo, "rev-list", "--count", "HEAD").strip(), "2")

    def test_push_uses_exact_sha_not_moved_head(self):
        rid = self.pub()
        self.e.push_mode = "fail"
        self.e.cli("publish", "--run", rid, "--publish")
        commit = self.journal(rid)["phases"]["commit"]["commit"]
        write(self.e.repo / "extra.txt", "unauthorized later commit")
        git(self.e.repo, "add", "-A")
        git(self.e.repo, "commit", "-qm", "someone else")
        self.e.push_mode = "ok"
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.e.remote, "rev-parse", "master").strip(), commit)  # extra commit not published
        push_cmd = next(c for c in self.e.calls if "push" in c)
        self.assertIn(f"{commit}:refs/heads/master", push_cmd)
        self.assertNotIn("HEAD", " ".join(push_cmd).replace("-C", ""))

    def test_head_moved_before_commit_refused(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        write(self.e.repo / "extra.txt", "x")
        git(self.e.repo, "add", "extra.txt")
        git(self.e.repo, "commit", "-qm", "other work lands on branch")
        self.e.build_fail = False
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "head_moved"))
        self.assertEqual(self.e.pushes, 0)

    def test_branch_or_origin_drift_refused(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        git(self.e.repo, "checkout", "-q", "-b", "other")
        self.e.build_fail = False
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["error"], "resume_digest_changed")
        git(self.e.repo, "checkout", "-q", "master")
        git(self.e.repo, "remote", "set-url", "origin", str(self.e.tmp / "elsewhere.git"))
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[1]["error"], "resume_digest_changed")
        self.assertEqual(self.e.pushes, 0)

    def test_approval_bound_to_target_identity(self):
        rid = self.e.to_enhance()
        _, fr = self.e.cli("freeze", "--run", rid)
        self.assertEqual({"site_url", "repo_root", "origin", "branch"}, set(fr["target"]))
        git(self.e.repo, "remote", "set-url", "origin", "https://user:tok@example.test/x.git")
        self.assertEqual(self.e.cli("freeze", "--run", rid)[1]["target"]["origin"], "https://example.test/x.git")  # no credentials in digest input
        self.assertNotEqual(self.e.cli("freeze", "--run", rid)[1]["digest"], fr["digest"])

    def test_target_bytes_edited_after_copy_refused_before_commit(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        write(self.e.repo / "source/img/posts" / SLUG / "panda.webp", b"tampered")
        self.e.build_fail = False
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "target_bytes_changed"))
        self.assertEqual(self.e.pushes, 0)

    def test_commit_tree_tampered_before_push_refused(self):
        rid = self.pub()
        self.e.push_mode = "fail"
        self.e.cli("publish", "--run", rid, "--publish")
        git(self.e.repo, "reset", "-q", "--soft", "HEAD~1")
        write(self.e.repo / "source/img/posts" / SLUG / "panda.webp", b"tampered-in-commit")
        git(self.e.repo, "add", "-A")
        git(self.e.repo, "commit", "-qm", "amended")
        new = git(self.e.repo, "rev-parse", "HEAD").strip()
        jp = self.e.tmp / "state/runs" / rid / "publish.json"
        j = json.loads(jp.read_text())
        j["phases"]["commit"]["commit"] = new  # even a journal pointing at it cannot launder it
        jp.write_text(json.dumps(j))
        write(self.e.repo / "source/img/posts" / SLUG / "panda.webp", b"panda-bytes")
        self.e.push_mode = "ok"
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "recovery_commit_unverified"))
        self.assertNotEqual(git(self.e.remote, "rev-parse", "master").strip(), new)

    def test_revoked_or_deauthorized_approval_stops_resume(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        self.e.build_fail = False
        aid = self.e.cli("status", "--run", rid)[1]["approvals"][0]["id"]
        self.assertEqual(self.e.cli("revoke", "--run", rid, "--approval", aid)[0], 0)
        code, out = self.e.cli("publish", "--run", rid, "--publish")
        self.assertEqual((code, out["error"]), (2, "approval_revoked_or_invalid"))
        self.assertEqual(self.e.pushes, 0)

    def test_actor_removed_from_allowlist_stops_resume(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        cfg = json.loads(self.e.cfg_path.read_text())
        cfg["allowed_user_ids"] = ["7"]
        write(self.e.cfg_path, json.dumps(cfg))
        self.e.build_fail = False
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 3)
        self.assertEqual(self.e.pushes, 0)

    def test_mutation_during_interrupted_publish_invalidates_used_approval(self):
        rid = self.pub()
        self.e.build_fail = True
        self.e.cli("publish", "--run", rid, "--publish")
        rel = be.expected_output(self.e.state(rid), "enhance")
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "enhance")
        write(self.e.blogs / rel, ARTICLE + "\n后改。\n")
        self.e.cli("record-stage", "--run", rid, "--stage", "enhance", "--file", rel, "--context-id", ctx["context_id"])
        self.assertEqual(self.e.cli("status", "--run", rid)[1]["approvals"][0]["state"], "invalidated")
        self.e.build_fail = False
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 2)
        self.assertEqual(self.e.pushes, 0)


class TestBackupVerifyPreview(Base):
    def published(self):
        rid = self.e.to_enhance()
        self.e.approve(rid)
        self.assertEqual(self.e.cli("publish", "--run", rid, "--publish")[0], 0)
        return rid

    def test_backup_exact_preserves_unrelated_and_conflicts(self):
        rid = self.published()
        write(self.e.drive / "unrelated/keep.md", "drive-only")
        write(self.e.drive / "50-assets/img/posts" / SLUG / "panda.webp", b"DRIVE-SIDE-EDIT")  # unexplained difference
        code, out = self.e.cli("backup", "--run", rid)
        self.assertEqual((code, out["error"]), (5, "backup_partial"))
        res = {f["path"]: f["result"] for f in out["files"]}
        self.assertEqual(res["50-assets/img/posts/pairi-daiza-day/panda.webp"], "conflict_preserved")
        self.assertEqual(res["50-assets/img/posts/pairi-daiza-day/cover.webp"], "copied")
        self.assertEqual((self.e.drive / "50-assets/img/posts" / SLUG / "panda.webp").read_bytes(), b"DRIVE-SIDE-EDIT")
        self.assertEqual((self.e.drive / "unrelated/keep.md").read_text(), "drive-only")
        self.assertFalse((self.e.drive / "50-assets/img/posts" / SLUG / "temp-unreferenced.tmp.webp").exists())
        for p, r in res.items():
            if r == "copied":
                self.assertEqual(be.sha_file(self.e.drive / p), be.sha_file(self.e.blogs / p))
        # second run after the human resolves the conflict: idempotent, only unchanged/copied
        (self.e.drive / "50-assets/img/posts" / SLUG / "panda.webp").unlink()
        code, out = self.e.cli("backup", "--run", rid)
        self.assertEqual(code, 0)
        self.assertTrue(all(f["result"] in ("copied", "unchanged") for f in out["files"]))

    def test_backup_overwrites_only_our_own_earlier_revision(self):
        rid = self.e.to_enhance()
        self.assertEqual(self.e.cli("backup", "--run", rid)[0], 0)
        rel = be.expected_output(self.e.state(rid), "enhance")
        _, ctx = self.e.cli("stage-context", "--run", rid, "--stage", "enhance")
        write(self.e.blogs / rel, ARTICLE + "\n改动。\n")
        self.e.cli("record-stage", "--run", rid, "--stage", "enhance", "--file", rel, "--context-id", ctx["context_id"])
        code, out = self.e.cli("backup", "--run", rid)
        self.assertEqual(code, 0, out)
        self.assertEqual(be.sha_file(self.e.drive / rel), be.sha_file(self.e.blogs / rel))

    def test_backup_refuses_path_escape(self):
        rid = self.e.to_enhance()
        code, out = self.e.cli("backup", "--run", rid, "--extra", "../outside.md")
        self.assertEqual(out["error"], "path_outside_root")

    def test_verify_online_reads_back_text_and_image_bytes(self):
        rid = self.published()
        base = "https://blog.example.test"
        page = "<html><h1>Pairi Daiza 一日</h1><article><p>我们早上八点出发去了公园，孩子一路都很兴奋地看着窗外的风景。</p><p>回家的路上大家都睡着了，只有我还醒着看着夕阳慢慢落下去。</p><img src=\"/img/posts/pairi-daiza-day/cover.webp\"><img src=\"/img/posts/pairi-daiza-day/panda.webp\"></article></html>"
        self.e.http[base + f"/2026/10/20/{SLUG}/"] = (200, {}, page.encode())
        self.e.http[base + f"/img/posts/{SLUG}/cover.webp"] = (200, {"Content-Type": "image/webp"}, b"cover-bytes")
        self.e.http[base + f"/img/posts/{SLUG}/panda.webp"] = (200, {"Content-Type": "image/webp"}, b"WRONG")
        code, out = self.e.cli("verify-online", "--run", rid)
        self.assertEqual((code, out["error"]), (5, "online_verification_failed"))
        self.e.http[base + f"/img/posts/{SLUG}/panda.webp"] = (200, {"Content-Type": "image/webp"}, b"panda-bytes")
        # public ok but no deployment reader configured: partial, never plain "verified"
        code, out = self.e.cli("verify-online", "--run", rid)
        self.assertEqual((code, out["error"], out["verdict"], out["public_ok"]), (5, "verification_partial", "partial_public_only", True))
        self.assertEqual(self.e.state(rid)["status"], "public_verified_deploy_unconfirmed")
        cfg = json.loads(self.e.cfg_path.read_text())
        cfg["cf_deploy_readback_cmd"] = ["cf-readback", "{project}", "{commit}"]
        write(self.e.cfg_path, json.dumps(cfg))
        self.e.cf_ok = False  # reader configured but failing
        code, out = self.e.cli("verify-online", "--run", rid)
        self.assertEqual((code, out["verdict"], out["deploy_readback"]["state"]), (5, "partial_public_only", "failed"))
        self.e.cf_ok = True
        code, out = self.e.cli("verify-online", "--run", rid)
        self.assertEqual((code, out["status"], out["deploy_readback"]["state"]), (0, "verified", "ok"))
        self.assertEqual(self.e.state(rid)["status"], "verified")

    def test_preview_unsupported_without_build_and_serves_single_page_then_cleans_up(self):
        rid = self.e.to_enhance()
        self.assertEqual(self.e.cli("preview", "probe")[1]["public_tunnel"], "unsupported_tonight")
        self.assertEqual(self.e.cli("preview", "start", "--run", rid)[1]["status"], "unsupported")
        self.e.approve(rid)
        self.e.cli("publish", "--run", rid, "--publish")
        write(self.e.repo / "public/admin-secret.txt", "must not be served")
        code, out = self.e.cli("preview", "start", "--run", rid)
        self.assertEqual((code, out["status"]), (0, "serving"))
        try:
            import urllib.request
            import urllib.error
            port = int(out["url"].split(":")[2].split("/")[0])
            with urllib.request.urlopen(out["url"], timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("noindex", response.headers["X-Robots-Tag"])
            root = f"http://127.0.0.1:{port}"
            for bad in ("/", "/admin-secret.txt", "/2026/"):
                with self.assertRaises(urllib.error.HTTPError, msg=bad) as c:
                    urllib.request.urlopen(root + bad, timeout=5)
                self.assertEqual(c.exception.code, 404)
        finally:
            stop = self.e.cli("preview", "stop")[1]
        self.assertEqual((stop["status"], stop["port_closed"], stop["dir_removed"]), ("stopped", True, True))


def hash_of(p):
    return be.sha_file(p)


if __name__ == "__main__":
    unittest.main()
