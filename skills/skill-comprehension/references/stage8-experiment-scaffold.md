# Stage 8 Experiment Scaffold

After Stage 4, the Agent writes a structured `scaffold-input.json` from read evidence
and may run `scripts/scaffold_experiment.py`. The script only creates directories and
templates. It never executes the Target Skill.

## Trigger

| When | Action |
|---|---|
| Stage 4 complete | Write `scaffold-input.json`. Optional: generate scaffold. `scaffold_generated` only means files exist. |
| Stage 7 after Martin answers | Update script-owned `callouts.md` / `unassigned-gaps.md` from real gaps. |
| Stage 8 | Martin fills `99_observation.md`. Empty four fields do not pass. |

`mapping_status=manual_required` still creates `00_input/`, `01_probe/`, `90_scripts/`, and
`99_observation.md`. That is not a successful workflow mapping.

## Command

```bash
python3 scripts/scaffold_experiment.py \
  --input /path/to/scaffold-input.json \
  --output-dir /path/to/learning-unit/experiments/YYYYMMDD_hypothesis \
  --quiz-gaps-file /path/to/quiz-gaps.json \
  --dry-run
```

`--dry-run` writes nothing. Actual writes in a temp directory are a fixture run.
Official writes on a real learning unit are official scaffold generation.

## Input contract

See `references/scaffold-input.schema.json`. The Agent maps Markdown dossiers explicitly.
The script does not parse natural language. Branches stay in `composition_notes`.

Quiz gaps file:

```json
{ "gaps": [{ "id": "RUN_ROOT", "step_id": "editable-pptx", "text": "..." }] }
```

Unmapped `step_id` values go to `unassigned-gaps.md`.

## Ownership

| File | Owner |
|---|---|
| `NN_<id>/callouts.md`, `NN_<id>/phase.md`, `pipeline.md`, `unassigned-gaps.md` | script |
| `README.md`, `99_observation.md` | human after first create |
| `00_input/` | human materials |

`phase.md` and `pipeline.md` render each step's inputs, outputs, gate
checklist, and evidence locator. Missing values are `unknown` or
`manual_required`; directory presence is not mapping success.

Default reruns update only script-owned files. `--force-generated` never overwrites human README or observation. Script-owned writes refuse destination symlinks and do not follow a `callouts.md` link onto README.

## Numbering

Reserved: `00_input`, `90_scripts`, `99_observation.md`. Step ids are kebab-case.
Chinese labels are display-only. Duplicate or illegal ids exit non-zero.

## Gorden worked example

| Gap | File |
|---|---|
| RUN_ROOT | `editable-pptx/callouts.md` |
| verbatim | `image-pptx/callouts.md` |
| assets-manifest | each mapped step `callouts.md` |
| B3 frame | `editable-pptx/callouts.md` |
