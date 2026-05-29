# Open Questions and Future R&D

## Open Product Questions

| Question | Priority | Current Position | Needed Evidence |
| --- | --- | --- | --- |
| How many benchmarks are enough before promotion? | high | Minimum 3 total, 2 formal PPTX. | Additional runs with different deck types. |
| Should theme library become a separate registry? | medium | Use one directory per theme for now. | More reusable themes and metadata needs. |
| How strict should body font threshold be for dense matrices? | medium | 16 pt for body; footer can be smaller. | More render reviews across Office environments. |
| Should `visual-brief.html` be mandatory? | low | Recommended, not mandatory. | User feedback on review speed. |
| Should speaker notes be mandatory for all formal decks? | medium | Editable when present; define per scenario. | More formal deck reviews. |

## Technical Open Questions

| Question | Priority | Current Position | Next Experiment |
| --- | --- | --- | --- |
| Can Option 5 builder become template-driven enough? | high | Needs component extraction. | Implement reusable components and run second benchmark. |
| Can BG Gate be automated without image understanding? | high | Hybrid deterministic + human review likely. | Add allowed/forbidden checklist and screenshot review. |
| Can Text Fidelity Gate detect semantic mismatch robustly? | high | Use structured rules + required/forbidden terms. | Add per-slide required_terms / forbidden_terms in outline. |
| Can Option 3 become reliable PPTX export? | medium | v1 R&D only. | Test HTML component-to-PPTX native mapping. |
| Can Option 4 be vendored or documented cleanly? | medium | Keep optional backup. | Record artifact-tool dependency contract if runtime available. |
| How to validate Office compatibility across Windows/Mac/Google Slides? | medium | Render QC locally first. | Add compatibility checklist and manual review. |

## Known Limitations of This Design Package

1. It defines script contracts, not full script implementations.
2. It does not include PPTX binaries, rendered screenshots, or visual assets.
3. It assumes local implementation can use Python and a local PPTX render/export path.
4. It does not solve every possible semantic fidelity issue; it defines a gate that must be implemented and iterated.
5. It does not require Option 4 runtime and therefore cannot guarantee backup deck generation in every environment.

## Recommended R&D Backlog

### R&D 1 — Option 5 Component Library

Build reusable Python components for:

- title bands
- evidence chips
- two-column contrast
- module architecture diagrams
- control matrices
- roadmaps
- watchlists

Success measure:

- A new formal deck can be built without hand-coding every slide.

### R&D 2 — Structured Outline Fields for Gates

Add to each slide in `deck-outline.md`:

```yaml
required_terms: []
forbidden_terms: []
allowed_title_compression: true/false
must_preserve_evidence_label: true/false
```

Success measure:

- Text Fidelity Gate produces fewer ambiguous warnings.

### R&D 3 — BG Gate Automation

Explore lightweight checks:

- compare background master against OCR/text extraction only when necessary
- use region masks for body area
- keep human visual review for final approval
- create `allowed_elements` and `forbidden_elements` declarations per background master

Success measure:

- Stale body text and charts are consistently caught before overlay.

### R&D 4 — Office Compatibility Matrix

Test formal PPTX outputs in:

- Windows Office
- Mac Office
- Google Slides
- LibreOffice render path

Success measure:

- Font and layout issues are documented and recoverable.

### R&D 5 — Theme Library Registry

Prototype:

```text
theme-library/<theme-id>/
  theme.yaml
  design.md
  style-preview.html
  reference/template.pptx
  examples/contact_sheet.png
```

Success measure:

- Formal and semi-formal themes can be reused without redesign.

## Decision Log To Preserve

- Keep `design.md` canonical.
- Keep `deck-outline.md` separate.
- Keep visual motherboard text-included by default.
- Keep Option 5 as main v0 route.
- Keep Option 4 as independent backup only.
- Keep BG Gate and Text Fidelity Gate mandatory for formal PPTX.
- Keep non-formal stop conditions flexible.
