from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    slug: str
    speaker: str
    title: str
    start: int
    end: int


def parse_time(value: str | int | float) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    parts = [int(part) for part in str(value).strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Unsupported time value: {value}")


def fmt_time(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def load_segments(path: Path) -> list[Segment]:
    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
    else:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    return [
        Segment(
            slug=row["slug"].strip(),
            speaker=row.get("speaker", "").strip(),
            title=row.get("title", "").strip(),
            start=parse_time(row["start"]),
            end=parse_time(row["end"]),
        )
        for row in rows
    ]


def transcript_entries(path: Path, heading: str | None) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    if heading and heading in text:
        text = text.split(heading, 1)[1]
    entries: list[tuple[int, str]] = []
    current_sec: int | None = None
    current: list[str] = []
    pattern = re.compile(r"^\s*(?:[-*]\s*)?\*\*(\d{1,2}:\d{2}(?::\d{2})?)\*\*")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            if current_sec is not None:
                entries.append((current_sec, "\n".join(current).rstrip()))
            current_sec = parse_time(match.group(1))
            current = [line]
        elif current_sec is not None:
            current.append(line)
    if current_sec is not None:
        entries.append((current_sec, "\n".join(current).rstrip()))
    return entries


def frontmatter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_transcript(segment: Segment, entries: list[tuple[int, str]], output_dir: Path, event_prefix: str, source_url: str) -> tuple[Path, int]:
    selected = [entry for sec, entry in entries if segment.start <= sec < segment.end]
    deck_name = f"{event_prefix}{segment.slug}-Deck.pdf"
    out = output_dir / f"{event_prefix}{segment.slug}-Transcript.md"
    body = "\n\n".join(selected).strip()
    content = f"""---
title: "{frontmatter_value(segment.slug.replace("_", " ").title())} Transcript"
source: "{frontmatter_value(source_url)}"
type: "transcript"
tags:
  - "conference"
  - "transcript"
status: "done"
speaker: "{frontmatter_value(segment.speaker)}"
talk: "{frontmatter_value(segment.title)}"
video_range: "{fmt_time(segment.start)}-{fmt_time(segment.end)}"
deck: "{frontmatter_value(deck_name)}"
---
# {segment.slug.replace("_", " ").title()} - Transcript

- **Speaker**: {segment.speaker}
- **Talk**: {segment.title}
- **Video range**: {fmt_time(segment.start)}-{fmt_time(segment.end)}
- **Deck**: [{deck_name}]({deck_name})

## Transcript

{body}
"""
    out.write_text(content, encoding="utf-8", newline="\n")
    return out, len(selected)


def update_manifest(output_dir: Path, rows: list[dict[str, str]]) -> None:
    manifest = output_dir / "event_manifest.csv"
    fieldnames = ["slug", "speaker", "title", "start", "end", "slides", "transcript_entries", "deck", "transcript"]
    existing: dict[str, dict[str, str]] = {}
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing[row["slug"]] = row
    for row in rows:
        merged = existing.get(row["slug"], {})
        merged.update({key: value for key, value in row.items() if value != ""})
        existing[row["slug"]] = merged
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for slug in [row["slug"] for row in rows]:
            writer.writerow({field: existing[slug].get(field, "") for field in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a full timestamped transcript into per-speaker transcript files.")
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--event-prefix", default="")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--heading", default="## Transcript", help="Optional heading marker before timestamped transcript content.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    segments = load_segments(args.segments)
    entries = transcript_entries(args.transcript, args.heading)
    manifest_rows: list[dict[str, str]] = []
    for segment in segments:
        out, count = write_transcript(segment, entries, args.output_dir, args.event_prefix, args.source_url)
        manifest_rows.append(
            {
                "slug": segment.slug,
                "speaker": segment.speaker,
                "title": segment.title,
                "start": fmt_time(segment.start),
                "end": fmt_time(segment.end),
                "slides": "",
                "transcript_entries": str(count),
                "deck": f"{args.event_prefix}{segment.slug}-Deck.pdf",
                "transcript": out.name,
            }
        )
        print(f"{segment.slug}: {count} transcript entries -> {out}")
    update_manifest(args.output_dir, manifest_rows)


if __name__ == "__main__":
    main()
