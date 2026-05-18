#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def slide_key(path: Path) -> int:
    m = re.search(r"(\d+)", path.stem)
    return int(m.group(1)) if m else 9999


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cols", type=int, default=5)
    parser.add_argument("--thumb-width", type=int, default=360)
    args = parser.parse_args()

    images = sorted(args.images.glob("slide_*.png"), key=slide_key)
    if not images:
        print("no PNG images found")
        return 1
    thumbs = []
    for path in images:
        img = Image.open(path).convert("RGB")
        ratio = args.thumb_width / img.width
        thumb = img.resize((args.thumb_width, int(img.height * ratio)))
        thumbs.append((path, thumb))
    pad = 24
    label_h = 28
    cols = max(1, args.cols)
    rows = (len(thumbs) + cols - 1) // cols
    cell_w = args.thumb_width + pad
    cell_h = thumbs[0][1].height + label_h + pad
    sheet = Image.new("RGB", (cols * cell_w + pad, rows * cell_h + pad), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (path, thumb) in enumerate(thumbs):
        row, col = divmod(i, cols)
        x = pad + col * cell_w
        y = pad + row * cell_h
        sheet.paste(thumb, (x, y + label_h))
        draw.text((x, y), f"{i + 1:02d}  {path.name}", fill=(20, 50, 80))
        draw.rectangle((x, y + label_h, x + thumb.width, y + label_h + thumb.height), outline=(140, 170, 200), width=2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"wrote {args.out} ({len(thumbs)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
