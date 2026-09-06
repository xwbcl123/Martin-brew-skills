# Artifact Prompt Compiler

Optional Stage 9 prompt-only fallback, normally used after Stages 1–8 have produced a working Dossier.
This adapter only produces text for Martin to paste manually. When an authenticated Notebook runtime
is available and Martin asks for real generation or export, use `notebook-learning-addon.md` instead.
For canonical semantics, read `comprehension-protocol.md` §8.

## What This Does Not Do

- Does not call, open, or automate NotebookLM Studio.
- Does not generate the Artifact itself.
- Never reports `artifact_generated_in_gui=true`.

## Input

- `artifact_type`: one of `custom-report`, `slide-deck`, `video-overview`, `audio-overview`,
  `flashcards`, `quiz`, `mind-map`, `data-table`, `infographic`.
- Sources/Dossier accumulated in the current session.
- Fixed defaults: Martin, beginner, master the current Target Skill, emphasis inferred from the Dossier.

If `artifact_type` cannot be determined, list the nine types and ask Martin to pick one. This is the
only permitted clarifying question here.

## Output Contract

Always produce:

1. GUI setting recommendation.
2. One paste-ready Custom Prompt block.
3. Source constraints and QA checklist.
4. `custom_prompt_generated=true; artifact_generated_in_gui=not_run`.

## Shared Compiler Baseline

Every Custom Prompt must instruct NotebookLM to:

- Ground every claim in loaded Sources; mark unsupported claims `待验证`.
- Open with the Target Skill's actual purpose.
- Separate confirmed/implemented capabilities from planned/unconfirmed ones.
- Close with a concrete learner action or check.
- Cite file/section evidence for specific technical claims.

## Nine Artifact Profiles

| `artifact_type` | Default purpose | GUI setting recommendation | Modality-specific clause | QA |
|---|---|---|---|---|
| `custom-report` | Deep reference doc | Report; Medium–Long | Sections for architecture, IPO, boundaries, conclusions and limits | Locator per claim; scannable headings |
| `slide-deck` | Visual teaching | Presenter Slides; Medium | One idea per slide; architecture/workflow visuals; Speaker Notes | Editable text; no misleading visuals |
| `video-overview` | Narrative overview | Short–Medium | Paced chapters matching workflow stages | Appropriate density; no unsupported visuals |
| `audio-overview` | Audio teaching | Short–Medium; conversational or monologue | Explain terminology aloud; do not rely on visuals | Navigable by ear |
| `flashcards` | Active recall | Count proportional to glossary and capabilities | Atomic, bidirectional Q/A; no answer leakage | Factual and applied balance |
| `quiz` | Diagnostic self-check | Mixed question types | Explanations and misconception notes | Score alone is not mastery |
| `mind-map` | Structural overview | Root = Target Skill; depth ≤ 3 | Label relationships, not only hierarchy | Show cross-dependencies |
| `data-table` | Comparison/reference | Row = capability or component | Explicit columns and Source locator column | No fabricated numbers |
| `infographic` | Single-glance synthesis | One primary message | Clear hierarchy tied to workflow or architecture | Legible sourced claims |

## Degradation

If Stage 1 has not run or the Dossier is empty, do not compile from guesses. Run a Source inventory
first.
