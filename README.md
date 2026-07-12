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
- `codex-fluent`
- `codex-retrospective`
- `conference-video-deck-transcript`
- `create-cover-illustration`
- `daily-knowledge-brief`
- `ds-citations`
- `doc-intelligent-summary`
- `grill-me`
- `life-os-reflect-cover-orchestrator`
- `life-os-smart-clipper`
- `martin-agent-roster`
- `martin-outcome-package`
- `notebooklm-deck-factory`
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
│   ├── codex-fluent/
│   ├── codex-retrospective/
│   ├── create-cover-illustration/
│   ├── daily-knowledge-brief/
│   ├── ds-citations/
│   ├── doc-intelligent-summary/
│   ├── grill-me/
│   ├── life-os-smart-clipper/
│   ├── notebooklm-export-formatter/
│   ├── llm-wiki-builder/
│   ├── martin-agent-roster/
│   ├── martin-outcome-package/
│   ├── martin-pptx-skill/
│   ├── notebooklm-deck-factory/
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

### `codex-fluent`

- keeps long-running Codex usage responsive through report-first maintenance
- includes handoff templates, archive safety rules, and maintenance checklists
- preserves work through explicit handoffs before any session cleanup

### `codex-retrospective`

- reviews recent Codex usage history to identify repeatable behavior improvements
- produces minimal, evidence-backed updates to AGENTS.md or tiny reusable skills
- includes rules for safe constitution updates and high-signal retrospective prompts

### `conference-video-deck-transcript`

- turns long conference/keynote/webinar videos into per-speaker Deck PDFs and Transcript Markdown files
- uses a speaker segment map as the source of truth for deck/transcript alignment
- includes scripts for deck extraction, transcript splitting, manifest generation, and artifact archiving
- keeps source media, raw frames, contact sheets, and process artifacts out of the final deliverable folder

### `create-cover-illustration`

- creates hand-drawn 16:9 journal and writing cover illustrations
- uses Codex image generation as the primary path
- includes a portable Gemini fallback script for agents without built-in image generation
- keeps configuration generic through `.env` placeholders, with no private workspace paths or secrets

### `daily-knowledge-brief`

- turns a bounded Life-OS clipping ledger into a grounded Chinese daily knowledge synthesis
- persists and validates Obsidian Markdown before Telegram or Gmail delivery
- tracks per-recipient delivery state and message IDs for idempotent retry
- supports per-job provider/model pinning in Hermes Cron without embedding private recipients or machine-specific paths

### `ds-citations`

- normalizes GPT / Gemini / OpenAI Deep Research citation artifacts
- includes script, quick reference, and tests

### `doc-intelligent-summary`

- turns long Markdown documents into Obsidian-friendly wiki outputs
- uses chunking + parallel analysis + dashboard synthesis
- includes persisted source chunks, `run_log.md`, and `--validate-only` for auditability
- prefers medium-sized chunks instead of over-fragmented slices, with summary depth tuned for reusable wiki notes

### `grill-me`

- adapts Matt Pocock's `grill-with-docs` idea for Martin's task/session workflow
- writes requirement questions, session context, and decision logs under `tasks/sessions/YYYYMMDD_slug/`
- asks one high-leverage clarification question at a time, with a recommended answer and tradeoff

### `life-os-reflect-cover-orchestrator`

- coordinates a daily reflection worker and a cover-generation worker in sequence
- enforces the rule that cover generation starts only after the journal is complete
- includes babysitting rules for approvals, `/btw` progress checks, and the 15-minute writing window
- verifies journal path, local image, hosted image URL, and operation log before final reporting

### `life-os-smart-clipper`

- turns explicitly authorized URLs into auditable Life-OS Markdown clippings
- routes article, video, social-media, and course URLs to template-compatible output contracts
- uses Defuddle for article-like HTML, with browser or configured web extraction as fallbacks
- documents Node.js/Defuddle installation, Hermes runtime PATH verification, and truthful fallback reporting
- resolves the vault through `LIFE_OS_ROOT` or common Google Drive locations, validates its structure, and never hardcodes a personal path

### `martin-agent-roster`

- manages Martin's local terminal agent roster across cmux and future WezTerm profiles
- separates `agent_harness`, model slot, desired layout, and observed runtime state
- includes guarded dry-run tooling, command catalogs, and a macOS cmux profile tested on Life and Work workspaces
- ships with a WezTerm testing handoff; WezTerm support is not yet validated

### `martin-outcome-package`

- turns transcripts, `.req.md` captures, or fuzzy task inputs into a governed six-deliverable outcome package
- keeps D1 deep report and D2 executive summary as the minimum deliverables, with optional D3-D6 package routes
- authors `design.md`, `design-stack.md`, and `martin-pptx-handoff.md` while delegating `deck-spec` / artifacts / PPTX production to `martin-pptx-skill`
- adds deck-first scheduling, D0/Deep Research escape hatches, external package access checks, route readiness checks, worker acceptance gates, and state synchronization safeguards for time-sensitive deck-led packages
- includes portable references, templates, smoke-test criteria, and no mandatory vault-specific runtime paths

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

### `notebooklm-deck-factory`

- creates auditable NotebookLM deck-generation run packages from source bundles, `deck-outline.md`, and `design.md`
- preserves source, prompt, notebook/artifact manifests, PPTX/PDF download records, and render evidence
- includes NotebookLM-specific outline/design templates and explicit editability QC for image-baked PPTX exports

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

### 2026-07-11

- add `life-os-smart-clipper`, a portable, template-aware URL-to-Obsidian workflow with Defuddle extraction, fallback routing, frontmatter validation, and Google Drive-aware Life-OS root discovery

### 2026-06-29

- update `martin-outcome-package` with deck-led execution gates from a real dry-run retrospective:
  - D4/D5 deck-first scheduling and polish-buffer guidance
  - D0 / Deep Research escape hatch when local context is stronger than generic research
  - Cloud Expert / external package access verification
  - cmux/shore delegation and master acceptance rules
  - deck route readiness and NotebookLM visual-reference defaults
  - package README gate-status fields for state synchronization

### 2026-06-03

- add `martin-outcome-package`, a portable six-deliverable outcome package skill with D1-D6 templates, DesignMD/DesignStack planning, and `martin-pptx-skill` handoff

### 2026-05-29

- add `conference-video-deck-transcript`, a workflow-and-scripts skill for producing numbered per-speaker Deck PDFs and Transcript Markdown files from conference videos, transcripts, and agendas
- add `life-os-reflect-cover-orchestrator`, a Life-OS workflow skill for coordinating daily reflection and cover generation across worker agents

### 2026-05-28

- add `codex-fluent` and `codex-retrospective` with full reference folders
- add `grill-me`, a session-scoped requirement grilling workflow adapted for Life-OS and Work-PKM
- document both skills in the root inventory and notes

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
