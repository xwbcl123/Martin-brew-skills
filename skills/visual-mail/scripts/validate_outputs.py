#!/usr/bin/env python3
"""
Validate visual-mail output files for cleanliness and required elements.

Usage:
  python validate_outputs.py <email_md> [<html_file>]

Checks:
  - Email contains BRIEF_LINK_PLACEHOLDER or a real https:// link
  - Email contains VIZ_LINK_PLACEHOLDER or a real https:// link
  - Email contains screenshot embed ![[...]]
  - No banned strings in email or HTML visible content

Exit codes:
  0  all checks passed
  1  one or more checks failed
"""

import sys
import re
from pathlib import Path


BANNED = [
    r"\bAgent\b", r"\bworker\b", r"AI generated", r"Main Agent",
    r"\bprompt\b", r"task\.md", r"handoff\.md", r"请读取", r"\bshore\b"
]

REQUIRED_EMAIL = [
    (r"BRIEF_LINK_PLACEHOLDER|https?://\S+", "report link (placeholder or real URL)"),
    (r"VIZ_LINK_PLACEHOLDER|https?://\S+", "visual brief link (placeholder or real URL)"),
    (r"!\[\[.*\.png\]\]", "screenshot embed ![[...]]"),
]


def check_file(path: str, checks, label: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    failures = []
    for pattern, description in checks:
        if not re.search(pattern, text):
            failures.append(f"[{label}] Missing: {description}")
    for banned in BANNED:
        matches = [(m.start(), m.group()) for m in re.finditer(banned, text)]
        if matches:
            for pos, match in matches[:3]:
                line_no = text[:pos].count("\n") + 1
                failures.append(f"[{label}] Banned string '{match}' at line {line_no}")
    return failures


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_outputs.py <email_md> [<html_file>]", file=sys.stderr)
        sys.exit(1)

    failures = []
    email_path = sys.argv[1]
    if Path(email_path).exists():
        failures += check_file(email_path, REQUIRED_EMAIL, "email")
    else:
        failures.append(f"Email file not found: {email_path}")

    if len(sys.argv) >= 3:
        html_path = sys.argv[2]
        if Path(html_path).exists():
            failures += check_file(html_path, [], "html")
        else:
            failures.append(f"HTML file not found: {html_path}")

    if failures:
        print("VALIDATION FAILED:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
