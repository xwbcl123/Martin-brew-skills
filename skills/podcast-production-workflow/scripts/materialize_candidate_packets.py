#!/usr/bin/env python3
"""Materialize embedded candidates as canonical, independently hashable packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/candidate-packet.schema.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_bytes(path: pathlib.Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(value)
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    args = parser.parse_args()
    bundle = json.loads(args.candidates.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    entries = []
    for candidate in bundle["candidates"]:
        jsonschema.validate(candidate, schema)
        value = canonical_bytes(candidate)
        path = args.output_dir / f"{candidate['candidate_id']}.json"
        if not path.exists() or path.read_bytes() != value:
            atomic_bytes(path, value)
        entries.append({"candidate_id": candidate["candidate_id"], "path": str(path), "sha256": sha256_bytes(value)})
    index = {
        "schema_version": "1.0", "stage": "S03-candidate-packets", "episode_id": bundle["episode_id"],
        "candidate_bundle_path": str(args.candidates), "candidate_bundle_sha256": sha256(args.candidates),
        "packet_count": len(entries), "packets": entries, "judge_dispatch_authorized": False,
        "publish_authorized": False,
    }
    atomic_bytes(args.index, canonical_bytes(index))
    print(json.dumps({"status": "candidate_packets_ready_local_only", "packet_count": len(entries),
                      "index": str(args.index), "index_sha256": sha256(args.index)}, indent=2))


if __name__ == "__main__":
    main()
