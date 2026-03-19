---
name: ds-citations
description: Deep Research Citation Normalizer - Convert GPT/Gemini/OpenAI Deep Research citation artifacts to Markdown footnotes with validation and audit output.
aspg:
  origin:
    vendor: claude
    imported_at: 2026-03-06
---

# Deep Research Citation Normalizer

Convert mixed AI-generated citations into clean, readable Markdown footnotes.

This skill now supports:
- GPT Deep Research legacy citations
- Gemini Deep Research citations
- OpenAI Deep Research artifact tokens (`cite...`, `entity...`)

## When to Use This Skill

- Processing AI-generated reports with noisy citation artifacts
- Converting inline citations to `[^n]` for better readability
- Cleaning residual `cite` / `entity` markers
- Running validation for missing/orphan footnotes
- Batch processing many Markdown reports with consistent output

## Supported Input Formats

| Source | Inline Format | Reference Format |
|--------|---------------|------------------|
| **GPT Deep Research (legacy)** | `[[n]](URL)` or `[\[n\]](URL)` | Mixed section styles |
| **Gemini Deep Research** | ` n。` (space + number + punctuation) | `1. Title, 访问时间为..., [URL](URL)` |
| **OpenAI Deep Research (artifact)** | `[Source text] citeturn...` or bare `citeturn...` | Often missing/implicit |

## Target Format

```markdown
Inline: [^n]
Reference: [^n]: Title URL
```

For bare trace citations (no readable source text), output defaults to:

```markdown
[^n]: Source trace: turn1view0; turn2view1
```

## CLI Usage

### Basic Commands

```bash
# Convert a single file
python skills/ds-citations/scripts/format_ds_citations.py report.md

# Preview changes (no write)
python skills/ds-citations/scripts/format_ds_citations.py -n report.md

# Check format and integrity only
python skills/ds-citations/scripts/format_ds_citations.py -c report.md

# Process a directory
python skills/ds-citations/scripts/format_ds_citations.py ./deep-research/

# Recursive directory processing
python skills/ds-citations/scripts/format_ds_citations.py -r ./sources/
```

### Advanced Controls

```bash
# Keep trace metadata in notes where only trace exists (default)
python skills/ds-citations/scripts/format_ds_citations.py report.md --trace-mode keep

# Append trace metadata to bracketed source notes
python skills/ds-citations/scripts/format_ds_citations.py report.md --trace-mode append

# Remove trace-only details for cleaner output
python skills/ds-citations/scripts/format_ds_citations.py report.md --trace-mode drop

# Handle entity artifacts as footnotes instead of stripping
python skills/ds-citations/scripts/format_ds_citations.py report.md --entity-mode footnote

# Keep entity artifacts untouched
python skills/ds-citations/scripts/format_ds_citations.py report.md --entity-mode keep

# Customize heading and export structured JSON report
python skills/ds-citations/scripts/format_ds_citations.py ./reports -r --footnote-heading "References" --report-json ./reports/citation-report.json
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-n, --dry-run` | Preview changes without writing |
| `-c, --check` | Check format and citation integrity only |
| `-f, --force` | Force re-check already converted files |
| `-r, --recursive` | Process subdirectories recursively |
| `-v, --verbose` | Show detailed output and warnings |
| `--trace-mode keep\|drop\|append` | Control handling of OpenAI trace metadata |
| `--entity-mode strip\|keep\|footnote` | Control handling of `entity` artifacts |
| `--footnote-heading <text>` | Set heading used when appending footnotes |
| `--report-json <path>` | Write machine-readable processing report |
| `-h, --help` | Show help message |

## Quality Gates (Recommended)

After conversion, verify all of these:

- No `cite` tokens remain
- No `entity` tokens remain (unless `--entity-mode keep`)
- Exactly one logical footnote block added for new notes
- No footnote definitions (`[^n]:`) appear inside正文表格、列表或段落区
- No missing references (`[^n]` without definition)
- No orphan references (definition without inline use)
- Re-running conversion yields no further changes (idempotent)

Suggested check command:

```bash
python skills/ds-citations/scripts/format_ds_citations.py -c -r ./deep-research/
```

## Output Symbols

| Symbol | Meaning |
|--------|---------|
| `✓` | Processed / converted successfully |
| `◈` | Already converted |
| `⊘` | Skipped (unknown format or no change) |
| `✗` | Error |
| `⚠` | Validation warning |

## Workflow Example

### 1) Check First

```bash
python skills/ds-citations/scripts/format_ds_citations.py -c ./deep-research/
```

### 2) Preview Conversion

```bash
python skills/ds-citations/scripts/format_ds_citations.py -n ./deep-research/ -r --trace-mode keep --entity-mode strip
```

### 3) Convert

```bash
python skills/ds-citations/scripts/format_ds_citations.py ./deep-research/ -r --trace-mode keep --entity-mode strip --report-json ./deep-research/citation-report.json
```

### 4) Verify

```bash
python skills/ds-citations/scripts/format_ds_citations.py -c ./deep-research/ -r
```

## Safety and Backups

- UTF-8 read/write is used for all content operations
- Automatic timestamp backup before write (`.bak.YYYYMMDD-HHMMSS`)
- Dry-run mode for safe preview
- Check mode for validation without modification

## Troubleshooting

### "Unknown format - skipping"

The file may be:
- Not a Deep Research report
- Already manually normalized
- Using an unsupported citation pattern

### "Missing refs" warning

Inline `[^n]` citations do not all have matching definitions. This can happen if:
- Source content is incomplete
- A prior manual edit removed references
- Mixed conversion styles exist in one file

### Inline citations turned into footnote definitions inside the body

This was a known GPT legacy edge case when a document used many `---` separators before the trailing raw reference block.

Current behavior:
- GPT trailing reference conversion only targets the final raw reference block at the end of the document
- Inline citation counting excludes footnote definition lines such as `[^1]: ...`

If you suspect an old bad conversion:
- Compare with the auto backup `.bak.YYYYMMDD-HHMMSS`
- Restore from backup, then rerun the formatter with the latest script
- Check that tables/lists still contain inline `[^n]` markers rather than `[^n]:`

### Artifact tokens still present

If `entity` remains, check if `--entity-mode keep` was used.

If `cite` remains, inspect malformed markers and rerun with `-v`.

### Duplicate `## 参考文献` / `## Footnotes`

The script collapses consecutive duplicate headings. Non-consecutive legacy headings may still need manual cleanup.

## File Locations

| File | Location |
|------|----------|
| Main Script | `skills/ds-citations/scripts/format_ds_citations.py` |
| This Documentation | `skills/ds-citations/SKILL.md` |

## Version History

- **v3.1** (2026-03-15): Fixed GPT legacy conversion so trailing raw reference parsing no longer hijacks body content after early `---` separators; refined converted-inline detection to avoid counting footnote definitions as inline citations
- **v3.0** (2026-02-27): Added OpenAI artifact support (`cite`, `entity`), fixed GPT format detection for unescaped `[[n]](URL)`, added trace/entity modes, JSON reporting, timestamp backups, and stronger validation metadata
- **v2.0** (2026-01-12): Added check mode, force mode, citation counting, improved format detection
- **v1.0** (2026-01-12): Initial GPT/Gemini conversion support
