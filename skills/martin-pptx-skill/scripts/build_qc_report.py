#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-folder", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    out_dir = args.run_folder / "output" / "full_deck_option5"
    bg = read_json(out_dir / "bg_gate_report.json")
    text = read_json(out_dir / "text_fidelity_gate.json")
    extraction = read_json(out_dir / "text_extraction.json")
    failures = []
    warnings = []
    if bg and bg.get("status") == "fail":
        failures.append("BG Gate failed")
    elif bg and bg.get("status") == "warn":
        warnings.append("BG Gate warning")
    if text.get("summary", {}).get("fail", 0):
        failures.append("Text Fidelity Gate has failures")
    if extraction.get("summary", {}).get("slide_count") is None:
        failures.append("Text extraction missing")
    if extraction.get("summary", {}).get("min_font_size") and extraction["summary"]["min_font_size"] < 9:
        warnings.append("Some extracted font sizes are below 9pt")

    status = "fail" if failures else "warn" if warnings else "pass"
    lines = [
        "# QC Report",
        "",
        f"- Run folder: `{args.run_folder}`",
        f"- Status: **{status}**",
        "",
        "## Gate Summary",
        "",
        f"- BG Gate: `{bg.get('status', 'missing')}`",
        f"- Text Fidelity: `{text.get('summary', {})}`",
        f"- Text extraction: `{extraction.get('summary', {})}`",
        "",
        "## Failures",
        "",
        *(f"- {x}" for x in failures),
        "" if failures else "- None",
        "",
        "## Warnings",
        "",
        *(f"- {x}" for x in warnings),
        "" if warnings else "- None",
        "",
        "## Recommendation",
        "",
        "Accepted for benchmark learning if there are no failures. For production delivery, visual polish and human review remain required.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"status={status}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
