#!/usr/bin/env python3
"""Append an idempotent Life-OS clipping event after note validation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\n\"']+)[\"']?\s*$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def list_value(frontmatter: str, key: str) -> list[str]:
    block = re.search(rf"^{re.escape(key)}:\s*\n((?:\s+-\s+.*\n?)*)", frontmatter, re.MULTILINE)
    if block:
        return [item.strip().strip("\"'") for item in re.findall(r"^\s+-\s+(.+)$", block.group(1), re.MULTILINE)]
    inline = scalar(frontmatter, key)
    if inline.startswith("[") and inline.endswith("]"):
        return [part.strip().strip("\"'") for part in inline[1:-1].split(",") if part.strip()]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("note", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    note = args.note.expanduser().resolve()
    if not note.is_file() or root not in note.parents:
        raise SystemExit(f"ERROR: note must exist beneath Life-OS root: {note}")

    text = note.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SystemExit("ERROR: note has no YAML frontmatter")
    fm = match.group(1)
    source_url = scalar(fm, "source_url") or scalar(fm, "source")
    if not source_url:
        raise SystemExit("ERROR: source_url/source missing")

    now = datetime.now(ZoneInfo("Europe/Brussels"))
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    relative = note.relative_to(root).as_posix()
    event_id = hashlib.sha256(f"{source_url}\n{relative}\n{content_hash}".encode()).hexdigest()[:20]
    event = {
        "event_id": event_id,
        "clipped_at": now.isoformat(),
        "source_url": source_url,
        "note_path": relative,
        "template": scalar(fm, "template"),
        "extraction_method": scalar(fm, "extraction_method"),
        "content_hash": content_hash,
        "tags": list_value(fm, "tags"),
    }

    ledger_dir = root / ".automation" / "clip-ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = ledger_dir / f"{now.date().isoformat()}.jsonl"
    with ledger.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        if any(json.loads(line).get("event_id") == event_id for line in handle if line.strip()):
            print(json.dumps({"status": "exists", "event_id": event_id, "ledger": str(ledger)}, ensure_ascii=False))
            return 0
        handle.seek(0, 2)
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
    print(json.dumps({"status": "appended", "event_id": event_id, "ledger": str(ledger)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
