#!/usr/bin/env python3
"""Compare an automatic production EDL with an evaluation-only reference EDL."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any


STAGE_VERSION = "1.0"
SAMPLE_RATE = 48000


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


def auto_interval(cut: dict[str, Any]) -> tuple[int, int]:
    interval = cut.get("applied_interval") or cut.get("proposed_interval") or cut.get("interval")
    return int(interval["start_sample"]), int(interval["end_sample"])


def overlap_score(auto: tuple[int, int], ref: dict[str, Any]) -> tuple[float, float] | None:
    rs = int(ref["interval"]["start_sample"])
    re = int(ref["interval"]["end_sample"])
    pad = int(round(float(ref["boundary_uncertainty_seconds"]) * SAMPLE_RATE))
    expanded_start, expanded_end = max(0, rs - pad), re + pad
    intersection = max(0, min(auto[1], expanded_end) - max(auto[0], expanded_start))
    if intersection <= 0:
        return None
    union = max(auto[1], expanded_end) - min(auto[0], expanded_start)
    boundary_error = (abs(auto[0] - rs) + abs(auto[1] - re)) / 2
    return intersection / union, boundary_error


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def compare(auto: dict[str, Any], reference: dict[str, Any], auto_sha: str, ref_sha: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if auto.get("episode_id") != reference.get("episode_id"):
        raise ValueError("episode identity mismatch")
    eligible_refs = [item for item in reference["cuts"] if item["evaluation_eligible"]]
    auto_cuts = auto.get("cuts", [])
    candidates: list[tuple[float, float, int, int]] = []
    for ai, cut in enumerate(auto_cuts):
        interval = auto_interval(cut)
        for ri, ref in enumerate(eligible_refs):
            score = overlap_score(interval, ref)
            if score:
                candidates.append((score[0], -score[1], ai, ri))
    used_auto: set[int] = set()
    used_ref: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, _, ai, ri in sorted(candidates, reverse=True):
        if ai not in used_auto and ri not in used_ref:
            used_auto.add(ai)
            used_ref.add(ri)
            matches.append((ai, ri))

    delta_items: list[dict[str, Any]] = []
    boundary_errors: list[float] = []
    match_by_auto = {ai: ri for ai, ri in matches}
    for ai, cut in enumerate(auto_cuts):
        start, end = auto_interval(cut)
        if ai in match_by_auto:
            ref = eligible_refs[match_by_auto[ai]]
            rs, re = int(ref["interval"]["start_sample"]), int(ref["interval"]["end_sample"])
            start_error = abs(start - rs) * 1000 / SAMPLE_RATE
            end_error = abs(end - re) * 1000 / SAMPLE_RATE
            boundary_errors.extend([start_error, end_error])
            kind = "boundary_drift" if max(start_error, end_error) > 250 else "matched"
            delta_items.append({
                "delta_id": f"D{len(delta_items)+1:04d}", "kind": kind,
                "auto_cut_id": cut.get("cut_id"), "reference_cut_id": ref["reference_cut_id"],
                "source_interval": {"start_sample": min(start, rs), "end_sample": max(end, re)},
                "auto_interval": {"start_sample": start, "end_sample": end}, "reference_interval": ref["interval"],
                "start_boundary_error_ms": start_error, "end_boundary_error_ms": end_error,
                "auto_categories": cut.get("categories", []), "review_required": kind == "boundary_drift",
            })
        else:
            delta_items.append({
                "delta_id": f"D{len(delta_items)+1:04d}", "kind": "auto_only",
                "auto_cut_id": cut.get("cut_id"), "reference_cut_id": None,
                "source_interval": {"start_sample": start, "end_sample": end},
                "auto_interval": {"start_sample": start, "end_sample": end}, "reference_interval": None,
                "auto_categories": cut.get("categories", []), "review_required": True,
            })
    for ri, ref in enumerate(eligible_refs):
        if ri not in used_ref:
            delta_items.append({
                "delta_id": f"D{len(delta_items)+1:04d}", "kind": "reference_only",
                "auto_cut_id": None, "reference_cut_id": ref["reference_cut_id"],
                "source_interval": ref["interval"], "auto_interval": None, "reference_interval": ref["interval"],
                "reference_confidence": ref.get("confidence", "unknown"), "review_required": True,
            })
    matched = len(matches)
    metrics = {
        "precision": matched / len(auto_cuts) if auto_cuts else 0.0,
        "recall": matched / len(eligible_refs) if eligible_refs else 0.0,
        "matched_count": matched,
        "auto_only_count": len(auto_cuts) - matched,
        "reference_only_count": len(eligible_refs) - matched,
        "auto_cut_count": len(auto_cuts),
        "eligible_reference_count": len(eligible_refs),
        "excluded_low_confidence_reference_count": len(reference["cuts"]) - len(eligible_refs),
        "boundary_error_ms": {
            "mean": statistics.mean(boundary_errors) if boundary_errors else None,
            "median": statistics.median(boundary_errors) if boundary_errors else None,
            "p95": percentile(boundary_errors, 0.95),
        },
        "auto_removed_seconds": sum((auto_interval(c)[1] - auto_interval(c)[0]) / SAMPLE_RATE for c in auto_cuts),
        "eligible_reference_removed_seconds": sum(c["duration_seconds"] for c in eligible_refs),
    }
    alignment_sha = reference["provenance"]["alignment"]["sha256"]
    run_key = canonical_sha256({"stage": "S08c-edl-delta-analysis", "stage_version": STAGE_VERSION, "auto_edl_sha256": auto_sha, "reference_edl_sha256": ref_sha})
    report = {
        "schema_version": "1.0", "stage": "S08c-edl-delta-analysis", "status": "review_required",
        "run_key": run_key, "episode_id": auto["episode_id"],
        "provenance": {"auto_edl": {"sha256": auto_sha}, "reference_edl": {"sha256": ref_sha}, "alignment": {"sha256": alignment_sha}},
        "metrics": metrics, "delta_items": delta_items,
        "feedback_taxonomy": {
            "outcomes": ["auto_error", "reference_style_only", "acceptable_alternative", "alignment_uncertain", "needs_context"],
            "reasons": ["meaningful_speech", "laughter_or_emotion", "filler", "repetition_or_false_start", "recording_control", "silence", "technical_failure", "join_or_boundary_defect", "other"],
        },
        "boundary": {"evaluation_only": True, "production_authority": False, "development_fixture": True, "heldout_claim_forbidden_after_tuning": True},
        "publish_authorized": False,
    }
    feedback = {
        "schema_version": "1.0", "episode_id": auto["episode_id"], "delta_report_run_key": run_key,
        "delta_report_sha256": None,
        "labels": [{"delta_id": item["delta_id"], "kind": item["kind"], "outcome": None, "reason": None, "note": ""} for item in delta_items if item["review_required"]],
        "policy_revision": None, "reviewer": None, "reviewed_at": None,
    }
    return report, feedback


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-edl", type=Path, required=True)
    parser.add_argument("--reference-edl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--feedback-template", type=Path, required=True)
    args = parser.parse_args()
    auto_sha, ref_sha = sha256_file(args.auto_edl), sha256_file(args.reference_edl)
    auto = json.loads(args.auto_edl.read_text(encoding="utf-8"))
    reference = json.loads(args.reference_edl.read_text(encoding="utf-8"))
    report, feedback = compare(auto, reference, auto_sha, ref_sha)
    if args.output.is_file():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run_key") == report["run_key"] and args.feedback_template.is_file():
            print(json.dumps({"status": "skipped_cached", "output": str(args.output), "run_key": report["run_key"], "sha256": sha256_file(args.output)}, indent=2))
            return 0
    atomic_json(args.output, report)
    feedback["delta_report_sha256"] = sha256_file(args.output)
    atomic_json(args.feedback_template, feedback)
    print(json.dumps({"status": report["status"], "output": str(args.output), "feedback_template": str(args.feedback_template), "run_key": report["run_key"], "metrics": report["metrics"], "sha256": sha256_file(args.output)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
