# ASF Paper / Ink — HTML template family v1.0.0

Status: **selected Paper + Georgia Ink HTML family**. Browser and print validation are recorded in QA.md. Native Office deliverables and acceptance are maintained separately.

## Entry points

- `index.html` — comparison entry, two full-deck links, ten archetype links, selected Georgia Ink and a labeled historical title specimen.
- `paper.html` — 12-slide Paper template (10 core + 2 appendices).
- `ink.html` — 12-slide Ink template (10 core + 2 appendices); editorial serif-led default.
- `overview.html` — 24 live HTML thumbnails, register filter, slide deep links and presenter guidance.
- `review.css` — local entry/overview styling.

Open the entry file in Open Design, or open it locally with its sibling files and assets present. Deck links use `#1` through `#12`. The canvas is 1920 × 1080; arrow keys, space, PageUp/PageDown, Home/End and R use the supplied framework. Position is stored locally per deck path. The lower-left slide link returns to the comparison. Browser fullscreen can be used with the scale-to-fit canvas. There is no autoplay or outbound request in the artifacts.

## Authoritative sources and provenance

Read-only source: ASF brand upstream Git repository, pinned below.

Read AGENTS.md, llms.txt, DESIGN.md, CSS/JSON tokens, registry components/patterns/icons and CHANGELOG.md. The consumption snapshot was extracted using `git show v1.2.2:<path>`, not copied from an unverified working-tree state.

- Locked version: **v1.2.2**.
- Commit: **13741fedd7d3b28b57aa9e74d99700c2f663aa9c**.
- Annotated tag object: **dd07a281cf22bed7287e53cdde39e3fbb8222866** (not the commit).
- Snapshot: `assets/asf-brand-v1.2.2/`.
- Integrity ledger: `assets/asf-brand-v1.2.2/PROVENANCE.json` (SHA-256 per file).
- 19 byte-identical upstream files, one governance-path-redacted AGENTS.md, and two local provenance ledgers are filesystem read-only (0444).
- Includes original CSS/JSON, all seven SVG logos, Spline Sans 700 WOFF2 and OFL license, registry and source guidance.
- Logos are inlined from the corresponding original SVG, retaining its geometry, live Spline Sans text and official fills. Only a sizing class is added. The original SVG files remain untouched in the snapshot.
- Brand tokens and assets are unchanged. Packaged AGENTS.md omits a private governance path; provenance records that documentation-only export delta. The upstream repository was not changed.

### Geometry rationale

The selected family uses warm paper or dark ink grounds, a compact official logo, Georgia editorial headlines, fine horizontal separators, rectangular visual frames, flat evidence tables and clear horizontal process sequences. The deck geometry is local to this template; it does not add or alter upstream ASF tokens. No internal reference material or meeting content is distributed.

## One brand, two registers

The supplied CSS is imported verbatim. Each slide declares `data-register="paper"` or `data-register="ink"`. Accent, kicker, focus, border, raised surfaces, muted text and semantic chart/status colors use register-resolved `--asf-*` variables. Ground and foreground use the official register values because this release supplies those as core tokens rather than register aliases.

| Role | Paper | Ink |
|---|---|---|
| Ground | `--asf-paper` | `--asf-ink-900` |
| Text | `--asf-ink-900` | `--asf-on-ink` |
| Secondary text | `--asf-text-muted` | `--asf-text-muted` |
| Accent | `--asf-accent` | `--asf-accent` |
| Raised layer | `--asf-raised` | `--asf-raised` |
| Rule | `--asf-border` | `--asf-border` |

Paper publishes: warm full-page stock, fine rules, open editorial groups, flat tables, restrained media frames.

Ink convenes: the same serif identity, dark full-page ground, quieter header rules, dark raised argument/process layers and sparing signal color. No decorative neon, glow, glass, gradients or fake event imagery.

The three chart series use the register-resolved positive / info / warning roles. Text identifies every series and every value; colors are not the only distinction. Semantic chart/status colors are an intentional brand-defined exception to the single decorative accent rule.

### Registry consumption

Stable references: publication feature, button/text link, status tag and logo/header conventions. Draft references: page-top headings, media-frame with caption/provenance and agenda/process treatment. Their deck-specific geometry is proposed below. No gap component is represented as an approved ASF component; in particular, the comparison is not an ASF data dashboard, and the event placeholder is not a speaker card. Retired glass/glow utilities are not used by slide content.

Review controls occupy the lower safe margin. The stage shadow is disabled; no slide contains a glass panel or blurred shadow.

## Portable typography

Per DESIGN.md §7:

- Display: Georgia, with Times New Roman / serif fallback; regular 400, italic used selectively.
- Body: Arial, Helvetica / sans-serif fallback.
- Metadata: Consolas, Courier New / monospace fallback.
- Logos: supplied local Spline Sans 700, preserving the genuine mark.
- Historical Ink title specimen on the index only: sanctioned Spline Sans 700 event-led headline. It is not the default deck typography and is not automatically approved for native Office text.

Georgia / Arial / Consolas are system fonts, not redistributed files. Exact installed fallback selection requires browser/Office verification on the destination machine. Spline Sans is bundled with its OFL license.

## Proposed deck geometry — not new ASF tokens

These are local layout proposals for this exploration only. No `--asf-*` token was added or changed. The source web layout does not define a 1920-pixel slide grid; numeric diagram/chart geometry and local `--deck-*` values must therefore be reviewed before a native template is standardized.

| Proposal | HTML geometry | Purpose |
|---|---|---|
| Canvas | 1920 × 1080 | 16:9 framework contract |
| Edge inset | 128 px | Consistent editorial field |
| Content width | 1664 px | Clear space around mark and type |
| Header | 100 px + 48 px separation | Logo / archetype metadata |
| Main region | 604 px nominal | Content finishes above footer band |
| Footer | 56 px from bottom; 128 px sides | Local ASF identity and page number |
| Main title | 120 px cover; 104 px divider/closing | At most two deliberate lines |
| Body title | 88 px; 64 px for table/story | Density-sensitive hierarchy |
| Pull quote | 80 px | Four readable lines |
| Body | 28–36 px | Readable live type |
| Metadata | 24 px | Quiet document information |
| Logo | 325 × 60 px | Ring radius ~22.5 px; surrounding space exceeds radius |
| Rules | supplied 1 px token | Fine editorial structure |
| Corners | supplied square geometry | No rounded presentation cards |
| Image slot | 360 px tall | Framed placeholder with external provenance caption |

The index/overview are responsive review surfaces, not presentation slides. Below 760 px they reflow to one column; compact cover previews receive a minimum height to separate logo, title and caption. Full decks always preserve their 16:9 geometry and scale as a unit.

## Archetype and future native PowerPoint mapping

Same semantic content and notes in both registers. The chart is editable DOM; tables are HTML tables; the process is text plus DOM blocks and connectors. No live slide content is rasterized.

| # | Archetype | Composition / persuasion role | Future native mapping |
|---|---|---|---|
| 01 | Cover | Two-line proposition; quiet contextual line | Background fill, live title/subtitle, logo image |
| 02 | Divider | Chapter number + single transition statement | Section-layout title and text boxes |
| 03 | Governing claim | Dominant claim above three supporting arguments | Title + three live text groups; Ink raised rectangles |
| 04 | Comparison | Grouped horizontal bars + compact interpretation | Editable native clustered bar chart and value labels |
| 05 | Evidence | Four flat rows; explicit review status | Native table and text status labels |
| 06 | System | Four stages; separate review-loop statement | Native shapes, text and connectors |
| 07 | Pull quote | Large original statement; clear sample designation | Live Georgia quote and separate source label |
| 08 | Event story | Framed approved-photo slot + editorial explanation | Image placeholder, caption, story text boxes |
| 09 | Decision | Two distinct alternatives, then recommendation slot | Two live comparison groups + action text |
| 10 | Closing | Next step + explicit contact placeholder | Live title, action and contact placeholders |

Illustrative chart data (sample score / 100, not ASF metrics):

| Dimension | Working notes | Shared record | Reviewed brief |
|---|---:|---:|---:|
| Traceability | 40 | 65 | 85 |
| Comparability | 55 | 70 | 80 |
| Reusability | 35 | 60 | 90 |

All bar widths are `--v / --max × 100%` with one shared `--max:100`. Every value is outside its bar. No factual quantitative claim is intended.

Evidence states are a sample workflow, not a record of current ASF work. The quote is original, unattributed sample copy. There was no approved local event-photo provenance supplied, so page 8 deliberately contains the requested “Replace with approved event photograph” slot. No photo search or download was performed.

### Native production proposal (future work)

Use 13⅓ × 7½ inch native slide size and map coordinates by `inches = px / 144` (font points = px / 2). This gives cover 60 pt, primary title 44 pt and body 14–18 pt. Metadata now uses 24 px (12 pt at the documented native mapping); rerun native fit checks after conversion. Native Office mapping must use Georgia / Arial / Consolas explicitly, not fallback stacks. Render only the logo to a high-resolution transparent PNG if portability requires it; keep all other text, chart data, tables and system geometry native and editable.

This HTML package does not provide evidence of native layouts, masters, theme XML or PPTX editability. Print and Office font metrics have not been approved. HTML print is tested separately through Chromium; see QA.md. Office production certification belongs to the native owner.

## Selected family and validation boundary

Paper and Georgia Ink are locked as one template family. Spline Sans is retained only as a labeled historical title specimen in the index. Each register contains 10 core archetypes plus 2 appendices (24 slides total).

HTML browser regression and print evidence are recorded in `QA.md` and `qa/`. This HTML delivery does not certify native PowerPoint editability or cross-platform Office font metrics. Approved photo provenance and final contact details remain replacement obligations before external use.

## Template language correction — 2026-10-07

Ink defaults to English across its 10 core slides, two appendices, navigation, accessibility labels and presenter notes. Georgia / Arial / Consolas remains the portable mapping; the ASF logo retains Spline Sans. This supersedes earlier Chinese-localization guidance for Ink. Historic visual enhancement scripts contain Chinese copy and must not be rerun unchanged against this English template.

## Paired-template contract — 2026-10-07

Paper and Ink are maintained as a symmetric pair. Apply shared structural, functional and geometry refinements to both in the same delivery; retain register-specific ASF colors and deliberate editorial treatments. Both now have 10 core slides, two icon/architecture appendices, official local icon symbols, editable cover architectures, identical navigation safeguards and compact non-cover headers/footers. English is the default template language. The delivered HTML is the editable source. Unsafe historical builders are excluded; edit it directly and run `qa/regression.cjs`.

## User-approved soft surfaces — 2026-10-08

The latest user iteration is preserved: Paper highlighted surfaces use `oklch(0.93100730 0.01191615 133.380526)` (pale sand green, approximately #E5EAE2); selected borders/connectors mix 18% register accent with 82% page ground. Ink uses 55% ground / 45% raised and borders mixing 65% existing border / 35% ground. These user-approved treatments are local CSS declarations, not changes to upstream ASF tokens. The exact live selectors are retained; text, icons, geometry and typography are unchanged. The Paper cover shared-record node retains its new `paper-cover-shared-record` identifier.

## Selected argument/process hierarchy — 2026-10-08

Slides 3 and 6 in both registers place each icon in a 44px left rail, with number/role directly above the Georgia title and body aligned beneath it. The local grid introduces a 20px column gap and preserves the existing typography, colors and content. Process arrows align to the title row. This supersedes the prior floating-right argument icons and detached process numbers; all other slide geometry is retained.
