# ImageGen Artifact Plan Template

Use this as the Stage 3 production contract for Option 6. A real run should save it as `output/motherboard_imagegen/artifact_plan.md`.

---
type: imagegen-artifact-plan
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
upstream_outline: output/deck-outline.md
upstream_spec: output/deck-spec.md
status: draft
artifact_mode: hybrid
batch_size_limit: 10
---

# ImageGen Artifact Plan

## Purpose

Use image generation to raise the visual ceiling of the deck. Do not substitute deterministic SVG/PIL/HTML screenshots as the official image-gen artifact pass unless Martin explicitly accepts that downgrade.

## Inputs

- `output/deck-outline.md`
- `output/deck-spec.md`
- Source/evidence index:

## Artifact Mode

Choose one:

- `full-slide-motherboard`: one 16:9 image per slide, useful for visual taste and route comparison.
- `component-kit`: reusable visual elements, icons, scene panels, backgrounds, and diagram pieces for PPTX assembly.
- `hybrid`: full-slide motherboard for direction plus component kit for editable reconstruction.
- `textless-background`: image-gen backgrounds only; all text rebuilt natively.

Default if uncertain: `hybrid`.

## Text Policy

- Visual motherboard images may include short headline/label text for visual reference.
- Exact claims, legal/regulatory wording, evidence labels, tables, speaker notes, and dense Chinese text must be rebuilt as native PPTX text.
- If text fidelity is critical, generate textless backgrounds or components.

## Batch Plan

| batch | slides/components | count | status | qc path |
|---|---|---:|---|---|
| batch_01 | S01-S10 | 10 | planned | `output/motherboard_batches/batch_01/qc_report_batch_01.md` |
| batch_02 | S11-SN | 0 | planned |  |

Rules:

- Maximum 10 image-generation calls per batch.
- Stop after each batch for contact sheet + QC + cooldown.
- Do not repeatedly retry into cooldown.

## Prompt Manifest

| artifact_id | prompt file | output file | visual intent | forbidden elements |
|---|---|---|---|---|
| `slide_01` | `motherboard_imagegen/prompts/slide_01_prompt.md` | `motherboard_batches/batch_01/slide_01.png` |  | fake logos; flags; unsupported numbers |

## Per-Prompt Template

```text
Generate a premium 16:9 executive presentation visual in zh-CN.
Topic:
Slide action title:
Core message:
Visual metaphor:
Design system:
Required visible short labels:
Keep as native PPTX later:
Forbidden:
Output intent:
```

## Component Kit Schema

Use this section when `artifact_mode` is `component-kit` or `hybrid`.

| component_id | type | slide use | background | target size | output | notes |
|---|---|---|---|---|---|---|
| `cmp_01` | icon / scene / diagram / panel / texture | S01 | transparent / solid / full-bleed |  |  |  |

## Batch QC

For each batch, create:

- `contact_sheet.png`
- `qc_report_batch_XX.md`

QC must check:

- image count
- aspect ratio
- visual quality
- style consistency
- text legibility
- prompt drift
- factual/evidence safety
- which slides require regeneration
- which text must be rebuilt natively

## Artifact Inventory

| artifact_id | output | method | source/spec section | QC status | limitations |
|---|---|---|---|---|---|
