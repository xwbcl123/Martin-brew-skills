#!/usr/bin/env python3
"""Run immutable, content-addressed Whisper raw transcription with atomic promotion."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile


EXTENSIONS = (".txt", ".srt", ".vtt", ".json")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RELEASE_APPROVAL_SCHEMA = ROOT / "references/release-audio-listen-approval.schema.json"


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
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        pathlib.Path(temporary_name).unlink(missing_ok=True)
        raise


def atomic_json(path: pathlib.Path, value: object) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def tool_version(command: pathlib.Path) -> str:
    result = subprocess.run([str(command), "--version"], capture_output=True, text=True)
    text = result.stdout + result.stderr
    match = re.search(r"whisper\.cpp version:\s*([^\s]+)", text)
    return match.group(1) if match else text.strip().splitlines()[-1]


def validate_json(path: pathlib.Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments = data.get("transcription")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Whisper JSON has no transcription segments")
    previous = 0
    for index, segment in enumerate(segments):
        offsets = segment.get("offsets", {})
        start, end = int(offsets.get("from", -1)), int(offsets.get("to", -1))
        if start < previous or end < start:
            raise ValueError(f"non-monotonic segment {index}")
        previous = end
    result = data.get("result", {})
    return {"segment_count": len(segments), "last_offset_ms": previous,
            "detected_language": result.get("language")}


def cache_valid(report: pathlib.Path, run_key: str) -> bool:
    if not report.is_file():
        return False
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("run_key") != run_key:
            return False
        return all(pathlib.Path(item["path"]).is_file() and sha256(pathlib.Path(item["path"])) == item["sha256"]
                   for item in data["outputs"].values())
    except (KeyError, OSError, json.JSONDecodeError):
        return False


def release_approval(path: pathlib.Path | None, audio_sha256: str) -> tuple[dict, str]:
    import jsonschema
    if path is None or not path.is_file():
        raise SystemExit("S11a requires an H3b release-audio approval file")
    value = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(value, json.loads(RELEASE_APPROVAL_SCHEMA.read_text(encoding="utf-8")))
    if value["release_audio_sha256"] != audio_sha256:
        raise SystemExit("H3b approval does not bind the exact release audio SHA-256")
    timestamp = dt.datetime.fromisoformat(value["approved_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise SystemExit("H3b approval timestamp must include timezone")
    return value, canonical_hash(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--analysis-audio", type=pathlib.Path, required=True)
    parser.add_argument("--model", type=pathlib.Path, help="Whisper ggml model (default: $WHISPER_MODEL, config whisper_model, else <workspace>/models/ggml-large-v3-q5_0.bin)")
    parser.add_argument("--output-base", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--language", help="Whisper language code or auto (default: config language, else auto)")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--whisper-cli", type=pathlib.Path, help="whisper-cli executable (default: $WHISPER_CLI, config whisper_cli, else PATH)")
    parser.add_argument("--stage", choices=("S02-whisper-raw", "S11a-postcut-whisper-raw"), default="S02-whisper-raw")
    parser.add_argument("--release-approval", type=pathlib.Path)
    args = parser.parse_args()
    args.model = pathlib.Path(_podcast_model(args.model))
    args.whisper_cli = pathlib.Path(_podcast_tool(args.whisper_cli, "WHISPER_CLI", "whisper_cli", "whisper-cli"))
    args.language = args.language or _podcast_cfg().get("language") or "auto"
    for path, role in ((args.analysis_audio, "analysis audio"), (args.model, "model"), (args.whisper_cli, "whisper-cli")):
        if not path.is_file():
            raise SystemExit(f"{role} missing: {path}")
    version = tool_version(args.whisper_cli)
    audio_sha256 = sha256(args.analysis_audio)
    is_postcut = args.stage == "S11a-postcut-whisper-raw"
    approval_value = None; approval_sha = None
    if is_postcut:
        approval_value, approval_sha = release_approval(args.release_approval, audio_sha256)
    elif args.release_approval is not None:
        raise SystemExit("--release-approval is only valid for S11a-postcut-whisper-raw")
    audio_role = "release_audio" if is_postcut else "analysis_audio"
    identities = {f"{audio_role}_sha256": audio_sha256, "model_sha256": sha256(args.model)}
    invocation = {"language": args.language, "threads": args.threads, "outputs": list(EXTENSIONS),
                  "json_mode": "full", "whisper_cpp_version": version}
    run_identity = {"stage": args.stage, "version": "1.0", **identities, **invocation}
    if approval_sha is not None:
        run_identity["release_approval_sha256"] = approval_sha
    run_key = canonical_hash(run_identity)
    if cache_valid(args.report, run_key):
        report = json.loads(args.report.read_text(encoding="utf-8"))
        print(json.dumps({"status": "skipped_cached", "run_key": run_key, "report": str(args.report),
                          "report_sha256": sha256(args.report), "outputs": report["outputs"],
                          "publish_authorized": False}, ensure_ascii=False, indent=2))
        return
    final_paths = {extension[1:]: pathlib.Path(str(args.output_base) + extension) for extension in EXTENSIONS}
    existing = [str(path) for path in final_paths.values() if path.exists()]
    if existing:
        raise SystemExit(f"immutable raw transcript outputs exist without verified matching report: {existing}")
    args.output_base.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = pathlib.Path(tempfile.mkdtemp(prefix=f".{args.output_base.name}.{run_key[:12]}.", dir=args.output_base.parent))
    temporary_base = temporary_dir / args.output_base.name
    command = [str(args.whisper_cli), "-m", str(args.model), "-f", str(args.analysis_audio),
               "-of", str(temporary_base), "-otxt", "-osrt", "-ovtt", "-ojf",
               "-l", args.language, "-t", str(args.threads)]
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    result = subprocess.run(command, capture_output=True, text=True)
    ended = dt.datetime.now(dt.timezone.utc).isoformat()
    atomic_text(args.log, result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(f"whisper-cli failed with exit {result.returncode}; log={args.log}")
    temporary_paths = {extension[1:]: pathlib.Path(str(temporary_base) + extension) for extension in EXTENSIONS}
    if any(not path.is_file() or path.stat().st_size == 0 for path in temporary_paths.values()):
        raise SystemExit(f"Whisper output missing/empty; log={args.log}")
    validation = validate_json(temporary_paths["json"])
    if not temporary_paths["txt"].read_text(encoding="utf-8").strip():
        raise SystemExit("Whisper TXT is empty")
    for key, temporary in temporary_paths.items():
        os.replace(temporary, final_paths[key])
    temporary_dir.rmdir()
    output_role = "immutable-postcut-raw-whisper" if is_postcut else "immutable-raw-whisper"
    outputs = {key: {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
                     "role": output_role} for key, path in final_paths.items()}
    inputs = {audio_role: {"path": str(args.analysis_audio), "sha256": audio_sha256},
              "model": {"path": str(args.model), "sha256": identities["model_sha256"]}}
    if is_postcut:
        inputs["release_audio_approval"] = {"path": str(args.release_approval), "canonical_sha256": approval_sha,
                                             "approved_by": approval_value["approved_by"], "approved_at": approval_value["approved_at"]}
    report = {"schema_version": "1.0", "episode_id": args.episode_id, "stage": args.stage,
              "status": "succeeded", "run_key": run_key, "inputs": inputs, "tool": {"path": str(args.whisper_cli), "version": version},
              "invocation": invocation, "argv": command, "started_at": started, "ended_at": ended,
              "exit_code": result.returncode, "log": {"path": str(args.log), "sha256": sha256(args.log)},
              "validation": validation, "outputs": outputs, "external_judge_dispatch_authorized": False,
              "publish_authorized": False}
    atomic_json(args.report, report)
    print(json.dumps({"status": "succeeded", "run_key": run_key, "report": str(args.report),
                      "report_sha256": sha256(args.report), "validation": validation, "outputs": outputs,
                      "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
