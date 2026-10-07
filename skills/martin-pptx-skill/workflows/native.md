# Native PPTX

Use for editable charts/tables/diagrams, existing deck edits, or ordinary deck requests. Read the current host presentation skill's implementation and template guidance. Codex uses JS artifact-tool; legacy Python builders are not its default.

1. Reuse the source material, selected template and existing approval. Internally define one purpose and required content for each slide. Retain good topic titles; do not force every title into an action claim.
2. Build or edit native text, required tables/charts and requested editable diagrams. Use original logo assets. Acquire planned explanatory or supporting imagery through the host's permitted image tools.
   Before assembly, apply [visual/text composition](../references/visual-contract.md): declare text mode, map components to nearby native labels and accept the real asset in its planned region. Baked text is permitted when the delivery allows it and wording/meaning pass QA; preserve all explicitly promised editable objects.
3. Apply container padding efficiency: tighten text box margins (3.6–5 pt top/bottom, 7.2–9 pt left/right) so body font stays >= 14 pt and card titles >= 16 pt without overflow.
4. Regulatory and topic cohesion: group foundational regulations or concepts together (e.g. NIS2 -> DORA -> CRA) before showing vendor operational support and joint synthesis.
5. Put sources in speaker notes; keep visible citations if the source/template requires them. Preserve evidence uncertainty.
6. Export a draft, run the host finalizer, inspect rendered pages and fix content or layout defects. Check template fonts and fit directly; no automatic pptx-polish step or blanket size remap.
7. Validate representative native object editability and exact source text/numbers. Deliver the final file. A motherboard, Gamma alternate and NotebookLM run are not prerequisites.
8. Rounded rectangle corner control: for cards and container panels (`ROUNDED_RECTANGLE`), set `shape.adjustments[0] = 0.03 ~ 0.05` (3% to 5% radius, matching reference benchmark); never allow PowerPoint's default 0.1667 (16.7%) which produces bulbous, childish corners.

If importing a deck loses native objects, compare against the original and repair only the requested scope or select a compatible host adapter. Do not flatten required evidence objects to work around backend limitations.
