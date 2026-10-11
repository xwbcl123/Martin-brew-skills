#!/usr/bin/env python3
"""Render a 48 kHz PCM review WAV from half-open sample EDL with explicit crossfade mapping."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import tempfile
import wave

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
EDL_SCHEMA = ROOT / "references/edl.schema.json"
REPORT_SCHEMA = ROOT / "references/render-report.schema.json"
RATE = 48000


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def keep_ranges(total: int, cuts: list[dict]) -> list[tuple[int, int]]:
    ranges = []; cursor = 0
    for cut in cuts:
        interval = cut["applied_interval"]; start, end = interval["start_sample"], interval["end_sample"]
        if start < cursor or end <= start or end > total:
            raise ValueError(f"invalid/overlapping cut {cut['cut_id']}: [{start},{end}), cursor={cursor}")
        if start > cursor:
            ranges.append((cursor, start))
        cursor = end
    if cursor < total:
        ranges.append((cursor, total))
    if not ranges:
        raise ValueError("EDL removes entire source")
    return ranges


def read_frames(source: wave.Wave_read, start: int, frames: int, channels: int) -> np.ndarray:
    source.setpos(start)
    data = source.readframes(frames)
    array = np.frombuffer(data, dtype="<i2")
    if array.size != frames * channels:
        raise ValueError(f"short source read at {start}: expected {frames}, got {array.size // channels}")
    return array.reshape(frames, channels)


def write_chunks(destination: wave.Wave_write, array: np.ndarray, qc: dict) -> None:
    if not array.size:
        return
    qc["max_abs_sample"] = max(qc["max_abs_sample"], int(np.abs(array.astype(np.int32)).max()))
    qc["clipped_sample_values"] += int(np.count_nonzero((array == -32768) | (array == 32767)))
    destination.writeframesraw(array.astype("<i2", copy=False).tobytes())


def render(source_path: pathlib.Path, output_path: pathlib.Path, ranges: list[tuple[int, int]], crossfade: int) -> dict:
    with wave.open(str(source_path), "rb") as source:
        if source.getframerate() != RATE or source.getsampwidth() != 2 or source.getcomptype() != "NONE":
            raise ValueError("source must be uncompressed PCM s16le at 48 kHz")
        channels, total = source.getnchannels(), source.getnframes()
        for index, (start, end) in enumerate(ranges):
            minimum = crossfade * (2 if 0 < index < len(ranges) - 1 else 1)
            if len(ranges) > 1 and end - start <= minimum:
                raise ValueError(f"keep segment {index} too short for {crossfade}-sample crossfade")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".wav", dir=output_path.parent)
        os.close(descriptor); temporary = pathlib.Path(temporary_name)
        qc = {"max_abs_sample": 0, "clipped_sample_values": 0}
        try:
            with wave.open(str(temporary), "wb") as destination:
                destination.setnchannels(channels); destination.setsampwidth(2); destination.setframerate(RATE)
                pending_tail = None
                for index, (start, end) in enumerate(ranges):
                    length = end - start; has_next = index + 1 < len(ranges)
                    head_length = crossfade if index else 0
                    tail_length = crossfade if has_next else 0
                    head = read_frames(source, start, head_length, channels) if head_length else None
                    if pending_tail is not None:
                        weights = (np.arange(crossfade, dtype=np.float64) + 0.5) / crossfade
                        mixed = np.rint(pending_tail.astype(np.float64) * (1.0 - weights[:, None])
                                        + head.astype(np.float64) * weights[:, None])
                        write_chunks(destination, np.clip(mixed, -32768, 32767).astype(np.int16), qc)
                    body_start = start + head_length; body_end = end - tail_length
                    cursor = body_start
                    while cursor < body_end:
                        count = min(65536, body_end - cursor)
                        write_chunks(destination, read_frames(source, cursor, count, channels), qc); cursor += count
                    pending_tail = read_frames(source, body_end, tail_length, channels) if tail_length else None
                if pending_tail is not None:
                    write_chunks(destination, pending_tail, qc)
            os.replace(temporary, output_path)
        finally:
            temporary.unlink(missing_ok=True)
    with wave.open(str(output_path), "rb") as output:
        return {"frames": output.getnframes(), "channels": output.getnchannels(),
                "sample_rate_hz": output.getframerate(), "sample_width_bytes": output.getsampwidth(), **qc}


def build_mapping(ranges: list[tuple[int, int]], crossfade: int) -> dict:
    kept = []; non_transition = []; transitions = []; release_cursor = 0
    for index, (start, end) in enumerate(ranges):
        release_start = release_cursor - (crossfade if index else 0)
        release_end = release_start + (end - start)
        kept.append({"segment_index": index, "source_start_sample": start, "source_end_sample": end,
                     "release_start_sample": release_start, "release_end_sample": release_end})
        left_trim = crossfade if index else 0; right_trim = crossfade if index + 1 < len(ranges) else 0
        if end - start > left_trim + right_trim:
            non_transition.append({"segment_index": index, "source_start_sample": start + left_trim,
                                   "source_end_sample": end - right_trim,
                                   "release_start_sample": release_start + left_trim,
                                   "release_end_sample": release_end - right_trim, "slope": 1})
        if index:
            previous = ranges[index - 1]
            transitions.append({"join_index": index - 1, "release_start_sample": release_start,
                                "release_end_sample": release_start + crossfade,
                                "left_source_start_sample": previous[1] - crossfade,
                                "left_source_end_sample": previous[1],
                                "right_source_start_sample": start,
                                "right_source_end_sample": start + crossfade,
                                "mapping_kind": "two-source-linear-crossfade-non-invertible"})
        release_cursor = release_end
    return {"kept_segments": kept, "non_transition_mappings": non_transition,
            "crossfade_transitions": transitions, "roundtrip_error_samples_non_transition_max": 0,
            "crossfade_regions_excluded_from_inverse_mapping": True}


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--edl", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    edl = json.loads(args.edl.read_text(encoding="utf-8")); jsonschema.validate(edl, json.loads(EDL_SCHEMA.read_text()))
    source_path = pathlib.Path(edl["source_audio"]["path"])
    if sha256(source_path) != edl["source_audio"]["sha256"]:
        raise SystemExit("source audio hash mismatch")
    with wave.open(str(source_path), "rb") as source:
        total = source.getnframes()
        if source.getframerate() != RATE or total != edl["source_audio"]["total_samples"]:
            raise SystemExit("source sample timebase mismatch")
    cuts = sorted(edl["cuts"], key=lambda item: item["applied_interval"]["start_sample"])
    ranges = keep_ranges(total, cuts); crossfade = int(edl["crossfade_samples"])
    run_key = canonical_hash({"stage": "S07-lossless-review-render-v1", "source": sha256(source_path),
                              "edl": sha256(args.edl), "crossfade_samples": crossfade})
    if args.report.is_file() and args.output.is_file():
        existing = json.loads(args.report.read_text())
        if existing.get("run_key") == run_key and existing["output_audio"]["sha256"] == sha256(args.output):
            print(json.dumps({"status": "skipped_cached", "run_key": run_key, "output": str(args.output),
                              "output_sha256": sha256(args.output), "report": str(args.report),
                              "report_sha256": sha256(args.report)}, indent=2)); return
    if args.output.exists() or args.report.exists():
        raise SystemExit("unverified render/report exists; choose a new revision path")
    output_probe = render(source_path, args.output, ranges, crossfade)
    removed = sum(item["applied_interval"]["end_sample"] - item["applied_interval"]["start_sample"] for item in cuts)
    joins = max(0, len(ranges) - 1); expected = total - removed - crossfade * joins
    if output_probe["frames"] != expected:
        args.output.unlink(missing_ok=True)
        raise SystemExit(f"sample accounting mismatch: expected {expected}, got {output_probe['frames']}")
    mapping = build_mapping(ranges, crossfade)
    report = {"schema_version": "1.0", "episode_id": edl["episode_id"], "stage": "S07-lossless-review-render",
              "status": "review_required", "run_key": run_key,
              "source_audio": {"path": str(source_path), "sha256": sha256(source_path), "total_samples": total},
              "edl": {"path": str(args.edl), "sha256": sha256(args.edl), "cut_count": len(cuts)},
              "output_audio": {"path": str(args.output), "sha256": sha256(args.output), "bytes": args.output.stat().st_size,
                               "role": "lossless-review-edit-not-master", **output_probe},
              "duration_accounting": {"source_samples": total, "cut_samples": removed,
                                      "crossfade_overlap_samples": crossfade * joins,
                                      "expected_output_samples": expected, "actual_output_samples": output_probe["frames"],
                                      "error_samples": output_probe["frames"] - expected},
              "mapping": mapping,
              "technical_join_qc": {"transition_count": joins, "crossfade_samples": crossfade,
                                    "max_abs_sample": output_probe["max_abs_sample"],
                                    "clipped_sample_values": output_probe["clipped_sample_values"],
                                    "audible_defects_proven_absent": False},
              "human_join_audit_required": True, "publish_authorized": False}
    jsonschema.validate(report, json.loads(REPORT_SCHEMA.read_text())); atomic_json(args.report, report)
    print(json.dumps({"status": report["status"], "run_key": run_key, "output": str(args.output),
                      "output_sha256": sha256(args.output), "report": str(args.report),
                      "report_sha256": sha256(args.report), "duration_accounting": report["duration_accounting"],
                      "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
