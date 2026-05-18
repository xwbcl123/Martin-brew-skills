---
name: martin-pptx-skill
description: Staged deck engineering pipeline orchestrator for producing, validating, and iterating HTML/PDF/graphic and editable PPTX presentation artifacts from separated deck-outline.md, design.md, and visual motherboard inputs.
---

# martin-pptx-skill

## 定位

Use this skill when a local coding agent needs to create, revise, validate, or hand over a presentation deck through a staged, reviewable, reproducible workflow.

This skill is a **deck engineering pipeline orchestrator**, not a one-shot slide generator.

Its job is to separate:

- content and narrative control: `deck-outline.md`
- visual system control: `design.md`
- visual reference review: `visual motherboard`
- formal editable delivery: Option 5 PPTX reconstruction
- quality assurance: BG Gate, Text Fidelity Gate, render QC, editability checks

## Trigger Conditions

Trigger this skill when any of the following are true:

1. The user asks to create or redesign a deck, PPTX, policy/business presentation, leadership briefing, customer deck, visual report, course deck, or research slide set.
2. The user asks for outputs across `html`, `pdf`, `png`, `pptx`, or hybrid deck artifacts.
3. The user requires a deck that is editable, reviewable, auditable, or can be continued across machines.
4. The user provides or asks for `design.md`, `style.md`, `deck-outline.md`, visual references, a PowerPoint template, or a visual motherboard.
5. The user asks to validate PPTX quality, editability, font policy, text fidelity, visual consistency, or handoff readiness.

Do not trigger this skill for a trivial single-slide mockup unless the user explicitly wants staged artifacts or formal QC.

## Required Inputs

At minimum, collect or create:

| Input | Required? | Notes |
| --- | --- | --- |
| `brief.md` or source material | yes | Must contain objective, audience, source context, and target use case. |
| scenario | yes | `formal-company-report`, `customer-communication`, `personal-creative`, `research-report`, `training-course`, or custom. |
| language | yes | Default `zh-CN`; preserve canonical English technical terms. |
| target output | yes | `pptx`, `pdf`, `html`, `graphic`, or `hybrid`. |
| target slide count | yes | Can be approximate during Stage 0; must be fixed before Stage 3 full motherboard. |
| source index | yes for evidence-heavy work | Claims must trace to input material or be marked as assumption / inference. |

## Optional Inputs

| Input | Usage |
| --- | --- |
| Existing `deck-outline.md` | Validate, normalize, and use as narrative SSOT. |
| Existing `design.md` | Validate and use as visual system SSOT. |
| Legacy `style.md` / `style instruction` | Import-only alias; normalize to `design.md`. |
| Reference deck or template PPTX | Extract theme rules or use as formal PPTX constraint. |
| Brand guide / screenshots | Extract palette, layout grammar, component rules. |
| Chart data / workbook | Feed chart/table generation and evidence gates. |
| Visual motherboard | Use as approved visual reference or Stage 3 output. |
| Existing PPTX | Audit, reconstruct, or compare against gates. |

## Hard Product Rules

1. Keep `deck-outline.md` and `design.md` separate.
2. New visual-system artifact name is always `design.md`.
3. `style.md` and `style instruction` are legacy aliases only.
4. `deck-outline.md` is the content and narrative source of truth.
5. `visual motherboard` is a per-slide 16:9 high-quality infographic reference set, usually text-included and image-generation-led.
6. Formal company reporting must end in editable PPTX unless the user explicitly waives this.
7. Non-formal scenarios may stop at visual motherboard PDF / image-only PPTX / HTML / graphic outputs when the delivery objective is satisfied.
8. Do not flatten formal PPTX title/body text into images.
9. For editable PPTX, slide titles, body text, evidence labels, core business claims, and speaker notes must be editable unless a documented exception is approved.
10. Formal PPTX font policy: Chinese `Microsoft YaHei` / `微软雅黑`; English `Calibri`.
11. Do not claim final PPTX quality without `qc_report.md` and rendered preview evidence.
12. Every real run must produce `handover.md`.
13. Formal PPTX runs must produce and review `visual motherboard` before Option 5 reconstruction. Direct `deck-outline.md + design.md -> PPTX` is allowed only as an explicitly labeled script smoke test, not as the full skill workflow.
14. Programmatic PNG/PDF/PPTX renders made from layout heuristics are `visual wireframes` or `scaffolds`, not the authoritative visual motherboard. They may help prompt writing or smoke testing, but they do not satisfy Motherboard Gate unless explicitly accepted by the user.

## Stage-by-Stage Workflow

### Stage 0 — Intake / Grill

Goal: turn the request into an executable deck brief.

Required actions:

1. Identify audience, objective, required questions, source materials, target scenario, output format, language, and template/reference constraints.
2. Decide whether missing information blocks generation or can be logged as `known_gaps.md`.
3. Create or update `input/brief.md` and `input/source_index.md`.
4. For evidence-heavy decks, classify sources as official fact, media claim, stakeholder advocacy, provider statement, inference, or open question.

Outputs:

```text
input/brief.md
input/source_index.md
known_gaps.md            # only if needed
notes.md
```

Stop conditions:

- Stop and ask for missing information only if objective, audience, or required output cannot be inferred.
- If non-blocking gaps remain, proceed and document them in `known_gaps.md`.

Human review point:

- Required when the scenario is formal company reporting or when source uncertainty could cause factual risk.

### Stage 1 — Design System

Goal: create or normalize `design.md`.

Required actions:

1. If input has `style.md` / `style instruction`, normalize it into `design.md`.
2. If a reference deck or brand guide exists, extract palette, typography, grid, components, chart grammar, image direction, negative rules, and PPTX font policy.
3. If no visual reference exists, propose a design system suited to audience, scenario, and content.
4. Generate `style-preview.html` so the user can review palette, typography, grid, cards, matrix/table grammar, and density.

Outputs:

```text
output/design.md
output/style-preview.html
```

Stop conditions:

- Do not proceed to Stage 3 full visual motherboard if `design.md` lacks concrete colors, font policy, layout grammar, or negative rules.
- For formal company reporting, do not proceed without PPTX-compatible font policy.

Human review point:

- Required before Stage 2/3 when the visual direction is new, high-stakes, or brand-sensitive.

### Stage 2 — Deck Outline

Goal: create `deck-outline.md` as the narrative and content SSOT.

Required actions:

1. Build narrative arc and slide-by-slide production contract.
2. Ensure every slide has an action title, core message, evidence label, content blocks, visual intent, layout hint, speaker note hint, and downstream generation notes.
3. Preserve evidence discipline: do not convert unconfirmed claims into settled facts.
4. Optionally generate `visual-brief.html` for fast human scanning.

Outputs:

```text
output/deck-outline.md
output/visual-brief.html     # recommended
```

Stop conditions:

- Stop if slides lack action titles or governing thoughts.
- Stop if important claims are not traceable to source material or marked as assumptions.
- Stop if target slide count and scenario are unresolved.

Human review point:

- Required for formal company reporting, customer-facing external decks, legal/regulatory decks, and high-density evidence decks.

### Stage 3 — Visual Motherboard

Goal: produce a per-slide 16:9 high-quality visual reference set that raises the visual ceiling for the final deck.

This is a first-class deliverable, not only an intermediate preview. For many non-editable workflows, the motherboard PNG sequence plus PDF or image-only PPTX can be the final accepted artifact.

Definition:

- The canonical motherboard route is `deck-outline.md + design.md -> image-generation prompts -> image-gen 16:9 infographic slide images`.
- A valid motherboard should look like a polished executive / policy infographic deck reference, not a crude box-and-text programmatic layout.
- It may include text because its purpose is visual/narrative reference, while Stage 5 later rebuilds formal text as editable PPTX objects.
- Programmatic diagrams, HTML screenshots, or PIL-generated slides are only acceptable as `wireframe_motherboard` scaffolds unless the user explicitly approves them as final visual references.

Required actions:

1. Generate image-gen prompt pack from `deck-outline.md` and `design.md`.
2. Generate a small image-gen sample first for high-risk decks, typically 2–3 representative slides.
3. Pass sample through Motherboard Gate before full-deck generation.
4. Generate full `visual motherboard` only after design and outline are stable enough.
5. Create one text-included image per slide by default.
6. Create `contact_sheet.png` for fast whole-deck visual QA.
7. Export `motherboard.pdf` and `motherboard_image_only.pptx` from approved image-gen images when needed.
8. Create `qc_report.md` for visual motherboard stage.

Outputs:

```text
output/motherboard_imagegen/prompts/slide_*.md
output/motherboard_imagegen/prompt_manifest.json
output/motherboard_sample/slide_*.png        # optional sample path
output/motherboard_sample/contact_sheet_sample.png
output/motherboard_sample/qc_report_sample.md
output/motherboard_full/slide_01.png ... slide_N.png
output/motherboard_full/contact_sheet.png
output/motherboard_full/motherboard.pdf
output/motherboard_full/motherboard_image_only.pptx
output/motherboard_full/qc_report.md
```

Stop conditions:

- If no image-generation capability is available, stop after producing `output/motherboard_imagegen/prompts/` and report the blocker. Do not substitute a programmatic scaffold as the official motherboard.
- If scenario is non-formal and the user accepts PDF / graphic / HTML delivery, the pipeline may stop here after export and QC.
- Do not use the visual motherboard as a full-slide PPTX background when formal editability is required.

Human review point:

- Required before formal PPTX reconstruction.

### Stage 4 — Route Selection

Goal: select the correct delivery route for the scenario and constraints.

Precondition:

- For formal PPTX routes, Stage 3 `visual motherboard` must exist and be reviewed before route execution.
- If a run skips motherboard for engineering smoke testing, mark the run as `pipeline_shortcut` and do not count it as a full quality benchmark.

Default rules:

| Scenario | Default route | Backup / optional route | Allowed stop point |
| --- | --- | --- | --- |
| `formal-company-report` | Option 5 | Option 4 if runtime exists | Editable PPTX required |
| `customer-communication` | HTML/PDF first; PPTX if requested | Option 5 or Option 4 | HTML/PDF accepted if approved |
| `personal-creative` | Visual motherboard / HTML / PDF | Option 4 for editorial deck | Graphic/PDF/HTML |
| `research-report` | HTML/PDF + visual motherboard | Option 5 if editable PPTX needed | PDF/HTML |
| `training-course` | HTML/PDF or PPTX depending distribution | Option 5 for editable PPTX | PDF/PPTX |

Route registry:

| Route | Use When | Default Status |
| --- | --- | --- |
| Option 5 — header/footer/background master + Python editable reconstruction | Formal PPTX, visual motherboard approved, editability required | v0 main route |
| Option 4 — Presentations / artifact-tool | Runtime available and independent editorial backup desired | independent backup |
| Option 1 — Direct Python PPTX | Need deterministic native shapes, no safe background extraction, or simple enterprise layout | foundation / fallback inside Option 5 |
| Option 3 — HTML-first editable export | Need fast HTML/CSS authoring loop and export mapping can preserve editability | v1 R&D |
| Option 2 — image-gen textless background + editable text | Special visual acceleration with known cleanup risk | special-case only |

Outputs:

```text
output/route_decision.md
```

Stop conditions:

- Stop if selected route cannot satisfy the required output format.
- Stop if selected route would flatten all formal PPTX text into images.
- Stop if backup route is treated as a hard dependency for v0.

### Stage 5 — Option 5 PPTX Reconstruction

Goal: produce the main editable formal PPTX.

Main v0 route:

```text
design.md + deck-outline.md + approved image-gen visual motherboard
-> shared header/footer/background master
-> Python editable PPTX reconstruction
-> BG Gate + Text Fidelity Gate + render QC
```

Required actions:

1. Extract or build a shared or per-section background master from approved visual motherboard / reference slide.
2. Run BG Gate before overlaying business content.
3. Keep only low-risk raster chrome in background: header/footer/logo/bottom chrome/background texture.
4. Remove body text, body proof objects, icons, charts, cards, labels, stale evidence text, stale subtitles, and other business content from background.
5. Rebuild slide title, subtitle, body, matrix/table text, labels, evidence strips, chips, and speaker notes as PowerPoint-native editable objects.
6. Render PPTX to PDF/PNG.
7. Generate contact sheet and `text_extraction.json`.
8. Run Text Fidelity Gate against `deck-outline.md`.

Hard precondition:

- `output/motherboard_full/contact_sheet.png` and per-slide `slide_*.png` must exist before formal Option 5 reconstruction.
- The PPTX builder may use a shared background master, but its layout decisions should be informed by the approved motherboard and not only by `deck-outline.md`.

Outputs:

```text
output/full_deck_option5/deck.pptx
output/full_deck_option5/rendered/deck.pdf
output/full_deck_option5/rendered/png/slide_*.png
output/full_deck_option5/contact_sheet.png
output/full_deck_option5/bg_gate_report.json
output/full_deck_option5/text_extraction.json
output/full_deck_option5/text_fidelity_gate.md
output/full_deck_option5/qc_report.md
```

Stop conditions:

- BG Gate fail blocks reconstruction or delivery.
- Text Fidelity Gate fail blocks delivery.
- Render fail blocks delivery.
- Editable text fail blocks formal PPTX delivery.
- Any factual mismatch blocks delivery until corrected.

### Stage 6 — Backup / Alternate Route

Goal: produce an independent backup deck when useful and available.

Option 4 usage:

- Use `Presentations` / `artifact-tool` route only when runtime is available.
- Treat it as an independent editorial analytics deck, not a pixel-perfect visual clone of the visual motherboard.
- Run render QC and text extraction if PPTX is produced.
- Compare against Option 5 with a scorecard.

Outputs:

```text
output/backup_option4/deck.pptx             # if runtime can produce PPTX
output/backup_option4/rendered/deck.pdf
output/backup_option4/rendered/png/slide_*.png
output/backup_option4/layout.json           # if artifact-tool route produces layout metadata
output/backup_option4/scorecard.md
output/backup_option4/qc_report.md
```

Stop conditions:

- If runtime is unavailable, record route as skipped; do not block Option 5.
- If backup deck is higher quality but diverges from formal requirements, present it as alternate, not replacement, unless user approves.

### Stage 7 — QC, Handover, and Promotion Evidence

Goal: record run status and make continuation reliable.

Required gates for formal PPTX:

1. Scaffold gate.
2. Render gate.
3. BG Gate.
4. Text Fidelity Gate.
5. Editability gate.
6. Font/readability gate.
7. Contact sheet visual review.
8. Evidence/source traceability gate.

Outputs:

```text
output/qc_report.md
notes.md
verdict.md
handover.md
```

Stop conditions:

- Any `fail` in mandatory formal PPTX gate blocks final delivery.
- `warn` is allowed only with documented rationale and recommended repair.
- `pass` means accepted for that gate, not necessarily visually perfect.

## Artifact Contracts

Use `references/artifact-schema.md` for full schema. Minimum contracts:

| Artifact | Required for | Contract Summary |
| --- | --- | --- |
| `brief.md` | all runs | audience, objective, questions, scenario, language, output, source materials. |
| `source_index.md` | evidence-heavy runs | source list, type, reliability, usage notes. |
| `design.md` | all visual runs | visual thesis, palette, typography, layout grammar, component rules, negative rules, PPTX font policy. |
| `style-preview.html` | Stage 1 review | human-readable preview of visual system. |
| `deck-outline.md` | all deck runs | narrative SSOT and per-slide production contract. |
| `visual-brief.html` | recommended | scan-friendly outline preview. |
| `visual motherboard` | Stage 3+ | per-slide 16:9 visual references and contact sheet. |
| `deck.pptx` | formal PPTX | editable title/body/notes and passable render. |
| `text_extraction.json` | formal PPTX | extracted PPTX text objects, fonts, text counts, page mapping. |
| `qc_report.md` | every major stage | pass/warn/fail gate outcomes and known tradeoffs. |
| `handover.md` | every run | current stage, confirmed artifacts, blockers, next commands. |

## Quality Gates

Gate policy:

```text
fail -> block delivery
warn -> allowed only with documented rationale and repair recommendation
pass -> accepted for the current stage
```

Mandatory formal PPTX gates:

- BG Gate: background hygiene and stale content removal.
- Text Fidelity Gate: outline-to-PPTX editable text fidelity.
- Render QC: PDF/PNG output exists and page count matches outline.
- Editability QC: titles, body, evidence labels, and speaker notes editable.
- Font/readability QC: formal font policy and body text threshold.
- Evidence QC: claims trace to source or are marked as inference/assumption.

See `references/gates.md` for exact pass/warn/fail rules.

## Failure Modes and Recovery Actions

| Failure Mode | Detection | Recovery |
| --- | --- | --- |
| `design.md` too vague | Design gate fail | Add concrete tokens: colors, fonts, grid, component grammar, negative rules. |
| `deck-outline.md` lacks action titles | Outline gate fail | Rewrite titles as conclusion-first claims. |
| Visual motherboard looks good but has too much text | Motherboard QC warn/fail | Compress content in outline or split slide. |
| Background master contains stale body content | BG Gate fail | Re-clean background or rebuild directly with Option 1. |
| PPTX text flattened into background | Editability fail | Rebuild text as native PPTX objects. |
| Text Fidelity Gate finds factual mismatch | Text Fidelity fail | Correct PPTX text layer; re-render and rerun gate. |
| Body text under 16 pt | Font/readability warn/fail | Reduce text, split slide, or change layout. |
| Render differs from PPTX expectations | Render gate warn/fail | Inspect PDF/PNG, adjust layout, rerun export. |
| Option 4 runtime unavailable | Route note | Skip backup route and continue Option 5. |
| Python reconstruction too bespoke | Implementation risk | Extract component builders and reusable CLIs. |

## Human Review Points

Human review is required at:

1. Stage 0 when source ambiguity can affect claims.
2. Stage 1 for new or brand-sensitive visual direction.
3. Stage 2 for formal company report outline approval.
4. Stage 3 contact sheet approval before formal PPTX reconstruction.
5. Stage 5 final contact sheet and Text Fidelity Gate review.
6. Any `warn` accepted for final delivery.

## Promotion Criteria

Promote from lab candidate to formal skill only when:

1. A fresh local agent can run the workflow from this `SKILL.md` without old chat history.
2. At least 3 benchmark runs have been executed using the same artifact schema.
3. At least 2 formal PPTX runs pass mandatory gates with no blocking failures.
4. Option 5 scripts are reusable and parameterized, not project-specific.
5. BG Gate and Text Fidelity Gate can run from CLI with documented inputs/outputs.
6. `handover.md` consistently supports cross-device continuation.
7. Failure modes and recoveries are documented in `qc_report.md` or `verdict.md`.
8. Option 4 backup route is documented as optional and independent.

## Output Language

Default user-facing output language: Simplified Chinese (`zh-CN`). Keep canonical artifact names and technical terms in English, for example:

- `design.md`
- `deck-outline.md`
- `visual motherboard`
- `contact_sheet.png`
- `BG Gate`
- `Text Fidelity Gate`
- `Option 5`
- `Option 4`
- `handover.md`
