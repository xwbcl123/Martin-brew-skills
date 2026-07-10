# Template contracts

When present, use the published Web Clipper JSON templates under
`$LIFE_OS_ROOT/50-59_Knowledge-Writing/51.10_pkm-learning-lib/11_obsidian-web-clipper-templates_proj/20_templates/`
as the local output authority. The contracts below remain self-contained so this skill works without those files.

## Selection order

| Priority | Match | Template | Required generated blocks |
| --- | --- | --- | --- |
| 1 | `anthropic.skilljar.com/claude-code-in-action` | `Claude Code in Action` | AI 摘要, 课程信息, 课程内容, 学习笔记与高亮; add `chapter`, `lesson`, `course` properties when known. |
| 2 | `youtube.com`, `youtu.be`, podcast/video URLs | `YouTube Briefing` | 报告摘要, 引言部分, 核心要点, 核心流程/机制解析, 核心引言, 数据与比喻, 后续思考与行动. Use a transcript, not page text. |
| 3 | X/Twitter, LinkedIn, WeChat official accounts | `Social Media` | 来源信息, 内容摘要, 结构化观点, 核心洞察, 高亮内容, 原文内容. Use rendered content when available. |
| 4 | Article-style HTTP(S) page | `Smart Summary` | AI 摘要, Args分析, 原始正文, 网页高亮. Use Defuddle first. |
| 5 | Other known web content | `Default` | concise AI 摘要, 原始正文, 网页高亮. |

## Required analysis contracts

### Smart Summary

- `AI 摘要`: 100–150 Chinese words covering the main topic, key arguments, and core value.
- `Args分析`: output exactly `## 🧩 论点解构`, `### 核心论题`, `### 主要论据`, `### 反论点处理`, `### 论证结构评估`.
- For each major argument, state the evidence strength (`强` / `中等` / `弱`) and say when evidence or counterarguments are absent.

### YouTube Briefing

- Do not infer video details from title/description alone. Mark unavailable blocks with `⚠️ 未取得可验证转录稿`.
- Include 4–6 structured takeaways when a transcript supports them. Preserve original-language quotations with Chinese translation where helpful.

### Social Media

- Identify platform, author, capture time, thread participants when visible, and distinguish the author’s claims from the agent’s synthesis.
- Use a Markdown table for `结构化观点`: `发言人 | 核心观点 | 关键证据/例子`.

### All templates

- Output in Simplified Chinese. Keep technical terms in their original English where precision matters.
- Preserve user highlights when supplied; otherwise write `- 无用户高亮`.
- Do not silently omit headings. State the evidence boundary inside the relevant section.
