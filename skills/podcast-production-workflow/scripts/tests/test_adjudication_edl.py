import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import wave


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
ZERO = "0" * 64


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdjudicationEdlIntegrationTests(unittest.TestCase):
    def test_dual_cut_promotes_but_disagreement_stays_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            policy = {
                "decision_policy": {"cut_confidence_min": 0.8},
                "buffer_policy": {"speech_inward_margin_ms": 20, "silence_inward_margin_ms": 200,
                                  "crossfade_ms": 15, "merge_gap_ms": 0,
                                  "applied_interval_must_be_subset_of_core": True},
            }
            policy_path = root / "policy.json"
            write_json(policy_path, policy)
            policy_sha = digest(policy_path)
            candidates = []
            for cid, interval in [("C0001", (4800, 14400)), ("C0002", (20000, 28000))]:
                candidates.append({"schema_version": "1.0", "candidate_id": cid, "episode_id": "20260822_odyssey",
                                   "source_sha256": ZERO, "analysis_audio_sha256": ZERO,
                                   "timebase": {"basis": "source-audio", "sample_rate_hz": 48000},
                                   "category": "filler", "core_interval": {"start_sample": interval[0], "end_sample": interval[1]},
                                   "context": {"text_before": "前", "candidate_text": "嗯", "text_after": "后", "protected_tokens": []},
                                   "detector_evidence": [{"detector": "fixture"}], "policy_sha256": policy_sha})
            bundle = {"episode_id": "20260822_odyssey", "candidates": candidates}
            bundle_path = root / "candidates.json"
            write_json(bundle_path, bundle)

            packet_entries = []
            for candidate in candidates:
                packet = root / "packets" / f"{candidate['candidate_id']}.json"
                write_json(packet, candidate)
                packet_entries.append({"candidate_id": candidate["candidate_id"], "path": str(packet), "sha256": digest(packet)})
            index = root / "packet-index.json"
            write_json(index, {"packets": packet_entries})
            text_prompt, audio_prompt = "1" * 64, "2" * 64
            stability = {"schema_version": "1.0", "status": "passed", "challenge_set_sha256": "3" * 64,
                         "policy_sha256": policy_sha,
                         "text": {"model_id": "opus-fixture", "prompt_sha256": text_prompt, "runs_per_candidate": 3,
                                  "exact_label_agreement": 1.0, "passed": True},
                         "audio": {"model_id": "gemini-fixture", "prompt_sha256": audio_prompt, "runs_per_candidate": 3,
                                   "exact_label_agreement": 1.0, "passed": True}}
            stability_path = root / "stability.json"
            write_json(stability_path, stability)

            for role, prompt, model, verdicts in [
                ("text", text_prompt, "opus-fixture", {"C0001": "cut", "C0002": "cut"}),
                ("audio", audio_prompt, "gemini-fixture", {"C0001": "cut", "C0002": "keep"}),
            ]:
                directory = root / role
                directory.mkdir()
                for cid, verdict in verdicts.items():
                    raw = directory / f"{cid}-r1.raw.txt"
                    raw.write_text(f"fixture {role} {cid} {verdict}\n")
                    packet_sha = next(item["sha256"] for item in packet_entries if item["candidate_id"] == cid)
                    response = {"schema_version": "1.0", "candidate_id": cid, "judge_role": role,
                                "verdict": verdict, "confidence": 0.95, "reason": "synthetic fixture",
                                "quoted_evidence": [], "candidate_packet_sha256": packet_sha,
                                "prompt_sha256": prompt, "model_id": model, "cli_version": "fixture-1",
                                "raw_response_sha256": digest(raw)}
                    write_json(directory / f"{cid}-r1.json", response)

            adjudication = root / "adjudication.json"
            command = [sys.executable, str(SCRIPTS / "adjudicate_judges.py"), "--candidates", str(bundle_path),
                       "--policy", str(policy_path), "--stability-report", str(stability_path),
                       "--text-packet-index", str(index), "--audio-packet-index", str(index),
                       "--text-response-dir", str(root / "text"), "--audio-response-dir", str(root / "audio"),
                       "--output", str(adjudication)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            first_hash = digest(adjudication)
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual(digest(adjudication), first_hash)
            decisions = {item["candidate_id"]: item for item in json.loads(adjudication.read_text())["decisions"]}
            self.assertEqual(decisions["C0001"]["decision"], "auto_cut_eligible")
            self.assertEqual(decisions["C0002"]["decision"], "review_required")

            audio = root / "render.wav"
            with wave.open(str(audio), "wb") as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(48000)
                handle.writeframes(b"\0\0" * 48000)
            edl = root / "edl.json"
            subprocess.run([sys.executable, str(SCRIPTS / "build_buffered_edl.py"), "--candidates", str(bundle_path),
                            "--adjudication", str(adjudication), "--policy", str(policy_path),
                            "--render-audio", str(audio), "--output", str(edl)], check=True, capture_output=True, text=True)
            cut = json.loads(edl.read_text())["cuts"][0]
            self.assertEqual(cut["candidate_ids"], ["C0001"])
            self.assertEqual(cut["applied_interval"], {"start_sample": 5760, "end_sample": 13440})

            render = root / "review.wav"
            render_report = root / "render-report.json"
            render_command = [sys.executable, str(SCRIPTS / "render_sample_edl.py"), "--edl", str(edl),
                              "--output", str(render), "--report", str(render_report)]
            first_render = json.loads(subprocess.run(render_command, check=True, capture_output=True, text=True).stdout)
            second_render = json.loads(subprocess.run(render_command, check=True, capture_output=True, text=True).stdout)
            self.assertEqual(second_render["status"], "skipped_cached")
            self.assertEqual(first_render["output_sha256"], second_render["output_sha256"])
            report = json.loads(render_report.read_text())
            self.assertEqual(report["duration_accounting"]["expected_output_samples"], 39600)
            self.assertEqual(report["duration_accounting"]["error_samples"], 0)
            self.assertEqual(report["mapping"]["roundtrip_error_samples_non_transition_max"], 0)
            self.assertEqual(len(report["mapping"]["crossfade_transitions"]), 1)
            self.assertTrue(report["human_join_audit_required"])


if __name__ == "__main__":
    unittest.main()
