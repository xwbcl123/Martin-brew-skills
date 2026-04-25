# Changelog

All notable changes to this repository will be documented in this file.

The format is intentionally lightweight and practical for a personal-but-shareable skills repository.

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
