#!/usr/bin/env python3
"""Run immutable, content-addressed Whisper raw transcription with atomic promotion."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile


EXTENSIONS = (".txt", ".srt", ".vtt", ".json")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RELEASE_APPROVAL_SCHEMA = ROOT / "references/release-audio-listen-approval.schema.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        pathlib.Path(temporary_name).unlink(missing_ok=True)
        raise


def atomic_json(path: pathlib.Path, value: object) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def tool_version(command: pathlib.Path) -> str:
    result = subprocess.run([str(command), "--version"], capture_output=True, text=True)
    text = result.stdout + result.stderr
    match = re.search(r"whisper\.cpp version:\s*([^\s]+)", text)
    return match.group(1) if match else text.strip().splitlines()[-1]


def validate_json(path: pathlib.Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments = data.get("transcription")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Whisper JSON has no transcription segments")
    previous = 0
    for index, segment in enumerate(segments):
        offsets = segment.get("offsets", {})
        start, end = int(offsets.get("from", -1)), int(offsets.get("to", -1))
        if start < previous or end < start:
            raise ValueError(f"non-monotonic segment {index}")
        previous = end
    result = data.get("result", {})
    return {"segment_count": len(segments), "last_offset_ms": previous,
            "detected_language": result.get("language")}


def cache_valid(report: pathlib.Path, run_key: str) -> bool:
    if not report.is_file():
        return False
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("run_key") != run_key:
            return False
        return all(pathlib.Path(item["path"]).is_file() and sha256(pathlib.Path(item["path"])) == item["sha256"]
                   for item in data["outputs"].values())
    except (KeyError, OSError, json.JSONDecodeError):
        return False


def release_approval(path: pathlib.Path | None, audio_sha256: str) -> tuple[dict, str]:
    import jsonschema
    if path is None or not path.is_file():
        raise SystemExit("S11a requires an H3b release-audio approval file")
    value = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(value, json.loads(RELEASE_APPROVAL_SCHEMA.read_text(encoding="utf-8")))
    if value["release_audio_sha256"] != audio_sha256:
        raise SystemExit("H3b approval does not bind the exact release audio SHA-256")
    timestamp = dt.datetime.fromisoformat(value["approved_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise SystemExit("H3b approval timestamp must include timezone")
    return value, canonical_hash(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--analysis-audio", type=pathlib.Path, required=True)
    parser.add_argument("--model", type=pathlib.Path, required=True)
    parser.add_argument("--output-base", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--whisper-cli", type=pathlib.Path, default=pathlib.Path("/opt/homebrew/bin/whisper-cli"))
    parser.add_argument("--stage", choices=("S02-whisper-raw", "S11a-postcut-whisper-raw"), default="S02-whisper-raw")
    parser.add_argument("--release-approval", type=pathlib.Path)
    args = parser.parse_args()
    for path, role in ((args.analysis_audio, "analysis audio"), (args.model, "model"), (args.whisper_cli, "whisper-cli")):
        if not path.is_file():
            raise SystemExit(f"{role} missing: {path}")
    version = tool_version(args.whisper_cli)
    audio_sha256 = sha256(args.analysis_audio)
    is_postcut = args.stage == "S11a-postcut-whisper-raw"
    approval_value = None; approval_sha = None
    if is_postcut:
        approval_value, approval_sha = release_approval(args.release_approval, audio_sha256)
    elif args.release_approval is not None:
        raise SystemExit("--release-approval is only valid for S11a-postcut-whisper-raw")
    audio_role = "release_audio" if is_postcut else "analysis_audio"
    identities = {f"{audio_role}_sha256": audio_sha256, "model_sha256": sha256(args.model)}
    invocation = {"language": args.language, "threads": args.threads, "outputs": list(EXTENSIONS),
                  "json_mode": "full", "whisper_cpp_version": version}
    run_identity = {"stage": args.stage, "version": "1.0", **identities, **invocation}
    if approval_sha is not None:
        run_identity["release_approval_sha256"] = approval_sha
    run_key = canonical_hash(run_identity)
    if cache_valid(args.report, run_key):
        report = json.loads(args.report.read_text(encoding="utf-8"))
        print(json.dumps({"status": "skipped_cached", "run_key": run_key, "report": str(args.report),
                          "report_sha256": sha256(args.report), "outputs": report["outputs"],
                          "publish_authorized": False}, ensure_ascii=False, indent=2))
        return
    final_paths = {extension[1:]: pathlib.Path(str(args.output_base) + extension) for extension in EXTENSIONS}
    existing = [str(path) for path in final_paths.values() if path.exists()]
    if existing:
        raise SystemExit(f"immutable raw transcript outputs exist without verified matching report: {existing}")
    args.output_base.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = pathlib.Path(tempfile.mkdtemp(prefix=f".{args.output_base.name}.{run_key[:12]}.", dir=args.output_base.parent))
    temporary_base = temporary_dir / args.output_base.name
    command = [str(args.whisper_cli), "-m", str(args.model), "-f", str(args.analysis_audio),
               "-of", str(temporary_base), "-otxt", "-osrt", "-ovtt", "-ojf",
               "-l", args.language, "-t", str(args.threads)]
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    result = subprocess.run(command, capture_output=True, text=True)
    ended = dt.datetime.now(dt.timezone.utc).isoformat()
    atomic_text(args.log, result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(f"whisper-cli failed with exit {result.returncode}; log={args.log}")
    temporary_paths = {extension[1:]: pathlib.Path(str(temporary_base) + extension) for extension in EXTENSIONS}
    if any(not path.is_file() or path.stat().st_size == 0 for path in temporary_paths.values()):
        raise SystemExit(f"Whisper output missing/empty; log={args.log}")
    validation = validate_json(temporary_paths["json"])
    if not temporary_paths["txt"].read_text(encoding="utf-8").strip():
        raise SystemExit("Whisper TXT is empty")
    for key, temporary in temporary_paths.items():
        os.replace(temporary, final_paths[key])
    temporary_dir.rmdir()
    output_role = "immutable-postcut-raw-whisper" if is_postcut else "immutable-raw-whisper"
    outputs = {key: {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
                     "role": output_role} for key, path in final_paths.items()}
    inputs = {audio_role: {"path": str(args.analysis_audio), "sha256": audio_sha256},
              "model": {"path": str(args.model), "sha256": identities["model_sha256"]}}
    if is_postcut:
        inputs["release_audio_approval"] = {"path": str(args.release_approval), "canonical_sha256": approval_sha,
                                             "approved_by": approval_value["approved_by"], "approved_at": approval_value["approved_at"]}
    report = {"schema_version": "1.0", "episode_id": args.episode_id, "stage": args.stage,
              "status": "succeeded", "run_key": run_key, "inputs": inputs, "tool": {"path": str(args.whisper_cli), "version": version},
              "invocation": invocation, "argv": command, "started_at": started, "ended_at": ended,
              "exit_code": result.returncode, "log": {"path": str(args.log), "sha256": sha256(args.log)},
              "validation": validation, "outputs": outputs, "external_judge_dispatch_authorized": False,
              "publish_authorized": False}
    atomic_json(args.report, report)
    print(json.dumps({"status": "succeeded", "run_key": run_key, "report": str(args.report),
                      "report_sha256": sha256(args.report), "validation": validation, "outputs": outputs,
                      "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
