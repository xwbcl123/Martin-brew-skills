
# ASF Brand Guideline v1.2

> **One brand, two registers.** The website's black-and-white editorial style (*Field Notes*) and the ASF-2026 mint-on-dark identity (*Borealis*) are one system. They share one logo, one ink and one teal-to-mint signal family. **Paper** is how ASF *publishes*; **Ink** is how ASF *convenes*.

Machine-readable source of truth: [`tokens/tokens.css`](tokens/tokens.css) · [`tokens/tokens.json`](tokens/tokens.json). Logo: [`logo/`](logo/). Icons: [`docs/icons.md`](docs/icons.md). Components: [`docs/components.md`](docs/components.md) · [`registry/`](registry/). Font: [`fonts/`](fonts/). Changes: [`CHANGELOG.md`](CHANGELOG.md).

## 1. Registers — which one to use

| | **Register A · Paper** | **Register B · Ink** |
|---|---|---|
| Use for | Website, publications, reports, PDF, newsletter body | Events, LinkedIn, stage slides, podcast covers, social cards, newsletter masthead |
| Ground | Paper `#F4F1E9` / White `#FFFFFF` | Ink-900 `#0B0F19` |
| Accent | Teal `--asf-signal-600` `#137B70` | Mint `--asf-signal-200` `#16FFBB` |
| Headline face | Serif display | Serif display or Spline Sans (event headlines) |
| Voice | Editorial, durable, evidence-first | Convening, energetic, forward |

Mixing is allowed by **band**: an Ink band (masthead, footer, publication pane) can sit inside a Paper page. Never mix accents inside one band.

## 2. Logo

Geometry and wordmark are unchanged from ASF-2026: a ring with “AI” plus the single-line wordmark “AI SECURITY **FORUM**”. Only the colourway follows the register.

| File | Use |
|---|---|
| `logo/asf-logo-ink.svg` | **Primary on dark** — white ring, mint “AI” and “FORUM”, `#F0FCFF` wordmark |
| `logo/asf-logo-paper.svg` | **Primary on light** — ink ring, teal “AI” and “FORUM”, ink wordmark |
| `logo/asf-logo-mono-ink.svg` | Single colour — print, co-branding strips |
| `logo/asf-logo-mono-white.svg` | Single colour — over photography and video |
| `logo/asf-mark-paper.svg` | Ring-mark only — website header (≤ 40px), small spaces |
| `logo/asf-mark-ink.svg` | Ring-mark on filled disc — favicon, social avatar, podcast app icon |
| `logo/asf-mark-reverse.svg` | Ring-mark, transparent, white ring + mint “AI” — on ink-800/900 artwork (LinkedIn avatar zone, podcast covers, slides) |

- **Clear space:** at least the ring radius on every side. **Minimum size:** ring-mark 24px; full lockup 160px wide.
- **Don't:** use mint on paper or white (1.16:1 contrast). Don't add glow, gradient or glass behind the mark. Don't set the wordmark in the serif. Don't let partner marks out-size ASF in co-branding.
- The SVGs use live text in Spline Sans. For external print vendors, export outlined versions.

## 3. Colour

### Signal ramp (shared)
| Token | Hex | Role |
|---|---|---|
| `--asf-signal-600` | `#137B70` | Teal. Text, links and accents on Paper |
| `--asf-signal-400` | `#29DDDA` | Cyan. Charts, secondary rules on Ink |
| `--asf-signal-300` | `#62D7BF` | Signal light. Focus ring and kicker on Ink |
| `--asf-signal-200` | `#16FFBB` | Mint. Logo and primary accent, **on Ink only** |

### Ink — one family, two depths
| Token | Hex | Role |
|---|---|---|
| `--asf-ink-900` | `#0B0F19` | **Ground** on Ink; **text colour** on Paper |
| `--asf-ink-800` | `#16212C` | **Raised**: cards, bands, footer, publication pane, buttons on Paper |
| `--asf-ink-700` | `#263241` | Rules and borders on Ink |

Rule: *900 is what you stand on, 800 is what sits on it.* Never place two full-bleed sections of 900 and 800 next to each other without a rule between them.

### Paper and text
| Token | Hex | Role |
|---|---|---|
| `--asf-paper` | `#F4F1E9` | Page ground |
| `--asf-surface` | `#FFFFFF` | Cards, reading panes |
| `--asf-rule` | `#D7D2C7` | 1px rules |
| `--asf-muted` | `#5F6971` | Secondary text (darkened from `#667078` for AA) |
| `--asf-on-ink` / `--asf-on-ink-muted` | `#EEF5F2` / `#B9CBC0` | Text on Ink |
| `--asf-amber` | `#F1C84B` | “Unconfirmed” or warning status, on Ink only |

### Semantic status and data viz
| Role | On Paper | On Ink | Contrast (Paper / Ink-900) |
|---|---|---|---|
| Positive / confirmed | `#137B70` | `#16FFBB` | 4.54 / 14.64 |
| Info | `#1F6FA8` | `#37A7E7` | 4.77 / 7.15 |
| Warning / unconfirmed | `#8A6100` | `#F1C84B` | 4.91 / 11.95 |
| Critical | `#B3261E` | `#FF8A7A` | 5.79 / 8.36 |

Use `--asf-positive`, `--asf-info`, `--asf-warning` and `--asf-critical`; they resolve per register. Chart series order: signal-600 → blue → amber → cyan → muted, five at most. Always label status in text.

### Verified contrast (WCAG 2.x)
| Pair | Ratio |
|---|---|
| Ink-900 on Paper | 16.97:1 |
| Muted on Paper / White | 4.97:1 / 5.61:1 |
| Teal on Paper | 4.54:1 — use ≥ 16px |
| White on Teal | 5.13:1 |
| On-ink on Ink-800 | 14.73:1 |
| On-ink-muted on Ink-800 | 9.60:1 |
| Mint on Ink-900 / Ink-800 | 14.64:1 / 12.47:1 |
| Signal-300 on Ink-800 | 9.31:1 |
| Amber on Ink-900 | 11.95:1 |

## 4. Typography — four roles

| Role | Stack | Use |
|---|---|---|
| Display | Iowan Old Style → Palatino → Georgia | H1–H3, publication titles, pull quotes. Regular 400; italic only for a final line |
| Body | Avenir Next → Avenir → Segoe UI | Body 16–18px / 1.62, measure ≈ 67ch; UI labels 14px/600 |
| Metadata | SFMono → Consolas → Liberation Mono | Kickers, dates, versions, status. 11–13px uppercase, +0.08em; **11px is the floor** |
| Brand | **Spline Sans 700** (self-hosted, OFL-1.1) · Barlow Condensed 600 | Wordmark always; Ink-register event headlines and stage or social titles only |

Spline Sans has no weight above 700. Every stack ends in PingFang SC / Microsoft YaHei for Chinese text.

## 5. UI elements

- **Shape:** panels, cards and tags are square (`--asf-radius` 0). Controls use 2px (`--asf-radius-control`), media 4px (`--asf-radius-media`). Round only for the ring-mark, avatars and timeline nodes. 1px rules, flat rows.
- **Elevation:** hard offset “paper stack” shadows only (`--asf-shadow-stack-sm/md/lg`, `-ink`), with no blur. Mark the current item with `--asf-shadow-marker` (3px inset accent bar).
- **Buttons:** Paper uses an Ink-800 primary and an outlined secondary. Ink uses a mint primary with `#06120F` text and a signal-300 outlined secondary. Minimum target 44px.
- **Focus:** 3px ring, teal on Paper and signal-300 on Ink.
- **Status:** a mono uppercase tag in a 1px box. Always write status as text, never colour alone.
- **Motion (three speeds):**
  - **Feedback** (hover, press, toggle) uses `--asf-duration` 180ms with `--asf-ease`.
  - **Step** (scrolly highlight, accordion) uses `--asf-duration-step` 320ms.
  - **Reveal** (entrance, Ink register only) uses `--asf-duration-reveal` 800ms with `--asf-ease-reveal`.
  - Hover travel is at most `--asf-move-max` 2px. No autoplay, parallax, scroll hijack or infinite decoration.
  - `prefers-reduced-motion` zeroes every duration through the token file.
  - Generative backgrounds (e.g. the old SignalField) need a static fallback.
- **Icons:** 24px grid, 1.7 stroke, round, `currentColor`, always with a text label. Use the sprite `icons/asf-icons.svg` first and Lucide (stroke 1.7) as the fallback. No shields, padlocks or brains.
- **Borealis elements:**
  - **Keep:** the mint accent rule (2px × 72px) and the mono kicker.
  - **Limit:** chamfer corners (`--asf-chamfer-frame`) to stage and social frames only.
  - **Retire:** glass blur, glow shadows and gradient washes.

## 6. Channel rules

| Channel | Register | Notes |
|---|---|---|
| Website | Paper, with Ink header band optional and Ink footer | Ring-mark in header; Field Notes layout contract stays in asf-website `DESIGN.md` |
| Publications / PDF | Paper | Ink publication pane allowed on covers |
| LinkedIn banner (1584×396) | Ink | Left 400px avatar zone in ink-800 carrying the reverse ring-mark; serif headline plus a mint kicker |
| LinkedIn avatar | Ink | `asf-mark-ink.svg` |
| Newsletter | Ink masthead band, Paper body | Teal kicker in the body |
| Partner-event slides (e.g. HCE) | Host template for **cover and thank-you only**; every content page in the ASF template (Ink for stage, Paper for documents) | No nesting of ASF pages inside the host frame. Applies to every partner event. Mint keyword highlight; chamfer allowed |
| Podcast cover (3000²) | Ink-800 | Reverse ring-mark top-left, “ASF Podcast” top-right, mint rule, serif title (last word italic) |

## 7. Office documents (PPTX, DOCX)
Office files cannot carry CSS font stacks and recipients may lack brand fonts. Map roles to portable fonts: display **Georgia**, body **Arial**, metadata **Consolas**. Spline Sans appears only inside logo images (PNG rendered from `logo/*.svg`). Colours come from `tokens/tokens.json`. Partner events: host template for cover and thank-you only; every content page uses the ASF template.

## 8. Layout
Shell `min(1220px, 100% − 64px)`. Breakpoints: 900px (navigation collapses), 620px (single column), 360px (small devices; test at 320px). z-index scale: raised 1 · sticky 20 · progress 30 · overlay 100.

