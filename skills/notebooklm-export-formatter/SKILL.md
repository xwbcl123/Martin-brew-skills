---
name: notebooklm-export-formatter
description: Convert NotebookLM-exported Markdown into clean Obsidian-friendly Markdown by restoring headings, lists, emphasis, and Markdown footnotes. Use this whenever the user mentions NotebookLM export formatting loss, wants to recover headings or bullet structure from a raw NotebookLM report, or needs bracket references like [1] / \\[1\\] converted into footnotes.
license: Internal
---

# NotebookLM Export Formatter

## Overview

这个 skill 用于处理 `NotebookLM` 导出的 Markdown 报告在复制或导出过程中出现的结构丢失问题。

V1 目标很明确：
- 恢复标题层级
- 恢复列表结构
- 保留并整理加粗标签
- 将正文引用从 `[1]` / `\[1\]` 转为 `[^1]`
- 将文末引用区改为 Markdown footnotes

这个 skill 默认只做格式修复，不改写事实内容，不重写论证，不摘要。

## When To Use

在这些场景下应优先使用本 skill：

- 用户说 `NotebookLM` 导出的 Markdown 很乱
- 用户想恢复 `heading` / `bold` / `list` 结构
- 用户已有一份 raw export，需要转成更适合 `Obsidian` 的版本
- 用户想把文中的 `[1]` 引用改成 `[^1]` 脚注
- 用户有 `origin` 和人工 `polished` 两版，想据此反向迭代格式规则

## File Structure

```text
.agents/skills/notebooklm-export-formatter/
├── SKILL.md
├── scripts/
│   └── format_notebooklm_export.py
├── reference/
│   ├── origin_example.md
│   └── formatted_example.md
└── workflows/
    └── iteration-loop.md
```

## Core Workflow

### 1. Read the input file

确认输入是 `NotebookLM` 导出的 Markdown，而不是已经高度整理过的正式文稿。

重点识别这些模式：
- frontmatter 中存在 `source: NotebookLM`
- 正文前部有 `导出时间:`
- 裸段落形式的章节标签，例如 `ℹ️Meeting Information`
- 裸段落形式的结构标签，例如 `💬 **Discussion** :`
- 文中引用是 `\[1\]` 或 `[1]`
- 文末存在 `## 引用来源` 与 `[1] xxx`

### 2. Run the formatter script

```bash
python skills/notebooklm-export-formatter/scripts/format_notebooklm_export.py "input.md"
```

常用参数：

```bash
python skills/notebooklm-export-formatter/scripts/format_notebooklm_export.py "input.md" --output "output.md"
python skills/notebooklm-export-formatter/scripts/format_notebooklm_export.py "input.md" --dry-run
python skills/notebooklm-export-formatter/scripts/format_notebooklm_export.py "input.md" --learn-from "polished.md" --notes-out "iteration_notes.md"
```

### 3. Review the output

检查以下质量门槛：

- frontmatter 仍然有效
- 主标题没有重复
- `Meeting Information` / `Meeting Minutes` 等大块结构已恢复为 headings
- `Discussion` / `Decisions` / `Follow-Up Action Plans` 已恢复为列表层级
- 所有正文引用都已变为 `[^n]`
- 文末引用区已变为 `[^n]: ...`
- 没有新增乱码或明显的层级错乱

## Output Contract

默认输出为同目录下：

```text
<stem>_formatted.md
```

例如：

```text
meeting_mom-origin.md -> meeting_mom-origin_formatted.md
```

如果显式传入 `--output`，则写入指定路径。

## Learning Loop

如果用户手工修过输出稿，使用：

```bash
python skills/notebooklm-export-formatter/scripts/format_notebooklm_export.py \
  "raw.md" \
  --learn-from "polished.md" \
  --notes-out "iteration_notes.md"
```

这个流程不会自动“训练模型”，而是做两件事：

- 输出当前格式化结果与 polished 版本的差异摘要
- 帮助后续更新脚本规则、few-shot 示例和 skill 指令

详细说明见：`workflows/iteration-loop.md`

## Reference Examples

格式判断优先参考：

- `reference/origin_example.md`
- `reference/formatted_example.md`

当模型不确定某一类段落应转为标题、一级列表还是二级列表时，先比对 reference 示例，再做最小改动。

## Non-Goals

本 skill 默认不负责：

- 改写正文内容
- 合并或删除引用编号
- 重写语言风格
- 修复复杂表格
- 补全外链或元数据

如果用户要的是“内容润色”而不是“格式恢复”，不要误用本 skill。
