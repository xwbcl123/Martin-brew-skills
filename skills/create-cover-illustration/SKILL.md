---
name: create-cover-illustration
description: Generate hand-drawn 16:9 journal memory-map covers, minimal editorial covers, article illustrations, cartoon infographics, or reusable image prompts. Use when Codex needs to create, compare, refine, replace, or publish a journal or writing cover, with built-in image generation first and Gemini as a verified-failure fallback.
---

# Create Cover Illustration

Create one memorable 16:9 hand-drawn cover from a journal, article, briefing, or note. For a daily journal, default to a dense but legible memory map that reconstructs the day. For ordinary writing, default to a minimal editorial illustration.

## Select a mode and profile

- Use `journal-cover` with `journal-memory-map` for daily journals and reflective logs. This is the default journal profile.
- Use `journal-cover` with `minimal-editorial` only when the user asks for a sparse, single-metaphor cover.
- Use `writing-illustration` with `minimal-editorial` for articles, briefings, and ordinary notes.
- Use `prompt-only` when the user wants a reusable prompt or no image generator is available.

Read the reference that matches the selected profile:

- `references/journal-memory-map.md` for daily journal covers.
- `references/minimal-editorial.md` for sparse covers and writing illustrations.
- `references/quality-and-retry.md` before generation, candidate comparison, regeneration, or fallback.
- `references/prompt-contract.md` for shared style and safety constraints.

## Build the visual plan

1. Read the complete source and identify the exact title, date, emotional tone, central narrative, major time blocks, and concrete objects that change the picture.
2. For `journal-memory-map`, build an in-memory storyboard with one central scene, 5-8 event clusters, a bottom timeline or emotional arc, exact critical labels, and explicit exclusions. Cover the major threads; do not illustrate every sentence.
3. For `minimal-editorial`, select one main metaphor and no more than three supporting clusters.
4. Compile the storyboard into a concrete final image prompt. Freeze that prompt before calling an image tool; retries must reuse it unchanged.

Prefer a Sol-class orchestrator for high-value journal storyboarding and candidate selection when the active surface can be chosen. The orchestrator plans the picture; the image model renders it. Do not simplify the contract merely because the active orchestrator is Terra or Luna.

## Generate with Codex

When built-in image generation is available, use it first.

1. Generate one 16:9 image from the frozen prompt.
2. If the call is still running, wait; running is not failure.
3. On an explicit retryable network or service failure, retry up to two times with the identical prompt. Do not translate, shorten, or otherwise rewrite it between attempts.
4. Locate the generated file under `~/.codex/generated_images/<run-id>/` when the tool does not return a visible path.
5. Inspect the image against the hard and preference gates in `references/quality-and-retry.md`.
6. Use a targeted edit for a localized defect. Regenerate for a wrong date, wrong central story, unreadable critical text, or substantial content drift.
7. Leave the original generated file in place unless the user explicitly asks to remove it.

Use `scripts/generate_cover_image.py` only when built-in generation is unavailable, the user asks for a CLI/API route, another agent needs a portable fallback, or the built-in path has exhausted the verified-failure retry policy. Reuse the same visual profile and storyboard.

## Preserve creative specificity

Prefer recognizable activities, tools, places, workflows, humor, and lived details over generic gears, lightbulbs, dashboards, or anonymous workbenches. Avoid unnecessary official logos and misleading endorsements, but do not suppress an incidental brand-like cue when it makes the memory more faithful and is not distracting.

## Handle supplied or competing candidates

- Inspect every candidate at full useful detail and compare it against the same rubric.
- Prefer semantic coverage, personal specificity, hierarchy, and retrieval value over mere cleanliness.
- If the user requests `mv & rename & replace`, move rather than copy the selected source, preserve or archive an existing published asset when one exists, and modify only the named target.
- A chat-visible image is not a completed artifact. Confirm a real local file before insertion or publication.

## Publish a journal cover

Before changing a journal file, read the nearest local instructions such as `_meta.md`, `AGENTS.md`, or a project README.

1. Save the source under the journal's configured asset folder. If no convention exists, prefer `_assets/YYYY/MM/YYYYMMDD_journal-cover[-slug].png`.
2. Insert exactly one Markdown image block immediately after the H1 and before the opening paragraph:
   ```markdown
   ![concrete visible-content alt](../../_assets/YYYY/MM/YYYYMMDD_journal-cover.png)
   > ⬆️ *short memory cue*
   ```
3. Keep the alt text concrete and ideally <= 60 Chinese characters. Keep the caption ideally <= 30 Chinese characters. Do not use an Obsidian image wikilink.
4. If the workspace has an image pipeline, run its dry-run before real execution.
5. Verify the local image MIME, H1-adjacent embedding, and every artifact promised by the local workflow. For hosted output, also verify HTTP 200 and an image content type.
6. Append the result to the local operation log when that convention exists. Record the generation path, prompt hash, attempt outcomes, selected candidate, local source, hosted URL if any, backup, URL map, caption, and warnings.

After a configured publishing pipeline runs, the journal may point to its hosted URL while the local source remains in the configured asset folder.

## Handle ordinary writing

- Save to the requested path or an article-local `_assets/` directory.
- Do not upload or edit the Markdown unless the user explicitly asks.
- If the document belongs to `writer-agent`, use its existing upload pipeline.

## Use the portable fallback

The fallback script prefers native Gemini through `google-genai` and uses an OpenAI-compatible proxy only when a configured endpoint is online. Configuration is loaded from the current project or parent `.env` files, `COVER_ILLUSTRATION_ENV_FILE`, or `--env-file`. It generates or prints a prompt and saves a local image; it does not upload or rewrite Markdown.

```bash
python skills/create-cover-illustration/scripts/generate_cover_image.py \
  --input-md path/to/journal.md \
  --mode journal-cover \
  --layout-profile journal-memory-map \
  --dry-run
```

```bash
python skills/create-cover-illustration/scripts/generate_cover_image.py \
  --input-text "Create a cover for a concise technical briefing." \
  --mode writing-illustration \
  --layout-profile minimal-editorial \
  --env-file .env \
  --output .tmp/briefing-cover.png
```
