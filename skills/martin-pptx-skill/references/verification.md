# Executable Visual Contract v1

Use for new decks or material visual revisions. One `visual-contract.json` is the machine-readable production contract, separate from the content Outline. A Design.md or visual-contract.md can explain decisions, but link to this JSON for geometry/text truth rather than keeping divergent copies. For a small existing-deck correction, reuse its contract and recheck only changed dependencies; do not retroactively require a full asset pipeline for an unrelated typo fix.

The standard-library verifier is `scripts/verify_visual_contract.py`. It never runs image generation or the PPTX builder. A nonzero exit blocks the dependent stage. Host finalizer/template validators remain required for package/render behavior outside this script.

## Commands and phase boundary

```bash
python3 <skill>/scripts/verify_visual_contract.py visual-contract.json --stage plan --out qa/plan-check.json
# Collect actual assets, freeze their SHA-256, rerun plan if the binding changed,
# inspect the files with their planned label placement, then record reviews.
python3 <skill>/scripts/verify_visual_contract.py visual-contract.json --stage assets --out qa/assembly-gate.json
# Only after success: record actual build_started_at; assemble/finalize/render.
python3 <skill>/scripts/verify_visual_contract.py visual-contract.json --stage final --out qa/final-check.json
```

Receipts never overwrite; use revisioned names on retries. All paths inside the JSON resolve relative to its directory and must remain inside that root, including symlinks. Copy the relevant outline/style/source evidence into this run root if needed. Output path is caller-selected. No workstation paths or raw run outputs belong in the reusable skill.

The receipt reports `plan_sha256`, a canonical hash of all contract fields except `evidence`. Changing labels, geometry, asset hashes, style or sources invalidates reviews/gates. Fill actual asset hashes before obtaining the final plan binding and writing asset review records. `evidence` only adds phase records; it cannot alter the production plan.

## Contract fields

- `schema_version`: integer `1`.
- `canvas`: `[width,height]` in CSS px (96 dpi).
- `outline`: `{path,sha256,approval_ref}`; existing user approval/decision reference, not a new permission request.
- `style`: `{source:{path,sha256},palette:{role:"#RRGGBB"}}`; retained selected template/Design/Style reference, same palette passed to prompts and builder.
- `assets`: objects `{id,path,origin,sha256}`. `origin`: `generated`, `source`, `reused`. Generated assets also require `tool` and `prompt:{path,sha256}`. Planned asset files/hashes may be absent at `plan`; actual bytes and hashes are mandatory at `assets` and `final`. No assets is valid for fully native pages.
- `slides`: ordered objects below; order must equal final PPTX slide order. Unique slide and asset IDs.

Each slide:

```json
{
  "id": "slide-01",
  "message": "Approved communication purpose",
  "visual_form": "diagram",
  "text_mode": "integrated_native",
  "reading_order": "left-to-right",
  "placements": [{"asset_id":"visual-01","box":[80,120,1120,350],"fit":"contain"}],
  "labels": [{
    "id":"label-01", "text":"Exact approved label", "box":[100,480,240,40],
    "asset_id":"visual-01", "component_id":"component-01", "component_box":[100,340,240,120]
  }]
}
```

Forms: `infographic`, `diagram`, `chart`, `illustration`, `photo`, `background`, `evidence`, `text`. Text modes: `native`, `integrated_native`, `embedded_text`, `none`.

- `labels` are expected native slide text objects with explicit, ungrouped geometry; one object per declared label. The final verifier checks exact text (whitespace normalized) and boxes within 2 px. Avoid declaring two indistinguishable same-text labels as separate objects without distinct geometry support; the current verifier rejects ambiguity.
- Integrated mode requires labels mapped to components inside the placed image. Default maximum label-to-component gap is 48 px; optional `max_label_gap_px` may not exceed 10% of the shorter canvas edge. Distant callouts require `connector:[[component_x,component_y],[label_x,label_y]]`. Endpoints must lie in the respective boxes; final PPTX must contain a native connector with matching endpoint bounds. Meaning and visual direction still require review.
- Embedded mode requires nonempty `embedded_text:["exact string",...]` and `editable_visual_text:false`. Native titles may remain in `labels` without component mappings. Image words are verified by actual image review, not OOXML text search.
- Pure native mode needs no image; use `labels` for required text. `none` on a diagram/infographic needs `unlabeled_reason`; an atmosphere photo does not need explanatory labels.
- Charts require `data_source:{path,sha256}` and `chart_mode:"native"|"image"`. Image charts must set `editable_data:false`. Final validation checks a native chart exists when promised; source data-to-mark accuracy remains a separate data/visual review, not a claim this script performs arithmetic/chart rendering validation.
- Image `fit` is planned intent, not a claim that image bytes have a particular appearance. Native picture frame is checked against `box`; cropping, alpha edges and final-size legibility remain visual QA. Grouped/transcoded images need a reviewed adapter; do not silently bypass failed checks.

## Review records (ordinary UTF-8 JSON files)

Each evidence reference is `{path,sha256}`. A review file contains:

```json
{
  "plan_sha256":"actual binding from verifier",
  "subject_sha256":"actual inspected asset or rendered PNG hash",
  "reviewer":"agent or human identity",
  "reviewed_at":"2026-01-01T12:00:00+00:00",
  "checks":{"subject":"pass","style":"pass","placement":"pass","textless":"pass","mapping":"pass"},
  "notes":"Concrete observations from inspecting this exact file in its planned placement."
}
```

Replace all example values with actual evidence. Allowed passing value is exactly `pass`; missing/pending/fail blocks. Asset checks: `subject/style/placement`, plus `textless/mapping` for integrated mode, `text_accuracy/mapping` for embedded mode, `data_geometry` for charts. A reused asset must be reviewed for its current placement too.

`evidence.asset_reviews` maps asset IDs to review-file references. After the assets stage succeeds, set `evidence.assembly_gate` to that receipt reference and `evidence.build_started_at` to actual timezone-aware build start. Keep the receipt with the builder execution record. Final stage requires recorded build start no earlier than the successful gate; this is record consistency, not independent proof of tool chronology.

`evidence.final`:
- `pptx:{path,sha256}` for actual final file.
- `renders:[{slide_id,path,sha256,pptx_sha256,review:{path,sha256}}]`, one actual rendered image per slide, bound to that PPTX.
- Render review checks: `content/style/legibility/mapping`, plus `text_accuracy` for embedded text and `data_geometry` for charts.

## Honest pass boundary

The script verifies actual file hashes, references, IDs, geometry, declared phase order, required review records, final slide order/count/canvas, expected native labels/connectors, image bytes/frames and chart presence. It rejects stale assets, stale renders and missing evidence. It cannot independently establish that a reviewer really looked, that generated words are correct, or that a renderer truly produced the PNG. Retain real tool/renderer records and inspect actual images. Never present its exit code as automatic semantic or aesthetic acceptance.
