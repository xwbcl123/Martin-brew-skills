# Martin Brand System v1.0

## 1. Brand architecture

Classify the artifact before styling:

| Context | Primary brand | Default visual system | Primary Logo |
|---|---|---|---|
| Life: personal life, learning, reflection, insight, creative work | Martin | Light Editorial | Balanced Signal M / Martin |
| Life: high-impact digital cover, personal keynote, story | Martin | Martin-Borealis | Balanced Signal M / Martin |
| Work: company responsibility, organizational communication | Organization Brand | approved organization template / Work Editorial | Organization Brand |
| Explicit Anthropic artifact | Anthropic | Archived upstream style | As supplied by Anthropic |

Use one primary brand per artifact. On Work outputs, Martin may appear as a byline, not as a co-equal Logo. A co-branded lockup requires an explicit brief.

## 2. Shared foundation

**Verbal personality**: Calm Authority · Evidence-led Insight · Human Curiosity.

- Lead with a judgment, tension, or useful implication.
- Support claims with evidence, source boundaries, and explicit uncertainty.
- Explain technical ideas plainly without flattening their complexity.
- Prefer concrete nouns and verbs over corporate abstractions.
- End with meaning, consequence, or a decision—not a motivational slogan.

Avoid corporate filler, exaggerated certainty, performative jargon, cold bureaucratic language, vague futurism, and decorative complexity.

## 3. Martin / Life identity

**Promise**: `From complexity to clarity` / `化繁为简，洞见本质`.

**Thinking method**:

> 由此及彼，由表及里，去粗存精，去伪存真。

### Content pillars

1. Cybersecurity and AI through a systems lens.
2. Sense-making: patterns, trade-offs, and second-order effects.
3. Personal practice: learning, health, relationships, and reflection.
4. Creative experiments: tools, visual thinking, and new forms of expression.

### Light Editorial tokens

| Token | Value | Purpose |
|---|---|---|
| `life.navy` | `#091231` | Logo, headings, formal anchor |
| `life.cyan` | `#29DDDA` | Primary accent |
| `life.mint` | `#16FFBB` | Secondary digital accent |
| `life.ice` | `#37A7E7` | Data and diagram support |
| `life.canvas` | `#F5F7F6` | Default canvas |
| `life.ink` | `#172033` | Body text |
| `life.slate` | `#697386` | Secondary text |
| `life.line` | `#DCE3E6` | Dividers and grids |

Use a flat navy Logo as the formal master. Use blue-green gradients only on large digital surfaces. Body text contrast must meet WCAG AA; never set body copy in mint or cyan.

### Typography

- Display/headings: Spline Sans 600/700; fallback Arial/Helvetica.
- Screen body: Barlow 400/500; fallback Arial/Helvetica.
- Long-form editorial: Charter; Chinese fallback Source Han Serif SC / Noto Serif CJK SC / Songti SC.
- Chinese headings/UI: Source Han Sans SC / Noto Sans CJK SC / Microsoft YaHei.
- Artistic `Martin` wordmark is a Logo asset, not a general-purpose typeface.

### Layout

- Use an 8-point spacing rhythm and a restrained column grid.
- Prefer one clear visual argument per page/slide.
- Use generous margins, strong title hierarchy, and left alignment.
- Allow asymmetry in Life covers, but keep reading order unambiguous.
- Use the signal curve as a divider, chart highlight, or subtle motion path; never as repeated decoration.

### Imagery

- Prefer real evidence: personal photography, screenshots, artifacts, diagrams, or data.
- Personal photography may be quiet, observational, and naturally lit.
- Illustrations use thin geometry, navy structure, and one blue-green accent.
- Do not use generic team stock photos, neon cyberpunk, circuit textures, glowing locks, or fake dashboards.

### Data visualization

- Navy is the baseline series; cyan is the primary comparison; mint marks positive change; ice blue supports secondary context.
- Use red only for genuine risk/error, not decoration.
- Label the insight directly and keep legends close to evidence.
- Do not use 3D charts, rainbow palettes, or gradients across quantitative scales.

## 4. Martin-Borealis variant

Use only when the user asks for Borealis/dark/expressive treatment or when the artifact is a personal digital cover, keynote, or story-led piece.

- Canvas: `#091231` with the approved Borealis image as an atmospheric layer.
- Cards: `rgba(10, 18, 49, 0.78)`, 12 px radius, 1 px cyan/white translucent border.
- Heading: `#F0FCFF`; body: `#E0E7EA`.
- Accent: cyan and mint; ice blue is supportive.
- Use glass effects sparingly and never behind dense reading text.
- Use the new M/Martin Logo family; never use the obsolete organization Publish Logo.

Canonical variant file: `references/martin-borealis.md`.

## 5. Organization Brand / Work identity

Mission: cybersecurity capability and transparency, external cooperation, compliance, customer trust, stakeholder continuity, and cybersecurity market access.

### Work tokens

- Deck Red `#B42318`
- Charcoal `#202124`
- Cool Gray `#525252`
- Light Gray `#D9D9D9`
- White `#FFFFFF`
- Typography: Arial / Microsoft YaHei fallback

### Work rules

- Treat `assets/organization-placeholder/organization-logo.svg` as a non-production sample only. Supply authorized organization assets and an approved template at runtime.
- Keep parent organization as a separate endorsement outside the core Logo clear space.
- Use the mission line only at readable sizes.
- Keep layouts clean, light, evidence-led, and restrained.
- Do not import the personal blue-green Logo or Borealis background into Work artifacts.

## 6. Document behavior

| Artifact | Life default | Work default |
|---|---|---|
| Blog/essay | Light Editorial; personal byline | Not normally applicable |
| Insight report | Light Editorial, dense evidence | Work Editorial, department Logo |
| One-pager | Light Editorial | Work palette and organization identity |
| Slides/PPTX | Personal light or Borealis if requested | Organization-approved PPTX template supplied at runtime |
| Social/cover | Digital gradient allowed | Work palette; no personal Logo |
| Resume/portfolio | Personal identity | N/A unless explicitly internal |

## 7. Accessibility and production

- Maintain WCAG AA contrast for body text.
- Provide flat one-color Logo variants and meaningful alt text.
- Never encode a conclusion by color alone; use labels or shape as well.
- Confirm fonts exist or use documented fallbacks.
- Verify small-size Logo legibility, slide overflow, document density, and dark/light reversal before shipping.

### Identity lockup alignment QA

- A document header has at most two primary zones: the title/content zone and one identity lockup. Do not place the Logo, byline, and metadata as independent flex or grid siblings.
- Group the Logo and byline/metadata in one container and choose one explicit alignment axis. Right alignment is the default for editorial one-pagers and reports; centered alignment is reserved for ceremonial compositions; left alignment is appropriate for horizontal wordmark lockups.
- Never mix a parent container aligned to one edge with a child Logo independently aligned to another edge unless the offset is part of a documented lockup.
- Measure the visible optical bounds of raster and SVG assets, not only their canvas or `viewBox`. Prefer tight-bound production assets; when transparent padding is intentional, record the optical inset and compensate explicitly.
- Verify the final HTML and PDF render independently. For a shared-edge lockup, the visible Logo edge and metadata edge should differ by no more than `2 px` on screen or `1 pt` in print.
- At the intended output size, confirm that the emblem remains legible, the byline reads as part of the same unit, and neither element appears to float away from the other.

### Fixed-canvas footer QA

- For a hard one-page A4 artifact, anchor the footer to the bottom of the page content box rather than placing it immediately after the last content block. The content-box height is the physical page height minus the declared top and bottom margins; for A4 with `15 mm` margins, it is `267 mm`.
- In WeasyPrint, do not rely on root `body` `min-height` plus flex auto margins for this contract; paged-media layout may leave the footer visibly high. Use a page wrapper with an explicit fixed-canvas height and a bottom-anchored footer, then enforce the one-page limit and overlap checks.
- Verify the rendered PDF geometrically. For standard editorial footers, the footer text bottom should sit `15-22 mm` from the physical page bottom. More than `30 mm` of unexplained space below the footer is a QA failure.
- Verify that the footer does not overlap the final content block and that the PDF page count remains within the document contract. Absolute positioning is allowed only for a hard single-page canvas whose content fit has been verified.
- Browser HTML must have a narrow-screen fallback. Below the document breakpoint, release the fixed height, return the footer to normal flow, and retain a visible content-to-footer gap; never let a print-oriented footer cover reflowed mobile content.
- Inspect PDF and HTML independently: PDF at physical-page geometry, desktop HTML at the intended canvas width, and mobile HTML at `375 px` when the HTML is delivered.

## 8. Governance

- Brand system owner: Martin Xie.
- Current version: 1.0, 2026-07-21.
- Packaged assets live under `assets/`; organization assets remain runtime inputs.
- Update the guideline, affected profile, named theme, and consuming templates together.
- Explicit task instructions override these defaults.
