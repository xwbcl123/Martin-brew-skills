# Product Contract — martin-pptx-skill

## Product Definition

`martin-pptx-skill` is a staged **deck engineering pipeline orchestrator** for producing and validating deck artifacts across HTML, PDF, graphic, and editable PPTX workflows.

It optimizes for:

- 可审查：each stage creates reviewable artifacts.
- 可修改：formal PPTX keeps business-critical text editable.
- 可复现：run folders, schemas, scripts, and gates are stable.
- 可交接：every run has `handover.md`.
- 可验证：render QC, BG Gate, and Text Fidelity Gate prove delivery quality.

It is not a one-shot slide generator.

## Product Invariants

These cannot be changed without a new product decision:

1. `design.md` is canonical visual system artifact.
2. `style.md` / `style instruction` are legacy aliases only.
3. `deck-outline.md` is narrative and content source of truth.
4. `visual motherboard` is a per-slide 16:9 high-quality infographic reference set, usually text-included and image-generation-led.
5. Formal company reporting must end in editable PPTX.
6. Non-formal scenarios may stop at visual motherboard PDF / image-only PPTX / HTML / graphic outputs.
7. Option 5 is v0 main route.
8. Option 4 is independent backup route.
9. BG Gate and Text Fidelity Gate are mandatory for formal PPTX delivery.
10. Business-critical formal PPTX text must not be flattened into images.
11. Formal PPTX delivery must pass through an image-gen visual motherboard stage before Option 5 reconstruction. Skipping motherboard is a pipeline shortcut and does not count as a full quality benchmark.
12. Programmatic PNG/PDF/PPTX artifacts generated from deterministic layout heuristics are `wireframe_motherboard` scaffolds. They may inform prompt writing and smoke tests, but they do not satisfy the visual motherboard contract unless explicitly accepted by Martin.
13. `Baked presentation`, `image-baked deck`, `image-gen baked deck`, and `visual motherboard` mean image-generation-led visual production by default. Programmatic PIL/HTML/canvas/card screenshots are not acceptable substitutes unless Martin explicitly approves a deterministic scaffold.
14. If a route uses deterministic programmatic cards, tables, chips, timelines, or layout grammar, its PPTX output must be editable native PowerPoint objects. Full-slide raster insertion from programmatic renders is allowed only for smoke tests, contact sheets, or explicitly accepted non-editable delivery.
15. Image-generation tools have a practical consecutive-call limit. For decks over 10 slides, the official visual motherboard workflow must split generation into batches of at most 10 images, with a QA / cooldown checkpoint after each batch before continuing.

## Users

Primary:

- Martin as product owner and heavy user.
- Future local coding agents running deck experiments or production workflows.

Secondary:

- Cloud experts or external agents delegated to run skill-design or deck-generation experiments.
- Reviewers who need to inspect artifacts without old chat context.

## Scenarios and Terminal Artifacts

| Scenario | Typical Language | Terminal Artifact | PPTX Required? | QC Required? |
| --- | --- | --- | --- | --- |
| Formal company report | `zh-CN` with English terms | editable `.pptx` + PDF/PNG render | yes | all mandatory gates |
| Customer communication | usually English | HTML/PDF; PPTX optional | optional | render + evidence + readability |
| Personal / creative work | zh-CN or English | HTML/PDF/graphic | usually no | visual + readability |
| Research report | zh-CN or English | PDF/HTML; PPTX if requested | optional | source/evidence + readability |
| Training/course deck | zh-CN or English | PPTX/PDF/HTML | depends | readability + structure |

## Stage Contract

| Stage | Name | Required Output | Review? | Blocks Next Stage? |
| --- | --- | --- | --- | --- |
| 0 | Intake / Grill | `brief.md`, `source_index.md`, optional `known_gaps.md` | yes for high-stakes | yes if objective/audience/output unknown |
| 1 | Design System | `design.md`, `style-preview.html` | yes | yes if visual rules vague |
| 2 | Deck Outline | `deck-outline.md`, optional `visual-brief.html` | yes | yes if action titles/evidence missing |
| 3 | Visual Motherboard | image-gen prompts, `slide_*.png`, `contact_sheet.png`, `motherboard.pdf`, `motherboard_image_only.pptx`, `qc_report.md` | yes | yes for formal PPTX |
| 4 | Route Selection | `route_decision.md` | usually | yes if route violates delivery requirements |
| 5 | PPTX Reconstruction | `deck.pptx`, render, extraction, gates, QC | yes | yes if any mandatory fail |
| 6 | Backup Route | optional Option 4 outputs | no, unless used | no for v0 main route |
| 7 | Handover / Verdict | `handover.md`, `verdict.md`, `notes.md` | yes | required to close run |

## Core Artifact Contracts

### `brief.md`

Must include:

- run id
- scenario
- audience
- objective
- language
- target output
- target slide count
- source materials
- required questions
- constraints
- known assumptions
- human approver / review cadence if formal

### `source_index.md`

Must include:

- source path or name
- source type: official fact, media report, stakeholder advocacy, provider statement, inference, open question, user-provided reference
- reliability / confidence note
- used for which slide or claim
- quote/claim extraction notes when relevant

### `design.md`

Must include:

- visual thesis
- scenario
- source basis
- palette tokens and roles
- typography rules
- PPTX font policy
- layout grammar
- component grammar
- chart/table grammar
- image/icon direction
- density/readability rules
- negative rules
- reuse/theme notes

### `deck-outline.md`

Must include frontmatter:

- type
- run id
- date
- version
- language
- scenario
- audience
- objective
- source materials used
- target slide count
- design system path
- evidence policy

Must include per slide:

- slide number
- action title
- core message
- evidence
- content blocks
- visual intent
- layout hint
- evidence label
- decision questions
- speaker note hint
- motherboard prompt / downstream generation notes

### `visual motherboard`

Must include:

- image-gen prompt pack created from `deck-outline.md` and `design.md`
- one polished 16:9 infographic image per slide
- default text-included pages
- shared `design.md` compliance
- alignment to `deck-outline.md`
- `contact_sheet.png`
- `qc_report.md`
- optional `motherboard.pdf` / image-based `motherboard.pptx` for non-formal delivery

Must not be:

- a crude programmatic box layout
- a simple PNG-to-PDF-to-PPTX smoke-test artifact
- a low-density placeholder that cannot guide visual ambition
- a substitute for image-gen exploration when the goal is to raise design quality

### Formal `deck.pptx`

Must include:

- editable slide titles
- editable body text
- editable evidence labels / core claims
- editable speaker notes when present
- PPTX-compatible font policy
- raster background limited to approved chrome / texture / decorative assets
- no stale body content embedded in background

### `qc_report.md`

Must include:

- artifact list and path status
- stage status summary
- page count / slide count
- render result
- contact sheet status
- font/readability metrics
- editability metrics
- BG Gate result if formal PPTX
- Text Fidelity Gate result if formal PPTX
- pass/warn/fail table
- known tradeoffs
- final verdict and repair recommendations

### `handover.md`

Must include:

- run id
- current stage
- confirmed artifacts
- pending human review
- blockers
- next actions
- next commands
- continuation prompt
- environment notes

## Quality Contract

### Gate Status Meaning

| Status | Meaning | Delivery Impact |
| --- | --- | --- |
| `pass` | Meets the contract for current stage. | Can proceed. |
| `warn` | Acceptable only with documented rationale and review. | Can proceed if approved. |
| `fail` | Violates a mandatory rule or creates high delivery risk. | Blocks delivery / next stage. |

### Mandatory Formal PPTX Gates

1. BG Gate.
2. Text Fidelity Gate.
3. Render QC.
4. Editability QC.
5. Font/readability QC.
6. Evidence/source traceability QC.
7. Human contact sheet review.

## Acceptance Contract

A run is accepted only when:

- Required terminal artifact exists.
- Required gates are pass or documented warn.
- No mandatory gate has fail.
- `handover.md` and `verdict.md` exist.
- Formal PPTX has editable critical text and render preview.
- Non-formal terminal artifact satisfies user-approved stop condition.

## Anti-Patterns

Reject outputs that:

- Collapse `design.md` and `deck-outline.md`.
- Treat visual motherboard as a single template image.
- Present deterministic wireframes or PNG-to-PDF-to-PPTX scaffolds as the official motherboard when the user expects image-gen visual exploration.
- Use Option 2 as default.
- Make cloud-only runtime mandatory for v0 main route.
- Present Option 4 as visual-faithful reconstruction.
- Deliver formal PPTX with all text flattened into images.
- Ignore BG Gate or Text Fidelity Gate.
- Omit local integration steps and script plan.
