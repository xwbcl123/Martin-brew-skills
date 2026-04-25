---
name: create-cover-illustration
description: Generate hand-drawn 16:9 journal cover images and writing illustrations. Use when Codex needs to create a daily journal chapter image, article cover illustration, cartoon infographic, or reusable image prompt, with Codex image_gen as the primary path and a bundled Gemini API fallback for other agents.
---

# Create Cover Illustration

Use this skill to create a single memorable cover illustration for a journal entry, article, briefing, or note. Default to a hand-drawn cartoon infographic in 16:9 landscape format with concise Chinese keywords when the source is Chinese.

## Mode Selection

- Use `journal-cover` when the target is a daily journal entry or reflective log.
- Use `writing-illustration` for ordinary Markdown articles, briefings, and notes.
- Use `prompt-only` when the user wants a reusable image prompt or when no image generator is available.

Read `references/prompt-contract.md` when writing or revising prompts, evaluating image quality, or using the fallback script.

## Primary Codex Workflow

When the built-in `image_gen` tool is available, use it first.

1. Read the target content and extract the title, core themes, emotional tone, and 3-6 visual keywords.
2. Build a prompt from `references/prompt-contract.md`.
3. Generate one 16:9 hand-drawn cartoon infographic.
4. Inspect the image for theme fit, readable text, hand-drawn style, and banned elements.
5. Save the selected image into the target workflow's asset location.

For journal covers, continue with the journal workflow below and follow any local workspace instructions before editing notes.

## Journal Cover Workflow

Before changing a journal library file, read the nearest local instructions such as `_meta.md`, `AGENTS.md`, or an equivalent project README when they exist.

1. Save the source image under the journal's configured asset folder. If no local convention exists, prefer `_assets/YYYY/MM/YYYYMMDD_journal-cover[-slug].png`.
2. Insert the image block immediately after the daily note H1 and before the opening paragraph:
   ```markdown
   ![concrete visible-content alt](../../_assets/YYYY/MM/YYYYMMDD_journal-cover.png)
   > *short memory cue*
   ```
3. Use Markdown image syntax only. Do not use Obsidian image wikilinks.
4. Make the alt text a concrete visible-content sentence, ideally <= 60 Chinese characters.
5. Make the caption a short retrieval cue, ideally <= 30 Chinese characters.
6. If the workspace has an image upload or rewrite pipeline, run its dry-run first, then execute it.
7. Verify the final image reference resolves locally or through the expected hosted URL.
8. Record the operation in the local workflow log when that convention exists, including local source, hosted URL if any, backup file, URL map, and caption.

## Writing Illustration Workflow

For ordinary writing, generate the image and keep mutations conservative.

- Save to the user-requested path or an article-local `_assets/` directory.
- Do not upload by default.
- Do not edit the Markdown unless the user explicitly asks for insertion.
- If the document belongs to a larger writing system with its own upload pipeline, prefer that existing pipeline instead of recreating upload logic in this skill.

## Fallback Script

Use `scripts/generate_cover_image.py` only when the built-in image tool is unavailable, the user asks for a CLI/API route, or another agent needs a portable fallback.

The fallback script prefers native Gemini through `google-genai`. It uses an OpenAI-compatible proxy only when `GEMINI_PROXY_ENDPOINT` is configured and online.

Configuration is read from the current project `.env`, parent `.env` files, `COVER_ILLUSTRATION_ENV_FILE`, or the explicit `--env-file` argument. Do not commit real `.env` files or API keys.

Examples:

```bash
python skills/create-cover-illustration/scripts/generate_cover_image.py \
  --input-md examples/journal-entry.md \
  --mode journal-cover \
  --dry-run
```

```bash
python skills/create-cover-illustration/scripts/generate_cover_image.py \
  --input-text "生成一张手绘卡通信息图，主题是 Skill fallback API smoke test。" \
  --title "Fallback API 验证" \
  --mode writing-illustration \
  --aspect-ratio 16:9 \
  --env-file .env \
  --output .tmp/create-cover-illustration-smoke/fallback-api-smoke.png
```

The fallback script generates or prints an image prompt, calls Gemini when not in dry-run or prompt-only mode, and saves a local image. It does not upload images or rewrite target Markdown.
