#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from deck_utils import compact_terms, norm, parse_deck_outline


def contains(haystack: str, needle: str) -> bool:
    return norm(needle).lower() in norm(haystack).lower()


def coverage(visible: str, items: list[str]) -> tuple[float, list[str]]:
    if not items:
        return 1.0, []
    hits = []
    missing = []
    for item in items:
        terms = compact_terms(item, limit=8)
        if not terms:
            continue
        if any(contains(visible, term) for term in terms):
            hits.append(item)
        else:
            missing.append(item)
    denom = len(hits) + len(missing)
    return (len(hits) / denom if denom else 1.0), missing


def write_md(report: dict, out: Path) -> None:
    lines = [
        "# Text Fidelity Gate",
        "",
        "## Summary",
        "",
        f"- Slides: {report['summary']['slides']}",
        f"- Pass: {report['summary']['pass']}",
        f"- Warn: {report['summary']['warn']}",
        f"- Fail: {report['summary']['fail']}",
        "",
        "## Slide Results",
        "",
        "| Slide | Status | Title | Required Terms | Semantic Coverage | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["results"]:
        missing = ", ".join(r["missing_required_terms"][:5]) if r["missing_required_terms"] else "-"
        note = "; ".join(r["notes"]) if r["notes"] else "-"
        lines.append(
            f"| {r['slide']} | {r['status']} | {r['title_status']} | {missing} | {r['semantic_status']} ({r['semantic_coverage']}) | {note} |"
        )
    lines.extend(["", "## Details", ""])
    for r in report["results"]:
        lines.extend(
            [
                f"### Slide {r['slide']}: {r['status']}",
                "",
                f"- Outline title: `{r['outline_title']}`",
                f"- PPTX first text/title: `{r['pptx_title']}`",
                f"- Key message: {r['key_message']}",
            ]
        )
        if r["missing_required_terms"]:
            lines.append(f"- Missing required terms: {', '.join(r['missing_required_terms'])}")
        if r["missing_semantic_items"]:
            lines.append("- Missing/unrepresented outline items:")
            for item in r["missing_semantic_items"][:8]:
                lines.append(f"  - {item}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outline", required=True, type=Path)
    parser.add_argument("--text-extraction", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--min-coverage", type=float, default=0.45)
    args = parser.parse_args()

    _, outline_slides = parse_deck_outline(args.outline)
    extracted = json.loads(args.text_extraction.read_text(encoding="utf-8"))
    ppt_slides = {int(s["slide"]): s for s in extracted.get("slides", [])}
    results = []

    for spec in outline_slides:
        got = ppt_slides.get(spec.number, {})
        visible = got.get("visible_text", "")
        texts = got.get("texts", [])
        first_text = texts[0]["text"] if texts else ""
        title_status = "pass" if contains(visible, spec.title) or any(contains(visible, t) for t in compact_terms(spec.title, 4)) else "warn"
        required_terms = compact_terms(" ".join([spec.title, spec.key_message]), limit=10)
        missing_required = [term for term in required_terms if not contains(visible, term)]
        semantic_items = [spec.key_message, *spec.bullets]
        score, missing_items = coverage(visible, semantic_items)
        semantic_status = "pass" if score >= 0.72 else "warn" if score >= args.min_coverage else "fail"
        notes = []
        if not visible:
            notes.append("no editable text extracted")
        if len(missing_required) > max(4, len(required_terms) // 2):
            notes.append("many title/key terms missing")
        statuses = [title_status, semantic_status]
        if not visible:
            statuses.append("fail")
        status = "fail" if "fail" in statuses else "warn" if "warn" in statuses else "pass"
        results.append(
            {
                "slide": spec.number,
                "status": status,
                "outline_title": spec.title,
                "pptx_title": first_text,
                "key_message": spec.key_message,
                "title_status": title_status,
                "required_terms": required_terms,
                "missing_required_terms": missing_required,
                "semantic_status": semantic_status,
                "semantic_coverage": round(score, 2),
                "missing_semantic_items": missing_items,
                "notes": notes,
            }
        )

    expected = len(outline_slides)
    actual = extracted.get("summary", {}).get("slide_count", len(ppt_slides))
    if expected != actual:
        results.append(
            {
                "slide": "deck",
                "status": "fail",
                "outline_title": "slide count",
                "pptx_title": str(actual),
                "key_message": "",
                "title_status": "fail",
                "required_terms": [],
                "missing_required_terms": [],
                "semantic_status": "fail",
                "semantic_coverage": 0,
                "missing_semantic_items": [],
                "notes": [f"outline slides={expected}, pptx slides={actual}"],
            }
        )

    summary = {
        "slides": expected,
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "warn": sum(1 for r in results if r["status"] == "warn"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
    }
    report = {"summary": summary, "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_md(report, args.out)
    json_out = args.json_out or args.out.with_suffix(".json")
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
