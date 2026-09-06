#!/usr/bin/env python3
"""Create a workflow-native Stage 8 experiment scaffold. Does not run the Target Skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "1"
SCRIPT_VERSION = "2"
RESERVED_NUMBERS = {0, 90, 99}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


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


def validate_input(data: dict) -> None:
    if str(data.get("schema_version")) != SCHEMA_VERSION:
        die(f"unsupported schema_version: {data.get('schema_version')}")
    status = data.get("mapping_status")
    if status not in {"mapped", "manual_required"}:
        die("mapping_status must be mapped | manual_required")
    if not data.get("unit_id"):
        die("unit_id is required")
    if not data.get("hypothesis_slug"):
        die("hypothesis_slug is required")
    if not SLUG_RE.match(str(data["hypothesis_slug"])):
        die(f"illegal hypothesis_slug: {data['hypothesis_slug']}")
    steps = data.get("steps")
    if steps is None:
        die("steps must be an array")
    if not isinstance(steps, list):
        die("steps must be an array")
    seen: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            die("each step must be an object")
        step_id = step.get("id")
        if not step_id or not SLUG_RE.match(str(step_id)):
            die(f"illegal step id: {step_id}")
        if step_id in seen:
            die(f"duplicate step id: {step_id}")
        seen.add(str(step_id))


def load_gaps(path: Path | None) -> list[dict]:
    if path is None:
        return []
    data = load_json(path)
    gaps = data.get("gaps", [])
    if not isinstance(gaps, list):
        die("quiz-gaps-file.gaps must be an array")
    out = []
    for gap in gaps:
        if not isinstance(gap, dict) or not gap.get("id"):
            die("each gap needs id")
        out.append(
            {
                "id": str(gap["id"]),
                "step_id": gap.get("step_id") or None,
                "text": str(gap.get("text") or gap["id"]),
            }
        )
    return out


def assign_step_numbers(steps: list[dict]) -> list[tuple[int, dict]]:
    assigned: list[tuple[int, dict]] = []
    number = 1
    for step in steps:
        while number in RESERVED_NUMBERS:
            number += 1
        if number > 89:
            die("step numbers exhausted before reserved 90")
        assigned.append((number, step))
        number += 1
    return assigned


def planned_paths(output_dir: Path, assigned: list[tuple[int, dict]], fallback: bool) -> list[dict]:
    actions = [
        {"action": "ensure_dir", "path": str(output_dir / "00_input")},
        {"action": "ensure_dir", "path": str(output_dir / "90_scripts")},
        {"action": "write_if_missing", "path": str(output_dir / "99_observation.md"), "owner": "human"},
        {"action": "write_if_missing", "path": str(output_dir / "README.md"), "owner": "human"},
        {"action": "update", "path": str(output_dir / "pipeline.md"), "owner": "script"},
        {"action": "update", "path": str(output_dir / "unassigned-gaps.md"), "owner": "script"},
    ]
    if fallback:
        actions.insert(2, {"action": "ensure_dir", "path": str(output_dir / "01_probe")})
        actions.append({"action": "update", "path": str(output_dir / "01_probe" / "callouts.md"), "owner": "script"})
        actions.append({"action": "update", "path": str(output_dir / "01_probe" / "phase.md"), "owner": "script"})
    for number, step in assigned:
        step_dir = output_dir / f"{number:02d}_{step['id']}"
        actions.append({"action": "ensure_dir", "path": str(step_dir)})
        actions.append({"action": "update", "path": str(step_dir / "callouts.md"), "owner": "script"})
        actions.append({"action": "update", "path": str(step_dir / "phase.md"), "owner": "script"})
    return actions


def observation_template() -> str:
    return (
        "# Observation\n\n"
        "- goal:\n"
        "- action:\n"
        "- observation:\n"
        "- next_step:\n\n"
        "> Empty four fields do not pass Stage 8. Martin fills this file.\n"
    )


def field_items(step: dict | None, key: str, missing: str) -> list[str]:
    if step is None or key not in step:
        return [missing]
    value = step[key]
    if value is None:
        return [missing]
    if isinstance(value, list):
        if not value:
            return ["(none)"]
        return [str(item) if str(item).strip() else missing for item in value]
    text = str(value).strip()
    return [text or missing]


def render_phase(step: dict | None, mapping_status: str) -> str:
    missing = "manual_required" if mapping_status == "manual_required" else "unknown"
    title = step["id"] if step else "probe"
    label = (step.get("label") if step else None) or title
    inputs = field_items(step, "inputs", missing)
    outputs = field_items(step, "outputs", missing)
    gates = field_items(step, "gates", missing)
    locator = field_items(step, "evidence_locator", missing)[0]
    lines = [
        f"# Phase — {title}",
        "",
        "<!-- script-owned; IPO and gate checklist -->",
        "",
        f"- label: {label}",
        f"- mapping_status: `{mapping_status}`",
        "",
        "## Inputs",
        "",
        *[f"- {item}" for item in inputs],
        "",
        "## Outputs",
        "",
        *[f"- {item}" for item in outputs],
        "",
        "## Gates",
        "",
        *[f"- [ ] {item}" for item in gates],
        "",
        "## Evidence locator",
        "",
        locator,
        "",
    ]
    return "\n".join(lines)


def render_pipeline(data: dict, assigned: list[tuple[int, dict]], fallback: bool) -> str:
    missing = "manual_required" if fallback else "unknown"
    lines = [
        f"# Pipeline — {data['hypothesis_slug']}",
        "",
        "<!-- script-owned; IPO map and gate checklist -->",
        "",
        f"- unit_id: `{data['unit_id']}`",
        f"- mapping_status: `{data['mapping_status']}`",
        f"- scaffold_script: v{SCRIPT_VERSION}",
        "",
        "## Map",
        "",
        "```text",
        "00_input → "
        + ("01_probe" if fallback else " → ".join(f"{n:02d}_{s['id']}" for n, s in assigned))
        + " → 99_observation",
        "```",
        "",
        "## Phases",
        "",
    ]
    if fallback:
        lines += [
            "### 01_probe",
            "",
            "- [phase](01_probe/phase.md) — mapping_status=manual_required",
            "- inputs: manual_required",
            "- outputs: manual_required",
            "- gates: `[ ] manual_required`",
            "",
        ]
    for number, step in assigned:
        rel = f"{number:02d}_{step['id']}"
        inputs = ", ".join(field_items(step, "inputs", missing))
        outputs = ", ".join(field_items(step, "outputs", missing))
        gates = ", ".join(f"[ ] {item}" for item in field_items(step, "gates", missing))
        locator = field_items(step, "evidence_locator", missing)[0]
        lines += [
            f"### {rel}",
            "",
            f"- [phase]({rel}/phase.md) — {step.get('label') or step['id']}",
            f"- inputs: {inputs}",
            f"- outputs: {outputs}",
            f"- gates: `{gates}`",
            f"- evidence_locator: {locator}",
            "",
        ]
    return "\n".join(lines)


def render_readme(data: dict, assigned: list[tuple[int, dict]], fallback: bool) -> str:
    lines = [
        f"# Experiment — {data['hypothesis_slug']}",
        "",
        f"- unit_id: `{data['unit_id']}`",
        f"- mapping_status: `{data['mapping_status']}`",
        f"- scaffold_script: v{SCRIPT_VERSION}",
        "",
        "## Pipeline",
        "",
        "```text",
        "00_input → " + ("01_probe" if fallback else " → ".join(f"{n:02d}_{s['id']}" for n, s in assigned)) + " → 99_observation",
        "```",
        "",
        "## Navigation",
        "",
        "- [pipeline / IPO / gates](pipeline.md)",
        "- [00_input](00_input/)",
    ]
    if fallback:
        lines.append("- [01_probe](01_probe/) — mapping_status=manual_required")
        lines.append("- [phase](01_probe/phase.md)")
        lines.append("- [callouts](01_probe/callouts.md)")
    for number, step in assigned:
        label = step.get("label") or step["id"]
        rel = f"{number:02d}_{step['id']}"
        lines.append(f"- [{rel}]({rel}/) — {label}")
        lines.append(f"- [phase]({rel}/phase.md)")
        lines.append(f"- [callouts]({rel}/callouts.md)")
    lines += [
        "- [90_scripts](90_scripts/)",
        "- [unassigned gaps](unassigned-gaps.md)",
        "- [99_observation](99_observation.md)",
        "",
        "## Notes",
        "",
        *(f"- {note}" for note in data.get("composition_notes") or data.get("mapping_notes") or ["(none)"]),
        "",
        "Human comments belong in this README or `99_observation.md`.",
        "Stage 7 updates only `*/callouts.md` and `unassigned-gaps.md`.",
        "IPO and gate checklists live in script-owned `pipeline.md` and `*/phase.md`.",
        "",
    ]
    return "\n".join(lines)


def render_callouts(step: dict | None, gaps: list[dict]) -> str:
    title = step["id"] if step else "probe"
    lines = [f"# Callouts — {title}", "", "<!-- script-owned; Stage 7 updates this file -->", ""]
    if not gaps:
        lines.append("_No mapped quiz gaps._")
        lines.append("")
        return "\n".join(lines)
    for gap in gaps:
        lines.append(f"## {gap['id']}")
        lines.append("")
        lines.append(gap["text"])
        lines.append("")
    return "\n".join(lines)


def render_unassigned(gaps: list[dict]) -> str:
    lines = ["# Unassigned gaps", "", "<!-- script-owned -->", ""]
    if not gaps:
        lines.append("_None._")
        lines.append("")
        return "\n".join(lines)
    for gap in gaps:
        lines.append(f"## {gap['id']}")
        lines.append("")
        lines.append(gap["text"])
        lines.append("")
    return "\n".join(lines)


def assert_not_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        die(f"refusing to write through symlink ({label}): {path}")


def assert_dir_owned(path: Path, root: Path, label: str) -> None:
    if path.is_symlink():
        die(f"refusing to use symlink directory ({label}): {path}")
    if not path.exists():
        return
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        die(f"{label} escapes experiment root: {path}")


def write_if_missing(path: Path, content: str, dry_run: bool) -> str:
    if path.is_symlink() or path.exists():
        return "skip"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        assert_not_symlink(path, "create")
        path.write_text(content, encoding="utf-8", newline="\n")
    return "create"


def update_script_owned(path: Path, content: str, dry_run: bool) -> str:
    assert_not_symlink(path, "script-owned")
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return "unchanged"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        assert_not_symlink(path, "script-owned")
        path.write_text(content, encoding="utf-8", newline="\n")
    return "update"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create numbered experiment dirs from a structured scaffold-input.json."
    )
    parser.add_argument("--input", required=True, help="Path to scaffold-input.json")
    parser.add_argument("--output-dir", required=True, help="Experiment directory to create")
    parser.add_argument("--quiz-gaps-file", help="Optional quiz-gaps.json; default empty gaps")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions; write nothing")
    parser.add_argument(
        "--force-generated",
        action="store_true",
        help="Rewrite script-owned callout files only; never overwrites README or 99_observation.md",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser()
    gaps_path = Path(args.quiz_gaps_file).expanduser().resolve() if args.quiz_gaps_file else None

    data = load_json(input_path)
    validate_input(data)
    gaps = load_gaps(gaps_path)
    fallback = data["mapping_status"] == "manual_required" or not data.get("steps")
    assigned = [] if fallback else assign_step_numbers(data["steps"])
    step_ids = {step["id"] for _, step in assigned}
    mapped_gaps = {sid: [] for sid in step_ids}
    unassigned = []
    for gap in gaps:
        sid = gap["step_id"]
        if sid and sid in mapped_gaps:
            mapped_gaps[sid].append(gap)
        else:
            unassigned.append(gap)

    actions = planned_paths(output_dir, assigned, fallback)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "fallback": fallback, "actions": actions}, indent=2))
        return 0

    if output_dir.exists() or output_dir.is_symlink():
        assert_not_symlink(output_dir, "output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_root = output_dir.resolve()
    for rel in ("00_input", "90_scripts"):
        folder = output_dir / rel
        if folder.exists() or folder.is_symlink():
            assert_dir_owned(folder, output_root, rel)
        folder.mkdir(exist_ok=True)
    if fallback:
        probe = output_dir / "01_probe"
        if probe.exists() or probe.is_symlink():
            assert_dir_owned(probe, output_root, "01_probe")
        probe.mkdir(exist_ok=True)
        update_script_owned(probe / "callouts.md", render_callouts(None, []), False)
        update_script_owned(probe / "phase.md", render_phase(None, data["mapping_status"]), False)
    for number, step in assigned:
        step_dir = output_dir / f"{number:02d}_{step['id']}"
        if step_dir.exists() or step_dir.is_symlink():
            assert_dir_owned(step_dir, output_root, step_dir.name)
        step_dir.mkdir(exist_ok=True)
        update_script_owned(step_dir / "callouts.md", render_callouts(step, mapped_gaps[step["id"]]), False)
        update_script_owned(step_dir / "phase.md", render_phase(step, data["mapping_status"]), False)
    write_if_missing(output_dir / "99_observation.md", observation_template(), False)
    write_if_missing(output_dir / "README.md", render_readme(data, assigned, fallback), False)
    update_script_owned(output_dir / "pipeline.md", render_pipeline(data, assigned, fallback), False)
    update_script_owned(output_dir / "unassigned-gaps.md", render_unassigned(unassigned), False)
    if args.force_generated:
        pass
    print(json.dumps({"ok": True, "output_dir": str(output_dir), "fallback": fallback, "steps": len(assigned)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
