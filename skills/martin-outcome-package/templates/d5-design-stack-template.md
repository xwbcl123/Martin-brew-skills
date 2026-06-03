# D5 — design-stack.md

## Header

```yaml
deliverable: D5-design-stack
title: "{{PROJECT_NAME}} — Production & Render Contract"
date: {{ISO_DATE}}
author: martin-outcome-package
version: 1.0
companion: design.md
```

---

## Target Output

| Field | Value |
|-------|-------|
| Primary format | {{FORMAT}} (`pptx` / `pdf` / `html` / `graphic` / `hybrid`) |
| Secondary format | {{SECONDARY_FORMAT_OR_NONE}} |
| Language | {{LANGUAGE}} (preserve canonical English technical terms) |

## Render Toolchain

| Stage | Tool / Skill | Notes |
|-------|-------------|-------|
| Outline | martin-outcome-package (D4) | Content/narrative SSOT |
| Design system | martin-outcome-package (D5) | `design.md` = visual SSOT |
| Deck spec + artifacts | martin-pptx-skill | Consumes handoff; produces `deck-spec.md` |
| Final assembly | martin-pptx-skill | Produces target output |

## Budget

- **Slide/page count**: {{SLIDE_COUNT}} (approximate; finalized by martin-pptx-skill)
- **Production timeline**: {{TIMELINE_OR_NO_CONSTRAINT}}

## Accessibility

- Minimum contrast ratio: 4.5:1 (WCAG AA)
- Minimum font size: 13px / 10pt
- Alt text required for all images
- Color must not be the only differentiator

## Brand Constraints

{{BRAND_CONSTRAINTS_OR_NONE}}

> If an external brand guide exists, reference its location here. The `design.md` tokens should be derived from or compatible with the brand guide.

## Negative Constraints

> Formats, tools, or approaches explicitly excluded.

- {{NEGATIVE_1}}
- {{NEGATIVE_2}}

## Handoff Notes

> Additional context for the downstream render pipeline.

{{HANDOFF_NOTES}}
