#!/usr/bin/env python3
"""Deterministic risk-stratified H2 sampling shared by renderer and receipt verifier."""

from __future__ import annotations

import hashlib
import json


RATE = 48000
PROTOCOL_ID = "human-restore-risk-sampling-v1"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def risk_tier(cut: dict) -> str:
    categories = set(cut["categories"])
    duration = (cut["applied_interval"]["end_sample"] - cut["applied_interval"]["start_sample"]) / RATE
    if "recording_control" in categories or len(categories) > 1 or len(cut["candidate_ids"]) >= 3 or duration >= 1.2:
        return "high"
    if "repetition" in categories or len(cut["candidate_ids"]) == 2 or duration > 0.8:
        return "medium"
    return "low"


def targeted(cut: dict) -> bool:
    categories = set(cut["categories"])
    duration = (cut["applied_interval"]["end_sample"] - cut["applied_interval"]["start_sample"]) / RATE
    return "recording_control" in categories or len(categories) > 1 or duration >= 2.0


def spread_sample(cuts: list[dict], count: int) -> list[str]:
    ordered = sorted(cuts, key=lambda item: (item["applied_interval"]["start_sample"], item["cut_id"]))
    if len(ordered) <= count:
        return [item["cut_id"] for item in ordered]
    indices = []
    for index in range(count):
        position = round(index * (len(ordered) - 1) / (count - 1)) if count > 1 else len(ordered) // 2
        if position not in indices:
            indices.append(position)
    return [ordered[index]["cut_id"] for index in indices]


def build_plan(edl: dict) -> dict:
    enriched = [{**cut, "risk_tier": risk_tier(cut)} for cut in edl["cuts"]]
    targeted_ids = [cut["cut_id"] for cut in enriched if targeted(cut)]
    targeted_set = set(targeted_ids)
    targets = {"high": 15, "medium": 10, "low": 10}
    strata = []
    for tier in ("high", "medium", "low"):
        population = [cut for cut in enriched if cut["risk_tier"] == tier and cut["cut_id"] not in targeted_set]
        sample_ids = spread_sample(population, min(targets[tier], len(population)))
        strata.append({"stratum_id": tier, "population_count": len(population), "sample_cut_ids": sample_ids,
                       "sample_count": len(sample_ids), "fail_at_restore_count": 2,
                       "acceptance_rule": "pass only when sampled restore_count <= 1"})
    required = list(dict.fromkeys(targeted_ids + [cut_id for stratum in strata for cut_id in stratum["sample_cut_ids"]]))
    plan = {"schema_version": "1.0", "protocol_id": PROTOCOL_ID,
            "selection_method": "targeted sentinels plus deterministic timeline-spread risk strata",
            "targeted_cut_ids": targeted_ids, "strata": strata, "required_review_cut_ids": required,
            "required_review_count": len(required), "total_cut_count": len(edl["cuts"]),
            "unreviewed_default_action": "accept_cut",
            "failure_policy": {"sample_fail_at_restore_count": 2,
                               "failed_stratum_blocks_h2_approval": True,
                               "targeted_restores_are_corrected_exceptions_not_sampling_failures": True}}
    return plan


def evaluate(plan: dict, decisions: list[dict]) -> dict:
    actions = {item["cut_id"]: item["action"] for item in decisions}
    results = []
    for stratum in plan["strata"]:
        restores = [cut_id for cut_id in stratum["sample_cut_ids"] if actions.get(cut_id) == "restore_source"]
        results.append({"stratum_id": stratum["stratum_id"], "sample_count": stratum["sample_count"],
                        "restore_count": len(restores), "restored_cut_ids": restores,
                        "passed": len(restores) < stratum["fail_at_restore_count"]})
    failed = [item["stratum_id"] for item in results if not item["passed"]]
    return {"strata": results, "failed_strata": failed, "sampling_passed": not failed}
