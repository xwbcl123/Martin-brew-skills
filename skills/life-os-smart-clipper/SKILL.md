---
name: life-os-smart-clipper
description: Extract, summarize, classify, and archive a user-supplied URL as a Life-OS smart clipping. Use when the user says to save, archive, clip, collect, or turn a URL into a note; when a URL needs the same intelligent-template treatment as the Obsidian Web Clipper; or when a clipping needs Chinese summary, structured analysis, frontmatter, tags, Johnny Decimal routing, and related-note links.
---

# Life-OS Smart Clipper

Turn an explicitly user-authorized URL into an auditable Life-OS note. Match the existing Obsidian Web Clipper templates' output contracts, but render ordinary Markdown rather than Web Clipper JSON.

## Resolve the Life-OS root

Do not infer the vault from Hermes' current working directory. Resolve `LIFE_OS_ROOT` in this order:

```text
1. Use an explicit LIFE_OS_ROOT environment variable when it is set.
2. Search these common Google Drive locations for a Life-OS folder:
   ~/Library/CloudStorage/GoogleDrive-*/我的云端硬盘/Life-OS
   ~/Library/CloudStorage/GoogleDrive-*/My Drive/Life-OS
   ~/Google Drive/*/Life-OS
3. As a final local fallback, check ~/Documents/Life-OS.
```

- Accept a candidate only when it contains both `AGENTS.md` and `00-09_System-Meta/`.
- If several candidates pass validation, never guess a write target; report them and ask the user to select one.
- Run vault searches and all note writes beneath the resolved `LIFE_OS_ROOT`.
- Resolve every destination in `references/life-os-routing.md` relative to `LIFE_OS_ROOT`.
- `HERMES_HOME` stores skill state only; never write clipped notes there.

## Authorization and scope

- Treat `保存为笔记`、`归档`、`剪藏`、`收藏` or an equivalent explicit instruction as authorization to write one note.
- For `看看`、`分析` or a bare URL, extract and propose the template/path without writing.
- Never create a new Johnny Decimal entity or guess a JD_ID. Route source material into the existing libraries; create derived notes only when separately requested.
- Preserve the extracted Markdown under `## 原始正文`. Generated summaries, translations, tags, and links must be additive.

## Read the contracts

Before clipping, read both references:

1. `references/template-contracts.md` for the template selection and required output blocks.
2. `references/life-os-routing.md` for destinations, frontmatter, naming, deduplication, and link rules.
3. `references/defuddle-dependency.md` before the first Defuddle invocation in a session.

## Workflow

1. Canonicalize the URL and identify its source type before fetching.
2. Select the template using the ordered matching rules in `template-contracts.md`; record it in `template:` frontmatter.
3. Verify the Defuddle dependency when the selected route is an article-like HTML page; use the dependency reference's installation and fallback rules.
4. Extract source material:
   - Use `defuddle parse "$URL" --md` for standard article-like HTML pages. Capture its output before summarizing.
   - Use the configured Hermes web extractor (Firecrawl) when Defuddle fails, returns an access/error page, or returns too little meaningful text.
   - Do not use Defuddle for YouTube/podcasts, PDFs, raw `.md` files, or social-platform pages. Use a transcript extractor, PDF extractor, direct Markdown fetch, or the rendered web/browser fallback instead.
   - Preserve factual failure signals such as `HTTP 403`, `原文提取失败`, or missing transcript. Do not invent unavailable source content.
5. Validate extraction quality before generating analysis: title and canonical URL must exist; source text must be substantial enough for the chosen template; reject cookie walls, login pages, navigation-only output, and duplicate text.
6. Render the selected template in Simplified Chinese. Generate only claims grounded in the extracted source. Keep original-language quotations marked as quotations.
7. Use the routing reference to select a stable existing destination under `LIFE_OS_ROOT`, normalize the filename, and check for duplicate canonical URLs or substantially identical titles before writing.
8. Find related notes by title, tags, and topic. Link only high-confidence matches; otherwise write `- 暂无高置信关联笔记`.
9. Write exactly one Markdown note, then run:

   ```bash
   python3 scripts/validate_clip.py /absolute/path/to/note.md
   ```

10. Report the selected template, extraction method/fallback, final path, and validation result.

## Safety and fallback rules

- Keep Hermes' configured Firecrawl backend unchanged; this skill is a source router, not a global backend replacement.
- If a page needs authentication, payment, CAPTCHA, or consent interaction, stop extraction and state the boundary. Do not bypass it.
- For a failed extraction, save no fabricated full-text clipping. If the user explicitly still wants a record, write a short intake note that contains the URL, available metadata, and the exact failure signal.
- Do not replace existing Web Clipper template JSON files. Their prompts are the design contract for this skill.
