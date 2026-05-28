---
name: grill-me
description: Use when Martin says "grill me", "green me", "grill with docs", or wants to clarify a task/session before implementation. Adapts grill-with-docs into the Life-OS and Work-PKM task/session workflow by interviewing the user one decision at a time, inspecting local context first, and writing session-local requirement, context, and decision artifacts under tasks/sessions/YYYYMMDD_slug/.
---

# Grill Me

Project-adapted requirement grilling for Martin's Life-OS and Work-PKM sessions.

This skill is inspired by Matt Pocock's `grill-with-docs`, but it does **not** create repo-root `CONTEXT.md` or `docs/adr/` by default. In Martin's projects, the durable home for task clarification is the active session folder:

```text
tasks/sessions/YYYYMMDD_slug/
```

## Core Behavior

Interview Martin relentlessly but efficiently until the task has enough shared context to execute safely.

- Ask one question at a time.
- For each question, provide a recommended answer.
- If the answer can be discovered from local files, inspect first instead of asking.
- Challenge fuzzy terms, overloaded terms, hidden assumptions, and premature implementation choices.
- Capture resolved context and decisions immediately in session-local artifacts.
- Do not turn this into a long questionnaire. Stop when the next implementation step is unblocked.

## Session Resolution

Before writing artifacts, resolve the session target:

1. If the user names a session path, use it.
2. If the current working directory is inside `tasks/sessions/<session>/`, use that session.
3. If the user is asking to start a task (`task new`, `task-init`, `session new`), create or reuse the newly created session scaffold.
4. If no session exists and multiple destinations are plausible, ask one concise question for the target session.

Supported roots:

- Life-OS: `tasks/sessions/YYYYMMDD_slug/`
- Work-PKM-Vault: `tasks/sessions/YYYYMMDD_slug/`

Use repo-relative paths in artifacts.

## Required Artifacts

Create these lazily inside the session. Do not create empty files just to satisfy a template.

```text
05_grill_me.md
context/grill_context.md
context/decision_log.md
```

Use `references/session-artifacts.md` for formats.

## During The Grill

Read first:

- `AGENTS.md`
- The session's `00_request.md`, `10_plan.md`, and existing `context/` files if present
- Relevant project docs, source files, notes, or prior decisions named by the task

Then proceed:

1. Summarize the current understanding in 3-6 bullets.
2. Identify the highest-risk missing decision.
3. Ask exactly one question with:
   - why it matters
   - recommended answer
   - tradeoff if Martin chooses differently
4. After Martin answers, update the relevant artifact immediately.
5. Continue until requirements, context, and decision boundaries are clear enough to implement.

## What To Capture

`05_grill_me.md`:

- question log
- Martin's answers
- recommended defaults
- open questions
- implementation readiness

`context/grill_context.md`:

- project-specific vocabulary
- domain boundaries
- source materials
- constraints that must shape implementation
- avoid-list for ambiguous terms

`context/decision_log.md`:

- decisions that affect later implementation or review
- rejected alternatives worth remembering
- alignment points Martin explicitly approved

Use a decision log entry only when the decision is material. If it is easy to reverse or obvious, keep it in `05_grill_me.md` instead.

## Non-Goals

- Do not block obvious low-risk work with excessive questions.
- Do not create global glossary or ADR files unless the project already has that convention and the user explicitly wants it.
- Do not write implementation code while still in the grill phase, unless the user redirects.
- Do not overwrite existing session artifacts; append or update targeted sections.

## Closeout

When the grill is done, update `10_plan.md` or `40_results.md` only if the session already uses those files and the clarification changes execution.

End with:

- the session path
- files created or updated
- remaining open questions, if any
- whether the task is ready for implementation
