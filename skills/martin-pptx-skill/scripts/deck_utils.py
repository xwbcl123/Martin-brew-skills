#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SlideSpec:
    number: int
    title: str
    key_message: str = ""
    bullets: list[str] = field(default_factory=list)
    visual: str = ""
    source: str = ""
    evidence_label: str = ""
    raw: str = ""


def norm(text: str) -> str:
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def strip_md(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("：", ":")
    return norm(text)


def parse_frontmatter(markdown: str) -> dict[str, str]:
    if not markdown.startswith("---"):
        return {}
    end = markdown.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in markdown[3:end].splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _field_from_body(body: str, names: list[str]) -> str:
    for name in names:
        patterns = [
            rf"^\*\*{re.escape(name)}\*\*\s*[:：]\s*(.+?)(?=\n\n|\n\*\*|\Z)",
            rf"^- \*\*{re.escape(name)}:\*\*\s*(.+)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, body, flags=re.M | re.S)
            if m:
                return strip_md(m.group(1))
    return ""


def _bullets_from_body(body: str) -> list[str]:
    bullets: list[str] = []
    m = re.search(
        r"^\*\*supporting_bullets\*\*\s*[:：]\s*(.+?)(?=\n\n\*\*|\n---|\Z)",
        body,
        flags=re.M | re.S,
    )
    if m:
        block = m.group(1)
        for line in block.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if cleaned and not cleaned.startswith("|") and not re.match(r"^-{2,}$", cleaned):
                bullets.append(strip_md(cleaned))
    if not bullets:
        m = re.search(r"- \*\*content_blocks:\*\*(.+?)(?=\n- \*\*|\Z)", body, flags=re.S)
        if m:
            for line in m.group(1).splitlines():
                cleaned = re.sub(r"^\s*-\s*", "", line).strip()
                if cleaned:
                    bullets.append(strip_md(cleaned))
    return bullets[:8]


def parse_deck_outline(path: Path) -> tuple[dict[str, str], list[SlideSpec]]:
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    pattern = r"^## Slide\s+(\d+)\s*(?:[-—:：]\s*(.+))?$"
    matches = list(re.finditer(pattern, text, flags=re.M))
    slides: list[SlideSpec] = []
    for idx, match in enumerate(matches):
        number = int(match.group(1))
        heading_title = strip_md(match.group(2) or "")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end]
        title = _field_from_body(body, ["slide_title", "action_title"]) or heading_title
        key_message = _field_from_body(body, ["key_message", "core_message"])
        visual = _field_from_body(body, ["suggested_visual", "visual_intent"])
        source = _field_from_body(body, ["source", "evidence_label"])
        evidence_label = _field_from_body(body, ["evidence_label"]) or ("Source-backed" if source else "")
        bullets = _bullets_from_body(body)
        slides.append(
            SlideSpec(
                number=number,
                title=title,
                key_message=key_message,
                bullets=bullets,
                visual=visual,
                source=source,
                evidence_label=evidence_label,
                raw=body.strip(),
            )
        )
    return meta, slides


def compact_terms(text: str, limit: int = 14) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}|[\u4e00-\u9fff]{2,}", text)
    seen: set[str] = set()
    out: list[str] = []
    stop = {"the", "and", "with", "from", "that", "this", "source", "slide"}
    for token in tokens:
        key = token.lower()
        if key in stop or key in seen:
            continue
        seen.add(key)
        out.append(token)
        if len(out) >= limit:
            break
    return out
