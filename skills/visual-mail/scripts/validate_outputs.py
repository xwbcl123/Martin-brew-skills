#!/usr/bin/env python3
"""
Validate visual-mail output files for cleanliness and required elements.

Usage:
  python validate_outputs.py <email_md> [<html_file>]

Checks:
  - Email contains BRIEF_LINK_PLACEHOLDER or a real https:// link
  - Email contains VIZ_LINK_PLACEHOLDER or a real https:// link
  - Email contains screenshot embed ![[...]]
  - No private execution paths; subject-matter terms remain valid
  - --final rejects unresolved delivery placeholders

Exit codes:
  0  all checks passed
  1  one or more checks failed
"""

import argparse
import sys
import re
from pathlib import Path


BANNED = [
    r"/(?:Users|home)/[^\s<]+", r"tasks/sessions/[^\s<]+", r"tasks/shore/[^\s<]+"
]


REQUIRED_EMAIL = [
    (r"BRIEF_LINK_PLACEHOLDER|https?://\S+", "report link (placeholder or real URL)"),
    (r"VIZ_LINK_PLACEHOLDER|https?://\S+", "visual brief link (placeholder or real URL)"),
    (r"!\[\[.*\.png\]\]", "screenshot embed ![[...]]"),
]


def check_file(path: str, checks, label: str, *, final: bool = False) -> list[str]:
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
    if final and re.search(r"(?:BRIEF_LINK_PLACEHOLDER|VIZ_LINK_PLACEHOLDER|<AUDIENCE>|<REPORT_TITLE>)", text):
        failures.append(f"[{label}] Unresolved delivery placeholder")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email_md")
    parser.add_argument("html_file", nargs="?")
    parser.add_argument("--final", action="store_true", help="Reject unresolved delivery placeholders")
    args = parser.parse_args()

    failures = []
    email_path = args.email_md
    if Path(email_path).exists():
        failures += check_file(email_path, REQUIRED_EMAIL, "email", final=args.final)
    else:
        failures.append(f"Email file not found: {email_path}")

    if args.html_file:
        html_path = args.html_file
        if Path(html_path).exists():
            failures += check_file(html_path, [], "html", final=args.final)
        else:
            failures.append(f"HTML file not found: {html_path}")

    if failures:
        print("VALIDATION FAILED:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("Structural checks passed; inspect content, brand, links and actual delivery separately.")
        sys.exit(0)


if __name__ == "__main__":
    main()
