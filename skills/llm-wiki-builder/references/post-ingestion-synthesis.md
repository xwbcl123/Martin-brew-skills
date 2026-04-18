# Post-Ingestion Synthesis

Use this after `scripts/build_wiki.py` finishes. The script creates the scaffold; this phase turns the scaffold into a real wiki.

## Role

Act as a knowledge architect. The goal is a source-linked knowledge network, not a prettier file tree. A reader should be able to scan `index.md`, understand the core thesis, choose a semantic route, and drill down to the exact source file behind each claim.

## Semantic MoC Rules

- Derive MoC categories from the actual input files.
- Do not copy another wiki's category structure unless the input structure genuinely matches it.
- Use benchmark wikis for quality expectations, not taxonomy decisions.
- Prefer business or research logic over filename order.
- Keep root MoC pages few and high-signal.

Every MoC entry should include:

- a Markdown link to the source in `raw-normalized/` when present, otherwise `raw/`
- one or two sentences of summary, interpretation, or relevance
- enough context for click-free value

## Index and Overview

Rewrite `index.md` so it contains:

- a domain-specific title
- a core thesis
- root-level MoC routes with short explanations
- links to governance and evidence pages

Rewrite `analysis/overview.md` so it contains:

- the major themes
- event line or issue map when applicable
- strategic implications or key findings
- explicit links to source files or MoC pages

Do not leave these as file-count summaries unless the user explicitly asked only for inventory.

## Coverage QC

Before final handoff:

1. List every in-scope file from `raw-normalized/` if it exists, otherwise from `raw/`.
2. List every source file linked from root MoC pages.
3. Compare both lists.
4. Add missing files to the appropriate MoC, or mark them explicitly excluded with a reason.

Go/no-go:

- MoC coverage must be 100%.
- Omitted in-scope files must be zero.
- `Core Thesis`, `Coverage QC`, and `Cross-linking` are hard gates.
