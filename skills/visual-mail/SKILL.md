---
name: visual-mail
description: "Transforms any report, brief, analysis, progress report, or meeting minutes into a complete email delivery package: email body (Martin Email Style), visual brief HTML, screenshot preview, and screenshot embedded in email. Use when users want to share a report by email, generate a visual brief and screenshot, embed a visual preview in an email, produce a report-to-email package, or send a brief/analysis/meeting minutes to a team or stakeholder."
---
# Visual-Mail

Compose a full delivery package from a source report: email + visual brief HTML + screenshot.

## Inputs

| Parameter           | Required | Notes                                                   |
| ------------------- | -------- | ------------------------------------------------------- |
| `source_report`   | yes      | Markdown report path                                    |
| `audience`        | yes      | Recipient / target group                                |
| `share_purpose`   | yes      | e.g. 同步进展 / 请求确认 / 正式发送材料                 |
| `report_title`    | no       | Infer from source if omitted                            |
| `email_language`  | no       | Default: Chinese                                        |
| `brief_link`      | no       | Use `<BRIEF_LINK_PLACEHOLDER>` if unpublished         |
| `visual_link`     | no       | Use `<VIZ_LINK_PLACEHOLDER>` if unpublished           |
| `brand_guideline` | no       | Path to `.brand_guideline.md`; auto-select if omitted |
| `output_slug`     | no       | Auto-generate from date + title if omitted              |

## Workflow

### Step 1 — Analyze the source report

Read `source_report`. Extract:

- One-line report positioning
- 3–5 core points most relevant to `audience`
- Any deadlines, risks, requests, or next steps
- What belongs in the email body vs. in the visual brief

### Step 2 — Select brand guideline

See `references/brand-selection.md` for full policy.

1. Use the user's explicit brand or template.
2. Otherwise read `brand-guidelines` and classify Life versus Work.
3. Use only the assets and typography of that selected identity. Use a neutral bundled fallback only when no applicable brand is available.

Before writing, resolve the canonical Task Session and its approved `artifact_class` / authoritative destination. Set `OUTPUT_ROOT` to that destination; working HTML, screenshots and email drafts may use the session's working directories. Do not create new `tasks/shore/` records or default new outputs to global root assets/emails.

### Step 3 — Generate visual brief HTML

Apply `viz-brief` principles (see `.claude/commands/viz/viz-brief.md`):

- Single-file HTML, Tailwind CDN + Lucide CDN + Inter font (Google Fonts CDN).
- Output: `<OUTPUT_ROOT>/assets/viz/YYYYMMDD-<slug>.html`
- Apply selected brand colors: header gradient, card accent colors, typography.
- Content cards by report type:
  - Progress brief: 总体判断 / 关键进展 / 支撑体系 / 下一步
  - Analysis report: 核心发现 / 影响判断 / 风险机会 / 建议
  - Meeting minutes: 决策 / 行动项 / 责任人 / 风险 / 后续
- Font sizes (Mandatory Legibility Rule): Avoid using `text-xs` entirely across all visual briefs (including badges, footers, metadata, tags, and body copy). Use `text-sm` (14px) as the absolute minimum font size to ensure crystal-clear legibility in screenshot previews and emails.
- Footer, byline, Logo and Logo dimensions follow the selected brand/template contract. Do not rotate logos or override a user-selected identity.
- Test intermediates belong under the current canonical session's scoped test directory.

### Step 4 — Capture screenshot

Load the HTML file and capture a full-page PNG.

Select a currently available capture tool that fits the active harness. These are alternatives, not claims of availability:

1. Chrome DevTools MCP / CDP
2. Playwright (`playwright screenshot --full-page`)
3. `chromium-browser --headless --screenshot`

Wait for Lucide icons, web fonts, and Tailwind CDN to finish rendering before capturing.

Output: `<OUTPUT_ROOT>/assets/img/YYYYMMDD_<slug>.png`

If screenshot is unavailable: record the blocker in `test-report.md` and continue.

Keep test screenshots in the current session's scoped test directory.

### Step 5 — Draft email

Apply Martin Email Style Guide v2 (see `references/output-contract.md` for summary). For executive leadership briefings, drill/compliance reports, and formal business communication, follow `references/business-email-style.md` (Three-Paragraph Executive Body Rule, Factual Reconstruction, Highlights model, and no-ai-slop baseline).

- File: `<OUTPUT_ROOT>/emails/YYYYMMDD_<slug>-to-<audience>.md`
- Flow pattern: Update/Briefing
- Language: Chinese by default
- No emoji
- Body: purpose sentence → 2–4 key facts → links → screenshot embed

Required elements:

```
[报告标题](<BRIEF_LINK_PLACEHOLDER>)
[可视化简报](<VIZ_LINK_PLACEHOLDER>)
![[assets/img/YYYYMMDD_<slug>.png]]
```

Replace placeholders with real links if provided.

Keep test email drafts in the current session's scoped test directory.

### Step 6 — Validate outputs

Run cleanup checklist from `references/cleanup-checklist.md`.

Remove internal production notes, private paths, credentials and review chatter from public content. Preserve legitimate subject matter about agents, prompts or AI; keywords alone are not a deletion rule. Check links and screenshot fidelity. Draft placeholders must be resolved before sending.

Creating this package does not send an email or publish its assets. Send only when the user has authorized the recipients and content; reuse that authorization without repeated confirmation. Check existing send receipts before retrying an uncertain send.

## Output Summary

| File          | Location                                    |
| ------------- | ------------------------------------------- |
| Email `.md` | `<OUTPUT_ROOT>/emails/YYYYMMDD_<slug>-to-<audience>.md` |
| Visual HTML   | `<OUTPUT_ROOT>/assets/viz/YYYYMMDD-<slug>.html`         |
| Screenshot    | `<OUTPUT_ROOT>/assets/img/YYYYMMDD_<slug>.png`          |

## References

- `references/brand-selection.md` — brand guideline selection policy
- `references/output-contract.md` — email style guide and output format rules
- `references/business-email-style.md` — executive briefing and business email style guide (three-paragraph rule, factual reconstruction, no-ai-slop)
- `references/cleanup-checklist.md` — cleanliness and security validation checklist
- `assets/fallback-styles/` — three bundled fallback brand styles

