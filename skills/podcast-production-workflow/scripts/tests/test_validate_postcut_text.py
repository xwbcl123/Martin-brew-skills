#!/usr/bin/env python3
"""Integration tests for release-bound S11 text validation."""

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


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "validate_postcut_text.py"
RENDERER = pathlib.Path(__file__).resolve().parents[1] / "render_subtitle_review.py"
PROFILE = pathlib.Path(__file__).resolve().parents[2] / "references" / "subtitle-profile.zh-v1.json"


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ValidatePostcutTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(); self.root = pathlib.Path(self.temporary.name)
        self.audio = self.root / "release.mp3"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=5:sample_rate=48000", "-c:a", "libmp3lame", "-b:a", "128k", str(self.audio)], check=True)
        raw_base = self.root / "raw"
        outputs = {}
        for extension, content in {"txt": "原始逐字稿", "srt": "1\n00:00:00,000 --> 00:00:04,000\n原始逐字稿\n",
                                   "vtt": "WEBVTT\n\n00:00.000 --> 00:04.000\n原始逐字稿\n",
                                   "json": json.dumps({"result": {"language": "zh"}, "transcription": [{"offsets": {"from": 0, "to": 4000}, "text": "原始逐字稿"}]})}.items():
            path = pathlib.Path(str(raw_base) + "." + extension); path.write_text(content, encoding="utf-8")
            outputs[extension] = {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size, "role": "immutable-postcut-raw-whisper"}
        self.raw_report = self.root / "raw-report.json"
        self.raw_report.write_text(json.dumps({"episode_id": "fixture", "stage": "S11a-postcut-whisper-raw", "run_key": "r" * 64,
                                               "inputs": {"release_audio": {"sha256": sha(self.audio)}}, "outputs": outputs}), encoding="utf-8")
        self.verbatim = self.root / "verbatim.txt"; self.verbatim.write_text("Host：这是校准后的逐字稿。\n", encoding="utf-8")
        self.subs = self.root / "subs.vtt"; self.subs.write_text("WEBVTT\n\n00:00.000 --> 00:02.000\n这是校准后的\n\n00:02.000 --> 00:04.500\n逐字稿\n", encoding="utf-8")
        self.ledger = self.root / "ledger.json"
        self.ledger.write_text(json.dumps({"schema_version": "1.0", "episode_id": "fixture", "release_audio_sha256": sha(self.audio),
                                           "raw_transcript_json_sha256": outputs["json"]["sha256"], "terminology_sources": [],
                                           "corrections": [{"id": "C1", "start_ms": 0, "end_ms": 2000, "raw_text": "原始",
                                                            "corrected_text": "校准", "evidence": "fixture glossary", "confidence": "high", "status": "applied"}],
                                           "speaker_decisions": [{"range_start_ms": 0, "range_end_ms": 4500, "speaker": "Host",
                                                                  "evidence": "single-speaker fixture", "status": "assigned"}]}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, report: pathlib.Path, approval: pathlib.Path | None = None, final_video: pathlib.Path | None = None) -> list[str]:
        result = [sys.executable, str(SCRIPT), "--episode-id", "fixture", "--release-audio", str(self.audio),
                  "--raw-report", str(self.raw_report), "--verbatim", str(self.verbatim), "--subs", str(self.subs),
                  "--correction-ledger", str(self.ledger), "--report", str(report)]
        if final_video: result.extend(["--delivery-profile", "video", "--final-video", str(final_video)])
        if approval: result.extend(["--approval", str(approval)])
        return result

    def approval(self, final_video: pathlib.Path | None = None) -> dict:
        raw = json.loads(self.raw_report.read_text())
        payload = {"gate": "H4-postcut-text", "status": "approved", "episode_id": "fixture",
                "delivery_profile": "video" if final_video else "audio", "subtitle_profile_sha256": sha(PROFILE),
                "release_audio_sha256": sha(self.audio), "raw_transcript_json_sha256": raw["outputs"]["json"]["sha256"],
                "verbatim_sha256": sha(self.verbatim), "timed_subs_sha256": sha(self.subs),
                "correction_ledger_sha256": sha(self.ledger), "terminology_review": "approved", "speaker_review": "approved",
                "semantic_review": "approved", "timing_review": "approved", "approved_by": "fixture-reviewer",
                "approved_at": "2026-08-24T12:00:00+02:00", "publish_authorized": False}
        if final_video: payload.update({"final_video_sha256": sha(final_video), "subtitle_visual_review": "approved"})
        return payload

    def test_review_required_then_exact_h4_acceptance_and_cache(self) -> None:
        pending_report = self.root / "pending.json"
        pending = subprocess.run(self.command(pending_report), capture_output=True, text=True)
        self.assertEqual(pending.returncode, 1, pending.stdout + pending.stderr)
        self.assertEqual(json.loads(pending_report.read_text())["status"], "review_required")
        approval_path = self.root / "H4.json"; approval_path.write_text(json.dumps(self.approval()), encoding="utf-8")
        accepted_report = self.root / "accepted.json"
        first = subprocess.run(self.command(accepted_report, approval_path), check=True, capture_output=True, text=True)
        second = subprocess.run(self.command(accepted_report, approval_path), check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(first.stdout)["status"], "accepted")
        self.assertEqual(json.loads(second.stdout)["status"], "skipped_cached")
        accepted = json.loads(accepted_report.read_text())
        self.assertTrue(accepted["contract_text_ready"]); self.assertFalse(accepted["publish_authorized"])
        self.assertEqual(accepted["timeline_qc"]["cue_count"], 2)
        self.assertTrue(accepted["timeline_qc"]["passed"]); self.assertEqual(accepted["delivery_profile"], "audio")

    def test_wrong_audio_hash_approval_fails_closed(self) -> None:
        payload = self.approval(); payload["release_audio_sha256"] = "0" * 64
        approval_path = self.root / "bad-H4.json"; approval_path.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(self.command(self.root / "bad-report.json", approval_path), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0); self.assertIn("hash mismatch", result.stdout + result.stderr)
        self.assertFalse((self.root / "bad-report.json").exists())

    def test_video_profile_binds_final_video_and_visual_review(self) -> None:
        video = self.root / "final.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=black:s=320x180:d=5:r=25", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
        approval = self.root / "video-H4.json"; approval.write_text(json.dumps(self.approval(video)), encoding="utf-8")
        report = self.root / "video-report.json"
        subprocess.run(self.command(report, approval, video), check=True, capture_output=True, text=True)
        value = json.loads(report.read_text())
        self.assertEqual(value["delivery_profile"], "video"); self.assertTrue(value["video_ready"])
        self.assertEqual(value["final_video"]["sha256"], sha(video))
        preview = self.root / "subtitle-review.html"
        subprocess.run([sys.executable, str(RENDERER), "--validation-report", str(report), "--subs", str(self.subs),
                        "--output", str(preview)], check=True, capture_output=True, text=True)
        html = preview.read_text(); self.assertIn("Accurate Subtitle Review", html); self.assertIn("final_video_sha256", html)
        if shutil.which("node"):
            script = re.search(r"<script>(.*)</script>", html, re.DOTALL)
            self.assertIsNotNone(script)
            subprocess.run(["node", "--check"], input=script.group(1), text=True, check=True, capture_output=True)

    def test_h4_rejects_reading_speed_violation(self) -> None:
        self.subs.write_text("WEBVTT\n\n00:00.000 --> 00:00.500\n这是一行远远超过阅读速度限制的中文字幕内容\n", encoding="utf-8")
        payload = self.approval(); payload["timed_subs_sha256"] = sha(self.subs)
        approval = self.root / "fast-H4.json"; approval.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(self.command(self.root / "fast-report.json", approval), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0); self.assertIn("subtitle QC violations", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
