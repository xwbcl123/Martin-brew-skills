---
name: skill-comprehension
description: Turn an unfamiliar third-party Skill (a Target Skill repo/package with SKILL.md, references, scripts, or examples) into tested, source-grounded understanding for Martin — architecture, atomic capabilities, workflow, glossary, critique, a short quiz, and a minimal hands-on experiment, plus optional NotebookLM/Gemini Notebook learning artifacts. Use this skill when Martin wants to learn, evaluate, audit, or decide whether to adopt a Skill/agent-skill/package before installing or relying on it, asks to be "taught", "walked through", or "quizzed", or wants a Notebook-backed learning pack. Do not use it to install, execute, or ship the Target Skill itself.
---

# Skill Comprehension

Turn a Target Skill from an installable black box into something Martin can explain, question, test,
and try hands-on. Success is Martin's demonstrated understanding, not a summary document and not the
Agent successfully running the Target Skill.

This Skill is self-contained. Resolve every instruction and reference relative to this Skill directory;
do not search for an external workspace specification or sibling distribution. Read
`references/comprehension-protocol.md` when full protocol context or cross-runtime semantics are needed.

## Default Guided Flow

When Martin names a Target Skill (a path, repo, or pasted file set) with no further instruction, run
this sequence, pausing where noted:

1. **Source inventory** — read the Target Skill's `SKILL.md`/entry file, `README.md`, `references/*`,
   `scripts/*`, and `examples/*` in that order. Follow
   `references/source-grounding-and-dossier.md` before asserting anything as confirmed.
2. **Architecture and design principles** — see `references/learning-and-mastery.md` Stage 2.
3. **Atomic capability and IPO** — Stage 3.
4. **Workflow, failure paths, composition** — Stage 4. Write `scaffold-input.json`
   from read evidence (do not let the script guess Markdown). Optionally generate
   the Stage 8 directory scaffold; `scaffold_generated` is not mastery.
5. **Domain glossary** — Stage 5.
6. **Three critique filters** (systems / critical thinking / fallacies) — Stage 6. Do not skip this even
   for a fast pass; each filter must produce something actionable.
7. **Pause. Offer the short quiz** (3–5 questions) — Stage 7. Wait for Martin's answers before revealing
   correct answers or gaps. After answers exist, update script-owned experiment
   `callouts.md` files only.
8. **Pause. Propose one minimal hands-on experiment** distinct from the Target Skill's bundled example —
   Stage 8. Prefer the numbered scaffold. Martin (not the Agent alone) must perform
   it and report `goal/action/observation/next_step`. An empty observation template
   does not pass.
9. **Optional Notebook learning**: if Martin asks for NotebookLM/Gemini Notebook sources, slash
   commands, generated Artifacts, downloads, or a Vault reading pack, read
   `references/notebook-learning-addon.md`. For a Repomix source, keep the raw Pack unchanged and run
   `scripts/build_notebook_ingestion.py` to create the default single-file retrieval adapter before
   upload. Use `references/artifact-prompt-compiler.md` only for the prompt-only fallback.
   After Notebook export, compile `outcomes/reading/wiki/` with
   `scripts/compile_skill_wiki.py`. Without Notebook, a dossier-only wiki is allowed.

State progress plainly ("已完成架构与能力盘点，进入 Stage 6 三重滤镜") rather than silently jumping
stages. If Martin interrupts to ask something specific, answer it, then offer to resume the flow at the
next stage.

## Stage Shortcuts

Martin may ask for any single stage directly ("just show me the architecture", "quiz me now", "give me
the audio overview prompt") without running the full sequence first. Honor the request using the
matching reference, but if no Dossier exists yet for this Target Skill, run a quick Source inventory
first.

## When To Read Each Reference

- `references/source-grounding-and-dossier.md` — always, before or during Stage 1.
- `references/learning-and-mastery.md` — for Stages 2–8.
- `references/artifact-prompt-compiler.md` — only when Martin asks for a Custom Prompt for one of the
  nine NotebookLM Artifact types.
- `references/notebook-learning-addon.md` — when an authenticated Notebook runtime is available or
  Martin asks to ingest Sources, run slash modules, generate/download Artifacts, or build a 41.15
  reading pack.
- `references/comprehension-protocol.md` — when exact vocabulary, Dossier schema, completion-state
  semantics, or cross-runtime conformance rules are needed.
- `references/stage8-experiment-scaffold.md` — Stage 4 structured input and Stage 8 scaffold.
- `references/gemini-notebook-wiki-export.md` — wiki allowlist, render rules, quiz-answer gating.
- `references/outcomes-layout-contract.md` — `reading/` vs `_transport/` and migration rules.

## Honest Degradation

- Never assert a capability as implemented from a README, repo name, or filename alone.
- Never claim filesystem, network, shell, or GUI-automation capability beyond the current runtime.
- Never infer Artifact completion from a prompt or task receipt. An Agent may set
  `artifact_generated_in_notebook=true` only after the exact Artifact ID reports `completed`.
  `artifact_generated_in_gui=true` still requires Martin's GUI confirmation.
- Never treat Notebook reading, generated Quiz Artifacts, or Agent-run modules as Martin mastery;
  Stage 7 answers and Stage 8 observation remain human gates.
- Never treat the Agent's successful execution of a Target Skill example as evidence of Martin's
  understanding.
- If a bundled reference cannot be opened, name it explicitly and stop any conclusion that depends on
  it; do not fall back to files outside this Skill directory.

## Final Output

After the guided flow (or a requested stage), give Martin a compact summary grounded in the Dossier:
what was read, what is confirmed vs. unconfirmed, the workflow, glossary, critique findings, quiz gaps,
and experiment record if completed. Suggest the next unfinished stage.
