#!/usr/bin/env python3
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def command_exists(name):
    return shutil.which(name) is not None


def profile_path(profile):
    return CONFIG / "profiles" / f"{profile}.yaml"


def load_profile(profile):
    path = profile_path(profile)
    if not path.exists():
        raise SystemExit(f"Profile not found: {path}")
    return load_yaml(path)


def load_commands():
    return load_yaml(CONFIG / "commands.yaml")


def flatten_services(profile):
    rows = []
    for workspace in profile.get("workspaces", []):
        for pane in workspace.get("panes", []):
            for service in pane.get("services", []):
                rows.append(
                    {
                        "workspace": workspace,
                        "pane": pane,
                        "service": service,
                    }
                )
    return rows


def detect_profile(args):
    candidates = []
    os_name = platform.system().lower()
    hostname = platform.node()
    for path in sorted((CONFIG / "profiles").glob("*.yaml")):
        profile = load_yaml(path)
        match = profile.get("match", {})
        score = 0
        reasons = []
        if match.get("os") and match["os"].lower() in os_name:
            score += 40
            reasons.append(f"os={match['os']}")
        if hostname in match.get("hostnames", []):
            score += 40
            reasons.append(f"hostname={hostname}")
        missing_required = []
        for cmd in match.get("required_commands", []):
            if command_exists(cmd):
                score += 10
                reasons.append(f"has:{cmd}")
            else:
                missing_required.append(cmd)
        if missing_required:
            score -= 100
            reasons.append("missing_required:" + ",".join(missing_required))
        candidates.append(
            {
                "profile": profile.get("profile", path.stem),
                "score": score,
                "reasons": reasons,
                "path": str(path),
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    result = {
        "hostname": hostname,
        "os": os_name,
        "selected": candidates[0]["profile"] if candidates and candidates[0]["score"] > 0 else None,
        "ambiguous": len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"],
        "candidates": candidates,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["selected"] and not result["ambiguous"] else 2


def cmux_tree():
    proc = run(["cmux", "tree", "--all", "--json"])
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "cmux tree failed")
    return json.loads(proc.stdout)


def cmux_top():
    proc = run(["cmux", "top", "--all", "--processes", "--flat", "--format", "tsv"])
    if proc.returncode != 0:
        return {"raw": "", "surface_processes": {}}
    surface_processes = {}
    current_surface = None
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        kind = parts[3]
        ident = parts[4]
        parent = parts[5]
        name = parts[6] if len(parts) > 6 else ""
        if kind == "surface":
            current_surface = ident
            surface_processes.setdefault(ident, [])
        elif kind == "process":
            target = parent if parent.startswith("surface:") else current_surface
            if target:
                surface_processes.setdefault(target, []).append(name)
    return {"raw": proc.stdout, "surface_processes": surface_processes}


def flatten_cmux(tree):
    rows = []
    for window in tree.get("windows", []):
        for workspace in window.get("workspaces", []):
            for pane in workspace.get("panes", []):
                for surface in pane.get("surfaces", []):
                    rows.append(
                        {
                            "window_ref": window.get("ref"),
                            "workspace_ref": workspace.get("ref"),
                            "workspace_title": workspace.get("title"),
                            "pane_ref": pane.get("ref"),
                            "pane_index": pane.get("index"),
                            "surface_ref": surface.get("ref"),
                            "surface_title": surface.get("title"),
                            "index_in_pane": surface.get("index_in_pane"),
                            "type": surface.get("type"),
                            "tty": surface.get("tty"),
                            "selected": surface.get("selected_in_pane"),
                        }
                    )
    return rows


def match_surface(live_rows, workspace_name, pane_index, service):
    candidates = [
        row
        for row in live_rows
        if row["workspace_title"] == workspace_name
        and row["pane_index"] == pane_index
        and row["index_in_pane"] == service.get("index_in_pane")
    ]
    if candidates:
        return candidates[0]
    title = service.get("surface_title_hint")
    candidates = [
        row
        for row in live_rows
        if row["workspace_title"] == workspace_name and row["surface_title"] == title
    ]
    return candidates[0] if candidates else None


def validate_roster(args):
    profile = load_profile(args.profile)
    commands = load_commands()
    errors = []
    launch_refs = set(commands.get("launches", {}).keys())
    update_refs = set(commands.get("updates", {}).keys())
    exit_refs = set(commands.get("exit_policies", {}).keys())
    ids = set()
    for item in flatten_services(profile):
        svc = item["service"]
        sid = svc.get("id")
        if not sid:
            errors.append("service missing id")
        elif sid in ids:
            errors.append(f"duplicate service id: {sid}")
        ids.add(sid)
        for field in ("surface_title_hint", "index_in_pane", "agent_harness", "model_slot", "role"):
            if field not in svc:
                errors.append(f"{sid}: missing {field}")
        if svc.get("launch_ref") and svc.get("launch_ref") not in launch_refs:
            errors.append(f"{sid}: unknown launch_ref {svc.get('launch_ref')}")
        if svc.get("update_ref") and svc.get("update_ref") not in update_refs:
            errors.append(f"{sid}: unknown update_ref {svc.get('update_ref')}")
        if svc.get("exit_policy_ref") and svc.get("exit_policy_ref") not in exit_refs:
            errors.append(f"{sid}: unknown exit_policy_ref {svc.get('exit_policy_ref')}")
    result = {"profile": args.profile, "service_count": len(ids), "errors": errors}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if errors else 0


def render_dry_run(profile_name, workspace_filter=None):
    profile = load_profile(profile_name)
    commands = load_commands()
    tree = cmux_tree()
    top = cmux_top()
    live_rows = flatten_cmux(tree)
    services = flatten_services(profile)
    if workspace_filter:
        services = [s for s in services if s["workspace"].get("name") == workspace_filter]
    update_refs = []
    matches = []
    missing = []
    needs_review = []
    for item in services:
        ws = item["workspace"]
        pane = item["pane"]
        svc = item["service"]
        if svc.get("update_ref") and svc["update_ref"] not in update_refs:
            update_refs.append(svc["update_ref"])
        surface = match_surface(live_rows, ws.get("name"), pane.get("index"), svc)
        if not surface:
            missing.append(svc)
            continue
        procs = top["surface_processes"].get(surface["surface_ref"], [])
        matches.append((ws, pane, svc, surface, procs))
        if svc.get("needs_review"):
            needs_review.append(svc)

    print(f"# Martin Agent Roster Dry Run\n")
    print(f"- profile: `{profile_name}`")
    print(f"- authority: `guarded`")
    print(f"- workspace filter: `{workspace_filter or 'all'}`")
    print(f"- live control: `disabled`\n")
    print("## Update Plan\n")
    for ref in update_refs:
        meta = commands["updates"].get(ref, {})
        print(f"- `{ref}`: `{meta.get('command')}`")
        if meta.get("fallback"):
            print(f"  fallback: `{meta['fallback']}`")
    print("\n## Startup Plan\n")
    for ws, pane, svc, surface, procs in matches:
        launch_ref = svc.get("launch_ref")
        launch = commands.get("launches", {}).get(launch_ref, {}) if launch_ref else {}
        state = "idle-shell" if procs == ["zsh"] else ("empty" if not procs else "has-process:" + ",".join(procs))
        print(
            f"- `{svc['id']}` on `{ws['name']}` `{surface['surface_ref']}` "
            f"title=`{surface['surface_title']}` state=`{state}`"
        )
        if launch_ref:
            print(f"  launch: `{launch.get('command')}`")
        if svc.get("post_launch") or launch.get("post_launch"):
            print(f"  post_launch: {svc.get('post_launch') or launch.get('post_launch')}")
        if svc.get("needs_review"):
            print("  needs_review: true")
    if missing:
        print("\n## Missing Services\n")
        for svc in missing:
            print(f"- `{svc.get('id')}` title_hint=`{svc.get('surface_title_hint')}`")
    extra = []
    matched_refs = {surface["surface_ref"] for _, _, _, surface, _ in matches}
    for row in live_rows:
        if workspace_filter and row["workspace_title"] != workspace_filter:
            continue
        if row["surface_ref"] not in matched_refs:
            extra.append(row)
    if extra:
        print("\n## Extra Live Surfaces\n")
        for row in extra:
            print(f"- `{row['workspace_title']}` `{row['surface_ref']}` title=`{row['surface_title']}`")
    if needs_review:
        print("\n## Needs Review\n")
        for svc in needs_review:
            print(f"- `{svc['id']}`: {svc.get('surface_title_hint')} / {svc.get('model_slot')}")
    print("\n## Guarded Mode Result\n")
    print("No update, launch, exit, rescue, or restart commands were executed.")
    return 0


def inspect_cmux(args):
    rows = flatten_cmux(cmux_tree())
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect-profile")
    v = sub.add_parser("validate-roster")
    v.add_argument("--profile", default="macos-cmux")
    i = sub.add_parser("inspect-cmux")
    d = sub.add_parser("dry-run")
    d.add_argument("--profile", default="macos-cmux")
    d.add_argument("--workspace", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "detect-profile":
        return detect_profile(args)
    if args.cmd == "validate-roster":
        return validate_roster(args)
    if args.cmd == "inspect-cmux":
        return inspect_cmux(args)
    if args.cmd == "dry-run":
        return render_dry_run(args.profile, args.workspace)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

