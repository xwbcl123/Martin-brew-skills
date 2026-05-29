# Artifact Schema

## Canonical Run Folder

```text
40_runs/YYYYMMDD_exp-xxx-short-slug/
├── input/
│   ├── brief.md
│   ├── source_index.md
│   └── known_gaps.md                # optional
├── output/
│   ├── design.md
│   ├── style-preview.html
│   ├── deck-outline.md
│   ├── deck-spec.md                 # required for Option 6
│   ├── visual-brief.html            # recommended
│   ├── route_decision.md            # required once Stage 4 starts
│   ├── motherboard_imagegen/
│   │   ├── prompts/slide_01_prompt.md
│   │   ├── prompts/slide_02_prompt.md
│   │   ├── ...
│   │   ├── prompt_manifest.json
│   │   └── README.md
│   ├── motherboard_sample/          # optional but recommended for complex decks
│   │   ├── slide_02.png
│   │   ├── slide_04.png
│   │   ├── slide_09.png
│   │   ├── contact_sheet_sample.png
│   │   └── qc_report_sample.md
│   ├── motherboard_full/
│   │   ├── slide_01.png
│   │   ├── slide_02.png
│   │   ├── ...
│   │   ├── contact_sheet.png
│   │   ├── full-preview.html        # optional
│   │   └── qc_report.md
│   ├── wireframe_motherboard/       # optional scaffold; not official unless approved
│   │   ├── slide_01.png
│   │   ├── ...
│   │   ├── contact_sheet.png
│   │   └── qc_report.md
│   ├── full_deck_option5/
│   │   ├── deck.pptx
│   │   ├── rendered/
│   │   │   ├── deck.pdf
│   │   │   └── png/slide_*.png
│   │   ├── bg_masters/
│   │   ├── contact_sheet.png
│   │   ├── bg_gate_report.json
│   │   ├── text_extraction.json
│   │   ├── text_fidelity_gate.md
│   │   └── qc_report.md
│   ├── backup_option4/              # optional independent backup
│   │   ├── deck.pptx
│   │   ├── layout.json
│   │   ├── rendered/
│   │   ├── contact_sheet.png
│   │   ├── scorecard.md
│   │   └── qc_report.md
│   ├── gamma_route/                 # Option 6 required when Gamma is available
│   │   ├── deck.pptx
│   │   ├── rendered/
│   │   ├── contact_sheet.png
│   │   ├── gamma_route.md
│   │   └── qc_report.md
│   ├── local_pptx_route/            # Option 6 local route
│   │   ├── deck.pptx
│   │   ├── rendered/
│   │   ├── contact_sheet.png
│   │   ├── text_extraction.json
│   │   └── qc_report.md
│   ├── optional_route_c/             # optional extra model/tool route
│   │   ├── deck.pptx
│   │   └── qc_report.md
│   ├── route_scorecard.md            # Option 6 route comparison
│   └── qc_report.md                  # final rollup
├── notes.md
├── verdict.md
└── handover.md
```

## `run_manifest.yaml`

Optional but recommended.

```yaml
run_id: YYYYMMDD_exp-xxx-short-slug
scenario: formal-company-report
language: zh-CN
target_output: [pptx, pdf]
editable_pptx_required: true
source_materials:
  - path: input/source-1.md
    type: official_fact
    status: available
stage_status:
  stage_0_intake: pass
  stage_1_design: pass
  stage_2_outline: pass
  stage_3_motherboard_prompts: pass
  stage_3_motherboard_sample: pending
  stage_3_motherboard_full: pending
  stage_4_route: pass
  stage_5_option5: in_progress
selected_routes:
  main: option5
  backup: option4_skipped_runtime_unavailable
mandatory_gates:
  bg_gate: pending
  text_fidelity_gate: pending
  render_gate: pending
  editability_gate: pending
human_reviews:
  design: approved
  outline: approved
  motherboard: pending
```

## `brief.md` Schema

```markdown
# Brief

## Run

- Run ID:
- Date:
- Owner:
- Scenario:
- Language:
- Target output:
- Editable PPTX required: yes/no
- Target slide count:

## Audience

## Objective

## Required Questions

1.
2.
3.

## Source Materials

| Source | Type | Path/URL | Usage | Notes |
| --- | --- | --- | --- | --- |

## Constraints

- Template / brand:
- Font policy:
- Deadline:
- Review cadence:

## Assumptions

## Known Gaps
```

## `source_index.md` Schema

```markdown
# Source Index

| ID | Source | Source Type | Reliability | Used In | Notes |
| --- | --- | --- | --- | --- | --- |
| S1 |  | official fact / media / stakeholder advocacy / provider statement / inference / open question / user reference | high/medium/low | Slide # |  |
```

## `design.md` Schema

Required sections:

1. Metadata.
2. Visual thesis.
3. Scenario and source basis.
4. Palette tokens and roles.
5. Typography and PPTX font policy.
6. Layout grammar.
7. Component grammar.
8. Chart/table grammar.
9. Image/icon direction.
10. Density/readability rules.
11. Negative rules.
12. Theme-library reuse notes.

## `deck-spec.md` Schema

Required for Option 6. `deck-spec.md` includes the full `design.md` contract plus additional production instructions.

Required sections:

1. Metadata and upstream references.
2. Global design system: visual thesis, palette, typography, grid, layout grammar, component grammar, chart/table grammar, image direction, negative rules, PPTX font policy.
3. Evidence label system and footer policy.
4. Per-slide production contract: layout template, text blocks, speaker notes, visual elements, artifact references, route notes.
5. Artifact plan: artifact IDs, mode (`full-slide-motherboard`, `component-kit`, `hybrid`, `textless-background`), prompt constraints, required outputs, batch order.
6. Image-generation policy: batch size, cooldown, text policy, forbidden visual elements, no-logo/no-flag/no-people constraints where relevant.
7. PPTX assembly policy: required routes, native text requirements, text fidelity expectations, fallback route rules.
8. QC gates: outline/spec consistency, motherboard gate, render gate, text fidelity gate, route scorecard.

Recommended template:

`templates/deck-spec-template.md`

## Option 6 ImageGen Artifact Schema

```text
motherboard_imagegen/
  prompts/
    slide_01_prompt.md
    slide_02_prompt.md
  prompt_manifest.json
  artifact_plan.md
motherboard_batches/
  batch_01/
    slide_01.png
    slide_02.png
    contact_sheet.png
    qc_report_batch_01.md
  batch_02/
    ...
motherboard_full/
  slide_01.png
  ...
  contact_sheet.png
  qc_report.md
component_kit/                       # optional
  backgrounds/
  icons/
  diagrams/
  panels/
```

Artifact modes:

| mode | contract |
|---|---|
| `full-slide-motherboard` | one 16:9 visual reference per slide |
| `component-kit` | reusable visual components for PPTX assembly |
| `hybrid` | full-slide images for visually important slides plus components for editable assembly |
| `textless-background` | image-gen backgrounds without business text; final text rebuilt natively |

## `deck-outline.md` Schema

Recommended frontmatter:

```yaml
type: deck-outline
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
version: stage2-v1
language: zh-CN
scenario: formal-company-report
audience: 
objective: 
source_materials_used: []
target_slide_count: 0
deck_status: not-generated
deck_link: ""
design_system: output/design.md
preview_artifact: output/visual-brief.html
evidence_policy: official facts, media claims, stakeholder advocacy, provider statements, inference, and open questions must remain separated
```

Per-slide schema:

```yaml
slide_number: 1
title: 
action_title: 
core_message: 
evidence:
  - type: official_fact
    claim: 
    source_id: 
content_blocks:
  - 
visual_intent: 
layout_hint: 
evidence_label: 
decision_questions: []
speaker_note_hint: 
downstream_generation_notes:
  motherboard_prompt: 
  pptx_notes: 
  required_terms: []
  forbidden_terms: []
```

## Visual Motherboard Schema

```text
motherboard_full/
  slide_01.png
  slide_02.png
  ...
  slide_N.png
  contact_sheet.png
  qc_report.md
  prompts/
    slide_01_prompt.md      # optional but recommended
```

`qc_report.md` must include:

- slide count
- image dimensions / aspect ratio
- missing slide check
- visual consistency notes
- readability notes
- alignment to `design.md`
- alignment to `deck-outline.md`
- human review status

## Option 5 PPTX Output Schema

```text
full_deck_option5/
  deck.pptx
  rendered/
    deck.pdf
    png/
      slide_01.png
      slide_02.png
      ...
  bg_masters/
    shared_bg_master.png
    section_*.png             # optional
  contact_sheet.png
  bg_gate_report.json
  text_extraction.json
  text_fidelity_gate.md
  qc_report.md
```

### `bg_gate_report.json`

```json
{
  "run_id": "",
  "background_master": "",
  "status": "pass",
  "kept_elements": ["header chrome", "footer chrome", "logo area", "background texture"],
  "removed_elements": ["body text", "proof objects", "charts", "cards", "labels"],
  "findings": [],
  "warnings": [],
  "failures": []
}
```

### `text_extraction.json`

```json
{
  "run_id": "",
  "pptx_path": "",
  "slide_count": 0,
  "total_text_shapes": 0,
  "total_image_shapes": 0,
  "min_font_pt": 0,
  "max_font_pt": 0,
  "slides": [
    {
      "slide_number": 1,
      "text_shapes": 0,
      "image_shapes": 0,
      "texts": [],
      "fonts": [],
      "notes": ""
    }
  ]
}
```

### `text_fidelity_gate.md`

Required sections:

- Summary: slides, pass, warn, fail.
- Gate rules.
- Slide results table.
- Details per warning/failure.
- Required repair actions.

## `qc_report.md` Schema

See `templates/qc-report-template.md`.

## `handover.md` Schema

See `templates/handover-template.md`.
