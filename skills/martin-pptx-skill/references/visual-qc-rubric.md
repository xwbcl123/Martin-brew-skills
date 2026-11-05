# Deck Visual QC Rubric

Apply to every formal deck before delivery, after `verify_deck_compliance.py` (or the host finalizer) passes and the full deck is rendered. A compliance PASS is necessary, not sufficient: it checks geometry and font floors, not whether the page communicates.

## Procedure

1. Choose a reference deck: the latest Martin-accepted deck on the same template and audience. Prefer the most recent accepted deck in the same series.
2. Render both decks to images. Compare every candidate slide side by side with the closest reference page (same pattern or purpose). Look at the images; do not score from XML or script output.
3. Score the 8 items below, 0 / 1 / 2 each, total 16.
4. Record in the session QA log: per-item scores, total, the weakest 3 slides, and the fix for each.
5. Gate: total below 13/16, or any item at 0, blocks delivery. Fix the weakest slides first, rerender, rescore. The producing agent self-scores; the reviewer (CoS) rescores independently before forwarding.

## Items

| # | Item | 2 | 1 | 0 |
|---|---|---|---|---|
| 1 | Action titles | Every content title states the page's conclusion, at most two lines | Some topic labels or vague claims | Mostly topic labels |
| 2 | Information structure | One clear pattern per page (map + status, hub, chain, decision, table, timeline); reading order obvious | Structure present but crowded or ambiguous | Text walls or card grids without logic |
| 3 | Brand and template | Real template masters, cover and title-only layouts, palette with A50C0B used sparingly, Arial + Microsoft YaHei | Minor drift (off colors, inconsistent axes) | Blank layouts with hand-drawn chrome, foreign palette, emoji |
| 4 | Density and fit | Readable at presentation scale, no clipping, detail moved to notes | One or two crowded pages | Overflow, shrunk text, or near-empty pages |
| 5 | Visual assets | Purposeful textless visuals with anchored native labels on the pages that need them | Visuals generic or detached from text | No visuals, or emoji/icon cards instead of evidence |
| 6 | Decision usability | Ask, recommendation and pending owner explicit; next steps dated with owners | Ask present but buried | No clear ask or next step |
| 7 | Sources and accuracy | Speaker notes and source ids on every slide; facts match sources; uncertainty kept | Notes or sources missing on some slides | No notes, or unsupported claims |
| 8 | Reference comparison | Each page equal to or better than its reference counterpart | Some pages clearly weaker | Most pages clearly weaker |
