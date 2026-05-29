from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas


@dataclass(frozen=True)
class Segment:
    slug: str
    speaker: str
    title: str
    start: int
    end: int
    keep_ranges: str = ""


def parse_time(value: str | int | float) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    parts = [int(part) for part in text.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Unsupported time value: {value}")


def load_segments(path: Path) -> list[Segment]:
    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
    else:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    segments = []
    for row in rows:
        segments.append(
            Segment(
                slug=row["slug"].strip(),
                speaker=row.get("speaker", "").strip(),
                title=row.get("title", "").strip(),
                start=parse_time(row["start"]),
                end=parse_time(row["end"]),
                keep_ranges=row.get("keep_ranges", "").strip(),
            )
        )
    return segments


def parse_crop(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    parts = [int(part) for part in value.replace(",", ":").split(":")]
    if len(parts) != 4:
        raise ValueError("--crop must be x:y:w:h")
    return parts[0], parts[1], parts[2], parts[3]


def parse_keep_ranges(value: str, count: int) -> set[int] | None:
    if not value:
        return None
    keep: set[int] = set()
    for chunk in value.replace(",", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = [int(part) for part in chunk.split("-", 1)]
            keep.update(range(start, end + 1))
        else:
            keep.add(int(chunk))
    return {idx for idx in keep if 1 <= idx <= count}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def extract_frames(video: Path, segment: Segment, raw_dir: Path, crop: tuple[int, int, int, int] | None, fps: float, overwrite: bool) -> list[Path]:
    seg_dir = raw_dir / segment.slug
    if overwrite and seg_dir.exists():
        shutil.rmtree(seg_dir)
    existing = sorted(seg_dir.glob("frame_*.jpg"))
    if existing:
        return existing
    seg_dir.mkdir(parents=True, exist_ok=True)
    filters = [f"fps={fps}"]
    if crop:
        x, y, w, h = crop
        filters.append(f"crop={w}:{h}:{x}:{y}")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            str(segment.start),
            "-t",
            str(segment.end - segment.start),
            "-i",
            str(video),
            "-vf",
            ",".join(filters),
            "-q:v",
            "2",
            str(seg_dir / "frame_%05d.jpg"),
        ]
    )
    return sorted(seg_dir.glob("frame_*.jpg"))


def image_signature(path: Path) -> np.ndarray:
    img = Image.open(path).convert("L").resize((64, 36), Image.Resampling.LANCZOS)
    return np.asarray(img, dtype=np.int16)


def select_frames(frames: list[Path], threshold: float) -> list[Path]:
    selected: list[Path] = []
    last_sig: np.ndarray | None = None
    for frame in frames:
        sig = image_signature(frame)
        if last_sig is None or float(np.mean(np.abs(sig - last_sig))) >= threshold:
            selected.append(frame)
            last_sig = sig
    return selected


def copy_selected(segment: Segment, selected: list[Path], selected_root: Path, overwrite: bool) -> list[Path]:
    keep = parse_keep_ranges(segment.keep_ranges, len(selected))
    if keep is not None:
        selected = [frame for idx, frame in enumerate(selected, 1) if idx in keep]
    dest = selected_root / segment.slug
    if overwrite and dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for idx, frame in enumerate(selected, 1):
        out = dest / f"{idx:03d}_{segment.slug}.jpg"
        shutil.copy2(frame, out)
        copied.append(out)
    return copied


def make_pdf(frames: list[Path], output: Path) -> None:
    if not frames:
        return
    with Image.open(frames[0]) as first:
        width, height = first.size
    c = canvas.Canvas(str(output), pagesize=(width, height))
    for frame in frames:
        c.drawImage(str(frame), 0, 0, width=width, height=height)
        c.showPage()
    c.save()


def make_contact_sheet(frames: list[Path], output: Path) -> None:
    if not frames:
        return
    thumbs = []
    for frame in frames:
        img = Image.open(frame).convert("RGB")
        img.thumbnail((214, 120))
        tile = Image.new("RGB", (214, 140), "white")
        tile.paste(img, (0, 0))
        ImageDraw.Draw(tile).text((4, 122), frame.name[:32], fill=(0, 0, 0))
        thumbs.append(tile)
    cols = 4
    rows = max(1, (len(thumbs) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * 214, rows * 140), "white")
    for idx, tile in enumerate(thumbs):
        sheet.paste(tile, ((idx % cols) * 214, (idx // cols) * 140))
    sheet.save(output, quality=90)


def fmt_time(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def write_manifest(rows: list[dict[str, str]], output_dir: Path) -> None:
    manifest = output_dir / "event_manifest.csv"
    fieldnames = ["slug", "speaker", "title", "start", "end", "slides", "transcript_entries", "deck", "transcript"]
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract per-speaker deck PDFs from a conference video.")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--event-prefix", default="")
    parser.add_argument("--crop", help="Presentation crop as x:y:w:h. Omit to use the full frame.")
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=18.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    crop = parse_crop(args.crop)
    segments = load_segments(args.segments)
    raw_root = args.work_dir / "raw_frames"
    selected_root = args.work_dir / "selected_slides"
    contact_root = args.work_dir / "contact_sheets"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    selected_root.mkdir(parents=True, exist_ok=True)
    contact_root.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    for segment in segments:
        raw = extract_frames(args.video, segment, raw_root, crop, args.fps, args.overwrite)
        candidates = select_frames(raw, args.threshold)
        selected = copy_selected(segment, candidates, selected_root, args.overwrite)
        pdf = args.output_dir / f"{args.event_prefix}{segment.slug}-Deck.pdf"
        make_pdf(selected, pdf)
        make_contact_sheet(selected, contact_root / f"{segment.slug}_contact.jpg")
        manifest_rows.append(
            {
                "slug": segment.slug,
                "speaker": segment.speaker,
                "title": segment.title,
                "start": fmt_time(segment.start),
                "end": fmt_time(segment.end),
                "slides": str(len(selected)),
                "transcript_entries": "",
                "deck": pdf.name,
                "transcript": "",
            }
        )
        print(f"{segment.slug}: {len(selected)} slides -> {pdf}")
    write_manifest(manifest_rows, args.output_dir)


if __name__ == "__main__":
    main()
