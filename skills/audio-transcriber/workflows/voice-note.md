# Voice-Note Workflow

The `voice-note` scenario uses the same transcript-first architecture as `reflection`.

## Step 1: 转录 — Gemini API 做高保真语音笔记转录

```bash
python scripts/transcribe_audio_gemini.py "audio.m4a" --scenario voice-note
```

输出: `{stem}_transcript.md` — 纯语音笔记转录文本（第一人称、保留填充词和口语表达）

## Step 2: Purify + 术语匹配与发现 + 轻量分段 — Claude 后处理

同 Reflection Step 2（见 `workflows/reflection.md`）。

1. 读取 `prompts/glossary.md` 和 `{stem}_transcript.md`
2. 清洗、术语校正、术语发现（规则同 Reflection Step 2）
3. 轻量分段（规则同 Reflection Step 2）
4. 输出 `{stem}_transcript_clean.md` + `{stem}_new_terms.md`

`_new_terms.md` 必须复用 Reflection Step 2 的格式契约（ASCII `->` 箭头，见 `workflows/glossary-loop.md`）。

## Step 3: 生成结构化 Brief

Claude 读取 `{stem}_transcript_clean.md` + `prompts/voice_note_brief.md`，生成结构化执行简报。

输出: `{stem}_brief.md`

参考结构见: `reference/voice_note_brief_example.md`

## Step 4: (可选) Glossary 回写

见 `workflows/glossary-loop.md`。
