# design.md Template

```markdown
# Design System: <Deck / Theme Name>

**Run ID:** `<run_id>`  
**Scenario:** `<scenario>`  
**Source:** `<source basis>`  
**Baseline / Theme:** `<theme or reference>`  
**Canonical file:** `design.md`

## 1. Visual Thesis & Atmosphere

<Describe the visual goal, emotional tone, and business context.>

Design adjectives:

- 
- 
- 

Avoid:

- 
- 
- 

## 2. Color Palette & Roles

| Token | Color | Role |
| --- | --- | --- |
| Primary | `#000000` |  |
| Background | `#FFFFFF` |  |
| Card | `#F3F6FA` |  |
| Accent | `#0066CC` |  |
| Warning | `#CC3300` |  |
| Body | `#333333` |  |

Usage rules:

- 
- 
- 

## 3. Typography Rules

HTML / visual preview:

- Heading:
- Body:
- Numeric / tags:

Formal PPTX reconstruction:

- Chinese: `Microsoft YaHei` / `微软雅黑`
- English: `Calibri`

Hierarchy:

| Level | Use | PPTX minimum |
| --- | --- | ---: |
| Title | Slide title / action title | 28 pt |
| H1 | Section-level claim | 22 pt |
| H2 | Card heading | 20 pt |
| H3 | Matrix / evidence label | 18 pt |
| Body | Bullets and explanations | 16 pt |

Tone:

- 
- 

## 4. Layout Grammar

Preferred slide archetypes:

1. 
2. 
3. 

Grid:

- 

Spacing:

- 

Density:

- 

## 5. Component Grammar

### Evidence Tags / Chips

- Fill:
- Stroke:
- Text:
- Meaning:

### Cards

- Shape:
- Radius:
- Padding:
- Header:
- Body:

### Tables / Matrices

- Header:
- Row height:
- Column style:
- Highlight rules:

### Timelines / Roadmaps

- Node style:
- Connector style:
- Status tags:

### Callouts

- Use cases:
- Tone:
- Warning style:

## 6. Image and Icon Direction

Use:

- 

Avoid:

- 

For PPTX reconstruction:

- Image layers may be non-editable.
- Business-critical text must be rebuilt as editable PPTX objects.

## 7. Motion / Interaction Intent

For HTML preview only:

- 

For deck output:

- Static by default.

## 8. Negative Rules

- Do not use tiny text.
- Do not flatten PPTX title/body text into images.
- Do not invent unsupported claims.
- Do not use decorative elements that look like evidence.
- Do not overuse warning colors.

## 9. PPTX Font Policy

- Chinese: `Microsoft YaHei` / `微软雅黑`
- English: `Calibri`
- Titles and body must be editable.
- Backgrounds, icons, and complex infographics may be images.

## 10. Theme Library Reuse Notes

Recommended future theme path:

```text
theme-library/<theme-id>/
├── theme.yaml
├── design.md
├── style-preview.html
├── reference/
└── examples/
```
```
