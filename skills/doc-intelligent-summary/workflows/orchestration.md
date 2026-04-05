# DIS 编排流程 (Phase 0-4)

> 主执行文件。收到 `/summary` 指令后，按此文件逐 Phase 执行。
> Claude 作为 Orchestrator，通过 Agent tool 派发子代理。

---

## Phase 0 — 输入验证与输出目录准备

### 0.1 解析参数

从用户指令中提取：
- `file_path`: 源文档路径（必填）
- `start_from`: 可选，正文起始标题（`--start-from "## Transcript"`）
- `output`: 可选，覆盖输出目录（`--output <path>`）

若用户指令包含 `--validate-only`，**立即跳转到附录：`--validate-only` 独立验证模式**，不执行 Phase 1-3。

### 0.2 验证源文件与计算 SHA256（尽力尝试）

使用 `Read` 工具读取源文件：
- 若文件不存在，**立即停止**，报错：`文件不存在: {file_path}`

**尝试计算源文件 SHA256**（带超时保护）：
```bash
# Windows（PowerShell）—— 建议加超时保护，避免网络盘卡死
(Get-FileHash "{file_path}" -Algorithm SHA256).Hash
```

> **执行规则**：
> - 若 hash 计算在合理时间内（约 10–15 秒）成功，保存为上下文变量 `{source_sha256}`，写入 `run_log.md`
> - 若 hash 计算**超时、挂起或失败**（网络盘、大文件等场景），则：
>   1. 将 `{source_sha256}` 设为 `SKIPPED`
>   2. 在 `run_log.md` 中写入 `source_sha256: "SKIPPED（计算超时或不可用）"`
>   3. **继续执行任务**，不中止
> - `--validate-only` 模式下若 SHA256 为 `SKIPPED`，跳过历史 hash 比对，记录 `⚠️ SHA256 不可用，跳过完整性校验`

### 0.3 确定输出目录

若用户未指定 `--output`：
1. 取源文件所在目录
2. 生成 slug（规则见 `reference/output-templates.md`）
3. 拼接: `{source_dir}/DIS-Outputs/{YYYYMMDD}_{slug}/`
4. 检查目录是否存在，若存在追加 `-v2`/`-v3`

若用户指定 `--output <path>`，直接使用该路径。

使用 `Bash` 工具创建目录：
```bash
mkdir -p "{output_dir}"
```

### 0.4 判断文档格式

读取正文内容（从正文起点开始），快速扫描：
- 含 `###` → Markdown with H3（主策略）
- 含 `##` 但无 `###` → Markdown with H2
- 无 H2/H3 → 纯文本 / 无标题 Markdown

---

## Phase 1 — 分片

### 1.1 确定正文起点

按 `workflows/chunking-strategy.md` §1 的规则确定正文起始位置。

### 1.2 执行分片

按 `workflows/chunking-strategy.md` §2-5 的策略切分文档，生成 chunk manifest。

**manifest 示例**:
```json
[
  {"id": 1, "title": "Introduction", "start_line": 45, "end_line": 112, "char_count": 6200, "status": "pending"},
  {"id": 2, "title": "Key Findings",  "start_line": 113, "end_line": 210, "char_count": 8100, "status": "pending"}
]
```

### 1.3 持久化 Source Chunk 文件

在报告分片结果之前，将每个 chunk 的原文片段写入独立文件：

1. 使用 `Bash` 工具创建子目录：
   ```bash
   mkdir -p "{output_dir}/chunks"
   ```
2. 为 manifest 中的每个 chunk，使用 `Write` 工具写入 `{output_dir}/chunks/Chunk_NN_Source.md`：

```markdown
---
chunk_id: {NN}
title: "{chunk_title}"
source_file: "{file_path}"
start_line: {start_line}
end_line: {end_line}
---

{chunk_text_原文片段}
```

> **模板约定（强制执行）**：
> - `chunk_id`、`title`、`source_file`、`start_line`、`end_line` 全部必填，**缺一不可**
> - `source_file` 必须写入**完整源文件路径**，不允许省略、留空或写 `N/A`
> - NN 为两位数补零（01, 02...），与 Summary 文件对应
> - 用途：Phase 2 子代理通过文件路径读取原文，避免 orchestrator 上下文中内联大块文本；同时作为可审计的原文存档

同时记录正文起始行（`body_start_line`）供 Phase 4 写入 `run_log.md` 使用：将 Phase 1.1 确定的正文起始行号存入上下文变量 `{body_start_line}`。

### 1.4 报告分片结果

向用户输出一行摘要：
```
✅ 分片完成：共 {N} 个 chunk，输出目录 {output_dir}
Source 文件已写入 {output_dir}/chunks/
```

若 chunk 数 > 20，额外提示预计并行批次数。

---

## Phase 2 — 并行子代理分析

### 2.1 子代理配置

- **类型**: `general-purpose`
- **人格注入**: `prompts/dis-analyst-persona.md` 内容 + `prompts/chunk-summary-instruction.md` 内容
- **变量替换**:
  - `{chunk_id}` → 当前 chunk 编号（两位数）
  - `{total_chunks}` → chunk 总数
  - `{chunk_title}` → 当前 chunk 标题
  - `{prev_title}` → 前一 chunk 标题（第一个 chunk 填「无」）
  - `{next_title}` → 后一 chunk 标题（最后一个 chunk 填「无」）
  - `{chunk_source_path}` → Source 文件路径：`{output_dir}/chunks/Chunk_{NN}_Source.md`（替代原 `{chunk_text}`，不再内联原文）
  - `{source_filename}` → 源文件名（不含路径，不含扩展名）
  - `{NN}` → 两位数 chunk 编号（01, 02...）
  - `{NN-1}` / `{NN+1}` → 前/后 chunk 编号（边界情况见下）

> **重要**：`{chunk_text}` 不再直接传入子代理 prompt。改为在 prompt 末尾指示子代理：
> ```
> 请使用 Read 工具读取以下文件，分析其中的文档内容：
> 文件路径：{chunk_source_path}
> ```

### 2.2 批量并行规则

- **每批并发数**: 4-6 个（推荐 5 个）
- **批次间隔**: 等待当前批次全部完成后，发下一批
- **发送方式**: 在单个消息中并发发出多个 Agent tool 调用

```
第 1 批: Chunk 01-05（并行）
第 2 批: Chunk 06-10（并行）
...
```

### 2.3 失败处理与状态机

**单 chunk 处理流程**:
1. 启动子代理，状态改为 `running`
2. 收到结果:
   - 非空且包含 `### 🌟 核心论点` → 状态改为 `succeeded`，写入文件
   - 空输出 / 异常 / 超时 → 记录错误，等待 3s，**重试一次**（最多重试 1 次）
3. 重试仍失败 → 状态改为 `failed`，生成失败占位文件（见 `reference/output-templates.md`）

**中止条件**: 
- 若 `failed` chunk 数 > 总数的 50%，**立即中止整个任务**
- 输出错误报告：`❌ 任务中止：超过 50% chunk 处理失败（{N}/{total} 失败）`

### 2.4 写入 Chunk 文件

每个成功的子代理返回完整 `Chunk_NN_Summary.md` 内容后：
- 使用 `Write` 工具写入 `{output_dir}/Chunk_NN_Summary.md`
- 状态更新为 `succeeded`

---

## Phase 3 — 组装 Dashboard

### 3.1 准备综合输入

收集所有 chunk 的处理结果：
- `succeeded` chunk: 读取其 `Chunk_NN_Summary.md` 文件内容
- `failed` chunk: 使用占位摘要 `[⚠️ 此章节处理失败]`

### 3.2 启动综合子代理

启动一个 `general-purpose` 子代理，prompt 使用 `prompts/dashboard-synthesis.md`，变量替换：
- `{source_title}` → 源文档标题（从 frontmatter 的 `title` 字段提取，或使用文件名）
- `{source_filename}` → 源文件名（不含路径和扩展名）
- `{YYYY-MM-DD}` → 今日日期
- `{total_chunks}` → 总 chunk 数
- `{N}` → 成功 chunk 数
- `{all_chunk_summaries}` → 所有 chunk 摘要内容（按顺序拼接，每个之间加分隔线）

### 3.3 写入 Dashboard

综合子代理返回完整 `Summary_Dashboard.md` 内容后：
- 使用 `Write` 工具写入 `{output_dir}/Summary_Dashboard.md`

---

## Phase 4 — 验证与报告

### 4.1 分层产物计数验证

按类型分层统计，不递归计数（`run_log.md` 在 Phase 4 末尾写入，不参与此步）：

```
根目录校验:
  预期 Dashboard  = 1 个（Summary_Dashboard.md）
  预期 Chunk Summary = {total_chunks} 个（Chunk_NN_Summary.md）
  实际根目录 .md 数 = 统计 {output_dir}/*.md（排除 run_log.md）

chunks/ 子目录校验:
  预期 Source Chunk = {total_chunks} 个（Chunk_NN_Source.md）
  实际 chunks/ .md 数 = 统计 {output_dir}/chunks/*.md
```

若数量不匹配，列出缺失文件名，继续执行后续校验（不因数量不符中止）。

### 4.2 源文件完整性验证

重新计算源文件 SHA256，与 Phase 0.2 记录的 `{source_sha256}` 变量比较：
- 一致 → `✅ 源文件未被修改`
- 不一致 → `⚠️ 警告：源文件 hash 变化，请检查`

### 4.3 全量 Chunk Validator（阻断式）

逐一读取每个 `{output_dir}/Chunk_NN_Summary.md`，执行以下两层检查：

#### 4.3.1 Frontmatter 必填字段检查

检查以下字段是否全部存在：`title`、`type`、`chunk_id`、`dashboard`、`tags`

**不通过时的行为**：
- 列出缺失字段
- **尝试自动修补**：使用 Edit 工具补写缺失字段，推断规则：
  - `title` → `"Chunk {NN}: {chunk_title}"`（从文件名和 manifest 推断）
  - `type` → 固定值 `dis-chunk`
  - `chunk_id` → 从文件名中的 NN 推断
  - `dashboard` → 固定值 `"[[Summary_Dashboard]]"`
  - `tags` → 固定值 `[dis-output, chunk-summary]`
- 修补后标记为 `auto-fixed`

#### 4.3.2 四维标题精确匹配检查

检查正文是否包含全部四个**精确字符串**（含 Emoji，注意 `###` 后有空格）：
- `### 🌟 核心论点`
- `### 📊 关键数据`
- `### 🧠 底层逻辑`
- `### 💬 关键故事与引言`

**不通过时的行为**：
- **不自动修改正文**（内容性错误，有损风险）
- 标记为 `needs-review`，记录具体缺失的标题字符串
- 继续验证其余文件

### 4.4 Dashboard Validator

读取 `{output_dir}/Summary_Dashboard.md`，检查 frontmatter 必填字段：
`title`、`type`、`source`、`created`、`total_chunks`

**不通过时的行为**（同 4.3.1 自动修补规则）：
- `type` → 固定值 `dis-dashboard`
- `source` → `"[[{source_filename}]]"`
- `created` → 今日日期 `YYYY-MM-DD`
- `total_chunks` → manifest 中 chunk 总数

### 4.5 Source Chunk frontmatter 完整性验证（硬阻断）

逐一读取每个 `{output_dir}/chunks/Chunk_NN_Source.md`，检查以下**全部五个字段**：
- `chunk_id`
- `title`
- `source_file`
- `start_line`
- `end_line`

**强制执行规则**：

1. **任一字段缺失即视为校验失败**
2. **自动补齐尝试**：若缺失值可由文件名、现有 frontmatter、manifest 上下文唯一推断，允许自动补写缺失字段，然后**重跑一次该文件的完整字段检查**
3. **自动补齐后仍不满足**：整次运行**立即标记为失败**，不输出"验证通过"
4. **`source_file` 特别规则**：该字段只能从当次运行的 `{file_path}` 推断，如上下文已清除则使用 `run_log.md` 中的 `source_file` 字段值作为推断来源

> **为何是硬阻断**：Source Chunk frontmatter 是审计链路的核心契约，缺少任何字段将破坏可追溯性与 --validate-only 的独立验证能力。

### 4.6 二次验证（仅在有 auto-fixed 时执行）

若 4.3.1、4.4 或 4.5 有自动修补操作，重新读取被修补的文件，再次执行 frontmatter 检查，确认修补生效。

### 4.7 输出验证结论

汇总所有 chunk 的验证状态，输出报告：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{验证通过时}
✅ Validator 通过

源文件:                   {file_path}
输出目录:                 {output_dir}
Chunk 数:                 {success_count}/{total_chunks} 成功
Dashboard:                ✅ 通过
Chunk frontmatter:        {passed}/{total_chunks} 通过（{auto_fixed} 个已自动修补）
四维标题:                 {passed}/{total_chunks} 通过（{needs_review} 个需人工复查）
Source Chunk 存在性:      {total_chunks}/{total_chunks} 存在
Source Chunk frontmatter: {src_passed}/{total_chunks} 通过（{src_auto_fixed} 个已自动修补）

{若有 needs-review}
⚠️ 以下 {N} 个 Chunk 四维标题不完整，需人工复查：
- Chunk_NN_Summary.md: 缺少 [具体标题字符串]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{Source Chunk frontmatter 硬阻断触发时}
❌ Validator 失败：Source Chunk frontmatter 不完整（硬阻断）
以下文件缺少必填字段：
- chunks/Chunk_NN_Source.md: 缺少 [source_file, start_line]（自动补齐失败）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{其他检查仍不通过时（含二次验证后）}
❌ Validator 未完全通过，请检查上方报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> **注意**：`needs-review` 条目不阻断流程，仅作警示。Source Chunk frontmatter 缺失是硬阻断。仅 frontmatter 自动修补失败时才输出 `❌`。Phase 2 的粗判（包含 `### 🌟 核心论点`）不作为最终契约，Phase 4 全量校验为最终 gate。

### 4.8 写入 run_log.md（Phase 4 收尾步骤）

在 Validator 输出验证结论**之后**，作为 Phase 4 的最后一步，将本次运行元数据写入 `{output_dir}/run_log.md`：

```markdown
---
type: dis-run-log
source_file: "{file_path}"
output_dir: "{output_dir}"
run_at: "YYYY-MM-DD HH:MM:SS"
source_sha256: "{sha256_hash}"
body_start_line: {body_start_line}
total_chunks: {total_chunks}
---

# DIS 运行日志

## 运行元数据

| 字段 | 值 |
|------|----|
| 源文件 | `{file_path}` |
| 输出目录 | `{output_dir}` |
| 运行时间 | {run_at} |
| 正文起始行 | {body_start_line} |
| 源文件 SHA256 | `{sha256_hash}` |

## Chunk 状态

| Chunk | 状态 |
|-------|------|
| Chunk 01 | {status_01} |
| Chunk 02 | {status_02} |
| ... | ... |

（按 manifest 终态填写：succeeded / failed）

## Validator 摘要

| 检查项 | 结果 |
|--------|------|
| 根目录产物计数 | {count_root_pass} |
| chunks/ 产物计数 | {count_chunks_pass} |
| Dashboard frontmatter | {dashboard_fm_pass} |
| Chunk frontmatter（自动修补数） | {chunk_fm_pass}（{auto_fixed} 个已修补） |
| 四维标题（需人工复查数） | {chunk_titles_pass}（{needs_review} 个待复查） |
| Source Chunk frontmatter 完整性 | {src_fm_pass}（{src_auto_fixed} 个已修补，缺失字段：{missing_fields_summary}） |
| 源文件完整性 | {sha256_pass} |
```

> **时序保证**：`run_log.md` 仅在 Validator 全部步骤执行完毕后写入，因此 Validator 摘要可以准确反映本次校验结果。
> `run_log.md` 不参与 Validator 的产物计数（见 §4.1）。
> **Source Chunk frontmatter 完整性** 必须作为独立行出现在 Validator 摘要表格中，不能与"存在性"合并。

---

## 附录：`--validate-only` 独立验证模式

> **触发**：用户指令包含 `--validate-only` 参数时，跳过 Phase 1-3，仅执行本节流程。

### V.1 参数解析

从用户指令中提取（两个参数均为必填）：
- `--output <existing-output-dir>`：已存在的 DIS 输出目录（必填）
- `--source <file-path>`：对应的原始源文件路径（必填）

若任一必填参数缺失，**立即停止**，报错：
```
❌ --validate-only 模式缺少必填参数
用法：/summary --validate-only --output <dir> --source <file>
```

### V.2 磁盘重建 manifest

**不依赖任何运行态内存变量**，通过磁盘文件重建 manifest：

1. 扫描 `{output_dir}/chunks/Chunk_NN_Source.md` 文件列表，确定 `total_chunks`
2. 扫描 `{output_dir}/Chunk_NN_Summary.md` 文件列表，与 Source 数量交叉核对
3. 对每个 Source Chunk，读取其 frontmatter（`chunk_id`、`title`、`start_line`、`end_line`）
4. 期望计数 = `chunks/` 目录下 `Chunk_NN_Source.md` 文件数量（主口径）

### V.3 计算源文件 SHA256

使用与 Phase 0.2 相同的命令计算 `{source}` 指向文件的 SHA256。

若目录中存在 `run_log.md`，读取其 `source_sha256` 字段，与当前计算结果比对：
- 一致 → `✅ 源文件 SHA256 与原始运行记录一致`
- 不一致 → `⚠️ 源文件 SHA256 不匹配（源文件已变更或路径不符）`
- `run_log.md` 不存在 → `⚠️ run_log.md 不存在，跳过历史 hash 比对`

### V.4 执行 Source Chunk frontmatter 完整性验证

与 Phase 4.5 相同的**硬阻断**规则，但采用磁盘数据：

逐一读取每个 `{output_dir}/chunks/Chunk_NN_Source.md`，检查全部五个字段：
`chunk_id`、`title`、`source_file`、`start_line`、`end_line`

**--validate-only 模式下的自动补齐限制**：
- 允许从文件名、现有 frontmatter、其他文件推断进行补齐
- 但 `source_file` 只能用 `--source` 参数提供的路径补齐
- 补齐后需重新验证，仍不满足则标记失败

### V.5 执行 Chunk Summary frontmatter 验证

与 Phase 4.3.1 相同规则，逐一检查 `Chunk_NN_Summary.md` 的必填字段。

### V.6 执行 Dashboard frontmatter 验证

与 Phase 4.4 相同规则，检查 `Summary_Dashboard.md` 必填字段。

### V.7 输出验证结论

输出格式与 Phase 4.7 相同，额外说明"本次为 --validate-only 独立验证模式"。

### V.8 写入 validation_log.md（不覆盖 run_log.md）

**重要**：`--validate-only` 模式**不修改**原有 `run_log.md`，另外写 `{output_dir}/validation_log.md`：

```markdown
---
type: dis-validation-log
output_dir: "{output_dir}"
source_file: "{source}"
validated_at: "YYYY-MM-DD HH:MM:SS"
result: "passed" | "failed"
---

# DIS 独立验证日志

验证时间：{validated_at}
验证模式：--validate-only（不重跑分片，仅校验现有产物）

## 验证结果

| 检查项 | 结果 |
|--------|------|
| Source Chunk 计数 | {N} 个 |
| Summary Chunk 计数 | {N} 个 |
| Source Chunk frontmatter 完整性 | {src_fm_result} |
| Summary Chunk frontmatter 完整性 | {sum_fm_result} |
| Dashboard frontmatter 完整性 | {dash_fm_result} |
| 源文件 SHA256 比对 | {sha256_result} |

{若有失败项}
## 失败详情

{列出不合规文件与缺失字段}
- chunks/Chunk_NN_Source.md: 缺少 [source_file]
```
