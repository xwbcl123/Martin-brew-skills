#!/usr/bin/env python3
"""Evaluate candidate-level exact-label stability without majority-vote promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--challenge", type=pathlib.Path, required=True)
    parser.add_argument("--protocol", type=pathlib.Path, required=True)
    parser.add_argument("--text-results", type=pathlib.Path, required=True)
    parser.add_argument("--audio-results", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--audit", type=pathlib.Path, required=True)
    args = parser.parse_args()
    challenge = json.loads(args.challenge.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    candidate_ids = [item["candidate_id"] for item in challenge["candidates"]]
    threshold = float(protocol["judge_stability"]["exact_label_agreement_min"])
    details = {}
    role_outputs = {}
    for role, directory in (("text", args.text_results), ("audio", args.audio_results)):
        candidates = []
        exact = 0
        complete = 0
        for candidate_id in candidate_ids:
            labels = []
            hashes = []
            for run in (1, 2, 3):
                path = directory / f"run-{run:02}" / "parsed" / f"{candidate_id}.json"
                if path.is_file():
                    response = json.loads(path.read_text(encoding="utf-8"))
                    labels.append(response["verdict"])
                    hashes.append(sha256(path))
                else:
                    labels.append(None)
                    hashes.append(None)
            is_complete = None not in labels
            is_exact = is_complete and len(set(labels)) == 1
            complete += int(is_complete)
            exact += int(is_exact)
            candidates.append({"candidate_id": candidate_id, "labels": labels,
                               "response_hashes": hashes, "complete": is_complete,
                               "exact_agreement": is_exact,
                               "action": "eligible_for_adjudication" if is_exact else "review_required"})
        agreement = exact / len(candidate_ids)
        role_outputs[role] = {
            "model_id": protocol["judge_stability"][f"{role}_model_id"],
            "prompt_sha256": challenge[f"{role}_prompt_sha256"],
            "runs_per_candidate": 3,
            "exact_label_agreement": agreement,
            "passed": complete == len(candidate_ids) and agreement >= threshold,
        }
        details[role] = {"complete_candidates": complete, "exact_candidates": exact,
                         "candidate_count": len(candidate_ids), "candidates": candidates}
    status = "passed" if role_outputs["text"]["passed"] and role_outputs["audio"]["passed"] else (
        "failed" if details["audio"]["complete_candidates"] == len(candidate_ids)
        and role_outputs["audio"]["exact_label_agreement"] < threshold else "pending"
    )
    report = {"schema_version": "1.0", "status": status,
              "challenge_set_sha256": sha256(args.challenge),
              "policy_sha256": challenge["policy_sha256"],
              "text": role_outputs["text"], "audio": role_outputs["audio"]}
    schema = json.loads((ROOT / "references/judge-stability.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)
    audit = {"schema_version": "1.0", "status": status,
             "protocol_sha256": sha256(args.protocol), "threshold": threshold,
             "roles": details, "majority_vote_may_auto_cut": False,
             "publish_authorized": False}
    atomic_json(args.output, report)
    atomic_json(args.audit, audit)
    print(json.dumps({"status": status, "report": str(args.output), "report_sha256": sha256(args.output),
                      "audit": str(args.audit), "audit_sha256": sha256(args.audit)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
