# Gates and QC Contract

## Gate Policy

```text
pass = accepted for the stage
warn = accepted only with documented rationale and review
fail = blocks next stage or final delivery
```

Formal PPTX delivery cannot ship with any mandatory gate in `fail` status.

## Mandatory Gate Matrix

| Gate | Stage | Required For | Blocks? |
| --- | --- | --- | --- |
| G0 Scaffold Gate | 0/7 | all real runs | yes |
| G1 Outline Gate | 2 | all deck runs | yes |
| G2 Design Gate | 1 | all visual runs | yes |
| G3 Motherboard Gate | 3 | visual/PPTX runs | yes for formal PPTX |
| G4 Route Gate | 4 | all route decisions | yes |
| G5 BG Gate | 5 | formal Option 5 PPTX | yes |
| G6 Render Gate | 5/6 | PPTX/PDF outputs | yes |
| G7 Editability Gate | 5/6 | formal PPTX | yes |
| G8 Text Fidelity Gate | 5/6 | formal PPTX | yes |
| G9 Font/Readability Gate | 3/5/6 | all visible outputs | yes for severe issues |
| G10 Evidence Gate | 2/5 | evidence-heavy decks | yes for factual mismatch |
| G11 Handover Gate | 7 | all real runs | yes to close run |

## G0 — Scaffold Gate

Pass:

- Run folder follows canonical structure.
- Required `input/`, `output/`, `notes.md`, `verdict.md`, `handover.md` exist or are scheduled for creation.
- Stage-specific required outputs are present.

Warn:

- Minor naming mismatch that does not block continuation.

Fail:

- Missing core run folder or outputs cannot be located.
- No handover path for cross-device continuation.

## G1 — Outline Gate

Pass:

- `deck-outline.md` exists.
- Every slide has action title, core message, evidence label, visual intent, layout hint, speaker note hint.
- Narrative arc and target slide count are clear.
- Claims trace to source or are marked as inference/assumption.

Warn:

- Some slide content may be too dense but can be resolved during layout.
- Some title compression is expected but not yet applied.

Fail:

- Slides have descriptive labels instead of action titles.
- Key claims are untraceable or overstate uncertain evidence.
- Target output / scenario is unresolved.

## G2 — Design Gate

Pass:

- `design.md` exists and includes visual thesis, palette, typography, layout grammar, components, chart/table grammar, negative rules, and PPTX font policy.
- `style-preview.html` exists for human review.
- Legacy `style.md` has been normalized to `design.md` if present.

Warn:

- Visual direction is adequate but theme library metadata is incomplete.

Fail:

- Design system lacks concrete tokens.
- PPTX font policy missing for formal deck.
- Negative rules are absent for high-risk visual styles.

## G3 — Motherboard Gate

Pass:

- Image-gen prompt pack exists and is traceable to `deck-outline.md` + `design.md`.
- One polished 16:9 infographic visual reference per slide exists.
- Contact sheet exists.
- Visual references align with `design.md` and `deck-outline.md`.
- Visual references raise the design ceiling enough to guide PPTX reconstruction, including meaningful composition, icon/label/chart language, spacing, hierarchy, and executive-ready finish.
- Human review has approved the visual direction for formal PPTX.

Warn:

- Some slides need polish but are acceptable as reconstruction reference.
- Minor text density issue documented.
- Programmatic wireframes are present and useful for prompt scaffolding, but final image-gen motherboard is not yet complete.

Fail:

- Missing slides.
- Only a crude programmatic PNG/PDF/PPTX scaffold exists and no approved image-gen visual reference exists.
- Inconsistent visual system.
- Text too small/unreadable in major body content.
- Visual motherboard contradicts `deck-outline.md`.
- Visual reference is too simple to guide the final deck's visual ambition.

## G4 — Route Gate

Pass:

- `route_decision.md` exists.
- Main route satisfies target output and editability constraints.
- Option 5 selected for formal PPTX unless a documented exception exists.
- Option 4 treated as optional independent backup.

Warn:

- Experimental route selected for non-formal work with documented rationale.

Fail:

- Cloud-only runtime made mandatory for v0 main route.
- Formal PPTX route flattens all text into images.
- Option 2 selected as default without special-case rationale.

## G5 — BG Gate

Purpose: ensure background master is safe before editable content is overlaid.

### Allowed in background

- header chrome
- footer chrome
- logo/footer area
- page marker block
- subtle background texture
- bottom line / bottom circuitry
- non-semantic decorative shapes
- approved brand background elements

### Must be removed from background

- slide title and subtitle
- body text
- proof objects
- body icons
- charts
- cards
- labels
- stale evidence text
- stale dates / source claims
- stale matrix/table contents
- stale callouts
- old footer evidence text that duplicates editable layer

### Pass

- Background contains only approved chrome / texture / decorative elements.
- No stale body content is visible.
- Body area is visually clean enough for editable objects.
- `bg_gate_report.json` or `bg_gate.md` records kept/removed elements.

### Warn

- Minor decorative artifacts remain but cannot be confused with business content.
- Slight texture discontinuity that does not reduce readability.

### Fail

- Any stale body text or evidence label remains.
- Any stale chart/matrix/card could be read as business content.
- Background overlaps editable text.
- Background cleanup damages brand/footer/header in a way that affects delivery.

### Recovery

1. Re-clean or regenerate background.
2. Clear dirty region with deterministic mask and rerender.
3. Use per-section or per-slide background instead of shared background.
4. Fall back to Option 1 direct Python reconstruction if background extraction remains unsafe.

## G6 — Render Gate

Pass:

- PPTX exports to PDF.
- PDF pages render to PNG.
- Page count equals outline slide count.
- Contact sheet generated.
- No major clipping, missing pages, or blank slides.

Warn:

- Minor visual difference between PPTX editor and PDF render.
- Some non-critical decorative mismatch.

Fail:

- Export fails.
- Missing slide render.
- Page count mismatch.
- Important text clipped or hidden.

## G7 — Editability Gate

Pass:

- Formal PPTX title, body, evidence labels, major callouts, and speaker notes are editable.
- `text_extraction.json` exists.
- Critical text is not embedded only in images.
- Image layers are limited to background, icons, decorative assets, or complex infographics.

Warn:

- Some chart internals remain as image but title/label/callout text is editable or documented.
- Some icons are raster but non-critical.

Fail:

- Title/body text flattened into images.
- Speaker notes missing when required.
- Business-critical labels only exist in raster background.

## G8 — Text Fidelity Gate

Purpose: compare `deck-outline.md` to editable PPTX text layer.

### Required Checks

- slide count alignment
- title fidelity
- evidence label preservation
- required terms present
- forbidden terms absent
- semantic coverage
- factual mismatch detection
- source status preservation, especially official fact vs inference vs open question

### Pass

- No factual mismatch.
- Required terms and evidence labels preserved.
- Core meaning of each slide remains traceable.
- Title changes are either exact or semantically equivalent.

### Warn

- Layout-driven title compression.
- Semantic compression that preserves source meaning.
- Minor wording change that reviewer can accept.

### Fail

- Missing required evidence label.
- Required term absent from editable text layer.
- Forbidden factual mismatch appears.
- Official/inference/open-question distinction lost.
- Core slide meaning no longer traceable.

### Recovery

1. Patch PPTX editable text layer.
2. Re-render.
3. Rerun text extraction and Text Fidelity Gate.
4. Document any remaining warn in `qc_report.md`.

## G9 — Font / Readability Gate

Recommended thresholds for formal PPTX:

| Level | Minimum |
| --- | ---: |
| Title | 28 pt |
| H1 | 22 pt |
| H2 | 20 pt |
| H3 | 18 pt |
| Body | 16 pt |
| Footer / metadata | can be smaller if non-critical |

Pass:

- Body text meets threshold.
- Chinese uses `Microsoft YaHei` / `微软雅黑`; English uses `Calibri` for formal PPTX.
- No obvious overlap or overflow.

Warn:

- Footer/metadata below body threshold but non-critical.
- One or two dense slides need human approval.

Fail:

- Body content below threshold.
- Text overlaps or is clipped.
- Font renders as tofu/garbage.

## G10 — Evidence Gate

Pass:

- Claims trace to sources or are marked as inference/assumption.
- Evidence labels preserve source type.
- Unpublished / uncertain items remain conditional.

Warn:

- Claim is plausible but needs source note before external delivery.

Fail:

- Media/stakeholder claim presented as official fact.
- Unpublished legal text treated as settled law.
- Factual contradiction introduced in PPTX layer.

## G11 — Handover Gate

Pass:

- `handover.md` includes run id, current stage, confirmed artifacts, pending reviews, blockers, next commands, continuation prompt.
- A fresh agent can continue without old chat history.

Warn:

- Minor command details missing but next stage is clear.

Fail:

- No handover.
- Handover lacks current stage or confirmed artifacts.

## QC Report Minimum Table

Every `qc_report.md` should include:

| Gate | Status | Evidence | Action |
| --- | --- | --- | --- |
| Scaffold | pass/warn/fail | paths checked | next action |
| Outline | pass/warn/fail | file/slide count | next action |
| Design | pass/warn/fail | preview/design path | next action |
| Motherboard | pass/warn/fail | contact sheet | next action |
| Route | pass/warn/fail | route decision | next action |
| BG | pass/warn/fail/N/A | report path | next action |
| Render | pass/warn/fail | PDF/PNG path | next action |
| Editability | pass/warn/fail | text extraction | next action |
| Text Fidelity | pass/warn/fail | gate report | next action |
| Font/Readability | pass/warn/fail | metrics | next action |
| Evidence | pass/warn/fail | source index | next action |
| Handover | pass/warn/fail | handover path | next action |
