# Multi-Route Assembly QC Template

Use this as the Stage 4 route comparison record for Option 6. A real run should save it as `output/route_scorecard.md`.

---
type: multi-route-assembly-qc
run_id: YYYYMMDD_exp-xxx-short-slug
date: YYYY-MM-DD
status: draft
routes:
  - gamma
  - local_pptx
  - optional_third_route
---

# Multi-Route Assembly QC

## Inputs

- `output/deck-outline.md`
- `output/deck-spec.md`
- `output/motherboard_full/contact_sheet.png` or batch contact sheets
- Artifact inventory:

## Route Outputs

| route | tool/owner | pptx | pdf | contact sheet | qc report | status |
|---|---|---|---|---|---|---|
| Gamma AI | Codex/Gamma connector |  |  |  |  |  |
| Local PPTX | Codex / pptx skill / Presentations |  |  |  |  |  |
| Optional Route C | Opus/Claude Code/Gemini/etc. |  |  |  |  |  |

## Route Scorecard

Score: 1 = poor, 3 = acceptable, 5 = strong.

| criterion | Gamma | Local PPTX | Route C | notes |
|---|---:|---:|---:|---|
| Visual quality |  |  |  |  |
| Alignment to deck-spec |  |  |  |  |
| Narrative fidelity |  |  |  |  |
| Text fidelity |  |  |  |  |
| Editability |  |  |  |  |
| Evidence safety |  |  |  |  |
| Render quality |  |  |  |  |
| Production cost / speed |  |  |  |  |

## Findings

### Gamma AI

- Strengths:
- Weaknesses:
- Best use:

### Local PPTX

- Strengths:
- Weaknesses:
- Best use:

### Optional Route C

- Strengths:
- Weaknesses:
- Best use:

## Recommendation

- Preferred route:
- Backup route:
- Required hardening:
- External-use blockers:

## Mandatory Evidence

- Slide counts checked:
- Rendered PNG/PDF exists:
- Contact sheets inspected:
- `text_extraction.json` exists for editable PPTX route:
- Text Fidelity Gate:
- Editability Gate:

## Handover Note

Summarize what the next agent/human should do first.
