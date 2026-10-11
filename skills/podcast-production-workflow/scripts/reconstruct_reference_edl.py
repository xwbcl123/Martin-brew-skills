#!/usr/bin/env python3
"""Convert a validated Filmora alignment into an evaluation-only reference EDL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
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


def confidence_for(uncertainty: float, high_max: float, eligible_max: float) -> str:
    if uncertainty <= high_max:
        return "high"
    if uncertainty <= eligible_max:
        return "medium"
    return "low"


def reconstruct(alignment: dict[str, Any], alignment_sha256: str, episode_id: str,
                high_max: float, eligible_max: float) -> dict[str, Any]:
    if not alignment.get("alignment_valid"):
        raise ValueError("alignment is not valid; reference EDL reconstruction refused")
    transitions = alignment.get("reference_transitions", [])
    cuts: list[dict[str, Any]] = []
    cumulative_removed = 0.0
    for index, item in enumerate(transitions, start=1):
        start = int(item["source_start_sample_48k"])
        end = int(item["source_end_sample_48k"])
        if start < 0 or end <= start:
            raise ValueError(f"invalid alignment transition interval: {item}")
        uncertainty = float(item["boundary_uncertainty_seconds"])
        confidence = confidence_for(uncertainty, high_max, eligible_max)
        reference_start = max(0.0, start / SAMPLE_RATE - cumulative_removed)
        duration = (end - start) / SAMPLE_RATE
        cuts.append({
            "reference_cut_id": f"REFCUT{index:04d}",
            "alignment_transition_id": item["reference_transition_id"],
            "kind": item.get("kind", "inferred_removed_interval"),
            "interval": {"start_sample": start, "end_sample": end},
            "duration_seconds": duration,
            "approx_reference_start_seconds": reference_start,
            "boundary_uncertainty_seconds": uncertainty,
            "confidence": confidence,
            "evaluation_eligible": confidence != "low",
            "production_edl_eligible": False,
        })
        cumulative_removed += duration
    source = alignment["provenance"]["source_render"]
    reference = alignment["provenance"]["filmora_reference"]
    run_key = canonical_sha256({
        "stage": "S08b-reference-edl-reconstruction",
        "stage_version": STAGE_VERSION,
        "alignment_sha256": alignment_sha256,
        "episode_id": episode_id,
        "high_uncertainty_max_seconds": high_max,
        "eligible_uncertainty_max_seconds": eligible_max,
    })
    eligible = [item for item in cuts if item["evaluation_eligible"]]
    return {
        "schema_version": "1.0",
        "stage": "S08b-reference-edl-reconstruction",
        "status": "succeeded" if eligible else "review_required",
        "run_key": run_key,
        "episode_id": episode_id,
        "timebase": {"sample_rate_hz": SAMPLE_RATE, "interval_convention": "half-open"},
        "provenance": {
            "alignment": {"sha256": alignment_sha256, "run_key": alignment["run_key"]},
            "source_render": source,
            "filmora_reference": reference,
        },
        "thresholds": {
            "high_uncertainty_max_seconds": high_max,
            "eligible_uncertainty_max_seconds": eligible_max,
        },
        "cuts": cuts,
        "summary": {
            "cut_count": len(cuts),
            "eligible_cut_count": len(eligible),
            "excluded_low_confidence_count": len(cuts) - len(eligible),
            "eligible_removed_seconds": sum(item["duration_seconds"] for item in eligible),
            "all_removed_seconds": sum(item["duration_seconds"] for item in cuts),
        },
        "boundary": {
            "filmora_is_evaluation_only": True,
            "production_edl_emitted": False,
            "human_feedback_required_for_policy_change": True,
            "heldout_claim_forbidden_after_tuning": True,
        },
        "publish_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alignment", type=Path, required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--high-uncertainty-max-seconds", type=float, default=0.40)
    parser.add_argument("--eligible-uncertainty-max-seconds", type=float, default=0.80)
    args = parser.parse_args()
    if args.high_uncertainty_max_seconds > args.eligible_uncertainty_max_seconds:
        raise SystemExit("high uncertainty threshold cannot exceed eligible threshold")
    alignment_sha = sha256_file(args.alignment)
    alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
    report = reconstruct(alignment, alignment_sha, args.episode_id,
                         args.high_uncertainty_max_seconds,
                         args.eligible_uncertainty_max_seconds)
    if args.output.is_file():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run_key") == report["run_key"]:
            print(json.dumps({"status": "skipped_cached", "output": str(args.output), "run_key": report["run_key"], "sha256": sha256_file(args.output)}, indent=2))
            return 0
    atomic_json(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "run_key": report["run_key"], "summary": report["summary"], "sha256": sha256_file(args.output)}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
