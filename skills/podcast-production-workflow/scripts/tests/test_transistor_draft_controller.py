#!/usr/bin/env python3
"""Fail-closed tests for the Transistor draft controller."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "transistor_draft_controller.py"
SPEC = importlib.util.spec_from_file_location("transistor_draft_controller", SCRIPT)
assert SPEC and SPEC.loader
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)


class TransistorDraftControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(); self.root = pathlib.Path(self.temporary.name)
        for relative, content in {
            "media/episode-release.mp3": b"mp3-release",
            "metadata/summary.txt": "summary".encode(),
            "metadata/description.html": "<p>description</p>".encode(),
            "transcripts/transcript.txt": "verbatim".encode(),
        }.items():
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
        release_sha = controller.sha256(self.root / "media/episode-release.mp3")
        self.manifest = self.root / "manifest.json"
        manifest = {
            "episode_key": "20990101_fixture", "provider": {"name": "transistor", "show_id": "12345", "episode_id": None},
            "episode": {"title": "Fixture episode", "author": "Example Host", "summary_file": "metadata/summary.txt",
                        "description_file": "metadata/description.html", "explicit": False, "type": "full", "season": 1, "number": 2},
            "media": {"release_audio": "media/episode-release.mp3", "release_audio_sha256": release_sha},
            "transcript": {"text_file": "transcripts/transcript.txt"},
            "approvals": {"release_candidate": {"payload_sha256": "a" * 64}},
        }
        manifest["episode"]["summary_sha256"] = controller.sha256(self.root / "metadata/summary.txt")
        manifest["episode"]["description_sha256"] = controller.sha256(self.root / "metadata/description.html")
        manifest["transcript"]["text_sha256"] = controller.sha256(self.root / "transcripts/transcript.txt")
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        self.report = self.root / "acceptance-report.json"
        report = {"contract_passed": True, "human_preview_ready": True, "growth_ready": True, "publish_authorized": False,
                  "manifest_sha256": controller.sha256(self.manifest), "release_audio_sha256": release_sha,
                  "release_candidate_payload_sha256": "a" * 64,
                  "gates": [{"id": f"G{index:02d}", "status": "passed"} for index in range(1, 13)]}
        self.report.write_text(json.dumps(report), encoding="utf-8")
        self.context = controller.local_contract(self.manifest, self.report)
        self.approval = {"gate": "H6-transistor-draft-upload", "status": "approved", "episode_key": "20990101_fixture",
                         "show_id": "12345", "acceptance_report_sha256": controller.sha256(self.report),
                         "manifest_sha256": controller.sha256(self.manifest), "release_candidate_payload_sha256": "a" * 64,
                         "release_audio_sha256": release_sha, "approved_by": "Example Host",
                         "approved_at": "2026-08-24T12:00:00+02:00", "publish_authorized": False}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_approval_is_bound_to_all_acceptance_hashes(self) -> None:
        path = self.root / "approval.json"; path.write_text(json.dumps(self.approval), encoding="utf-8")
        validated = controller.validate_approval(path, self.context)
        self.assertEqual(validated["show_id"], "12345")
        payload = dict(self.approval); payload["release_audio_sha256"] = "0" * 64
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(controller.DraftError, "release_audio_sha256"):
            controller.validate_approval(path, self.context)

    def test_exact_duplicate_stops_before_attempt_or_mutation(self) -> None:
        commands: list[list[str]] = []
        def runner(command: list[str]) -> dict:
            commands.append(command)
            return {"data": [{"id": "existing", "attributes": {"title": "Fixture episode", "status": "draft"}}]}
        receipt = self.root / "receipt.json"; attempt = self.root / "attempt.json"
        with self.assertRaisesRegex(controller.DraftError, "existing"):
            controller.execute(self.context, self.approval, binary="transistor", receipt=receipt, attempt=attempt, runner=runner)
        self.assertEqual(len(commands), 1); self.assertFalse(attempt.exists()); self.assertFalse(receipt.exists())

    def test_successful_upload_create_and_readback_stops_at_draft(self) -> None:
        commands: list[list[str]] = []
        def runner(command: list[str]) -> dict:
            commands.append(command)
            if command[1:3] == ["episodes", "list"]: return {"data": []}
            if command[1:3] == ["episodes", "upload"]: return {"uploaded": True, "audio_url": "https://uploads.transistor.fm/fixture.mp3"}
            if command[1:3] == ["episodes", "create"] and "--dry-run" in command: return {"dry_run": True, "request": {"authentication": "environment"}}
            if command[1:3] == ["episodes", "create"]: return {"data": {"id": "12345", "attributes": {"status": "draft"}}}
            if command[1:3] == ["episodes", "get"]: return {"data": {"id": "12345", "attributes": {"title": "Fixture episode", "status": "draft"}}}
            raise AssertionError(command)
        receipt = self.root / "receipt.json"; attempt = self.root / "attempt.json"
        result = controller.execute(self.context, self.approval, binary="transistor", receipt=receipt, attempt=attempt, runner=runner)
        self.assertEqual(result["remote_episode_id"], "12345"); self.assertEqual(result["remote_status"], "draft")
        self.assertFalse(result["publish_authorized"]); self.assertTrue(receipt.is_file()); self.assertTrue(attempt.is_file())
        persisted = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertNotIn("audio_url", persisted); self.assertTrue(persisted["presigned_url_persisted"] is False)
        flattened = " ".join(part for command in commands for part in command)
        self.assertNotIn(" publish ", f" {flattened} "); self.assertNotIn("--yes", flattened)
        with self.assertRaises(controller.DraftError):
            controller.execute(self.context, self.approval, binary="transistor", receipt=receipt, attempt=attempt, runner=runner)

    def test_prior_attempt_blocks_all_remote_calls(self) -> None:
        attempt = self.root / "attempt.json"; attempt.write_text("{}", encoding="utf-8")
        called = False
        def runner(command: list[str]) -> dict:
            nonlocal called; called = True; return {}
        with self.assertRaisesRegex(controller.DraftError, "Reconcile"):
            controller.execute(self.context, self.approval, binary="transistor", receipt=self.root / "receipt.json",
                               attempt=attempt, runner=runner)
        self.assertFalse(called)

    def test_attempt_receipt_alias_denied_before_remote_call(self):
        commands = []
        receipt = self.root / "receipt.json"
        with self.assertRaisesRegex(controller.DraftError, "distinct resolved paths"):
            controller.execute(self.context, self.approval, binary="never", receipt=receipt,
                               attempt=self.root / "alias" / ".." / "receipt.json",
                               runner=lambda argv: commands.append(argv))
        self.assertEqual(commands, [])
        self.assertFalse(receipt.exists())

    def test_payload_mutation_during_probe_stops_before_upload(self):
        for relative in ("media/episode-release.mp3", "metadata/summary.txt", "metadata/description.html",
                         "transcripts/transcript.txt", "manifest.json", "acceptance-report.json"):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                calls = []
                def runner(command):
                    calls.append(command)
                    self.assertEqual(command[1:3], ["episodes", "list"])
                    path.write_bytes(original + b"changed during probe")
                    return {"data": []}
                attempt = self.root / "attempt.json"
                try:
                    with self.assertRaisesRegex(controller.DraftError, "identity changed"):
                        controller.execute(self.context, self.approval, binary="never",
                                           receipt=self.root / "receipt.json", attempt=attempt, runner=runner)
                    self.assertEqual(len(calls), 1)
                    self.assertFalse(attempt.exists())
                finally:
                    path.write_bytes(original)

    def test_provider_uses_snapshot_when_original_changes_at_upload(self):
        original_audio = self.context["release_audio"]
        expected = original_audio.read_bytes()
        seen = []
        def runner(command):
            if command[1:3] == ["episodes", "list"]:
                return {"data": []}
            if command[1:3] == ["episodes", "upload"]:
                original_audio.write_bytes(b"concurrent original modification")
                uploaded_path = pathlib.Path(command[3])
                self.assertNotEqual(uploaded_path, original_audio)
                self.assertEqual(uploaded_path.read_bytes(), expected)
                seen.append(uploaded_path)
                return {"audio_url": "https://uploads.transistor.fm/fixture.mp3"}
            if command[1:3] == ["episodes", "create"]:
                return {"data": {"id": "12345"}}
            return {"data": {"id": "12345", "attributes": {"title": "Fixture episode", "status": "draft"}}}
        result = controller.execute(self.context, self.approval, binary="never", receipt=self.root / "receipt.json",
                                    attempt=self.root / "attempt.json", runner=runner)
        self.assertEqual(result["release_audio_sha256"], self.approval["release_audio_sha256"])
        self.assertFalse(seen[0].exists())


if __name__ == "__main__":
    unittest.main()
