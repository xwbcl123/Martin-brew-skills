#!/usr/bin/env python3
"""Synthetic-only local draft boundary tests; no model, network or live media."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import Mock

import jsonschema
import validate_agent_draft as draft
import validate_release_package as release

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "podcast-production-workflow/scripts"))
import transistor_draft_controller as adapter


class AgentDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with wave.open(str(self.root / "review.wav"), "wb") as wav:
            wav.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x00" * 480 * 4)
        (self.root / "evidence.txt").write_text("Independent fixture-only review; no listening claimed.")
        self.manifest = {
            "schema_version": "agent-draft-v1", "review_mode": "agent_draft",
            "episode_key": "20260905_fixture", "revision": 1, "producer_id": "producer-task",
            "artifacts": {"review_audio": self.artifact("review.wav")},
            "limitations": ["Synthetic fixture. No release master, subtitles or rights review."]}
        self.mp = self.write("agent-draft.json", self.manifest)
        self.auth = {"kind": "user_local_draft_authorization", "review_mode": "agent_draft",
                     "episode_key": self.manifest["episode_key"], "manifest_sha256": draft.sha256_file(self.mp),
                     "authorized_by": "user", "source_ref": "fixture-user-task-only",
                     "actions": ["validate_local", "preview_local"]}
        self.ap = self.write("authorization.json", self.auth)
        self.review = {"kind": "independent_agent_draft_review", "reviewer_id": "reviewer-task",
                       "producer_id": "producer-task", "episode_key": self.manifest["episode_key"],
                       "manifest_sha256": draft.sha256_file(self.mp),
                       "artifact_hashes": {"review_audio": self.artifact("review.wav")["sha256"]},
                       "verdict": "draft_acceptable", "coverage": "Fixture technical review only",
                       "evidence": self.artifact("evidence.txt")}
        self.rp = self.write("review.json", self.review)

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def artifact(self, name):
        return {"path": name, "sha256": draft.sha256_file(self.root / name)}

    def validate(self):
        return draft.validate(self.mp, self.ap, self.rp, draft.sha256_file(self.ap))

    def test_valid_draft_never_release(self):
        report = self.validate()
        self.assertTrue(report["draft_contract_passed"])
        for key in ("contract_passed", "human_preview_ready", "publish_authorized", "upload_authorized", "external_mutation_authorized"):
            self.assertIs(report[key], False)
        self.assertFalse(release.validate(self.mp)["contract_passed"])
        self.assertIn("NOT RELEASE ACCEPTED", draft.preview(self.mp, report, self.root / "preview.html"))

    def test_forged_human_approval_rejected(self):
        for field in ("approved_by", "human_approval", "publish_authorized"):
            with self.subTest(field=field):
                forged = dict(self.review, **{field: "approved"})
                self.write("review.json", forged)
                with self.assertRaises(jsonschema.ValidationError):
                    self.validate()

    def test_control_documents_cannot_be_review_evidence(self):
        for name in ("agent-draft.json", "authorization.json"):
            with self.subTest(name=name):
                self.review["evidence"] = self.artifact(name)
                self.write("review.json", self.review)
                with self.assertRaisesRegex(ValueError, "control documents"):
                    self.validate()
        self.write("another-control.json", {"kind": "control"})
        self.review["evidence"] = self.artifact("another-control.json")
        self.write("review.json", self.review)
        with self.assertRaisesRegex(ValueError, "dedicated Markdown or text"):
            self.validate()
        self.write("disguised-control.txt", self.manifest)
        self.review["evidence"] = self.artifact("disguised-control.txt")
        self.write("review.json", self.review)
        with self.assertRaisesRegex(ValueError, "JSON control data"):
            self.validate()

    def test_artifact_copy_or_hardlink_cannot_be_review_evidence(self):
        transcript = self.root / "transcript.txt"
        transcript.write_text("Source transcript, not independent review.")
        self.manifest["artifacts"]["transcript"] = self.artifact("transcript.txt")
        self.write("agent-draft.json", self.manifest)
        self.auth["manifest_sha256"] = draft.sha256_file(self.mp)
        self.write("authorization.json", self.auth)
        self.review["manifest_sha256"] = draft.sha256_file(self.mp)
        self.review["artifact_hashes"]["transcript"] = self.artifact("transcript.txt")["sha256"]
        for kind in ("copy", "hardlink"):
            with self.subTest(kind=kind):
                evidence = self.root / (kind + ".txt")
                if kind == "copy":
                    evidence.write_bytes(transcript.read_bytes())
                else:
                    evidence.hardlink_to(transcript)
                self.review["evidence"] = self.artifact(evidence.name)
                self.write("review.json", self.review)
                with self.assertRaisesRegex(ValueError, "duplicate artifact content"):
                    self.validate()

    def test_blank_coverage_limitations_and_evidence_rejected(self):
        self.review["coverage"] = " \n\t "
        self.write("review.json", self.review)
        with self.assertRaises(jsonschema.ValidationError):
            self.validate()
        self.review["coverage"] = "Actual bounded technical review"
        (self.root / "evidence.txt").write_text(" \n\t ")
        self.review["evidence"] = self.artifact("evidence.txt")
        self.write("review.json", self.review)
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            self.validate()
        self.manifest["limitations"] = [" \n\t "]
        self.write("agent-draft.json", self.manifest)
        with self.assertRaises(jsonschema.ValidationError):
            self.validate()

    def test_stale_audio_and_evidence(self):
        for name in ("review.wav", "evidence.txt"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                with self.assertRaisesRegex(ValueError, "Stale artifact hash"):
                    self.validate()
                path.write_bytes(original)

    def test_stale_manifest_review_and_authorization(self):
        self.manifest["revision"] = 2
        self.write("agent-draft.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "Stale manifest binding"):
            self.validate()

    def test_incomplete_hashes_and_self_review(self):
        for changes in ({"artifact_hashes": {"other": "0" * 64}}, {"reviewer_id": "producer-task"}):
            self.write("review.json", dict(self.review, **changes))
            with self.assertRaises(ValueError):
                self.validate()

    def test_wrong_episode_and_untrusted_authorization(self):
        with self.assertRaisesRegex(ValueError, "trusted task digest"):
            draft.validate(self.mp, self.ap, self.rp, "0" * 64)
        self.auth["episode_key"] = "20260906_other"
        self.write("authorization.json", self.auth)
        with self.assertRaisesRegex(ValueError, "Wrong episode"):
            self.validate()

    def test_external_actions_rejected(self):
        self.auth["actions"].append("upload")
        self.write("authorization.json", self.auth)
        with self.assertRaises(jsonschema.ValidationError):
            self.validate()

    def test_adapter_denies_even_forged_release_flags(self):
        report = dict(self.validate(), contract_passed=True, human_preview_ready=True, growth_ready=True)
        report_path = self.write("forged-report.json", report)
        with self.assertRaisesRegex(adapter.DraftError, "cannot enter"):
            adapter.local_contract(self.mp, report_path)
        runner = Mock()
        with self.assertRaisesRegex(adapter.DraftError, "cannot enter"):
            adapter.execute({"manifest": self.manifest, "report": report}, {}, binary="never",
                            receipt=self.root / "receipt.json", attempt=self.root / "attempt.json", runner=runner)
        runner.assert_not_called()
        self.assertFalse((self.root / "attempt.json").exists())

    def test_path_escape(self):
        self.review["evidence"]["path"] = "../outside.txt"
        self.write("review.json", self.review)
        with self.assertRaises(ValueError):
            self.validate()

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "evidence.txt"
            target.write_text("outside")
            (self.root / "escaped.txt").symlink_to(target)
            self.review["evidence"] = self.artifact("escaped.txt")
            self.write("review.json", self.review)
            with self.assertRaisesRegex(ValueError, "escapes package root"):
                self.validate()

    def test_truncated_pcm_rejected_even_with_current_hashes(self):
        audio = self.root / "review.wav"
        audio.write_bytes(audio.read_bytes()[:-4])
        self.manifest["artifacts"]["review_audio"] = self.artifact("review.wav")
        self.write("agent-draft.json", self.manifest)
        for record, name in ((self.auth, "authorization.json"), (self.review, "review.json")):
            record["manifest_sha256"] = draft.sha256_file(self.mp)
            if record is self.review:
                record["artifact_hashes"]["review_audio"] = self.artifact("review.wav")["sha256"]
            self.write(name, record)
        with self.assertRaisesRegex(ValueError, "Truncated PCM"):
            self.validate()

    def test_technical_invalid_rate(self):
        with wave.open(str(self.root / "review.wav"), "wb") as wav:
            wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x00" * 320)
        self.manifest["artifacts"]["review_audio"] = self.artifact("review.wav")
        self.write("agent-draft.json", self.manifest)
        for record, name in ((self.auth, "authorization.json"), (self.review, "review.json")):
            record["manifest_sha256"] = draft.sha256_file(self.mp)
            if record is self.review:
                record["artifact_hashes"]["review_audio"] = self.artifact("review.wav")["sha256"]
            self.write(name, record)
        with self.assertRaisesRegex(ValueError, "technical checks failed"):
            self.validate()

    def test_cli_opt_in_and_no_overwrite(self):
        output = self.root / "report.json"
        command = [sys.executable, str(Path(draft.__file__)), "--manifest", str(self.mp),
                   "--authorization", str(self.ap), "--authorization-sha256", draft.sha256_file(self.ap),
                   "--review", str(self.rp), "--report", str(output), "--preview", str(self.root / "preview.html")]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.assertFalse(output.exists())
        command += ["--review-mode", "agent_draft"]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        before = output.read_bytes()
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.assertEqual(before, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
