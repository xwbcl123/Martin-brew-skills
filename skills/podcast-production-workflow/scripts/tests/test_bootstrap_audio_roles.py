import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import wave


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "bootstrap_audio_roles.py"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BootstrapAudioRolesTests(unittest.TestCase):
    def fixture(self, root: pathlib.Path):
        source = root / "source.wav"
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(2); handle.setsampwidth(2); handle.setframerate(48000)
            handle.writeframes(b"\0\0\0\0" * 48000)
        intake = root / "intake.json"
        intake.write_text(json.dumps({"schema_version": "1.0", "episode_id": "20260814_daily-reflection",
                                      "source": {"path": str(source), "sha256": sha256(source),
                                                 "bytes": source.stat().st_size, "role": "immutable_external_ssot"}}))
        command = [sys.executable, str(SCRIPT), "--intake", str(intake), "--manifest", str(root / "manifest.json"),
                   "--render", str(root / "render.wav"), "--analysis", str(root / "analysis.wav"),
                   "--report", str(root / "report.json")]
        return source, command

    def test_replay_is_hash_stable_and_cache_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source, command = self.fixture(root)
            first = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
            report_hash = first["report_sha256"]
            second = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
            self.assertEqual(first["cache"], "miss")
            self.assertEqual(second["cache"], "verified_hit")
            self.assertEqual(second["report_sha256"], report_hash)
            self.assertEqual(sha256(source), json.loads((root / "intake.json").read_text())["source"]["sha256"])
            report = json.loads((root / "report.json").read_text())
            self.assertTrue(report["source_immutable"])
            self.assertFalse(report["publish_authorized"])

    def test_source_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source, command = self.fixture(root)
            source.write_bytes(source.read_bytes() + b"tamper")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("immutable source identity mismatch", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
