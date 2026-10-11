#!/usr/bin/env python3
"""Validate a frozen H1 protocol, live hashes, alignment gates and unopened labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/benchmark-protocol.schema.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--approval", type=pathlib.Path)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(protocol)]
    artifacts = []
    for role, artifact in protocol.get("frozen_artifacts", {}).items():
        path = pathlib.Path(artifact["path"])
        actual = sha256(path) if path.is_file() else None
        artifacts.append({"role": role, "path": str(path), "expected_sha256": artifact["sha256"],
                          "actual_sha256": actual, "verified": actual == artifact["sha256"]})
    alignment_path = pathlib.Path(protocol["frozen_artifacts"]["filmora_alignment"]["path"])
    alignment = json.loads(alignment_path.read_text())
    evidence = alignment["evidence"]; thresholds = protocol["timeline_thresholds"]
    alignment_valid = bool(alignment.get("alignment_valid")
                           and evidence["confident_reference_coverage"] >= thresholds["filmora_confident_coverage_min"]
                           and evidence["anchor_residual_median_ms"] <= thresholds["alignment_residual_median_ms_max"]
                           and evidence["anchor_residual_p95_ms"] <= thresholds["alignment_residual_p95_ms_max"])
    labels_path = pathlib.Path(protocol["labels"]["template_artifact"]["path"])
    labels = json.loads(labels_path.read_text())
    unopened = all(item.get("human_label") is None and item.get("reviewed_by") is None for item in labels["labels"])
    challenge = json.loads(pathlib.Path(protocol["frozen_artifacts"]["challenge_set"]["path"]).read_text())
    challenge_blind = challenge.get("label_blind") is True and challenge.get("filmora_reference_consumed") is False
    approval_valid = False; approval_detail = None
    protocol_sha = sha256(args.protocol)
    if args.approval and args.approval.is_file():
        approval_detail = json.loads(args.approval.read_text())
        approval_valid = (approval_detail.get("gate") == "H1-benchmark-protocol"
                          and approval_detail.get("status") == "approved"
                          and approval_detail.get("protocol_sha256") == protocol_sha
                          and approval_detail.get("approved_by") == "Martin")
    protocol_valid = not errors and all(item["verified"] for item in artifacts) and alignment_valid and unopened and challenge_blind
    report = {"schema_version": "1.0", "protocol_path": str(args.protocol), "protocol_sha256": protocol_sha,
              "schema_valid": not errors, "schema_errors": errors, "artifacts": artifacts,
              "alignment_gate_valid": alignment_valid, "heldout_labels_unopened": unopened,
              "challenge_set_blind": challenge_blind, "protocol_valid": protocol_valid,
              "h1_approval_valid": approval_valid, "approval_detail": approval_detail,
              "external_judge_dispatch_authorized": protocol_valid and approval_valid,
              "publish_authorized": False}
    atomic_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["external_judge_dispatch_authorized"] else 1)


if __name__ == "__main__":
    main()
