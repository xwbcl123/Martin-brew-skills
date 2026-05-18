# Handover Template

```markdown
# Handover

## Run

- Run ID:
- Scenario:
- Current stage:
- Target output:
- Main route:
- Backup route:
- Date:

## Current Status

<One paragraph summary of what has been completed and what remains.>

## Confirmed Artifacts

- `input/brief.md`
- `input/source_index.md`
- `output/design.md`
- `output/style-preview.html`
- `output/deck-outline.md`
- `output/visual-brief.html`
- `output/motherboard_full/contact_sheet.png`
- `output/full_deck_option5/deck.pptx`
- `output/full_deck_option5/qc_report.md`

## Pending Human Review

| Artifact | Review Needed | Decision Needed |
| --- | --- | --- |

## Gate Status

| Gate | Status | Notes |
| --- | --- | --- |
| BG Gate |  |  |
| Text Fidelity Gate |  |  |
| Render Gate |  |  |
| Editability Gate |  |  |
| Font/Readability Gate |  |  |

## Blockers

- 

## Next Actions

1. 
2. 
3. 

## Next Commands

```bash
# Example commands; replace with real paths.
python scripts/render_pptx.py --pptx output/full_deck_option5/deck.pptx --out output/full_deck_option5/rendered
python scripts/extract_pptx_text_metrics.py --pptx output/full_deck_option5/deck.pptx --out output/full_deck_option5/text_extraction.json
python scripts/text_fidelity_gate.py --outline output/deck-outline.md --text-extraction output/full_deck_option5/text_extraction.json --out output/full_deck_option5/text_fidelity_gate.md
```

## Continuation Prompt

```text
Continue <run_id> from:
runs/<run_id>/handover.md

Use confirmed artifacts:
- input/brief.md
- input/source_index.md
- output/design.md
- output/deck-outline.md
- output/motherboard_full/contact_sheet.png
- output/full_deck_option5/qc_report.md

Current task:
<next action>

Important constraints:
- Preserve design.md as visual SSOT.
- Preserve deck-outline.md as narrative/content SSOT.
- Formal PPTX must keep critical text editable.
- Rerun BG Gate and Text Fidelity Gate before delivery.
```

## Environment Notes

- Local repo:
- Python version:
- Rendering tool:
- PPTX library:
- Runtime limitations:
```
