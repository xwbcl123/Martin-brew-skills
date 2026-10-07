# ASF native production contract

Production source: user-selected Paper and Georgia Ink, fixed v1.0.0 HTML after soft-surface and icon-left followups (latest source receipt `c535c577`). Each register has 10 core slides plus 2 appendices. The frozen r2 audit establishes design intent; final geometry and RGB colors come from the fixed production HTML, not r2.

## Delivered native structure

- Two 1280×720 authoring canvases, exported as 13⅓×7½ inch PPTX.
- Editable native text shapes, one native 3-series/3-category bar chart with embedded literal-data workbook on slide 4, one native 5×4 evidence table on slide 5, native diagram anchor shapes and attached connectors on slides 1, 6 and 12.
- Official logo SVG is rendered to a transparent PNG after loading the official Spline Sans 700 WOFF2 in Chrome. Spline appears only in the logo artwork. Official icon SVG paths retain symbol fill/stroke/caps/joins attributes. These logo/icons are source images, not editable Office vector primitives. No full-slide screenshot is used.
- One explicit ASF master and one blank native canvas layout are authored per deck. Actual exported master/layout/theme part counts are recorded by `verify_ooxml.py`. This is **not** a 12-archetype Office master/placeholder library or POTX. The 12 archetypes are editable sample slides and reusable JSON geometry.
- Labels, node frames, icons and background boxes are separate objects. Connector endpoints attach to native anchor shapes. Labels are not bound to node movement and no SmartArt behavior is promised; move the related objects together when editing manually.

## Typography and matching

Georgia is the selected display face; Arial is the reference body face; Consolas is the intended metadata role. The verified local font inventory contains Georgia/Arial/Courier New and lacks Consolas. Native metadata deliberately uses **Courier New** on this host, rather than silently allowing a proportional fallback. Font metadata records intended and actual families; no fonts are embedded or redistributed. Other hosts can use Consolas only after updating the render font selection and visually checking layout.

Geometry and font sizes use CSS pixels at 96 DPI. 1920px reference geometry scales by 2/3 to 1280px; 24px reference metadata becomes 16px authoring / 12pt OOXML. Character tracking is written in OOXML hundredths of a point. Actual browser line segmentation becomes separate editable single-line text slots, including explicit line breaks and measured wrapped lines. This prevents native reflow from colliding with neighboring content. Vertical cover labels retain a rotated native frame in the right safe margin.

Chart order, categories and data labels follow the source visually: Traceability / Comparability / Reusability, Working notes / Shared record / Reviewed brief; ticks 0, 50, 100. The chart retains editable data. Its engine-controlled internal plot margins, legend centering and data label appearance differ slightly from CSS bars. Export ordering is reversed intentionally to compensate for the horizontal-bar renderer's display ordering; workbook values and their categories stay paired.

Tables preserve all source rows/columns and status text. Header fill is the captured computed RGB value (including the latest Paper soft surface), rather than the upstream raised token. Explicit cell borders are schema-ordered before cell fill. A named no-grid table style prevents Office's default grid inheritance. Horizontal rules remain editable. Source inline status badge outlines are not reproduced as additional table-cell borders; status words and semantic colors remain.

CSS oklch/color-mix colors are converted through a browser canvas to actual sRGB pixels. Reusable brand theme values are derived from the verified upstream tokens JSON; local surface treatments remain measured production-layout values. The sample does not claim pixel-identical CSS/Office rasterization or cross-platform glyph metrics.

## Portable invocation

Use the bundled Node executable, with dependencies resolved by package name, `ASF_RUNTIME_NODE_MODULES`, or `NODE_PATH`. Set `PRESENTATIONS_SKILL_DIR` to the installed Presentations skill and `RUNTIME_PYTHON` to the bundled Python executable. The wrapper supplies the finalizer's internal runtime variable from the portable configuration. No machine-specific runtime path is embedded in released scripts.

```sh
node scripts/native/build.mjs \
  --input assets/native/inputs/paper.sample.json \
  --resource-root assets/native \
  --output-dir new-build \
  --brand-root assets/source/assets/asf-brand-v1.2.2 \
  --name asf-paper-custom
```

`--brand-root` / `ASF_BRAND_ROOT` accepts a Git checkout **or** standalone snapshot. If omitted, the builder uses the skill-relative packaged snapshot `assets/source/assets/asf-brand-v1.2.2`. All 10 upstream assets must match `scripts/native/brand-lock.json`, with v1.2.2 commit `13741fedd7d3b28b57aa9e74d99700c2f663aa9c`. A version string alone is insufficient. The small lock file is a byte-identical verification input copied from the brand profile's SSOT lock; it is not an independent brand specification.

Inputs contain schema 1, register, exactly 12 slide records, text slot values, chart categories/series, table values and notes. All text slots are required. Long text is rejected by a conservative fixed-layout capacity guard, never silently shrunk or dropped. Native slots are intentionally line-based; fresh content must be short enough for the selected archetype. This generator does not automatically produce arbitrary narrative outlines, add rows/series, reflow long paragraphs, or author new layouts. Inspect the rendered fresh-content output before real use.

To recapture an explicitly selected production source:

```sh
node scripts/native/capture.mjs --source-root SOURCE_HTML_DIR \
  --output-dir native --brand-root BRAND_SNAPSHOT_DIR
```

Capture does not alter source files. It only normalizes the viewer transform and hides review controls for observation; it applies no native-only typography, color or layout CSS overrides.

## Validation and delivery boundaries

Build intermediates, raw/candidate PPTX, previews, inspections, validation reports and edited test copies belong under `native/work/`. Only the revision-specific deliverable decks listed in `native/QA.md` belong in `native/output/`. Old failed/superseded drafts are excluded from distributables.

Required verification: finalizer integrity/layout/font/native-object/import checks, full 24-slide actual rendering and visual review, source-content coverage, master/layout/theme and attached-connector OOXML inspection, chart/workbook consistency, font floor, fresh JSON builds, and import/edit/save/reopen tests of text/table/chart/diagram nodes. `style_ooxml.py` applies narrowly scoped font scheme, character tracking and table style/border changes before finalization; final exported bytes must be inspected again.

Worker testing is artifact-tool/OOXML/render testing. Main owns actual PowerPoint application verification. r4 opened without repair, but Office showed black table borders; that revision is rejected. Main verified r6 Paper in actual PowerPoint: no repair dialog, black grid removed, fine horizontal rules and correct soft-surface header. This verifies the table compatibility fix, not all 24 slides or Windows Office portability. Main also confirmed r7 Paper opens as 12 slides without a repair dialog and accepted all four Paper/Ink slide 3/6 renders. Actual r7 Ink application review remains controller-owned. No Windows PowerPoint, Google Slides or field projection test is claimed.

Artifact Tool import/re-export does not retain the embedded literal chart workbook by itself. `smoke.mjs` explicitly restores the generator's original snapshot and updates the corresponding literal cells from the edited chart caches, then validates chart/workbook agreement. `restore_chart_workbook.py` rejects formulas, unsupported ranges and multi-sheet workbooks. This repair is narrowly scoped to this generator's own literal-data snapshot; it is not a general preservation claim for arbitrary imported PPTX workbooks.
