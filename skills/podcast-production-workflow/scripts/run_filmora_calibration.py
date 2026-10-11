#!/usr/bin/env python3
"""Stable local E2E entry for Filmora Golden Reference calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def run(command: list[str]) -> dict:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return {"argv": command, "exit_code": result.returncode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    for role, spec in (
        ("render_audio", config["audio_roles"]["render_audio"]),
        ("filmora_audio", config["gold_references"]["filmora_audio"]),
        ("auto_edl", config["auto_edl"]),
    ):
        path = Path(spec["path"])
        if not path.is_file() or sha256_file(path) != spec["sha256"]:
            raise SystemExit(f"{role} identity mismatch")
    root = Path(config["output_root"])
    root.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    alignment = root / "alignment.json"
    reference_edl = root / "reference-edl.json"
    delta = root / "edl-delta-report.json"
    feedback = root / "feedback-template.json"
    preview = root / "filmora-calibration-review.html"
    steps = []
    steps.append(run([sys.executable, str(scripts / "align_filmora_reference.py"), "--manifest", str(args.config), "--output", str(alignment)]))
    steps.append(run([sys.executable, str(scripts / "reconstruct_reference_edl.py"), "--alignment", str(alignment), "--episode-id", config["episode_id"], "--output", str(reference_edl)]))
    steps.append(run([sys.executable, str(scripts / "compare_edls.py"), "--auto-edl", config["auto_edl"]["path"], "--reference-edl", str(reference_edl), "--output", str(delta), "--feedback-template", str(feedback)]))
    steps.append(run([sys.executable, str(scripts / "render_calibration_review.py"), "--delta-report", str(delta), "--reference-edl", str(reference_edl), "--source-audio", config["audio_roles"]["render_audio"]["path"], "--filmora-audio", config["gold_references"]["filmora_audio"]["path"], "--output", str(preview)]))
    outputs = {name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for name, path in {
        "alignment": alignment, "reference_edl": reference_edl, "delta_report": delta, "feedback_template": feedback, "preview": preview,
    }.items()}
    summary = {"status": "succeeded", "episode_id": config["episode_id"], "config": {"path": str(args.config), "sha256": sha256_file(args.config)}, "outputs": outputs, "steps": steps, "publish_authorized": False}
    report = root / "calibration-smoke-report.json"
    atomic_json(report, summary)
    print(json.dumps({"status": "succeeded", "report": str(report), "report_sha256": sha256_file(report), "outputs": outputs}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
