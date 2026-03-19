---
name: audio-transcriber
description: "Multi-scenario audio transcriber using Gemini API. Supports meeting minutes, daily reflection, and voice-note modes with glossary-based terminology enforcement and learning loop. When Claude needs to transcribe audio files (.m4a, .mp3, .wav) into structured Markdown."
license: Custom
aspg:
  origin:
    vendor: custom
    imported_at: 2026-03-19
---

# Audio Transcriber (Multi-Scenario)

## Overview

This skill leverages the Gemini API's native multi-modal capabilities to process audio files (e.g., .m4a, .mp3, .wav). It uploads the file via the Gemini File API, transcribes it with a scenario-specific prompt, enforces terminology via a glossary, and outputs structured Markdown.

## Scenarios

| Scenario | Input | Description | Output Structure |
|----------|-------|-------------|------------------|
| `meeting` | audio | Meeting minutes (MoM) | Executive Briefing → Agenda Audit → Discussion by Topic → Action Table |
| `reflection` | audio | Raw high-fidelity transcript (API only does ASR) | 连续段落，无结构化，Claude 后处理做清洗+术语 |
| `journal` | text (.md) | Structured daily journal (second pass) | 章首总评 → 按时段回顾 → 核心洞察 |
| `voice-note` | audio | General voice notes | Terminology Discovery → Clean Verbatim (by topic) → Executive Briefing |

## Usage

When the user asks to "transcribe audio", "generate MoM", "转录音频", or mentions `audio-transcriber`, follow these steps:

### 1. Activate Virtual Environment

```bash
# Linux/macOS
source .venv/bin/activate

# Or run directly with venv python
.venv/bin/python ...

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Or run directly on Windows
.venv\Scripts\python.exe ...
```

### 2. Execute Transcription

```bash
python skills/audio-transcriber/scripts/transcribe_audio_gemini.py "path/to/audio.m4a"
```

### Common Options

```bash
# Specify scenario (default: voice-note)
python scripts/transcribe_audio_gemini.py "audio.m4a" --scenario meeting

# Custom output path
python scripts/transcribe_audio_gemini.py "audio.m4a" --output "output/meeting_notes.md"

# Override model
python scripts/transcribe_audio_gemini.py "audio.m4a" --model gemini-3.1-flash

# Custom glossary
python scripts/transcribe_audio_gemini.py "audio.m4a" --glossary "/path/to/glossary.md"

# Dry-run: print final prompt without calling API
python scripts/transcribe_audio_gemini.py "audio.m4a" --dry-run

# Set timeout (default 600s)
python scripts/transcribe_audio_gemini.py "audio.m4a" --timeout 900

# Fully custom prompt (overrides scenario)
python scripts/transcribe_audio_gemini.py "audio.m4a" --prompt "Your custom instructions here"
```

### 3. Review Output

The script generates:
- `{input_stem}_transcript.md` — main transcript/summary
- `{input_stem}_new_terms.md` — candidate new terms for glossary (if any `[❓ New]` terms detected; meeting/voice-note only)

---

## Reflection Workflow (完整流程)

The `reflection` scenario uses a multi-step workflow where the API only does raw transcription, and Claude handles all post-processing.

### Step 1: 转录 — Gemini API 做高保真转录

```bash
python scripts/transcribe_audio_gemini.py "audio.m4a" --scenario reflection
```

输出: `{stem}_transcript.md` — 纯转录文本（无术语标注、无结构化、保留填充词和口语表达）

### Step 2: Purify + 术语匹配与发现 + 轻量分段 — Claude 后处理

Claude 读取 raw transcript 和 glossary，执行清洗、术语工作和轻量分段：

1. 读取 `prompts/glossary.md` 和 `{stem}_transcript.md`（raw transcript，不修改此文件）
2. 清洗：移除填充词（uh, um, 那个, 就是说）、规范中英空格 (pangu spacing)
3. 术语校正：按 glossary 标准形式替换（如 `Chart GPT → ChatGPT`）
4. 术语发现：识别 glossary 中未收录的新术语
   - **必须**: 过滤 glossary 已存在条目（不重复已知的人名/项目名/术语）
   - **必须**: 语义去重（同一术语只保留一条，合并变体写法）
   - **必须**: 输出格式为 `term → 标准形式`，原始形式与标准形式分离
   - **禁止**: 不重复 glossary 中已收录的人名、项目名、组织名
5. 轻量分段：在自然 topic 切换处插入 `## [Topic Label]`（每 3-5 段落一个）
   - Topic heading 说明主题，不做摘要（如 `## CSPD Agent 学习例会`，不要写 `## CSPD 例会讨论了三个问题`）
   - 优先在话题明确切换处分段
   - 不强制分段——如果一段连续讨论同一主题，可以合并为一个大段
6. 输出 `{stem}_transcript_clean.md` — 清洗 + 术语校正 + 轻量分段后的版本
7. 如有新术语，输出 `{stem}_new_terms.md`（与现有 sidecar 格式一致）

参考格式见: `skills/audio-transcriber/reference/transcript_clean_example.md`

**文件约定（双文件，保留审计基线）**：
- `{stem}_transcript.md` — raw transcript（API 原始输出，不可修改）
- `{stem}_transcript_clean.md` — Claude 后处理版本（供 journal pass 和人类阅读使用）
- `{stem}_new_terms.md` — 候选新术语（Claude 产出）

### Step 3: (可选) 生成结构化日记

**主路径（推荐）**: Claude 直接生成 journal

1. Claude 读取 `{stem}_transcript_clean.md`（Step 2 产出）和 `prompts/journal.txt`
2. 按 `journal.txt` 的 Workflow 指令，直接生成 `{stem}_journal.md`
3. 输出应包含：章首总评、按时段回顾、核心洞察阐述、Related Links

参考结构见: `skills/audio-transcriber/reference/journal_example.md`（仅作风格和结构锚点参考，内容长度和深度应根据实际 transcript 调整，不要机械模仿示例的篇幅）

**备选路径（legacy）**: Python 脚本，仅在 Claude 不可用时使用

```bash
python scripts/transcribe_audio_gemini.py "{stem}_transcript_clean.md" --scenario journal
```

注意：journal 的输入是 `_clean.md`（已校正版本），不是 raw transcript。journal 场景要求 text-only 输入（.md/.txt），对音频文件使用会报错。

### Step 4: (可选) Glossary 回写

用户在 Obsidian 中勾选确认 `_new_terms.md` 中的术语后：

```bash
# Preview
python scripts/transcribe_audio_gemini.py --update-glossary "{stem}_new_terms.md"

# Write
python scripts/transcribe_audio_gemini.py --update-glossary "{stem}_new_terms.md" --apply
```

---

## Glossary Learning Loop

The skill includes a closed-loop terminology learning system:

### How It Works

1. **During transcription** (meeting/voice-note): Gemini outputs a `🧠 Terminology Discovery` section with:
   - `[✅ Applied]` — glossary terms that were enforced
   - `[❓ New]` — new terms discovered (candidates)

2. **During reflection workflow**: Claude handles terminology discovery in Step 2 (post-processing).

3. **After transcription**: New terms are extracted into `{input_stem}_new_terms.md` as a checklist.

4. **User review**: Check confirmed terms with `[x]` in Obsidian.

5. **Write back to glossary**:

```bash
# Step 1: Preview what will be written (safe, no changes)
python scripts/transcribe_audio_gemini.py --update-glossary path/to/_new_terms.md

# Step 2: Confirm and write
python scripts/transcribe_audio_gemini.py --update-glossary path/to/_new_terms.md --apply
```

### Glossary Maintenance

- The glossary lives at `prompts/glossary.md` (relative to skill root)
- The published repository only includes a starter template. Replace it locally with your own private glossary.
- Auto-discovered terms are appended to `## 📝 新增术语 (Auto-discovered)` section
- Duplicate terms are automatically skipped
- **Best practice**: Periodically review the `📝 新增术语` section for accuracy and re-categorize terms into the main glossary sections as needed

## System Requirements

- Python 3.9+
- `google-genai>=1.0.0` — activate the skill's venv first (see Step 1), then:
  `python -m pip install -r requirements.txt`
- `GEMINI_API_KEY` environment variable
- optional local `.env` file for private development

### Default Model

默认模型为 `gemini-3.1-flash-lite-preview`。选择原因：
- 前一个稳定版 `gemini-2.0-flash-lite` 已被 Google 弃用
- 当前 preview 模型是经过实际测试的可用基线
- Preview 模型输出可能有波动，如遇问题可尝试 `--model gemini-3.1-flash`

## Architecture Notes

### API vs Claude 职责边界

| 场景 | API (Gemini) 职责 | Claude 后处理 | 输出文件 |
|------|-------------------|---------------|----------|
| `reflection` | ASR + `[inaudible]` 标记 | purify (填充词/pangu) + 术语校正 + 术语发现 | `_transcript.md` (raw) → `_transcript_clean.md` + `_new_terms.md` (Claude) |
| `meeting` | ASR + Purify + Terminology Discovery + 结构化输出 | — | `_transcript.md` + `_new_terms.md` (脚本提取) |
| `voice-note` | ASR + Purify + Terminology Discovery + 结构化输出 | — | `_transcript.md` + `_new_terms.md` (脚本提取) |
| `journal` | —（输入为 `_transcript_clean.md`，非 ASR） | **Claude (主)** / Python (legacy 备选) | `_journal.md` |

### Design Rationale

`reflection` 场景将 API 职责收缩至纯转录，原因：
- API (flash-lite) 在单次调用中承担 ASR + 清洗 + 结构化 + 术语发现导致输出膨胀和保真度下降
- Claude 的语义理解能力远强于 flash-lite，术语匹配/发现质量更高
- 保留 raw transcript 作为审计基线，Claude 后处理产出 clean 版本
- `meeting` 和 `voice-note` 保留现有架构，待 reflection workflow 验证后可复用同一模式 (Phase 2/3)

## Trigger Patterns

- "transcribe audio", "transcribe recording"
- "generate MoM", "meeting minutes from audio"
- "转录", "音频转文字", "语音转录"
- "voice note to text", "语音笔记"
- `@audio-transcriber`

## File Structure

```
skills/audio-transcriber/
├── SKILL.md                 # This file
├── requirements.txt         # Python dependencies
├── scripts/
│   └── transcribe_audio_gemini.py
├── prompts/
│   ├── meeting.txt          # Meeting minutes prompt
│   ├── reflection.txt       # Raw transcript prompt (pass 1, ASR only)
│   ├── journal.txt          # Structured daily journal prompt (pass 2, text input)
│   ├── voice-note.txt       # Voice note prompt
│   └── glossary.md          # Terminology glossary
└── reference/
    ├── transcript_clean_example.md  # Few-shot: clean transcript with H2 topic headings
    └── journal_example.md           # Few-shot: structured journal output
```

## Privacy Note

The public repository version of this skill intentionally ships with:

- a starter `glossary.md` template instead of a real working glossary
- sanitized reference examples instead of real transcripts or journals

Replace those files locally in your own private workspace if you need domain-specific terminology.
