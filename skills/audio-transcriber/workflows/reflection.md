# Reflection Workflow

The `reflection` scenario uses a multi-step workflow where the API only does raw transcription, and Claude handles all post-processing.

## Step 1: 转录 — Gemini API 做高保真转录

```bash
python scripts/transcribe_audio_gemini.py "audio.m4a" --scenario reflection
```

输出: `{stem}_transcript.md` — 纯转录文本（无术语标注、无结构化、保留填充词和口语表达）

## Step 2: Purify + 术语匹配与发现 + 轻量分段 — Claude 后处理

Claude 读取 raw transcript 和 glossary，执行清洗、术语工作和轻量分段：

1. 读取 `prompts/glossary.md` 和 `{stem}_transcript.md`（raw transcript，不修改此文件）
2. 清洗：移除填充词（uh, um, 那个, 就是说）、规范中英空格 (pangu spacing)
3. 术语校正：按 glossary 标准形式替换（如 `Chart GPT → ChatGPT`）
4. 术语发现：识别 glossary 中未收录的新术语
   - **必须**: 过滤 glossary 已存在条目（不重复已知的人名/项目名/术语）
   - **必须**: 语义去重（同一术语只保留一条，合并变体写法）
   - **必须**: 输出格式为 `term -> 标准形式`，原始形式与标准形式分离
   - **禁止**: 不重复 glossary 中已收录的人名、项目名、组织名
5. 轻量分段：在自然 topic 切换处插入 `## [Topic Label]`（每 3-5 段落一个）
   - Topic heading 说明主题，不做摘要（如 `## Weekly Planning Review`，不要写 `## 本周讨论了三个问题`）
   - 优先在话题明确切换处分段
   - 不强制分段——如果一段连续讨论同一主题，可以合并为一个大段
6. 输出 `{stem}_transcript_clean.md` — 清洗 + 术语校正 + 轻量分段后的版本
7. 如有新术语，输出 `{stem}_new_terms.md`（格式见 `workflows/glossary-loop.md`）

参考格式见: `reference/transcript_clean_example.md`

**文件约定（双文件，保留审计基线）**：
- `{stem}_transcript.md` — raw transcript（API 原始输出，不可修改）
- `{stem}_transcript_clean.md` — Claude 后处理版本（供后续 pass 和人类阅读使用）
- `{stem}_new_terms.md` — 候选新术语（Claude 产出）

## Step 3: (可选) 生成结构化日记

**主路径（推荐）**: Claude 直接生成 journal

1. Claude 读取 `{stem}_transcript_clean.md`（Step 2 产出）和 `prompts/journal.md`
2. 按 `journal.md` 的 Workflow 指令，直接生成 `{stem}_journal.md`
3. 输出应包含：章首总评、按时段回顾、核心洞察阐述、Related Links

参考结构见: `reference/journal_example.md`（仅作风格和结构锚点参考，内容长度和深度应根据实际 transcript 调整，不要机械模仿示例的篇幅）

**备选路径（legacy）**: Python 脚本，仅在 Claude 不可用时使用

```bash
python scripts/transcribe_audio_gemini.py "{stem}_transcript_clean.md" --scenario journal
```

注意：journal 的输入是 `_clean.md`（已校正版本），不是 raw transcript。journal 场景要求 text-only 输入（.md/.txt），对音频文件使用会报错。

## Step 4: (可选) Glossary 回写

见 `workflows/glossary-loop.md`。
