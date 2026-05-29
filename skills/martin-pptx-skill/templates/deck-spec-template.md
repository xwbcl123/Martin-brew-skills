# Deck Spec Template

Use this as the Stage 2 production contract for Option 6. A real run should save it as `output/deck-spec.md`.

---
type: deck-spec
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
version: stage2-spec-v1
language: zh-CN
scenario: formal-company-report
upstream_outline: output/deck-outline.md
status: draft
target_slide_count: 0
artifact_mode: hybrid
routes_required:
  - gamma
  - local_pptx
routes_optional:
  - third_model_pptx
---

# Deck Spec: <Deck Title>

## 1. Production Intent

- **Audience:**
- **Objective:**
- **Scenario:**
- **Target output:** PPTX + PDF + contact sheets
- **Primary route recommendation:**
- **Evidence policy:**

## 2. Upstream Contract

| item | value |
|---|---|
| Outline source | `output/deck-outline.md` |
| Source index | `input/source_index.md` |
| Known gaps | `input/known_gaps.md` |
| Review owner |  |
| Claims requiring caution |  |

## 3. Global Design System

This section must include everything normally required in `design.md`, then add production details that PPTX routes can execute.

### 3.1 Visual Thesis

<Describe the visual world, tone, audience fit, and why it fits the topic.>

### 3.2 Palette Tokens

| token | hex | role |
|---|---|---|
| navy | `#0B2B5C` | cover / dark panels |
| blue-700 | `#10417F` | section panels |
| blue-500 | `#1F6FD8` | active accents |
| blue-300 | `#7AB0F2` | secondary accents |
| blue-100 | `#E4EEF9` | light cards |
| amber | `#E89A2C` | inference / warning / key dates |
| graphite | `#4A4A4A` | body text |
| white | `#FFFFFF` | dark-background text |

### 3.3 Typography And PPTX Font Policy

- Chinese: `Microsoft YaHei` / `微软雅黑`
- English: `Calibri`
- Title:
- Body:
- Evidence footer:
- Minimum formal PPTX body size:

### 3.4 Layout Grammar

Preferred slide archetypes:

1. <archetype>
2. <archetype>
3. <archetype>

Grid:

Spacing:

Density:

### 3.5 Component Grammar

#### Cards

#### Evidence Tags

#### Tables / Matrices

#### Timelines / Roadmaps

#### Callouts / Warnings

### 3.6 Image Direction

Use:

- <visual direction>

Avoid:

- fake logos
- invented source marks
- decorative elements that look like evidence

### 3.7 Negative Rules

- Do not flatten formal title/body/evidence text into images.
- Do not allow image-gen text to become final factual text.
- Do not continue with programmatic wireframes if the user asked for image-gen/baked visuals.
- Do not skip contact-sheet review.

## 4. Evidence Label System

| label | meaning | visual treatment |
|---|---|---|
| `事实·官方文本` | official source / law / regulator text |  |
| `事实·媒体政策信号` | media-reported policy signal |  |
| `前线信息` | non-public stakeholder/frontline signal |  |
| `推断` | reasoned inference | amber |
| `供应商影响` | downstream implication |  |

Footer rule:

## 5. Slide Production Contract

Repeat for every slide.

### S01 - <Slide Title>

- **section:**
- **action_title:**
- **key_message:**
- **layout_template:**
- **text_blocks:**
  - title:
  - subtitle:
  - body:
- **speaker_notes:**
- **visual_elements:**
- **artifact_refs:**
- **evidence_footer:**
- **image_generation_prompt_seed:**
- **pptx_reconstruction_notes:**
  - native editable text:
  - allowed raster elements:
  - forbidden baked elements:
- **route_notes:**
  - Gamma:
  - Local PPTX:
  - Optional third route:

## 6. Artifact Plan

| artifact_id | slide/component | mode | prompt intent | output path | priority |
|---|---|---|---|---|---|
| `slide_01_motherboard` | S01 | full-slide-motherboard |  | `output/motherboard_batches/batch_01/slide_01.png` | P1 |

Artifact modes:

- `full-slide-motherboard`
- `component-kit`
- `hybrid`
- `textless-background`

Default:

```yaml
artifact_mode: hybrid
batch_size_limit: 10
contact_sheet_required: true
batch_qc_required: true
cooldown_after_each_batch: true
text_policy: "image-gen text is visual reference only; final claims rebuilt as native PPTX text"
```

## 7. PPTX Assembly Plan

### Route A - Gamma AI

- Input:
- Parameters:
- Expected output:
- QC:

### Route B - Local PPTX

- Input:
- Assembly method:
- Native editable text requirements:
- Render/QC:

### Route C - Optional Third Route

- Owner/tool:
- Use when:
- QC:

## 8. QC Gates

| gate | required | pass condition |
|---|---|---|
| Outline/spec consistency | yes | slide count and claims match |
| Motherboard contact sheet | yes | visual direction accepted |
| Batch cooldown | yes | max 10 image-gen calls before QC |
| Render gate | yes | PDF/PNG previews exist |
| Text Fidelity Gate | yes for final | claims match outline/source |
| Editability Gate | yes for formal PPTX | business text is native PPTX |
| Route scorecard | yes for Option 6 | routes compared and recommendation recorded |
