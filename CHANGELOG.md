# Changelog

All notable changes to this repository will be documented in this file.

The format is intentionally lightweight and practical for a personal-but-shareable skills repository.

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
