#!/usr/bin/env python3
"""Build an H2-review EDL from auto-cut-eligible adjudications without expanding cores."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/edl.schema.json"
RATE = 48000


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


def probe_samples(path: pathlib.Path) -> tuple[int, dict]:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                             "-show_entries", "stream=sample_rate,channels,duration_ts,time_base,codec_name",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    if int(stream["sample_rate"]) != RATE:
        raise SystemExit("render audio must be 48 kHz")
    duration_ts = int(stream["duration_ts"])
    numerator, denominator = map(int, stream["time_base"].split("/"))
    samples = round(duration_ts * numerator / denominator * RATE)
    return samples, stream


def margin_samples(category: str, policy: dict) -> tuple[int, str]:
    key = "silence_inward_margin_ms" if category == "silence" else "speech_inward_margin_ms"
    return round(policy["buffer_policy"][key] * RATE / 1000), key


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--adjudication", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--render-audio", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text())
    by_id = {item["candidate_id"]: item for item in candidates["candidates"]}
    adjudication = json.loads(args.adjudication.read_text())
    policy = json.loads(args.policy.read_text())
    source_samples, probe = probe_samples(args.render_audio)
    proposed = []
    skipped_too_short = []
    for decision in adjudication["decisions"]:
        if decision["decision"] != "auto_cut_eligible":
            continue
        candidate = by_id[decision["candidate_id"]]
        core = candidate["core_interval"]
        margin, rule = margin_samples(candidate["category"], policy)
        start, end = core["start_sample"] + margin, core["end_sample"] - margin
        if start >= end:
            skipped_too_short.append(candidate["candidate_id"])
            continue
        if not (core["start_sample"] <= start < end <= core["end_sample"] <= source_samples):
            raise SystemExit(f"buffer invariant failed for {candidate['candidate_id']}")
        proposed.append({"candidate_ids": [candidate["candidate_id"]], "categories": [candidate["category"]],
                         "core_intervals": [core], "start_sample": start, "end_sample": end,
                         "buffer_rule": f"{rule}:inward_only"})

    merged = []
    for item in sorted(proposed, key=lambda x: (x["start_sample"], x["end_sample"])):
        if merged and item["start_sample"] <= merged[-1]["end_sample"]:
            previous = merged[-1]
            previous["end_sample"] = max(previous["end_sample"], item["end_sample"])
            previous["candidate_ids"].extend(item["candidate_ids"])
            previous["categories"].extend(item["categories"])
            previous["core_intervals"].extend(item["core_intervals"])
            previous["buffer_rule"] = "overlapping_inward_only_intervals_union"
        else:
            merged.append(item)
    cuts = []
    for index, item in enumerate(merged, 1):
        interval = {"start_sample": item.pop("start_sample"), "end_sample": item.pop("end_sample")}
        cuts.append({"cut_id": f"CUT{index:04d}", "candidate_ids": list(dict.fromkeys(item["candidate_ids"])),
                     "categories": list(dict.fromkeys(item["categories"])), "core_intervals": item["core_intervals"],
                     "proposed_interval": interval, "applied_interval": dict(interval),
                     "buffer_rule": item["buffer_rule"], "decision_status": "requires_h2_human_approval"})
    removed = sum(c["applied_interval"]["end_sample"] - c["applied_interval"]["start_sample"] for c in cuts)
    inputs = {"candidates": sha256(args.candidates), "adjudication": sha256(args.adjudication),
              "policy": sha256(args.policy), "render_audio": sha256(args.render_audio)}
    run_key = hashlib.sha256(json.dumps({"stage": "S07-v1", "inputs": inputs}, sort_keys=True).encode()).hexdigest()
    output = {"schema_version": "1.0", "episode_id": candidates["episode_id"], "stage": "S07-buffered-edl",
              "status": "review_required", "run_key": run_key,
              "timebase": {"basis": "source-audio", "sample_rate_hz": RATE, "interval_semantics": "half-open"},
              "source_audio": {"path": str(args.render_audio), "sha256": inputs["render_audio"],
                               "total_samples": source_samples, "probe": probe},
              "adjudication_sha256": inputs["adjudication"], "policy_sha256": inputs["policy"],
              "crossfade_samples": round(policy["buffer_policy"]["crossfade_ms"] * RATE / 1000),
              "cuts": cuts,
              "summary": {"auto_cut_eligible_candidates": len(proposed), "applied_cut_count": len(cuts),
                          "skipped_too_short": skipped_too_short, "removed_samples": removed,
                          "removed_seconds": removed / RATE, "overlap_count": 0,
                          "applied_intervals_subset_of_candidate_cores": True},
              "approved": False, "publish_authorized": False}
    jsonschema.validate(output, json.loads(SCHEMA.read_text()))
    atomic_json(args.output, output)
    print(json.dumps({"status": output["status"], "run_key": run_key, "summary": output["summary"],
                      "output": str(args.output), "sha256": sha256(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
