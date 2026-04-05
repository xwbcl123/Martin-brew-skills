# Output Templates

> DIS Skill 产物的标准模板和规范
> 被 orchestration.md 和 dashboard-synthesis.md 引用

---

## Summary_Dashboard.md 模板

```yaml
---
title: "智能摘要：{source_title}"
type: dis-dashboard
source: "[[{source_filename}]]"
created: YYYY-MM-DD
total_chunks: N
tags: [dis-output, summary]
---
```

**文件位置**: `{output_dir}/Summary_Dashboard.md`

**必填字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | `智能摘要：` + 源文档标题（从 frontmatter 或文件名提取） |
| `type` | string | 固定值 `dis-dashboard` |
| `source` | wikilink | 指向源文件的 Obsidian wikilink |
| `created` | date | 生成日期，格式 `YYYY-MM-DD` |
| `total_chunks` | int | 成功处理的 chunk 总数 |
| `tags` | list | 固定包含 `dis-output` 和 `summary` |

---

## Chunk_NN_Summary.md 模板

```yaml
---
title: "Chunk {NN}: {chunk_title}"
type: dis-chunk
chunk_id: NN
dashboard: "[[Summary_Dashboard]]"
tags: [dis-output, chunk-summary]
---
```

**文件位置**: `{output_dir}/Chunk_NN_Summary.md`

**命名规则**: NN 为两位数，补零（01, 02, ..., 27）

**必填字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | `Chunk NN: ` + 原始章节标题 |
| `type` | string | 固定值 `dis-chunk` |
| `chunk_id` | int | 对应 manifest 中的 id |
| `dashboard` | wikilink | 指向本次运行的 Dashboard 文件 |
| `tags` | list | 固定包含 `dis-output` 和 `chunk-summary` |

---

## Chunk_NN_Source.md 模板

```yaml
---
chunk_id: NN
title: "{chunk_title}"
source_file: "{file_path}"
start_line: N
end_line: N
---
```

**文件位置**: `{output_dir}/chunks/Chunk_NN_Source.md`

**命名规则**: NN 为两位数，补零（01, 02, ..., 27）

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `chunk_id` | int | 对应 manifest 中的 id |
| `title` | string | 原始章节标题 |
| `source_file` | string | 源文档完整路径 |
| `start_line` | int | 该 chunk 在源文件中的起始行号 |
| `end_line` | int | 该 chunk 在源文件中的结束行号 |

**正文**：frontmatter 之后为对应源文档片段的原文内容。

**回链约定**：`Chunk_NN_Summary.md` 底部应包含 `*源片段: [[Chunk_NN_Source]]*` 以建立双向导航。

---

## 失败占位文件模板

当某个 chunk 两次重试均失败时，生成占位文件：

```markdown
---
title: "Chunk {NN}: {chunk_title} [处理失败]"
type: dis-chunk
chunk_id: NN
dashboard: "[[Summary_Dashboard]]"
status: failed
tags: [dis-output, chunk-summary, failed]
---

< {prev_nav} | [[Summary_Dashboard|仪表板]] | {next_nav} >

---

# Chunk {NN}: {chunk_title}

> ⚠️ **此章节处理失败**
>
> 原因: {error_message}
> 失败时间: {timestamp}
> 重试次数: 2

请手动分析源文档对应章节（行 {start_line} - {end_line}）。

---

{prev_nav_bottom} | [[Summary_Dashboard|仪表板]] | {next_nav_bottom}

*来源: [[{source_filename}]]*
```

---

## 输出目录命名规则

**默认规则**: 源文件同级目录下创建 `DIS-Outputs/YYYYMMDD_slug/`

**slug 生成规则**:
- 取源文件名（去扩展名）
- 去掉日期前缀（如 `2026-04-04_`）
- 将下划线替换为连字符
- 全小写
- 截取前 30 字符

**示例**:
```
源文件: Clippings/2026-04-04_yt_ai-coding.md
输出目录: Clippings/DIS-Outputs/20260404_yt-ai-coding/
```

**版本去重**:
- 若目录已存在，追加 `-v2`
- 若 `-v2` 也存在，追加 `-v3`，以此类推

---

## 完整产物清单

运行完成后，产物分为四类，按类型分层统计（Phase 4 Validator 按此口径验证，而非递归计数）：

| 类型 | 位置 | 数量 | 纳入 Validator 计数 |
|------|------|------|------|
| Dashboard | `{output_dir}/Summary_Dashboard.md` | 1 | ✅ 是 |
| Chunk Summary | `{output_dir}/Chunk_NN_Summary.md` | N（含失败占位） | ✅ 是 |
| Source Chunk | `{output_dir}/chunks/Chunk_NN_Source.md` | N | ✅ 是 |
| 运行日志 | `{output_dir}/run_log.md` | 1 | ❌ 否（Phase 4 收尾写入） |

**Validator 校验口径**（Phase 4 S4.1 使用）：
- 根目录：`Summary_Dashboard.md`（1）+ `Chunk_NN_Summary.md`（N）= N + 1 个
- `chunks/` 子目录：`Chunk_NN_Source.md`（N）= N 个
- `run_log.md` 不参与此步计数，由 Phase 4 末尾独立写入
