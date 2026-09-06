# Source Grounding And Dossier

## Source Inventory Order

When a Target Skill is named, read in this order before asserting anything as confirmed:

1. `SKILL.md` (or the package's equivalent entry file) — declared triggers, scope, main flow.
2. `README.md` if present — treat its capability claims as claims, not facts, until implementation
   sources confirm them.
3. `references/*` — detailed schemas, contracts, workflow docs.
4. `scripts/*` — actual executable behavior; open and read, do not infer from filenames.
5. `examples/*` or sample inputs — what the bundled example actually exercises.

Track each file as `read: true` or `read: false (not found / not opened)`. Never promote a `false` entry
to confirmed by inference.

## Claim → Evidence Locator → Confidence Contract

Every important claim about the Target Skill takes this shape:

```text
claim: <what you are asserting>
evidence_locator: <file path> § <heading, section, or code symbol>
confidence: confirmed | unconfirmed | conflicting
```

- `confirmed`: the cited file was actually opened and read in this session, and the locator supports
  the claim.
- `unconfirmed`: inferred from a title, filename, or README description without opening the underlying
  file; state this explicitly.
- `conflicting`: README/docs and actual implementation disagree; record both sides with their locators
  and prefer implementation as authoritative.

## README vs. Implementation Conflicts

1. Record both claims with locators.
2. Mark the capability `planned` if only documented, `implemented` only if code confirms it, or
   `conflicting` if evidence points both ways.
3. Surface the conflict directly in the Architecture or Capability output.

## Minimal Dossier Schema

Keep this as working session state; no fixed file is required:

```text
target_skill: {name, sources_read[], sources_missing[]}
architecture: {summary, components[{name, responsibility, evidence_locator}]}
capabilities: [{name, ipo, preconditions, boundaries, evidence_locator, status}]
workflows: {primary_path, failure_paths[], composition_points[]}
glossary: [{term, definition, evidence_locator}]
critique: {systems[], critical_thinking[], fallacies[]}
quiz: {questions_asked[], gaps_identified[]}
experiment: {design, martin_action, martin_observation, next_step}
scaffold: {schema_version, input_path, mapping_status, scaffold_generated}
wiki: {wiki_compiled, snapshot_path, snapshot_sha256, content_hash, missing_modules, compile_mode}
artifact_prompt: {artifact_type, custom_prompt_generated, artifact_generated_in_gui}
```

After Stage 4, persist `scaffold-input.json` beside the dossier. The Agent maps
workflow steps explicitly; `scripts/scaffold_experiment.py` must not parse the
Markdown dossier. Wiki compile must consume `_transport/dossier-snapshots/<sha256>.md`,
not live `wiki.*` writeback.

## Missing Source Rule

If a Source referenced by the Target Skill cannot be opened:

- State: `未读到 <path>，无法确认其行为`.
- Do not guess behavior from the filename, similar Skills, or convention.
- Mark dependent capabilities `unconfirmed` and continue with readable Sources.

## Forbidden Inferences

- Do not infer implemented behavior from a repo name, tagline, or marketing description.
- Do not treat one successful example as evidence for capabilities it did not exercise.
- Do not invent file paths, line numbers, or code symbols.
