# Skill Comprehension Protocol

Portable, platform-neutral protocol for the `skill-comprehension` Skill. This bundled copy defines the
vocabulary, Source grounding, Dossier, learning mainline, Mastery Gate, Artifact Prompt Compiler,
completion states, and cross-runtime conformance rules. It has no dependency on the original build
workspace or on an App GUI Worker distribution.

## 1. Vocabulary

- **Target Skill**: the third-party Skill repository/package being studied.
- **Agent-facing Skill**: this installed `skill-comprehension` package.
- **App GUI Worker**: a separately configured Gemini or NotebookLM worker that can use only its loaded
  Sources and host GUI capabilities.
- **Source-grounded claim**: an important statement with a locator to an actually read file plus a
  heading, section, or code symbol.
- **Dossier**: minimal working state accumulated during a comprehension pass.
- **Mastery Gate**: short quiz plus minimal hands-on experiment and observation.
- **Artifact Prompt Compiler**: logic that turns Sources/Dossier plus `artifact_type` into a GUI setting
  recommendation and paste-ready Custom Prompt. It does not generate the Artifact.
- **Artifact Profile**: one of nine type-specific configurations used by the Compiler.
- **`custom_prompt_generated`**: a non-empty, Source-grounded, paste-ready Custom Prompt exists.
- **`artifact_generated_in_gui`**: Martin has actually generated the Artifact in the GUI.
- **Notebook Learning Add-on**: optional platform adapter for ingestion, slash modules, typed Artifact
  generation, export, and reading handoff.
- **`artifact_generated_in_notebook`**: the exact typed-generation Artifact ID reports `completed`.
- **`artifact_exported_to_vault`**: a sanitized downloaded Artifact with SHA-256 exists in 41.15.

Never infer `artifact_generated_in_gui` from `custom_prompt_generated`.

## 2. Zero-Config Defaults

- User: Martin.
- Level: beginner.
- Goal: master the current Target Skill.
- Emphasis: infer after Source inventory.
- Ask at most one clarifying question, only when ambiguity materially changes the output and Context
  cannot resolve it.

## 3. Source Grounding

1. Read the underlying file before confirming a claim about architecture, capability, workflow, or
   terminology.
2. Treat README and repository-name claims as unconfirmed until implementation Sources support them.
3. Keep planned/TODO/roadmap behavior out of confirmed capabilities.
4. When README and implementation disagree, record both and prefer implementation.
5. State missing Sources explicitly; never guess from filenames or convention.
6. Never claim runtime capabilities the current surface does not expose.

## 4. Minimal Dossier

```text
target_skill:
  name:
  sources_read:
  sources_missing:
architecture:
  summary:
  components:
capabilities:
  # {name, ipo, preconditions, boundaries, evidence_locator, status}
workflows:
  primary_path:
  failure_paths:
  composition_points:
glossary:
critique:
  systems:
  critical_thinking:
  fallacies:
quiz:
  questions_asked:
  gaps_identified:
experiment:
  design:
  martin_action:
  martin_observation:
  next_step:
artifact_prompt:
  artifact_type:
  custom_prompt_generated:
  artifact_generated_in_gui:
notebook_learning:
  notebook_id:
  source_ids:
  source_readable:
  artifact_task_id:
  artifact_generated_in_notebook:
  artifact_exported_to_vault:
  martin_reading_confirmed:
scaffold:
  schema_version:
  input_path:
  mapping_status:
  scaffold_generated:
wiki:
  wiki_compiled:
  snapshot_path:
  snapshot_sha256:
  content_hash:
  missing_modules:
  compile_mode:
```

Every confirmed item needs an `evidence_locator`. Items without one stay unconfirmed.
`scaffold_generated` and `wiki_compiled` are file/integrity states. They do not write
`martin_action`, `martin_observation`, or `artifact_exported_to_vault`.

## 5. Nine-Stage Mainline

```text
1. Source inventory
2. Architecture and design principles
3. Atomic capability and IPO
4. Workflow, failure paths and composition
5. Domain glossary
6. Systems / critical / fallacy filters
7. Short quiz
8. Minimal hands-on experiment
9. Optional Artifact Custom Prompt
```

Stages 6–8 are not optional shortcuts to a faster claim of mastery.

### Stage 6 Critique

Each filter must produce at least one actionable question, risk, or verification experiment:

- **Systems thinking**: feedback loops, hidden state, coupling, environmental assumptions.
- **Critical thinking**: unsupported claims, alternatives, evidence that would change the assessment.
- **Cognitive fallacies**: over-generalization, confusing one run with understanding, README anchoring.

## 6. Lightweight Mastery Gate

Passing requires both:

1. A 3–5 question diagnostic quiz covering architecture, boundaries, and transfer. Collect answers
   before feedback.
2. One safe experiment distinct from the bundled example, performed or directly observed by Martin,
   with `goal`, `action`, `observation`, and `next_step`.

The Agent's own execution success never substitutes for Martin's understanding.

## 7. Module Semantics

| Module | Stage | Contract |
|---|---:|---|
| `SC_ARCHITECTURE` | 2 | Responsibilities, relationships, design principles, unknowns |
| `SC_CAPABILITY` | 3 | Atomic IPO, dependencies, preconditions, boundaries |
| `SC_WORKFLOW` | 4 | Primary path, failure/recovery, composition |
| `SC_GLOSSARY` | 5 | Term, definition, locator, avoid-confusion note |
| `SC_CRITIQUE` | 6 | Three actionable critique filters |
| `SC_QUIZ` | 7 | 3–5 questions, answers before feedback, gaps recorded |
| `SC_EXPERIMENT` | 8 | Distinct safe experiment and four-field observation |
| `SC_ARTIFACT_PROMPT` | 9 | One Compiler-selected Profile; no Artifact generation claim |

Missing Source causes explicit degradation, not guessing.

## 8. Artifact Prompt Compiler

```text
Target Skill Sources/Dossier
  → read artifact_type
  → apply Martin/beginner/master defaults
  → infer emphasis
  → select exactly one Artifact Profile
  → output:
      1. GUI setting recommendation
      2. one paste-ready Source-grounded Custom Prompt
      3. Source constraints and QA checklist
      4. custom_prompt_generated=true
         artifact_generated_in_gui=not_run
```

Martin then opens the GUI, selects the Artifact type, pastes the prompt, generates the Artifact, and
performs lightweight QA.

When an authenticated Notebook runtime is available, `notebook-learning-addon.md` may instead route
the same canonical `artifact_type` to a typed generation endpoint. The prompt-only Compiler and typed
generation are separate adapters; a chat response never proves typed generation.

Canonical `artifact_type` values:

- `custom-report`
- `slide-deck`
- `video-overview`
- `audio-overview`
- `flashcards`
- `quiz`
- `mind-map`
- `data-table`
- `infographic`

If the type cannot be determined, list the nine values and ask Martin to choose. This is the only
permitted clarifying question at this stage.

## 9. Completion States

| State | Set by | Meaning |
|---|---|---|
| `custom_prompt_generated` | Compiler | Paste-ready, Source-grounded prompt exists |
| `artifact_generated_in_gui` | Martin after real GUI generation | Artifact was actually generated |
| `artifact_generation_requested` | Notebook adapter | Exact task/Artifact ID exists and is pending/in progress |
| `artifact_generated_in_notebook` | Notebook adapter after status verification | Exact Artifact ID is completed |
| `artifact_exported_to_vault` | Notebook adapter after download and sanitization | Verified export exists in 41.15 |
| `martin_reading_confirmed` | Martin | Martin confirms reading in Notebook or Obsidian |
| `scaffold_generated` | scaffold script after files exist | Numbered dirs/templates written; not mapping success; not Stage 8 |
| `wiki_compiled` | wiki compiler after integrity checks | Wiki pages + content hash exist; not mastery; not 41.15 export |

No Agent module may set `artifact_generated_in_gui=true` on its own authority. An Agent may set
`artifact_generated_in_notebook=true` only from the exact completed Artifact ID, and may set
`artifact_exported_to_vault=true` only after local file, hash, sanitization, and index verification.
`wiki_compiled` never implies any artifact generation or 41.15 export state.

## 10. Cross-Runtime Conformance

For the same Target Skill Sources, compatible Agent and App GUI runs must not contradict each other on:

1. Goal and primary components.
2. Implemented vs. planned/unconfirmed capabilities.
3. Primary workflow and at least one failure path.
4. Core glossary definitions.
5. At least one output from each critique filter.
6. Nine Artifact types and their QA checkpoints.

Compatible does not require identical wording, depth, or stage ordering.

## 11. Non-Goals

- Do not install, ship, or expose the Target Skill.
- The platform-neutral Core does not assume GUI or Notebook generation capability. A selected and
  authenticated Notebook adapter may generate Artifacts when Martin requested it and evidence states
  remain separate.
- Do not invent filesystem, shell, network, database, MCP, or GUI access.
- Do not introduce persona matrices, multi-user state, or background update daemons.
