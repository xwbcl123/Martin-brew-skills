# AGENTS.md

## Project Purpose

This repository stores Martin's self-built, reusable skills for cross-PC and cross-project sharing.

The goal is portability, reuse, and safe publication. It is not a dumping ground for private workspace state.

## Working Principles

- Make the smallest necessary change
- Do not revert unrelated work
- Prefer reusable structure over project-specific hacks
- Sanitize before publishing
- Keep the repository easy to copy into other projects

## Scope

Only include skills that Martin built or substantially shaped by hand.

Current in-scope skills:

- `audio-transcriber`
- `ds-citations`
- `publish-assets`
- `slide-renamer`
- `prompt-crafter`

Out of scope:

- temporary experiments
- one-off project scripts
- unsanitized real examples
- secrets, tokens, internal URLs, private glossary content

## Repository Layout

- top-level reusable documentation lives in the repo root
- each skill lives under `skills/<skill-name>/`
- each skill should be portable on its own

Prefer to keep:

- `SKILL.md`
- scripts
- prompts
- generic references
- minimal tests

Prefer to remove:

- caches
- generated outputs
- `.venv`
- private examples
- local machine artifacts

## Privacy Rules

Before publishing any change, review for:

- real names, internal project names, customer context
- private glossary entries
- raw meeting transcripts or journals
- secrets or `.env` values
- private infrastructure references
- workstation-specific paths unless they are generic installation examples

If content is useful structurally but not safe to publish:

- replace it with a template
- replace it with a sanitized demo
- or remove it entirely

## Skill-Specific Notes

### audio-transcriber

- keep the script and public prompts
- glossary must remain a starter template, not a private working glossary
- reference examples must stay sanitized

### ds-citations

- keep script, tests, and docs aligned
- prefer path examples that match this repository layout

### publish-assets

- treat it as an integration skill
- do not hardcode private infrastructure paths
- document external prerequisites through placeholders and examples

### slide-renamer

- keep examples generic
- avoid embedding project-specific folder structures in docs

### prompt-crafter

- keep references generic and reusable
- avoid leaking old private prompt history

## Installation Guidance

When updating docs, assume users may:

- clone the whole repo
- copy a single skill into another project's skill directory
- use a submodule or their own sync layer

Prefer commands that work from the repository root, for example:

```bash
python skills/<skill-name>/scripts/<tool>.py
```

## Final Check Before Commit

- repository contains no secrets
- no private glossary or raw transcript remains
- docs point to repo-relative paths
- copied skills are still understandable and portable
