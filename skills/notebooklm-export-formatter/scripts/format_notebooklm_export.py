#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path


TOP_LEVEL_BULLET_EMOJIS = {
    "📅", "👥", "🎯", "💬", "🤝", "🚀",
}

SECOND_LEVEL_BULLET_EMOJIS = {
    "📝", "⚠️", "🛑", "👨‍👩‍👧", "✅", "📌", "🏢", "💰", "💡", "🗣",
}

HEADING_PATTERNS = (
    re.compile(r"^ℹ️Meeting Information$"),
    re.compile(r"^✍️ Meeting Minutes$"),
    re.compile(r"^📋Summary of Outstanding Issues$"),
)

SECTION_HEADING_RE = re.compile(r"^\d+️⃣\s+.+$")
INLINE_REF_RE = re.compile(r"\\?\[(\d+)\\?\]")
REFERENCE_LINE_RE = re.compile(r"^\[\^?(\d+)\](?::)?\s+(.*)$")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return "", text

    frontmatter = parts[0] + "\n---\n"
    body = parts[1]
    return frontmatter, body


def normalize_inline_references(line: str) -> str:
    return INLINE_REF_RE.sub(r"[^\1]", line)


def is_heading_line(line: str) -> bool:
    return any(pattern.match(line) for pattern in HEADING_PATTERNS) or bool(SECTION_HEADING_RE.match(line))


def starts_with_emoji_from(line: str, emojis: set[str]) -> bool:
    return any(line.startswith(emoji) for emoji in emojis)


def unwrap_blockquote(line: str) -> str:
    return re.sub(r"^\s*>\s?", "", line).strip()


def is_reference_heading(line: str) -> bool:
    normalized = unwrap_blockquote(line)
    return normalized in {"## 引用来源", "引用来源", "**来源：**", "来源："}


def extract_frontmatter_title(frontmatter: str) -> str | None:
    match = re.search(r'^title:\s*"(.*)"\s*$', frontmatter, flags=re.MULTILINE)
    if match:
        return match.group(1)
    return None


def format_body(body: str, frontmatter_title: str | None = None) -> str:
    raw_lines = [line.rstrip() for line in body.splitlines()]
    output: list[str] = []
    title_seen = False
    in_references = False
    current_section = ""

    for raw_line in raw_lines:
        line = raw_line.strip()

        if not line:
            if output and output[-1] != "":
                output.append("")
            continue

        if line == "---":
            continue

        if line.startswith("导出时间:"):
            continue

        if is_reference_heading(line):
            if output and output[-1] != "":
                output.append("")
            output.append("---")
            output.append("")
            output.append("## 引用来源")
            output.append("")
            in_references = True
            continue

        if in_references:
            normalized_ref_line = unwrap_blockquote(line)
            if not normalized_ref_line:
                continue
            match = REFERENCE_LINE_RE.match(normalized_ref_line)
            if match:
                output.append(f"[^{match.group(1)}]: {match.group(2)}")
            else:
                output.append(normalized_ref_line)
            continue

        line = normalize_inline_references(line)

        if re.match(r"^#{1,6}\s+", line):
            heading_text = re.sub(r"^#{1,6}\s+", "", line)
            if not title_seen and frontmatter_title and heading_text == frontmatter_title:
                title_seen = True
                continue
            if not title_seen:
                title_seen = True
                output.append(f"# {heading_text}")
            elif heading_text.startswith("【"):
                output.append(f"# {heading_text}")
            else:
                output.append(f"## {heading_text}")
            output.append("")
            continue

        if line in {"ℹ️Meeting Information", "✍️ Meeting Minutes"}:
            current_section = line
            output.append(f"## {line}")
            output.append("")
            continue

        if line == "📋Summary of Outstanding Issues":
            current_section = "summary"
            output.append("### 📋Summary of Outstanding Issues")
            output.append("")
            continue

        if SECTION_HEADING_RE.match(line):
            current_section = "minutes"
            output.append(f"### {line}")
            output.append("")
            continue

        if starts_with_emoji_from(line, TOP_LEVEL_BULLET_EMOJIS):
            output.append(f"- {line}")
            output.append("")
            continue

        if starts_with_emoji_from(line, SECOND_LEVEL_BULLET_EMOJIS):
            indent = "" if current_section == "summary" else "  "
            output.append(f"{indent}- {line}")
            output.append("")
            continue

        output.append(line)
        output.append("")

    while output and output[-1] == "":
        output.pop()

    return "\n".join(output) + "\n"


def format_markdown(text: str) -> str:
    frontmatter, body = split_frontmatter(text)
    formatted_body = format_body(body, extract_frontmatter_title(frontmatter))
    if frontmatter:
        return frontmatter + "\n" + formatted_body
    return formatted_body


def build_learning_notes(raw_path: Path, formatted_text: str, polished_text: str) -> str:
    diff = list(
        difflib.unified_diff(
            formatted_text.splitlines(),
            polished_text.splitlines(),
            fromfile="formatted",
            tofile="polished",
            lineterm="",
        )
    )

    repeated_deltas: list[str] = []
    if "## 引用来源" in polished_text and "## 引用来源" in formatted_text:
        repeated_deltas.append("引用区标题保持一致，主要关注正文结构差异。")
    if "[^" in polished_text and "[^" in formatted_text:
        repeated_deltas.append("脚注格式已经对齐，后续主要看 heading / list 层级是否仍需微调。")

    candidate_rules: list[str] = []
    if re.search(r"^### ", polished_text, flags=re.MULTILINE):
        candidate_rules.append("若同类数字段落在 polished 版稳定为三级标题，可继续强化 section heading 识别。")
    if re.search(r"^  - ", polished_text, flags=re.MULTILINE):
        candidate_rules.append("若同类 emoji 行稳定为二级列表，可补充 emoji 到二级列表集合。")

    manual_only = [
        "如果 polished 版本改动了正文措辞或新增总结，不应回写为脚本规则。",
        "如果某一处只是作者主观偏好的空行风格，不必升级成通用规则。",
    ]

    notes = [
        "# Iteration Notes",
        "",
        "## Source",
        f"- raw: {raw_path}",
        "- polished: provided by user",
        "",
        "## Repeated deltas",
    ]

    notes.extend([f"- {item}" for item in repeated_deltas] or ["- 暂未识别到稳定重复差异，请人工查看 unified diff。"])
    notes.extend([
        "",
        "## Candidate generalized rules",
    ])
    notes.extend([f"- {item}" for item in candidate_rules] or ["- 暂无自动建议，请基于 diff 手工判断。"])
    notes.extend([
        "",
        "## Keep manual-only",
    ])
    notes.extend([f"- {item}" for item in manual_only])
    notes.extend([
        "",
        "## Unified diff",
        "",
        "```diff",
        *diff[:400],
        "```",
        "",
    ])
    return "\n".join(notes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format NotebookLM exported Markdown into cleaner Obsidian-friendly Markdown.")
    parser.add_argument("input", help="Path to NotebookLM exported Markdown file")
    parser.add_argument("--output", help="Write formatted output to this path")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted output instead of writing file")
    parser.add_argument("--learn-from", dest="learn_from", help="Path to a manually polished Markdown file for iteration notes")
    parser.add_argument("--notes-out", dest="notes_out", help="Path to write iteration notes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    text = input_path.read_text(encoding="utf-8")
    formatted_text = format_markdown(text)

    if args.dry_run:
        print(formatted_text, end="")
    else:
        output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_formatted.md")
        output_path.write_text(formatted_text, encoding="utf-8")
        print(f"Wrote formatted Markdown to {output_path}")

    if args.learn_from:
        polished_path = Path(args.learn_from)
        polished_text = polished_path.read_text(encoding="utf-8")
        notes = build_learning_notes(input_path, formatted_text, polished_text)
        notes_path = Path(args.notes_out) if args.notes_out else input_path.with_name(f"{input_path.stem}_iteration_notes.md")
        notes_path.write_text(notes, encoding="utf-8")
        print(f"Wrote iteration notes to {notes_path}")

    summary = {
        "input": str(input_path),
        "references_converted": len(re.findall(r"\[\^\d+\]", formatted_text)),
        "footnote_definitions": len(re.findall(r"^\[\^\d+\]:", formatted_text, flags=re.MULTILINE)),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
