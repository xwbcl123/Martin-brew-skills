---
name: doc-intelligent-summary
description: "文档智能摘要 (DIS) Skill。将长文档（YouTube 转录稿、研究报告、长篇文章）分片并行分析，输出结构化 Wiki 知识库（Dashboard + Chunk 文件）。触发词：长文档、摘要、summary、wiki、转录稿分析、DIS。"
license: Internal
aspg:
  origin:
    vendor: custom
    imported_at: 2026-04-04
---

# Doc Intelligent Summary (DIS)

## Overview

读取长文档 → 按语义章节分片 → 并行子代理四维分析 → 组装 Dashboard + Chunk Wiki 矩阵。

每个 Chunk 由一个 DIS-Analyst（智库分析师人格）处理，输出核心论点 / 关键数据 / 底层逻辑 / 关键引言四个维度。最终产物完全 Obsidian 兼容，双向 wikilink 导航。

## Quickstart

```
/summary <file-path>
/summary Clippings/2026-04-04_yt_ai-coding.md
/summary Clippings/report.md --start-from "## Transcript"
/summary Clippings/report.md --output Projects/summaries/
```

**参数说明**

| 参数 | 说明 | 默认 |
|------|------|------|
| `<file-path>` | 源文档路径（必填） | — |
| `--start-from "<标题>"` | 显式指定正文起始标题（跳过该标题之前的所有内容） | frontmatter 后全文 |
| `--output <path>` | 覆盖输出目录 | 源文件同级 `DIS-Outputs/YYYYMMDD_slug/` |

> **默认行为**：对全文进行总结（frontmatter 之后即为正文起点），不自动跳过任何章节。
> 若只想分析转录稿部分，请传入 `--start-from "## Transcript"`。

## Hard Contracts

1. **源文件只读**：全程使用 Read 工具，不得修改源文档任何内容
2. **输出命名规范**：
   - Dashboard: `Summary_Dashboard.md`
   - Chunk: `Chunk_NN_Summary.md`（NN 两位数补零，如 `Chunk_01_Summary.md`）
3. **Obsidian wikilink**：所有内部引用使用 `[[文件名]]` 格式（不带路径前缀），确保在 Obsidian vault 内可跳转
4. **frontmatter 必填字段**：见 `reference/output-templates.md`
5. **不创建 JD 实体**：输出是 skill 产物，不分配 JD_ID，不生成 `_meta.md`
6. **版本去重**：若输出目录已存在，追加 `-v2`/`-v3` 后缀

## Workflow Routing

| 阶段 | 文件 |
|------|------|
| 主编排流程 (Phase 0-4) | `workflows/orchestration.md` |
| 分片规则 | `workflows/chunking-strategy.md` |
| DIS-Analyst 人格注入 | `prompts/dis-analyst-persona.md` |
| Chunk 四维分析格式 | `prompts/chunk-summary-instruction.md` |
| 全局综合指令 | `prompts/dashboard-synthesis.md` |
| 输出模板 | `reference/output-templates.md` |

**执行入口**: 收到 `/summary` 指令后，立即读取 `workflows/orchestration.md` 启动 Phase 0。

## Trigger Patterns

- `/summary <file>`
- "总结这个文档", "帮我分析这篇文章"
- "生成 wiki", "转换为知识库"
- "long document summary", "document analysis"
- "DIS", "@doc-intelligent-summary"
- 用户提供文档路径 + 要求摘要/分析/总结

## File Structure

```text
skills/doc-intelligent-summary/
├── SKILL.md
├── workflows/
│   ├── orchestration.md
│   └── chunking-strategy.md
├── prompts/
│   ├── dis-analyst-persona.md
│   ├── chunk-summary-instruction.md
│   └── dashboard-synthesis.md
└── reference/
    └── output-templates.md
```
