# martin-pptx-skill Delegation

## Purpose

This document defines how `martin-outcome-package` delegates deck production to `martin-pptx-skill`. The handoff must be complete enough that `martin-pptx-skill` can start its Stage 0 without re-asking basic intake questions.

## Required Inputs Mapping

The `d5-martin-pptx-handoff-template.md` must provide all required inputs for `martin-pptx-skill`:

| martin-pptx-skill Required Input | Source in Outcome Package | Notes |
|---|---|---|
| `brief.md` / source material | D1 deep report + D2 exec summary + D4 deck outline | Objective, audience, source context, target use case extracted from these deliverables |
| `scenario` | Determined during intake grill | One of: `formal-company-report`, `customer-communication`, `personal-creative`, `research-report`, `training-course`, or custom |
| `language` | Determined during intake grill | Default `zh-CN`; preserve canonical English technical terms |
| `target output` | Determined during intake grill | `pptx`, `pdf`, `html`, `graphic`, or `hybrid` |
| `target slide count` | Estimated from D4 deck outline | Approximate is acceptable for Stage 0; must be fixed before full visual motherboard |
| `source index` | Built from D1 source references | Required for evidence-heavy work; every claim traces to input or marked assumption |
| `design.md` | D5 `design.md` authored by this Skill | Visual system SSOT |
| `design-stack.md` | D5 `design-stack.md` authored by this Skill | Top-level production/render contract |

## Optional Inputs

| martin-pptx-skill Optional Input | Source | Notes |
|---|---|---|
| Existing `deck-outline.md` | D4 output | Validate, normalize, use as narrative SSOT |
| Brand guide / screenshots | External input captured during intake | Pass through if available |
| Chart data / workbook | External input captured during intake | Feed chart/table generation |
| Reference deck or template PPTX | External input captured during intake | Extract theme rules |

## Delegation Protocol

1. Complete D1-D4 before starting D5.
2. Author `design.md` and `design-stack.md` using templates.
3. Fill `martin-pptx-handoff.md` with all required fields mapped above.
4. Verify handoff completeness: all required fields populated, no TBD placeholders for required items.
5. The handoff file itself is the delegation trigger. No additional coordination protocol needed.

## What This Skill Does NOT Do

- Does not create `deck-spec.md` (martin-pptx-skill Stage 1-2 output)
- Does not generate slide artifacts (martin-pptx-skill Stage 3-4 output)
- Does not produce PPTX files (martin-pptx-skill Stage 4-5 output)
- Does not modify design.md/design-stack.md after handoff (unless explicitly re-triggered)
