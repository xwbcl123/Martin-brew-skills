# Output Contract

## File Naming

All patterns below are relative to the approved OUTPUT_ROOT, not the vault root. Resolve actual links before delivery.

| Output | Pattern | Example |
|---|---|---|
| Email | `emails/YYYYMMDD_<slug>-to-<audience>.md` | `emails/20260424_csa2-progress-brief-to-cspd.md` |
| Visual HTML | `assets/viz/YYYYMMDD-<slug>.html` | `assets/viz/20260424-csa2-progress-brief.html` |
| Screenshot | `assets/img/YYYYMMDD_<slug>.png` | `assets/img/20260424_csa2_progress_brief.png` |

- `<slug>`: lowercase, hyphen-separated, derived from report title
- `<audience>`: lowercase, hyphen-separated

## Email Format (Martin Email Style v2 — Update/Briefing)

```markdown
---
to: <audience>
subject: <report title> — 进展同步
date: YYYY-MM-DD
---

<recipient salutation>,

<opening: one sentence stating share purpose and report headline>

<body: 2–4 sentences or a compact list of the 3–5 most important points for this audience>

报告原文：[<report_title>](<BRIEF_LINK_PLACEHOLDER>)
可视化简报：[可视化简报](<VIZ_LINK_PLACEHOLDER>)

![[assets/img/YYYYMMDD_<slug>.png]]

<closing line>

Martin
```

### Required elements

- `[报告标题](<BRIEF_LINK_PLACEHOLDER>)` — or real URL if published
- `[可视化简报](<VIZ_LINK_PLACEHOLDER>)` — or real URL if published
- `![[assets/img/YYYYMMDD_<slug>.png]]` — Obsidian-style embed

### Style rules

- No emoji
- No headers (`##`) inside email body
- Low verbosity by default: one screen
- Chinese for Chinese audience; English body + Chinese summary for mixed
- Sentences only — no `> blockquotes` in email body

## Outlook 字体（2026-10-09 Martin 确认）

问题：HTML 邮件在浏览器和 Gmail 里显示正常，到 Outlook 桌面版却变成宋体或 Times New Roman。

原因：Outlook 桌面版用 Word 引擎渲染 HTML 邮件。
1. Word 引擎不走 CSS 字体回退链。第一个字体（如 Inter、PingFang SC、Spline Sans、-apple-system）没装时，它直接用默认字体，不会往后找。
2. 中文属于东亚文字，必须另外用 `mso-fareast-font-family` 声明，`font-family` 里的字体管不到中文。
3. `<style>` 和外层 `body`/`div`/`table` 上的样式经常传不到表格单元格里的文字。

规则（只针对邮件正文 HTML）：
1. 每个带文字的元素（`td`、`th`、`p`、`span`、`a`、`li`、`div`、`h1` 到 `h6`）都写内联字体，微软雅黑放第一位：`font-family:'Microsoft YaHei','微软雅黑',Arial,'PingFang SC',sans-serif; mso-fareast-font-family:'Microsoft YaHei';`。style 属性用双引号，字体名用单引号。
2. `<head>` 里放 Outlook 条件注释块 `<!--[if mso]><style>… mso-fareast-font-family: "Microsoft YaHei"; …</style><![endif]-->`。这是邮件正文里唯一允许的 `<style>`。
3. 不用网页字体：不引 Google Fonts，不写 `@font-face`、`@import`、字体 `<link>`，`font-family` 里不出现 Inter、Spline Sans 等网页字体。

工具：`scripts/outlook_email_fonts.py fix <in.html> <out.html>` 自动补齐，只改标签属性和 `<head>`，正文文字不变；`check <file.html>` 单独检查。visual-mail 的 `validate_outputs.py --email-html` 与 monthly-report-workflow 的 `verify_monthly_report.py`（Gate 7）都会在缺失时报 ERROR。

不在范围内：visual-mail 用来截图的 1080px Tailwind 可视化简报页不是邮件正文，继续按原规则使用 Inter。

## Visual Brief HTML Contract

(Screenshot page only, not an email body. Its Inter/Tailwind fonts are allowed because it is rendered to PNG.)

- Self-contained single `.html` file
- Dependencies via CDN only (Tailwind, Lucide, Inter font)
- Width: 1080px fixed container
- Header: gradient + title + date + audience
- Main: responsive grid of content cards (2–3 columns desktop)
- Footer: selected brand/template contract; no fixed CSTC footer on Life or third-party outputs.
- Font sizes: Keep card body text and list items at `text-sm` (14px) or larger to ensure legibility in screenshots. Avoid using `text-xs` (12px) for card body text or list content; restrict `text-xs` (12px) to minor labels, metadata, or timestamps.

## Screenshot Contract

- Format: PNG
- Full-page capture (no clipping)
- Wait for: Lucide icon render, Google Fonts load, Tailwind CSS parse
- On failure: record exact command attempted and error in `test-report.md`
