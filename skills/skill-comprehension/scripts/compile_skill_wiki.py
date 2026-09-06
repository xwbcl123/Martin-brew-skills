#!/usr/bin/env python3
"""Deterministic skill-wiki compiler. No second LLM ingest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1"
COMPILER_VERSION = "6"
ROLE_ORDER = {"dossier_snapshot": 0, "module": 1, "studio": 2, "meta": 3}
FILENAME_ORDER = re.compile(r"(?:^|/)(\d{2})[_-]")
ITEM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SNAPSHOT_RE = re.compile(r"^outcomes/_transport/dossier-snapshots/([0-9a-f]{64})\.md$")
MARKDOWN_TYPES = {"markdown", "md", "quiz", "flashcards"}
MEDIA_TYPES = {"pdf", "png", "jpg", "jpeg", "gif", "webp", "mp3", "m4a", "wav", "mp4", "webm", "mov", "pptx"}
KNOWN_JSON_KINDS = (
    ("scaffold-input", lambda obj: "steps" in obj and "mapping_status" in obj and "unit_id" in obj),
    ("wiki-input-manifest", lambda obj: isinstance(obj.get("inputs"), list) and "unit_id" in obj),
    ("quiz-gaps", lambda obj: isinstance(obj.get("gaps"), list) and "inputs" not in obj),
    ("content-manifest", lambda obj: "content_hash" in obj and isinstance(obj.get("pages"), list)),
    ("wiki-pointers", lambda obj: "input_hash" in obj and isinstance(obj.get("inputs"), list)),
)

MODULE_ORDER = {
    "dossier": 0,
    "architecture": 1,
    "capability": 2,
    "workflow": 3,
    "glossary": 4,
    "critique": 5,
    "quiz": 6,
    "experiment": 7,
    "artifact-prompt": 8,
}
STUDIO_ORDER = {
    "custom-report": 1,
    "slide-deck": 2,
    "video": 3,
    "video-overview": 3,
    "audio-overview": 4,
    "flashcards": 5,
    "quiz": 6,
    "data-table": 7,
    "infographic": 8,
    "mind-map": 9,
}


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON {path}: {exc}")
    if not isinstance(data, dict):
        die(f"{path} must be a JSON object")
    return data


def yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and type(value) is int:
        return str(value)
    text = str(value)
    if text == "" or re.search(r"[:#{}[\],&*?|>!%@`'\"]|\s", text) or text in {"true", "false", "null"}:
        return json.dumps(text, ensure_ascii=False)
    return text


def resolve_under(root: Path, rel: str | None) -> Path | None:
    if rel in (None, "", "null"):
        return None
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        die(f"path escapes unit root: {rel}")
    path = root / rel
    if path.is_symlink():
        target = path.resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            die(f"symlink escapes unit root: {rel}")
        return target
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        die(f"path escapes unit root: {rel}")
    return resolved


def planned_dest(output: Path, rel: str) -> Path:
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        die(f"illegal page path: {rel}")
    dest = output.joinpath(*Path(rel).parts)
    if dest.is_symlink():
        die(f"refusing to write through symlink: {rel}")
    try:
        dest.parent.resolve().relative_to(output.resolve())
    except ValueError:
        die(f"page path escapes output: {rel}")
    if dest.exists():
        try:
            dest.resolve().relative_to(output.resolve())
        except ValueError:
            die(f"page path escapes output: {rel}")
    return dest


def infer_order(item: dict) -> int:
    if item.get("order") is not None:
        return int(item["order"])
    path = str(item.get("path") or "")
    match = FILENAME_ORDER.search(path)
    if match:
        return int(match.group(1))
    item_id = str(item.get("item_id") or "")
    if item["role"] == "dossier_snapshot":
        return 0
    if item["role"] == "module":
        return MODULE_ORDER.get(item_id, 90)
    if item["role"] == "studio":
        return STUDIO_ORDER.get(item_id, 90)
    return 90


def source_claim_status(item: dict) -> str:
    if item.get("status") == "present":
        return "unconfirmed"
    return "unknown"


def validate_manifest(data: dict) -> None:
    if str(data.get("schema_version")) != SCHEMA_VERSION:
        die(f"unsupported schema_version: {data.get('schema_version')}")
    if not data.get("unit_id"):
        die("unit_id is required")
    quiz = data.get("quiz_answers_collected", False)
    if type(quiz) is not bool:
        die("quiz_answers_collected must be a JSON boolean")
    evidence = data.get("quiz_evidence") or {"path": None, "sha256": None, "locator": None}
    if not isinstance(evidence, dict):
        die("quiz_evidence must be an object")
    if quiz is True:
        path = evidence.get("path")
        digest = evidence.get("sha256")
        locator = evidence.get("locator")
        if not isinstance(path, str) or not path.strip() or path == "null":
            die("quiz_answers_collected=true requires a non-empty quiz_evidence.path")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            die("quiz_answers_collected=true requires quiz_evidence.sha256 as 64 hex chars")
        if not isinstance(locator, str) or not locator.strip() or locator == "null":
            die("quiz_answers_collected=true requires a non-empty quiz_evidence.locator")
    inputs = data.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        die("inputs must be a non-empty array")
    seen: dict[tuple[str, str, str], dict] = {}
    dossiers = []
    for item in inputs:
        if not isinstance(item, dict):
            die("each input must be an object")
        role = item.get("role")
        item_id = item.get("item_id")
        if role not in ROLE_ORDER:
            die(f"unknown role: {role}")
        if not isinstance(item_id, str) or not ITEM_ID_RE.fullmatch(item_id):
            die(f"item_id must be a kebab-case slug: {item_id}")
        fmt = str(item.get("format") or item.get("artifact_type") or "unknown")
        key = (role, str(item_id), fmt)
        if key in seen:
            die(f"ambiguous duplicate input for {key}; select exactly one")
        seen[key] = item
        status = item.get("status")
        if status not in {"present", "pending", "missing", "unsupported"}:
            die(f"invalid status: {status}")
        if status == "present" and not item.get("sha256"):
            die(f"present input {item_id} needs sha256")
        if status in {"pending", "missing"} and item.get("sha256") not in (None, "", "null"):
            die(f"{status} input {item_id} must have sha256=null")
        playback = item.get("playback")
        if playback is not None:
            if not isinstance(playback, dict):
                die(f"{item_id} playback must be an object")
            pb_path = playback.get("path")
            pb_hash = playback.get("sha256")
            pb_fmt = playback.get("format")
            if not isinstance(pb_path, str) or not pb_path.strip() or Path(pb_path).is_absolute() or ".." in Path(pb_path).parts:
                die(f"{item_id} playback.path must be a unit-relative file")
            if not isinstance(pb_hash, str) or not SHA256_RE.fullmatch(pb_hash):
                die(f"{item_id} playback.sha256 must be 64 hex chars")
            if not isinstance(pb_fmt, str) or not pb_fmt.strip():
                die(f"{item_id} playback.format is required")
        if role == "dossier_snapshot":
            rel = item.get("path")
            if status == "present":
                match = SNAPSHOT_RE.fullmatch(str(rel or ""))
                if not match:
                    die("dossier_snapshot path must be outcomes/_transport/dossier-snapshots/<sha256>.md")
                if match.group(1) != item.get("sha256"):
                    die("dossier snapshot filename must match sha256")
            dossiers.append(item)
        item["order"] = infer_order(item)
    if len(dossiers) > 1:
        die("multiple dossier_snapshot inputs; select exactly one")


def excerpt_markdown(text: str) -> str:
    body = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return body + "\n"


def render_json_template(obj) -> str:
    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
    return f"```json\n{pretty}\n```\n"


def classify_json(obj) -> str | None:
    if not isinstance(obj, dict):
        return None
    for name, predicate in KNOWN_JSON_KINDS:
        if predicate(obj):
            return name
    return None


def _cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_csv_table(text: str) -> str:
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    rows = list(reader)
    if not rows:
        return "_Empty table._\n"
    header = [_cell(c) for c in rows[0]]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        padded = list(row) + [""] * max(0, len(header) - len(row))
        lines.append("| " + " | ".join(_cell(c) for c in padded[: len(header)]) + " |")
    return "\n".join(lines) + "\n"


def rel_from_page(page_name: str, artifact_rel: str, output_rel: str) -> str:
    page_parent = Path(output_rel) / Path(page_name).parent
    return Path(os.path.relpath(artifact_rel, page_parent)).as_posix()


def sniff_media(data: bytes, declared: str | None = None) -> str | None:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"GIF8"):
        return "gif"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if declared in {"mp3", "m4a", "aac"} or brand in {b"M4A ", b"M4B ", b"mp4a"}:
            return "m4a"
        return "mp4"
    if data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    if data.startswith(b"RIFF") and b"WAVE" in data[:16]:
        return "wav"
    return None


def provenance(item: dict, size: int, extra: list[str] | None = None) -> str:
    lines = [
        "<details><summary>Provenance</summary>\n",
        f"- sha256: `{item.get('sha256')}`",
        f"- bytes: `{size}`",
        f"- status: `{item.get('status')}`",
    ]
    for line in extra or []:
        lines.append(f"- {line}")
    lines.append("\n</details>\n")
    return "\n".join(lines)


def render_media(item: dict, page_name: str, output_rel: str, path: Path | None) -> str:
    rel = item.get("path")
    if not rel:
        return "_No artifact file._\n"
    artifact = str(item.get("artifact_type") or Path(rel).suffix.lstrip(".")).lower()
    size = path.stat().st_size if path and path.exists() else 0
    detected = sniff_media(path.read_bytes()[:64], artifact) if path and path.is_file() else None
    playback = item.get("playback") if isinstance(item.get("playback"), dict) else None
    play_rel = playback["path"] if playback else rel
    href = rel_from_page(page_name, play_rel, output_rel)
    original_href = rel_from_page(page_name, rel, output_rel)
    label = Path(play_rel).name
    extra = []
    if detected and detected != Path(rel).suffix.lstrip(".").lower():
        extra.append(f"declared_suffix: `.{Path(rel).suffix.lstrip('.').lower()}`")
        extra.append(f"detected_format: `{detected}`")
    if playback:
        extra.append(f"playback_alias: `{play_rel}`")
        extra.append(f"original_export: `{rel}`")
    if artifact == "pptx":
        body = (
            f"[Open {Path(rel).name}]({original_href})\n\n"
            "Obsidian previews PDF/audio/video more reliably than PPTX. Prefer the PDF sibling when present.\n\n"
        )
    else:
        body = f"![]({href})\n\n[Open {label}]({href})\n\n"
        if play_rel != rel:
            body += f"[Open original export]({original_href})\n\n"
    return body + provenance(item, size, extra)


def frontmatter(page_id: str, page_type: str, unit_id: str, sources: list[dict], boundary: str, order: int) -> str:
    lines = [
        "---",
        f"type: {page_type}",
        f"unit_id: {yaml_scalar(unit_id)}",
        f"page_id: {yaml_scalar(page_id)}",
        f"order: {order}",
        f"generated_by: compile_skill_wiki.py",
        f"compiler_version: {yaml_scalar(COMPILER_VERSION)}",
        f"evidence_boundary: {boundary}",
        "sources:",
    ]
    if not sources:
        lines.append("  []")
    for src in sources:
        lines.append(f"  - path: {yaml_scalar(src.get('path'))}")
        lines.append(f"    sha256: {yaml_scalar(src.get('sha256'))}")
        lines.append(f"    locator: {yaml_scalar(src.get('locator'))}")
        lines.append(f"    status: {yaml_scalar(src.get('status'))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def page_name(item: dict) -> str:
    order = int(item.get("order") or infer_order(item))
    slug = str(item["item_id"])
    numbered = f"{order:02d}-{slug}.md"
    if item["role"] == "dossier_snapshot":
        return numbered
    if item["role"] == "module":
        return numbered
    if item["role"] == "studio":
        return f"studio/{numbered}"
    return f"meta/{numbered}"


def display_title(item: dict) -> str:
    order = int(item.get("order") or infer_order(item))
    label = str(item["item_id"]).replace("-", " ").title()
    return f"{order:02d} {label}"


def is_answer_page(item: dict) -> bool:
    artifact = str(item.get("artifact_type") or "")
    item_id = str(item.get("item_id") or "")
    return artifact in {"quiz", "flashcards"} or item_id in {"quiz", "flashcards", "sc-quiz"}


def metadata_card(item: dict, page: str, output_rel: str, path: Path | None, reason: str) -> str:
    rel = item.get("path") or "null"
    href = rel_from_page(page, rel, output_rel) if item.get("path") else None
    link = f"[Open original]({href})\n\n" if href else ""
    size = path.stat().st_size if path and path.exists() else 0
    return f"{reason}\n\n{link}" + provenance(item, size)


def build_body(
    item: dict,
    raw: str | None,
    path: Path | None,
    quiz_ok: bool,
    page: str,
    output_rel: str,
) -> tuple[str, str]:
    status = item["status"]
    if status == "pending":
        return "_Pending source. Not completed. Wiki will embed the original file once it exists._\n", "meta"
    if status == "missing":
        return "_Missing source. Unavailable._\n", "meta"
    if status == "unsupported":
        return "_Unsupported type. Metadata only._\n", "meta"
    if is_answer_page(item) and not quiz_ok:
        rel = item.get("path")
        note = "_Answers withheld until Martin quiz evidence is recorded._\n"
        if rel:
            href = rel_from_page(page, rel, output_rel)
            note += f"\nOriginal file is not inlined: `{rel}`.\n"
            note += f"\n<!-- source {href} -->\n"
        return note, "practice_only"
    artifact = str(item.get("artifact_type") or "")
    if artifact in MARKDOWN_TYPES and raw is not None:
        return excerpt_markdown(raw), "source_excerpt"
    if artifact == "json" and raw is not None:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return metadata_card(item, page, output_rel, path, "_JSON parse failed; metadata only._"), "meta"
        kind = classify_json(obj)
        if kind is None:
            return metadata_card(item, page, output_rel, path, "_Unsupported JSON schema. Metadata only._"), "meta"
        return f"**JSON type:** `{kind}`\n\n" + render_json_template(obj), "source_excerpt"
    if artifact == "csv" and raw is not None:
        href = rel_from_page(page, str(item.get("path")), output_rel) if item.get("path") else None
        table = render_csv_table(raw)
        extra = f"\n[Open CSV]({href})\n" if href else ""
        return table + extra, "source_excerpt"
    if artifact in MEDIA_TYPES or (path and path.suffix.lstrip(".").lower() in MEDIA_TYPES):
        return render_media(item, page, output_rel, path), "source_excerpt"
    return metadata_card(item, page, output_rel, path, "_Unsupported type. Metadata only._"), "meta"


def collect_input_hash(manifest: dict) -> str:
    blob = json.dumps(
        {
            "compiler_version": COMPILER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "unit_id": manifest["unit_id"],
            "quiz_answers_collected": manifest.get("quiz_answers_collected", False),
            "quiz_evidence": manifest.get("quiz_evidence") or {},
            "inputs": sorted(
                manifest["inputs"],
                key=lambda i: (
                    ROLE_ORDER[i["role"]],
                    infer_order(i),
                    i["item_id"],
                    str(i.get("format") or i.get("artifact_type") or ""),
                ),
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(blob)


def output_rel_from_unit(unit: Path, output: Path) -> str:
    return output.resolve().relative_to(unit.resolve()).as_posix()


def load_previous_manifest(output: Path) -> dict | None:
    path = output / "content-manifest.json"
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    pages = data.get("pages")
    if not isinstance(pages, list):
        return None
    return data


def recorded_hash(previous: dict | None, rel: str) -> str | None:
    if not previous:
        return None
    hashes = previous.get("page_hashes")
    if isinstance(hashes, dict) and rel in hashes:
        value = hashes[rel]
        return value if isinstance(value, str) else None
    return None


def file_matches_recorded(path: Path, previous: dict | None, rel: str) -> bool:
    expected = recorded_hash(previous, rel)
    if expected is None or not path.is_file() or path.is_symlink():
        return False
    return sha256_bytes(path.read_bytes()) == expected


def assert_replaceable(path: Path, previous: dict | None, rel: str, adopt_legacy: bool) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink():
        die(f"refusing to write through symlink: {rel}")
    if file_matches_recorded(path, previous, rel):
        return
    if adopt_legacy and previous and rel in set(previous.get("pages") or []) and recorded_hash(previous, rel) is None:
        return
    die(f"unowned or human-modified file, refusing overwrite: {rel}")


def commit_paths(output: Path) -> tuple[Path, Path]:
    parent = output.parent
    return parent / f".{output.name}.commit", parent / f".{output.name}.prev"


def valid_generated_tree(root: Path, expected_unit: str) -> dict | None:
    path = root / "content-manifest.json"
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("unit_id") != expected_unit:
        return None
    hashes = data.get("page_hashes")
    pages = data.get("pages")
    if not isinstance(hashes, dict) or not isinstance(pages, list) or not pages:
        return None
    if set(pages) != set(hashes):
        return None
    ordered = {}
    for rel in sorted(pages):
        if not isinstance(rel, str) or not isinstance(hashes.get(rel), str):
            return None
        page = root / rel
        if page.is_symlink() or not page.is_file():
            return None
        digest = sha256_bytes(page.read_bytes())
        if digest != hashes[rel]:
            return None
        ordered[rel] = digest
    expected = sha256_text(json.dumps(ordered, separators=(",", ":")))
    if data.get("content_hash") != expected:
        return None
    return data


def recover_commit_state(output: Path, commit_dir: Path, prev_dir: Path, expected_unit: str) -> None:
    marker = commit_dir / ".COMMITTED"
    if commit_dir.exists():
        commit_ok = marker.is_file() and valid_generated_tree(commit_dir, expected_unit) is not None
        if not commit_ok or output.exists():
            die(f"leftover or untrusted commit directory, inspect before compile: {commit_dir}")
        if prev_dir.exists() and valid_generated_tree(prev_dir, expected_unit) is None:
            die(f"unknown prev directory, inspect before compile: {prev_dir}")
        os.replace(commit_dir, output)
        leftover = output / ".COMMITTED"
        if leftover.exists():
            leftover.unlink()
        if prev_dir.exists():
            keep = generated_rels(output) | generated_rels(prev_dir)
            merge_extras_from(prev_dir, output, keep)
            shutil.rmtree(prev_dir)
        return
    if prev_dir.exists() and not output.exists():
        if valid_generated_tree(prev_dir, expected_unit) is None:
            die(f"unknown prev directory, inspect before compile: {prev_dir}")
        os.replace(prev_dir, output)
    if prev_dir.exists() and output.exists():
        die(f"leftover prev directory, inspect before compile: {prev_dir}")


def generated_rels(root: Path) -> set[str]:
    keep = {"log.md", ".COMMITTED", "content-manifest.json"}
    path = root / "content-manifest.json"
    if path.is_file() and not path.is_symlink():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            keep.update(str(item) for item in data.get("pages") or [])
            keep.update(str(item) for item in (data.get("page_hashes") or {}))
    return keep


def extra_human_files(output: Path, keep: set[str]) -> list[str]:
    extras: list[str] = []
    if not output.is_dir():
        return extras
    for path in output.rglob("*"):
        if not path.is_file() and not path.is_symlink():
            continue
        rel = path.relative_to(output).as_posix()
        if rel in keep or rel in {"log.md", ".COMMITTED"} or rel == ".next" or rel.startswith(".next/"):
            continue
        extras.append(rel)
    return extras


def merge_extras_from(src_root: Path, dest_root: Path, keep: set[str]) -> None:
    for rel in extra_human_files(src_root, keep):
        src = src_root / rel
        dest = dest_root / rel
        data = src.read_bytes() if src.is_file() and not src.is_symlink() else None
        if data is None:
            die(f"unowned symlink in prev tree: {rel}")
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.read_bytes() != data:
                die(f"prev extra conflicts with live wiki: {rel}")
            continue
        planned_dest(dest_root, rel).parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)


def write_wiki_tree(commit_dir: Path, pages: dict[str, str], log_text: str, extras: dict[str, bytes]) -> None:
    if commit_dir.exists():
        die(f"leftover commit directory, inspect before compile: {commit_dir}")
    commit_dir.mkdir(parents=True, exist_ok=False)
    for name, text in pages.items():
        dest = planned_dest(commit_dir, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")
    log_path = commit_dir / "log.md"
    log_path.write_text(log_text, encoding="utf-8", newline="\n")
    for rel, data in extras.items():
        dest = planned_dest(commit_dir, rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    (commit_dir / ".COMMITTED").write_text("ok\n", encoding="utf-8")


def swap_commit(output: Path, commit_dir: Path, prev_dir: Path, inject_fail: str | None) -> None:
    if inject_fail == "before-swap":
        die("injected failure before-swap")
    if output.exists():
        if prev_dir.exists():
            die(f"leftover prev directory, inspect before compile: {prev_dir}")
        os.replace(output, prev_dir)
    if inject_fail == "after-rename-old":
        die("injected failure after-rename-old")
    os.replace(commit_dir, output)
    committed = output / ".COMMITTED"
    if committed.exists():
        committed.unlink()
    if prev_dir.exists():
        keep = generated_rels(output) | generated_rels(prev_dir)
        merge_extras_from(prev_dir, output, keep)
        shutil.rmtree(prev_dir)


def source_record(item: dict) -> dict:
    return {
        "path": item.get("path"),
        "sha256": item.get("sha256"),
        "locator": item.get("locator") or "file",
        "status": source_claim_status(item),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a minimal skill wiki from an allowlist manifest.")
    parser.add_argument("--learning-unit", required=True, help="Learning unit root")
    parser.add_argument("--input-manifest", required=True, help="wiki-input-manifest.json")
    parser.add_argument("--output", required=True, help="Wiki output directory, usually outcomes/reading/wiki")
    parser.add_argument("--dry-run", action="store_true", help="Print planned pages; write nothing")
    parser.add_argument(
        "--adopt-legacy-pages",
        action="store_true",
        help="One-time replace of previous.pages that have no page_hashes (compiler upgrade).",
    )
    parser.add_argument(
        "--inject-fail",
        choices=["before-swap", "after-rename-old"],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    unit = Path(args.learning_unit).expanduser().resolve()
    if not unit.is_dir():
        die(f"learning unit not found: {unit}")
    manifest_path = Path(args.input_manifest).expanduser().resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = (unit / output)
    output = output if output.exists() or output.parent.exists() else output
    try:
        output_resolved = output.resolve()
        output_resolved.relative_to(unit)
    except ValueError:
        die("output must stay under the learning unit")
    if output.exists() and output.is_symlink():
        die("output must not be a symlink")

    manifest = load_json(manifest_path)
    validate_manifest(manifest)
    quiz_ok = manifest.get("quiz_answers_collected") is True
    if quiz_ok:
        ev_path = resolve_under(unit, manifest["quiz_evidence"]["path"])
        if ev_path is None or not ev_path.is_file() or ev_path.is_symlink():
            die("quiz evidence file missing")
        if ev_path.stat().st_size <= 0:
            die("quiz evidence file is empty")
        actual = sha256_bytes(ev_path.read_bytes())
        if actual != manifest["quiz_evidence"]["sha256"]:
            die("quiz evidence sha256 mismatch")

    inputs = sorted(
        manifest["inputs"],
        key=lambda i: (
            ROLE_ORDER[i["role"]],
            infer_order(i),
            i["item_id"],
            str(i.get("format") or i.get("artifact_type") or ""),
        ),
    )
    input_hash = collect_input_hash(manifest)
    planned = []
    builds: dict[str, dict] = {}
    out_rel = output_rel_from_unit(unit, output.resolve() if output.exists() else (unit / Path(args.output)))

    for item in inputs:
        rel = item.get("path")
        path = resolve_under(unit, rel if item["status"] == "present" else None)
        raw = None
        if item["status"] == "present":
            if path is None or not path.is_file():
                die(f"present path missing: {rel}")
            data = path.read_bytes()
            if sha256_bytes(data) != item["sha256"]:
                die(f"sha256 mismatch: {rel}")
            artifact = str(item.get("artifact_type") or "")
            if artifact in {*MARKDOWN_TYPES, "json", "csv"}:
                raw = data.decode("utf-8")
            playback = item.get("playback")
            if isinstance(playback, dict):
                pb_path = resolve_under(unit, playback["path"])
                if pb_path is None or not pb_path.is_file() or pb_path.is_symlink():
                    die(f"playback path missing: {playback['path']}")
                if sha256_bytes(pb_path.read_bytes()) != playback["sha256"]:
                    die(f"playback sha256 mismatch: {playback['path']}")
        name = page_name(item)
        body, boundary = build_body(item, raw, path, quiz_ok, name, out_rel)
        fmt = str(item.get("format") or item.get("artifact_type") or "source")
        if name in builds and item["role"] == "studio":
            builds[name]["sections"].append((fmt, body, boundary))
            builds[name]["sources"].append(source_record(item))
        else:
            builds[name] = {
                "item": item,
                "sections": [(fmt, body, boundary)],
                "sources": [source_record(item)],
            }
        planned.append({"page": name, "item_id": item["item_id"], "order": infer_order(item), "status": item["status"]})

    pages: dict[str, str] = {}
    for name, build in builds.items():
        item = build["item"]
        sources = build["sources"]
        sections = build["sections"]
        boundary = sections[0][2]
        if len(sections) == 1:
            body = sections[0][1]
        else:
            parts = [sections[0][1].rstrip()]
            for fmt, section, _boundary in sections[1:]:
                parts.append(f"## Format {fmt}\n\n{section.rstrip()}")
            body = "\n\n".join(parts) + "\n"
        page_id = f"{manifest['unit_id']}:{item['role']}:{item['item_id']}"
        pages[name] = (
            frontmatter(
                page_id,
                item["role"].replace("_snapshot", ""),
                manifest["unit_id"],
                sources,
                boundary,
                infer_order(item),
            )
            + f"# {display_title(item)}\n\n"
            + body
        )

    purpose = (
        frontmatter(f"{manifest['unit_id']}:purpose", "meta", manifest["unit_id"], [], "meta", 98)
        + "# Purpose\n\n"
        + f"Comprehension wiki for `{manifest['unit_id']}`.\n"
    )
    schema = (
        frontmatter(f"{manifest['unit_id']}:schema", "meta", manifest["unit_id"], [], "meta", 99)
        + "# Schema\n\n"
        + "- page names are `NN-slug.md`, aligned with slash/prompt numbers\n"
        + "- frontmatter fields are flattened: type, unit_id, page_id, sources[], generated_by\n"
        + "- present files stay `unconfirmed` until a page-level locator upgrades a claim\n"
        + "- studio pages embed or link the original artifact for Obsidian preview\n"
        + "- CSV is rendered as a Markdown table\n"
        + "- unknown JSON is a metadata card, not a pretty-print dump\n"
        + "- log.md is not part of content identity\n"
        + "- quiz answers require a strict boolean gate plus path+sha256+locator\n"
    )
    raw_manifest = json.dumps(
        {"unit_id": manifest["unit_id"], "inputs": inputs, "input_hash": input_hash},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    def index_line(name: str) -> str:
        stem = Path(name).stem
        if name.startswith("studio/"):
            return f"- [[studio/{stem}|{stem}]] — `{name}`"
        return f"- [[{stem}]] — `{name}`"

    module_pages = [n for n in pages if not n.startswith("studio/") and not n.startswith("meta/")]
    studio_pages = [n for n in pages if n.startswith("studio/")]
    index_links = ["## Modules", ""] + [index_line(n) for n in sorted(module_pages)]
    index_links += ["", "## Studio artifacts", ""] + [index_line(n) for n in sorted(studio_pages)]
    index = (
        frontmatter(f"{manifest['unit_id']}:index", "meta", manifest["unit_id"], [], "meta", 0)
        + f"# Wiki index — {manifest['unit_id']}\n\n"
        + "\n".join(index_links)
        + "\n\n- [[purpose]]\n- [[schema]]\n- [[log]]\n"
    )
    pages["purpose.md"] = purpose
    pages["schema.md"] = schema
    pages["index.md"] = index
    pages["raw/pointers.json"] = raw_manifest

    page_only = {k: v for k, v in pages.items() if k not in {"log.md", "content-manifest.json"}}
    page_hashes = {k: sha256_text(v) for k, v in sorted(page_only.items())}
    content_hash = sha256_text(json.dumps(page_hashes, separators=(",", ":")))
    pages["content-manifest.json"] = json.dumps(
        {
            "generated_by": "compile_skill_wiki.py",
            "compiler_version": COMPILER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "unit_id": manifest["unit_id"],
            "input_hash": input_hash,
            "content_hash": content_hash,
            "pages": sorted(page_only),
            "page_hashes": page_hashes,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if args.dry_run:
        print(json.dumps({"dry_run": True, "output": str(output_resolved), "pages": planned, "content_hash": content_hash}, indent=2))
        return 0

    output_parent = output.parent
    if not output_parent.exists():
        output_parent.mkdir(parents=True, exist_ok=True)
        try:
            output_parent.resolve().relative_to(unit)
        except ValueError:
            shutil.rmtree(output_parent, ignore_errors=True)
            die("output parent must stay under the learning unit")
    output_resolved = output.resolve() if output.exists() else (output_parent.resolve() / output.name)
    try:
        output_resolved.relative_to(unit)
    except ValueError:
        die("output must stay under the learning unit")
    leftover_next = output_resolved / ".next"
    if leftover_next.exists():
        die(f"leftover .next directory, inspect before compile: {leftover_next}")
    commit_dir, prev_dir = commit_paths(output_resolved)
    recover_commit_state(output_resolved, commit_dir, prev_dir, str(manifest["unit_id"]))

    previous = load_previous_manifest(output_resolved if output_resolved.exists() else output)
    previous_pages = set(previous.get("pages") or []) if previous else set()
    keep = set(pages)
    if output_resolved.exists():
        for rel in keep:
            dest = planned_dest(output_resolved, rel)
            if rel == "content-manifest.json" and previous is not None:
                continue
            assert_replaceable(dest, previous, rel, args.adopt_legacy_pages)
        for rel in sorted(previous_pages - keep - {"log.md"}):
            dest = planned_dest(output_resolved, rel)
            if dest.exists() or dest.is_symlink():
                assert_replaceable(dest, previous, rel, args.adopt_legacy_pages)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    line = f"{stamp} | compile | pages={len(page_only)} | content_hash={content_hash} | input_hash={input_hash} | compiler={COMPILER_VERSION}\n"
    existing_log = ""
    log_path = output_resolved / "log.md"
    if log_path.is_symlink():
        die("refusing to write log.md through a symlink")
    if log_path.is_file():
        existing_log = log_path.read_text(encoding="utf-8")
    log_text = (existing_log if existing_log else "# Compile log\n\n") + line

    extras: dict[str, bytes] = {}
    if output_resolved.exists():
        for rel in extra_human_files(output_resolved, keep):
            src = output_resolved / rel
            if src.is_symlink():
                die(f"unowned symlink in wiki, refusing compile: {rel}")
            extras[rel] = src.read_bytes()
    write_wiki_tree(commit_dir, pages, log_text, extras)
    swap_commit(output_resolved, commit_dir, prev_dir, args.inject_fail)
    print(json.dumps({"ok": True, "output": str(output_resolved), "content_hash": content_hash, "input_hash": input_hash}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
