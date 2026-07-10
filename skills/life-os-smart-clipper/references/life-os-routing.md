# Life-OS routing and note contract

All destinations below are relative to the `LIFE_OS_ROOT` resolved by `SKILL.md`. On the current machine, it is the Google Drive-mounted Life-OS vault; do not hard-code that machine-specific path in generated notes.

## Stable destinations

| Source type | Destination | Filename |
| --- | --- | --- |
| Article / blog / policy / documentation | `50-59_Knowledge-Writing/51.14_reading-clippings-lib/articles/` | `YYYYMMDD_<source>_<slug>.md` |
| Newsletter / Substack | `50-59_Knowledge-Writing/51.14_reading-clippings-lib/newsletters/` | `YYYYMMDD_<source>_<slug>.md` |
| YouTube / podcast / interview | `50-59_Knowledge-Writing/51.14_reading-clippings-lib/podcasts/` | `YYYYMMDD_yt_<slug>.md` or `YYYYMMDD_podcast_<slug>.md` |
| X/Twitter / LinkedIn / WeChat social post | `50-59_Knowledge-Writing/51.14_reading-clippings-lib/tweets/` | `YYYYMMDD_<source>_<slug>.md` |
| Claude Code in Action lesson | `40-49_Technology-Tools/41.10_agi-gpt-research-lib/05_learning_projects/10_claude-code-in-action/00_inbox/` | `YYYY-MM-DD_<chapter>-<lesson>_<slug>.md` |

Use the article destination as the fallback for ordinary web pages. Keep all source clips inside their library even if they inform a project; link the project note instead of moving the source material.

## Frontmatter

Write valid YAML and include the fields below. Omit a value only when unavailable; do not invent it.

```yaml
---
title: "Original title"
source: "https://canonical-url"
source_url: "https://canonical-url"
author: []
published: "YYYY-MM-DD"
created: "YYYY-MM-DD"
clipped: "YYYY-MM-DD"
jd_id: "51.14"
type: clip
template: smart-summary
tags:
  - clippings
  - source/example
  - topic/example
status: active
extraction_method: defuddle
---
```

Use `type: video` for YouTube, `type: social` for social sources, and `type: course-note` for the course. Use the destination entity's JD_ID when it is not `51.14`.

## Deduplication and linking

1. Search the proposed destination and `51.14_reading-clippings-lib` for the canonical URL before writing.
2. If a matching URL exists, update nothing; report the existing note unless the user explicitly asks for a refresh.
3. Search title keywords and generated topic tags for related notes. Add only high-confidence wikilinks under `## 关联笔记`.
4. Never create a new JD entity, MOC, or project as a side effect of clipping.

## Required note order

1. YAML frontmatter
2. `# <title>`
3. Template-specific generated blocks
4. `## 关联笔记`
5. `## 原始正文`
6. `## 网页高亮`
