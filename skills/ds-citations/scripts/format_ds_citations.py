#!/usr/bin/env python3
"""
Deep Research Citation Formatter
================================

Convert Deep Research reports (GPT/Gemini/OpenAI artifact style) citations
to Markdown footnote format.

Usage:
    python format_ds_citations.py <file_or_directory>
    python format_ds_citations.py -n <file>  # Preview mode (dry run)
    python format_ds_citations.py -c <file>  # Check mode (verify format only)
    python format_ds_citations.py -f <file>  # Force re-process converted files

Options:
    -n, --dry-run                Preview changes without writing
    -c, --check                  Check file format without processing
    -f, --force                  Force re-process even if already converted
    -r, --recursive              Process subdirectories recursively
    -v, --verbose                Show detailed output
    --trace-mode <mode>          keep|drop|append (default: keep)
    --entity-mode <mode>         strip|keep|footnote (default: strip)
    --footnote-heading <text>    Heading to use when appending footnotes
    --report-json <path>         Write structured processing report to JSON
    -h, --help                   Show this help message
"""

import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Fix Windows encoding issues
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# =============================================================================
# Configuration
# =============================================================================

GPT_INLINE_PATTERN = re.compile(r"\[\\?\[(\d+)\\?\]\]\([^)]+\)")

# Gemini: conservative inline marker in sentence context.
# Match citation numbers like "层级 1。" or "公允价值）4，" while avoiding
# dimensions/decimals such as "5×5×2 英寸" or "0.73 千克".
GEMINI_INLINE_PATTERN = re.compile(
    r"(?:(?<=\s)|(?<=[）)】》」]))(\d{1,3})(?=[。，,；;：:])"
)
GEMINI_REF_PATTERN = re.compile(
    r"^(\d+)\. (.+?)(?:, 访问时间为[^，]+，)? ?\[?(https?://[^\s\]]+)\]?\(?[^)]*\)?$",
    re.MULTILINE,
)

# Already-converted footnotes
CONVERTED_INLINE_PATTERN = re.compile(r"\[\^(\d+)\](?!:)")
CONVERTED_REF_PATTERN = re.compile(r"^\[\^(\d+)\]:", re.MULTILINE)

# OpenAI Deep Research artifact style
ARTIFACT_BRACKET_CITE_PATTERN = re.compile(r"\[([^\]\n]+?)\]\s*cite([^\n]+)")
ARTIFACT_BARE_CITE_PATTERN = re.compile(r"cite([^\n]+)")
ARTIFACT_ENTITY_PATTERN = re.compile(r"entity([^\n]+)")


@dataclass
class ProcessResult:
    """Result of processing a file."""

    success: bool
    message: str
    file_path: str = ""
    format_type: str = "unknown"
    citations_before: int = 0
    citations_after: int = 0
    refs_before: int = 0
    refs_after: int = 0
    changed: bool = False
    missing_refs: int = 0
    orphan_refs: int = 0
    artifact_tokens_remaining: int = 0


@dataclass
class DirectoryStats:
    """Statistics for directory processing."""

    processed: int = 0
    converted: int = 0
    skipped: int = 0
    errors: int = 0

    def total(self) -> int:
        return self.processed + self.converted + self.skipped + self.errors


# =============================================================================
# Format Detection and Validation
# =============================================================================


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_trace_tokens(raw: str) -> List[str]:
    # Raw shape is usually "turn1view0turn2view1"
    return [token.strip() for token in raw.split("") if token.strip()]


def count_artifact_tokens(content: str) -> int:
    return len(re.findall(r"(?:cite|entity)", content))


def detect_format(content: str) -> str:
    """
    Detect report format: 'gpt', 'gemini', 'openai_artifact', 'converted', or 'unknown'.

    Priority:
    1) openai_artifact (if cite/entity tokens exist)
    2) converted
    3) gpt
    4) gemini
    5) unknown
    """
    has_artifact = bool(
        ARTIFACT_BRACKET_CITE_PATTERN.search(content)
        or ARTIFACT_BARE_CITE_PATTERN.search(content)
        or ARTIFACT_ENTITY_PATTERN.search(content)
    )
    if has_artifact:
        return "openai_artifact"

    inline_matches = CONVERTED_INLINE_PATTERN.findall(content)
    ref_matches = CONVERTED_REF_PATTERN.findall(content)
    if inline_matches and ref_matches:
        return "converted"

    if GPT_INLINE_PATTERN.search(content):
        return "gpt"

    # Gemini references at document tail
    if re.search(r"\n\d+\..+访问时间为", content):
        return "gemini"

    # Gemini fallback: sentence-level markers, avoid converted format
    if re.search(r"\s\d{1,3}[。，]", content) and not CONVERTED_INLINE_PATTERN.search(
        content
    ):
        return "gemini"

    return "unknown"


def count_citations(content: str, format_type: str) -> Tuple[int, int]:
    """Count inline citations and reference definitions in content."""
    if format_type == "gpt":
        inline_count = len(GPT_INLINE_PATTERN.findall(content))
        ref_count = len(CONVERTED_REF_PATTERN.findall(content))
        if ref_count == 0 and "---" in content:
            ref_section = content.split("---")[-1]
            ref_count = len(set(GPT_INLINE_PATTERN.findall(ref_section)))
    elif format_type == "gemini":
        inline_count = len(GEMINI_INLINE_PATTERN.findall(content))
        ref_count = len(GEMINI_REF_PATTERN.findall(content))
    elif format_type == "openai_artifact":
        # Bracket cite replacements consume one ARTIFACT_BARE match each, so we estimate
        # raw inline citations as either bracket cite or standalone cite blocks.
        bracket = len(ARTIFACT_BRACKET_CITE_PATTERN.findall(content))
        bare = len(ARTIFACT_BARE_CITE_PATTERN.findall(content)) - bracket
        inline_count = bracket + max(0, bare)
        ref_count = len(CONVERTED_REF_PATTERN.findall(content))
    elif format_type == "converted":
        inline_count = len(CONVERTED_INLINE_PATTERN.findall(content))
        ref_count = len(CONVERTED_REF_PATTERN.findall(content))
    else:
        inline_count = 0
        ref_count = 0
    return inline_count, ref_count


def get_unique_citation_numbers(content: str) -> Tuple[Set[str], Set[str]]:
    inline_nums = set(CONVERTED_INLINE_PATTERN.findall(content))
    ref_nums = set(CONVERTED_REF_PATTERN.findall(content))
    return inline_nums, ref_nums


def remove_consecutive_duplicate_headings(
    content: str, extra_heading: Optional[str] = None
) -> str:
    """Collapse consecutive duplicate reference/footnote headings separated by blank lines."""
    headings = {"## 参考文献", "## References", "## Footnotes"}
    if extra_heading:
        headings.add(f"## {extra_heading}")

    out: List[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped in headings:
            j = len(out) - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            if j >= 0 and out[j].strip() == stripped:
                continue
        out.append(line)
    return "\n".join(out)


def append_footnotes_block(content: str, heading: str, definitions: List[str]) -> str:
    """Append footnote definitions with a heading, merging if heading already exists."""
    if not definitions:
        return content

    heading_line = f"## {heading}"
    trimmed = content.rstrip()
    has_heading = re.search(rf"(?m)^\s*{re.escape(heading_line)}\s*$", trimmed)

    if has_heading:
        return trimmed + "\n\n" + "\n".join(definitions) + "\n"

    return trimmed + f"\n\n{heading_line}\n\n" + "\n".join(definitions) + "\n"


def find_body_footnote_definition_lines(
    content: str, extra_heading: Optional[str] = None
) -> List[int]:
    """Return line numbers for footnote definitions that appear before the final footnote block."""
    headings = {"## 参考文献", "## References", "## Footnotes"}
    if extra_heading:
        headings.add(f"## {extra_heading}")

    lines = content.split("\n")
    def_indices = [
        i for i, line in enumerate(lines) if CONVERTED_REF_PATTERN.match(line)
    ]
    if not def_indices:
        return []

    block_start: Optional[int] = None

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() in headings:
            if any(idx > i for idx in def_indices):
                block_start = i
                break

    if block_start is None:
        saw_def = False
        i = len(lines) - 1
        while i >= 0:
            stripped = lines[i].strip()
            if CONVERTED_REF_PATTERN.match(lines[i]):
                saw_def = True
                i -= 1
                continue
            if stripped == "":
                i -= 1
                continue
            break
        if saw_def:
            block_start = i + 1

    if block_start is None:
        return [idx + 1 for idx in def_indices]

    malformed = [idx + 1 for idx in def_indices if idx < block_start]
    return malformed


GPT_REF_LINE_PATTERN = re.compile(
    r"^(?:\[\\?\[\d+\\?\]\]\([^)]+\)\s*)+(?:https?://\S+)?\s*$"
)
GPT_URL_ONLY_LINE_PATTERN = re.compile(r"^\[https?://[^]]+\]\(https?://[^)]+\)\s*$")


def split_trailing_gpt_reference_block(content: str) -> Tuple[str, str]:
    """Split GPT content into main body and trailing raw reference block.

    The raw GPT exports we handle often end with a loose block like:
    [[1]](url) [[2]](url) https://example.com
    [https://example.com](https://example.com)

    We only want to normalize that trailing block, not anything after the first
    markdown horizontal rule in the document.
    """
    lines = content.split("\n")
    end = len(lines) - 1

    while end >= 0 and lines[end].strip() == "":
        end -= 1

    if end < 0:
        return content, ""

    start = end
    saw_ref_line = False

    while start >= 0:
        stripped = lines[start].strip()
        if stripped == "":
            start -= 1
            continue
        if GPT_REF_LINE_PATTERN.match(stripped) or GPT_URL_ONLY_LINE_PATTERN.match(
            stripped
        ):
            saw_ref_line = True
            start -= 1
            continue
        break

    if not saw_ref_line:
        return content, ""

    split_at = start + 1
    main_lines = lines[:split_at]
    ref_lines = lines[split_at:]
    main_content = "\n".join(main_lines).rstrip()
    ref_content = "\n".join(ref_lines).strip()
    return main_content, ref_content


# =============================================================================
# GPT Format Conversion
# =============================================================================


def convert_gpt_inline(content: str) -> str:
    """Convert GPT inline citations: [[n]](URL) -> [^n]."""
    return GPT_INLINE_PATTERN.sub(r"[^\1]", content)


def convert_gpt_variant_references(content: str) -> str:
    """
    Handle GPT variant references section:
    [[n]](URL) [[m]](URL) Title
    [URL](URL)
    ->
    [^n]: Title URL
    [^m]: Title URL
    """
    main_content, ref_content = split_trailing_gpt_reference_block(content)
    if not ref_content:
        return content

    lines = ref_content.split("\n")
    result = []
    i = 0
    skip_next = False

    while i < len(lines):
        line = lines[i]
        if skip_next:
            skip_next = False
            i += 1
            continue

        citation_pattern = re.compile(r"\[\\?\[(\d+)\\?\]\]\([^)]+\)")
        citations = citation_pattern.findall(line)

        if citations:
            title = normalize_space(citation_pattern.sub("", line))

            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                url_link_pattern = re.compile(r"\[https?://[^]]+\]\(https?://[^)]+\)")
                if url_link_pattern.match(next_line):
                    url_match = re.search(r"\]\((https?://[^)]+)\)", next_line)
                    if url_match:
                        url = url_match.group(1)
                        for num in citations:
                            result.append(f"[^{num}]: {title} {url}")
                        skip_next = True
                        i += 1
                        continue

            urls = re.findall(r"\[\\?\[\d+\\?\]\]\(([^)]+)\)", line)
            for j, num in enumerate(citations):
                url = urls[j] if j < len(urls) else ""
                if url:
                    result.append(f"[^{num}]: {title} {url}")
                else:
                    result.append(f"[^{num}]: {title}")
        else:
            url_link_pattern = re.compile(r"^\[https?://[^]]+\]\(https?://[^)]+\)$")
            if not url_link_pattern.match(line.strip()):
                result.append(line)
        i += 1

    converted_ref_block = "\n".join(result).strip()
    if not converted_ref_block:
        return main_content + "\n"

    return main_content.rstrip() + "\n\n## Footnotes\n\n" + converted_ref_block + "\n"


def convert_gpt_references(content: str) -> str:
    """Clean GPT reference blocks that contain nested [[n]](URL) fragments."""
    lines = content.split("\n")
    result = []
    in_references = False
    skip_raw_urls = False

    for line in lines:
        if line.strip().startswith("## 参考文献") or line.strip().startswith(
            "## References"
        ):
            in_references = True
            result.append(line)
            continue

        if in_references and line.strip() == "---":
            skip_raw_urls = True
            continue

        if skip_raw_urls:
            continue

        if in_references and line.strip().startswith("[^"):
            urls = re.findall(r"\[\\?\[\d+\\?\]\]\(([^)]+)\)", line)
            title = re.sub(r"\[\\?\[\d+\\?\]\]\([^)]+\)", "", line)
            title = normalize_space(title).replace(r"\[", "[").replace(r"\]", "]")

            match = re.match(r"\[\^?(\d+)\]?:\s*(.+)", title)
            if match:
                num, rest = match.groups()
                rest = normalize_space(re.sub(r"\[\^?\d+\]?:?", "", rest))
                if urls:
                    result.append(f"[^{num}]: {rest} {urls[0]}")
                else:
                    result.append(f"[^{num}]: {rest}")
            else:
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


# =============================================================================
# Gemini Format Conversion
# =============================================================================


def convert_gemini_inline(content: str) -> str:
    """Convert Gemini inline citations: n。 -> [^n]."""
    result = []
    for line in content.split("\n"):
        if line.strip().startswith("#"):
            result.append(line)
            continue
        result.append(GEMINI_INLINE_PATTERN.sub(r" [^\1]", line))
    return "\n".join(result)


def convert_gemini_references(content: str) -> str:
    """Convert Gemini references section to footnotes."""
    result = []
    for line in content.split("\n"):
        match = GEMINI_REF_PATTERN.match(line.strip())
        if match:
            num, title, url = match.groups()
            result.append(f"[^{num}]: {title} {url}")
        else:
            result.append(line)
    return "\n".join(result)


# =============================================================================
# OpenAI Deep Research Artifact Conversion
# =============================================================================


def convert_openai_artifact(
    content: str,
    trace_mode: str = "keep",
    entity_mode: str = "strip",
    footnote_heading: str = "Footnotes",
) -> str:
    """
    Convert artifact style citations to markdown footnotes.

    Examples:
    - [Title, URL] citeturn1view0 -> [^n]
    - citeturn1view0 -> [^n]
    - entity... -> stripped/kept/footnote by entity_mode
    """
    existing_nums = [int(n) for n in CONVERTED_REF_PATTERN.findall(content)]
    next_num = (max(existing_nums) + 1) if existing_nums else 1

    notes_by_key: Dict[str, int] = {}
    note_by_num: Dict[int, str] = {}

    def add_note(note_text: str) -> int:
        nonlocal next_num
        normalized = normalize_space(note_text)
        key = normalized.lower()
        if key in notes_by_key:
            return notes_by_key[key]
        number = next_num
        next_num += 1
        notes_by_key[key] = number
        note_by_num[number] = normalized
        return number

    def trace_text_for_bracket(source_text: str, raw_trace: str) -> str:
        traces = parse_trace_tokens(raw_trace)
        if trace_mode == "append" and traces:
            return f"{source_text} | Source trace: {'; '.join(traces)}"
        return source_text

    def trace_text_for_bare(raw_trace: str) -> str:
        traces = parse_trace_tokens(raw_trace)
        if trace_mode == "drop":
            return "Source citation"
        if traces:
            return f"Source trace: {'; '.join(traces)}"
        return "Source trace"

    def replace_bracket(match: re.Match) -> str:
        source_text = normalize_space(match.group(1))
        raw_trace = match.group(2)
        note = trace_text_for_bracket(source_text, raw_trace)
        num = add_note(note)
        return f"[^{num}]"

    new_content = ARTIFACT_BRACKET_CITE_PATTERN.sub(replace_bracket, content)

    def replace_bare(match: re.Match) -> str:
        raw_trace = match.group(1)
        note = trace_text_for_bare(raw_trace)
        num = add_note(note)
        return f"[^{num}]"

    new_content = ARTIFACT_BARE_CITE_PATTERN.sub(replace_bare, new_content)

    if entity_mode == "strip":
        new_content = ARTIFACT_ENTITY_PATTERN.sub("", new_content)
    elif entity_mode == "footnote":

        def replace_entity(match: re.Match) -> str:
            payload = normalize_space(match.group(1))
            num = add_note(f"Entity metadata: {payload}")
            return f"[^{num}]"

        new_content = ARTIFACT_ENTITY_PATTERN.sub(replace_entity, new_content)

    # entity_mode == "keep" leaves entity tokens in place.

    definitions = [f"[^{n}]: {note_by_num[n]}" for n in sorted(note_by_num.keys())]
    if definitions:
        new_content = append_footnotes_block(new_content, footnote_heading, definitions)

    return new_content


# =============================================================================
# Main Processing
# =============================================================================


def process_file(
    file_path: Path,
    dry_run: bool = False,
    force: bool = False,
    check_only: bool = False,
    verbose: bool = False,
    trace_mode: str = "keep",
    entity_mode: str = "strip",
    footnote_heading: str = "Footnotes",
) -> ProcessResult:
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return ProcessResult(
            False, f"Error reading file: {e}", file_path=str(file_path)
        )

    format_type = detect_format(content)
    inline_before, refs_before = count_citations(content, format_type)
    artifact_before = count_artifact_tokens(content)

    if check_only:
        if format_type == "converted":
            inline_nums, ref_nums = get_unique_citation_numbers(content)
            missing_refs = inline_nums - ref_nums
            orphan_refs = ref_nums - inline_nums
            malformed_body_defs = find_body_footnote_definition_lines(
                content, extra_heading=footnote_heading
            )
            msg = f"Format: converted | Inline: {len(inline_nums)} unique | Refs: {len(ref_nums)}"
            if missing_refs:
                msg += f" | ⚠ Missing refs: {sorted(missing_refs)[:5]}"
            if orphan_refs:
                msg += f" | ⚠ Orphan refs: {sorted(orphan_refs)[:5]}"
            if malformed_body_defs:
                msg += (
                    " | ⚠ Body footnote definitions at lines: "
                    f"{malformed_body_defs[:5]}"
                )
            if artifact_before:
                msg += f" | ⚠ Artifact tokens: {artifact_before}"
            return ProcessResult(
                True,
                msg,
                file_path=str(file_path),
                format_type=format_type,
                citations_before=inline_before,
                citations_after=inline_before,
                refs_before=refs_before,
                refs_after=refs_before,
                missing_refs=len(missing_refs),
                orphan_refs=len(orphan_refs),
                artifact_tokens_remaining=artifact_before,
            )

        if format_type in ("gpt", "gemini", "openai_artifact"):
            return ProcessResult(
                True,
                f"Format: {format_type} | Needs conversion | Inline: {inline_before} | Refs: {refs_before}",
                file_path=str(file_path),
                format_type=format_type,
                citations_before=inline_before,
                refs_before=refs_before,
                artifact_tokens_remaining=artifact_before,
            )

        return ProcessResult(
            False,
            "Format: unknown | Cannot process",
            file_path=str(file_path),
            format_type=format_type,
            artifact_tokens_remaining=artifact_before,
        )

    if format_type == "converted":
        if force:
            inline_nums, ref_nums = get_unique_citation_numbers(content)
            missing_refs = len(inline_nums - ref_nums)
            orphan_refs = len(ref_nums - inline_nums)
            return ProcessResult(
                True,
                f"Already converted (forced check) | {len(inline_nums)} citations, {len(ref_nums)} refs",
                file_path=str(file_path),
                format_type=format_type,
                citations_before=inline_before,
                citations_after=inline_before,
                refs_before=refs_before,
                refs_after=refs_before,
                missing_refs=missing_refs,
                orphan_refs=orphan_refs,
                artifact_tokens_remaining=artifact_before,
            )
        return ProcessResult(
            False,
            "Already converted - use -f to force re-check",
            file_path=str(file_path),
            format_type=format_type,
            artifact_tokens_remaining=artifact_before,
        )

    if format_type == "unknown":
        return ProcessResult(
            False,
            "Unknown format - skipping",
            file_path=str(file_path),
            format_type=format_type,
            artifact_tokens_remaining=artifact_before,
        )

    if verbose:
        print(f"  Detected format: {format_type}")
        print(f"  Citations before: {inline_before} inline, {refs_before} refs")

    new_content = content
    if format_type == "gpt":
        ref_section = content.split("---")[-1] if "---" in content else content
        is_variant = "[[" in ref_section or "[\\[" in ref_section
        if is_variant:
            new_content = convert_gpt_variant_references(new_content)
            new_content = convert_gpt_inline(new_content)
        else:
            new_content = convert_gpt_inline(new_content)
            new_content = convert_gpt_references(new_content)
    elif format_type == "gemini":
        new_content = convert_gemini_inline(new_content)
        new_content = convert_gemini_references(new_content)
    elif format_type == "openai_artifact":
        new_content = convert_openai_artifact(
            new_content,
            trace_mode=trace_mode,
            entity_mode=entity_mode,
            footnote_heading=footnote_heading,
        )

    new_content = remove_consecutive_duplicate_headings(
        new_content, extra_heading=footnote_heading
    )

    inline_after, refs_after = count_citations(new_content, "converted")
    inline_nums, ref_nums = get_unique_citation_numbers(new_content)
    missing_refs = len(inline_nums - ref_nums)
    orphan_refs = len(ref_nums - inline_nums)
    malformed_body_defs = find_body_footnote_definition_lines(
        new_content, extra_heading=footnote_heading
    )
    artifact_after = count_artifact_tokens(new_content)

    if malformed_body_defs:
        return ProcessResult(
            False,
            "Validation failed | footnote definitions found before final footnote block "
            f"at lines {malformed_body_defs[:5]}",
            file_path=str(file_path),
            format_type=format_type,
            citations_before=inline_before,
            citations_after=inline_after,
            refs_before=refs_before,
            refs_after=refs_after,
            missing_refs=missing_refs,
            orphan_refs=orphan_refs,
            artifact_tokens_remaining=artifact_after,
        )

    if new_content == content:
        return ProcessResult(
            False,
            "No changes needed",
            file_path=str(file_path),
            format_type=format_type,
            citations_before=inline_before,
            citations_after=inline_after,
            refs_before=refs_before,
            refs_after=refs_after,
            missing_refs=missing_refs,
            orphan_refs=orphan_refs,
            artifact_tokens_remaining=artifact_after,
        )

    validation_parts = []
    if missing_refs:
        validation_parts.append(f"⚠ {missing_refs} missing refs")
    if orphan_refs:
        validation_parts.append(f"⚠ {orphan_refs} orphan refs")
    if artifact_after:
        validation_parts.append(f"⚠ {artifact_after} artifact tokens remain")
    validation_msg = (
        f" | {' | '.join(validation_parts)}" if validation_parts and verbose else ""
    )

    if dry_run:
        lines_old = content.split("\n")[:20]
        lines_new = new_content.split("\n")[:20]
        print("\n  === Preview (first 20 lines) ===")
        for i, (old, new) in enumerate(zip(lines_old, lines_new), start=1):
            if old != new:
                print(f"  Line {i}:")
                print(f"    - {old[:100]}")
                print(f"    + {new[:100]}")
        return ProcessResult(
            True,
            f"Preview complete | {inline_after} citations, {refs_after} refs{validation_msg}",
            file_path=str(file_path),
            format_type=format_type,
            citations_before=inline_before,
            citations_after=inline_after,
            refs_before=refs_before,
            refs_after=refs_after,
            changed=True,
            missing_refs=missing_refs,
            orphan_refs=orphan_refs,
            artifact_tokens_remaining=artifact_after,
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = file_path.with_suffix(file_path.suffix + f".bak.{timestamp}")
    shutil.copy2(file_path, backup_path)
    file_path.write_text(new_content, encoding="utf-8")

    return ProcessResult(
        True,
        f"Converted | {inline_after} citations, {refs_after} refs | backup: {backup_path.name}{validation_msg}",
        file_path=str(file_path),
        format_type=format_type,
        citations_before=inline_before,
        citations_after=inline_after,
        refs_before=refs_before,
        refs_after=refs_after,
        changed=True,
        missing_refs=missing_refs,
        orphan_refs=orphan_refs,
        artifact_tokens_remaining=artifact_after,
    )


def process_directory(
    dir_path: Path,
    dry_run: bool = False,
    force: bool = False,
    check_only: bool = False,
    recursive: bool = False,
    verbose: bool = False,
    trace_mode: str = "keep",
    entity_mode: str = "strip",
    footnote_heading: str = "Footnotes",
    collected_results: Optional[List[ProcessResult]] = None,
) -> DirectoryStats:
    stats = DirectoryStats()

    md_files = (
        list(dir_path.rglob("*.md")) if recursive else list(dir_path.glob("*.md"))
    )

    for md_file in md_files:
        rel_path = md_file.relative_to(dir_path) if recursive else md_file.name
        print(f"\nProcessing: {rel_path}")

        result = process_file(
            md_file,
            dry_run=dry_run,
            force=force,
            check_only=check_only,
            verbose=verbose,
            trace_mode=trace_mode,
            entity_mode=entity_mode,
            footnote_heading=footnote_heading,
        )

        if collected_results is not None:
            collected_results.append(result)

        if result.success:
            if result.format_type == "converted" and not force:
                stats.converted += 1
                print(f"  ◈ {result.message}")
            else:
                stats.processed += 1
                print(f"  ✓ {result.message}")
        else:
            if "Already converted" in result.message:
                stats.converted += 1
                print(f"  ◈ {result.message}")
            elif "Unknown format" in result.message or "No changes" in result.message:
                stats.skipped += 1
                print(f"  ⊘ {result.message}")
            else:
                stats.errors += 1
                print(f"  ✗ {result.message}")

    return stats


# =============================================================================
# CLI Entry Point
# =============================================================================


def parse_args(args: List[str]) -> Dict[str, Any]:
    options: Dict[str, Any] = {
        "dry_run": False,
        "check_only": False,
        "force": False,
        "recursive": False,
        "verbose": False,
        "help": False,
        "trace_mode": "keep",
        "entity_mode": "strip",
        "footnote_heading": "Footnotes",
        "report_json": None,
        "paths": [],
    }

    i = 0
    while i < len(args):
        arg = args[i]

        if arg in ("-n", "--dry-run"):
            options["dry_run"] = True
        elif arg in ("-c", "--check"):
            options["check_only"] = True
        elif arg in ("-f", "--force"):
            options["force"] = True
        elif arg in ("-r", "--recursive"):
            options["recursive"] = True
        elif arg in ("-v", "--verbose"):
            options["verbose"] = True
        elif arg in ("-h", "--help"):
            options["help"] = True
        elif arg == "--trace-mode":
            i += 1
            if i >= len(args):
                raise ValueError("--trace-mode requires a value: keep|drop|append")
            options["trace_mode"] = args[i]
        elif arg == "--entity-mode":
            i += 1
            if i >= len(args):
                raise ValueError("--entity-mode requires a value: strip|keep|footnote")
            options["entity_mode"] = args[i]
        elif arg == "--footnote-heading":
            i += 1
            if i >= len(args):
                raise ValueError("--footnote-heading requires text")
            options["footnote_heading"] = args[i]
        elif arg == "--report-json":
            i += 1
            if i >= len(args):
                raise ValueError("--report-json requires a file path")
            options["report_json"] = args[i]
        elif arg.startswith("-"):
            raise ValueError(f"Unknown option: {arg}")
        else:
            options["paths"].append(arg)

        i += 1

    trace_mode = str(options["trace_mode"])
    if trace_mode not in {"keep", "drop", "append"}:
        raise ValueError("--trace-mode must be one of: keep, drop, append")

    entity_mode = str(options["entity_mode"])
    if entity_mode not in {"strip", "keep", "footnote"}:
        raise ValueError("--entity-mode must be one of: strip, keep, footnote")

    return options


def serialize_result(result: ProcessResult) -> Dict[str, object]:
    return {
        "path": result.file_path,
        "success": result.success,
        "format": result.format_type,
        "message": result.message,
        "changed": result.changed,
        "citations_before": result.citations_before,
        "citations_after": result.citations_after,
        "refs_before": result.refs_before,
        "refs_after": result.refs_after,
        "missing_refs": result.missing_refs,
        "orphan_refs": result.orphan_refs,
        "artifact_tokens_remaining": result.artifact_tokens_remaining,
    }


def write_report_json(
    report_path: Path,
    mode: str,
    input_path: str,
    results: List[ProcessResult],
    stats: Optional[DirectoryStats] = None,
) -> None:
    payload: Dict[str, object] = {
        "mode": mode,
        "input": input_path,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": [serialize_result(r) for r in results],
    }
    if stats is not None:
        payload["summary"] = {
            "processed": stats.processed,
            "already_converted": stats.converted,
            "skipped": stats.skipped,
            "errors": stats.errors,
            "total": stats.total(),
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    args = sys.argv[1:]
    try:
        options = parse_args(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not args or options["help"]:
        print(__doc__)
        print("\nArguments:")
        print("  <file_or_directory>  Path to .md file or directory")
        print("\nOptions:")
        print("  -n, --dry-run                 Preview changes without writing")
        print("  -c, --check                   Check file format and citation counts")
        print(
            "  -f, --force                   Force re-process even if already converted"
        )
        print("  -r, --recursive               Process subdirectories recursively")
        print("  -v, --verbose                 Show detailed output")
        print("  --trace-mode keep|drop|append Control artifact trace handling")
        print("  --entity-mode strip|keep|footnote Control artifact entity handling")
        print("  --footnote-heading <text>     Heading used for appended footnotes")
        print("  --report-json <path>          Write structured report in JSON")
        print("  -h, --help                    Show this help message")
        print("\nExamples:")
        print("  python format_ds_citations.py report.md")
        print("  python format_ds_citations.py -n ./deep-research/")
        print("  python format_ds_citations.py -c -r ./sources/")
        print(
            "  python format_ds_citations.py ./reports --trace-mode append --entity-mode footnote"
        )
        sys.exit(0)

    paths: List[str] = options["paths"]
    if not paths:
        print("Error: Please specify a file or directory")
        sys.exit(1)

    input_path = Path(paths[0])
    if not input_path.exists():
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    print("=" * 60)
    print("Deep Research Citation Formatter")
    print("=" * 60)

    mode_indicators = []
    if options["dry_run"]:
        mode_indicators.append("PREVIEW")
    if options["check_only"]:
        mode_indicators.append("CHECK")
    if options["force"]:
        mode_indicators.append("FORCE")
    if options["recursive"]:
        mode_indicators.append("RECURSIVE")
    if options["verbose"]:
        mode_indicators.append("VERBOSE")

    if mode_indicators:
        print(f"\n[{' | '.join(mode_indicators)}]")

    report_results: List[ProcessResult] = []
    report_path_raw = options["report_json"]
    report_path = Path(report_path_raw) if isinstance(report_path_raw, str) else None

    if input_path.is_file():
        result = process_file(
            input_path,
            dry_run=bool(options["dry_run"]),
            force=bool(options["force"]),
            check_only=bool(options["check_only"]),
            verbose=bool(options["verbose"]),
            trace_mode=str(options["trace_mode"]),
            entity_mode=str(options["entity_mode"]),
            footnote_heading=str(options["footnote_heading"]),
        )
        report_results.append(result)

        if result.success:
            print(f"\n✓ {result.message}")
        else:
            print(f"\n✗ {result.message}")
            if report_path is not None:
                write_report_json(report_path, "file", str(input_path), report_results)
            sys.exit(1)

        if report_path is not None:
            write_report_json(report_path, "file", str(input_path), report_results)
            print(f"\nReport written: {report_path}")

    elif input_path.is_dir():
        stats = process_directory(
            input_path,
            dry_run=bool(options["dry_run"]),
            force=bool(options["force"]),
            check_only=bool(options["check_only"]),
            recursive=bool(options["recursive"]),
            verbose=bool(options["verbose"]),
            trace_mode=str(options["trace_mode"]),
            entity_mode=str(options["entity_mode"]),
            footnote_heading=str(options["footnote_heading"]),
            collected_results=report_results,
        )

        print("\n" + "=" * 60)
        print(
            f"Summary: {stats.processed} processed, {stats.converted} already converted, "
            f"{stats.skipped} skipped, {stats.errors} errors"
        )
        print("=" * 60)

        if report_path is not None:
            write_report_json(
                report_path, "directory", str(input_path), report_results, stats
            )
            print(f"\nReport written: {report_path}")

    else:
        print(f"Error: Not a file or directory: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
