#!/usr/bin/env python3
"""Audio transcriber using Gemini API with multi-scenario support and glossary enforcement.

Scenarios:
  - meeting:    Raw meeting transcript (API-only ASR; structured MoM moved to Claude)
  - reflection: Raw high-fidelity transcript (API-only ASR; no cleaning or structure)
  - journal:    Structured daily journal (second pass, takes transcript text as input)
  - voice-note: Raw voice-note transcript (API-only ASR; briefing moved to Claude)

Supports both audio files (uploaded via File API) and text files (.md/.txt — read
directly, no upload). All ASR scenarios produce raw transcripts only; structured
synthesis (MoM, brief, journal) is handled by Claude in subsequent passes.

Two-pass example (reflection → journal):
  Pass 1: audio → raw transcript (API-only ASR)
  Pass 2: transcript_clean.md → structured journal (Claude or this script)

Usage:
  # Basic transcription (default: voice-note scenario)
  python transcribe_audio_gemini.py "path/to/audio.m4a"

  # Daily reflection: two-pass workflow
  python transcribe_audio_gemini.py "audio.m4a" --scenario reflection
  python transcribe_audio_gemini.py "audio_transcript.md" --scenario journal

  # Dry-run (print prompt, no API call)
  python transcribe_audio_gemini.py "audio.m4a" --dry-run

  # Glossary update (preview)
  python transcribe_audio_gemini.py --update-glossary "path/to/_new_terms.md"

  # Glossary update (write)
  python transcribe_audio_gemini.py --update-glossary "path/to/_new_terms.md" --apply
"""

import argparse
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROMPTS_DIR = SKILL_DIR / "prompts"
DEFAULT_GLOSSARY = PROMPTS_DIR / "glossary.md"
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_TIMEOUT = 600
DEFAULT_SCENARIO = "voice-note"

AUTO_SECTION_HEADER = "## 📝 新增术语 (Auto-discovered)"
TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}
RAW_TRANSCRIPT_SCENARIOS = {"reflection", "meeting", "voice-note"}


def build_prompt(scenario: str, custom_prompt: str | None, glossary_path: str | None,
                  use_glossary: bool = True) -> str:
    """Build the final prompt from scenario template + glossary.

    Args:
        use_glossary: If False, skip glossary injection entirely (e.g. reflection scenario).
    """
    # Determine base prompt
    if custom_prompt:
        base_prompt = custom_prompt
    else:
        # .md-first, .txt-fallback
        template_md = PROMPTS_DIR / f"{scenario}.md"
        template_txt = PROMPTS_DIR / f"{scenario}.txt"
        if template_md.exists():
            template_file = template_md
        elif template_txt.exists():
            template_file = template_txt
        else:
            available = sorted({f.stem for f in PROMPTS_DIR.glob("*.md")} |
                               {f.stem for f in PROMPTS_DIR.glob("*.txt")})
            print(f"Error: Scenario template '{scenario}' not found.")
            print(f"Available scenarios: {', '.join(available) if available else '(none)'}")
            sys.exit(1)
        base_prompt = template_file.read_text(encoding="utf-8")

    # Skip glossary for scenarios that don't need it (e.g. reflection = pure ASR)
    if not use_glossary:
        print("Glossary injection skipped (scenario does not use glossary).")
        return base_prompt

    # Append glossary if available
    glossary_content = ""
    gpath = Path(glossary_path) if glossary_path else DEFAULT_GLOSSARY
    if gpath.exists():
        glossary_content = gpath.read_text(encoding="utf-8")
        print(f"Glossary loaded: {gpath} ({len(glossary_content)} chars)")
    else:
        print(f"Warning: Glossary not found at {gpath}, proceeding without terminology enforcement.")

    if glossary_content:
        final_prompt = (
            f"{base_prompt}\n\n"
            f"---\n"
            f"## 术语库 (Glossary)\n"
            f"请严格按以下术语库进行术语校正和标准化：\n"
            f"{glossary_content}"
        )
    else:
        final_prompt = base_prompt

    return final_prompt


def dedup_terminology_section(text: str) -> str:
    """Deduplicate repeated [✅ Applied] and [❓ New] lines in Terminology Discovery section."""
    lines = text.split("\n")
    result = []
    seen_terms = set()
    in_terminology = False

    for line in lines:
        # Detect terminology section boundaries
        if "Terminology Discovery" in line:
            in_terminology = True
        elif in_terminology and line.startswith("---"):
            in_terminology = False

        # Dedup within terminology section
        if in_terminology and re.match(r"\s*-\s*\[(✅|❓)", line):
            normalized = line.strip()
            if normalized in seen_terms:
                continue
            seen_terms.add(normalized)

        result.append(line)

    return "\n".join(result)


def extract_glossary_terms(glossary_text: str) -> set[str]:
    """Parse glossary lines and extract normalized canonical terms.

    Rules (applied in order):
      1. Backtick content takes priority: ``term`` → 'term'
      2. Split on ALL separators (/ = （ ( : —), collect every segment
      3. Normalize: strip, lower()

    Both misspelling variants (left side) AND canonical forms (right side)
    are collected so that filtering works regardless of which form appears.
    """
    SEPARATORS = re.compile(r"[/=（(:—]")
    terms: set[str] = set()
    for line in glossary_text.splitlines():
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        # Remove leading '- '
        entry = line.lstrip("-").strip()

        # Strategy 1: backtick content
        backtick_match = re.findall(r"`([^`]+)`", entry)
        if backtick_match:
            for bt in backtick_match:
                terms.add(bt.strip().lower())
            continue

        # Strategy 2: split on ALL separators, collect every segment
        parts = SEPARATORS.split(entry)
        for part in parts:
            canonical = part.strip().lower()
            if canonical:
                terms.add(canonical)

    return terms


def extract_new_terms(transcript_text: str, source_file: str,
                      glossary_path: str | None = None) -> str | None:
    """Extract [❓ New] terms from transcript output into a sidecar checklist.

    Applies dedup and glossary filtering:
      - Removes terms already present in glossary (by canonical form)
      - Deduplicates by normalized canonical form (seen_forms)
    """
    pattern = r"\[❓\s*New\]\s*(.+)"
    matches = re.findall(pattern, transcript_text)
    if not matches:
        return None

    # Load known terms from glossary for filtering (fall back to default glossary)
    known_terms: set[str] = set()
    gpath = Path(glossary_path) if glossary_path else DEFAULT_GLOSSARY
    if gpath.exists():
        known_terms = extract_glossary_terms(gpath.read_text(encoding="utf-8"))

    # Extract canonical form from each match for dedup/filtering
    # Pattern: `raw` -> `standard` (context)  OR  raw -> standard  OR  plain text
    ARROW_RE = re.compile(r"(?:`([^`]+)`|(\S+))\s*->\s*(?:\*\*([^*]+)\*\*|`([^`]+)`|(\S+))")
    SEPARATORS = re.compile(r"[/=（(:—]")

    today = date.today().isoformat()
    lines = [
        "# 候选新术语 (待确认)",
        f"> 来源: {source_file}",
        f"> 日期: {today}",
        "",
    ]
    seen_forms: set[str] = set()

    for match in matches:
        raw = match.strip()

        # Derive canonical form for dedup
        arrow = ARROW_RE.search(raw)
        if arrow:
            # Prefer the standard/target side (groups 3/4/5)
            canonical = (arrow.group(3) or arrow.group(4) or arrow.group(5) or "").strip().lower()
        else:
            # Fallback: split on separators, take leftmost
            parts = SEPARATORS.split(raw, maxsplit=1)
            canonical = parts[0].strip(" `*").lower()

        if not canonical:
            continue

        # Filter: skip if already in glossary
        if canonical in known_terms:
            continue

        # Dedup: skip if we've already seen this canonical form
        if canonical in seen_forms:
            continue
        seen_forms.add(canonical)

        lines.append(f"- [ ] {raw}")

    # If all matches were filtered out, return None
    if len(lines) <= 4:  # only header lines
        return None

    return "\n".join(lines) + "\n"


def is_text_file(file_path: str) -> bool:
    """Check if the input is a text file (for second-pass processing)."""
    return Path(file_path).suffix.lower() in TEXT_EXTENSIONS


def do_transcribe(args: argparse.Namespace) -> None:
    """Main transcription workflow. Supports both audio and text file input."""
    file_path = args.file_path
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    text_mode = is_text_file(file_path)

    # Enforce text-only input for journal scenario
    if args.scenario == "journal" and not text_mode:
        print("Error: --scenario journal requires text input (.md/.txt).")
        print("Journal is a second-pass scenario. First run --scenario reflection on your audio file,")
        print("then run --scenario journal on the generated transcript.")
        sys.exit(1)

    # Build prompt (reflection scenario skips glossary — API does pure ASR only)
    final_prompt = build_prompt(args.scenario, args.prompt, args.glossary,
                                use_glossary=(args.scenario not in RAW_TRANSCRIPT_SCENARIOS))

    # Dry-run mode — no API key or SDK needed
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — Final prompt that would be sent to Gemini:")
        print("=" * 60)
        try:
            print(final_prompt)
        except UnicodeEncodeError:
            # Windows GBK/cp936 console cannot render emoji/special chars in glossary
            print(final_prompt.encode(sys.stdout.encoding or "utf-8",
                                      errors="replace").decode(
                                          sys.stdout.encoding or "utf-8",
                                          errors="replace"))
            print("(Note: some characters replaced due to console encoding limitations)")
        print("=" * 60)
        print(f"Model: {args.model}")
        print(f"Input: {file_path} ({'text mode' if text_mode else 'audio mode'})")
        print(f"Output: {args.output or Path(file_path).stem + '_transcript.md'}")
        return

    # Lazy import — fail fast with clear message if not installed
    try:
        from google import genai
    except ImportError:
        print("Error: google-genai package not installed.")
        print("Activate the skill's virtual environment first:")
        print("  Linux/macOS:  source .venv/bin/activate")
        print("  Windows:      .venv\\Scripts\\Activate.ps1")
        print("Then install:   python -m pip install -r requirements.txt")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    # Initialize client
    client = genai.Client()
    model = args.model
    uploaded_file = None

    if text_mode:
        # Text mode: read file content, send as text (no upload)
        input_text = Path(file_path).read_text(encoding="utf-8")
        print(f"Text input loaded: {file_path} ({len(input_text)} chars)")
        contents = [final_prompt + "\n\n---\n## 输入文本\n\n" + input_text]
    else:
        # Audio mode: upload via File API
        print(f"Uploading file: {file_path} ...")
        try:
            uploaded_file = client.files.upload(file=file_path)
            print(f"File uploaded. URI: {uploaded_file.uri}")
        except Exception as e:
            print(f"Failed to upload file: {e}")
            print(f"模型 '{model}' 调用失败: {e}。尝试 --model gemini-3.1-flash 或检查 https://ai.google.dev/models")
            sys.exit(1)

        # Wait for processing with timeout
        print("Waiting for file processing...")
        start_time = time.time()
        timeout = args.timeout

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"\nError: File processing timed out after {timeout}s.")
                print("Try increasing --timeout or check file size/format.")
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass
                sys.exit(1)

            file_info = client.files.get(name=uploaded_file.name)
            state_name = file_info.state.name if hasattr(file_info.state, 'name') else str(file_info.state)

            if state_name == "ACTIVE":
                print("\nFile processing complete.")
                break
            elif state_name == "FAILED":
                print("\nError: File processing failed.")
                sys.exit(1)

            time.sleep(5)
            print(".", end="", flush=True)

        contents = [uploaded_file, final_prompt]

    # Generate content
    mode_label = "text processing" if text_mode else "transcription"
    print(f"Requesting {mode_label} from {model} (scenario: {args.scenario})...")
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
        )

        if not response.text:
            print("Error: Empty response from model.")
            print("Try a different model with --model gemini-3.1-flash")
            sys.exit(1)

        # Deduplicate terminology section (for scenarios that include it)
        output_text = dedup_terminology_section(response.text)

        # Determine output path
        default_suffix = "_journal.md" if args.scenario == "journal" else "_transcript.md"
        output_file = args.output or f"{os.path.splitext(file_path)[0]}{default_suffix}"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"\nOutput saved to: {output_file}")

        # Extract new terms sidecar (skip for raw-transcript scenarios and journal)
        if args.scenario not in RAW_TRANSCRIPT_SCENARIOS and args.scenario != "journal":
            new_terms_content = extract_new_terms(output_text, os.path.basename(file_path),
                                                     glossary_path=args.glossary)
            if new_terms_content:
                terms_file = f"{os.path.splitext(file_path)[0]}_new_terms.md"
                with open(terms_file, "w", encoding="utf-8") as f:
                    f.write(new_terms_content)
                print(f"New terms candidates saved to: {terms_file}")
            else:
                print("No new term candidates detected in output.")

    except Exception as e:
        print(f"模型 '{model}' 调用失败: {e}。尝试 --model gemini-3.1-flash 或检查 https://ai.google.dev/models")
        sys.exit(1)
    finally:
        # Cleanup uploaded file (only for audio mode)
        if uploaded_file:
            print("Cleaning up uploaded file...")
            try:
                client.files.delete(name=uploaded_file.name)
                print("Cleanup successful.")
            except Exception as e:
                print(f"Warning: Failed to delete uploaded file: {e}")


def do_update_glossary(args: argparse.Namespace) -> None:
    """Read confirmed terms from _new_terms.md and write back to glossary."""
    terms_path = Path(args.update_glossary)
    if not terms_path.exists():
        print(f"Error: Terms file not found at {terms_path}")
        sys.exit(1)

    glossary_path = Path(args.glossary) if args.glossary else DEFAULT_GLOSSARY
    if not glossary_path.exists():
        print(f"Error: Glossary file not found at {glossary_path}")
        sys.exit(1)

    # Parse confirmed terms (checked boxes)
    terms_content = terms_path.read_text(encoding="utf-8")
    confirmed_pattern = r"- \[x\]\s*(.+)"
    confirmed = re.findall(confirmed_pattern, terms_content, re.IGNORECASE)

    if not confirmed:
        print("没有已确认的新术语 (no checked [x] items found).")
        sys.exit(0)

    # Read existing glossary for dedup
    glossary_content = glossary_path.read_text(encoding="utf-8")

    # Filter duplicates
    new_entries = []
    for term in confirmed:
        # Extract the raw term for dedup (before the ->)
        term_clean = term.strip()
        # Check if term text already exists in glossary (fuzzy: check the suggested form)
        arrow_match = re.search(r"->\s*`?([^`\(]+)`?", term_clean)
        check_text = arrow_match.group(1).strip() if arrow_match else term_clean

        if check_text.lower() in glossary_content.lower():
            print(f"  [SKIP] Already exists: {term_clean}")
        else:
            new_entries.append(term_clean)

    if not new_entries:
        print("所有确认的术语已存在于 glossary 中，无需更新。")
        sys.exit(0)

    # Build the new section content
    new_lines = []
    for entry in new_entries:
        # Clean up: remove backticks and context parentheses for glossary format
        # Transform: `raw` -> `standard` (context) => raw = standard
        cleaned = re.sub(r"`([^`]+)`\s*->\s*`([^`]+)`(?:\s*\(.*?\))?", r"\1 = \2", entry)
        if cleaned == entry:
            # No transformation matched, use as-is
            new_lines.append(f"- {entry}")
        else:
            new_lines.append(f"- {cleaned}")

    # Show diff preview
    print(f"\n{'=' * 50}")
    print(f"将向 {glossary_path} 追加以下术语:")
    print(f"{'=' * 50}")
    for line in new_lines:
        print(f"  + {line}")
    print(f"{'=' * 50}")
    print(f"共 {len(new_entries)} 条新术语")

    if not args.apply:
        print(f"\n这是预览模式。添加 --apply 以确认写入。")
        sys.exit(0)

    # Write to glossary
    # Check if auto-discovered section already exists
    if AUTO_SECTION_HEADER in glossary_content:
        # Append to existing section
        updated = glossary_content.rstrip() + "\n" + "\n".join(new_lines) + "\n"
    else:
        # Create new section at the end
        updated = (
            glossary_content.rstrip() + "\n\n"
            + AUTO_SECTION_HEADER + "\n\n"
            + "\n".join(new_lines) + "\n"
        )

    glossary_path.write_text(updated, encoding="utf-8")
    print(f"\n已写入 {len(new_entries)} 条术语到 {glossary_path}")
    print("建议定期审查 '📝 新增术语' section 的准确性，并将确认的术语重新分类到主要分类中。")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using Gemini API with multi-scenario support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe with default voice-note scenario
  %(prog)s audio.m4a

  # Raw meeting transcript (Step 1 only; MoM via Claude Step 3)
  %(prog)s audio.m4a --scenario meeting

  # Dry-run to preview prompt
  %(prog)s audio.m4a --dry-run

  # Update glossary from confirmed terms
  %(prog)s --update-glossary audio_new_terms.md
  %(prog)s --update-glossary audio_new_terms.md --apply
""",
    )

    # Positional argument (optional when using --update-glossary)
    parser.add_argument(
        "file_path",
        nargs="?",
        default=None,
        help="Path to audio (.m4a, .mp3, .wav) or text (.md, .txt) file",
    )

    # Transcription options
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO,
        help=f"Scenario: meeting, reflection, voice-note, journal (default: {DEFAULT_SCENARIO})",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Custom prompt text (overrides --scenario)",
    )
    parser.add_argument(
        "--glossary",
        default=None,
        help=f"Path to glossary file (default: {DEFAULT_GLOSSARY})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: {{input_stem}}_transcript.md)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"File processing timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print final prompt without calling API",
    )

    # Glossary update mode
    parser.add_argument(
        "--update-glossary",
        metavar="TERMS_FILE",
        default=None,
        help="Path to _new_terms.md file for glossary update (mutually exclusive with transcription)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirm glossary write (use with --update-glossary)",
    )

    args = parser.parse_args()

    # Route to correct mode
    if args.update_glossary:
        do_update_glossary(args)
    elif args.file_path:
        do_transcribe(args)
    else:
        parser.print_help()
        print("\nError: Either provide an audio file path or use --update-glossary.")
        sys.exit(1)


if __name__ == "__main__":
    main()
