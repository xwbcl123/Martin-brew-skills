#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from human_review_sampling import PROTOCOL_ID, build_plan, canonical_hash, evaluate


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HumanRestoreReviewTests(unittest.TestCase):
    def test_aggressive_default_accept_with_one_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); audio = root / "source.wav"
            with wave.open(str(audio), "wb") as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(48000); handle.writeframes(b"\0\0" * 96000)
            policy = root / "policy.json"; policy.write_text(json.dumps({"buffer_policy": {"speech_inward_margin_ms": 0,
                "silence_inward_margin_ms": 0, "crossfade_ms": 0}, "human_restore_review": {"include_categories": ["filler"]}}))
            candidates = root / "candidates.json"; candidates.write_text(json.dumps({"episode_id": "fixture", "candidates": [
                {"candidate_id": "C1", "category": "filler", "core_interval": {"start_sample": 4800, "end_sample": 9600}},
                {"candidate_id": "C2", "category": "filler", "core_interval": {"start_sample": 24000, "end_sample": 28800}}]}))
            edl = root / "aggressive.json"
            subprocess.run([sys.executable, str(SCRIPTS / "build_aggressive_human_edl.py"), "--candidates", str(candidates),
                            "--policy", str(policy), "--render-audio", str(audio), "--output", str(edl)], check=True)
            edited = root / "edited.wav"; render_report = root / "render.json"
            subprocess.run([sys.executable, str(SCRIPTS / "render_sample_edl.py"), "--edl", str(edl),
                            "--output", str(edited), "--report", str(render_report)], check=True)
            preview = root / "review.html"
            subprocess.run([sys.executable, str(SCRIPTS / "render_human_restore_review.py"), "--edl", str(edl),
                            "--render-report", str(render_report), "--original-audio", str(audio),
                            "--edited-audio", str(edited), "--output", str(preview)], check=True)
            html = preview.read_text(); self.assertIn("Risk-Sampled H2 Review", html); self.assertIn("HCUT0001", html)
            self.assertIn("edited.pause()", html); self.assertIn("origin.pause()", html); self.assertIn("setTimeout", html)
            if shutil.which("node"):
                script = re.search(r"<script>(.*)</script>", html, re.DOTALL); self.assertIsNotNone(script)
                subprocess.run(["node", "--check"], input=script.group(1), text=True, check=True, capture_output=True)
            plan = build_plan(json.loads(edl.read_text()))
            decisions = [{"cut_id": "HCUT0001", "action": "accept_cut", "listened": True},
                         {"cut_id": "HCUT0002", "action": "restore_source", "listened": True}]
            receipt = root / "H2.json"; receipt.write_text(json.dumps({"schema_version": "1.1", "episode_id": "fixture",
                "gate": "H2-human-restore-review", "status": "approved", "review_complete": True,
                "edl_sha256": sha(edl), "render_report_sha256": sha(render_report), "edited_audio_sha256": sha(edited),
                "review_plan_sha256": canonical_hash(plan), "review_protocol_id": PROTOCOL_ID, "default_action": "accept_cut",
                "decisions": decisions, "sampling_evaluation": evaluate(plan, decisions),
                "reviewed_by": "Example Host", "reviewed_at": "2026-08-29T00:00:00+02:00", "publish_authorized": False}))
            recovered = root / "recovered.json"
            subprocess.run([sys.executable, str(SCRIPTS / "apply_human_restore_review.py"), "--edl", str(edl),
                            "--render-report", str(render_report), "--edited-audio", str(edited),
                            "--review", str(receipt), "--output", str(recovered)], check=True)
            value = json.loads(recovered.read_text()); self.assertEqual([item["cut_id"] for item in value["cuts"]], ["HCUT0001"])
            self.assertEqual(value["summary"]["restored_cut_ids"], ["HCUT0002"]); self.assertFalse(value["approved"])

    def test_incomplete_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); edited = root / "edited.wav"; edited.write_bytes(b"review-audio")
            interval = {"start_sample": 1, "end_sample": 2}
            cuts = [{"cut_id": cid, "candidate_ids": [cid], "categories": ["filler"], "core_intervals": [interval],
                     "proposed_interval": interval, "applied_interval": interval, "buffer_rule": "fixture",
                     "decision_status": "requires_h2_human_approval"} for cid in ("HCUT0001", "HCUT0002")]
            edl = root / "edl.json"; edl.write_text(json.dumps({"schema_version": "1.0", "episode_id": "fixture",
                "stage": "S07-buffered-edl", "status": "review_required", "run_key": "1" * 64,
                "timebase": {}, "source_audio": {}, "adjudication_sha256": "2" * 64, "policy_sha256": "3" * 64,
                "crossfade_samples": 0, "cuts": cuts, "summary": {}, "approved": False, "publish_authorized": False}))
            render_report = root / "render.json"; render_report.write_text(json.dumps({"edl": {"sha256": sha(edl)},
                "output_audio": {"sha256": sha(edited)}}))
            plan = build_plan(json.loads(edl.read_text())); decisions = [{"cut_id": "HCUT0001", "action": "accept_cut", "listened": True}]
            receipt = root / "H2.json"; receipt.write_text(json.dumps({"schema_version": "1.1", "episode_id": "fixture",
                "gate": "H2-human-restore-review", "status": "approved", "review_complete": True,
                "edl_sha256": sha(edl), "render_report_sha256": sha(render_report), "edited_audio_sha256": sha(edited),
                "review_plan_sha256": canonical_hash(plan), "review_protocol_id": PROTOCOL_ID, "default_action": "accept_cut",
                "decisions": decisions, "sampling_evaluation": evaluate(plan, decisions), "reviewed_by": "Example Host",
                "reviewed_at": "2026-08-29T00:00:00+02:00", "publish_authorized": False}))
            result = subprocess.run([sys.executable, str(SCRIPTS / "apply_human_restore_review.py"), "--edl", str(edl),
                "--render-report", str(render_report), "--edited-audio", str(edited), "--review", str(receipt),
                "--output", str(root / "out.json")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0); self.assertIn("canonical required sample", result.stdout + result.stderr)

    def test_two_restores_in_ten_sample_stratum_fail_closed(self) -> None:
        cuts = []
        for index in range(10):
            interval = {"start_sample": index * 10000 + 1, "end_sample": index * 10000 + 1001}
            cuts.append({"cut_id": f"HCUT{index+1:04d}", "candidate_ids": [f"C{index}"], "categories": ["filler"],
                         "core_intervals": [interval], "proposed_interval": interval, "applied_interval": interval,
                         "buffer_rule": "fixture", "decision_status": "requires_h2_human_approval"})
        plan = build_plan({"cuts": cuts})
        decisions = [{"cut_id": cut_id, "action": "restore_source" if index < 2 else "accept_cut", "listened": True}
                     for index, cut_id in enumerate(plan["required_review_cut_ids"])]
        result = evaluate(plan, decisions)
        self.assertFalse(result["sampling_passed"]); self.assertIn("low", result["failed_strata"])


if __name__ == "__main__": unittest.main()
