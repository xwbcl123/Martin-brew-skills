#!/usr/bin/env python3
"""One-command generic S00-S02 baseline for a production episode."""

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
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def execute(script: str, arguments: list[str]) -> dict:
    result = subprocess.run([sys.executable, str(HERE / script), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"{script} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8")); p = config["paths"]
    execute("bootstrap_audio_roles.py", ["--intake", p["intake"], "--manifest", p["manifest"],
            "--render", p["render_audio"], "--analysis", p["analysis_audio"], "--report", p["s01_report"]])
    # Per-episode values win; anything omitted falls back to run_whisper_raw.py (CLI > env > personal config > neutral default).
    whisper_arguments = ["--episode-id", config["episode_id"], "--analysis-audio", p["analysis_audio"],
                         "--output-base", p["raw_output_base"],
                         "--report", p["s02_report"], "--log", p["s02_log"], "--threads", str(config.get("threads", 8))]
    if p.get("whisper_model"):
        whisper_arguments.extend(["--model", p["whisper_model"]])
    if config.get("language"):
        whisper_arguments.extend(["--language", config["language"]])
    if p.get("whisper_cli"):
        whisper_arguments.extend(["--whisper-cli", p["whisper_cli"]])
    execute("run_whisper_raw.py", whisper_arguments)
    s01 = json.loads(pathlib.Path(p["s01_report"]).read_text()); s02 = json.loads(pathlib.Path(p["s02_report"]).read_text())
    outputs = {"manifest": {"path": p["manifest"], "sha256": sha256(pathlib.Path(p["manifest"]))},
               "s01_report": {"path": p["s01_report"], "sha256": sha256(pathlib.Path(p["s01_report"]))},
               "s02_report": {"path": p["s02_report"], "sha256": sha256(pathlib.Path(p["s02_report"]))},
               "render_audio": {"path": p["render_audio"], "sha256": sha256(pathlib.Path(p["render_audio"]))},
               "analysis_audio": {"path": p["analysis_audio"], "sha256": sha256(pathlib.Path(p["analysis_audio"]))}}
    for name, item in s02["outputs"].items():
        outputs[f"raw_{name}"] = {"path": item["path"], "sha256": item["sha256"]}
    report = {"schema_version": "1.0", "episode_id": config["episode_id"], "stage": "S00-S02-production-baseline",
              "status": "succeeded", "config_path": str(args.config), "config_sha256": sha256(args.config),
              "stage_run_keys": {"S00_S01": s01["run_key"], "S02": s02["run_key"]},
              "outputs": outputs, "external_judge_dispatch_authorized": False, "publish_authorized": False}
    baseline_report = pathlib.Path(p["baseline_report"]); atomic_json(baseline_report, report)
    print(json.dumps({**report, "report_path": str(baseline_report), "report_sha256": sha256(baseline_report)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
