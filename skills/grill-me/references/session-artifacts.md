# Grill Me Session Artifacts

Use these formats inside `tasks/sessions/YYYYMMDD_slug/`.

## `05_grill_me.md`

```md
---
title: "Grill Me - <session title>"
type: requirement-grill
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Grill Me - <session title>

## Current Understanding

- <objective>
- <target paths / affected systems>
- <known constraints>

## Question Log

### Q1. <question>

Why it matters:
<short reason>

Recommended answer:
<the default Codex recommends>

Martin's answer:
<answer>

Decision impact:
<what changes downstream>

## Open Questions

- <remaining question, or "None">

## Implementation Readiness

- Ready: yes/no
- Blockers:
- Next execution step:
```

## `context/grill_context.md`

```md
---
title: "Grill Context - <session title>"
type: session-context
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Grill Context - <session title>

## Source Materials

- `<repo-relative path>` - <why it matters>

## Vocabulary

**<Canonical Term>**:
<1-2 sentence definition.>
_Avoid_: <ambiguous synonyms>

## Boundaries

- In scope:
- Out of scope:

## Constraints

- <constraint that affects implementation>

## Assumptions To Verify

- <assumption>
```

## `context/decision_log.md`

```md
---
title: "Decision Log - <session title>"
type: decision-log
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Decision Log - <session title>

## Decisions

### D1. <short decision title>

Decision:
<what was decided>

Why:
<why this is the right tradeoff>

Alternatives considered:
- <alternative> - <why rejected>

Downstream impact:
- <what future implementation/review must respect>
```

## Capture Rules

- Keep definitions tight.
- Prefer Martin's canonical terms, but call out ambiguity.
- Record material decisions only.
- Use repo-relative paths.
- Append or targeted-update existing files; do not wipe prior grill history.
