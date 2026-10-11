#!/usr/bin/env python3
"""Validate release-bound raw Transcript, Verbatim and timed Subs for H4."""

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
LEDGER_SCHEMA = ROOT / "references/postcut-correction-ledger.schema.json"
APPROVAL_SCHEMA = ROOT / "references/postcut-text-approval.schema.json"
REPORT_SCHEMA = ROOT / "references/postcut-text-report.schema.json"
DEFAULT_SUBTITLE_PROFILE = ROOT / "references/subtitle-profile.zh-v1.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True); raise


def artifact(path: pathlib.Path, role: str) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing/empty {role}: {path}")
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}


def duration_seconds(path: pathlib.Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                            check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def parse_timestamp(value: str) -> int:
    pieces = value.replace(",", ".").split(":")
    if len(pieces) == 2: hours = 0; minutes, seconds = pieces
    elif len(pieces) == 3: hours, minutes, seconds = pieces
    else: raise ValueError(value)
    return round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)


def subtitle_qc(path: pathlib.Path, audio_duration: float, profile: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    timing = re.compile(r"(?m)^(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})")
    matches = list(timing.finditer(text))
    if not matches: raise SystemExit("timed Subs contain no VTT/SRT cues")
    previous_start = -1; previous_end = -1; overlaps = 0; max_end = 0
    violations = []; cue_metrics = []
    for index, match in enumerate(matches):
        start, end = parse_timestamp(match.group(1)), parse_timestamp(match.group(2))
        if start <= previous_start or end <= start: raise SystemExit(f"invalid/non-increasing subtitle cue {index + 1}")
        if start < previous_end: overlaps += 1
        if end > round((audio_duration + 0.25) * 1000): raise SystemExit(f"subtitle cue {index + 1} exceeds release audio")
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():next_start]
        lines = [item.strip() for item in body.splitlines() if item.strip() and not item.strip().isdigit() and not item.strip().startswith("NOTE")]
        compact_lengths = [len(re.sub(r"\s+", "", line)) for line in lines]
        characters = sum(compact_lengths); duration_s = (end - start) / 1000
        cps = characters / duration_s if duration_s else float("inf")
        cue_metrics.append({"cue": index + 1, "start_ms": start, "end_ms": end, "duration_seconds": duration_s,
                            "line_count": len(lines), "max_line_characters": max(compact_lengths, default=0),
                            "characters": characters, "characters_per_second": round(cps, 3)})
        if not lines: violations.append({"cue": index + 1, "code": "EMPTY_CUE"})
        if len(lines) > profile["max_lines_per_cue"]: violations.append({"cue": index + 1, "code": "TOO_MANY_LINES", "actual": len(lines)})
        for length in compact_lengths:
            if length > profile["max_characters_per_line"]: violations.append({"cue": index + 1, "code": "LINE_TOO_LONG", "actual": length})
        if cps > profile["max_characters_per_second"]: violations.append({"cue": index + 1, "code": "READING_SPEED", "actual": round(cps, 3)})
        if duration_s < profile["minimum_cue_duration_seconds"]: violations.append({"cue": index + 1, "code": "CUE_TOO_SHORT", "actual": duration_s})
        if duration_s > profile["maximum_cue_duration_seconds"]: violations.append({"cue": index + 1, "code": "CUE_TOO_LONG", "actual": duration_s})
        previous_start, previous_end, max_end = start, end, end
    if overlaps and not profile["overlap_allowed"]: violations.append({"code": "OVERLAPPING_CUES", "actual": overlaps})
    return {"cue_count": len(matches), "strictly_increasing_starts": True, "overlap_count": overlaps,
            "last_end_ms": max_end, "audio_duration_ms": round(audio_duration * 1000),
            "cue_metrics": cue_metrics, "violations": violations, "passed": not violations}


def validate_raw_report(path: pathlib.Path, release_sha: str, episode_id: str) -> tuple[dict, dict]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("stage") != "S11a-postcut-whisper-raw" or report.get("episode_id") != episode_id:
        raise SystemExit("raw transcript report is not the matching S11a episode report")
    if report.get("inputs", {}).get("release_audio", {}).get("sha256") != release_sha:
        raise SystemExit("raw transcript report is not bound to exact release audio")
    for item in report.get("outputs", {}).values():
        candidate = pathlib.Path(item["path"])
        if not candidate.is_file() or sha256(candidate) != item["sha256"] or item.get("role") != "immutable-postcut-raw-whisper":
            raise SystemExit("raw transcript artifact identity/role mismatch")
    raw_json = report["outputs"]["json"]
    value = json.loads(pathlib.Path(raw_json["path"]).read_text(encoding="utf-8"))
    segments = value.get("transcription")
    if not isinstance(segments, list) or not segments:
        raise SystemExit("post-cut raw Whisper JSON has no segments")
    previous = 0
    for index, segment in enumerate(segments):
        offsets = segment.get("offsets", {})
        start, end = int(offsets.get("from", -1)), int(offsets.get("to", -1))
        if start < previous or end < start:
            raise SystemExit(f"post-cut raw Whisper JSON is non-monotonic at segment {index}")
        previous = end
    raw_json = {**raw_json, "segment_count": len(segments), "last_offset_ms": previous}
    return report, raw_json


def main() -> int:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id", required=True); parser.add_argument("--release-audio", type=pathlib.Path, required=True)
    parser.add_argument("--raw-report", type=pathlib.Path, required=True); parser.add_argument("--verbatim", type=pathlib.Path, required=True)
    parser.add_argument("--subs", type=pathlib.Path, required=True); parser.add_argument("--correction-ledger", type=pathlib.Path, required=True)
    parser.add_argument("--delivery-profile", choices=["audio", "video"], default="audio")
    parser.add_argument("--subtitle-profile", type=pathlib.Path, default=DEFAULT_SUBTITLE_PROFILE)
    parser.add_argument("--final-video", type=pathlib.Path)
    parser.add_argument("--approval", type=pathlib.Path); parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    release = artifact(args.release_audio, "release-mp3"); duration = duration_seconds(args.release_audio)
    profile_value = json.loads(args.subtitle_profile.read_text(encoding="utf-8")); profile_artifact = artifact(args.subtitle_profile, "subtitle-profile")
    required_profile = {"profile_id", "language", "max_characters_per_line", "max_lines_per_cue", "max_characters_per_second",
                        "minimum_cue_duration_seconds", "maximum_cue_duration_seconds", "maximum_av_duration_delta_ms", "overlap_allowed"}
    if not required_profile <= set(profile_value): raise SystemExit("subtitle profile is missing required fields")
    final_video = None
    if args.delivery_profile == "video":
        if not args.final_video: raise SystemExit("video delivery profile requires --final-video")
        final_video = artifact(args.final_video, "final-video"); video_duration = duration_seconds(args.final_video)
        final_video["duration_seconds"] = video_duration
        if abs(video_duration - duration) * 1000 > profile_value["maximum_av_duration_delta_ms"]:
            raise SystemExit("final video/audio duration mismatch exceeds subtitle profile")
    elif args.final_video:
        raise SystemExit("--final-video is only valid with --delivery-profile video")
    raw_report, raw_json = validate_raw_report(args.raw_report, release["sha256"], args.episode_id)
    verbatim = artifact(args.verbatim, "canonical-untimed-verbatim"); subs = artifact(args.subs, "timed-subs")
    verbatim_text = args.verbatim.read_text(encoding="utf-8")
    if not verbatim_text.strip(): raise SystemExit("Verbatim is empty")
    if "-->" in verbatim_text or re.search(r"(?m)^\s*\[?\d{1,2}:\d{2}(?::\d{2})?", verbatim_text):
        raise SystemExit("canonical Verbatim must be untimed; use Subs for timestamps")
    ledger_value = json.loads(args.correction_ledger.read_text(encoding="utf-8")); jsonschema.validate(ledger_value, json.loads(LEDGER_SCHEMA.read_text()))
    ledger = artifact(args.correction_ledger, "correction-ledger")
    if ledger_value["episode_id"] != args.episode_id or ledger_value["release_audio_sha256"] != release["sha256"] or ledger_value["raw_transcript_json_sha256"] != raw_json["sha256"]:
        raise SystemExit("correction ledger lineage mismatch")
    verified_sources = []
    for source in ledger_value["terminology_sources"]:
        source_path = pathlib.Path(source["path"])
        if not source_path.is_absolute(): source_path = args.correction_ledger.parent / source_path
        if not source_path.is_file() or sha256(source_path) != source["sha256"]:
            raise SystemExit(f"terminology source identity mismatch: {source_path}")
        verified_sources.append({"path": str(source_path), "sha256": source["sha256"]})
    invalid_ranges = [item["id"] for item in ledger_value["corrections"] if item["end_ms"] <= item["start_ms"]]
    invalid_speakers = [index for index, item in enumerate(ledger_value["speaker_decisions"]) if item["range_end_ms"] <= item["range_start_ms"]]
    if invalid_ranges or invalid_speakers: raise SystemExit("correction/speaker ledger has invalid ranges")
    duration_ms = round(duration * 1000)
    if any(item["end_ms"] > duration_ms + 250 for item in ledger_value["corrections"]) or any(item["range_end_ms"] > duration_ms + 250 for item in ledger_value["speaker_decisions"]):
        raise SystemExit("correction/speaker ledger range exceeds release audio")
    unresolved = ([item["id"] for item in ledger_value["corrections"] if item["status"] == "review_required"]
                  + [f"speaker:{index}" for index, item in enumerate(ledger_value["speaker_decisions"]) if item["status"] == "review_required"])
    timeline = subtitle_qc(args.subs, duration, profile_value)
    identities = {"episode_id": args.episode_id, "delivery_profile": args.delivery_profile,
                  "subtitle_profile_sha256": profile_artifact["sha256"], "release_audio_sha256": release["sha256"],
                  "raw_transcript_json_sha256": raw_json["sha256"], "verbatim_sha256": verbatim["sha256"],
                  "timed_subs_sha256": subs["sha256"], "correction_ledger_sha256": ledger["sha256"]}
    if final_video: identities["final_video_sha256"] = final_video["sha256"]
    approval_value = None
    if args.approval:
        if unresolved: raise SystemExit("H4 cannot accept unresolved correction/speaker decisions: " + ", ".join(unresolved))
        if not timeline["passed"]: raise SystemExit("H4 cannot accept subtitle QC violations: " + json.dumps(timeline["violations"], ensure_ascii=False))
        approval_value = json.loads(args.approval.read_text(encoding="utf-8")); jsonschema.validate(approval_value, json.loads(APPROVAL_SCHEMA.read_text()))
        mismatch = {key: {"expected": value, "actual": approval_value.get(key)} for key, value in identities.items() if approval_value.get(key) != value}
        if mismatch: raise SystemExit("H4 post-cut text approval hash mismatch: " + json.dumps(mismatch, sort_keys=True))
        timestamp = dt.datetime.fromisoformat(approval_value["approved_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None: raise SystemExit("H4 approval timestamp must include timezone")
    run_key = canonical_hash({"stage": "S11-postcut-text-validation-v2", **identities,
                              "raw_report_sha256": sha256(args.raw_report),
                              "approval": canonical_hash(approval_value) if approval_value else None})
    if args.report.exists():
        existing = json.loads(args.report.read_text(encoding="utf-8"))
        if existing.get("run_key") == run_key:
            print(json.dumps({"status": "skipped_cached", "run_key": run_key, "report_sha256": sha256(args.report),
                              "contract_text_ready": existing["contract_text_ready"], "publish_authorized": False}, indent=2)); return 0 if approval_value else 1
        raise SystemExit("existing post-cut text report belongs to another revision")
    report = {"schema_version": "1.1", "episode_id": args.episode_id, "stage": "S11-postcut-text-validation",
              "status": "accepted" if approval_value else "review_required", "run_key": run_key,
              "delivery_profile": args.delivery_profile,
              "release_audio": {**release, "duration_seconds": duration},
              "final_video": final_video,
              "raw_transcript": {"report_path": str(args.raw_report), "report_sha256": sha256(args.raw_report),
                                     "raw_json": raw_json, "run_key": raw_report["run_key"]},
              "verbatim": verbatim, "timed_subs": subs,
              "correction_ledger": {**ledger, "correction_count": len(ledger_value["corrections"]),
                                      "speaker_decision_count": len(ledger_value["speaker_decisions"]),
                                      "verified_terminology_sources": verified_sources,
                                      "unresolved_decisions": unresolved},
              "subtitle_profile": {**profile_artifact, "profile_id": profile_value["profile_id"], "language": profile_value["language"]},
              "timeline_qc": timeline,
              "human_review": ({"approval_path": str(args.approval), "approval_sha256": sha256(args.approval),
                                  "approved_by": approval_value["approved_by"], "approved_at": approval_value["approved_at"]}
                                 if approval_value else None),
              "contract_text_ready": bool(approval_value),
              "video_ready": bool(approval_value and args.delivery_profile == "video"), "publish_authorized": False}
    jsonschema.validate(report, json.loads(REPORT_SCHEMA.read_text())); atomic_json(args.report, report)
    print(json.dumps({"status": report["status"], "run_key": run_key, "report_sha256": sha256(args.report),
                      "timeline_qc": timeline, "contract_text_ready": report["contract_text_ready"],
                      "publish_authorized": False}, ensure_ascii=False, indent=2))
    return 0 if approval_value else 1


if __name__ == "__main__":
    raise SystemExit(main())
