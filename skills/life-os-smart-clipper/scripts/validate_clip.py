#!/usr/bin/env python3
"""Validate the durable structure of a Life-OS smart clipping."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "title",
    "source",
    "source_url",
    "created",
    "clipped",
    "jd_id",
    "type",
    "template",
    "tags",
    "status",
    "extraction_method",
}
REQUIRED_HEADINGS = {"## 关联笔记", "## 原始正文", "## 网页高亮"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_clip.py /absolute/path/to/note.md", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).expanduser()
    if not path.is_file():
        print(f"ERROR: note not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        print("ERROR: missing YAML frontmatter")
        return 1

    fields = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_-]*):", match.group(1), flags=re.MULTILINE))
    missing_fields = sorted(REQUIRED_FIELDS - fields)
    missing_headings = sorted(h for h in REQUIRED_HEADINGS if h not in text)

    errors: list[str] = []
    if missing_fields:
        errors.append("missing frontmatter: " + ", ".join(missing_fields))
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))
    if not re.search(r"^#\s+\S", text, flags=re.MULTILINE):
        errors.append("missing H1 title")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
