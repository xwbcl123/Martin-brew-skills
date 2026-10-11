#!/usr/bin/env python3
"""Build a blinded human-label template from a valid Filmora alignment report."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alignment", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
    if not alignment.get("alignment_valid"):
        raise SystemExit("alignment is not valid; refusing to build held-out labels")
    alignment_sha = sha256(args.alignment)
    run_key = hashlib.sha256(f"S02-label-template-v1:{alignment_sha}".encode()).hexdigest()
    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run_key") == run_key:
            print(json.dumps({"status": "skipped_cached", "run_key": run_key,
                              "output": str(args.output), "sha256": sha256(args.output)}, indent=2))
            return
    labels = []
    for transition in alignment["reference_transitions"]:
        labels.append({
            "reference_transition_id": transition["reference_transition_id"],
            "source_start_sample_48k": transition["source_start_sample_48k"],
            "source_end_sample_48k": transition["source_end_sample_48k"],
            "boundary_uncertainty_seconds": transition["boundary_uncertainty_seconds"],
            "filmora_action": "removed",
            "human_label": None,
            "human_note": None,
            "reviewed_by": None,
            "reviewed_at": None,
        })
    output = {
        "schema_version": "1.0",
        "stage": "S02-heldout-benchmark-labeling",
        "status": "human_label_required",
        "run_key": run_key,
        "alignment_path": str(args.alignment),
        "alignment_sha256": alignment_sha,
        "allowed_labels": ["must_cut", "acceptable_cut", "must_keep"],
        "judge_input_allowed": False,
        "production_edl_eligible": False,
        "publish_authorized": False,
        "instructions": "Listen on the immutable source timebase. Label editorial necessity; do not infer labels solely from Filmora removal.",
        "label_count": len(labels),
        "labels": labels,
    }
    atomic_json(args.output, output)
    print(json.dumps({"status": output["status"], "label_count": len(labels), "run_key": run_key,
                      "output": str(args.output), "sha256": sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
