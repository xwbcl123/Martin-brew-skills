# NotebookLM design.md Template

This is a NotebookLM-oriented `design.md` template. It should be compact enough to ingest as a source, but concrete enough to steer visual output.

Canonical reference:

- `.agents/skills/martin-pptx-skill/templates/design-template.md`

```markdown
---
type: design-system
context: <project-or-customer-context>
date: YYYY-MM-DD
status: source
theme: <theme-name>
theme_id: <theme-id-if-any>
canonical_file: design.md
output_language: <deck-output-language>
---

# Design System: <Deck / Theme Name>

**Run ID:** `<run_id>`
**Scenario:** `<customer-communication | research-report | formal-company-report | custom>`
**Source:** `<theme metadata / reference deck / user direction>`
**Baseline / Theme:** `<theme or reference>`
**Canonical file:** `design.md`

## 1. Visual Thesis

<Describe the visual goal, emotional tone, and business context in 3-5 sentences.>

Design adjectives:

- <adjective>
- <adjective>
- <adjective>

Avoid:

- <visual anti-pattern>
- <visual anti-pattern>
- <visual anti-pattern>

## 2. Color Palette & Roles

| Token | Color | Role |
| --- | --- | --- |
| Primary | `#000000` | Main headings / high emphasis |
| Background | `#FFFFFF` | Slide background |
| Card | `#F7F7F7` | Panels and content cards |
| Accent | `#0066CC` | Dividers, chips, selected highlights |
| Warning | `#CC3300` | Real risk / constraint only |
| Body | `#333333` | Main text |
| Secondary Text | `#666666` | Captions and source notes |

Usage rules:

- <rule>
- <rule>
- <rule>

## 3. Typography Rules

NotebookLM output:

- Use clean executive sans-serif typography.
- Use large readable titles and body text.
- Prefer concise phrases over long paragraphs.

Formal PPTX fallback policy:

- Chinese: `Microsoft YaHei` / `微软雅黑`
- English: `Calibri`

Hierarchy:

| Level | Use | Minimum guidance |
| --- | --- | ---: |
| Title | Slide action title | large |
| H2 | Card heading | medium-large |
| Body | Explanations / bullets | readable |
| Source note | References / evidence notes | compact but readable |

## 4. Layout Grammar

Preferred slide archetypes:

1. <archetype, e.g. three-card thesis slide>
2. <archetype, e.g. two-column evidence / implication slide>
3. <archetype, e.g. timeline / regulatory clock>
4. <archetype, e.g. matrix / operating model>
5. <archetype, e.g. final references slide>

Density:

- <density rule>
- <readability rule>

## 5. Component Grammar

Evidence tags / chips:

- Fill:
- Stroke:
- Text:
- Meaning:

Cards:

- Shape:
- Padding:
- Header:
- Body:

Timelines / matrices:

- Node style:
- Connector style:
- Highlight rules:

## 6. Image and Icon Direction

Use:

- <image/icon direction>
- <image/icon direction>

Avoid:

- <image/icon anti-pattern>
- <image/icon anti-pattern>

## 7. NotebookLM Generation Instructions

- Generate a `<deck-output-language>` executive deck.
- Follow the imported `deck-outline.md` for content and slide order.
- Use this design file only for style and layout behavior.
- Use compact evidence labels and readable references.
- Preserve uncertainty labels such as planned, reported, draft, or analytical inference.
- Do not invent facts, dates, institutions, model names, quotes, or regulatory milestones.

## 8. Negative Rules

- Do not turn the deck into a generic topic presentation.
- Do not use tiny text.
- Do not overuse warning colors.
- Do not use decorative elements that look like evidence.
- Do not invent unsupported claims.
- Do not claim the exported PPTX is editable unless QC proves native text exists.
```
