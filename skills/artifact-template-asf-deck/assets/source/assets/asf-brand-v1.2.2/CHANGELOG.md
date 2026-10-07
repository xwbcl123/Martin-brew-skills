# Changelog — ASF Brand Tokens

Versioning (semver on `tokens.css`):
- **major**: rename or remove a token, or change a register's meaning. Consumers must migrate.
- **minor**: add tokens, icons or components (backward compatible).
- **patch**: adjust a value inside the same role, e.g. a contrast fix.

Every release: update the header in `tokens.css`, run `python3 scripts/build-tokens-json.py`, re-run `scripts/coverage-audit.py`, and add an entry here.

## 1.2.2 — 2026-10-03
- Guideline PDF: paper colour now fills every page edge to edge (`@page` background), not only the content box (Martin review).
- Guideline PDF: `asf-logo-mono-ink` shown on a light ground (suffix match picked the ink ground).
- No token changes.

## 1.2.1 — 2026-10-03
- Registry fix: `reader-toc-scrolly` lists Reader/Toc/Scrolly; `icon` lists only Icon.astro (Glyph.astro retired by asf-website S6). No token changes.

## 1.2.0 — 2026-10-03
- Added type roles used by the live website so it can drop raw sizes: `--asf-text-meta` 11px (metadata floor, D-05), `--asf-text-caption` 13px, `--asf-text-ui` 15px, `--asf-text-body` 17px, `--asf-text-h3` 28px.
- No values changed; consumers on 1.1.x upgrade with `use v1.2.0` and no migration.

## 1.1.0 — 2026-10-03
Driven by the live-site coverage audit (`coverage-audit.md`).
- Added shape tokens `--asf-radius-control` 2px, `--asf-radius-media` 4px and `--asf-radius-round`, matching asf-website's live CSS.
- Added elevation: hard offset “paper stack” shadows `--asf-shadow-stack-*` and `--asf-shadow-marker`.
- Added motion: `--asf-ease-reveal`, `--asf-duration-step`, `--asf-duration-reveal`, `--asf-move-max`, plus a global reduced-motion override.
- Added icon tokens and the unified sprite `icons/asf-icons.svg` (15 icons).
- Added layout breakpoints (900 / 620 / 360) and a z-index scale.
- Added semantic status colours (positive / info / warning / critical) for Paper and Ink, plus register-resolved `--asf-positive` and the other three.
- Added `scripts/build-tokens-json.py` and `scripts/coverage-audit.py`.

## 1.0.0 — 2026-10-03
- Initial reconciliation of Field Notes and Borealis: Paper and Ink registers, ink-900/800/700, signal ramp, four type roles, logo kit, Spline Sans 700. Decisions D-01 to D-04.
