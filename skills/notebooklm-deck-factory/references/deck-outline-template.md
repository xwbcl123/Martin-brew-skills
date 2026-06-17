# NotebookLM deck-outline.md Template

This is a NotebookLM-oriented outline template. It is intentionally lighter than the full `martin-pptx-skill` production contract, but it preserves the fields NotebookLM needs to follow the intended structure.

Canonical references:

- `.claude/commands/deck-outline.md`
- `.agents/skills/martin-pptx-skill/templates/deck-outline-template.md`

```markdown
---
type: deck-outline
context: <project-or-customer-context>
date: YYYY-MM-DD
version: "notebooklm-v1"
language: <source-outline-language>
output_language: <deck-output-language>
audience: <specific audience>
objective: <communication outcome>
scenario: customer-communication
target_slide_count: <N>
design_source: design/<theme>-design.md
deck_status: not-generated
deck_link: ""
evidence_policy: separate official fact, media signal, provider statement, analytical inference, internal narrative, and open question
---

# <Deck Title>

## Deck Intent

<One paragraph explaining what this deck is for, what it is not for, and what decision or discussion it supports.>

## Source Priority for NotebookLM

1. Follow this `deck-outline.md` for slide order, narrative spine, titles, and main claims.
2. Use synthesis reports for converged findings and contradiction handling.
3. Use deep research reports for evidence backing and references.
4. Use `design.md` only for visual style and output behavior, not content.

## Required Questions

1. <Question the deck must answer>
2. <Question the deck must answer>
3. <Question the deck must answer>

## Narrative Arc

```text
<opening context>
  -> <capability / evidence shift>
  -> <implication for audience>
  -> <controllable actions>
  -> <discussion / next step>
```

## Key Messaging Summary

- **Central thesis:** <one sentence>
- **Key message 1:** <evidence-backed point>
- **Key message 2:** <evidence-backed point>
- **Key message 3:** <action / implication>

## Slide-by-Slide Contract

---

### Slide 1: <Short slide theme>

- **action_title:** <Conclusion-first title to show on slide.>
- **core_message:** <One-sentence governing thought.>
- **evidence_label:** <Official / First-party | Credible Media Signal | Analytical Inference | Internal Narrative>
- **content_blocks:**
  - <block 1>
  - <block 2>
  - <block 3>
- **visual_intent:** <cards / timeline / matrix / bridge / closing / references>
- **speaker_note_hint:** <what the presenter should emphasize or avoid>
- **must_keep_terms:** []
- **avoid_terms:** []

---

### Slide 2: <Short slide theme>

- **action_title:**
- **core_message:**
- **evidence_label:**
- **content_blocks:**
  -
- **visual_intent:**
- **speaker_note_hint:**
- **must_keep_terms:** []
- **avoid_terms:** []

## References / Evidence Policy

- Use compact source markers or evidence labels in body slides.
- Include a final references/evidence slide when the deck is evidence-heavy.
- Do not convert draft, planned, or reported claims into settled facts.
- Do not invent facts, dates, institutions, quotes, or regulatory milestones.

## NotebookLM Generation Notes

```yaml
format: slide-deck
slide_deck_format: detailed
length: default
language: <deck-output-language>
must_follow_outline_order: true
research_reports_are_evidence_only: true
include_final_references_slide: true
```
```
