# D5 Design Pipeline

## Overview

D5 produces three artifacts that together define the visual system and enable delegation to `martin-pptx-skill` for deck production:

1. **`design.md`** — Visual system definition (palette, typography, grid, components)
2. **`design-stack.md`** — Top-level production/render contract (output format, toolchain, constraints)
3. **`martin-pptx-handoff.md`** — Complete delegation brief for `martin-pptx-skill`

Before D5 starts, run the deck route readiness gate in `references/execution-gotchas.md`. In particular, confirm whether the intended deck route produces an editable PPTX or only image-baked slides. Treat image-baked slides as visual reference, not as the primary editable deck.

## Authorship Boundary

This Skill (martin-outcome-package) is the **single author** of all three D5 files. `martin-pptx-skill` **consumes** them as downstream inputs but never modifies them.

The downstream `deck-spec.md` (per-slide production spec) is authored by `martin-pptx-skill`, not by this Skill.

## design.md

The visual system definition. Contents:

- **Visual thesis**: one-sentence design direction
- **Color tokens**: primary, secondary, accent, background, surface, text (with hex/HSL values)
- **Typography**: font families, size scale, weight scale
- **Grid/Layout**: column system, margins, spacing scale
- **Component grammar**: card styles, callout boxes, dividers, icon style
- **Chart/Table grammar**: chart color sequence, table header style, border rules
- **Image direction**: photography style, illustration style, icon library preference
- **Negative rules**: what to explicitly avoid

Use `templates/d5-design-md-template.md` as the starting point.

## design-stack.md

The top-level production and render contract. Contents:

- **Target output format**: pptx, pdf, html, graphic, or hybrid
- **Render toolchain**: which tools/skills produce the final artifact
- **Slide/page budget**: approximate count
- **Language**: primary language + term preservation rules
- **Accessibility**: minimum contrast ratio, font size floor
- **Brand constraints**: if external brand guide exists, reference it here
- **Negative constraints**: formats, tools, or approaches explicitly excluded

Use `templates/d5-design-stack-template.md` as the starting point.

## martin-pptx-handoff.md

The delegation brief that maps directly to `martin-pptx-skill` Required Inputs. See `references/martin-pptx-delegation.md` for the field mapping.

Use `templates/d5-martin-pptx-handoff-template.md` as the starting point.

## Pipeline Flow

```
D1 (deep report) + D2 (exec summary) + D4 (deck outline)
        │
        ▼
   Intake context
        │
        ├── design.md (visual system)
        ├── design-stack.md (production contract)
        └── martin-pptx-handoff.md (delegation brief)
                │
                ▼
        martin-pptx-skill Stage 0
```

## Route Readiness Notes

- Gamma AI can be used as a formal deck route only after returned PPTX/PDF artifacts pass QA and are suitable for polish.
- NotebookLM is a visual reference route by default. It may inspire slide rhythm and composition, but it must pass editability checks before being treated as a formal editable deck.
- If the route requires a browser session, CLI auth, or download state, verify that readiness before the route is on the critical path.
