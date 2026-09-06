# Experiment — {{hypothesis_slug}}

- unit_id: `{{unit_id}}`
- mapping_status: `{{mapping_status}}`

## Pipeline

```text
00_input → {{steps}} → 99_observation
```

## Navigation

- [pipeline / IPO / gates](pipeline.md)
- [00_input](00_input/)
- [phase]({{first_step}}/phase.md)
- [callouts]({{first_step}}/callouts.md)
- [unassigned gaps](unassigned-gaps.md)
- [99_observation](99_observation.md)

Human comments belong in this README or `99_observation.md`.
Stage 7 updates only script-owned callout files.
IPO and gate checklists live in `pipeline.md` and `*/phase.md`.
