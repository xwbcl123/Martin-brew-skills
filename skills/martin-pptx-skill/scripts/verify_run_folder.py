#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_REQUIRED = [
    "input/brief.md",
    "input/source_index.md",
    "output/design.md",
    "output/deck-outline.md",
    "notes.md",
    "verdict.md",
    "handover.md",
]

FORMAL_REQUIRED = [
    "output/route_decision.md",
    "output/full_deck_option5/deck.pptx",
    "output/full_deck_option5/bg_gate_report.json",
    "output/full_deck_option5/text_extraction.json",
    "output/full_deck_option5/text_fidelity_gate.md",
    "output/full_deck_option5/qc_report.md",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-folder", required=True, type=Path)
    parser.add_argument("--formal-pptx", default="false")
    args = parser.parse_args()
    required = list(BASE_REQUIRED)
    if args.formal_pptx.lower() in {"1", "true", "yes", "y"}:
        required.extend(FORMAL_REQUIRED)
    missing = [p for p in required if not (args.run_folder / p).exists()]
    if missing:
        print("Missing required run artifacts:")
        for path in missing:
            print(f"- {path}")
        return 1
    print(f"Run folder OK: {args.run_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
