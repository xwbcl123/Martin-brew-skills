# D5 — martin-pptx-skill Handoff

## Header

```yaml
deliverable: D5-handoff
title: "{{PROJECT_NAME}} — Deck Production Handoff"
date: {{ISO_DATE}}
author: martin-outcome-package
target_skill: martin-pptx-skill
```

---

## Required Inputs for martin-pptx-skill

### brief.md / Source Material

**Objective**: {{OBJECTIVE}}

**Audience**: {{AUDIENCE_DESCRIPTION}}

**Source context**: {{SOURCE_CONTEXT}}

**Target use case**: {{USE_CASE}}

**Source deliverables**:
- D1 Deep Report: `{{PATH_TO_D1}}`
- D2 Executive Summary: `{{PATH_TO_D2}}`
- D4 Deck Outline: `{{PATH_TO_D4}}`

### scenario

`{{SCENARIO}}`

> One of: `formal-company-report`, `customer-communication`, `personal-creative`, `research-report`, `training-course`, or custom value with justification.

### language

`{{LANGUAGE}}`

> Default `zh-CN`; preserve canonical English technical terms.

### target output

`{{TARGET_OUTPUT}}`

> One of: `pptx`, `pdf`, `html`, `graphic`, `hybrid`.

### target slide count

`{{SLIDE_COUNT}}`

> Approximate for Stage 0; must be fixed before Stage 3 full visual motherboard.

### source index

{{SOURCE_INDEX_REFERENCE_OR_INLINE}}

> Required for evidence-heavy work. Every claim must trace to input material or be marked as assumption/inference. See D1 Source Index for full mapping.

### design.md

`{{PATH_TO_DESIGN_MD}}`

> Existing visual-system input authored by martin-outcome-package. Contains color tokens, typography, grid, component grammar, chart/table grammar, image direction, and negative rules.

### design-stack.md

`{{PATH_TO_DESIGN_STACK_MD}}`

> Existing top-level production/render constraint authored by martin-outcome-package. Contains target format, render toolchain, budget, accessibility, and brand constraints.

## Optional Inputs

| Input | Available | Path/Notes |
|-------|-----------|------------|
| Existing `deck-outline.md` | {{YES_NO}} | {{PATH_OR_NA}} |
| Brand guide / screenshots | {{YES_NO}} | {{PATH_OR_NA}} |
| Chart data / workbook | {{YES_NO}} | {{PATH_OR_NA}} |
| Reference deck or template PPTX | {{YES_NO}} | {{PATH_OR_NA}} |

## Known Gaps

> Items that martin-pptx-skill should resolve during its Stage 0.

{{KNOWN_GAPS_OR_NONE}}

## Delegation Notes

This handoff is complete. martin-pptx-skill should be able to start Stage 0 (Intake/Grill) without re-asking the questions answered above. If critical information is missing, it will be listed in Known Gaps.
