#!/usr/bin/env python3
"""Freeze bounded Daily Knowledge Brief inputs into deterministic JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Europe/Brussels")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)


def last_success(root: Path) -> datetime:
    manifests = sorted((root / ".automation" / "daily-knowledge-brief").glob("*/*/*_run.json"))
    for path in reversed(manifests):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("status") == "complete" and data.get("window_end"):
                return parse_time(data["window_end"])
        except (OSError, ValueError, TypeError):
            continue
    now = datetime.now(TZ)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def active_projects(root: Path) -> list[dict[str, str]]:
    projects: list[dict[str, str]] = []
    for meta in root.glob("[0-9][0-9]-[0-9][0-9]_*/*/_meta.md"):
        text = meta.read_text(encoding="utf-8", errors="replace")
        if "kind: \"project\"" not in text and "kind: project" not in text:
            continue
        if "status: \"active\"" not in text and "status: active" not in text:
            continue
        readme = meta.parent / "README.md"
        projects.append({
            "path": meta.parent.relative_to(root).as_posix(),
            "meta": text[:4000],
            "readme": readme.read_text(encoding="utf-8", errors="replace")[:8000] if readme.exists() else "",
        })
        if len(projects) >= 20:
            break
    return projects


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-at")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not (root / "AGENTS.md").is_file() or not (root / "00-09_System-Meta").is_dir():
        raise SystemExit(f"ERROR: invalid Life-OS root: {root}")

    run_at = parse_time(args.run_at) if args.run_at else datetime.now(TZ)
    start = last_success(root)
    events: dict[str, dict] = {}
    for ledger in sorted((root / ".automation" / "clip-ledger").glob("*.jsonl")):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            event_time = parse_time(event["clipped_at"])
            note = (root / event["note_path"]).resolve()
            if start < event_time <= run_at and note.is_file() and root in note.parents:
                events[event["event_id"]] = event

    payload = {
        "window_start": start.isoformat(),
        "window_end": run_at.isoformat(),
        "events": sorted(events.values(), key=lambda item: item["clipped_at"]),
        "active_projects": active_projects(root),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "ok", "events": len(events), "projects": len(payload["active_projects"]), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
