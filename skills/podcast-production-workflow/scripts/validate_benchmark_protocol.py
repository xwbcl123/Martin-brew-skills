#!/usr/bin/env python3
"""Validate a frozen H1 protocol, live hashes, alignment gates and unopened labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/benchmark-protocol.schema.json"



# BEGIN podcast-config (byte-identical in every consumer; guarded by podcast-release-package/scripts/test_config_copies.py)
def _podcast_cfg(_cache={}):
    """Personal defaults from $PODCAST_CONFIG or ~/.config/podcast-skills/config.json. Read lazily, once; never grants approval/authorization."""
    import json, os, re
    from pathlib import Path
    keys = {'workspace', 'whisper_cli', 'whisper_model', 'transistor_cli', 'transistor_cli_repo',
            'language', 'approver', 'artwork_registry', 'planning_profiles_dir'}
    plain = {'language', 'approver'}
    explicit = os.environ.get('PODCAST_CONFIG')
    if explicit is not None:
        if not explicit.strip() or not Path(explicit).expanduser().is_absolute():
            raise SystemExit('PODCAST_CONFIG must be a non-empty absolute path (unset it to use ~/.config/podcast-skills/config.json)')
        path = Path(explicit).expanduser()
    else:
        path = Path.home() / '.config' / 'podcast-skills' / 'config.json'
    if str(path) in _cache:
        return _cache[str(path)]
    if explicit is not None and not path.is_file():
        raise SystemExit(f'PODCAST_CONFIG points to a missing file: {path}')
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise SystemExit(f'invalid JSON in {path}: {exc}')
    if not isinstance(data, dict):
        raise SystemExit(f'{path}: top level must be an object')
    extra = sorted(set(data) - keys - {'shows'})
    if extra:
        raise SystemExit(f'{path}: unknown keys {extra}')
    for key in keys & set(data):
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f'{path}: {key} must be a non-empty string')
        if key not in plain and not Path(value).expanduser().is_absolute():
            raise SystemExit(f'{path}: {key} must be an absolute path')
    shows = data.setdefault('shows', {})
    if not isinstance(shows, dict):
        raise SystemExit(f'{path}: shows must be an object keyed by show id')
    for sid, entry in shows.items():
        if not re.fullmatch(r'[0-9]+', str(sid)) or not isinstance(entry, dict) or set(entry) - {'author', 'brand_name', 'brand_tagline'}:
            raise SystemExit(f'{path}: shows[{sid!r}] must be an object with only author/brand_name/brand_tagline')
        for field in ('author', 'brand_name'):
            if field in entry and (not isinstance(entry[field], str) or not entry[field].strip()):
                raise SystemExit(f'{path}: shows[{sid!r}].{field} must be a non-empty string')
        if 'brand_tagline' in entry and not isinstance(entry['brand_tagline'], str):
            raise SystemExit(f'{path}: shows[{sid!r}].brand_tagline must be a string')
    _cache[str(path)] = data
    return data


def _podcast_pick(cli, env_name, key):
    """Provided CLI value > provided environment variable > config file > None. A provided-but-blank value is an error, never "unset"."""
    import os
    for source, value in (('command line', cli), (f'${env_name}', os.environ.get(env_name) if env_name else None)):
        if value is not None:
            if not str(value).strip():
                raise SystemExit(f'{key}: empty value from the {source}; omit it to use the default')
            return value
    return _podcast_cfg().get(key)


def _podcast_tool(cli, env_name, key, command):
    """A provided tool path must be an absolute executable file and is used as-is (never re-resolved through PATH); `command` is only looked up when nothing was provided."""
    import os, shutil
    value = _podcast_pick(cli, env_name, key)
    if value is not None:
        value = os.path.expanduser(str(value))
        if not os.path.isabs(value):
            raise SystemExit(f'{key}: {value} must be an absolute path (relative values are never searched on PATH)')
        if not (os.path.isfile(value) and os.access(value, os.X_OK)):
            raise SystemExit(f'{key}: {value} is not an executable file (fix --{key.replace("_", "-")}, ${env_name or "PODCAST_CONFIG"} or the podcast-skills config)')
        return value
    found = shutil.which(command)
    if not found:
        raise SystemExit(f'{command} not found: pass --{key.replace("_", "-")}, set ${env_name or "PODCAST_CONFIG"} or add "{key}" to ~/.config/podcast-skills/config.json')
    return os.path.abspath(found)


def _podcast_model(cli):
    """Whisper model: CLI > $WHISPER_MODEL > config whisper_model > <workspace>/models/ggml-large-v3-q5_0.bin."""
    import os
    value = _podcast_pick(cli, 'WHISPER_MODEL', 'whisper_model')
    if value is None:
        workspace = _podcast_pick(None, 'PODCAST_WORKSPACE', 'workspace')
        if workspace is None:
            raise SystemExit('no Whisper model: pass --model, set $WHISPER_MODEL, or add whisper_model/workspace to ~/.config/podcast-skills/config.json')
        workspace = os.path.expanduser(str(workspace))
        if not os.path.isabs(workspace):
            raise SystemExit(f'workspace: {workspace} must be an absolute path')
        value = os.path.join(workspace, 'models', 'ggml-large-v3-q5_0.bin')
    value = os.path.expanduser(str(value))
    if not os.path.isabs(value):
        raise SystemExit(f'whisper_model: {value} must be an absolute path')
    if not os.path.isfile(value):
        raise SystemExit(f'Whisper model does not exist: {value}')
    return value
# END podcast-config


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n")
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--approval", type=pathlib.Path)
    parser.add_argument("--expected-approver", help="Name that approved_by must equal (default: config approver). Required when --approval is given.")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(protocol)]
    artifacts = []
    for role, artifact in protocol.get("frozen_artifacts", {}).items():
        path = pathlib.Path(artifact["path"])
        actual = sha256(path) if path.is_file() else None
        artifacts.append({"role": role, "path": str(path), "expected_sha256": artifact["sha256"],
                          "actual_sha256": actual, "verified": actual == artifact["sha256"]})
    alignment_path = pathlib.Path(protocol["frozen_artifacts"]["filmora_alignment"]["path"])
    alignment = json.loads(alignment_path.read_text())
    evidence = alignment["evidence"]; thresholds = protocol["timeline_thresholds"]
    alignment_valid = bool(alignment.get("alignment_valid")
                           and evidence["confident_reference_coverage"] >= thresholds["filmora_confident_coverage_min"]
                           and evidence["anchor_residual_median_ms"] <= thresholds["alignment_residual_median_ms_max"]
                           and evidence["anchor_residual_p95_ms"] <= thresholds["alignment_residual_p95_ms_max"])
    labels_path = pathlib.Path(protocol["labels"]["template_artifact"]["path"])
    labels = json.loads(labels_path.read_text())
    unopened = all(item.get("human_label") is None and item.get("reviewed_by") is None for item in labels["labels"])
    challenge = json.loads(pathlib.Path(protocol["frozen_artifacts"]["challenge_set"]["path"]).read_text())
    challenge_blind = challenge.get("label_blind") is True and challenge.get("filmora_reference_consumed") is False
    approval_valid = False; approval_detail = None
    protocol_sha = sha256(args.protocol)
    if args.approval and args.approval.is_file():
        expected_approver = _podcast_pick(args.expected_approver, None, "approver")
        if not expected_approver:
            raise SystemExit("--approval requires --expected-approver (or an 'approver' entry in the podcast-skills config); refusing to accept an arbitrary approved_by")
        approval_detail = json.loads(args.approval.read_text())
        approval_valid = (approval_detail.get("gate") == "H1-benchmark-protocol"
                          and approval_detail.get("status") == "approved"
                          and approval_detail.get("protocol_sha256") == protocol_sha
                          and approval_detail.get("approved_by") == expected_approver)
    protocol_valid = not errors and all(item["verified"] for item in artifacts) and alignment_valid and unopened and challenge_blind
    report = {"schema_version": "1.0", "protocol_path": str(args.protocol), "protocol_sha256": protocol_sha,
              "schema_valid": not errors, "schema_errors": errors, "artifacts": artifacts,
              "alignment_gate_valid": alignment_valid, "heldout_labels_unopened": unopened,
              "challenge_set_blind": challenge_blind, "protocol_valid": protocol_valid,
              "h1_approval_valid": approval_valid, "approval_detail": approval_detail,
              "external_judge_dispatch_authorized": protocol_valid and approval_valid,
              "publish_authorized": False}
    atomic_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["external_judge_dispatch_authorized"] else 1)


if __name__ == "__main__":
    main()
