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

# 独立验证（不重跑分析，仅校验现有产物）
/summary --validate-only --output Clippings/DIS-Outputs/20260405_slug/ --source Clippings/2026-04-05_yt_source.md
```

**参数说明**

| 参数 | 说明 | 默认 |
|------|------|------|
| `<file-path>` | 源文档路径（必填，正常模式） | — |
| `--start-from "<标题>"` | 显式指定正文起始标题（跳过该标题之前的所有内容） | frontmatter 后全文 |
| `--output <path>` | 覆盖输出目录 | 源文件同级 `DIS-Outputs/YYYYMMDD_slug/` |
| `--validate-only` | 独立验证模式：仅校验已存在产物，不重跑分析 | — |
| `--source <file-path>` | 配合 `--validate-only` 使用，指定原始源文件（必填） | — |

> **默认行为**：对全文进行总结（frontmatter 之后即为正文起点），不自动跳过任何章节。
> 若只想分析转录稿部分，请传入 `--start-from "## Transcript"`。

> **`--validate-only` 模式**：对已有的 DIS 输出目录执行独立校验，通过磁盘扫描重建 manifest，
> 不依赖运行态内存。校验结果写入 `validation_log.md`，不覆盖原有 `run_log.md`。
> Source Chunk frontmatter 缺失字段为**硬阻断**，会导致验证失败并明确列出不合规文件。

## Hard Contracts

1. **源文件只读**：全程使用 Read 工具，不得修改源文档任何内容
2. **输出命名规范**：
   - Dashboard: `Summary_Dashboard.md`
   - Chunk: `Chunk_NN_Summary.md`（NN 两位数补零，如 `Chunk_01_Summary.md`）
3. **Obsidian wikilink**：所有内部引用使用 `[[文件名]]` 格式（不带路径前缀），确保在 Obsidian vault 内可跳转
4. **frontmatter 必填字段**：见 `reference/output-templates.md`
5. **不创建 JD 实体**：输出是 skill 产物，不分配 JD_ID，不生成 `_meta.md`
6. **版本去重**：若输出目录已存在，追加 `-v2`/`-v3` 后缀
7. **SHA256 尽力审计**：尝试计算并写入 `run_log.md`；若在网络盘等场景下超时/挂起，写入 `SKIPPED` 并继续，不中止任务
8. **Source Chunk 完整性**：`Chunk_NN_Source.md` 必须包含全部五个字段（`chunk_id`/`title`/`source_file`/`start_line`/`end_line`）；缺失为硬阻断
9. **切片厚度**：默认目标 5K–10K 字符/chunk，优先合并相邻标题块；总 chunk 数目标区间 15–25

## Workflow Routing

| 阶段 | 文件 |
|------|------|
| 主编排流程 (Phase 0-4) | `workflows/orchestration.md` |
| 分片规则 | `workflows/chunking-strategy.md` |
| DIS-Analyst 人格注入 | `prompts/dis-analyst-persona.md` |
| Chunk 四维分析格式 | `prompts/chunk-summary-instruction.md` |
| 全局综合指令 | `prompts/dashboard-synthesis.md` |
| 输出模板 | `reference/output-templates.md` |

**执行入口**:
- 收到 `/summary <file>` 指令 → 读取 `workflows/orchestration.md` 启动 Phase 0
- 收到 `/summary --validate-only` 指令 → 读取 `workflows/orchestration.md` 跳转至附录 `--validate-only` 节

## Trigger Patterns

- `/summary <file>`
- "总结这个文档", "帮我分析这篇文章"
- "生成 wiki", "转换为知识库"
- "long document summary", "document analysis"
- "DIS", "@doc-intelligent-summary"
- 用户提供文档路径 + 要求摘要/分析/总结

## File Structure

```
skills/doc-intelligent-summary/
├── SKILL.md                           # 入口路由（本文件）
├── workflows/
│   ├── orchestration.md               # 主流程 Phase 0-4
│   └── chunking-strategy.md           # 分片规则 + 边界情况
├── prompts/
│   ├── dis-analyst-persona.md         # 智库分析师人格
│   ├── chunk-summary-instruction.md   # 四维分析输出格式
│   └── dashboard-synthesis.md         # 全局综合指令
└── reference/
    └── output-templates.md            # Dashboard + Chunk 模板
```
