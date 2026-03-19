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
- `ds-citations`
- `publish-assets`
- `slide-renamer`
- `prompt-crafter`

## Repository Structure

```text
Martin-brew-skills/
├── skills/
│   ├── audio-transcriber/
│   ├── ds-citations/
│   ├── prompt-crafter/
│   ├── publish-assets/
│   └── slide-renamer/
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
- `publish-assets` is documented as an integration skill and expects external tooling
- environment variables are documented through placeholders only

If you reuse these skills in your own workspace, replace the templates with your private versions locally instead of committing them back here.

## Notes by Skill

### `audio-transcriber`

- Gemini-based audio workflow
- suitable for large-audio transcription and structured markdown generation
- ships with sanitized glossary and demo references

### `ds-citations`

- normalizes GPT / Gemini / OpenAI Deep Research citation artifacts
- includes script, quick reference, and tests

### `publish-assets`

- integration-oriented wrapper skill
- depends on an external image hosting toolkit
- this repository keeps the workflow contract, not the private infrastructure

### `slide-renamer`

- OCR-based slide image renaming utility
- lightweight and self-contained

### `prompt-crafter`

- methodology-driven prompt design skill
- includes reusable reference notes

## Maintenance Principles

- Prefer reusable over clever
- Sanitize before publishing
- Keep structure portable
- Minimize project-specific assumptions

## License

Add the license that matches how you want to share these skills.
