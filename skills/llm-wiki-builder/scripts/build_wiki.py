from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


PARSED_EXTS = {".md", ".pdf", ".docx", ".pptx"}
COPY_ONLY_EXTS = {".xlsx", ".xlsm", ".csv", ".tsv", ".png", ".jpg", ".jpeg", ".webp"}
MANUAL_EXTS = {".zip"}
CORE_FILES = ["index.md", "log.md", "AGENTS.md", "LINTS.md", "_meta.md"]


@dataclass
class FileRecord:
    relative_path: str
    extension: str
    size: int
    category: str
    extracted: bool = False
    note: str = ""


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "-", value, flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "untitled"


def today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def detect_markitdown() -> bool:
    return shutil.which("markitdown") is not None


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, incremental_safe: bool) -> None:
    if incremental_safe and path.exists():
        return
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(content)


def has_contract(root: Path) -> bool:
    markers = [
        root / "analysis",
        root / "evidence",
        root / "index.md",
        root / "AGENTS.md",
        root / "LINTS.md",
        root / "_meta.md",
    ]
    return any(marker.exists() for marker in markers)


def next_sibling_root(root: Path) -> Path:
    parent = root.parent
    stem = root.name
    counter = 2
    while True:
        candidate = parent / f"{stem}-v{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_tree_contents(src: Path, dst: Path) -> None:
    ensure_dir(dst)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def classify_extension(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in PARSED_EXTS:
        return "supported-and-parsed"
    if ext in COPY_ONLY_EXTS:
        return "copied-only"
    if ext in MANUAL_EXTS:
        return "manual-review-required"
    return "manual-review-required"


def is_lockfile(path: Path) -> bool:
    return path.name.startswith("~$")


def inventory_files(root: Path) -> List[FileRecord]:
    records: List[FileRecord] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if is_lockfile(path):
            continue
        category = classify_extension(path)
        rel = path.relative_to(root).as_posix()
        records.append(
            FileRecord(
                relative_path=rel,
                extension=path.suffix.lower() or "<none>",
                size=path.stat().st_size,
                category=category,
            )
        )
    return records


def infer_normalized_name(path: Path, context: str, template: str | None) -> str:
    if re.match(r"^\d{8}_", path.name):
        return path.name
    stem = slugify(path.stem)
    date_part = today_yyyymmdd()
    ext = path.suffix.lower()
    if template:
        name = template.replace("{date}", date_part).replace("{context}", context).replace("{slug}", stem)
        if not name.endswith(ext):
            name += ext
        return name
    return f"{date_part}_[{context}]_{stem}{ext}"


def build_normalized_copy(raw_dir: Path, normalized_dir: Path, context: str, template: str | None) -> Dict[str, str]:
    if normalized_dir.exists():
        shutil.rmtree(normalized_dir)
    ensure_dir(normalized_dir)
    rename_map: Dict[str, str] = {}
    for path in sorted(raw_dir.rglob("*")):
        rel = path.relative_to(raw_dir)
        target_parent = normalized_dir / rel.parent
        if path.is_dir():
            ensure_dir(target_parent / path.name)
            continue
        ensure_dir(target_parent)
        new_name = infer_normalized_name(path, context, template)
        target = target_parent / new_name
        counter = 2
        while target.exists():
            target = target_parent / f"{target.stem}-v{counter}{target.suffix}"
            counter += 1
        shutil.copy2(path, target)
        rename_map[rel.as_posix()] = target.relative_to(normalized_dir).as_posix()
    return rename_map


def try_markitdown(src: Path, dst: Path) -> bool:
    ensure_dir(dst.parent)
    result = subprocess.run(
        ["markitdown", str(src)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return False
    dst.write_text(result.stdout, encoding="utf-8")
    return True


def extract_sources(
    source_root: Path,
    ingest_root: Path,
    records: List[FileRecord],
    enable_ocr: bool,
) -> tuple[List[FileRecord], List[str], List[str]]:
    skipped: List[str] = []
    uncertain: List[str] = []
    markitdown_available = detect_markitdown()
    for record in records:
        src = source_root / Path(record.relative_path)
        rel = Path(record.relative_path)
        if record.category == "supported-and-parsed":
            if src.suffix.lower() == ".md":
                dst = ingest_root / rel
                ensure_dir(dst.parent)
                shutil.copy2(src, dst)
                record.extracted = True
                record.note = "markdown copied into ingest layer"
                continue
            if markitdown_available:
                dst = ingest_root / rel.with_suffix(".md")
                ok = try_markitdown(src, dst)
                if ok:
                    record.extracted = True
                    record.note = "extracted via markitdown"
                else:
                    record.category = "manual-review-required"
                    record.note = "markitdown failed"
                    uncertain.append(record.relative_path)
            else:
                record.category = "manual-review-required"
                record.note = "markitdown unavailable"
                uncertain.append(record.relative_path)
        elif record.category == "copied-only":
            if src.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and enable_ocr and markitdown_available:
                dst = ingest_root / rel.with_suffix(".md")
                ok = try_markitdown(src, dst)
                if ok:
                    record.category = "supported-and-parsed"
                    record.extracted = True
                    record.note = "ocr/extraction succeeded via markitdown"
                else:
                    record.note = "copied-only; OCR attempt failed"
                    skipped.append(record.relative_path)
            else:
                record.note = "copied-only"
                skipped.append(record.relative_path)
        else:
            record.note = "manual review required"
            uncertain.append(record.relative_path)
    return records, skipped, uncertain


def build_index(root: Path, records: List[FileRecord], canonical_lang: str, normalize: bool) -> str:
    total = len(records)
    parsed = sum(1 for r in records if r.extracted)
    copied_only = sum(1 for r in records if r.category == "copied-only")
    manual = sum(1 for r in records if r.category == "manual-review-required")
    return f"""---
title: Folder Wiki
type: kb-index
status: active
canonical_lang: {canonical_lang}
source_layer: wiki
updated: {datetime.now().date()}
schema_version: wiki-skill-v1
---

# Folder Wiki

## Overview

- Total files: {total}
- Parsed files: {parsed}
- Copied-only files: {copied_only}
- Manual-review-required files: {manual}
- Filename normalization enabled: {"yes" if normalize else "no"}

## Navigation

- [log.md](log.md)
- [analysis/overview.md](analysis/overview.md)
- [evidence/source-inventory.md](evidence/source-inventory.md)
- [AGENTS.md](AGENTS.md)
- [LINTS.md](LINTS.md)
- [_meta.md](_meta.md)

## Source Layers

- [raw/](raw/)
- {"- [raw-normalized/](raw-normalized/)" if normalize else "- raw-normalized/: not generated"}
- [analysis/](analysis/)
- [evidence/](evidence/)
"""


def build_log(records: List[FileRecord], source_path: Path, rerun_mode: str) -> str:
    return f"""---
title: Wiki Build Log
type: kb-log
status: active
canonical_lang: zh-CN
source_layer: wiki
updated: {datetime.now().date()}
schema_version: wiki-skill-v1
---

# Wiki Build Log

## [{datetime.now().date()}] bootstrap

- source_path: `{source_path}`
- rerun_mode: `{rerun_mode}`
- total_files: `{len(records)}`
- generated_by: `llm-wiki-builder`
"""


def build_agents() -> str:
    return """# AGENTS.md

## Scope

This local handbook applies only to this wiki root.

## Contract

- Keep source files in `raw/`
- Keep renamed working copies in `raw-normalized/` only
- Keep extracted text in `analysis/ingest-src/`
- Keep evidence pages in `evidence/`
- Keep root clean: only navigation and governance pages belong here

## Working Rules

- Do not mutate `raw/` after ingestion
- Do not present copied-only files as parsed evidence
- Append to `log.md`; do not rewrite history
- Keep analysis and evidence traceable back to source files
"""


def build_lints() -> str:
    return """# LINTS.md

## Core Lints

- `raw/` must not contain analysis markdown
- `raw-normalized/` must not be treated as source of truth
- `analysis/ingest-src/` is intermediate text, not final knowledge
- root must stay clean and keep only navigation/governance files
- every evidence or analysis page should be traceable to source files
- unsupported or uncertain files must appear in skipped/uncertain reporting
"""


def build_meta() -> str:
    return """# _meta.md

## Minimum Frontmatter

Use these keys for generated wiki pages when applicable:

```yaml
title:
type:
status:
canonical_lang:
source_layer:
updated:
schema_version:
```

## Minimal Types

- `kb-index`
- `kb-log`
- `analysis-overview`
- `evidence-inventory`
"""


def build_analysis_overview(records: List[FileRecord], source_root: Path) -> str:
    by_ext: Dict[str, int] = {}
    for record in records:
        by_ext[record.extension] = by_ext.get(record.extension, 0) + 1
    lines = "\n".join(f"- `{ext}`: {count}" for ext, count in sorted(by_ext.items(), key=lambda kv: (-kv[1], kv[0])))
    return f"""---
title: Analysis Overview
type: analysis-overview
status: active
canonical_lang: zh-CN
source_layer: analysis
updated: {datetime.now().date()}
schema_version: wiki-skill-v1
---

# Analysis Overview

## Intake Summary

- Source root: `{source_root}`
- Total files inventoried: `{len(records)}`

## File Types

{lines}
"""


def build_inventory(records: List[FileRecord]) -> str:
    header = "| relative_path | ext | size | category | extracted | note |\n| --- | --- | ---: | --- | --- | --- |\n"
    rows = []
    for r in records:
        rows.append(f"| `{r.relative_path}` | `{r.extension}` | {r.size} | `{r.category}` | `{str(r.extracted).lower()}` | {r.note or '-'} |")
    return f"""---
title: Source Inventory
type: evidence-inventory
status: active
canonical_lang: zh-CN
source_layer: evidence
updated: {datetime.now().date()}
schema_version: wiki-skill-v1
---

# Source Inventory

{header}{os.linesep.join(rows)}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a small LLM wiki from a source folder.")
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--wiki-root")
    parser.add_argument("--canonical-lang", default="zh-CN")
    parser.add_argument("--mode", default="resource", choices=["project", "area", "resource", "temporary"])
    parser.add_argument("--profile", default="generic")
    parser.add_argument("--normalize-filenames", action="store_true")
    parser.add_argument("--custom-naming-template")
    parser.add_argument("--rerun-mode", default="refuse-with-report", choices=["refuse-with-report", "incremental-safe", "rebuild-to-new-sibling"])
    parser.add_argument("--enable-ocr", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.source_path).resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise SystemExit(f"source path does not exist or is not a directory: {source_path}")

    wiki_root = Path(args.wiki_root).resolve() if args.wiki_root else source_path.parent.resolve()
    if has_contract(wiki_root):
        if args.rerun_mode == "refuse-with-report":
            raise SystemExit(f"wiki contract already exists at {wiki_root}; rerun_mode=refuse-with-report")
        if args.rerun_mode == "rebuild-to-new-sibling":
            wiki_root = next_sibling_root(wiki_root)

    raw_dir = wiki_root / "raw"
    normalized_dir = wiki_root / "raw-normalized"
    analysis_dir = wiki_root / "analysis"
    evidence_dir = wiki_root / "evidence"
    ingest_dir = analysis_dir / "ingest-src"
    incremental_safe = args.rerun_mode == "incremental-safe"

    ensure_dir(wiki_root)
    ensure_dir(raw_dir)
    ensure_dir(analysis_dir)
    ensure_dir(evidence_dir)
    ensure_dir(ingest_dir)

    source_is_raw = source_path.resolve() == raw_dir.resolve()
    if not source_is_raw:
        copy_tree_contents(source_path, raw_dir)

    source_root = normalized_dir if args.normalize_filenames else raw_dir
    rename_map: Dict[str, str] = {}
    if args.normalize_filenames:
        rename_map = build_normalized_copy(raw_dir, normalized_dir, args.mode, args.custom_naming_template)
        source_root = normalized_dir

    records = inventory_files(source_root)
    records, skipped, uncertain = extract_sources(source_root, ingest_dir, records, args.enable_ocr)

    write_text(wiki_root / "index.md", build_index(wiki_root, records, args.canonical_lang, args.normalize_filenames), incremental_safe)
    if incremental_safe and (wiki_root / "log.md").exists():
        append_text(
            wiki_root / "log.md",
            f"\n\n## [{datetime.now().date()}] incremental-safe rerun\n- source_path: `{source_path}`\n- total_files: `{len(records)}`\n",
        )
    else:
        write_text(wiki_root / "log.md", build_log(records, source_path, args.rerun_mode), False)
    write_text(wiki_root / "AGENTS.md", build_agents(), incremental_safe)
    write_text(wiki_root / "LINTS.md", build_lints(), incremental_safe)
    write_text(wiki_root / "_meta.md", build_meta(), incremental_safe)
    write_text(analysis_dir / "overview.md", build_analysis_overview(records, source_root), incremental_safe)
    write_text(evidence_dir / "source-inventory.md", build_inventory(records), incremental_safe)

    summary = {
        "workspace_path": str(wiki_root),
        "source_path": str(source_path),
        "raw_path": str(raw_dir),
        "raw_normalized_path": str(normalized_dir) if args.normalize_filenames else None,
        "generated_pages": [
            str(wiki_root / name) for name in CORE_FILES
        ] + [str(analysis_dir / "overview.md"), str(evidence_dir / "source-inventory.md")],
        "rename_map_size": len(rename_map),
        "skipped_files": skipped,
        "uncertain_items": uncertain,
        "profile": args.profile,
        "mode": args.mode,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
