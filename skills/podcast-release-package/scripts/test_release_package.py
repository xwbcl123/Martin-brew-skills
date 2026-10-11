#!/usr/bin/env python3
"""Forward tests for the podcast release package skill."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from render_release_preview import atomic_text, render
from validate_release_package import atomic_json, canonical_payload_sha256, sha256_file, validate


ZERO = "0" * 64
APPROVED_AT = "2026-08-24T09:00:00+02:00"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_fixture(root: Path) -> Path:
    for directory in ("media", "metadata", "transcripts", "chapters", "artwork", "promo", "preview", "qc"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    master = root / "media/episode-master.wav"
    release = root / "media/episode-release.mp3"
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=12",
        "-af", "loudnorm=I=-16:TP=-1:LRA=11", "-ac", "1", "-c:a", "pcm_s24le", str(master),
    ])
    run(["ffmpeg", "-y", "-i", str(master), "-c:a", "libmp3lame", "-b:a", "128k", str(release)])

    artwork = root / "artwork/episode-artwork.jpg"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x10244f:s=1400x1400", "-frames:v", "1", "-q:v", "5", str(artwork)])

    summary = "这一期由 Example Host 主持，Sage 与 Felix 作为嘉宾，从家庭视角讨论英雄、战争、成长与归家，并呈现适合新听众理解的核心问题。"
    description = "<p>本期节目从家庭共同观看《奥德赛》的体验出发，讨论少年与成年人对英雄叙事、战争代价、责任选择和回归家园的不同理解，并通过具体对话帮助听众快速判断这一期是否值得完整收听。</p>" * 5
    transcript = ("Example Host：欢迎收听家庭时光胶囊播客。Sage：今天我们讨论英雄、战争与归家。Felix：我最关心少年如何理解选择与责任。\n" * 24).strip()
    vtt = "WEBVTT\n\n00:00.000 --> 00:04.000\n欢迎收听家庭时光胶囊播客。\n\n00:04.000 --> 00:08.000\n今天讨论英雄、战争与归家。\n\n00:08.000 --> 00:11.500\n少年如何理解选择与责任。\n"
    chapters = {"chapters": [
        {"start_seconds": 0, "title": "开场"},
        {"start_seconds": 4, "title": "英雄与战争"},
        {"start_seconds": 8, "title": "成长与归家"}
    ]}
    launch_copy = "家庭时光胶囊播客第一期已经准备就绪。本期由 Example Host、Sage 和 Felix 讨论《奥德赛》中的英雄、战争、成长与归家。正式发布后，请通过平台无关链接收听并分享：{{share_url}}"

    write(root / "metadata/summary.txt", summary)
    write(root / "metadata/description.html", description)
    write(root / "transcripts/transcript.txt", transcript)
    write(root / "transcripts/transcript.vtt", vtt)
    write(root / "chapters/chapters.json", json.dumps(chapters, ensure_ascii=False, indent=2) + "\n")
    write(root / "promo/launch-copy.md", launch_copy)

    audio_sha = sha256_file(release)
    transcript_sha = sha256_file(root / "transcripts/transcript.txt")
    artwork_sha = sha256_file(artwork)
    manifest = {
        "schema_version": "1.0",
        "episode_key": "20260824_contract-fixture",
        "package_revision": 1,
        "production": {"run_key": "fixture-run-20260824", "source_sha256": "1" * 64, "source_basename": "fixture.mov", "timeline_basis": "release-audio"},
        "provider": {"name": "transistor", "show_id": "12345", "episode_id": None},
        "show": {"title": "家庭时光胶囊播客", "language": "zh-CN"},
        "episode": {
            "title": "《奥德赛》：少年如何理解英雄、战争与归家",
            "author": "Example Host",
            "summary_file": "metadata/summary.txt",
            "summary_sha256": sha256_file(root / "metadata/summary.txt"),
            "description_file": "metadata/description.html",
            "description_sha256": sha256_file(root / "metadata/description.html"),
            "type": "full", "season": 1, "number": 1, "explicit": False,
            "participants": [
                {"name": "Example Host", "role": "host"},
                {"name": "Sage", "role": "guest"},
                {"name": "Felix", "role": "guest"}
            ],
            "alternate_url": None, "video_url": None, "keywords": None
        },
        "media": {
            "release_audio": "media/episode-release.mp3", "release_audio_sha256": audio_sha,
            "archive_master": "media/episode-master.wav", "archive_master_sha256": sha256_file(master),
            "target_lufs_i": -16.0, "max_true_peak_dbtp": -1.0
        },
        "transcript": {
            "text_file": "transcripts/transcript.txt", "text_sha256": transcript_sha,
            "timed_file": "transcripts/transcript.vtt", "timed_sha256": sha256_file(root / "transcripts/transcript.vtt"),
            "language": "zh-CN", "audio_sha256": audio_sha
        },
        "chapters": {"file": "chapters/chapters.json", "sha256": sha256_file(root / "chapters/chapters.json"), "audio_sha256": audio_sha},
        "artwork": {"episode_file": "artwork/episode-artwork.jpg", "episode_sha256": artwork_sha, "public_image_url": None},
        "promo": {"launch_copy_file": "promo/launch-copy.md", "launch_copy_sha256": sha256_file(root / "promo/launch-copy.md"), "share_url_placeholder": "{{share_url}}", "clip_manifest_file": None},
        "rights": {
            "content": {"status": "cleared", "reviewed_by": "Example Host", "reviewed_at": APPROVED_AT},
            "music": {"status": "not_applicable", "reviewed_by": "Example Host", "reviewed_at": APPROVED_AT},
            "artwork": {"status": "cleared", "reviewed_by": "Example Host", "reviewed_at": APPROVED_AT},
            "minor_consent": {"status": "cleared", "reviewed_by": "Example Host", "reviewed_at": APPROVED_AT}
        },
        "approvals": {
            "editorial": {"status": "approved", "approved_by": "Example Host", "approved_at": APPROVED_AT, "artifact_sha256": audio_sha},
            "transcript": {"status": "approved", "approved_by": "Example Host", "approved_at": APPROVED_AT, "artifact_sha256": transcript_sha},
            "mastering": {"status": "approved", "approved_by": "Example Host", "approved_at": APPROVED_AT, "artifact_sha256": audio_sha},
            "artwork": {"status": "approved", "approved_by": "Example Host", "approved_at": APPROVED_AT, "artifact_sha256": artwork_sha},
            "release_candidate": {"status": "approved", "approved_by": "Example Host", "approved_at": APPROVED_AT, "payload_sha256": ZERO, "release_audio_sha256": audio_sha}
        },
        "preview": {"output_file": "preview/episode-release-preview.html"}
    }
    manifest["approvals"]["release_candidate"]["payload_sha256"] = canonical_payload_sha256(manifest)
    manifest_path = root / "manifest.json"
    write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return manifest_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="podcast-release-package-test-") as temp:
        root = Path(temp)
        manifest_path = create_fixture(root)
        report_path = root / "qc/acceptance-report.json"

        report = validate(manifest_path)
        assert report["contract_passed"], json.dumps(report, ensure_ascii=False, indent=2)
        assert report["human_preview_ready"] is True
        assert report["growth_ready"] is True
        assert report["publish_authorized"] is False
        assert len(report["gates"]) == 12
        atomic_json(report_path, report)

        preview_path = root / "preview/episode-release-preview.html"
        preview = render(manifest_path, report_path, preview_path)
        atomic_text(preview_path, preview)
        assert "publication not authorized" in preview
        assert "Release audio SHA-256" in preview
        assert "FINAL PREFLIGHT · CONTRACT 12/12" in preview
        assert "Visual Assets" in preview
        assert "artwork/episode-artwork.jpg" in preview
        assert manifest_path.parent.joinpath("artwork/episode-artwork.jpg").name in preview
        assert "1400 × 1400 px" in preview
        assert preview == render(manifest_path, report_path, preview_path), "preview rendering must be deterministic"

        second_report = validate(manifest_path)
        assert report == second_report, "validator output must be deterministic"

        transcript_path = root / "transcripts/transcript.txt"
        transcript_path.write_text(transcript_path.read_text(encoding="utf-8") + "\n篡改", encoding="utf-8")
        failed = validate(manifest_path)
        assert failed["contract_passed"] is False
        failed_ids = {g["id"] for g in failed["gates"] if g["status"] == "failed"}
        assert "G06_TRANSCRIPT" in failed_ids

        try:
            render(manifest_path, report_path, preview_path)
        except ValueError as exc:
            assert "validation" in str(exc).lower()
        else:
            raise AssertionError("preview render must reject mutated accepted artifacts")

    print("PASS: valid package, deterministic replay, preview render, tamper rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
