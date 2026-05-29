# Option 6 Deck Outline Template

Use this as the Stage 1 narrative contract for Option 6. A real run should save it as `output/deck-outline.md`.

---
type: deck-outline
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
version: option6-outline-v1
language: zh-CN
scenario: formal-company-report
audience:
objective:
target_slide_count:
deck_status: not-generated
deck_link: ""
downstream_spec: output/deck-spec.md
downstream_artifact_plan: output/motherboard_imagegen/artifact_plan.md
routes_expected:
  - gamma
  - local_pptx
---

# <Deck Title>

## Intent

- **What this deck is for:**
- **What this deck is not for:**
- **Decision / discussion outcome:**

## Required Questions

1. <question>
2. <question>
3. <question>

## Narrative Arc

```text
<scene-setting>
  -> <evidence/reaction map>
  -> <inference / implications>
  -> <decision / action>
```

## Key Messaging Summary

- **中心思想:**
- **KMS 1:**
- **KMS 2:**
- **KMS 3:**

## Slide-by-Slide Contract

### Slide 1 - <short title>

- **section:**
- **action_title:**
- **key_message:**
- **evidence_label:**
- **evidence_items:**
  - type:
    claim:
    source_id:
- **content_blocks:**
  - <content block>
- **visual_intent:**
- **layout_hint:**
- **speaker_note_hint:**
- **imagegen_artifact_hint:**
- **pptx_reconstruction_notes:**
  - native editable text:
  - allowed raster background:
  - final text fidelity risk:
- **gamma_notes:**
- **local_pptx_notes:**

---

## Downstream Generation Defaults

```yaml
deck_spec_required: true
artifact_mode: hybrid
image_generation_required: true
batch_size_limit: 10
contact_sheet_required: true
routes_required:
  - gamma
  - local_pptx
routes_optional:
  - third_model_pptx
text_policy: "image tool for visual taste; PPTX native text for factual control"
```

## Human Review Questions

1. Is the narrative arc correct?
2. Are any claims too strong for the evidence?
3. Which slides require visual motherboard samples before full generation?
4. Which route should be primary after route scorecard review?
