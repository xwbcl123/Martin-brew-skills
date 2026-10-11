#!/usr/bin/env python3
"""Align a human Filmora rough-cut reference to the immutable source timeline.

This creates blinded benchmark evidence, never a production EDL. It uses several
compression-robust spectral signatures, keeps source-unique matches, and finds a
monotone deletion-only path by longest non-decreasing source-minus-reference
offset. Transition boundaries carry uncertainty and require human labels.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import numpy as np


SCHEMA_VERSION = "1.0"
STAGE_VERSION = "1.0"
DECODE_RATE = 8000
FRAME_SIZE = 512
HOP = 160
FRAME_SECONDS = HOP / DECODE_RATE
PLATEAU_TOLERANCE_FRAMES = 2
MIN_RUN_ANCHORS = 3
SIGNATURE_SCHEMES = (
    (3, (0, 1, 2)),
    (4, (0, 1, 2)),
    (5, (0, 1, 2)),
    (4, (0, 2, 4)),
    (4, (0, 3, 6, 9)),
    (3, (0, 2, 4, 6)),
    (5, (0, 3, 6)),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def decode(path: Path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(DECODE_RATE), "-f", "f32le", "-"],
        check=True, capture_output=True,
    )
    return np.frombuffer(result.stdout, dtype="<f4")


def spectral_ranks(samples: np.ndarray) -> np.ndarray:
    count = 1 + (len(samples) - FRAME_SIZE) // HOP
    frames = np.lib.stride_tricks.as_strided(
        samples,
        shape=(count, FRAME_SIZE),
        strides=(samples.strides[0] * HOP, samples.strides[0]),
    ).copy()
    frames *= np.hanning(FRAME_SIZE)
    spectrum = np.abs(np.fft.rfft(frames, axis=1))[:, 4:221]
    bands = np.stack([spectrum[:, index * 7:(index + 1) * 7].mean(axis=1) for index in range(31)], axis=1)
    return np.sort(np.argsort(bands, axis=1)[:, -5:], axis=1).astype(np.uint8)


def signatures(ranks: np.ndarray, top_n: int, offsets: tuple[int, ...]) -> list[bytes]:
    limit = len(ranks) - max(offsets)
    return [
        bytes(sum((ranks[index + offset, -top_n:].tolist() for offset in offsets), []))
        for index in range(limit)
    ]


def unique_matches(source: np.ndarray, reference: np.ndarray) -> list[tuple[int, int, int]]:
    pairs: set[tuple[int, int, int]] = set()
    for top_n, offsets in SIGNATURE_SCHEMES:
        source_signatures = signatures(source, top_n, offsets)
        reference_signatures = signatures(reference, top_n, offsets)
        counts = Counter(source_signatures)
        source_index = {signature: index for index, signature in enumerate(source_signatures) if counts[signature] == 1}
        for reference_frame, signature in enumerate(reference_signatures):
            source_frame = source_index.get(signature)
            if source_frame is not None:
                pairs.add((reference_frame, source_frame, source_frame - reference_frame))
    return sorted(pairs)


def longest_nondecreasing_delta(pairs: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    tails: list[int] = []
    tail_indices: list[int] = []
    previous = [-1] * len(pairs)
    for index, (_, _, delta) in enumerate(pairs):
        position = bisect.bisect_right(tails, delta)
        if position == len(tails):
            tails.append(delta)
            tail_indices.append(index)
        else:
            tails[position] = delta
            tail_indices[position] = index
        if position:
            previous[index] = tail_indices[position - 1]
    cursor = tail_indices[-1]
    path: list[tuple[int, int, int]] = []
    while cursor >= 0:
        path.append(pairs[cursor])
        cursor = previous[cursor]
    path.reverse()
    # Multiple schemes can match the same reference frame. Keep one monotone anchor.
    deduplicated: list[tuple[int, int, int]] = []
    last_reference = -1
    for pair in path:
        if pair[0] > last_reference:
            deduplicated.append(pair)
            last_reference = pair[0]
    return deduplicated


def plateau_runs(path: list[tuple[int, int, int]]) -> list[list[tuple[int, int, int]]]:
    runs: list[list[tuple[int, int, int]]] = []
    current: list[tuple[int, int, int]] = []
    median_delta = 0
    for pair in path:
        if not current:
            current = [pair]
            median_delta = pair[2]
        elif abs(pair[2] - median_delta) <= PLATEAU_TOLERANCE_FRAMES:
            current.append(pair)
            median_delta = round(float(np.median([item[2] for item in current[-101:]])))
        else:
            runs.append(current)
            current = [pair]
            median_delta = pair[2]
    if current:
        runs.append(current)
    return [run for run in runs if len(run) >= MIN_RUN_ANCHORS]


def duration_seconds(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source_spec = manifest["audio_roles"]["render_audio"]
    reference_spec = manifest["gold_references"]["filmora_audio"]
    source_path = Path(source_spec["path"])
    reference_path = Path(reference_spec["path"])
    if sha256_file(source_path) != source_spec["sha256"] or sha256_file(reference_path) != reference_spec["sha256"]:
        raise SystemExit("source or Filmora reference identity mismatch")

    run_key = canonical_sha256({
        "stage": "S08_FILMORA_ALIGNMENT",
        "stage_version": STAGE_VERSION,
        "source_sha256": source_spec["sha256"],
        "reference_sha256": reference_spec["sha256"],
        "decode_rate": DECODE_RATE,
        "frame_size": FRAME_SIZE,
        "hop": HOP,
        "schemes": SIGNATURE_SCHEMES,
        "plateau_tolerance_frames": PLATEAU_TOLERANCE_FRAMES,
    })
    if args.output.is_file():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run_key") == run_key:
            print(json.dumps({"status": "skipped_cached", "output": str(args.output), "run_key": run_key, "sha256": sha256_file(args.output)}, indent=2))
            return 0

    source_ranks = spectral_ranks(decode(source_path))
    reference_ranks = spectral_ranks(decode(reference_path))
    matches = unique_matches(source_ranks, reference_ranks)
    path = longest_nondecreasing_delta(matches)
    runs = plateau_runs(path)
    if len(runs) < 2:
        raise SystemExit("insufficient monotone alignment evidence")

    run_records: list[dict[str, Any]] = []
    residuals: list[float] = []
    for index, run in enumerate(runs, start=1):
        delta = int(round(float(np.median([item[2] for item in run]))))
        run_residuals = [abs(item[2] - delta) * FRAME_SECONDS for item in run]
        residuals.extend(run_residuals)
        run_records.append({
            "run_id": f"K{index:04d}",
            "anchor_count": len(run),
            "reference_start_seconds": run[0][0] * FRAME_SECONDS,
            "reference_end_seconds": run[-1][0] * FRAME_SECONDS,
            "source_start_seconds": run[0][1] * FRAME_SECONDS,
            "source_end_seconds": run[-1][1] * FRAME_SECONDS,
            "source_minus_reference_seconds": delta * FRAME_SECONDS,
            "median_residual_ms": float(np.median(run_residuals) * 1000),
            "p95_residual_ms": float(np.percentile(run_residuals, 95) * 1000),
        })

    transitions: list[dict[str, Any]] = []
    previous_delta = 0
    previous_end_reference = 0
    for index, record in enumerate(run_records):
        new_delta = round(record["source_minus_reference_seconds"] / FRAME_SECONDS)
        delta_change = new_delta - previous_delta
        if delta_change > PLATEAU_TOLERANCE_FRAMES:
            reference_boundary_frame = round(record["reference_start_seconds"] / FRAME_SECONDS)
            start_frame = reference_boundary_frame + previous_delta
            end_frame = reference_boundary_frame + new_delta
            uncertainty = max(0.0, record["reference_start_seconds"] - previous_end_reference) + max(offset for _, offsets in SIGNATURE_SCHEMES for offset in offsets) * FRAME_SECONDS
            transitions.append({
                "reference_transition_id": f"R{len(transitions) + 1:04d}",
                "kind": "leading_trim" if index == 0 else "inferred_removed_interval",
                "source_start_sample_48k": int(round(start_frame * FRAME_SECONDS * 48000)),
                "source_end_sample_48k": int(round(end_frame * FRAME_SECONDS * 48000)),
                "duration_seconds": delta_change * FRAME_SECONDS,
                "boundary_uncertainty_seconds": uncertainty,
                "label_status": "human_label_required",
                "production_edl_eligible": False,
            })
        previous_delta = new_delta
        previous_end_reference = record["reference_end_seconds"]

    source_duration = duration_seconds(source_path)
    reference_duration = duration_seconds(reference_path)
    mapped_reference_end = reference_duration + previous_delta * FRAME_SECONDS
    trailing = source_duration - mapped_reference_end
    if trailing > FRAME_SECONDS * PLATEAU_TOLERANCE_FRAMES:
        transitions.append({
            "reference_transition_id": f"R{len(transitions) + 1:04d}",
            "kind": "trailing_trim",
            "source_start_sample_48k": int(round(mapped_reference_end * 48000)),
            "source_end_sample_48k": int(round(source_duration * 48000)),
            "duration_seconds": trailing,
            "boundary_uncertainty_seconds": max(offset for _, offsets in SIGNATURE_SCHEMES for offset in offsets) * FRAME_SECONDS,
            "label_status": "human_label_required",
            "production_edl_eligible": False,
        })

    coverage = sum(record["reference_end_seconds"] - record["reference_start_seconds"] for record in run_records) / reference_duration
    median_residual_ms = float(np.median(residuals) * 1000)
    p95_residual_ms = float(np.percentile(residuals, 95) * 1000)
    alignment_valid = coverage >= 0.95 and median_residual_ms <= 20 and p95_residual_ms <= 80
    removed_total = sum(item["duration_seconds"] for item in transitions)
    report = {
        "schema_version": SCHEMA_VERSION,
        "stage": "S08_FILMORA_ALIGNMENT",
        "status": "alignment_valid_for_blinded_labeling" if alignment_valid else "alignment_invalid_review_required",
        "run_key": run_key,
        "method": {
            "name": "multi-signature-monotone-deletion-alignment",
            "stage_version": STAGE_VERSION,
            "decode_rate_hz": DECODE_RATE,
            "frame_size_samples": FRAME_SIZE,
            "hop_samples": HOP,
            "frame_seconds": FRAME_SECONDS,
            "signature_schemes": [[top_n, list(offsets)] for top_n, offsets in SIGNATURE_SCHEMES],
            "plateau_tolerance_frames": PLATEAU_TOLERANCE_FRAMES,
        },
        "provenance": {
            "source_render": {"path": str(source_path), "sha256": source_spec["sha256"], "duration_seconds": source_duration},
            "filmora_reference": {"path": str(reference_path), "sha256": reference_spec["sha256"], "duration_seconds": reference_duration},
        },
        "evidence": {
            "unique_signature_matches": len(matches),
            "monotone_anchor_count": len(path),
            "kept_run_count": len(run_records),
            "reference_transition_count": len(transitions),
            "confident_reference_coverage": coverage,
            "anchor_residual_median_ms": median_residual_ms,
            "anchor_residual_p95_ms": p95_residual_ms,
            "inferred_removed_seconds": removed_total,
            "observed_duration_difference_seconds": source_duration - reference_duration,
        },
        "thresholds": {"coverage_min": 0.95, "median_residual_ms_max": 20, "p95_residual_ms_max": 80},
        "alignment_valid": alignment_valid,
        "runs": run_records,
        "reference_transitions": transitions,
        "boundary": {
            "filmora_is_evaluation_only": True,
            "production_edl_emitted": False,
            "human_labels_required": True,
            "duration_is_not_an_optimization_target": True,
        },
        "publish_authorized": False,
    }
    atomic_json(args.output, report)
    print(json.dumps({
        "status": report["status"], "output": str(args.output), "run_key": run_key,
        "alignment_valid": alignment_valid, "evidence": report["evidence"], "sha256": sha256_file(args.output),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if alignment_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
