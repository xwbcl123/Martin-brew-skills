# Chunk 四维分析输出格式

> 注入方式: 拼接到 dis-analyst-persona.md 之后，在 chunk 文本之前
> 被 `workflows/orchestration.md` Phase 2 引用

---

## 任务指令

分析下方提供的文档片段，按以下**严格格式**输出四维分析报告。

**输出的完整文件结构**如下（包含 frontmatter 和导航）：

```
---
title: "Chunk {NN}: {chunk_title}"
type: dis-chunk
chunk_id: {NN}
dashboard: "[[Summary_Dashboard]]"
tags: [dis-output, chunk-summary]
---

< [[Chunk_{NN-1}_Summary|上一节]] | [[Summary_Dashboard|仪表板]] | [[Chunk_{NN+1}_Summary|下一节]] >

---

# Chunk {NN}: {chunk_title}

### 🌟 核心论点

- **主论**: [一句话结论，直接说明本段最重要的发现或观点]
  - 支撑 1: [原文中的具体证据或论据]
  - 支撑 2: [原文中的具体证据或论据]
  - 支撑 3（如有）: [原文中的具体证据或论据]

### 📊 关键数据

- [量化指标]: [数值] — [上下文说明，该数据说明了什么]
- [量化指标 2]: ...

> 若本段未包含量化数据，写: 本段未包含量化数据。

### 🧠 底层逻辑

- **第一性原理**: [识别本段论点的根本假设或不可约简的核心前提]
- **系统视角**: [描述本段涉及的关系、依赖或反馈回路]
- **逆向思考**: [挑战本段的隐含假设，或构建最强反论]

### 💬 关键故事与引言

- **核心故事**: [2-3 句概括本段中最重要的叙事或案例]
- **金句**: "[原文引用，英文保持英文，中文保持中文]"
  （若无明显金句，省略此条）

---

< [[Chunk_{NN-1}_Summary|上一节]] | [[Summary_Dashboard|仪表板]] | [[Chunk_{NN+1}_Summary|下一节]] >

*来源: [[{source_filename}]]* | *源片段: [[Chunk_{NN}_Source]]*
```

---

## 标题层级约定

| 层级 | 用途 |
|------|------|
| `#` | 文档主标题（Chunk 编号+章节名），**仅出现一次** |
| `###` | 四个维度标题（带 Emoji） |
| `####` | 维度内子项（如需进一步分层） |

**不使用 `##`**，保持层级统一。

---

## 导航 wikilink 规则

- 第一个 chunk（NN=01）: 上一节链接替换为 `← 首节`（纯文本，无链接）
- 最后一个 chunk: 下一节链接替换为 `尾节 →`（纯文本，无链接）
- chunk 文件名格式: `Chunk_NN_Summary`（NN 两位数补零）

---

## 现在开始分析

请使用 **Read 工具**读取以下文件，分析其中的文档原文内容：

**文件路径**: `{chunk_source_path}`

> 文件包含 YAML frontmatter（`chunk_id`、`title`、`start_line`、`end_line`）和原文正文。
> 仅分析正文内容（frontmatter 之后的部分），按上方格式输出四维分析报告。
