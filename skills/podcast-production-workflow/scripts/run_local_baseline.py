#!/usr/bin/env python3
"""Stable local-only entrypoint for S01-S03; never dispatches Judges or publishes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent


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


def run(script: str, arguments: list[str]) -> dict:
    result = subprocess.run([sys.executable, str(HERE / script), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"{script} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    p = config["paths"]
    run("prepare_audio_roles.py", ["--manifest", p["manifest"], "--report", p["s01_report"]])
    run("align_filmora_reference.py", ["--manifest", p["manifest"], "--output", p["alignment"]])
    run("build_heldout_label_template.py", ["--alignment", p["alignment"], "--output", p["heldout_labels"]])
    run("generate_edit_candidates.py", [
        "--manifest", p["manifest"], "--policy", p["policy"], "--standard-asr", p["standard_asr"],
        "--filler-asr", p["filler_asr"], "--silence-log", p["silence_log"], "--output", p["candidates"],
    ])
    outputs = {name: {"path": p[name], "sha256": sha256(pathlib.Path(p[name]))}
               for name in ("s01_report", "alignment", "heldout_labels", "candidates")}
    stage_documents = {name: json.loads(pathlib.Path(p[name]).read_text(encoding="utf-8"))
                       for name in ("s01_report", "alignment", "heldout_labels", "candidates")}
    normalized_receipts = {
        "S01": {"run_key": stage_documents["s01_report"]["run_key"], "artifact_sha256": outputs["s01_report"]["sha256"]},
        "S02": {"run_key": stage_documents["alignment"]["run_key"], "artifact_sha256": outputs["alignment"]["sha256"]},
        "S02_labels": {"run_key": stage_documents["heldout_labels"]["run_key"], "artifact_sha256": outputs["heldout_labels"]["sha256"]},
        "S03": {"run_key": stage_documents["candidates"]["run_key"], "artifact_sha256": outputs["candidates"]["sha256"]},
    }
    report = {
        "schema_version": "1.0",
        "stage": "S01-S03-local-baseline",
        "status": "local_baseline_ready_external_judges_blocked",
        "episode_id": config["episode_id"],
        "config_path": str(args.config),
        "config_sha256": sha256(args.config),
        "substage_receipts": normalized_receipts,
        "outputs": outputs,
        "external_judge_dispatch_authorized": False,
        "publish_authorized": False,
    }
    atomic_json(pathlib.Path(p["baseline_report"]), report)
    print(json.dumps({**report, "report_path": p["baseline_report"],
                      "report_sha256": sha256(pathlib.Path(p["baseline_report"]))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
