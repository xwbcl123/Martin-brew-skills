# ASF Paper / Ink HTML templates v1.0.0

Paper and Georgia Ink form one selected template family. Each register has 10 core archetypes and 2 appendices, for 24 slides total. The Spline Sans title specimen in the index is labeled historical reference.

Open `index.html` with the sibling files and `assets/` present. `overview.html` compares all 12 pairs. Full decks use a fixed 1920 × 1080 canvas; links `paper.html#1`–`#12` and `ink.html#1`–`#12` open individual slides.

Edit the HTML directly. Shared navigation lives in `deck.js`; review styling lives in `review.css`. There is no regeneration step or historical builder. Native files are managed separately under `native/`.

## Browser regression

Run `node qa/regression.cjs` with Playwright, Chrome and Poppler's `pdftotext` available. Set `ASF_PLAYWRIGHT` to the installed Playwright package directory and optionally `ASF_PDFTOTEXT` to its executable. The script uses a temporary loopback server, closes it after completion, and writes screenshots, two 12-page PDFs and machine-readable results to `qa/evidence/`.

`QA.md` records checks and limitations. `qa/FIXES.md` maps the frozen audit findings to the fixes and evidence. Printing uses the browser's Save as PDF with background graphics enabled and zero margins; the CSS defines one slide per page.

## Brand lock

Upstream brand tag: `v1.2.2`. Peeled commit: `13741fedd7d3b28b57aa9e74d99700c2f663aa9c`. Annotated tag object: `dd07a281cf22bed7287e53cdde39e3fbb8222866`.

The read-only local snapshot is `assets/asf-brand-v1.2.2/`. Its two provenance ledgers list 20 immutable upstream files with SHA-256 hashes. Bundled Spline Sans includes its OFL license; Georgia, Arial and Consolas are system font targets, not redistributed fonts. Source AGENTS.md is retained for private Vault use and may be omitted by the public packager.

Sample data, event photo and contact slots are explicitly illustrative or replaceable. Native Office editing, font metrics and venue projection remain separate acceptance tasks.
