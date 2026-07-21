# Changelog

All notable changes to this repository will be documented in this file.

The format is intentionally lightweight and practical for a personal-but-shareable skills repository.

## 2026-07-21

### Added

- Added `brand-guidelines`, Martin's portable Life-versus-Work brand router.
- Added the Balanced Signal personal Logo family, the Light Editorial and Martin-Borealis modes, routing acceptance scenarios, and a responsive HTML visual reference.
- Added a sanitized `Organization Brand` adapter so the public package does not expose private organization identities, templates, or workstation paths.

### Changed

- Updated the root README and agent guidance to include the new portable brand system.

## 2026-06-18

### Added

- Added `notebooklm-deck-factory`, a NotebookLM alternate-deck generation workflow with run package scaffolding, prompt/source manifests, PPTX/PDF download records, render evidence, and editability QC.

### Changed

- Updated README skill inventory and structure tree to include `notebooklm-deck-factory`.

## 2026-06-03

### Added

- Added `martin-outcome-package`, a portable six-deliverable outcome package skill for turning transcripts, `.req.md` captures, or fuzzy task inputs into D1-D6 delivery packages.
- Included references, templates, smoke-test criteria, DesignMD / DesignStack planning, and a `martin-pptx-skill` handoff template.

### Changed

- Updated root README and agent guidance to include the new outcome-package skill and its D5 delegation boundary.

## 2026-05-28

### Added

- Added `codex-fluent`, a report-first Codex session hygiene and handoff discipline skill.
- Added `codex-retrospective`, a minimal evidence-backed Codex behavior improvement loop.
- Added `grill-me`, a session-scoped requirement grilling workflow adapted from `grill-with-docs`.

### Changed

- Updated README and agent guidance to include the new Codex workflow and session clarification skills.

## 2026-04-26

### Added

- Added `create-cover-illustration`, a hand-drawn 16:9 journal and writing cover illustration skill.
- Included a portable Gemini fallback script plus generic prompt contract and OpenAI-agent metadata.

### Changed

- Updated root README, `.env.example`, and agent guidance to include `create-cover-illustration`.
- Sanitized fallback configuration docs so they use placeholders and repo-relative examples only.

## 2026-04-24

### Added

- Added `visual-mail`, a report-to-email package skill that generates a share-ready email, visual brief HTML, and screenshot preview.
- Included fallback brand styles, output cleanup rules, and Selenium/CDP full-page screenshot capture.

### Changed

- Updated root README and agent guidance to include `visual-mail`.

## 2026-04-03

### Added

- Added `notebooklm-export-formatter`
- Added `pptx-polish`

### Changed

- Updated `README.md` skill inventory and structure tree
- Added public descriptions for the two newly synced skills

## 2026-03-19

### Added

- Initial repository structure for `Martin-brew-skills`
- Root documentation: `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`
- Imported skills:
  - `audio-transcriber`
  - `ds-citations`
  - `publish-assets`
  - `slide-renamer`
  - `prompt-crafter`

### Changed

- Sanitized `audio-transcriber` for public sharing
- Replaced private glossary content with a starter template
- Replaced private references with demo examples
- Rewrote `publish-assets` as a provider-agnostic integration skill
- Normalized repo-relative paths in skill documentation

### Removed

- Private transcript and journal source material
- Project-specific path examples that should not ship in a reusable public repo
- Generated cache artifacts such as `__pycache__`

### Updated Later The Same Day

- Synced `audio-transcriber` to the new transcript-first architecture
- Added `workflows/` routing docs for `reflection`, `meeting`, `voice-note`, glossary loop, and architecture notes
- Migrated prompt files from mixed `.txt` usage to `.md`-based workflow prompts
- Added sanitized public demo files for MoM and voice-note brief outputs
- Kept public `glossary.md` and reference examples sanitized instead of copying private working data
