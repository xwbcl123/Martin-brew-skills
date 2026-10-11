import json
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "run_whisper_raw.py"


class RunWhisperRawTests(unittest.TestCase):
    def setup_fixture(self, root: pathlib.Path):
        audio = root / "analysis.wav"; audio.write_bytes(b"fixture-audio")
        model = root / "model.bin"; model.write_bytes(b"fixture-model")
        fake = root / "whisper-cli"
        fake.write_text("""#!/usr/bin/env python3
import json, pathlib, sys
if '--version' in sys.argv:
    print('whisper.cpp version: fixture-1.0')
    raise SystemExit(0)
base=pathlib.Path(sys.argv[sys.argv.index('-of')+1])
(pathlib.Path(str(base)+'.txt')).write_text('测试。\\n')
(pathlib.Path(str(base)+'.srt')).write_text('1\\n00:00:00,000 --> 00:00:01,000\\n测试。\\n')
(pathlib.Path(str(base)+'.vtt')).write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\n测试。\\n')
(pathlib.Path(str(base)+'.json')).write_text(json.dumps({'result':{'language':'zh'},'transcription':[{'offsets':{'from':0,'to':1000},'text':'测试。'}]}))
""")
        fake.chmod(0o755)
        output_base = root / "raw" / "episode"
        command = [sys.executable, str(SCRIPT), "--episode-id", "20260814_daily-reflection",
                   "--analysis-audio", str(audio), "--model", str(model), "--output-base", str(output_base),
                   "--report", str(root / "report.json"), "--log", str(root / "run.log"),
                   "--whisper-cli", str(fake), "--language", "zh"]
        return command, output_base

    def test_atomic_outputs_and_cache_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            command, output_base = self.setup_fixture(root)
            first = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
            second = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
            self.assertEqual(first["status"], "succeeded")
            self.assertEqual(second["status"], "skipped_cached")
            self.assertEqual(first["report_sha256"], second["report_sha256"])
            self.assertEqual(first["validation"]["segment_count"], 1)
            for extension in (".txt", ".srt", ".vtt", ".json"):
                self.assertTrue(pathlib.Path(str(output_base) + extension).is_file())

    def test_unverified_existing_raw_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            command, output_base = self.setup_fixture(root)
            output_base.parent.mkdir(parents=True)
            pathlib.Path(str(output_base) + ".txt").write_text("existing")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("immutable raw transcript outputs exist", result.stdout + result.stderr)

    def test_postcut_stage_requires_exact_h3b_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            command, output_base = self.setup_fixture(root)
            command.extend(["--stage", "S11a-postcut-whisper-raw"])
            missing = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("H3b", missing.stdout + missing.stderr)
            audio = root / "analysis.wav"
            approval = root / "H3b.json"
            payload = {"gate": "H3b-mastered-release-audio", "status": "approved",
                       "release_audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
                       "listen_through": "complete", "technical_qc": "approved",
                       "approved_by": "fixture-reviewer", "approved_at": "2026-08-24T12:00:00+02:00",
                       "publish_authorized": False}
            approval.write_text(json.dumps(payload), encoding="utf-8")
            approved_command = command + ["--release-approval", str(approval)]
            first = json.loads(subprocess.run(approved_command, check=True, capture_output=True, text=True).stdout)
            second = json.loads(subprocess.run(approved_command, check=True, capture_output=True, text=True).stdout)
            self.assertEqual(first["status"], "succeeded")
            self.assertEqual(second["status"], "skipped_cached")
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["stage"], "S11a-postcut-whisper-raw")
            self.assertEqual(report["inputs"]["release_audio"]["sha256"], payload["release_audio_sha256"])
            self.assertEqual(report["outputs"]["json"]["role"], "immutable-postcut-raw-whisper")
            self.assertFalse(report["publish_authorized"])


if __name__ == "__main__":
    unittest.main()
