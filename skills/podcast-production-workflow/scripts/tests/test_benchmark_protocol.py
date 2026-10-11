import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "validate_benchmark_protocol.py"


def write(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BenchmarkProtocolTests(unittest.TestCase):
    def test_exact_hash_approval_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            generic = root / "generic.txt"; generic.write_text("frozen")
            alignment = root / "alignment.json"
            write(alignment, {"alignment_valid": True, "evidence": {"confident_reference_coverage": 0.96,
                  "anchor_residual_median_ms": 1, "anchor_residual_p95_ms": 2}})
            labels = root / "labels.json"
            write(labels, {"labels": [{"human_label": None, "reviewed_by": None}]})
            challenge = root / "challenge.json"
            write(challenge, {"label_blind": True, "filmora_reference_consumed": False})
            artifacts = {f"artifact_{i}": {"path": str(generic), "sha256": sha(generic)} for i in range(8)}
            artifacts.update({"filmora_alignment": {"path": str(alignment), "sha256": sha(alignment)},
                              "heldout_template": {"path": str(labels), "sha256": sha(labels)},
                              "challenge_set": {"path": str(challenge), "sha256": sha(challenge)}})
            protocol = {"schema_version": "1.0", "protocol_id": "odyssey-smart-edit-benchmark-v1", "revision": 1,
                        "status": "frozen_pending_h1", "episode_id": "20260822_odyssey", "frozen_artifacts": artifacts,
                        "labels": {"allowed": ["must_cut", "acceptable_cut", "must_keep"],
                                   "template_artifact": artifacts["heldout_template"],
                                   "opening_condition": "H1 approval bound to this protocol SHA-256",
                                   "filmora_action_is_not_human_label": True},
                        "primary_thresholds": {}, "timeline_thresholds": {"filmora_confident_coverage_min": 0.95,
                        "alignment_residual_median_ms_max": 20, "alignment_residual_p95_ms_max": 80},
                        "judge_stability": {}, "anti_leakage": {}, "generalization_claim": {}, "change_control": {},
                        "external_judge_dispatch_authorized": False, "publish_authorized": False}
            protocol_path = root / "protocol.json"; write(protocol_path, protocol)
            report = root / "report.json"
            base = [sys.executable, str(SCRIPT), "--protocol", str(protocol_path), "--report", str(report)]
            pending = subprocess.run(base, capture_output=True, text=True)
            self.assertEqual(pending.returncode, 1)
            self.assertTrue(json.loads(report.read_text())["protocol_valid"])
            approval = root / "approval.json"
            write(approval, {"gate": "H1-benchmark-protocol", "status": "approved", "approved_by": "Martin",
                             "protocol_sha256": sha(protocol_path)})
            accepted = subprocess.run([*base, "--approval", str(approval)], capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0)
            self.assertTrue(json.loads(report.read_text())["external_judge_dispatch_authorized"])

            protocol["protocol_id"] = "odyssey-smart-edit-benchmark-v2"
            protocol["revision"] = 2
            write(protocol_path, protocol)
            write(approval, {"gate": "H1-benchmark-protocol", "status": "approved", "approved_by": "Martin",
                             "protocol_sha256": sha(protocol_path)})
            revised = subprocess.run([*base, "--approval", str(approval)], capture_output=True, text=True)
            self.assertEqual(revised.returncode, 0)
            self.assertTrue(json.loads(report.read_text())["external_judge_dispatch_authorized"])


if __name__ == "__main__":
    unittest.main()
