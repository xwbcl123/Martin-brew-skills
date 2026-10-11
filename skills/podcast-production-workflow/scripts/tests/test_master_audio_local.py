#!/usr/bin/env python3
"""Integration tests for the local two-pass mastering stage."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "master_audio_local.py"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MasterAudioLocalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.source = self.root / "selected-edit.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=12:sample_rate=48000",
                "-af",
                "volume=0.08",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(self.source),
            ],
            check=True,
        )
        self.approval = self.root / "H3a-approval.json"
        self.approval.write_text(
            json.dumps(
                {
                    "gate": "H3a-selected-edit-listen",
                    "status": "approved",
                    "selected_edit_sha256": sha256(self.source),
                    "listen_through": "complete",
                    "join_audit": "approved",
                    "approved_by": "fixture-reviewer",
                    "approved_at": "2026-08-24T10:00:00+02:00",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, approval: pathlib.Path | None = None) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--episode-id",
            "fixture-episode",
            "--selected-edit",
            str(self.source),
            "--editorial-approval",
            str(approval or self.approval),
            "--archive-master",
            str(self.root / "media" / "episode-master.wav"),
            "--release-mp3",
            str(self.root / "media" / "episode-release.mp3"),
            "--report",
            str(self.root / "qc" / "mastering-report.json"),
            "--log-dir",
            str(self.root / "logs"),
        ]

    def test_master_qc_and_cache_replay(self) -> None:
        first = subprocess.run(self.command(), check=False, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        report_path = self.root / "qc" / "mastering-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "technical_qc_passed_h3b_required")
        self.assertTrue(report["technical_qc_passed"])
        self.assertTrue(report["human_mastering_approval_required"])
        self.assertFalse(report["publish_authorized"])
        self.assertEqual(report["archive_master"]["probe"]["codec_name"], "pcm_s24le")
        self.assertEqual(report["release_audio"]["probe"]["codec_name"], "mp3")
        self.assertGreaterEqual(report["release_audio"]["probe"]["bit_rate"], 96000)
        self.assertLessEqual(abs(report["release_audio"]["loudness"]["integrated_lufs"] + 16.0), 1.0)
        self.assertLessEqual(report["release_audio"]["loudness"]["true_peak_dbtp"], -1.0)
        self.assertNotEqual(report["archive_master"]["sha256"], report["release_audio"]["sha256"])
        stable_hashes = (
            sha256(self.root / "media" / "episode-master.wav"),
            sha256(self.root / "media" / "episode-release.mp3"),
            sha256(report_path),
        )

        replay = subprocess.run(self.command(), check=False, capture_output=True, text=True)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        self.assertEqual(json.loads(replay.stdout)["status"], "skipped_cached")
        self.assertEqual(
            stable_hashes,
            (
                sha256(self.root / "media" / "episode-master.wav"),
                sha256(self.root / "media" / "episode-release.mp3"),
                sha256(report_path),
            ),
        )

    def test_rejects_approval_hash_mismatch_before_writes(self) -> None:
        bad_approval = self.root / "bad-approval.json"
        payload = json.loads(self.approval.read_text(encoding="utf-8"))
        payload["selected_edit_sha256"] = "0" * 64
        bad_approval.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(self.command(bad_approval), check=False, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact-hash", result.stdout + result.stderr)
        self.assertFalse((self.root / "media" / "episode-master.wav").exists())
        self.assertFalse((self.root / "media" / "episode-release.mp3").exists())
        self.assertFalse((self.root / "qc" / "mastering-report.json").exists())


if __name__ == "__main__":
    unittest.main()
