#!/usr/bin/env python3
"""Validate a Life-OS Deep Research package before Hermes delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from pypdf import PdfReader


FORBIDDEN = re.compile(r"(?:OPENAI_API_KEY|GOOGLE_API_KEY|Bearer\s+[A-Za-z0-9._-]{20,})")
LOCAL_PATH = re.compile(r"(?:file:///|/Users/|/home/)[^\s\"'<>]+")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_dir", type=Path)
    ap.add_argument("--require-html", action="store_true")
    ap.add_argument("--require-published", action="store_true")
    args = ap.parse_args()
    root = args.package_dir.resolve()
    errors: list[str] = []

    md = sorted(root.glob("*_deep-research*.md"))
    pdf = sorted(root.glob("*_deep-research*.pdf"))
    manifests = sorted(root.glob("*_manifest.json"))
    html = sorted(root.glob("*_viz-brief.html"))
    publish_manifest = root / "publish-manifest.json"
    sources = root / "sources.jsonl"
    if len(md) != 1:
        errors.append(f"expected one canonical Markdown, found {len(md)}")
    if len(pdf) != 1:
        errors.append(f"expected one canonical PDF, found {len(pdf)}")
    if len(manifests) != 1:
        errors.append(f"expected one manifest, found {len(manifests)}")
    if not sources.is_file():
        errors.append("missing sources.jsonl")
    if len(html) > 1:
        errors.append(f"expected at most one viz-brief HTML, found {len(html)}")
    if args.require_html and len(html) != 1:
        errors.append(f"required one viz-brief HTML, found {len(html)}")
    if args.require_published and not publish_manifest.is_file():
        errors.append("required publish-manifest.json is missing")

    source_counts = {"total": 0, "verified": 0, "partial": 0, "blocked": 0}
    if sources.is_file():
        for n, line in enumerate(sources.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"sources.jsonl:{n}: {exc}")
                continue
            source_counts["total"] += 1
            status = row.get("status")
            if status not in {"verified", "partial", "blocked"}:
                errors.append(f"sources.jsonl:{n}: invalid status {status!r}")
            else:
                source_counts[status] += 1
            if not row.get("url") or not row.get("source_id"):
                errors.append(f"sources.jsonl:{n}: missing source_id/url")

    pages = 0
    if len(pdf) == 1:
        try:
            reader = PdfReader(str(pdf[0]))
            pages = len(reader.pages)
            if pages <= 1:
                errors.append(f"substantive report PDF has only {pages} page")
            if any(not (page.extract_text() or "").strip() for page in reader.pages):
                errors.append("PDF contains a text-empty page")
        except Exception as exc:
            errors.append(f"PDF unreadable: {exc}")

    if len(md) == 1:
        text = md[0].read_text(encoding="utf-8")
        required_sections = {
            "Executive Summary": ("executive summary", "执行摘要"),
            "Key Findings or analytical findings": (
                "key findings",
                "核心发现",
                "核心结论",
                "结论与研究启示",
            ),
            "References": ("references", "参考文献", "来源账本"),
        }
        lowered = text.lower()
        for label, alternatives in required_sections.items():
            if not any(value in lowered for value in alternatives):
                errors.append(f"Markdown missing required section: {label}")
        if FORBIDDEN.search(text):
            errors.append("possible secret found in Markdown")
        if re.search(r"\{\{[^}]+\}\}|\b(?:TODO|TBD)\b", text):
            errors.append("placeholder residue found in Markdown")

    if len(html) == 1:
        html_text = html[0].read_text(encoding="utf-8")
        lowered_html = html_text.lower()
        if "<html" not in lowered_html or "<title" not in lowered_html:
            errors.append("viz-brief HTML missing html/title structure")
        for label, alternatives in {
            "Executive Summary": ("executive summary", "执行摘要"),
            "Key Findings": ("key findings", "核心发现", "核心结论"),
            "References": ("references", "参考文献", "来源"),
        }.items():
            if not any(value in lowered_html for value in alternatives):
                errors.append(f"viz-brief HTML missing required content: {label}")
        if FORBIDDEN.search(html_text) or LOCAL_PATH.search(html_text):
            errors.append("possible secret or local absolute path found in viz-brief HTML")
        if re.search(r"\[\[[^]]+\]\]|\[[^]]+\]\(https?://", html_text):
            errors.append("Markdown link residue found in viz-brief HTML")
        if re.search(r"<script\b[^>]*\bsrc\s*=\s*[\"']https?://", html_text, re.I):
            errors.append("external script found in viz-brief HTML")
        for value in re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)", html_text, re.I):
            if value.startswith(("http://", "https://", "#", "data:", "mailto:")):
                continue
            candidate = (html[0].parent / value.split("#", 1)[0].split("?", 1)[0]).resolve()
            if not candidate.is_file():
                errors.append(f"viz-brief HTML has missing local asset: {value}")

    if publish_manifest.is_file():
        try:
            published = json.loads(publish_manifest.read_text(encoding="utf-8"))
            latest = published.get("latest")
            records = published.get("publications", [])
            current = next((item for item in records if item.get("publication_id") == latest), None)
            if args.require_published and (
                not latest
                or not current
                or current.get("lifecycle") != "active"
                or not current.get("readback", {}).get("verified")
                or not str(current.get("public_url", "")).startswith("https://")
            ):
                errors.append("latest R2 publication is not active and verified")
        except Exception as exc:
            errors.append(f"publish manifest unreadable: {exc}")

    file_hashes = {}
    for path in [*(md or []), *(pdf or []), *(html or []), sources, publish_manifest]:
        if path.is_file():
            file_hashes[path.name] = sha256(path)

    result = {
        "ok": not errors,
        "package": str(root),
        "pdf_pages": pages,
        "sources": source_counts,
        "html_present": len(html) == 1,
        "publish_manifest_present": publish_manifest.is_file(),
        "sha256": file_hashes,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
