#!/usr/bin/env python3
"""Plan narrow artifact/approval invalidation over a versioned dependency DAG."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import tempfile


HEX = set("0123456789abcdef")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True); raise


def validate_hash(value: str) -> bool:
    return len(value) == 64 and set(value) <= HEX


def load_lock(path: pathlib.Path, nodes: set[str]) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "1.0" or not isinstance(value.get("artifacts"), dict): raise SystemExit(f"invalid lock: {path}")
    unknown = set(value["artifacts"]) - nodes
    if unknown: raise SystemExit(f"lock has unknown DAG nodes: {sorted(unknown)}")
    for node, digest in value["artifacts"].items():
        if not isinstance(digest, str) or not validate_hash(digest): raise SystemExit(f"invalid SHA-256 for {node}")
    return value["artifacts"]


def validate_dag(value: dict) -> tuple[dict[str, dict], dict[str, list[str]], list[str]]:
    if value.get("schema_version") != "1.0" or not isinstance(value.get("nodes"), list): raise SystemExit("invalid DAG")
    nodes = {item["id"]: item for item in value["nodes"]}
    if len(nodes) != len(value["nodes"]): raise SystemExit("duplicate DAG node")
    reverse = {node: [] for node in nodes}; indegree = {node: 0 for node in nodes}
    for node, item in nodes.items():
        for parent in item.get("depends_on", []):
            if parent not in nodes: raise SystemExit(f"unknown dependency {parent} for {node}")
            reverse[parent].append(node); indegree[node] += 1
    queue = collections.deque(sorted(node for node, degree in indegree.items() if degree == 0)); order = []
    while queue:
        node = queue.popleft(); order.append(node)
        for child in sorted(reverse[node]):
            indegree[child] -= 1
            if indegree[child] == 0: queue.append(child)
    if len(order) != len(nodes): raise SystemExit("dependency graph contains a cycle")
    return nodes, reverse, order


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--dag", type=pathlib.Path, required=True)
    parser.add_argument("--previous-lock", type=pathlib.Path, required=True); parser.add_argument("--current-lock", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True); args = parser.parse_args()
    dag = json.loads(args.dag.read_text(encoding="utf-8")); nodes, reverse, order = validate_dag(dag); node_ids = set(nodes)
    previous, current = load_lock(args.previous_lock, node_ids), load_lock(args.current_lock, node_ids)
    changed = sorted(node for node in set(previous) | set(current) if previous.get(node) != current.get(node))
    reasons: dict[str, list[str]] = {node: [node] for node in changed}; queue = collections.deque(changed)
    while queue:
        parent = queue.popleft()
        for child in reverse[parent]:
            inherited = reasons[parent]
            if child not in reasons:
                reasons[child] = inherited + [child]; queue.append(child)
            elif len(inherited) + 1 < len(reasons[child]): reasons[child] = inherited + [child]
    impacted = [node for node in order if node in reasons]
    unchanged_materialized = [node for node in order if node in current and previous.get(node) == current[node]]
    reusable = [node for node in unchanged_materialized if node not in reasons]
    invalidated_approvals = [node for node in impacted if nodes[node]["kind"] == "approval"]
    recompute = [node for node in impacted if nodes[node]["kind"] in {"artifact", "external_state"}]
    report = {"schema_version": "1.0", "dag_id": dag.get("dag_id"), "dag_sha256": sha256(args.dag),
              "previous_lock_sha256": sha256(args.previous_lock), "current_lock_sha256": sha256(args.current_lock),
              "changed_roots": changed, "impacted_nodes": impacted, "must_recompute_or_reconcile": recompute,
              "must_reapprove": invalidated_approvals, "reusable_nodes": reusable,
              "impact_paths": {node: reasons[node] for node in impacted},
              "global_invalidation": False, "publish_authorized": False}
    atomic_json(args.output, report)
    print(json.dumps({"status": "planned", "changed_roots": changed, "must_recompute_or_reconcile": recompute,
                      "must_reapprove": invalidated_approvals, "reusable_nodes": reusable,
                      "output": str(args.output), "sha256": sha256(args.output), "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
