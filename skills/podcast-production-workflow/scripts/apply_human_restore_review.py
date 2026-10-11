#!/usr/bin/env python3
"""Apply a complete H2 human restore receipt to an aggressive EDL."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile

from human_review_sampling import PROTOCOL_ID, build_plan, canonical_hash, evaluate


ROOT = pathlib.Path(__file__).resolve().parents[1]
EDL_SCHEMA = ROOT / "references/edl.schema.json"
REVIEW_SCHEMA = ROOT / "references/human-restore-review.schema.json"
RATE = 48000


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser(); parser.add_argument("--edl", type=pathlib.Path, required=True)
    parser.add_argument("--render-report", type=pathlib.Path, required=True)
    parser.add_argument("--edited-audio", type=pathlib.Path, required=True); parser.add_argument("--review", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True); args = parser.parse_args()
    edl = json.loads(args.edl.read_text(encoding="utf-8")); jsonschema.validate(edl, json.loads(EDL_SCHEMA.read_text()))
    review = json.loads(args.review.read_text(encoding="utf-8")); jsonschema.validate(review, json.loads(REVIEW_SCHEMA.read_text()))
    render_report = json.loads(args.render_report.read_text(encoding="utf-8"))
    if render_report.get("edl", {}).get("sha256") != sha256(args.edl) or render_report.get("output_audio", {}).get("sha256") != sha256(args.edited_audio):
        raise SystemExit("render report does not bind EDL and edited review audio")
    if review["episode_id"] != edl["episode_id"] or review["edl_sha256"] != sha256(args.edl):
        raise SystemExit("review receipt does not bind this episode/EDL")
    if review["render_report_sha256"] != sha256(args.render_report): raise SystemExit("review receipt does not bind render report")
    if review["edited_audio_sha256"] != sha256(args.edited_audio): raise SystemExit("review receipt does not bind edited review audio")
    plan = build_plan(edl)
    if review["review_protocol_id"] != PROTOCOL_ID or review["review_plan_sha256"] != canonical_hash(plan):
        raise SystemExit("review receipt does not bind canonical sampling plan")
    expected = [item["cut_id"] for item in edl["cuts"]]; required = set(plan["required_review_cut_ids"]); decisions = review["decisions"]
    actual = [item["cut_id"] for item in decisions]
    if len(actual) != len(set(actual)) or not set(actual) <= set(expected) or not required <= set(actual):
        raise SystemExit("review must contain every canonical required sample exactly once and no unknown cuts")
    computed = evaluate(plan, decisions)
    if review["sampling_evaluation"] != computed: raise SystemExit("sampling evaluation mismatch")
    if review["status"] != ("approved" if computed["sampling_passed"] else "failed"):
        raise SystemExit("review status does not match sampling evaluation")
    if not computed["sampling_passed"]:
        raise SystemExit(f"sampling failed for strata {computed['failed_strata']}; expand review or revise edit policy")
    action = {item["cut_id"]: item["action"] for item in decisions}
    kept = [item for item in edl["cuts"] if action.get(item["cut_id"], "accept_cut") == "accept_cut"]
    restored = [item for item in expected if action.get(item) == "restore_source"]
    removed = sum(item["applied_interval"]["end_sample"] - item["applied_interval"]["start_sample"] for item in kept)
    review_sha = sha256(args.review); output = dict(edl); output["cuts"] = kept
    output["adjudication_sha256"] = review_sha
    output["run_key"] = canonical_hash({"stage": "S07-human-restored-v1.1", "parent_edl_sha256": sha256(args.edl), "review_sha256": review_sha})
    output["summary"] = {**edl["summary"], "authority": "risk_stratified_human_restore_review", "review_receipt_sha256": review_sha,
                         "reviewed_by": review["reviewed_by"], "reviewed_at": review["reviewed_at"],
                         "review_protocol_id": PROTOCOL_ID, "review_plan_sha256": canonical_hash(plan),
                         "required_review_count": plan["required_review_count"], "sampling_evaluation": computed,
                         "accepted_cut_count": len(kept), "restored_cut_ids": restored,
                         "removed_samples": removed, "removed_seconds": removed / RATE}
    jsonschema.validate(output, json.loads(EDL_SCHEMA.read_text())); atomic_json(args.output, output)
    print(json.dumps({"status": "review_required", "output": str(args.output), "sha256": sha256(args.output),
                      "accepted_cut_count": len(kept), "restored_cut_ids": restored,
                      "h2_receipt_verified": True, "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
