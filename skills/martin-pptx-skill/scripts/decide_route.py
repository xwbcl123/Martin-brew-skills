#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def truthy(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y", "available"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--target-output", required=True)
    parser.add_argument("--editable-pptx-required", default="false")
    parser.add_argument("--has-visual-motherboard", default="false")
    parser.add_argument("--presentations-runtime", default="unavailable")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    target = {x.strip() for x in args.target_output.split(",")}
    editable = truthy(args.editable_pptx_required) or args.scenario == "formal-company-report"
    has_motherboard = truthy(args.has_visual_motherboard)
    presentations = args.presentations_runtime == "available"
    if "pptx" in target and editable:
        main_route = "Option 5"
        backup = "Option 4 selected as independent backup" if presentations else "Option 4 skipped: runtime unavailable"
        gates = "BG Gate, Render Gate, Editability Gate, Text Fidelity Gate"
        stop = "editable PPTX + render/QC artifacts"
    elif "html" in target or "pdf" in target:
        main_route = "Stage 3 HTML/PDF/visual delivery"
        backup = "Option 4 optional editorial route" if presentations else "No backup route required"
        gates = "Outline Gate, Design Gate, Motherboard/Render Gate"
        stop = "approved HTML/PDF/graphic output"
    else:
        main_route = "Option 1 direct Python PPTX"
        backup = "Option 5 if visual motherboard becomes available" if has_motherboard else "none"
        gates = "Outline Gate, Design Gate, Render Gate"
        stop = "target artifact plus handover"

    lines = [
        "# Route Decision",
        "",
        f"- Scenario: `{args.scenario}`",
        f"- Target output: `{args.target_output}`",
        f"- Editable PPTX required: `{editable}`",
        f"- Visual motherboard available: `{has_motherboard}`",
        f"- Main route: **{main_route}**",
        f"- Backup route: {backup}",
        f"- Required gates: {gates}",
        f"- Stop condition: {stop}",
        "",
        "## Rationale",
        "",
        "Formal editable PPTX work uses Option 5 by default because it preserves editable title/body/evidence text while allowing approved header/footer/background image masters.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"main_route={main_route}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
