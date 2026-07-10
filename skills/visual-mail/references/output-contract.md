# Output Contract

## File Naming

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

## Visual Brief HTML Contract

- Self-contained single `.html` file
- Dependencies via CDN only (Tailwind, Lucide, Inter font)
- Width: 1080px fixed container
- Header: gradient + title + date + audience
- Main: responsive grid of content cards (2–3 columns desktop)
- Footer: `Martin Design ©️ CSTC All Rights Reserved`
- Font sizes: Keep card body text and list items at `text-sm` (14px) or larger to ensure legibility in screenshots. Avoid using `text-xs` (12px) for card body text or list content; restrict `text-xs` (12px) to minor labels, metadata, or timestamps.

## Screenshot Contract

- Format: PNG
- Full-page capture (no clipping)
- Wait for: Lucide icon render, Google Fonts load, Tailwind CSS parse
- On failure: record exact command attempted and error in `test-report.md`
