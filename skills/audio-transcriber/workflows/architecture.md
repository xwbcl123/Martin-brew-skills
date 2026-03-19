# Architecture Notes

## API vs Claude 职责边界

| 场景 | API (Gemini) 职责 | Claude 后处理 | 输出文件 |
|------|-------------------|---------------|----------|
| `reflection` | ASR + `[inaudible]` 标记 | purify + glossary + segmentation + journal (optional) | `_transcript.md` → `_transcript_clean.md` + `_new_terms.md` + `_journal.md` |
| `meeting` | ASR + speaker-faithful raw transcript | purify + glossary + segmentation + MoM synthesis | `_transcript.md` → `_transcript_clean.md` + `_new_terms.md` + `_mom.md` |
| `voice-note` | ASR + raw transcript | purify + glossary + segmentation + brief synthesis | `_transcript.md` → `_transcript_clean.md` + `_new_terms.md` + `_brief.md` |
| `journal` | —（输入为 `_transcript_clean.md`，非 ASR） | **Claude (主)** / Python (legacy 备选) | `_journal.md` |

## Design Rationale

所有三个 ASR 场景（reflection, meeting, voice-note）均将 API 职责收缩至纯转录：

- API (flash-lite) 在单次调用中承担 ASR + 清洗 + 结构化 + 术语发现导致输出膨胀和保真度下降
- Claude 的语义理解能力远强于 flash-lite，术语匹配/发现质量更高
- 保留 raw transcript 作为审计基线，Claude 后处理产出 clean 版本
- 统一架构降低维护成本，三场景共享 Step 2 流程

## System Requirements

- Python 3.9+
- `google-genai>=1.0.0` — activate the skill's venv first, then:
  `python -m pip install -r requirements.txt`
- `GEMINI_API_KEY` environment variable

### Default Model

默认模型为 `gemini-3.1-flash-lite-preview`。选择原因：
- 前一个稳定版 `gemini-2.0-flash-lite` 已被 Google 弃用
- 当前 preview 模型是经过实际测试的可用基线
- Preview 模型输出可能有波动，如遇问题可尝试 `--model gemini-3.1-flash`

## Breaking Changes (Phase 2)

- `meeting` 场景 Step 1 现在只生成 raw transcript（含 speaker attribution），不再直接输出 Executive Briefing / Action Table / Terminology Discovery
- `voice-note` 场景 Step 1 现在只生成 raw transcript，不再直接输出 Clean Verbatim / Executive Briefing / Terminology Discovery
- 结构化 MoM（会议纪要）已迁移到 Claude Step 3（`prompts/meeting_minutes.md`）
- 结构化 Brief（执行简报）已迁移到 Claude Step 3（`prompts/voice_note_brief.md`）
- `_new_terms.md` 不再由脚本自动从 API 输出中提取（meeting/voice-note），改由 Claude Step 2 产出
- 这是有意的架构升级（transcript-first），不是能力回退。Phase 1.5 在 reflection 场景验证了此架构的优越性。
