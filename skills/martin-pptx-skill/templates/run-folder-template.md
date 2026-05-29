# Run Folder Template

Use this template for every real `martin-pptx-skill` run.

## Folder Name

```text
40_runs/YYYYMMDD_exp-xxx-short-slug/
```

Examples:

```text
40_runs/20260518_exp-008-chart-heavy-business-review/
40_runs/20260519_exp-009-customer-english-briefing/
```

## Required Structure

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
│   ├── visual-brief.html            # recommended
│   ├── route_decision.md            # required after route selection
│   ├── motherboard_sample/          # optional
│   ├── motherboard_full/
│   ├── full_deck_option5/           # required for formal PPTX
│   ├── backup_option4/              # optional backup
│   └── qc_report.md                 # final rollup
├── notes.md
├── verdict.md
└── handover.md
```

## Option 6 Structure

Use this structure when the selected route is `Option 6 — Four-Step ImageGen Multi-Route Deck Factory`.

```text
40_runs/YYYYMMDD_exp-xxx-short-slug/
├── input/
│   ├── brief.md
│   ├── source_index.md
│   └── known_gaps.md
├── output/
│   ├── deck-outline.md
│   ├── deck-spec.md
│   ├── motherboard_imagegen/
│   │   ├── artifact_plan.md
│   │   ├── prompt_manifest.json
│   │   └── prompts/
│   │       └── slide_01_prompt.md
│   ├── motherboard_batches/
│   │   └── batch_01/
│   │       ├── slide_01.png
│   │       ├── contact_sheet.png
│   │       └── qc_report_batch_01.md
│   ├── motherboard_full/
│   │   ├── slide_01.png
│   │   ├── contact_sheet.png
│   │   ├── motherboard.pdf
│   │   └── qc_report.md
│   ├── component_kit/               # optional; required for hybrid/component-kit mode
│   ├── gamma_route/
│   │   ├── deck.pptx
│   │   ├── rendered/
│   │   ├── contact_sheet.png
│   │   └── qc_report.md
│   ├── local_pptx_route/
│   │   ├── deck.pptx
│   │   ├── rendered/
│   │   ├── contact_sheet.png
│   │   ├── text_extraction.json
│   │   ├── text_fidelity_gate.md
│   │   └── qc_report.md
│   ├── optional_route_c/
│   ├── route_scorecard.md
│   └── qc_report.md
├── notes.md
├── verdict.md
└── handover.md
```

Option 6 template mapping:

| output | template |
| --- | --- |
| `output/deck-outline.md` | `templates/option6-deck-outline-template.md` |
| `output/deck-spec.md` | `templates/deck-spec-template.md` |
| `output/motherboard_imagegen/artifact_plan.md` | `templates/imagegen-artifact-plan-template.md` |
| `output/route_scorecard.md` | `templates/multi-route-assembly-qc-template.md` |

## `input/brief.md` Starter

```markdown
# Brief

## Run

- Run ID:
- Date:
- Owner:
- Scenario:
- Language:
- Target output:
- Editable PPTX required:
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

## `input/source_index.md` Starter

```markdown
# Source Index

| ID | Source | Type | Reliability | Used In | Notes |
| --- | --- | --- | --- | --- | --- |
| S1 |  | official fact / media / stakeholder advocacy / provider statement / inference / open question / user reference |  |  |  |
```

## `notes.md` Starter

```markdown
# Notes

## Run Log

| Time | Stage | Note | Decision / Action |
| --- | --- | --- | --- |

## Defect Register

| ID | Stage | Defect | Severity | Status | Fix |
| --- | --- | --- | --- | --- | --- |

## Human Feedback

| Reviewer | Artifact | Feedback | Decision |
| --- | --- | --- | --- |
```

## `verdict.md` Starter

```markdown
# Verdict

## Run Summary

- Run ID:
- Scenario:
- Target output:
- Final artifact:
- Status: pass / warn / fail / in-progress

## Stage Verdicts

| Stage | Status | Evidence | Next Action |
| --- | --- | --- | --- |
| Stage 0 Intake |  |  |  |
| Stage 1 Design |  |  |  |
| Stage 2 Outline |  |  |  |
| Stage 3 Motherboard |  |  |  |
| Stage 4 Route |  |  |  |
| Stage 5 Option 5 |  |  |  |
| Stage 6 Backup |  |  |  |
| Stage 7 Handover |  |  |  |

## Final Recommendation
```

## `handover.md` Starter

Use `templates/handover-template.md`.

## Formal PPTX Output Folder Starter

```text
output/full_deck_option5/
├── deck.pptx
├── rendered/
│   ├── deck.pdf
│   └── png/slide_*.png
├── bg_masters/
├── contact_sheet.png
├── bg_gate_report.json
├── text_extraction.json
├── text_fidelity_gate.md
└── qc_report.md
```
