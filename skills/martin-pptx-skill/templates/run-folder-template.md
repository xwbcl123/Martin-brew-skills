# Run Folder Template

Use this template for every real `martin-pptx-skill` run.

## Folder Name

```text
runs/YYYYMMDD_exp-xxx-short-slug/
```

Examples:

```text
runs/YYYYMMDD_exp-008-chart-heavy-business-review/
runs/YYYYMMDD_exp-009-customer-english-briefing/
```

## Required Structure

```text
runs/YYYYMMDD_exp-xxx-short-slug/
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
