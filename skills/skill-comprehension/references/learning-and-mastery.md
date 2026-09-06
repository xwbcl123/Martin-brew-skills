# Learning And Mastery

Covers stages 2–8. Stage 1 is Source inventory; Stage 9 is the Artifact Prompt Compiler.

## Stage 2 — Architecture And Design Principles

Produce, from actually-read Sources only:

- A file-tree or component breakdown with each component's responsibility.
- Relationships between components.
- One to three design principles the Target Skill actually follows.
- A Mermaid, ASCII, or plain-list diagram only when it helps understanding.
- Unread or unclear components marked unconfirmed.

## Stage 3 — Atomic Capability And IPO

For each atomic capability, state:

- **Input**: what it consumes and constraints.
- **Process**: what actually happens.
- **Output**: what it produces.
- **Preconditions**: what must be true.
- **Boundaries**: what it does not do and known failure inputs.

## Stage 4 — Workflow, Failure Paths, Composition

- Describe the primary end-to-end path.
- Describe at least one documented or observed failure path and its recovery.
- Describe sequencing, shared state, and handoffs.
- If no failure path is documented or observed, say `未在源文中找到失败路径说明`.
- Write `scaffold-input.json` from this evidence. Mark inferences in `mapping_notes`.
  If the path is not a linear step list, set `mapping_status=manual_required`.
  Optionally run `scripts/scaffold_experiment.py`. `scaffold_generated` is not
  workflow-mapping success and is not Stage 8 completion.

## Stage 5 — Domain Glossary

Build a compact vocabulary: term, one-line definition, evidence locator, and an
`avoid confusing with` note where relevant. Only include grounded definitions.

## Stage 6 — Three Critique Filters

Each filter must produce an actionable question, risk, or minimal verification experiment:

1. **Systems thinking** — feedback loops, hidden state, coupling, environmental assumptions.
2. **Critical thinking** — unsupported claims, alternatives, evidence that would change the assessment.
3. **Cognitive fallacies** — over-generalizing examples, equating one run with understanding, or
   anchoring on README framing.

## Stage 7 — Short Quiz

- Ask 3–5 questions covering architecture, boundaries, and transfer.
- Collect Martin's answers before giving feedback.
- Record gaps rather than only a score.
- Never treat the quiz alone as mastery.
- After answers exist, bind gaps to `step_id` and update script-owned `callouts.md`.
  Do not rewrite human README text or `99_observation.md`.

## Stage 8 — Minimal Hands-On Experiment

- Design one small, safe experiment distinct from the bundled example.
- Martin must perform it, or explicitly direct the Agent to run it as his hands-on action and then
  observe the result.
- Prefer the numbered scaffold from Stage 4. The scaffold is a preparation artifact.
- Require exactly: `goal`, `action`, `observation`, `next_step`.
- An empty four-field template does not pass Stage 8.

## Honest Degradation

- Do not fabricate quiz answers, experiments, or observation records.
- If the runtime cannot execute a required action, say so and ask Martin to perform it.

## Final Output Shape

Summarize architecture, capabilities, workflow, glossary, critique, quiz gaps, and experiment record
using the Dossier. Keep it scannable.
