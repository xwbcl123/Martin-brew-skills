#!/usr/bin/env python3
"""Fail-closed adjudication of independently captured text and audio Judge evidence."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESPONSE_SCHEMA = ROOT / "references/judge-response.schema.json"
STABILITY_SCHEMA = ROOT / "references/judge-stability.schema.json"
OUTPUT_SCHEMA = ROOT / "references/adjudication.schema.json"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def packet_map(path: pathlib.Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["candidate_id"]: item["sha256"] for item in data["packets"]}


def load_responses(directory: pathlib.Path, role: str, packets: dict[str, str], stability: dict,
                   response_schema: dict) -> tuple[dict[str, list[dict]], list[str]]:
    import jsonschema
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    errors: list[str] = []
    expected = stability[role]
    for path in sorted(directory.glob("*.json")):
        try:
            response = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(response, response_schema)
            candidate_id = response["candidate_id"]
            if response["judge_role"] != role:
                raise ValueError("judge_role mismatch")
            if response["model_id"] != expected["model_id"] or response["prompt_sha256"] != expected["prompt_sha256"]:
                raise ValueError("model/prompt identity mismatch")
            if packets.get(candidate_id) != response["candidate_packet_sha256"]:
                raise ValueError("candidate packet identity mismatch")
            raw = path.with_suffix(".raw.txt")
            if not raw.is_file() or sha256(raw) != response["raw_response_sha256"]:
                raise ValueError("raw response missing or hash mismatch")
            grouped[candidate_id].append(response)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    return grouped, errors


def stable_verdict(responses: list[dict]) -> tuple[str, float]:
    if not responses:
        return "missing", 0.0
    labels = {item["verdict"] for item in responses}
    if len(labels) != 1:
        return "drift", min(float(item["confidence"]) for item in responses)
    return next(iter(labels)), min(float(item["confidence"]) for item in responses)


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--stability-report", type=pathlib.Path, required=True)
    parser.add_argument("--text-packet-index", type=pathlib.Path, required=True)
    parser.add_argument("--audio-packet-index", type=pathlib.Path, required=True)
    parser.add_argument("--text-response-dir", type=pathlib.Path, required=True)
    parser.add_argument("--audio-response-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    response_schema = json.loads(RESPONSE_SCHEMA.read_text())
    stability_schema = json.loads(STABILITY_SCHEMA.read_text())
    output_schema = json.loads(OUTPUT_SCHEMA.read_text())
    stability = json.loads(args.stability_report.read_text())
    jsonschema.validate(stability, stability_schema)
    policy_sha = sha256(args.policy)
    if stability["status"] != "passed" or not stability["text"]["passed"] or not stability["audio"]["passed"]:
        raise SystemExit("Judge stability gate has not passed")
    if stability["policy_sha256"] != policy_sha:
        raise SystemExit("stability report policy hash mismatch")

    candidates = json.loads(args.candidates.read_text())
    policy = json.loads(args.policy.read_text())
    text, text_errors = load_responses(args.text_response_dir, "text", packet_map(args.text_packet_index), stability, response_schema)
    audio, audio_errors = load_responses(args.audio_response_dir, "audio", packet_map(args.audio_packet_index), stability, response_schema)
    threshold = float(policy["decision_policy"]["cut_confidence_min"])
    decisions = []
    for candidate in candidates["candidates"]:
        cid = candidate["candidate_id"]
        tv, tc = stable_verdict(text.get(cid, []))
        av, ac = stable_verdict(audio.get(cid, []))
        reasons = []
        if tv == av == "cut" and tc >= threshold and ac >= threshold:
            decision = "auto_cut_eligible"
            reasons.append("dual_cut_stable_above_confidence_gate")
        elif tv == av == "keep":
            decision = "keep"
            reasons.append("dual_keep_stable")
        else:
            decision = "review_required"
            if tv in {"missing", "drift"} or av in {"missing", "drift"}:
                reasons.append("missing_or_drifting_judge_evidence")
            if tv != av:
                reasons.append("judge_disagreement_or_abstention")
            if tv == av == "cut" and min(tc, ac) < threshold:
                reasons.append("cut_confidence_below_gate")
        decisions.append({"candidate_id": cid, "category": candidate["category"],
                          "core_interval": candidate["core_interval"], "text_verdict": tv,
                          "audio_verdict": av, "decision": decision, "reason_codes": reasons})
    counts = collections.Counter(item["decision"] for item in decisions)
    input_hashes = {name: sha256(path) for name, path in {
        "candidates": args.candidates, "policy": args.policy, "stability": args.stability_report,
        "text_index": args.text_packet_index, "audio_index": args.audio_packet_index}.items()}
    response_hashes = sorted(sha256(p) for d in (args.text_response_dir, args.audio_response_dir) for p in d.glob("*"))
    run_key = hashlib.sha256(json.dumps({"stage": "S06-v1", "inputs": input_hashes,
                                         "responses": response_hashes}, sort_keys=True).encode()).hexdigest()
    output = {"schema_version": "1.0", "episode_id": candidates["episode_id"], "stage": "S06-adjudicate",
              "status": "review_required" if counts["review_required"] or text_errors or audio_errors else "succeeded",
              "run_key": run_key, "policy_sha256": policy_sha,
              "stability_report_sha256": sha256(args.stability_report),
              "candidate_bundle_sha256": sha256(args.candidates), "decisions": decisions,
              "summary": {"decision_counts": dict(sorted(counts.items())), "invalid_text_responses": text_errors,
                          "invalid_audio_responses": audio_errors}, "publish_authorized": False}
    jsonschema.validate(output, output_schema)
    atomic_json(args.output, output)
    print(json.dumps({"status": output["status"], "run_key": run_key, "summary": output["summary"],
                      "output": str(args.output), "sha256": sha256(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
