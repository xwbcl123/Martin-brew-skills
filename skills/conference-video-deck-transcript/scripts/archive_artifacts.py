from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


DEFAULT_KEEP = [
    r".*-Deck\.pdf$",
    r".*-Transcript\.md$",
    r".*manifest\.csv$",
]


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for idx in range(2, 1000):
        candidate = parent / f"{stem}-{idx:02d}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {path}")


def move_item(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_destination(dest_dir / src.name)
    shutil.move(str(src), str(dest))
    return dest


def archive_final_dir(final_dir: Path, archive_dir: Path, keep_patterns: list[str]) -> list[Path]:
    moved = []
    compiled = [re.compile(pattern) for pattern in keep_patterns]
    dest = archive_dir / f"{final_dir.name}_artifacts"
    for item in final_dir.iterdir():
        if any(pattern.match(item.name) for pattern in compiled):
            continue
        moved.append(move_item(item, dest))
    return moved


def archive_work_dirs(work_dirs: list[Path], archive_dir: Path) -> list[Path]:
    moved = []
    dest = archive_dir / "work"
    for work_dir in work_dirs:
        if work_dir.exists():
            moved.append(move_item(work_dir, dest))
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Move non-final processing artifacts to an archive folder.")
    parser.add_argument("--final-dir", required=True, type=Path)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--work-dir", action="append", default=[], type=Path, help="Processing/work directory to move into the archive. Repeatable.")
    parser.add_argument("--keep-pattern", action="append", default=[], help="Regex filename pattern to keep in final-dir. Repeatable.")
    args = parser.parse_args()

    keep_patterns = args.keep_pattern or DEFAULT_KEEP
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    moved.extend(archive_final_dir(args.final_dir, args.archive_dir, keep_patterns))
    moved.extend(archive_work_dirs(args.work_dir, args.archive_dir))
    for path in moved:
        print(path)
    print(f"moved={len(moved)}")


if __name__ == "__main__":
    main()
