# Package Contract

## Six-Deliverable Shape

Every Martin Outcome Package produces exactly six deliverables:

| ID | Name | Format | Required |
|----|------|--------|----------|
| D1 | Deep Report | Markdown | Yes |
| D2 | Executive Summary | Markdown | Yes |
| D3 | Visual Briefing | HTML/Image | No (skippable if no visual context) |
| D4 | Deck Outline & Brief | Markdown | No (skippable if no deck needed) |
| D5 | Design System | `design.md` + `design-stack.md` + `martin-pptx-handoff.md` | No (skippable if no deck needed) |
| D6 | Email Package | Markdown | No (skippable if no stakeholder send) |

## Minimum Viable Package

A valid package must produce at minimum **D1 + D2**. D3-D6 are produced when the intake grill confirms they are needed.

## Package Metadata

Every package folder must contain a `README.md` (generated from `templates/package-readme-template.md`) with:

- `package_id`: unique slug
- `created`: ISO date
- `deliverable_home`: resolved output path
- `source_type`: one of `transcript`, `req-md`, `inbox-capture`, `session`, `fuzzy-task`
- `deliverables_produced`: list of D-IDs actually generated
- `needs_archive_destination`: boolean, true if `deliverable_home` fell back to session-local

## Deliverable Lifecycle

```
Intake → Context Discovery → deliverable_home resolution →
  D1 (deep report) → D2 (executive summary) →
  [D3 (visual briefing)] → [D4 (deck outline)] →
  [D5 (design system + handoff)] → [D6 (email package)] →
  Package README → Completion
```

## D5 Ownership Boundary

This Skill is the **single author** of:
- `design.md` — visual system definition
- `design-stack.md` — top-level production/render contract
- `martin-pptx-handoff.md` — delegation brief for `martin-pptx-skill`

This Skill does **not** produce:
- `deck-spec.md` (belongs to `martin-pptx-skill`)
- Slide artifacts (belongs to `martin-pptx-skill`)
- PPTX files (belongs to `martin-pptx-skill`)

## Graceful Degradation

If optional inputs (brand styles, taste guidance, external design references) are unavailable, the Skill must still produce a valid package using bundled defaults. Missing optional inputs are logged in the package README, not treated as errors.
