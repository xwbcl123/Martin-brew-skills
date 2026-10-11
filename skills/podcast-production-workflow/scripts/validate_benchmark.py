#!/usr/bin/env python3
"""Validate benchmark schema, live artifact hashes, role separation, and gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/benchmark.schema.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(path: Path) -> dict[str, Any]:
    import jsonschema

    declaration = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = [
        f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
        for error in sorted(jsonschema.Draft202012Validator(schema).iter_errors(declaration), key=lambda item: list(item.absolute_path))
    ]
    artifacts: list[dict[str, Any]] = []

    def inspect(role: str, value: dict[str, Any]) -> bool:
        if value.get("status") == "pending":
            artifacts.append({"role": role, "path": value.get("path"), "status": "pending"})
            return False
        target = Path(value["path"])
        if not target.is_file():
            artifacts.append({"role": role, "path": str(target), "status": "missing"})
            return False
        actual = sha256_file(target)
        ok = actual == value["sha256"]
        artifacts.append({"role": role, "path": str(target), "expected_sha256": value["sha256"], "actual_sha256": actual, "bytes": target.stat().st_size, "status": "verified" if ok else "hash_mismatch"})
        return ok

    checks = []
    checks.append(inspect("source", declaration["source"]))
    checks.append(inspect("render_audio", declaration["audio_roles"]["render_audio"]))
    checks.append(inspect("analysis_audio", declaration["audio_roles"]["analysis_audio"]))
    for name, value in declaration["gold_references"].items():
        checks.append(inspect(f"gold:{name}", value))

    render_path = declaration["audio_roles"]["render_audio"].get("path")
    analysis_path = declaration["audio_roles"]["analysis_audio"].get("path")
    role_separation = bool(render_path and analysis_path and Path(render_path) != Path(analysis_path))
    gates = declaration["human_gates"]
    h0 = gates["data_scope_authorization"] == "approved" and gates["minor_consent"] in {"cleared", "not_applicable"}
    h1 = gates["benchmark_protocol"] == "approved"
    artifact_ok = not errors and all(checks) and role_separation
    report = {
        "schema_version": "1.0",
        "episode_id": declaration["episode_id"],
        "schema_valid": not errors,
        "schema_errors": errors,
        "artifacts": artifacts,
        "role_separation_valid": role_separation,
        "deterministic_baseline_ready": artifact_ok,
        "external_judge_dispatch_authorized": artifact_ok and h0 and h1,
        "human_gates": gates,
        "publish_authorized": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.manifest)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["external_judge_dispatch_authorized"] else 1


if __name__ == "__main__":
    sys.exit(main())
