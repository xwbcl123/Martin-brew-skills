#!/usr/bin/env python3
"""Run one fresh-process Judge pass over a frozen challenge set."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import tempfile
import time
from typing import Any

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESPONSE_SCHEMA = ROOT / "references/judge-response.schema.json"
SEMANTIC_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate_id", "verdict", "confidence", "reason", "quoted_evidence"],
    "properties": {
        "candidate_id": {"type": "string"},
        "verdict": {"enum": ["cut", "keep", "abstain"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string", "minLength": 1, "maxLength": 1000},
        "quoted_evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    },
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def normalize_semantic(value: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    """Project provider-shaped JSON onto the frozen semantic response surface."""
    verdict = next((value.get(key) for key in
                    ("verdict", "decision", "raw_verdict", "judgment", "editorial_verdict")
                    if value.get(key)), None)
    reason = next((value.get(key) for key in ("reason", "explanation", "rationale", "abstain_reason")
                   if value.get(key)), None)
    evidence = value.get("quoted_evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    normalized = {
        "candidate_id": value.get("candidate_id"),
        "verdict": verdict,
        "confidence": value.get("confidence"),
        "reason": reason,
        "quoted_evidence": evidence,
    }
    jsonschema.validate(normalized, SEMANTIC_SCHEMA)
    if normalized["candidate_id"] != candidate_id:
        raise ValueError("candidate_id mismatch")
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", choices=["text", "audio"], required=True)
    parser.add_argument("--run", type=int, choices=[1, 2, 3], required=True)
    parser.add_argument("--challenge", type=pathlib.Path, required=True)
    parser.add_argument("--text-packets", type=pathlib.Path)
    parser.add_argument("--audio-packets", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--agy", default="agy")
    parser.add_argument("--audio-adapter", choices=["agy", "gemini-file-api"], default="agy")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        raise SystemExit(f"refusing non-empty output directory: {args.output}")

    challenge_sha = sha256(args.challenge)
    challenge = json.loads(args.challenge.read_text(encoding="utf-8"))
    prompt_path = ROOT / "references" / f"{args.judge}-judge-prompt-v1.md"
    prompt_sha = sha256(prompt_path)
    expected_prompt_sha = challenge[f"{args.judge}_prompt_sha256"]
    if prompt_sha != expected_prompt_sha:
        raise SystemExit("prompt hash drift")
    model = "claude-opus-4-6-thinking" if args.judge == "text" else (
        "gemini-3.7-flash" if args.audio_adapter == "gemini-file-api" else "gemini-3.7-flash-high"
    )
    if args.judge == "audio" and args.audio_adapter == "gemini-file-api":
        import importlib.metadata
        from google import genai
        from google.genai import types
        cli_version = f"google-genai {importlib.metadata.version('google-genai')}"
        gemini_client = genai.Client()
        gemini_config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=SEMANTIC_SCHEMA,
        )
    else:
        cli_version = subprocess.run([args.agy, "--version"], check=True, capture_output=True, text=True).stdout.strip()
        gemini_client = None
        gemini_config = None
    raw_dir = args.output / "raw"
    parsed_dir = args.output / "parsed"
    raw_dir.mkdir(parents=True, exist_ok=args.resume)
    parsed_dir.mkdir(parents=True, exist_ok=args.resume)
    errors: list[dict[str, str]] = []
    output_hashes: dict[str, dict[str, str]] = {}

    for item in challenge["candidates"]:
        candidate_id = item["candidate_id"]
        existing_parsed = parsed_dir / f"{candidate_id}.json"
        if args.resume and existing_parsed.is_file():
            existing = json.loads(existing_parsed.read_text(encoding="utf-8"))
            jsonschema.validate(existing, json.loads(RESPONSE_SCHEMA.read_text(encoding="utf-8")))
            output_hashes[candidate_id] = {
                "raw": existing["raw_response_sha256"],
                "parsed": sha256(existing_parsed),
            }
            continue
        if args.judge == "text":
            if not args.text_packets:
                raise SystemExit("--text-packets required")
            packet_path = args.text_packets / f"{candidate_id}.json"
            packet_sha = sha256(packet_path)
            if packet_sha != item["text_packet_sha256"]:
                raise SystemExit(f"packet hash drift: {candidate_id}")
            packet = packet_path.read_text(encoding="utf-8")
            bounded_input = f"Candidate packet JSON:\n{packet}"
        else:
            if not args.audio_packets:
                raise SystemExit("--audio-packets required")
            packet_path = args.audio_packets / f"{candidate_id}.json"
            packet_sha = sha256(packet_path)
            packet_obj = json.loads(packet_path.read_text(encoding="utf-8"))
            audio_path = pathlib.Path(packet_obj["audio_window"]["path"])
            if sha256(audio_path) != packet_obj["audio_window"]["sha256"]:
                raise SystemExit(f"audio hash drift: {candidate_id}")
            minimal = {
                key: packet_obj[key]
                for key in ("schema_version", "episode_id", "candidate_id", "category", "core_interval", "timebase")
            }
            minimal["audio_window"] = {
                "start_sample": packet_obj["audio_window"]["start_sample"],
                "end_sample": packet_obj["audio_window"]["end_sample"],
                "sha256": packet_obj["audio_window"]["sha256"],
            }
            bounded_input = (
                f"Minimal candidate metadata:\n{json.dumps(minimal, ensure_ascii=False, sort_keys=True)}\n"
                f"Native audio attachment (judge this audio directly): @{audio_path}"
            )
        full_prompt = prompt_path.read_text(encoding="utf-8") + "\n\n" + bounded_input
        if args.judge == "audio" and args.audio_adapter == "gemini-file-api":
            full_prompt += ("\n\nRequired semantic JSON shape (no extra fields):\n" +
                            json.dumps(SEMANTIC_SCHEMA, ensure_ascii=False, sort_keys=True))
        raw_path = raw_dir / f"{candidate_id}.json"
        if raw_path.exists():
            retry = 1
            while (raw_dir / f"{candidate_id}.retry-{retry:02}.json").exists():
                retry += 1
            raw_path = raw_dir / f"{candidate_id}.retry-{retry:02}.json"
        try:
            if args.judge == "audio" and args.audio_adapter == "gemini-file-api":
                assert gemini_client is not None
                uploaded = gemini_client.files.upload(file=audio_path)
                try:
                    deadline = time.time() + 120
                    while True:
                        uploaded = gemini_client.files.get(name=uploaded.name)
                        state = getattr(uploaded.state, "name", str(uploaded.state))
                        if state == "ACTIVE":
                            break
                        if state == "FAILED" or time.time() > deadline:
                            raise RuntimeError(f"Gemini file processing state={state}")
                        time.sleep(1)
                    response = gemini_client.models.generate_content(
                        model=model, contents=[uploaded, full_prompt], config=gemini_config
                    )
                    raw_text = response.text or ""
                finally:
                    gemini_client.files.delete(name=uploaded.name)
                raw_path.write_text(raw_text, encoding="utf-8")
                cleaned = raw_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                semantic = normalize_semantic(json.loads(cleaned), candidate_id)
            else:
                command = [
                    args.agy, "--model", model, "--print", full_prompt,
                    "--json-schema", json.dumps(SEMANTIC_SCHEMA, separators=(",", ":")),
                    "--output-format", "json", "--print-timeout", "5m",
                ]
                completed = subprocess.run(command, capture_output=True, text=True)
                raw_path.write_text(completed.stdout, encoding="utf-8")
                if completed.returncode != 0:
                    raise RuntimeError(completed.stderr.strip() or "agy failed")
                envelope = json.loads(completed.stdout)
                if envelope.get("status") != "SUCCESS":
                    raise RuntimeError(envelope.get("error") or f"agy status={envelope.get('status')}")
                semantic = normalize_semantic(envelope["structured_output"], candidate_id)
            parsed = {
                **semantic,
                "schema_version": "1.0",
                "judge_role": args.judge,
                "candidate_packet_sha256": packet_sha,
                "prompt_sha256": prompt_sha,
                "model_id": model,
                "cli_version": cli_version,
                "raw_response_sha256": sha256(raw_path),
            }
            jsonschema.validate(parsed, json.loads(RESPONSE_SCHEMA.read_text(encoding="utf-8")))
            parsed_path = parsed_dir / f"{candidate_id}.json"
            atomic_json(parsed_path, parsed)
            output_hashes[candidate_id] = {"raw": sha256(raw_path), "parsed": sha256(parsed_path)}
        except Exception as exc:  # noqa: BLE001 - report each isolated model failure
            errors.append({"candidate_id": candidate_id, "error": str(exc)})

    report = {
        "schema_version": "1.0",
        "status": "passed" if not errors and len(output_hashes) == len(challenge["candidates"]) else "failed",
        "judge_role": args.judge,
        "run": args.run,
        "fresh_process_per_candidate": True,
        "expected_candidates": len(challenge["candidates"]),
        "produced_candidates": len(output_hashes),
        "challenge_set_sha256": challenge_sha,
        "prompt_sha256": prompt_sha,
        "model_id": model,
        "adapter": "Antigravity CLI" if args.judge == "text" or args.audio_adapter == "agy" else "Google Gemini File API",
        "generation_config": ({"temperature": 0, "response_mime_type": "application/json",
                               "response_json_schema_sha256": sha256(RESPONSE_SCHEMA)}
                              if args.judge == "audio" and args.audio_adapter == "gemini-file-api" else None),
        "cli_version": cli_version,
        "output_hashes": output_hashes,
        "errors": errors,
        "filmora_consumed": False,
        "heldout_labels_consumed": False,
        "other_judge_consumed": False,
        "publish_authorized": False,
    }
    atomic_json(args.output / "run-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
