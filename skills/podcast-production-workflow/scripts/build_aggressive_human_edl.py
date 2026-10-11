#!/usr/bin/env python3
"""Build an aggressive, deterministic H2-review EDL without LLM Judge authority."""

from __future__ import annotations

import argparse
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


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def probe_samples(path: pathlib.Path) -> tuple[int, dict]:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                             "stream=sample_rate,channels,duration_ts,time_base,codec_name", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    if int(stream["sample_rate"]) != RATE:
        raise SystemExit("render audio must be 48 kHz")
    numerator, denominator = map(int, stream["time_base"].split("/"))
    samples = round(int(stream["duration_ts"]) * numerator / denominator * RATE)
    return samples, stream


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--render-audio", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--include-category", action="append", default=[])
    args = parser.parse_args()
    bundle = json.loads(args.candidates.read_text(encoding="utf-8")); policy = json.loads(args.policy.read_text(encoding="utf-8"))
    source_samples, probe = probe_samples(args.render_audio)
    selected_categories = set(args.include_category or policy.get("human_restore_review", {}).get("include_categories", []))
    proposed = []; skipped = []
    for candidate in bundle["candidates"]:
        category = candidate["category"]
        if selected_categories and category not in selected_categories:
            continue
        core = candidate["core_interval"]
        margin_key = "silence_inward_margin_ms" if category == "silence" else "speech_inward_margin_ms"
        margin = round(policy["buffer_policy"][margin_key] * RATE / 1000)
        start, end = core["start_sample"] + margin, core["end_sample"] - margin
        if start >= end:
            skipped.append(candidate["candidate_id"]); continue
        if not (0 <= core["start_sample"] <= start < end <= core["end_sample"] <= source_samples):
            raise SystemExit(f"buffer invariant failed for {candidate['candidate_id']}")
        proposed.append({"candidate_ids": [candidate["candidate_id"]], "categories": [category],
                         "core_intervals": [core], "start_sample": start, "end_sample": end,
                         "buffer_rule": f"{margin_key}:inward_only:human_restore_review"})
    merged: list[dict] = []
    for item in sorted(proposed, key=lambda value: (value["start_sample"], value["end_sample"])):
        if merged and item["start_sample"] <= merged[-1]["end_sample"]:
            previous = merged[-1]; previous["end_sample"] = max(previous["end_sample"], item["end_sample"])
            previous["candidate_ids"].extend(item["candidate_ids"]); previous["categories"].extend(item["categories"])
            previous["core_intervals"].extend(item["core_intervals"])
            previous["buffer_rule"] = "overlapping_inward_only_intervals_union:human_restore_review"
        else:
            merged.append(item)
    cuts = []
    for index, item in enumerate(merged, 1):
        interval = {"start_sample": item.pop("start_sample"), "end_sample": item.pop("end_sample")}
        cuts.append({"cut_id": f"HCUT{index:04d}", "candidate_ids": list(dict.fromkeys(item["candidate_ids"])),
                     "categories": list(dict.fromkeys(item["categories"])), "core_intervals": item["core_intervals"],
                     "proposed_interval": interval, "applied_interval": dict(interval),
                     "buffer_rule": item["buffer_rule"], "decision_status": "requires_h2_human_approval"})
    source_sha, candidate_sha, policy_sha = sha256(args.render_audio), sha256(args.candidates), sha256(args.policy)
    local_declaration = {"mode": "aggressive_human_restore_review", "candidates_sha256": candidate_sha,
                         "policy_sha256": policy_sha, "selected_categories": sorted(selected_categories)}
    declaration_sha = canonical_hash(local_declaration)
    removed = sum(item["applied_interval"]["end_sample"] - item["applied_interval"]["start_sample"] for item in cuts)
    requested_crossfade = round(policy["buffer_policy"]["crossfade_ms"] * RATE / 1000)
    keep_gaps = [right["applied_interval"]["start_sample"] - left["applied_interval"]["end_sample"]
                 for left, right in zip(cuts, cuts[1:])]
    safe_crossfade = min(requested_crossfade, max(0, (min(keep_gaps) - 1) // 2)) if keep_gaps else requested_crossfade
    run_key = canonical_hash({"stage": "S07-human-restore-v1", "source": source_sha, "declaration": declaration_sha})
    output = {"schema_version": "1.0", "episode_id": bundle["episode_id"], "stage": "S07-buffered-edl",
              "status": "review_required", "run_key": run_key,
              "timebase": {"basis": "source-audio", "sample_rate_hz": RATE, "interval_semantics": "half-open"},
              "source_audio": {"path": str(args.render_audio), "sha256": source_sha, "total_samples": source_samples, "probe": probe},
              "adjudication_sha256": declaration_sha, "policy_sha256": policy_sha,
              "crossfade_samples": safe_crossfade, "cuts": cuts,
              "summary": {"authority": "human_restore_review", "llm_judge_consumed": False,
                          "candidate_count": len(bundle["candidates"]), "aggressive_candidate_count": len(proposed),
                          "applied_cut_count": len(cuts), "skipped_too_short": skipped,
                          "removed_samples": removed, "removed_seconds": removed / RATE,
                          "requested_crossfade_samples": requested_crossfade, "effective_crossfade_samples": safe_crossfade,
                          "default_review_action": "accept_cut", "explicit_exception_action": "restore_source"},
              "approved": False, "publish_authorized": False}
    jsonschema.validate(output, json.loads(SCHEMA.read_text(encoding="utf-8"))); atomic_json(args.output, output)
    print(json.dumps({"status": "review_required", "run_key": run_key, "output": str(args.output),
                      "sha256": sha256(args.output), "summary": output["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
