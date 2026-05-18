# deck-outline.md Template

```markdown
---
type: deck-outline
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
version: "stage2-v1"
language: zh-CN
scenario: formal-company-report
audience: 
objective: 
source_materials_used:
  - input/source_index.md
target_slide_count: 0
deck_status: not-generated
deck_link: ""
design_system: output/design.md
preview_artifact: output/visual-brief.html
evidence_policy: official facts, media claims, stakeholder advocacy, provider statements, inference, and open questions must remain separated
---

# <Deck Title>

## Deck Intent

<Explain what this deck is for, what it is not for, and what decision or communication outcome it supports.>

## Required Questions

1. 
2. 
3. 

## Narrative Arc

```text
<start>
  -> <development>
  -> <decision / action>
  -> <watchlist / handover>
```

## Key Messaging Summary

- **中心思想：**
- **核心判断 1：**
- **核心判断 2：**
- **核心判断 3：**

## Slide-by-Slide Production Contract

---

## Slide 1: <短标题>

- **action_title:** <Conclusion-first slide claim.>
- **core_message:** <One-sentence governing thought.>
- **evidence:**
  - Official fact / media report / stakeholder advocacy / provider statement / inference / open question: <claim and source reference>
- **content_blocks:**
  - <block 1>
  - <block 2>
  - <block 3>
- **visual_intent:** <Visual idea aligned to design.md.>
- **layout_hint:** <Layout archetype and density guidance.>
- **evidence_label:** <label shown on slide>
- **decision_questions:**
  - <question, if any>
- **speaker_note_hint:** <What the presenter should say or avoid.>
- **motherboard_prompt:** <Prompt/spec for 16:9 visual reference.>
- **pptx_reconstruction_notes:** <Editable objects required; background notes; required terms.>
- **required_terms:** []
- **forbidden_terms:** []

---

## Slide 2: <短标题>

- **action_title:**
- **core_message:**
- **evidence:**
- **content_blocks:**
- **visual_intent:**
- **layout_hint:**
- **evidence_label:**
- **decision_questions:** []
- **speaker_note_hint:**
- **motherboard_prompt:**
- **pptx_reconstruction_notes:**
- **required_terms:** []
- **forbidden_terms:** []

## Downstream Generation Params

```yaml
visual_motherboard:
  aspect_ratio: "16:9"
  language: "zh-CN with English terms preserved"
  slide_count: 0
  use_design_system: "output/design.md"
  text_policy: "text-included visual references by default"
  contact_sheet_required: true
  avoid: []
pptx_render_params:
  editable_text_required: true
  chinese_font: "Microsoft YaHei"
  english_font: "Calibri"
  body_minimum_pt: 16
  preserve_evidence_labels: true
  allow_image_layers_for:
    - backgrounds
    - icons
    - complex infographics
gamma_connector_params:
  format: presentation
  numCards: 0
  theme_hint: ""
```

## Review Questions

1. 是否保留当前页数和 narrative arc？
2. 哪些 wording 可以作为 approved external wording？
3. 哪些 slides 需要先做 visual motherboard sample？
```
