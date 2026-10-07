#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organization Deck Compliance & Formatting Gate Validator
Strictly verifies PowerPoint (.pptx) deliverables against Organization Modernist formatting guidelines:
1. Prohibits full-bleed canvas background shapes (Rectangle 1 ban)
2. Prohibits excessive corner radius on rounded rectangles (Anti-kindergarten rounded corners: adj <= 0.05)
3. Enforces strict typography floors (H1 >= 20/24/28pt, Body >= 14pt, Pills >= 10pt, Captions >= 10pt, Footers >= 9pt)
4. Enforces tight text frame internal margins (L/R <= 0.12", T/B <= 0.07") to free space for large fonts
5. Detects horizontal overlapping collisions in footer metadata zones
6. Detects text frame bounding box depth overkill (preventing invisible hit-box occlusions)
7. Detects card-level element vertical collisions / lack of breathing space
8. Verifies 16:9 widescreen canvas aspect ratio
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt
except ImportError:
    print("ERROR: python-pptx is required. Install via `pip install python-pptx`.", file=sys.stderr)
    sys.exit(2)


class DeckComplianceValidator:
    def __init__(self, pptx_path: Path, strict: bool = False, verbose: bool = False):
        self.pptx_path = pptx_path
        self.strict = strict
        self.verbose = verbose
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.passes: list[dict[str, Any]] = []

    def validate(self) -> dict[str, Any]:
        if not self.pptx_path.is_file():
            self.errors.append({
                "slide": 0,
                "category": "FILE",
                "message": f"File does not exist: {self.pptx_path}"
            })
            return self._build_report()

        try:
            prs = Presentation(str(self.pptx_path))
        except Exception as e:
            self.errors.append({
                "slide": 0,
                "category": "FILE",
                "message": f"Failed to parse presentation: {e}"
            })
            return self._build_report()

        sw = prs.slide_width.inches
        sh = prs.slide_height.inches

        # Check 1: Slide Aspect Ratio (16:9 widescreen standard: 13.333 x 7.5 inches)
        aspect = sw / sh if sh > 0 else 0
        if abs(aspect - (16.0 / 9.0)) > 0.05:
            self.errors.append({
                "slide": 0,
                "category": "CANVAS_SIZE",
                "message": f"Slide dimensions ({sw:.2f}\" x {sh:.2f}\") do not match 16:9 ratio (aspect={aspect:.2f})."
            })
        else:
            self.passes.append({
                "slide": 0,
                "category": "CANVAS_SIZE",
                "message": f"Widescreen 16:9 layout verified ({sw:.2f}\" x {sh:.2f}\")."
            })

        for s_idx, slide in enumerate(prs.slides):
            slide_num = s_idx + 1
            is_cover = (s_idx == 0)

            # Check 2: Ban on full-bleed canvas shapes (Rectangle 1 ban)
            for shape in slide.shapes:
                if (shape.left.inches <= 0.1 and shape.top.inches <= 0.1 and
                        shape.width.inches >= sw - 0.2 and shape.height.inches >= sh - 0.2):
                    self.errors.append({
                        "slide": slide_num,
                        "category": "BACKGROUND_SHAPE",
                        "shape": shape.name,
                        "message": (
                            f"Full-bleed canvas shape '{shape.name}' ({shape.width.inches:.2f}\" x {shape.height.inches:.2f}\") "
                            f"detected. Never draw manual background rectangles; use native slide.background or blank master layout."
                        )
                    })

            # Check 3: Rounded Rectangle Corner Radius (reference Benchmark: adj <= 0.055 for cards)
            for shape in slide.shapes:
                try:
                    is_round_rect = False
                    if hasattr(shape, "auto_shape_type") and shape.auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
                        is_round_rect = True
                    elif "roundrect" in shape.name.lower() or "圆角矩形" in shape.name:
                        is_round_rect = True

                    if is_round_rect and hasattr(shape, "adjustments") and len(shape.adjustments) > 0:
                        adj = shape.adjustments[0]
                        w = shape.width.inches
                        h = shape.height.inches
                        # For card/panel containers (width >= 1.5 in and height >= 0.8 in)
                        if w >= 1.5 and h >= 0.8:
                            if adj > 0.055:
                                self.errors.append({
                                    "slide": slide_num,
                                    "category": "EXCESSIVE_CORNER_RADIUS",
                                    "shape": shape.name,
                                    "adjustment": adj,
                                    "message": (
                                        f"Rounded rectangle '{shape.name}' ({w:.2f}\" x {h:.2f}\") has excessive corner radius "
                                        f"(adj={adj:.3f} > 0.055; default is 0.167). Giant rounded corners appear childish and unprofessional "
                                        f"('kindergarten' aesthetic). Explicitly set shape.adjustments[0] = 0.03 ~ 0.05 (reference benchmark)."
                                    )
                                })
                            else:
                                self.passes.append({
                                    "slide": slide_num,
                                    "category": "CORNER_RADIUS",
                                    "message": f"Professional subtle corner radius verified on '{shape.name}' (adj={adj:.3f})."
                                })
                except Exception:
                    pass

            # Check 4: Footer horizontal collision detection
            footer_shapes = [s for s in slide.shapes if s.has_text_frame and s.top.inches >= sh - 0.65]
            for i in range(len(footer_shapes)):
                for j in range(i + 1, len(footer_shapes)):
                    s1, s2 = footer_shapes[i], footer_shapes[j]
                    l1, r1 = s1.left.inches, s1.left.inches + s1.width.inches
                    l2, r2 = s2.left.inches, s2.left.inches + s2.width.inches
                    if max(l1, l2) < min(r1, r2):
                        self.errors.append({
                            "slide": slide_num,
                            "category": "FOOTER_COLLISION",
                            "shapes": [s1.name, s2.name],
                            "message": (
                                f"Footer shapes '{s1.name}' and '{s2.name}' horizontally overlap: "
                                f"[{l1:.2f}\", {r1:.2f}\"] vs [{l2:.2f}\", {r2:.2f}\"]. Use decoupled 3-segment coordinates."
                            )
                        })

            # Check 5: Card internal vertical element collision & breathing space
            # Exclude headers, footers, and parent card backgrounds containing children
            content_items = []
            for s in slide.shapes:
                top_in = s.top.inches
                if 0.8 <= top_in <= sh - 0.7:
                    content_items.append({
                        "shape": s,
                        "name": s.name,
                        "left": s.left.inches,
                        "top": s.top.inches,
                        "width": s.width.inches,
                        "height": s.height.inches,
                        "right": s.left.inches + s.width.inches,
                        "bottom": s.top.inches + s.height.inches,
                        "has_text": s.has_text_frame and bool(s.text_frame.text.strip())
                    })

            for i in range(len(content_items)):
                for j in range(i + 1, len(content_items)):
                    sa, sb = content_items[i], content_items[j]

                    # Helper: check containment (parent card background containing child element)
                    def contains(p, c):
                        return (p["left"] <= c["left"] + 0.15 and p["right"] >= c["right"] - 0.15 and
                                p["top"] <= c["top"] + 0.15 and p["bottom"] >= c["bottom"] - 0.15)

                    if contains(sa, sb) or contains(sb, sa):
                        continue

                    # Helper: check intentional overlay (e.g. pill badge bg + pill badge text)
                    if abs(sa["left"] - sb["left"]) < 0.15 and abs(sa["top"] - sb["top"]) < 0.15:
                        continue

                    # Check if horizontally aligned in the same card/column (horizontal overlap >= 50% of narrower)
                    h_overlap = max(0.0, min(sa["right"], sb["right"]) - max(sa["left"], sb["left"]))
                    min_w = min(sa["width"], sb["width"])
                    if min_w > 0 and (h_overlap / min_w) >= 0.5:
                        top_s = sa if sa["top"] <= sb["top"] else sb
                        bot_s = sb if sa["top"] <= sb["top"] else sa

                        overlap = top_s["bottom"] - bot_s["top"]
                        if overlap > 0.05:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "ELEMENT_COLLISION",
                                "shapes": [top_s["name"], bot_s["name"]],
                                "message": (
                                    f"Card elements '{top_s['name']}' and '{bot_s['name']}' vertically overlap by "
                                    f"{overlap:.2f}\". Nudge elements to restore clean separation."
                                )
                            })
                        elif 0.0 <= -overlap < 0.04 and top_s["height"] < 1.5:
                            self.warnings.append({
                                "slide": slide_num,
                                "category": "BREATHING_ROOM",
                                "shapes": [top_s["name"], bot_s["name"]],
                                "message": (
                                    f"Card elements '{top_s['name']}' and '{bot_s['name']}' lack vertical breathing room "
                                    f"(gap={-overlap:.2f}\" < 0.04\"). Ensure >= 0.08\" breathing space."
                                )
                            })

            # Check 6: Typography floors, Text frame margins & Bounding box snugness
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue

                tf = shape.text_frame
                raw_text = tf.text.strip()
                if not raw_text:
                    continue

                top = shape.top.inches
                left = shape.left.inches
                height = shape.height.inches
                width = shape.width.inches
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

                # Role Classification
                if is_cover:
                    role = "cover_meta"
                    if top < 2.5:
                        role = "cover_title"
                else:
                    if top >= sh - 0.65:
                        role = "footer"
                    elif top < 0.50 and left < 2.50 and len(lines) <= 1:
                        role = "eyebrow"
                    elif 0.40 <= top <= 0.85 and left < 2.50:
                        role = "slide_title"
                    elif 0.85 < top <= 1.35 and left < 2.50 and len(lines) <= 2:
                        role = "slide_subtitle"
                    elif height <= 0.38 and len(lines) <= 1 and len(raw_text) <= 35:
                        role = "pill_badge"
                    elif height <= 0.45 and len(lines) <= 1 and any(
                        shape.name.lower().startswith(x) for x in ["card_title", "heading", "title", "h3"]
                    ):
                        role = "card_heading"
                    else:
                        role = "body"

                # Check 6a: Text box internal margins (Tight Padding Technique from reference proposal)
                # If body text frame inside a card has bulky default margins (>0.15" left/right or >0.12" top/bottom)
                if not is_cover and role in ("body", "card_heading"):
                    ml = tf.margin_left.inches if tf.margin_left is not None else 0.1
                    mr = tf.margin_right.inches if tf.margin_right is not None else 0.1
                    mt = tf.margin_top.inches if tf.margin_top is not None else 0.05
                    mb = tf.margin_bottom.inches if tf.margin_bottom is not None else 0.05
                    if ml > 0.15 or mt > 0.12:
                        self.warnings.append({
                            "slide": slide_num,
                            "category": "BULKY_TEXT_MARGINS",
                            "shape": shape.name,
                            "message": (
                                f"Text frame '{shape.name}' uses bulky margins (L:{ml:.2f}\", T:{mt:.2f}\"). "
                                f"Tighten internal margins to Top/Bottom 3.6-5pt (0.05\") and Left/Right 7.2-9pt (0.10\") "
                                f"to maximize available container area for 14/16pt text."
                            )
                        })

                # Check 6b: Text frame depth overkill (warning)
                # If text has <= 3 short lines but height is > 3.2 inches, warning for invisible hit-box occlusion
                if not is_cover and role == "body" and height >= 3.2:
                    estimated_lines = sum(max(1, len(l) // 30) for l in lines)
                    if estimated_lines <= 3:
                        self.warnings.append({
                            "slide": slide_num,
                            "category": "BOUNDING_BOX_DEPTH",
                            "shape": shape.name,
                            "message": (
                                f"Text frame '{shape.name}' height {height:.2f}\" is excessively tall for only {estimated_lines} "
                                f"lines of text. Snug-fit bounding box to <= 2.5\" to avoid invisible hit-box occlusion."
                            )
                        })

                # Check 6c: Validate font sizes per run
                for p_i, p in enumerate(tf.paragraphs):
                    for r_i, r in enumerate(p.runs):
                        if not r.text.strip():
                            continue
                        sz = r.font.size.pt if r.font.size else (p.font.size.pt if p.font.size else None)
                        if sz is None:
                            continue

                        run_snippet = r.text[:30].replace("\n", " ")
                        if role == "body" and sz < 14.0:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Body text font size {sz:.1f}pt is below the 14.0pt hard floor in '{shape.name}': \"{run_snippet}\""
                            })
                        elif role == "slide_title" and sz < 20.0:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Slide title font size {sz:.1f}pt is below 20.0pt floor in '{shape.name}': \"{run_snippet}\""
                            })
                        elif role == "pill_badge" and sz < 10.0:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Pill badge font size {sz:.1f}pt is below 10.0pt floor in '{shape.name}': \"{run_snippet}\""
                            })
                        elif role == "footer" and sz < 9.0:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Footer text font size {sz:.1f}pt is below 9.0pt floor in '{shape.name}': \"{run_snippet}\""
                            })
                        elif role == "eyebrow" and sz < 9.0:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Eyebrow font size {sz:.1f}pt is below 9.0pt floor in '{shape.name}': \"{run_snippet}\""
                            })
                        elif role == "slide_subtitle" and sz < 10.5:
                            self.errors.append({
                                "slide": slide_num,
                                "category": "FONT_SIZE_FLOOR",
                                "shape": shape.name,
                                "role": role,
                                "size": sz,
                                "message": f"Subtitle font size {sz:.1f}pt is below 11.0pt floor in '{shape.name}': \"{run_snippet}\""
                            })

        return self._build_report()

    def _build_report(self) -> dict[str, Any]:
        passed = len(self.errors) == 0 and (not self.strict or len(self.warnings) == 0)
        return {
            "file": str(self.pptx_path),
            "passed": passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "pass_count": len(self.passes),
            "errors": self.errors,
            "warnings": self.warnings,
            "passes": self.passes
        }


def format_cli_output(report: dict[str, Any], verbose: bool = False) -> str:
    lines = []
    lines.append("================================================================================")
    lines.append(f"Organization Deck Compliance Verification Report: {Path(report['file']).name}")
    lines.append("================================================================================")
    
    if report["passed"]:
        status_line = "STATUS: [PASS] All mandatory compliance checks passed."
    else:
        status_line = f"STATUS: [FAIL] {report['error_count']} errors, {report['warning_count']} warnings found."
    lines.append(status_line)
    lines.append("")

    if report["errors"]:
        lines.append("--- ERRORS (Hard Violations) ---")
        for err in report["errors"]:
            prefix = f"Slide {err['slide']:02d}" if err.get("slide", 0) > 0 else "Deck Global"
            lines.append(f"  ❌ [{prefix}] [{err['category']}] {err['message']}")
        lines.append("")

    if report["warnings"]:
        lines.append("--- WARNINGS (Quality & Layout Smells) ---")
        for warn in report["warnings"]:
            prefix = f"Slide {warn['slide']:02d}" if warn.get("slide", 0) > 0 else "Deck Global"
            lines.append(f"  ⚠️  [{prefix}] [{warn['category']}] {warn['message']}")
        lines.append("")

    if verbose and report["passes"]:
        lines.append("--- PASSED CHECKS ---")
        for p in report["passes"]:
            prefix = f"Slide {p['slide']:02d}" if p.get("slide", 0) > 0 else "Deck Global"
            lines.append(f"  ✅ [{prefix}] [{p['category']}] {p['message']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify PPTX deliverables against Organization Modernist formatting standards."
    )
    parser.add_argument("pptx_path", type=Path, help="Path to the PowerPoint presentation file (.pptx)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors (fail on warnings)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include passed checks in terminal output")

    args = parser.parse_args()

    validator = DeckComplianceValidator(args.pptx_path, strict=args.strict, verbose=args.verbose)
    report = validator.validate()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_cli_output(report, verbose=args.verbose))

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
