---
name: martin-outcome-package
description: Use when Martin wants to turn a transcript, .req.md, Inbox capture, session, or fuzzy task into a portable six-deliverable outcome package with grill-me intake, context discovery, deliverable_home routing, D1-D6 outputs, DesignMD/DesignStack planning, and optional delegation to martin-pptx-skill for deck-spec, artifacts, and PPTX production. Use this skill for outcome-package, delivery-package, executive-report-plus-deck, transcript-to-deliverables, and new task-session packaging requests, even if Martin does not explicitly say "skill".
aspg:
  origin:
    vendor: custom
    imported_at: 2026-06-03
---

# Martin Outcome Package

Turn any source material into a portable six-deliverable outcome package.

## Contract

Six deliverables, produced sequentially. D1+D2 are mandatory; D3-D6 are gated by intake.

| ID | Deliverable | Format | Required |
|----|-------------|--------|----------|
| D1 | Deep Report | Markdown (8400-12000 字) | Yes |
| D2 | Executive Summary | Markdown (800-2000 字) | Yes |
| D3 | Visual Briefing | HTML + assets | No |
| D4 | Deck Outline & Brief | Markdown | No |
| D5 | Design System + Handoff | `design.md` + `design-stack.md` + `martin-pptx-handoff.md` | No |
| D6 | Email Package | Markdown | No |

## Mandatory Gates

1. **Intake before production.** Run the intake grill (see `references/intake-grill.md`) unless the source already answers all required questions.
2. **deliverable_home captured.** Resolve output directory before writing any deliverable (see `references/output-routing.md`).
3. **D5 ownership.** This Skill is the single author of `design.md`, `design-stack.md`, and `martin-pptx-handoff.md`. Do not create `deck-spec.md` — that belongs to `martin-pptx-skill`.
4. **Portability.** Runtime instructions must not depend on paths outside this Skill folder (see `references/portability.md`).
5. **Package README.** Every completed package must have a `README.md` with structured metadata.

## Quick Workflow

1. **Intake**: Identify source material. Run grill if ambiguous. Capture intake metadata. Resolve `deliverable_home`.
2. **D1 — Deep Report**: Analyze source material. Produce comprehensive report using `templates/d1-deep-report-template.md`. Include source references and evidence tracking.
3. **D2 — Executive Summary**: Distill D1 into executive-level summary using `templates/d2-executive-summary-template.md`.
4. **D3 — Visual Briefing** (if needed): Generate HTML visual briefing using `templates/d3-visual-briefing-template.md`. Use bundled style defaults; optional brand-style input accepted but not required.
5. **D4 — Deck Outline** (if needed): Produce structured deck outline using `templates/d4-deck-outline-brief-template.md`.
6. **D5 — Design System + Handoff** (if D4 produced):
   - Author `design.md` using `templates/d5-design-md-template.md`
   - Author `design-stack.md` using `templates/d5-design-stack-template.md`
   - Author `martin-pptx-handoff.md` using `templates/d5-martin-pptx-handoff-template.md`
   - See `references/d5-design-pipeline.md` and `references/martin-pptx-delegation.md`
7. **D6 — Email Package** (if needed): Draft stakeholder email using `templates/d6-email-package-template.md`.
8. **Package README**: Generate package metadata using `templates/package-readme-template.md`.

## References

Read on demand:

| Need | Read |
|------|------|
| Package shape, D5 boundary, degradation | `references/package-contract.md` |
| Intake interview protocol | `references/intake-grill.md` |
| deliverable_home resolution | `references/output-routing.md` |
| D5 artifacts and pipeline | `references/d5-design-pipeline.md` |
| martin-pptx-skill delegation | `references/martin-pptx-delegation.md` |
| Portability rules and scan | `references/portability.md` |
| ASPG registration and discovery | `references/runtime-registration.md` |

## Templates

All templates are in `templates/`. Use the template as a starting point; adapt section content to the actual source material. Do not leave placeholder text in final deliverables.

## Version

- v1.0 — 2026-06-03 — Initial implementation. Skill-first, portable, six-deliverable package.
