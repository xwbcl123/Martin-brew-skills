# Martin-brew-skills

Martin 手工打造的可复用 skills 仓库，用于跨电脑、跨项目同步与分享。

Handcrafted, reusable skills maintained by Martin for cross-device and cross-project reuse.

## 中文简介

这个仓库只收录我亲手打造、适合独立复用的 skills。目标不是备份某个单一项目，而是沉淀一组能被多个工作流重复调用的能力模块。

当前仓库优先保留：

- 可独立迁移的 `SKILL.md`
- 可执行脚本
- 通用 prompts / references
- 最少必要的测试与快速参考

当前仓库不会保留：

- 真实客户材料
- 个人私密 glossary / reference
- API keys / tokens / cookies
- 仅服务单项目的临时产物

## English Overview

This repository contains self-built skills that are worth maintaining as reusable building blocks. It is designed to be a portable skills library rather than a dump of one specific workspace.

It keeps:

- reusable skill instructions
- scripts and lightweight tooling
- generic prompts and references
- minimal tests and quick references

It does not keep:

- private notes or client material
- unsanitized glossaries or examples
- secrets or environment-specific credentials
- one-off project artifacts

## Included Skills

- `audio-transcriber`
- `create-cover-illustration`
- `ds-citations`
- `doc-intelligent-summary`
- `notebooklm-export-formatter`
- `pptx-polish`
- `martin-pptx-skill`
- `publish-assets`
- `slide-renamer`
- `prompt-crafter`
- `llm-wiki-builder`
- `visual-mail`

## Repository Structure

```text
Martin-brew-skills/
├── skills/
│   ├── audio-transcriber/
│   ├── create-cover-illustration/
│   ├── ds-citations/
│   ├── doc-intelligent-summary/
│   ├── notebooklm-export-formatter/
│   ├── llm-wiki-builder/
│   ├── martin-pptx-skill/
│   ├── pptx-polish/
│   ├── prompt-crafter/
│   ├── publish-assets/
│   ├── slide-renamer/
│   └── visual-mail/
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

## Installation

### Option 1: Clone the full repository

```bash
git clone https://github.com/<your-user>/Martin-brew-skills.git
```

### Option 2: Copy one skill only

Copy the skill directory you need into a target project's skill folder, for example:

```text
skills/<skill-name>/
```

### Option 3: Reuse via submodule or sync script

For advanced setups, you can manage this repository as a Git submodule or with your own sync automation. The default recommendation is to keep it simple and copy only the skills you actually use.

## Sync Workflow

- Use GitHub as the source of truth
- `git pull` before making local updates on another machine
- `git add`, `git commit`, and `git push` after changes
- Keep each skill self-contained whenever possible

## Privacy and Sanitization

This repository intentionally ships with sanitized templates instead of private working data.

- `audio-transcriber/prompts/glossary.md` is a starter template, not a real personal glossary
- `audio-transcriber/reference/` contains demo examples only
- `create-cover-illustration` documents Gemini configuration through placeholders only
- `publish-assets` is documented as an integration skill and expects external tooling
- environment variables are documented through placeholders only

If you reuse these skills in your own workspace, replace the templates with your private versions locally instead of committing them back here.

## Notes by Skill

### `audio-transcriber`

- Gemini-based audio workflow
- suitable for large-audio transcription and structured markdown generation
- ships with sanitized glossary and demo references

### `create-cover-illustration`

- creates hand-drawn 16:9 journal and writing cover illustrations
- uses Codex image generation as the primary path
- includes a portable Gemini fallback script for agents without built-in image generation
- keeps configuration generic through `.env` placeholders, with no private workspace paths or secrets

### `ds-citations`

- normalizes GPT / Gemini / OpenAI Deep Research citation artifacts
- includes script, quick reference, and tests

### `doc-intelligent-summary`

- turns long Markdown documents into Obsidian-friendly wiki outputs
- uses chunking + parallel analysis + dashboard synthesis
- includes persisted source chunks, `run_log.md`, and `--validate-only` for auditability
- prefers medium-sized chunks instead of over-fragmented slices, with summary depth tuned for reusable wiki notes

### `publish-assets`

- integration-oriented wrapper skill
- depends on an external image hosting toolkit
- this repository keeps the workflow contract, not the private infrastructure

### `llm-wiki-builder`

- builds a governed, navigable LLM wiki from a source folder, not just a file inventory
- preserves source safety via copy-first ingestion into `raw/` and optional `raw-normalized/` working copies
- treats Markdown/TXT as native text and avoids redundant `analysis/ingest-src/` copies
- adds mandatory post-ingestion synthesis: core thesis, semantic MoC pages, source-linked summaries, and coverage QC
- includes Windows-safe `source-inventory.md` table generation and multi-agent workflow guidance for inventory, clustering, and QC

### `notebooklm-export-formatter`

- restores headings, list structure, and emphasis from raw NotebookLM Markdown exports
- converts bracket references into Markdown footnotes
- includes a lightweight learn-from-polished iteration loop

### `pptx-polish`

- post-processes AI-generated PPTX decks
- focuses on font normalization, minimum font size, and visual cleanup
- includes a PPTX diff helper for extracting reusable formatting patterns

### `martin-pptx-skill`

- stages deck production from `deck-outline.md` and `design.md`
- separates image-gen visual motherboard exploration from editable PPTX reconstruction
- includes reusable script contracts for route choice, image-gen prompts, Option 5 PPTX reconstruction, render QC, Text Fidelity Gate, BG Gate, and contact sheets
- ships with sanitized templates and references only; no private benchmark materials or generated deck outputs

## Changelog

### 2026-05-18

- add `martin-pptx-skill`, a sanitized staged deck engineering skill for visual motherboard and editable PPTX workflows

### 2026-04-26

- add `create-cover-illustration`, a reusable hand-drawn cover illustration skill with Codex image generation as the primary path and Gemini fallback for other agents
- document generic Gemini image configuration placeholders without private paths or secrets
- tighten `create-cover-illustration` decision rules so Codex uses `$imagegen` before fallback scripts, documents generated-image handoff, and supports full-source prompts with explicit visual-theme extraction

### 2026-04-18

- `llm-wiki-builder`: upgrade from scaffold-only bootstrap to a full Knowledge Architect workflow with mandatory semantic synthesis, source-linked MoC pages, and coverage QC
- classify Markdown/TXT as `native-text` to prevent redundant ingest copies; keep rich/binary extraction in `analysis/ingest-src/`
- fix Windows Markdown table rendering in `source-inventory.md` by forcing LF output and avoiding `os.linesep` row joins
- add post-ingestion synthesis reference and expanded multi-agent delegation guidance for semantic clustering, source sampling, and MoC coverage checks

### 2026-04-15

- `notebooklm-export-formatter`: expand heading pattern recognition to cover Chinese plain-text section titles (`核心发现`, `报告优势`, `主题：xxx`, `案例：xxx`, `论据 N：xxx` etc.) and emoji-prefixed section headers (`📋 案例研究分析`, `🧩 论点解构` etc.)
- these are emitted as `###` level headings in the formatted output

### 2026-04-13

- `pptx-polish` v1.2: add short-label background expansion so empty label shapes widen with the text box after polish
- improve width sizing with rendered-text estimation plus extra safety padding to reduce visible text overflow
- add adjacent-label spacing protection to avoid overlap after widening
- document the learn-from-manual-polish iteration in `skills/pptx-polish/SKILL.md`

### `slide-renamer`

- OCR-based slide image renaming utility
- lightweight and self-contained

### `prompt-crafter`

- methodology-driven prompt design skill
- includes reusable reference notes

### `visual-mail`

- turns a report, brief, analysis, progress update, or meeting note into a share-ready email package
- produces an email draft, visual brief HTML, and screenshot preview with placeholder links when publication URLs are not available
- includes fallback brand styles, output cleanup rules, and a Selenium/CDP full-page screenshot helper
- keeps public-facing outputs free of automation/provenance traces

## Maintenance Principles

- Prefer reusable over clever
- Sanitize before publishing
- Keep structure portable
- Minimize project-specific assumptions

## License

MIT
