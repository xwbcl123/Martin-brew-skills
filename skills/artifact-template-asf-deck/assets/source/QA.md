# ASF HTML QA — v1.0.0

Scope: Paper and Georgia Ink HTML, each 10 core slides + 2 appendices; index and 24-slide overview. This record covers HTML only. Native Office deliverables have a separate owner.

## Real-browser evidence

`qa/regression.cjs` runs bundled Playwright against installed Chrome through a temporary 127.0.0.1 server. Results are in `qa/evidence/regression.json`; these are browser checks, not mocked DOM simulations.

- All 24 page hashes resolve to the correct active slide; 24 full viewport screenshots are captured at 1920 × 1080.
- Every visible text run remains inside the slide canvas; deck metadata, chart values, evidence headers/status and icon codes use at least 24px. Georgia heading roles remain unchanged.
- Previous/Next accept both Space and Enter. Arrow keys, PageUp/PageDown, canvas Space, Home/End and R work once per event; boundary buttons disable correctly.
- Counter clicks do not advance; a focused footer that becomes hidden transfers focus to the new slide. The current counter has a polite live region. Footer Enter returns to index.
- Hash reload and per-deck stored position restore correctly; both half-screen click directions work.
- Print shows all 12 slides and hides controls. Actual PDFs contain 12 page objects each, with the expected headings in slide order. Printed inactive pages explicitly use column flex layout.
- Index/overview are checked at 320, 360, 390, 430, 600, 768, 820, 1024, 1366, 1440 and 1920px without horizontal scrolling.
- Overview filters return 12 Paper, 12 Ink or 24 total; notes accept Enter; thumbnail Enter opens the correct slide. Both thumbnail focus rings remain inset and visible within the clipped frame.
- Appendix cards compare Paper 11 / Ink 11 / Paper 12 / Ink 12. Pair anchors 6, 11 and 12 exist.
- The Chinese toolbox title has `lang="zh-CN"`, 1.35 line height, normal tracking and an unbroken “视觉工具箱” phrase at 390px.
- Upstream brand hashes and the peeled commit are checked. No browser exception or failed HTTP response is allowed.

Contact sheets `qa/evidence/pairs-01-04.jpg`, `pairs-05-08.jpg` and `pairs-09-12.jpg` cover all 24 actual screenshots. Full-size pages 6 and 12, narrow index, and both overview focus states are checked visually. Paper's open columns, Ink's continuous process band, warm paper, Georgia and existing spacing rhythm are preserved.

## Practical boundaries

This Chrome/macOS run observes Courier New fallback for metadata when Consolas is unavailable. It does not verify Windows/macOS Office reopening, native connectors or editable charts, venue projection, Safari/Firefox, or browser fullscreen transitions. Spline Sans is local and licensed; system font files are not distributed.

No actual event photo or approved final contact was supplied: retain those labeled replacement slots until production content is approved. Historical builders, request briefs and the frozen audit package are excluded from the release source.

## Latest user surface iteration — 2026-10-08

The guarded live source delta adds paired soft background/border treatments and the Paper cover shared-record identifier only. The release retains that exact CSS and identifier while preserving all audit fixes. Re-run: **237 passed assertions = original 213 + 24 per-slide contrast checks**; 24 fresh screenshots and two fresh 12-page PDFs with verified heading order; zero browser/HTTP errors. All visible text colors are resolved through a browser Canvas into sRGB, alpha-composited over actual ancestor backgrounds, then evaluated with the WCAG relative luminance formula. Minimum text contrast is **4.5436:1**, exceeding 4.5:1 across both decks. Actual OKLch/color-mix background and border values and resolved RGB samples are recorded per surface in `qa/evidence/regression.json`. Decorative borders are intentionally low contrast and are not treated as text. No geometry, typography, content or upstream tokens changed.

## User hierarchy feedback — slides 3/6, 2026-10-08

Both registers now use a 44px icon rail to the left of each content group. Number/role sits directly above the title and shares its left edge; body follows the title in the same text column. Process arrows align with the title row and stay clear of numbers. This CSS-only change retains all live text, body font sizes, soft-surface declarations, upstream tokens and navigation/audit fixes. Paper open columns and Ink continuous process band remain intact.

241 assertions pass: prior 237 plus four scoped hierarchy checks for Paper/Ink slides 3/6. Each check measures left-icon separation, number/title alignment, vertical order and text-group bounds; the existing canvas/font/contrast checks also pass. All 24 slide screenshots and both 12-page ordered PDFs were refreshed. Minimum text contrast remains 4.5436:1. Final review images: `qa/evidence/paper-03.png`, `ink-03.png`, `paper-06.png`, `ink-06.png`. Full-size images were reviewed. Native capture must use the latest `qa/release-source.json` hashes.

Packaged-source note: evidence paths above are produced by running qa/regression.cjs on a workspace copy. Historical screenshots/PDFs and runtime logs are intentionally not bundled.
