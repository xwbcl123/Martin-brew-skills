#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", required=True, type=Path)
    parser.add_argument("--mode", default="formal-option5")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--review-note", default="")
    args = parser.parse_args()

    failures = []
    warnings = []
    if not args.background.exists():
        failures.append("background file missing")
        width = height = None
    else:
        img = Image.open(args.background)
        width, height = img.size
        ratio = width / height if height else 0
        if not 1.72 <= ratio <= 1.82:
            failures.append(f"background is not close to 16:9: {width}x{height}")
        if width < 1200 or height < 650:
            warnings.append(f"background resolution is low for PPTX: {width}x{height}")

    result = {
        "status": "fail" if failures else "warn" if warnings else "pass",
        "mode": args.mode,
        "background": str(args.background),
        "dimensions": {"width": width, "height": height},
        "kept_elements": [
            "header chrome",
            "footer chrome",
            "logo/footer area",
            "subtle background texture",
            "non-semantic decorative shapes",
        ],
        "removed_elements_expected": [
            "slide title and subtitle",
            "body text",
            "body icons",
            "charts",
            "cards",
            "labels",
            "stale evidence text",
        ],
        "warnings": warnings,
        "failures": failures,
        "human_review_note": args.review_note or "Automated hygiene check only; reviewer must confirm no stale semantic content remains.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "warnings": len(warnings), "failures": len(failures)}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
