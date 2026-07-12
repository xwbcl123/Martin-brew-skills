#!/usr/bin/env python3
"""Initialize or update per-channel Daily Brief delivery state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--path", required=True, type=Path)
    init.add_argument("--window-start", required=True)
    init.add_argument("--window-end", required=True)
    init.add_argument("--note", required=True)
    mark = sub.add_parser("mark")
    mark.add_argument("--path", required=True, type=Path)
    mark.add_argument("--channel", required=True)
    mark.add_argument("--target", required=True)
    mark.add_argument("--status", required=True, choices=["pending", "sent", "failed", "skipped", "skipped_dry_run"])
    mark.add_argument("--message-id", default="")
    mark.add_argument("--error", default="")
    args = parser.parse_args()

    if args.command == "init":
        data = {"status": "local_validated", "window_start": args.window_start, "window_end": args.window_end, "note_path": args.note, "deliveries": {}}
    else:
        data = json.loads(args.path.read_text(encoding="utf-8"))
        key = f"{args.channel}:{args.target}"
        data.setdefault("deliveries", {})[key] = {"channel": args.channel, "target": args.target, "status": args.status, "message_id": args.message_id, "error": args.error}
        states = [item["status"] for item in data["deliveries"].values()]
        data["status"] = "complete" if states and all(state in {"sent", "skipped", "skipped_dry_run"} for state in states) else "delivery_pending"
    args.path.parent.mkdir(parents=True, exist_ok=True)
    temp = args.path.with_suffix(args.path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(args.path)
    print(json.dumps({"status": data["status"], "path": str(args.path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
