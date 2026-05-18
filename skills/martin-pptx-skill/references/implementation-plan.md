# Implementation Plan

## Objective

Promote the current `martin-pptx-skill` candidate from experiment notes into a reusable local skill that can be executed by a fresh coding agent without old chat history.

## Milestone 1 — Replace Candidate Contract

Target:

```text
skills/martin-pptx-skill/SKILL.md
```

Actions:

1. Replace or merge current candidate with this package's `SKILL.md`.
2. Add the `references/` and `templates/` folders.
3. Preserve existing candidate insights, but make Option 5 main route explicit.
4. Add formal trigger conditions, inputs, stage workflow, gates, failure modes, and promotion criteria.

Exit criteria:

- A fresh agent can follow the skill without reading old chats.
- The skill explicitly says it is a `deck engineering pipeline orchestrator`.
- `design.md`, `deck-outline.md`, and `visual motherboard` are defined as separate artifacts.

## Milestone 2 — Add Canonical Run Schema

Target:

```text
runs/YYYYMMDD_exp-xxx-short-slug/
```

Actions:

1. Adopt `templates/run-folder-template.md`.
2. Add optional `run_manifest.yaml` support.
3. Update `scripts/verify_scaffold.py` to check run folders for:
   - `input/brief.md`
   - `input/source_index.md`
   - `output/design.md`
   - `output/deck-outline.md`
   - `notes.md`
   - `verdict.md`
   - `handover.md`
4. Add extra checks for formal PPTX runs:
   - `output/full_deck_option5/deck.pptx`
   - render PDF/PNG
   - `contact_sheet.png`
   - `bg_gate_report.json`
   - `text_extraction.json`
   - `text_fidelity_gate.md`
   - `qc_report.md`

Exit criteria:

- New run folders can be verified with one command.
- Missing formal artifacts produce clear errors.

## Milestone 3 — Extract Reusable Scripts

Extract one-off reusable experiment patterns into reusable scripts.

| Reusable Pattern | Target Script | Purpose |
| --- | --- | --- |
| Image-gen motherboard prompt builder | `scripts/build_imagegen_motherboard_prompts.py` | Produce canonical per-slide image-gen prompts from outline + design for high-quality 16:9 infographic motherboard images. |
| Wireframe motherboard builder | `scripts/build_motherboard_from_outline.py` | Produce deterministic 16:9 scaffold visuals and contact sheet from outline + design. These are scaffolds, not official motherboard outputs unless explicitly approved. |
| Full Option 5 deck builder | `scripts/build_option5_deck.py` | Generate editable PPTX from outline, design, approved motherboard, and background master. |
| Text fidelity runner | `scripts/text_fidelity_gate.py` | Compare outline with PPTX text layer. |
| PPTX text extraction | `scripts/extract_pptx_text_metrics.py` | Extract text, font, notes, and shape metrics. |
| Contact sheet generation | `scripts/make_contact_sheet.py` | Build contact sheet from slide PNGs. |
| Background hygiene report | `scripts/bg_gate.py` | Validate background master against allowed/forbidden content. |
| PPTX render wrapper | `scripts/render_pptx.py` | Export PPTX to PDF/PNG using available local tools. |
| QC rollup | `scripts/build_qc_report.py` | Combine gate outputs into `qc_report.md`. |
| Route decision helper | `scripts/decide_route.py` | Generate `route_decision.md` from scenario and target output. |

Exit criteria:

- Scripts accept CLI args and do not hardcode project-specific paths.
- A second benchmark can run without copying prior experiment files.
- Script README documents dependencies and expected outputs.
- Formal PPTX runs cannot be marked full benchmark pass unless image-gen motherboard prompts exist, image-gen sample/full motherboard images are generated and approved, and `motherboard_full/` exists before PPTX reconstruction.

## Milestone 4 — Build Component Library for Option 5

Target:

```text
skills/martin-pptx-skill/scripts/components/
```

Suggested components:

- `title_band`
- `evidence_chip`
- `two_column_contrast`
- `policy_architecture_modules`
- `four_quadrant_matrix`
- `stakeholder_bubble_map`
- `control_matrix`
- `timeline`
- `roadmap`
- `watchlist_table`
- `footer_metadata`

Exit criteria:

- Option 5 builder uses reusable components.
- Dense slides can be adjusted by component parameters rather than hand-coded per slide.

## Milestone 5 — Implement Gate CLIs

### BG Gate CLI

```bash
python scripts/bg_gate.py \
  --background output/full_deck_option5/bg_masters/shared_bg_master.png \
  --mode formal-option5 \
  --out output/full_deck_option5/bg_gate_report.json
```

Minimum output:

- status
- kept elements
- removed elements
- warnings
- failures
- human review note

### Text Fidelity Gate CLI

```bash
python scripts/text_fidelity_gate.py \
  --outline output/deck-outline.md \
  --text-extraction output/full_deck_option5/text_extraction.json \
  --out output/full_deck_option5/text_fidelity_gate.md
```

Minimum checks:

- slide count
- title fidelity
- evidence labels
- required terms
- forbidden terms
- semantic coverage
- factual mismatch notes

### Render QC CLI

```bash
python scripts/render_pptx.py \
  --pptx output/full_deck_option5/deck.pptx \
  --out output/full_deck_option5/rendered
```

Minimum outputs:

- PDF
- PNG per slide
- render log

Exit criteria:

- Gate outputs are deterministic enough for review.
- Any `fail` blocks final delivery.

## Milestone 6 — Add Benchmarks

Use a sanitized dense-policy benchmark as one example. Add at least three total benchmark runs before promotion.

Recommended benchmark set:

| Benchmark | Why | Required Route |
| --- | --- | --- |
| Dense policy / regulatory deck | Stress evidence discipline and Text Fidelity Gate | Option 5 |
| Chart-heavy business review | Stress charts/tables and readability | Option 5 + Option 1 fallback |
| Customer-facing English deck | Stress external polish and concise language | HTML/PDF + optional Option 4 |
| Personal/creative visual essay | Stress non-PPTX stop condition | Stage 3 / HTML / PDF |

Exit criteria:

- At least 3 full runs.
- At least 2 formal PPTX runs.
- No mandatory gate failures in accepted formal runs.

## Milestone 7 — Promotion Decision

Promotion status path:

```text
lab_candidate -> candidate_ready_for_review -> ready_for_promotion -> promoted_skill
```

Promotion requirements:

- `SKILL.md` is self-contained.
- References and templates are installed.
- Reusable scripts exist for Option 5, BG Gate, Text Fidelity Gate, render QC, contact sheet.
- Multiple benchmarks are logged.
- Acceptance review passes.
- Known limitations are recorded in a sanitized review note.

## Local Integration Checklist

```bash
# 1. Copy the reusable package into the skill directory.
cp -R <sanitized-skill-package>/* skills/martin-pptx-skill/

# 2. Verify repository scaffold.
python3 scripts/verify_scaffold.py

# 3. Create next run from template.
mkdir -p runs/YYYYMMDD_exp-xxx-short-slug/{input,output}
cp skills/martin-pptx-skill/templates/run-folder-template.md \
  runs/YYYYMMDD_exp-xxx-short-slug/README.md

# 4. Run next benchmark using this skill contract.
# Fill input/brief.md and input/source_index.md first.

# 5. After formal PPTX build, run gates.
python skills/martin-pptx-skill/scripts/extract_pptx_text_metrics.py --help
python skills/martin-pptx-skill/scripts/text_fidelity_gate.py --help
python skills/martin-pptx-skill/scripts/bg_gate.py --help
```

## Risks and Mitigations

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Option 5 remains too bespoke | high | Extract component library and builder parameters. |
| Background cleanup variance | medium | Prefer approved shared master; enforce BG Gate; fallback Option 1. |
| Text compression changes meaning | high | Keep Text Fidelity Gate mandatory. |
| HTML-first export fidelity | medium | Keep Option 3 as v1 R&D, not v0 main. |
| Option 4 runtime unavailable | medium | Treat as optional backup only. |
| Chinese font variance | medium | Render QC and formal font policy. |
| User accepts visual artifact too early for formal PPTX | high | Enforce formal scenario stop condition. |
