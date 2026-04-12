---
name: llm-wiki-builder
description: Convert a source folder into a governed small LLM wiki with `raw/`, `raw-normalized/`, `analysis/`, `evidence/`, `index.md`, `AGENTS.md`, `LINTS.md`, and `_meta.md`. Use when Codex needs to bootstrap or refresh a folder-based knowledge base from mixed source files such as Markdown, PDF, DOCX, PPTX, images, spreadsheets, or archives, while preserving source safety via copy-first ingestion.
---

# LLM Wiki Builder

## Overview

Bootstrap a small governed wiki from a source folder without mutating the source in place. The skill creates a wiki root, ingests sources into `raw/`, optionally creates a renamed working copy in `raw-normalized/`, extracts text where feasible, and generates base governance pages plus initial analysis/evidence pages.

## Quick Start

Run the bootstrap script:

```powershell
python skills/llm-wiki-builder/scripts/build_wiki.py `
  --source-path "20 Projects/example/10_raw" `
  --mode project `
  --canonical-lang zh-CN `
  --normalize-filenames
```

Useful options:

```powershell
--wiki-root "<path>"                      # Override wiki root; default is source parent
--rerun-mode refuse-with-report          # refuse-with-report | incremental-safe | rebuild-to-new-sibling
--custom-naming-template "<template>"    # Override default template
--enable-ocr                             # Try OCR-ready images only if extraction backend exists
--profile generic                        # Base bootstrap profile; future profiles may extend this
```

## Workflow

1. Read [references/base-contract.md](references/base-contract.md) to understand the directory contract and rerun safety.
2. Read [references/file-type-matrix.md](references/file-type-matrix.md) to understand parse vs copy-only behavior.
3. Run `scripts/build_wiki.py`.
4. Review the generated:
   - `index.md`
   - `log.md`
   - `AGENTS.md`
   - `LINTS.md`
   - `_meta.md`
   - `analysis/overview.md`
   - `evidence/source-inventory.md`
5. If the environment supports terminal delegation, use [workflows/multi-agent-delegation.md](workflows/multi-agent-delegation.md) for bounded chores such as frontmatter cleanup, extraction review, or link cleanup.

## What The Script Does

- Builds or probes a wiki root with `raw/`, `analysis/`, and `evidence/`
- Preserves source safety through copy-first ingestion
- Creates `raw-normalized/` only when filename normalization is enabled
- Extracts text from supported files using `markitdown` when available
- Records rename mappings and skipped/uncertain items
- Generates a generic governance bootstrap, not a project-specific profile

## Rerun Rules

- Default rerun mode is `refuse-with-report`
- `incremental-safe` may add missing pages and append logs, but does not overwrite existing core pages
- `rebuild-to-new-sibling` writes to a sibling wiki root, such as `foo-wiki-v2`
- Never use this skill to destructively merge or overwrite an existing wiki without an explicit user request

## Multi-Agent Guidance

This skill does not require WezTerm or tmux, but can use them as optional execution backends.

Good delegation targets:

- inventory review
- frontmatter cleanup
- extraction QA
- link cleanup

Keep synthesis, profile choice, and final acceptance with the main agent.
