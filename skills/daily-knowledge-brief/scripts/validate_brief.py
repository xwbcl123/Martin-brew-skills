#!/usr/bin/env python3
"""Validate a persisted Life-OS Daily Knowledge Brief."""

from __future__ import annotations

import re
import sys
from pathlib import Path


FIELDS = {"title", "date", "created", "type", "status", "window_start", "window_end", "source_count", "tags"}
HEADINGS = {"## 今日概览", "## 主题聚类", "## 关联项目", "## 来源笔记", "## 待跟进", "## 运行信息"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_brief.py /absolute/path/to/brief.md", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).expanduser()
    if not path.is_file() or path.stat().st_size < 300:
        print(f"ERROR: missing or too-short brief: {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        print("ERROR: missing YAML frontmatter")
        return 1
    present = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_-]*):", match.group(1), re.MULTILINE))
    missing_headings = sorted(heading for heading in HEADINGS if heading not in text)
    errors = []
    if FIELDS - present:
        errors.append("missing frontmatter: " + ", ".join(sorted(FIELDS - present)))
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))
    if not re.search(r"^# Daily Knowledge Brief — \d{4}-\d{2}-\d{2}$", text, re.MULTILINE):
        errors.append("invalid H1")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
