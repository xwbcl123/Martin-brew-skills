# QC Report Template

```markdown
# QC Report: <Run / Artifact>

## Summary

- Run ID:
- Scenario:
- Target output:
- Main route:
- Backup route:
- Status: pass / warn / fail
- Reviewer:
- Date:

## Artifacts

| Artifact | Status | Notes |
| --- | --- | --- |
| `input/brief.md` |  |  |
| `input/source_index.md` |  |  |
| `output/design.md` |  |  |
| `output/style-preview.html` |  |  |
| `output/deck-outline.md` |  |  |
| `output/motherboard_full/contact_sheet.png` |  |  |
| `output/full_deck_option5/deck.pptx` |  |  |
| `output/full_deck_option5/rendered/deck.pdf` |  |  |
| `output/full_deck_option5/text_extraction.json` |  |  |
| `output/full_deck_option5/text_fidelity_gate.md` |  |  |
| `handover.md` |  |  |

## Gate Summary

| Gate | Status | Evidence | Required Action |
| --- | --- | --- | --- |
| Scaffold Gate |  |  |  |
| Outline Gate |  |  |  |
| Design Gate |  |  |  |
| Motherboard Gate |  |  |  |
| Route Gate |  |  |  |
| BG Gate |  |  |  |
| Render Gate |  |  |  |
| Editability Gate |  |  |  |
| Text Fidelity Gate |  |  |  |
| Font/Readability Gate |  |  |  |
| Evidence Gate |  |  |  |
| Handover Gate |  |  |  |

## Route Decision

- Selected main route:
- Route rationale:
- Backup route:
- Backup status:
- Stop condition:

## BG Gate

- Background master path:
- Status:
- Kept elements:
- Removed elements:
- Warnings:
- Failures:
- Human review notes:

## Editability Check

```text
slides:
total_text_shapes:
total_image_shapes:
min_font_pt:
max_font_pt:
```

Interpretation:

- 

## Render QC

| Check | Result | Notes |
| --- | --- | --- |
| PPTX opens |  |  |
| PDF export |  |  |
| PNG render |  |  |
| Slide count |  |  |
| Contact sheet |  |  |
| Major clipping |  |  |
| Major overlap |  |  |

## Text Fidelity Gate

```text
slides:
pass:
warn:
fail:
```

Warnings:

- 

Failures:

- 

## Evidence / Source Integrity

- Official facts preserved:
- Inference labels preserved:
- Open questions preserved:
- Unsupported claims found:

## Known Tradeoffs

- 

## Defects and Fixes

| ID | Severity | Finding | Status | Fix / Owner |
| --- | --- | --- | --- | --- |

## Verdict

- Final status:
- Can deliver: yes/no
- Conditions:
- Next action:
```
