# D5 — design.md

## Header

```yaml
deliverable: D5-design
title: "{{PROJECT_NAME}} — Visual System"
date: {{ISO_DATE}}
author: martin-outcome-package
version: 1.0
```

---

## Visual Thesis

> One sentence describing the overall design direction.

{{VISUAL_THESIS}}

## Color Tokens

| Token | Hex | HSL | Usage |
|-------|-----|-----|-------|
| `primary` | {{HEX}} | {{HSL}} | Main brand/accent |
| `secondary` | {{HEX}} | {{HSL}} | Supporting accent |
| `background` | {{HEX}} | {{HSL}} | Page/slide background |
| `surface` | {{HEX}} | {{HSL}} | Card/panel background |
| `text-primary` | {{HEX}} | {{HSL}} | Body text |
| `text-secondary` | {{HEX}} | {{HSL}} | Captions, metadata |
| `accent-positive` | {{HEX}} | {{HSL}} | Success, growth |
| `accent-negative` | {{HEX}} | {{HSL}} | Warning, risk |
| `accent-neutral` | {{HEX}} | {{HSL}} | Neutral indicators |

## Typography

| Role | Family | Weight | Size | Line Height |
|------|--------|--------|------|-------------|
| Headline 1 | {{FONT}} | Bold (700) | 36px | 1.2 |
| Headline 2 | {{FONT}} | SemiBold (600) | 28px | 1.25 |
| Headline 3 | {{FONT}} | SemiBold (600) | 22px | 1.3 |
| Body | {{FONT}} | Regular (400) | 16px | 1.5 |
| Caption | {{FONT}} | Regular (400) | 13px | 1.4 |
| Data/Metric | {{MONO_FONT}} | Medium (500) | 24px | 1.2 |

## Grid & Layout

- **Column system**: {{COLUMNS}} columns with {{GUTTER}}px gutter
- **Max content width**: {{MAX_WIDTH}}px
- **Margins**: {{MARGIN}}px horizontal
- **Spacing scale**: 4px base unit (4, 8, 12, 16, 24, 32, 48, 64)

## Component Grammar

### Cards
- Border radius: {{RADIUS}}px
- Shadow: {{SHADOW_SPEC}}
- Padding: {{PADDING}}px

### Callout / Highlight Box
- Left border: 4px solid `primary`
- Background: `surface` at 50% opacity
- Padding: 16px 20px

### Dividers
- Horizontal: 1px solid `text-secondary` at 20% opacity
- Section: 2px solid `primary` at 40% opacity

### Icons
- Style: {{ICON_STYLE}} (outline / filled / duotone)
- Size: 20px inline, 32px feature, 48px hero
- Color: inherits from context

## Chart & Table Grammar

### Charts
- Color sequence: `primary`, `secondary`, `accent-positive`, `accent-neutral`, `accent-negative`
- Grid lines: `text-secondary` at 15% opacity
- Labels: Caption typography
- Data points: 6px circles with 2px stroke

### Tables
- Header: `primary` background, white text, Bold weight
- Rows: alternating `background` / `surface`
- Borders: 1px solid `text-secondary` at 20% opacity
- Cell padding: 8px 12px

## Image Direction

- **Photography**: {{PHOTO_STYLE}}
- **Illustrations**: {{ILLUSTRATION_STYLE}}
- **Aspect ratios**: 16:9 for hero, 4:3 for content, 1:1 for icons/avatars

## Negative Rules

> What to explicitly avoid.

- {{NEGATIVE_RULE_1}}
- {{NEGATIVE_RULE_2}}
- {{NEGATIVE_RULE_3}}
