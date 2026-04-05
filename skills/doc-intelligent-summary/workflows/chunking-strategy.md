# Chunking Strategy

> Part of: `doc-intelligent-summary` skill
> 被 `workflows/orchestration.md` Phase 1 引用

---

## 1. 正文起点检测（通用规则）

**优先级从高到低**:

1. **显式参数**: 若用户传入 `--start-from "<标题>"`，从该标题行开始，忽略之前所有内容
2. **默认全文**: 跳过 YAML frontmatter（`---` 到 `---` 之间）后，从第一个内容段落开始

> **产品意图**：DIS 的默认行为是对全文进行总结，不跳过任何正文区域。
> 若需从特定章节（如 `## Transcript`）开始分析，请**显式传入** `--start-from "## Transcript"`。
> 不再自动扫描任何锚点标题作为正文起点。
> 不硬编码行号，不做样本特判。

---

## 2. 分片策略矩阵

| 输入格式 | 检测条件 | 分片策略 |
|---------|---------|---------|
| Markdown (有 H3) | 正文区含 `###` 标题 | **主策略**: 按 `###` 切分 |
| Markdown (有 H2，无 H3) | 有 `##` 但无 `###` | 降级到按 `##` 切分 |
| Markdown (无 H2/H3) | 纯段落文本 | 降级到 2000 token 窗口 |
| TXT / 纯文本 | 非 Markdown 格式 | 2000 token 窗口，10-15% 重叠 |
| PDF（已转为文本） | — | 同 TXT 策略 |

---

## 3. H3 分片细化规则

按 `###` 切分后，对每个 chunk 进行后处理：

### 3.1 合并过短 chunk
- **条件**: chunk 字数 < 200 字（不含标题行）
- **操作**: 与下一个 chunk 合并，标题合并为 `标题A + 标题B`
- **边界**: 若是最后一个 chunk 且过短，与前一个合并

### 3.2 拆分过长 chunk
- **条件**: chunk 字数 > 5000 字
- **操作**: 在段落边界（空行）拆分为 2-3 个子 chunk
- **命名**: `原标题 (Part 1/2)`

### 3.3 最大 chunk 数限制
- 单次任务 chunk 数上限: 50
- 超出时，自动将字数最少的相邻 chunk 两两合并，直到不超过 50

---

## 4. Token 窗口策略（TXT/无标题 Markdown）

- **窗口大小**: 2000 tokens ≈ 1500 中文字 ≈ 3000 英文词
- **重叠**: 10-15%（约 200-300 tokens），保证上下文连贯
- **切点**: 优先在段落边界（空行）切分，其次在句号/换行处
- **chunk 标题**: 自动生成 `Section N (Lines X-Y)`

---

## 5. 短文档处理

- **条件**: 全文（去除 frontmatter 后）字数 < 500 字
- **策略**: 单 chunk 处理，chunk_id = 1，标题 = 文档标题
- **仍然生成 Dashboard**（包含单个 chunk 的四维分析）

---

## 6. Chunk Manifest 格式

分片完成后，Phase 1 生成内部 manifest（不写入磁盘，在内存/上下文中维护）：

```json
[
  {
    "id": 1,
    "title": "Chapter Title",
    "start_line": 45,
    "end_line": 112,
    "word_count": 1234,
    "status": "pending"
  }
]
```

**status 状态机**: `pending → running → succeeded | failed`
