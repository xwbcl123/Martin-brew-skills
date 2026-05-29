#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from deck_utils import SlideSpec, compact_terms, parse_deck_outline


DEFAULT_AVOID = [
    "crude wireframe",
    "plain boxes and labels",
    "generic cyberpunk imagery",
    "hacker hoodie imagery",
    "generic padlocks",
    "national flags as the main visual metaphor",
    "decorative gradient blobs",
    "tiny unreadable text",
    "browser chrome",
    "mockup frame",
    "invented legal claims",
    "Huawei logo",
    "any brand logo unless explicitly supplied as an asset",
    "wrong year such as 2024",
]


def _read_design_summary(path: Path, limit: int = 4500) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[design.md truncated for prompt pack; use full file as SSOT if conflicts arise.]"


def _sample_numbers(slides: list[SlideSpec], raw: str | None) -> set[int]:
    if raw:
        return {int(x.strip()) for x in raw.split(",") if x.strip()}
    if not slides:
        return set()
    candidates = {slides[0].number}
    midpoint = slides[len(slides) // 2].number
    candidates.add(midpoint)
    candidates.add(slides[-1].number)
    return candidates


def _prompt_for_slide(slide: SlideSpec, design_summary: str, deck_title: str, sample: bool) -> str:
    bullets = "\n".join(f"- {item}" for item in slide.bullets[:6]) or "- No supporting bullets provided; use the key message and visual intent."
    keywords = ", ".join(compact_terms(" ".join([slide.title, slide.key_message, slide.visual, " ".join(slide.bullets)]), 12))
    sample_line = "This is a sample-generation slide; maximize design quality for review." if sample else "This is part of the full motherboard sequence."
    avoid = ", ".join(DEFAULT_AVOID)
    return f"""Use case: productivity-visual
Asset type: 16:9 text-included slide visual reference for formal PPTX visual motherboard
Primary request: Create a polished 16:9 executive infographic slide for Slide {slide.number} of the deck "{deck_title}".
Canvas: 16:9 landscape, high-resolution, clean PowerPoint-like slide, premium formal company reporting style.
Motherboard role: This is a visual reference image, not the final editable PPTX. It should raise the visual ceiling for later editable reconstruction.
Generation mode: {sample_line}
Language/text: Preserve the slide title and core message exactly where possible. Keep all visible text readable at presentation distance.
Brand/logo rule: Use the visual language and palette only. Do not draw Huawei logo, Huawei wordmark, or any other brand logo unless a logo asset is explicitly provided for this run.
Date rule: If a date/year is shown, it must come from the outline/source. For this run, CSA2 source dates are in 2026; never show 2024.

Design system from design.md:
{design_summary}

Slide title: {slide.title}
Core message: {slide.key_message or "Use the slide title as the governing thought."}
Suggested visual: {slide.visual or "Create a boardroom-ready infographic composition that fits the title and evidence."}
Evidence/source label: {slide.evidence_label or slide.source or "Not specified"}
Key content blocks:
{bullets}
Keywords to visually emphasize: {keywords or "No extracted keywords"}

Visual direction:
- Create a refined policy/business infographic, not a simple wireframe.
- Use meaningful chart, icon, label, chip, matrix, timeline, or evidence-card language where appropriate.
- Use strong visual hierarchy: action title, governing thought, main evidence/body area, footer/source strip.
- Prefer clean, dense, executive-readable composition with enough whitespace.
- Icons and labels should support comprehension and improve polish.
- Keep factual content aligned to the outline; do not invent new numbers, law names, company positions, or claims.

Avoid: {avoid}.
Output: one complete 16:9 slide image only, no surrounding frame, no UI chrome."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate image-gen prompt pack for a high-quality visual motherboard.")
    parser.add_argument("--outline", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--sample-slides", default=None, help="Comma-separated slide numbers for sample generation.")
    args = parser.parse_args()

    meta, slides = parse_deck_outline(args.outline)
    if not slides:
        raise SystemExit(f"No slides parsed from {args.outline}")

    design_summary = _read_design_summary(args.design)
    deck_title = meta.get("title") or meta.get("objective") or args.outline.stem
    sample_slides = _sample_numbers(slides, args.sample_slides)

    prompts_dir = args.out_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "outline": str(args.outline),
        "design": str(args.design),
        "slide_count": len(slides),
        "sample_slides": sorted(sample_slides),
        "canonical_route": "deck-outline.md + design.md -> image-gen prompts -> image-gen 16:9 infographic motherboard",
        "wireframe_policy": "Deterministic programmatic PNG/PDF/PPTX outputs are scaffolds only and do not satisfy Motherboard Gate unless explicitly approved.",
        "prompts": [],
    }

    for slide in slides:
        path = prompts_dir / f"slide_{slide.number:02d}_prompt.md"
        prompt = _prompt_for_slide(slide, design_summary, deck_title, slide.number in sample_slides)
        path.write_text(prompt + "\n", encoding="utf-8")
        manifest["prompts"].append(
            {
                "slide": slide.number,
                "title": slide.title,
                "sample": slide.number in sample_slides,
                "path": str(path),
            }
        )

    (args.out_dir / "prompt_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "README.md").write_text(
        f"""# Image-Gen Motherboard Prompt Pack

This folder contains the canonical prompt pack for the visual motherboard stage.

- Outline SSOT: `{args.outline}`
- Design SSOT: `{args.design}`
- Slide count: {len(slides)}
- Sample slides: {", ".join(str(x) for x in sorted(sample_slides))}

Use these prompts with an image generation tool to create polished 16:9 text-included infographic slide references. Do not replace this stage with deterministic wireframes unless Martin explicitly accepts that downgrade.
""",
        encoding="utf-8",
    )
    print(f"Wrote {len(slides)} prompts to {prompts_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
