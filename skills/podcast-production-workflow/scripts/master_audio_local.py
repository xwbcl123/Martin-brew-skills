#!/usr/bin/env python3
"""Two-pass local podcast mastering with exact editorial approval and fresh MP3 QC."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/mastering-report.schema.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        pathlib.Path(temporary_name).unlink(missing_ok=True); raise


def atomic_json(path: pathlib.Path, value: object) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def timestamp_valid(value: object) -> bool:
    if not isinstance(value, str): return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def probe(path: pathlib.Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration,bit_rate,format_name,size:stream=codec_name,sample_rate,channels",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout); stream = data["streams"][0]; fmt = data["format"]
    return {"codec_name": stream["codec_name"], "sample_rate_hz": int(stream["sample_rate"]),
            "channels": int(stream["channels"]), "duration_seconds": float(fmt["duration"]),
            "bit_rate": int(fmt.get("bit_rate") or 0), "bytes": int(fmt["size"]), "format_name": fmt["format_name"]}


def loudness(path: pathlib.Path, target_i: float, target_tp: float, target_lra: float) -> tuple[dict, str]:
    command = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
               f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json", "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    matches = re.findall(r"\{\s*\"input_i\".*?\}", result.stderr, flags=re.DOTALL)
    if result.returncode or not matches:
        raise RuntimeError("ffmpeg loudness measurement failed")
    raw = json.loads(matches[-1])
    metrics = {"integrated_lufs": float(raw["input_i"]), "true_peak_dbtp": float(raw["input_tp"]),
               "loudness_range_lu": float(raw["input_lra"]), "threshold_lufs": float(raw["input_thresh"]),
               "target_offset_lu": float(raw["target_offset"])}
    return metrics, result.stdout + result.stderr


def second_pass_filter(measured: dict, target_i: float, target_tp: float, target_lra: float) -> str:
    return (f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:"
            f"measured_I={measured['integrated_lufs']}:measured_LRA={measured['loudness_range_lu']}:"
            f"measured_TP={measured['true_peak_dbtp']}:measured_thresh={measured['threshold_lufs']}:"
            f"offset={measured['target_offset_lu']}:linear=true:print_format=json")


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--selected-edit", type=pathlib.Path, required=True)
    parser.add_argument("--editorial-approval", type=pathlib.Path, required=True)
    parser.add_argument("--archive-master", type=pathlib.Path, required=True)
    parser.add_argument("--release-mp3", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--log-dir", type=pathlib.Path, required=True)
    parser.add_argument("--target-lufs", type=float, default=-16.0)
    parser.add_argument("--target-true-peak", type=float, default=-1.5)
    parser.add_argument("--max-true-peak", type=float, default=-1.0)
    parser.add_argument("--target-lra", type=float, default=11.0)
    parser.add_argument("--mp3-bitrate", default="128k")
    args = parser.parse_args()
    selected_sha = sha256(args.selected_edit); approval = json.loads(args.editorial_approval.read_text())
    if not (approval.get("gate") == "H3a-selected-edit-listen" and approval.get("status") == "approved"
            and approval.get("selected_edit_sha256") == selected_sha and approval.get("listen_through") == "complete"
            and approval.get("join_audit") == "approved" and approval.get("approved_by")
            and timestamp_valid(approval.get("approved_at"))):
        raise SystemExit("valid H3a exact-hash full-listen/join approval required")
    input_probe = probe(args.selected_edit)
    if input_probe["sample_rate_hz"] != 48000 or input_probe["codec_name"] not in {"pcm_s16le", "pcm_s24le"}:
        raise SystemExit("selected edit must be a 48 kHz lossless PCM artifact")
    ffmpeg_version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    target = {"integrated_lufs": args.target_lufs, "normalization_true_peak_dbtp": args.target_true_peak,
              "contract_max_true_peak_dbtp": args.max_true_peak, "loudness_range_lu": args.target_lra,
              "mp3_bitrate": args.mp3_bitrate}
    run_key = canonical_hash({"stage": "S10-local-two-pass-mastering-v1", "selected_edit": selected_sha,
                              "editorial_approval": sha256(args.editorial_approval), "target": target,
                              "ffmpeg": ffmpeg_version})
    if args.report.is_file() and args.archive_master.is_file() and args.release_mp3.is_file():
        existing = json.loads(args.report.read_text())
        if (existing.get("run_key") == run_key and existing["archive_master"]["sha256"] == sha256(args.archive_master)
                and existing["release_audio"]["sha256"] == sha256(args.release_mp3)):
            print(json.dumps({"status": "skipped_cached", "run_key": run_key,
                              "archive_master_sha256": sha256(args.archive_master),
                              "release_audio_sha256": sha256(args.release_mp3),
                              "report_sha256": sha256(args.report), "publish_authorized": False}, indent=2)); return
    if any(path.exists() for path in (args.archive_master, args.release_mp3, args.report)):
        raise SystemExit("unverified mastering output exists; choose a new revision path")
    args.log_dir.mkdir(parents=True, exist_ok=True)
    measured, pass1_log = loudness(args.selected_edit, args.target_lufs, args.target_true_peak, args.target_lra)
    pass1_path = args.log_dir / "pass1-measurement.log"; atomic_text(pass1_path, pass1_log)
    args.archive_master.parent.mkdir(parents=True, exist_ok=True); args.release_mp3.parent.mkdir(parents=True, exist_ok=True)
    partial_master = args.archive_master.parent / f".{args.archive_master.name}.{run_key[:12]}.partial.wav"
    partial_mp3 = args.release_mp3.parent / f".{args.release_mp3.name}.{run_key[:12]}.partial.mp3"
    filter_value = second_pass_filter(measured, args.target_lufs, args.target_true_peak, args.target_lra)
    master_command = ["ffmpeg", "-nostdin", "-hide_banner", "-y", "-i", str(args.selected_edit), "-af", filter_value,
                      "-map_metadata", "-1", "-c:a", "pcm_s24le", "-ar", "48000", "-ac", str(input_probe["channels"]),
                      str(partial_master)]
    master_result = subprocess.run(master_command, capture_output=True, text=True)
    pass2_path = args.log_dir / "pass2-normalization.log"; atomic_text(pass2_path, master_result.stdout + master_result.stderr)
    if master_result.returncode or not partial_master.is_file():
        partial_master.unlink(missing_ok=True); raise SystemExit("second-pass archive master render failed")
    mp3_command = ["ffmpeg", "-nostdin", "-hide_banner", "-y", "-i", str(partial_master), "-map_metadata", "-1",
                   "-c:a", "libmp3lame", "-b:a", args.mp3_bitrate, "-ar", "48000", "-ac", str(input_probe["channels"]),
                   str(partial_mp3)]
    mp3_result = subprocess.run(mp3_command, capture_output=True, text=True)
    encode_path = args.log_dir / "mp3-encode.log"; atomic_text(encode_path, mp3_result.stdout + mp3_result.stderr)
    if mp3_result.returncode or not partial_mp3.is_file():
        partial_master.unlink(missing_ok=True); partial_mp3.unlink(missing_ok=True); raise SystemExit("MP3 encode failed")
    master_probe = probe(partial_master); release_probe = probe(partial_mp3)
    master_metrics, master_qc_log = loudness(partial_master, args.target_lufs, args.target_true_peak, args.target_lra)
    release_metrics, release_qc_log = loudness(partial_mp3, args.target_lufs, args.target_true_peak, args.target_lra)
    master_qc_path = args.log_dir / "archive-master-qc.log"; release_qc_path = args.log_dir / "release-mp3-qc.log"
    atomic_text(master_qc_path, master_qc_log); atomic_text(release_qc_path, release_qc_log)
    technical_ok = (release_probe["codec_name"] == "mp3" and release_probe["sample_rate_hz"] in {44100, 48000}
                    and release_probe["channels"] in {1, 2} and release_probe["bit_rate"] >= 96000
                    and abs(release_metrics["integrated_lufs"] - args.target_lufs) <= 1.0
                    and release_metrics["true_peak_dbtp"] <= args.max_true_peak
                    and master_probe["codec_name"] == "pcm_s24le" and master_probe["sample_rate_hz"] == 48000)
    os.replace(partial_master, args.archive_master); os.replace(partial_mp3, args.release_mp3)
    report = {"schema_version": "1.0", "episode_id": args.episode_id, "stage": "S10-local-two-pass-mastering",
              "status": "technical_qc_passed_h3b_required" if technical_ok else "technical_qc_failed", "run_key": run_key,
              "selected_edit": {"path": str(args.selected_edit), "sha256": selected_sha, "probe": input_probe},
              "editorial_approval": {"path": str(args.editorial_approval), "sha256": sha256(args.editorial_approval),
                                     "approved_by": approval["approved_by"], "approved_at": approval["approved_at"]},
              "target": target, "measurement_pass": {"metrics": measured, "log_path": str(pass1_path),
              "log_sha256": sha256(pass1_path)},
              "archive_master": {"path": str(args.archive_master), "sha256": sha256(args.archive_master),
                                   "probe": master_probe, "loudness": master_metrics, "role": "lossless-archive-master",
                                   "qc_log_sha256": sha256(master_qc_path)},
              "release_audio": {"path": str(args.release_mp3), "sha256": sha256(args.release_mp3),
                                  "probe": release_probe, "loudness": release_metrics, "role": "release-mp3",
                                  "qc_log_sha256": sha256(release_qc_path)},
              "technical_qc_passed": technical_ok, "human_mastering_approval_required": True,
              "publish_authorized": False}
    jsonschema.validate(report, json.loads(SCHEMA.read_text())); atomic_json(args.report, report)
    print(json.dumps({"status": report["status"], "run_key": run_key,
                      "archive_master_sha256": report["archive_master"]["sha256"],
                      "release_audio_sha256": report["release_audio"]["sha256"],
                      "release_loudness": release_metrics, "report_sha256": sha256(args.report),
                      "publish_authorized": False}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if technical_ok else 1)


if __name__ == "__main__":
    main()
