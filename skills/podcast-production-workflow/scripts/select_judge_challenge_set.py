#!/usr/bin/env python3
"""Freeze a stratified, label-blind Judge stability challenge set."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile


QUOTAS = {"recording_control": 3, "silence": 2, "filler": 4, "repetition": 4,
          "false_start": 2, "technical_failure": 2}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def spread(items: list[dict], count: int) -> list[dict]:
    if len(items) <= count:
        return items
    if count == 1:
        return [items[len(items) // 2]]
    indexes = [round(i * (len(items) - 1) / (count - 1)) for i in range(count)]
    return [items[index] for index in indexes]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--packet-index", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--text-prompt", type=pathlib.Path, required=True)
    parser.add_argument("--audio-prompt", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    bundle = json.loads(args.candidates.read_text())
    packet_index = {item["candidate_id"]: item for item in json.loads(args.packet_index.read_text())["packets"]}
    selected = []
    counts = {}
    for category, quota in QUOTAS.items():
        candidates = [item for item in bundle["candidates"] if item["category"] == category]
        chosen = spread(candidates, quota)
        counts[category] = len(chosen)
        for item in chosen:
            selected.append({"candidate_id": item["candidate_id"], "category": category,
                             "core_interval": item["core_interval"],
                             "text_packet_sha256": packet_index[item["candidate_id"]]["sha256"]})
    selected.sort(key=lambda item: item["core_interval"]["start_sample"])
    output = {"schema_version": "1.0", "stage": "S04-S05-stability-challenge-set",
              "episode_id": bundle["episode_id"], "selection_method": "category_quota_even_timeline_spread_v1",
              "label_blind": True, "filmora_reference_consumed": False,
              "candidate_bundle_sha256": sha256(args.candidates), "policy_sha256": sha256(args.policy),
              "text_prompt_sha256": sha256(args.text_prompt), "audio_prompt_sha256": sha256(args.audio_prompt),
              "runs_per_judge_per_candidate": 3, "category_counts": counts,
              "candidate_count": len(selected), "candidates": selected,
              "status": "frozen_pending_h1_and_dispatch", "publish_authorized": False}
    atomic_json(args.output, output)
    print(json.dumps({"status": output["status"], "candidate_count": len(selected), "category_counts": counts,
                      "output": str(args.output), "sha256": sha256(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
