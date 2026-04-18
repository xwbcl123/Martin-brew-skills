---
name: llm-wiki-builder
description: Convert a source folder into a governed, navigable LLM wiki with safe source ingestion, semantic Map of Content pages, source-linked summaries, coverage QC, and governance files. Use this whenever Codex needs to bootstrap, refresh, or turn a folder of Markdown, PDF, DOCX, PPTX, NotebookLM exports, deep research notes, images, spreadsheets, archives, or mixed research material into a traceable knowledge base, not just a copied file inventory.
---

# LLM Wiki Builder

## Overview

Build a small governed wiki from a source folder without mutating the source in place. The skill first creates a safe scaffold, then turns that scaffold into a useful knowledge network.

Your role is not only to run a file organization script. Act as a knowledge architect: preserve the original evidence, extract what is machine-readable, read the important materials, synthesize the domain meaning, and create a wiki where the reader can move from a high-level thesis to source-level evidence through links.

The script output is a bootstrap, not the final deliverable. A complete run includes semantic synthesis, root-level Map of Content (MoC) pages, source-linked summaries, and coverage QC.

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
3. Run `scripts/build_wiki.py` for controlled ingestion.
4. Read [references/post-ingestion-synthesis.md](references/post-ingestion-synthesis.md), then complete the mandatory semantic synthesis phase.
5. Review the generated scaffold:
   - `index.md`
   - `log.md`
   - `AGENTS.md`
   - `LINTS.md`
   - `_meta.md`
   - `analysis/overview.md`
   - `evidence/source-inventory.md`
6. Rewrite `index.md` and `analysis/overview.md` into domain-specific synthesis pages.
7. Create root-level MoC pages from the actual input semantics. Do not copy another wiki's categories unless the input structure truly matches them.
8. Cross-link every material summary or claim back to `raw-normalized/` or `raw/`.
9. Run coverage QC: compare MoC coverage against the source inventory and fix omissions before final handoff.
10. If the environment supports delegation, use [workflows/multi-agent-delegation.md](workflows/multi-agent-delegation.md) for bounded parallel work such as inventory clustering, source sampling, and coverage QC.

## What The Script Does

- Builds or probes a wiki root with `raw/`, `analysis/`, and `evidence/`
- Preserves source safety through copy-first ingestion
- Creates `raw-normalized/` only when filename normalization is enabled
- Extracts rich/binary files using `markitdown` when available
- Treats native text such as Markdown and TXT as directly readable source-layer material instead of duplicating it into `analysis/ingest-src/`
- Records rename mappings and skipped/uncertain items
- Generates a generic governance bootstrap, not a project-specific profile

## Mandatory Semantic Synthesis

After controlled ingestion, complete these steps before claiming the wiki is done:

1. Read the inventory and sample enough important files from `raw-normalized/` or `raw/` to understand the domain.
2. Infer semantic clusters from the actual input files. Benchmark structures such as `10_original-documents`, `20_notebooklm-analysis`, and `30_deep-research` are examples, not templates.
3. Rewrite `index.md` with a core thesis, high-level MoC, and short descriptions of the major routes.
4. Rewrite `analysis/overview.md` with an actual domain summary, not only file counts.
5. Create root-level MoC pages whose entries include:
   - a link to the source file
   - one or two sentences of summary or interpretation
   - ordering that reflects business or research logic, not filename sort
6. Run coverage QC. MoC coverage must be 100% for the files in scope, with zero omitted files.

Acceptance hard gates:

- `Core Thesis`: the index states the domain-specific central argument.
- `Coverage QC`: every in-scope source appears in a MoC or is explicitly excluded with a reason.
- `Cross-linking`: summary claims can be traced to source files.

## Rerun Rules

- Default rerun mode is `refuse-with-report`
- `incremental-safe` may add missing pages and append logs, but does not overwrite existing core pages
- `rebuild-to-new-sibling` writes to a sibling wiki root, such as `foo-wiki-v2`
- Never use this skill to destructively merge or overwrite an existing wiki without an explicit user request

## Multi-Agent Guidance

This skill does not require WezTerm or tmux, but can use them as optional execution backends.

Good delegation targets:

- inventory review
- semantic clustering candidates
- source sampling and thesis extraction
- extraction QA
- MoC coverage QC
- link cleanup

Keep synthesis, profile choice, and final acceptance with the main agent.
