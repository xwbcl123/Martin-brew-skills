---
name: audio-transcriber
description: "Multi-scenario audio transcriber using Gemini API. Supports meeting minutes, daily reflection, and voice-note modes with glossary-based terminology enforcement and learning loop. When Claude needs to transcribe audio files (.m4a, .mp3, .wav) into structured Markdown."
license: CC BY 4.0
aspg:
  origin:
    vendor: custom
    imported_at: 2026-03-19
---

# Audio Transcriber (Multi-Scenario)

## Overview

Gemini API 做低成本 ASR（raw transcript），Claude agent 层做高价值后处理（清洗、术语、分段、结构化合成）。当前三个 ASR 场景统一采用 transcript-first 架构。

## Scenarios

| Scenario | Input | Step 1 (API) | Step 2-3 (Claude) | Final Output |
|----------|-------|-------------|-------------------|--------------|
| `reflection` | audio | Raw transcript | Clean + Terms -> Journal | `_journal.md` |
| `meeting` | audio | Raw transcript (speaker-attributed) | Clean + Terms -> MoM | `_mom.md` |
| `voice-note` | audio | Raw transcript | Clean + Terms -> Brief | `_brief.md` |
| `journal` | text (.md) | — | Structured daily journal | `_journal.md` |

## Quickstart

### 1. Activate venv

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2. Run transcription (Step 1)

```bash
python skills/audio-transcriber/scripts/transcribe_audio_gemini.py "audio.m4a" --scenario reflection
python skills/audio-transcriber/scripts/transcribe_audio_gemini.py "audio.m4a" --scenario meeting
python skills/audio-transcriber/scripts/transcribe_audio_gemini.py "audio.m4a" --scenario voice-note
```

### 3. Claude post-processing (Step 2 & 3)

按场景读取对应 workflow 文件继续执行后处理。

### Common Options

```bash
--output "path.md"       # Custom output path
--model gemini-3.1-flash # Override model
--glossary "path.md"     # Custom glossary
--dry-run                # Print prompt without API call
--timeout 900            # Custom timeout (default 600s)
--prompt "custom text"   # Override scenario prompt entirely
```

## Hard Contracts

- `{stem}_transcript.md` 是审计基线，**不可修改**
- `meeting` / `voice-note` / `reflection` 的 Step 1 都是 API-only ASR
- `_new_terms.md` **必须使用 ASCII `->`**，与 `--update-glossary` regex 兼容
- 结构化产物（MoM / Brief / Journal）由 Claude 在 Step 3 完成
- `journal` 是 text-input second pass，不直接处理音频

## Workflow Routing

| 场景 | Workflow 文件 |
|------|--------------|
| `reflection` | `skills/audio-transcriber/workflows/reflection.md` |
| `meeting` | `skills/audio-transcriber/workflows/meeting.md` |
| `voice-note` | `skills/audio-transcriber/workflows/voice-note.md` |
| Glossary 回写 | `skills/audio-transcriber/workflows/glossary-loop.md` |
| 架构说明 | `skills/audio-transcriber/workflows/architecture.md` |

## Trigger Patterns

- "transcribe audio", "transcribe recording"
- "generate MoM", "meeting minutes from audio"
- "转录", "音频转文字", "语音转录"
- "voice note to text", "语音笔记"
- `@audio-transcriber`

## File Structure

```text
skills/audio-transcriber/
├── SKILL.md
├── requirements.txt
├── scripts/
│   └── transcribe_audio_gemini.py
├── prompts/
│   ├── meeting.md
│   ├── meeting_minutes.md
│   ├── voice-note.md
│   ├── voice_note_brief.md
│   ├── reflection.md
│   ├── journal.md
│   └── glossary.md
├── workflows/
│   ├── reflection.md
│   ├── meeting.md
│   ├── voice-note.md
│   ├── glossary-loop.md
│   └── architecture.md
└── reference/
    ├── transcript_clean_example.md
    ├── journal_example.md
    ├── meeting_mom_example.md
    └── voice_note_brief_example.md
```

## Public Repo Note

这个公开仓库版本有意保留了两层保护：

- `prompts/glossary.md` 是 starter template，不是你的真实 glossary
- `reference/` 中的 examples 必须保持为 sanitized demo，而不是工作中的真实 transcript / journal / memo

如果你在私有工作区使用这个 skill，可以本地替换成自己的 glossary 和 examples，但不应把私有版本直接推回公开仓库。
