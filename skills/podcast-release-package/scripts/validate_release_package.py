#!/usr/bin/env python3
"""Validate a Podcast Episode Release Package Contract v1.0."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "references" / "episode-package.schema.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GateBook:
    def __init__(self) -> None:
        self.gates: list[dict[str, Any]] = []
        self.warnings: list[dict[str, str]] = []

    def gate(self, gate_id: str, passed: bool, evidence: Any, remediation: str = "") -> None:
        item: dict[str, Any] = {
            "id": gate_id,
            "status": "passed" if passed else "failed",
            "evidence": evidence,
        }
        if not passed and remediation:
            item["remediation"] = remediation
        self.gates.append(item)

    def warn(self, warning_id: str, message: str) -> None:
        self.warnings.append({"id": warning_id, "message": message})

    def passed(self, gate_id: str) -> bool:
        return any(g["id"] == gate_id and g["status"] == "passed" for g in self.gates)

    @property
    def contract_passed(self) -> bool:
        return bool(self.gates) and all(g["status"] == "passed" for g in self.gates)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_payload_sha256(manifest: dict[str, Any]) -> str:
    payload = copy.deepcopy(manifest)
    approvals = payload.get("approvals")
    if isinstance(approvals, dict):
        approvals.pop("release_candidate", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(manifest: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment failure
        raise RuntimeError("Python package 'jsonschema' is required for contract validation.") from exc
    schema = read_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def resolve_inside(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe package-relative path: {relative}")
    root_real = root.resolve()
    resolved = (root / candidate).resolve(strict=must_exist)
    if resolved != root_real and root_real not in resolved.parents:
        raise ValueError(f"path escapes package root: {relative}")
    if must_exist and not resolved.is_file():
        raise ValueError(f"not a regular file: {relative}")
    return resolved


def artifact_check(root: Path, relative: str, expected_sha: str) -> tuple[bool, dict[str, Any], Path | None]:
    try:
        path = resolve_inside(root, relative)
        actual_sha = sha256_file(path)
        evidence = {
            "path": relative,
            "bytes": path.stat().st_size,
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
        }
        return actual_sha == expected_sha, evidence, path
    except (OSError, ValueError) as exc:
        return False, {"path": relative, "error": str(exc)}, None


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,bit_rate,format_name:stream=codec_name,codec_type,sample_rate,channels,width,height,pix_fmt",
        "-of", "json", str(path),
    ]
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)


def measure_loudness(path: Path) -> dict[str, float]:
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-16:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    matches = re.findall(r"\{\s*\"input_i\".*?\}", result.stderr, flags=re.DOTALL)
    if result.returncode != 0 or not matches:
        raise RuntimeError("ffmpeg loudness measurement failed")
    raw = json.loads(matches[-1])
    return {
        "integrated_lufs": float(raw["input_i"]),
        "true_peak_dbtp": float(raw["input_tp"]),
        "loudness_range_lu": float(raw["input_lra"]),
        "threshold_lufs": float(raw["input_thresh"]),
    }


def validate_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def clean_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def validate(manifest_path: Path) -> dict[str, Any]:
    book = GateBook()
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    root = manifest_path.parent.resolve()

    try:
        manifest = json.loads(manifest_bytes)
        if not isinstance(manifest, dict):
            raise ValueError("manifest root must be an object")
        errors = schema_errors(manifest)
    except Exception as exc:
        manifest = {}
        errors = [str(exc)]
    book.gate("G01_MANIFEST", not errors, {"manifest": str(manifest_path), "schema_errors": errors}, "Conform the manifest to episode-package.schema.json.")
    if errors:
        return build_report(book, manifest_path, manifest_sha, None, None, {})

    secret_hits = []
    serialized = json.dumps(manifest, ensure_ascii=False)
    for marker in ("x-api-key", "TRANSISTOR_API_KEY", "X-Amz-Signature", "presigned", "upload_url"):
        if marker.lower() in serialized.lower():
            secret_hits.append(marker)
    if secret_hits:
        book.gates[0]["status"] = "failed"
        book.gates[0]["evidence"]["secret_markers"] = secret_hits
        book.gates[0]["remediation"] = "Remove credentials and upload capabilities from the package."

    production = manifest["production"]
    provenance_ok = (
        SHA256_RE.fullmatch(production["source_sha256"]) is not None
        and len(production["run_key"]) >= 8
        and production["timeline_basis"] == "release-audio"
    )
    book.gate("G02_PROVENANCE", provenance_ok, production, "Record immutable source SHA-256, run key, basename, and release-audio timeline basis.")

    media = manifest["media"]
    release_ok, release_evidence, release_path = artifact_check(root, media["release_audio"], media["release_audio_sha256"])
    archive_ok, archive_evidence, archive_path = artifact_check(root, media["archive_master"], media["archive_master_sha256"])
    forbidden_roles = {"analysis", "review", "rough-cut", "raw"}
    release_role_ok = release_path is not None and not any(token in release_path.name.lower() for token in forbidden_roles)
    archive_role_ok = archive_path is not None and archive_path.suffix.lower() in {".wav", ".flac", ".aif", ".aiff"}
    g03_ok = release_ok and archive_ok and release_role_ok and archive_role_ok and release_path != archive_path
    book.gate(
        "G03_RELEASE_AUDIO", g03_ok,
        {"release": release_evidence, "archive": archive_evidence, "release_role_ok": release_role_ok, "archive_role_ok": archive_role_ok},
        "Provide a hash-matched final MP3 and a distinct lossless archive master; do not use raw/analysis/review audio.",
    )

    audio_metrics: dict[str, Any] = {}
    technical_ok = False
    if release_path and shutil.which("ffprobe") and shutil.which("ffmpeg"):
        try:
            probe = ffprobe(release_path)
            stream = next(s for s in probe["streams"] if s.get("codec_type") == "audio")
            duration = float(probe["format"]["duration"])
            bitrate = int(probe["format"].get("bit_rate") or 0)
            loudness = measure_loudness(release_path)
            audio_metrics = {
                "codec": stream.get("codec_name"),
                "sample_rate_hz": int(stream.get("sample_rate") or 0),
                "channels": int(stream.get("channels") or 0),
                "bit_rate_bps": bitrate,
                "duration_seconds": duration,
                **loudness,
            }
            technical_ok = (
                stream.get("codec_name") == "mp3"
                and audio_metrics["sample_rate_hz"] in {44100, 48000}
                and audio_metrics["channels"] in {1, 2}
                and bitrate >= 96000
                and abs(audio_metrics["integrated_lufs"] - media["target_lufs_i"]) <= 1.0
                and audio_metrics["true_peak_dbtp"] <= media["max_true_peak_dbtp"]
            )
        except Exception as exc:
            audio_metrics = {"error": str(exc)}
    else:
        audio_metrics = {"error": "ffmpeg and ffprobe are required"}
    book.gate("G04_AUDIO_TECHNICAL_QC", technical_ok, audio_metrics, "Render a 44.1/48 kHz MP3 at >=96 kbps, -16±1 LUFS, and <=-1 dBTP, then rerun QC.")

    approvals = manifest["approvals"]
    editorial = approvals["editorial"]
    editorial_ok = editorial["artifact_sha256"] == media["release_audio_sha256"] and validate_timestamp(editorial["approved_at"])
    book.gate("G05_EDITORIAL_QC", editorial_ok, editorial, "Approve the final listen-through against the exact release-audio SHA-256.")

    transcript = manifest["transcript"]
    text_ok, text_evidence, text_path = artifact_check(root, transcript["text_file"], transcript["text_sha256"])
    timed_ok, timed_evidence, timed_path = artifact_check(root, transcript["timed_file"], transcript["timed_sha256"])
    transcript_content_ok = False
    if text_path and timed_path:
        text_body = clean_text(text_path)
        timed_body = clean_text(timed_path)
        transcript_content_ok = (
            len(text_body) >= 500
            and timed_path.suffix.lower() in {".vtt", ".srt"}
            and ("-->" in timed_body)
            and transcript["audio_sha256"] == media["release_audio_sha256"]
            and transcript["language"] == manifest["show"]["language"]
            and approvals["transcript"]["artifact_sha256"] == transcript["text_sha256"]
            and validate_timestamp(approvals["transcript"]["approved_at"])
        )
    g06_ok = text_ok and timed_ok and transcript_content_ok
    book.gate("G06_TRANSCRIPT", g06_ok, {"text": text_evidence, "timed": timed_evidence, "approval": approvals["transcript"]}, "Provide approved canonical TXT and timed VTT/SRT bound to the release-audio hash.")

    chapters = manifest["chapters"]
    chapters_ok, chapter_evidence, chapter_path = artifact_check(root, chapters["file"], chapters["sha256"])
    chapter_semantics: dict[str, Any] = {}
    if chapter_path:
        try:
            chapter_doc = read_json(chapter_path)
            chapter_list = chapter_doc["chapters"] if isinstance(chapter_doc, dict) else chapter_doc
            starts = [float(item["start_seconds"]) for item in chapter_list]
            titles = [str(item["title"]).strip() for item in chapter_list]
            duration = float(audio_metrics.get("duration_seconds", 0))
            chapter_semantics = {"count": len(starts), "starts": starts, "duration_seconds": duration}
            chapters_ok = chapters_ok and (
                len(starts) >= 1
                and starts[0] <= 1.0
                and all(b > a for a, b in zip(starts, starts[1:]))
                and all(titles)
                and (duration <= 0 or starts[-1] < duration)
                and chapters["audio_sha256"] == media["release_audio_sha256"]
            )
        except Exception as exc:
            chapters_ok = False
            chapter_semantics = {"error": str(exc)}
    book.gate("G07_CHAPTERS", chapters_ok, {"artifact": chapter_evidence, "semantics": chapter_semantics}, "Regenerate approved, increasing chapters on the final release-audio timebase.")

    episode = manifest["episode"]
    summary_ok, summary_evidence, summary_path = artifact_check(root, episode["summary_file"], episode["summary_sha256"])
    description_ok, description_evidence, description_path = artifact_check(root, episode["description_file"], episode["description_sha256"])
    summary_length = len(clean_text(summary_path)) if summary_path else 0
    description_length = len(re.sub(r"<[^>]+>", " ", clean_text(description_path))) if description_path else 0
    hosts = [p for p in episode["participants"] if p["role"] == "host"]
    metadata_ok = (
        summary_ok and description_ok and 50 <= summary_length <= 1000 and description_length >= 200
        and len(hosts) >= 1 and episode["author"].strip() and manifest["provider"]["show_id"].strip()
    )
    book.gate("G08_METADATA", metadata_ok, {"summary": summary_evidence, "description": description_evidence, "summary_length": summary_length, "description_text_length": description_length, "host_count": len(hosts), "show_id": manifest["provider"]["show_id"]}, "Complete hash-matched listener metadata and at least one host; keep summary 50–1000 characters and show notes >=200 characters.")

    artwork = manifest["artwork"]
    art_ok, art_evidence, art_path = artifact_check(root, artwork["episode_file"], artwork["episode_sha256"])
    art_probe: dict[str, Any] = {}
    if art_path and shutil.which("ffprobe"):
        try:
            probe = ffprobe(art_path)
            stream = next(s for s in probe["streams"] if s.get("codec_type") == "video")
            width, height = int(stream["width"]), int(stream["height"])
            art_probe = {"width": width, "height": height, "bytes": art_path.stat().st_size, "suffix": art_path.suffix.lower()}
            art_ok = art_ok and width == height and 1400 <= width <= 3000 and art_path.stat().st_size <= 512 * 1024 and art_path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        except Exception as exc:
            art_ok = False
            art_probe = {"error": str(exc)}
    if art_path and shutil.which("sips"):
        result = subprocess.run(["sips", "-g", "space", str(art_path)], capture_output=True, text=True)
        art_probe["colorspace_rgb"] = "RGB" in result.stdout
        art_ok = art_ok and art_probe["colorspace_rgb"]
    elif art_path:
        book.warn("W_ARTWORK_COLORSPACE", "Could not independently verify RGB colorspace because sips is unavailable.")
    art_approval_ok = approvals["artwork"]["artifact_sha256"] == artwork["episode_sha256"] and validate_timestamp(approvals["artwork"]["approved_at"])
    book.gate("G09_ARTWORK", art_ok and art_approval_ok, {"artifact": art_evidence, "probe": art_probe, "approval": approvals["artwork"]}, "Provide approved square RGB artwork at 1400–3000 px and <=512 KB.")

    rights = manifest["rights"]
    rights_ok = all(
        item["status"] in {"cleared", "not_applicable"}
        and bool(item["reviewed_by"].strip())
        and validate_timestamp(item["reviewed_at"])
        for item in rights.values()
    )
    book.gate("G10_RIGHTS_CONSENT", rights_ok, rights, "Resolve content, music, artwork, and minor-consent status with named, timestamped review evidence.")

    promo = manifest["promo"]
    promo_ok, promo_evidence, promo_path = artifact_check(root, promo["launch_copy_file"], promo["launch_copy_sha256"])
    launch_copy = clean_text(promo_path) if promo_path else ""
    preview_relative = manifest["preview"]["output_file"]
    try:
        resolve_inside(root, preview_relative, must_exist=False)
        preview_path_ok = Path(preview_relative).suffix.lower() == ".html"
    except ValueError:
        preview_path_ok = False
    preview_inputs_ok = all(book.passed(gate) for gate in ("G03_RELEASE_AUDIO", "G04_AUDIO_TECHNICAL_QC", "G06_TRANSCRIPT", "G07_CHAPTERS", "G08_METADATA", "G09_ARTWORK")) and preview_path_ok
    book.gate("G11_PREVIEW_INPUTS", preview_inputs_ok, {"output_file": preview_relative, "path_safe": preview_path_ok}, "Fix accepted preview inputs and use a safe package-relative .html output path.")

    payload_sha = canonical_payload_sha256(manifest)
    release_approval = approvals["release_candidate"]
    release_approval_ok = (
        release_approval["payload_sha256"] == payload_sha
        and release_approval["release_audio_sha256"] == media["release_audio_sha256"]
        and validate_timestamp(release_approval["approved_at"])
    )
    mastering_ok = approvals["mastering"]["artifact_sha256"] == media["release_audio_sha256"] and validate_timestamp(approvals["mastering"]["approved_at"])
    g12_ok = release_approval_ok and mastering_ok
    book.gate("G12_RELEASE_CANDIDATE", g12_ok, {"expected_payload_sha256": payload_sha, "approval": release_approval, "mastering_approval": approvals["mastering"]}, "Approve the canonical release-candidate payload and exact release-audio hash after all upstream gates pass.")

    growth_ok = promo_ok and len(launch_copy) >= 100 and promo["share_url_placeholder"] in launch_copy
    if not growth_ok:
        book.warn("W_GROWTH_BASELINE", "Launch copy must be hash-matched, at least 100 characters, and contain {{share_url}}.")
    if promo.get("clip_manifest_file") is None:
        book.warn("W_OPTIONAL_CLIPS", "No clip manifest supplied; this does not block the core release contract.")

    report = build_report(book, manifest_path, manifest_sha, payload_sha, media["release_audio_sha256"], audio_metrics)
    report["human_preview_ready"] = preview_inputs_ok and book.contract_passed
    report["growth_ready"] = growth_ok and book.contract_passed
    return report


def build_report(
    book: GateBook,
    manifest_path: Path,
    manifest_sha: str,
    payload_sha: str | None,
    audio_sha: str | None,
    audio_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": "1.0",
        "contract_passed": book.contract_passed,
        "human_preview_ready": False,
        "growth_ready": False,
        "publish_authorized": False,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": manifest_sha,
        "release_candidate_payload_sha256": payload_sha,
        "release_audio_sha256": audio_sha,
        "audio_metrics": audio_metrics,
        "gates": book.gates,
        "warnings": book.warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = validate(args.manifest.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    atomic_json(args.report.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["contract_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
