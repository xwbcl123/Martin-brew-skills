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

1. User-specified `brand_guideline` → use it.
2. Else: pick from `40 Resources/brand-styles/*.brand_guideline.md` by content tone.
   - Compliance / policy / regulation → Blue-Steel, Blue-Tone, Martin-Borealis
   - Research / insight / trend → Aurora, Nebulae, Nova
   - External market-facing → Martin-Gradient-1, Martin-Spectrum
   - Formal enterprise → Huawei-Template
3. Else: use bundled fallback styles in `assets/fallback-styles/`.

### Step 3 — Generate visual brief HTML

Apply `viz-brief` principles (see `.claude/commands/viz/viz-brief.md`):

- Single-file HTML, Tailwind CDN + Lucide CDN + Inter font (Google Fonts CDN).
- Output: `assets/viz/YYYYMMDD-<slug>.html`
- Apply selected brand colors: header gradient, card accent colors, typography.
- Content cards by report type:
  - Progress brief: 总体判断 / 关键进展 / 支撑体系 / 下一步
  - Analysis report: 核心发现 / 影响判断 / 风险机会 / 建议
  - Meeting minutes: 决策 / 行动项 / 责任人 / 风险 / 后续
- Font sizes: Ensure legibility in screenshots by keeping card body text and list items at `text-sm` (14px) or larger. Avoid using `text-xs` (12px) for card body text or list contents; limit `text-xs` only to minor labels, metadata, or timestamps.
- Footer: `Martin Design ©️ CSTC & EU RSPO All Rights Reserved`

For E2E tests, write to `tasks/shore/<task-slug>/artifacts/e2e/assets/viz/`.

### Step 4 — Capture screenshot

Load the HTML file and capture a full-page PNG.

Preferred tools (in order):

1. Chrome DevTools MCP / CDP
2. Playwright (`playwright screenshot --full-page`)
3. `chromium-browser --headless --screenshot`

Wait for Lucide icons, web fonts, and Tailwind CDN to finish rendering before capturing.

Output: `assets/img/YYYYMMDD_<slug>.png`

If screenshot is unavailable: record the blocker in `test-report.md` and continue.

For E2E tests, write to `tasks/shore/<task-slug>/artifacts/e2e/assets/img/`.

### Step 5 — Draft email

Apply Martin Email Style Guide v2 (see `references/output-contract.md` for summary).

- File: `emails/YYYYMMDD_<slug>-to-<audience>.md`
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

For E2E tests, write to `tasks/shore/<task-slug>/artifacts/e2e/emails/`.

### Step 6 — Validate outputs

Run cleanup checklist from `references/cleanup-checklist.md`.

Confirm public-facing files contain none of: `Agent`, `worker`, `AI generated`, `Main Agent`, `prompt`, `task.md`, `handoff.md`, internal review comments, automation logs.

## Output Summary

| File          | Location                                    |
| ------------- | ------------------------------------------- |
| Email `.md` | `emails/YYYYMMDD_<slug>-to-<audience>.md` |
| Visual HTML   | `assets/viz/YYYYMMDD-<slug>.html`         |
| Screenshot    | `assets/img/YYYYMMDD_<slug>.png`          |

## References

- `references/brand-selection.md` — brand guideline selection policy
- `references/output-contract.md` — email style guide and output format rules
- `references/cleanup-checklist.md` — cleanliness and security validation checklist
- `assets/fallback-styles/` — three bundled fallback brand styles
