# Article clipping execution checklist

Concise runbook distilled from successful article clipping sessions.

## When clipping ordinary HTML articles
- Resolve `LIFE_OS_ROOT` first and verify the vault contains both `AGENTS.md` and `00-09_System-Meta/`.
- Run `defuddle parse "$URL" --md` for the primary extraction.
- If the page is long, keep the raw output in a temp file and page through it instead of relying on truncated terminal output.
- If needed, run the web extractor as a fallback or cross-check, but always record the final `extraction_method` truthfully.

## Before writing
- Search the target library for the canonical URL first; then search title keywords and topic terms for near-duplicate notes.
- Prefer linking only high-confidence related notes; otherwise write `- 暂无高置信关联笔记`.
- Use stable routing under the existing library, never create a new Johnny Decimal entity.

## After writing
- Validate with `scripts/validate_clip.py /absolute/path/to/note.md`.
- Record the event with `scripts/record_clip_event.py /absolute/path/to/note.md --root "$LIFE_OS_ROOT"`.
- Preserve the raw extracted Markdown under `## 原始正文` and keep generated analysis additive.
