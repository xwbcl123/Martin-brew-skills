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

When the built-in `image_gen` tool is available, it is the mandatory first path for Codex. Do not call the fallback script first to generate the actual image or to "preflight" an image prompt unless the user explicitly asks for a CLI/API route or prompt-only output.

1. Read the target content and extract the title, core themes, emotional tone, and 3-6 visual keywords.
2. Build a prompt from `references/prompt-contract.md`; either provide structured theme bullets yourself, or include the full source with an explicit instruction for the image model to extract the visual themes before composing the image.
3. Generate one 16:9 hand-drawn cartoon infographic with `image_gen`.
4. Locate the generated PNG under the Codex generated-images directory. In typical Codex harnesses, generated images are saved under `~/.codex/generated_images/<run-id>/` by default.
5. Inspect the image for theme fit, readable text, hand-drawn style, and banned elements.
6. Copy the selected image into the target workflow's asset location. Leave the original generated image in place unless the user explicitly asks to delete it.

For journal covers, continue with the journal workflow below and follow any local workspace instructions before editing notes.

## Decision Gotchas

- `$imagegen` beats fallback. If Codex has `image_gen`, use it directly and only use `scripts/generate_cover_image.py` when `image_gen` is unavailable, the user asks for a CLI/API route, or another agent needs a portable fallback.
- The fallback script is not a prompt-preflight step for Codex. Use `references/prompt-contract.md` directly when composing the prompt.
- If the image appears in the chat but no path is shown inline, check the newest directory under `~/.codex/generated_images/` and copy the chosen PNG from there into the target asset path.
- Do not leave a script-generated or fallback-generated image as the final asset after the user requested or expected Codex `$imagegen`; replace it with the `$imagegen` result, rerun any local image pipeline, and update logs.
- For journal covers, the final note should point to the expected local or hosted image reference, while the local source image remains in the configured asset folder.

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
8. Record the operation in the local workflow log when that convention exists, including generation method, generated-image source path if available, local source, hosted URL if any, backup file, URL map, caption, and any pipeline warnings.

## Writing Illustration Workflow

For ordinary writing, generate the image and keep mutations conservative.

- Save to the user-requested path or an article-local `_assets/` directory.
- Do not upload by default.
- Do not edit the Markdown unless the user explicitly asks for insertion.
- If the document belongs to a larger writing system with its own upload pipeline, prefer that existing pipeline instead of recreating upload logic in this skill.

## Fallback Script

Use `scripts/generate_cover_image.py` only when the built-in image tool is unavailable, the user asks for a CLI/API route, or another agent needs a portable fallback.

For Codex runs with `image_gen` available, do not use the fallback script as a decision-making shortcut. The script is a portability fallback, not the preferred implementation.

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
