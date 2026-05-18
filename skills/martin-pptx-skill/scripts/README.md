# Scripts README

This folder describes reusable scripts expected for `martin-pptx-skill`. The scripts may be implemented incrementally, but they should use stable CLI contracts so a local agent can run the pipeline without copying one-off benchmark code.

## Script Inventory

| Script | Status | Purpose |
| --- | --- | --- |
| `decide_route.py` | implemented-v0 | Generate `output/route_decision.md` from scenario, output target, runtime availability, and editability requirement. |
| `build_imagegen_motherboard_prompts.py` | implemented-v0 | Generate per-slide image-gen prompts from `deck-outline.md` + `design.md` for the canonical high-quality visual motherboard. |
| `build_motherboard_from_outline.py` | implemented-v1-wireframe | Generate deterministic per-slide 16:9 wireframe/scaffold PNGs, contact sheet, PDF, and image-only PPTX from outline + design. This is not the canonical visual motherboard unless explicitly approved. |
| `build_option5_deck.py` | implemented-v0 | Build editable PPTX using Option 5: background master + Python editable reconstruction. |
| `bg_gate.py` | implemented-v0 | Check background master hygiene and produce `bg_gate_report.json`. |
| `render_pptx.py` | implemented-v0 | Export PPTX to PDF and PNG renders. |
| `make_contact_sheet.py` | implemented-v0 | Build contact sheet from slide PNGs. |
| `extract_pptx_text_metrics.py` | implemented-v0 | Extract text, fonts, notes, text/image shape counts. |
| `text_fidelity_gate.py` | implemented-v0 | Compare `deck-outline.md` to editable PPTX text layer. |
| `build_qc_report.py` | implemented-v0 | Roll up gate outputs into `qc_report.md`. |
| `verify_run_folder.py` | implemented-v0 | Validate canonical run folder and formal PPTX artifacts. |

## Dependency Policy

Main v0 route should not require cloud-only runtime.

Recommended local stack:

- Python 3.11+
- `python-pptx` or equivalent PPTX library
- LibreOffice or another local render/export path
- Pillow / image tooling for contact sheets
- optional OCR only as last resort; prefer deterministic extraction and visual render checks

Option 4 dependencies:

- `Presentations` / `artifact-tool` runtime if available.
- Must remain optional backup, not v0 hard dependency.

## CLI Contracts

### `decide_route.py`

```bash
python scripts/decide_route.py \
  --scenario formal-company-report \
  --target-output pptx,pdf \
  --editable-pptx-required true \
  --has-visual-motherboard true \
  --presentations-runtime available|unavailable \
  --out output/route_decision.md
```

Expected output:

```markdown
# Route Decision

- Main route: Option 5
- Backup route: Option 4 skipped/selected
- Rationale:
- Required gates:
- Stop condition:
```

### `build_imagegen_motherboard_prompts.py`

```bash
python scripts/build_imagegen_motherboard_prompts.py \
  --outline output/deck-outline.md \
  --design output/design.md \
  --out-dir output/motherboard_imagegen \
  --sample-slides 1,8,17
```

Expected outputs:

```text
output/motherboard_imagegen/prompts/slide_01_prompt.md ... slide_N_prompt.md
output/motherboard_imagegen/prompt_manifest.json
output/motherboard_imagegen/README.md
```

Expected behavior:

- Treat `deck-outline.md` as content/narrative SSOT.
- Treat `design.md` as visual system SSOT.
- Generate prompts for image-gen 16:9 text-included infographic slide references.
- Mark 2-3 representative slides for sample generation before full-deck generation.
- Preserve factual/evidence labels from the outline.
- Explicitly prohibit generic cyber imagery, crude wireframes, and tiny unreadable text.
- If image-gen is unavailable, stop after this prompt pack and report the capability blocker instead of substituting deterministic wireframes as the formal motherboard.

### `build_option5_deck.py`

```bash
python scripts/build_option5_deck.py \
  --outline output/deck-outline.md \
  --design output/design.md \
  --motherboard-dir output/motherboard_full \
  --background output/full_deck_option5/bg_masters/shared_bg_master.png \
  --out output/full_deck_option5/deck.pptx \
  --run-id YYYYMMDD_exp-xxx
```

Must not hardcode project-specific content.

Expected behavior:

- Parse outline slide contracts.
- Use reusable components.
- Rebuild critical text as editable shapes.
- Apply font policy.
- Save PPTX.

### `bg_gate.py`

```bash
python scripts/bg_gate.py \
  --background output/full_deck_option5/bg_masters/shared_bg_master.png \
  --mode formal-option5 \
  --out output/full_deck_option5/bg_gate_report.json
```

Expected JSON fields:

- status
- kept elements
- removed elements
- warnings
- failures
- review notes

### `render_pptx.py`

```bash
python scripts/render_pptx.py \
  --pptx output/full_deck_option5/deck.pptx \
  --out output/full_deck_option5/rendered
```

Expected outputs:

```text
rendered/deck.pdf
rendered/png/slide_01.png ... slide_N.png
rendered/render_log.txt
```

### `make_contact_sheet.py`

```bash
python scripts/make_contact_sheet.py \
  --images output/full_deck_option5/rendered/png \
  --out output/full_deck_option5/contact_sheet.png \
  --cols 3
```

Expected behavior:

- Preserve slide order.
- Add slide numbers if requested.
- Fail if any expected slide image is missing.

### `extract_pptx_text_metrics.py`

```bash
python scripts/extract_pptx_text_metrics.py \
  --pptx output/full_deck_option5/deck.pptx \
  --out output/full_deck_option5/text_extraction.json
```

Expected metrics:

- slide count
- total text shapes
- total image shapes
- text by slide
- font family / size
- speaker notes
- minimum / maximum font size

### `text_fidelity_gate.py`

```bash
python scripts/text_fidelity_gate.py \
  --outline output/deck-outline.md \
  --text-extraction output/full_deck_option5/text_extraction.json \
  --out output/full_deck_option5/text_fidelity_gate.md
```

Expected checks:

- slide count
- title fidelity
- evidence labels
- required terms
- forbidden terms
- semantic coverage
- factual mismatch indicators

### `build_qc_report.py`

```bash
python scripts/build_qc_report.py \
  --run-folder runs/YYYYMMDD_exp-xxx-short-slug \
  --out output/qc_report.md
```

Expected behavior:

- Read gate outputs.
- Produce pass/warn/fail summary.
- Identify blockers.
- Include recommended repair actions.

### `verify_run_folder.py`

```bash
python scripts/verify_run_folder.py \
  --run-folder runs/YYYYMMDD_exp-xxx-short-slug \
  --formal-pptx true
```

Expected behavior:

- Validate canonical file paths.
- Check required formal PPTX artifacts when applicable.
- Return non-zero exit code for missing blocking artifacts.

## Component Extraction Plan

Create a `components/` module for Option 5 builder:

```text
scripts/components/
  __init__.py
  theme.py
  text.py
  cards.py
  chips.py
  matrices.py
  timelines.py
  roadmaps.py
  background.py
  render_utils.py
```

Initial components:

- `add_slide_title()`
- `add_evidence_chip()`
- `add_two_column_contrast()`
- `add_policy_module_architecture()`
- `add_control_matrix()`
- `add_watchlist_table()`
- `add_roadmap()`
- `add_footer_metadata()`

## Script Quality Requirements

Each script should:

- Accept CLI args.
- Print clear pass/warn/fail summary.
- Write machine-readable output when possible.
- Avoid hardcoded benchmark paths.
- Return non-zero exit code for blocking failures.
- Log enough details for `handover.md`.
- Use deterministic behavior unless explicitly invoking image generation or optional runtime.

## Not Implemented Here

This design package defines script contracts and expected CLIs. It does not include production Python implementations. Local integration should implement these scripts by extracting and generalizing reusable experiment patterns.
