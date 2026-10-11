#!/usr/bin/env python3
"""Build a deterministic artifact identity lock for incremental invalidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dag", type=pathlib.Path, required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--artifact", action="append", default=[], metavar="NODE=PATH")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    dag = json.loads(args.dag.read_text(encoding="utf-8"))
    nodes = {node["id"] for node in dag.get("nodes", [])}
    if dag.get("schema_version") != "1.0" or not nodes:
        raise SystemExit("invalid dependency DAG")
    if not args.artifact:
        raise SystemExit("at least one --artifact NODE=PATH is required")
    records: dict[str, dict] = {}
    for binding in args.artifact:
        if "=" not in binding:
            raise SystemExit(f"invalid artifact binding: {binding}")
        node, raw_path = binding.split("=", 1)
        if node not in nodes:
            raise SystemExit(f"unknown DAG node: {node}")
        if node in records:
            raise SystemExit(f"duplicate DAG node: {node}")
        path = pathlib.Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"artifact is not a file: {path}")
        records[node] = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
    value = {"schema_version": "1.0", "episode_id": args.episode_id,
             "dag_id": dag.get("dag_id"), "dag_sha256": sha256(args.dag),
             "artifacts": {node: record["sha256"] for node, record in records.items()}, "records": records}
    atomic_json(args.output, value)
    print(json.dumps({"status": "locked", "episode_id": args.episode_id, "artifact_count": len(records),
                      "output": str(args.output), "sha256": sha256(args.output), "publish_authorized": False},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
