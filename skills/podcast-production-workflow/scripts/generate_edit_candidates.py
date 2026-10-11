#!/usr/bin/env python3
"""Generate high-recall edit candidates without making or applying cut decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import tempfile


FILLERS = {"嗯", "呃", "额", "昂"}
PURE_FILLER = re.compile(r"^[\s，。！？、,.!?…]*(?:嗯+|呃+|额+|昂+|啊+)(?:[\s，。！？、,.!?…]*(?:嗯+|呃+|额+|昂+|啊+))*[\s，。！？、,.!?…]*$")
CONTROL = re.compile(r"^[\s，。！？、,.!?…]*(?:卡+|停止(?:录制)?|停机录制)(?:[\s，。！？、,.!?…]*(?:卡+|停止(?:录制)?|停机录制))*[\s，。！？、,.!?…]*$")
SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")
PUNCT = " ，。！？、,.!?…"


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


def load_segments(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["transcription"]


def milliseconds_to_sample(value: int, rate: int = 48000) -> int:
    return round(value * rate / 1000)


def clean_token(text: str) -> str:
    return text.strip(PUNCT)


def segment_tokens(segment: dict) -> list[dict]:
    return [token for token in segment.get("tokens", [])
            if clean_token(token.get("text", "")) and not token.get("text", "").startswith("[")]


def add_restart_candidates(items: list[dict], segments: list[dict], lane: str,
                           common: dict, policy: dict) -> None:
    """Emit candidate-only restart evidence; never applies cuts itself."""
    detector = policy.get("rough_cut_detectors", {})
    if not detector.get("enabled", False):
        return
    protected = policy["protected_discourse_markers"]
    phrases = [[clean_token(part) for part in phrase.split() if clean_token(part)]
               for phrase in detector.get("restart_trigger_phrases", [])]
    repeat_words = int(detector.get("repeated_start_token_count", 3))
    previous_signature: tuple[str, ...] | None = None
    previous_index: int | None = None
    for index, segment in enumerate(segments):
        tokens = segment_tokens(segment)
        words = [clean_token(token.get("text", "")).lower() for token in tokens]
        for phrase in phrases:
            length = len(phrase)
            if not length:
                continue
            for offset in range(len(words) - length + 1):
                if words[offset:offset + length] == phrase:
                    start_ms = int(segment["offsets"]["from"])
                    end_ms = int(tokens[offset + length - 1]["offsets"]["to"])
                    add_candidate(items, category="restart_marker", start_ms=start_ms, end_ms=end_ms,
                                  context=bounded_context(segments, index, " ".join(phrase), protected),
                                  evidence={"detector": "explicit_restart_phrase", "lane": lane,
                                            "phrase": " ".join(phrase), "strategy": "segment_start_through_marker"}, **common)
                    break
        if repeat_words > 0 and len(words) >= repeat_words:
            signature = tuple(words[:repeat_words])
            if previous_signature == signature and previous_index is not None:
                previous = segments[previous_index]
                add_candidate(items, category="repetition", start_ms=int(previous["offsets"]["from"]),
                              end_ms=int(previous["offsets"]["to"]),
                              context=bounded_context(segments, previous_index, "".join(signature), protected),
                              evidence={"detector": "repeated_segment_start", "lane": lane,
                                        "token_count": repeat_words, "signature": list(signature)}, **common)
            previous_signature, previous_index = signature, index


def bounded_context(segments: list[dict], index: int, candidate: str, protected: list[str]) -> dict:
    before = segments[index - 1]["text"].strip() if index else ""
    after = segments[index + 1]["text"].strip() if index + 1 < len(segments) else ""
    return {
        "text_before": before[-240:],
        "candidate_text": candidate,
        "text_after": after[:240],
        "protected_tokens": protected,
    }


def add_candidate(items: list[dict], *, episode_id: str, source_sha: str, analysis_sha: str,
                  policy_sha: str, category: str, start_ms: int, end_ms: int, context: dict,
                  evidence: dict) -> None:
    if end_ms <= start_ms:
        return
    items.append({
        "schema_version": "1.0",
        "candidate_id": "pending",
        "episode_id": episode_id,
        "source_sha256": source_sha,
        "analysis_audio_sha256": analysis_sha,
        "timebase": {"basis": "source-audio", "sample_rate_hz": 48000},
        "category": category,
        "core_interval": {
            "start_sample": milliseconds_to_sample(start_ms),
            "end_sample": milliseconds_to_sample(end_ms),
        },
        "context": context,
        "detector_evidence": [evidence],
        "policy_sha256": policy_sha,
    })


def lane_candidates(items: list[dict], path: pathlib.Path, lane: str, common: dict, policy: dict) -> None:
    segments = load_segments(path)
    add_restart_candidates(items, segments, lane, common, policy)
    protected_terms = policy["protected_discourse_markers"]
    for index, segment in enumerate(segments):
        text = segment["text"].strip()
        offsets = segment["offsets"]
        if CONTROL.fullmatch(text):
            add_candidate(items, category="recording_control", start_ms=offsets["from"], end_ms=offsets["to"],
                          context=bounded_context(segments, index, text, protected_terms),
                          evidence={"detector": "control_segment", "lane": lane, "text": text}, **common)
        elif PURE_FILLER.fullmatch(text):
            add_candidate(items, category="filler", start_ms=offsets["from"], end_ms=offsets["to"],
                          context=bounded_context(segments, index, text, protected_terms),
                          evidence={"detector": "pure_filler_segment", "lane": lane, "text": text}, **common)

        real_tokens = segment_tokens(segment)
        for token_index, token in enumerate(real_tokens):
            token_text = clean_token(token.get("text", ""))
            token_offsets = token.get("offsets", {})
            duration = token_offsets.get("to", 0) - token_offsets.get("from", 0)
            probability = float(token.get("p", 0) or 0)
            if token_text in FILLERS and 50 <= duration <= 1800 and probability >= policy["candidate_thresholds"]["token_probability_min"]:
                add_candidate(items, category="filler", start_ms=token_offsets["from"], end_ms=token_offsets["to"],
                              context=bounded_context(segments, index, token_text, protected_terms),
                              evidence={"detector": "exact_filler_token", "lane": lane, "text": token_text,
                                        "probability": probability}, **common)
            if token_index and token_text == clean_token(real_tokens[token_index - 1].get("text", "")) and len(token_text) <= 3:
                previous = real_tokens[token_index - 1]["offsets"]
                add_candidate(items, category="repetition", start_ms=previous["from"], end_ms=token_offsets["to"],
                              context=bounded_context(segments, index, token_text * 2, protected_terms),
                              evidence={"detector": "adjacent_identical_asr_tokens", "lane": lane, "token": token_text}, **common)


def silence_candidates(items: list[dict], path: pathlib.Path, common: dict, policy: dict) -> None:
    pending: float | None = None
    edge_ms = round(policy["candidate_thresholds"]["silence_edge_keep_seconds"] * 1000)
    minimum = policy["candidate_thresholds"]["silence_min_seconds"]
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := SILENCE_START.search(line):
            pending = float(match.group(1))
        if match := SILENCE_END.search(line):
            end, duration = float(match.group(1)), float(match.group(2))
            start = pending if pending is not None else end - duration
            pending = None
            if duration < minimum:
                continue
            start_ms, end_ms = round(start * 1000) + edge_ms, round(end * 1000) - edge_ms
            add_candidate(items, category="silence", start_ms=start_ms, end_ms=end_ms,
                          context={"text_before": "", "candidate_text": f"silence {duration:.3f}s",
                                   "text_after": "", "protected_tokens": []},
                          evidence={"detector": "ffmpeg_silencedetect", "duration_seconds": duration,
                                    "edge_keep_seconds": edge_ms / 1000}, **common)


def merge_duplicates(items: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for item in items:
        core = item["core_interval"]
        key = (item["category"], core["start_sample"], core["end_sample"])
        if key in groups:
            groups[key]["detector_evidence"].extend(item["detector_evidence"])
        else:
            groups[key] = item
    ordered = sorted(groups.values(), key=lambda value: (value["core_interval"]["start_sample"], value["core_interval"]["end_sample"], value["category"]))
    for index, item in enumerate(ordered, 1):
        item["candidate_id"] = f"C{index:04d}"
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--standard-asr", type=pathlib.Path, required=True)
    parser.add_argument("--filler-asr", type=pathlib.Path, required=True)
    parser.add_argument("--silence-log", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    common = {
        "episode_id": manifest["episode_id"],
        "source_sha": manifest["source"]["sha256"],
        "analysis_sha": manifest["audio_roles"]["analysis_audio"]["sha256"],
        "policy_sha": sha256(args.policy),
    }
    input_hashes = {str(path): sha256(path) for path in (args.manifest, args.policy, args.standard_asr, args.filler_asr, args.silence_log)}
    run_key = hashlib.sha256(json.dumps({"stage": "S03", "inputs": input_hashes}, sort_keys=True).encode()).hexdigest()
    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run_key") == run_key:
            print(json.dumps({"status": "skipped_cached", "run_key": run_key, "output": str(args.output), "sha256": sha256(args.output)}, indent=2))
            return

    items: list[dict] = []
    lane_candidates(items, args.standard_asr, "whisper_standard", common, policy)
    lane_candidates(items, args.filler_asr, "whisper_filler_prompt", common, policy)
    silence_candidates(items, args.silence_log, common, policy)
    candidates = merge_duplicates(items)
    counts = {category: sum(item["category"] == category for item in candidates) for category in sorted({item["category"] for item in candidates})}
    output = {
        "schema_version": "1.0",
        "stage": "S03-candidate-generation",
        "status": "candidate_only_no_cuts_applied",
        "episode_id": manifest["episode_id"],
        "run_key": run_key,
        "policy_sha256": common["policy_sha"],
        "inputs": input_hashes,
        "calibrated_text_consumed": False,
        "filmora_reference_consumed": False,
        "judge_dispatch_authorized": False,
        "publish_authorized": False,
        "candidate_count": len(candidates),
        "category_counts": counts,
        "candidates": candidates,
    }
    atomic_json(args.output, output)
    print(json.dumps({"status": output["status"], "candidate_count": len(candidates), "category_counts": counts,
                      "run_key": run_key, "output": str(args.output), "sha256": sha256(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
