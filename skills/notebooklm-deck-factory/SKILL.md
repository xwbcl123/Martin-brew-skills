---
name: notebooklm-deck-factory
description: "Generate a quick alternate deck with NotebookLM from a source bundle, deck-outline.md, and design.md/theme brief. Use for customer briefings, research decks, visual route comparison, or NotebookLM 快速生成 deck workflows. Produces a local run package with sources, prompt, notebook/artifact manifests, PPTX/PDF downloads, render evidence, and explicit editability QC; do not use as the final formal editable PPTX route unless image-baked output is acceptable."
---

# NotebookLM Deck Factory

## Purpose

Create a fast NotebookLM-generated deck route as an auditable alternate, not a replacement for `martin-pptx-skill` formal editable PPTX workflows.

Use this for speed, visual inspiration, and route comparison. Always label the output honestly: NotebookLM slide-deck exports may be image-baked.

## Required Inputs

- Source bundle: research reports, synthesis, notes, or PDFs.
- Narrative source of truth: `deck-outline.md` or equivalent.
- Visual source: `design.md`, theme brief, or reference deck/theme metadata.
- Output root: a project-local `notebooklm-output/<run_id>/` folder.

Use this skill's `references/deck-outline-template.md` and `references/design-template.md` when the input outline or design brief is missing, loose, or not optimized for NotebookLM.

Cross-reference the canonical deck rules when quality matters:

- `.claude/commands/deck-outline.md` for Martin's board/customer outline style.
- `.agents/skills/martin-pptx-skill/templates/deck-outline-template.md` for formal slide production contracts.
- `.agents/skills/martin-pptx-skill/templates/design-template.md` for full `design.md` grammar.

For Gamma themes, fetch theme metadata when available and translate it into this skill's NotebookLM `design.md` template.

## Workflow

1. Verify CLI and auth.
   - Prefer `pipx install notebooklm-py` when `notebooklm` is missing.
   - Run `notebooklm --version`, `notebooklm auth check`, and `notebooklm list --json`.
   - Use explicit notebook IDs in all commands; avoid relying on `notebooklm use`.

2. Create the run package.
   - Use the structure in `references/run-package.md`.
   - Copy sources into `input/`; do not mutate originals.
   - Create `source_index.md`, `README.md`, and `handover.md`.

3. Create or normalize the outline and design inputs.
   - If the supplied outline is not slide-by-slide, normalize it with `references/deck-outline-template.md`.
   - If the design system is missing or vague, create `design/<theme>-design.md` from `references/design-template.md`.
   - Keep `deck-outline.md` and `design.md` separate.

4. Create or normalize design instructions.
   - Store as `design/<theme>-design.md`.
   - Include visual tone, palette roles, typography, slide archetypes, negative rules, and NotebookLM-specific style instructions.
   - State the target output language.

5. Create the notebook and import sources.
   - Create a clear notebook title with project + date.
   - Add sources with `notebooklm source add -n <notebook_id> --type file <path> --json`.
   - Wait until every source is `ready`.
   - Save notebook ID and source IDs in `notebook/notebook_manifest.json`.

6. Generate the slide deck.
   - Save the prompt as `prompt/generate_slide_deck_prompt.md`.
   - Require: follow deck-outline structure; use reports only as evidence backing; follow design file; avoid unsupported claims.
   - Run `notebooklm generate slide-deck -n <notebook_id> --prompt-file <prompt> --format detailed --length default --language <lang> --wait --timeout 900 --interval 15 --retry 1 --json`.
   - If rate-limited or timed out, check `notebooklm artifact list -n <notebook_id> --json` before retrying.

7. Download and QA.
   - Download PPTX and PDF with explicit artifact ID.
   - Run `zip -T` on PPTX.
   - Render PPTX to PDF with LibreOffice and check page count.
   - Render sample PNGs and, when useful, all slides.
   - Inspect OOXML for editable text: count `a:t` text nodes and `p:pic` picture nodes.
   - Write `qa/qc_report.md` and `notebook/artifact_manifest.json`.

## Hard Gates

- Source gate fails if any required source is not `ready`.
- Artifact gate fails if no completed Slide Deck artifact exists.
- Render gate fails if PPTX cannot export to PDF or page counts mismatch.
- Editability gate must be explicit:
  - `text_nodes > 0` means partial/native text may exist.
  - `text_nodes = 0` and one picture per slide means image-baked PPTX.
  - Image-baked output can be useful, but must not be called formal editable PPTX.

## Output Labels

Use one of these verdicts in `qc_report.md`:

- `ready`: generation and QA passed; limitations are minor.
- `ready-with-warnings`: usable alternate route, but has limitations such as image-baked output, watermark, or minor content roughness.
- `blocked`: generation, download, source readiness, or render failed.

## Common Commands

```bash
notebooklm create "<title>" --json
notebooklm source add -n <notebook_id> --type file "<path>" --json
notebooklm source list -n <notebook_id> --json
notebooklm generate slide-deck -n <notebook_id> --prompt-file prompt/generate_slide_deck_prompt.md --format detailed --length default --language en --wait --timeout 900 --interval 15 --retry 1 --json
notebooklm artifact list -n <notebook_id> --json
notebooklm download slide-deck -n <notebook_id> -a <artifact_id> --format pptx --force deck/output.pptx --json
notebooklm download slide-deck -n <notebook_id> -a <artifact_id> --format pdf --force qa/output.pdf --json
```

## Retrospective Lesson

From the 2026-06-17 Telefónica GCTIO Mythos run: NotebookLM produced a strong Sage-like 15-slide deck quickly, but the PPTX contained `text_nodes=0` and `pictures=15`. The right default is to treat NotebookLM as a rapid visual alternate and always run editability QC before recommending it for customer use.
