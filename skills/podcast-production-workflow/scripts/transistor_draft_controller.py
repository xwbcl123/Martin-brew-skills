#!/usr/bin/env python3
"""Create one hash-approved Transistor draft from an accepted episode package.

This controller never publishes or schedules. Unsafe upload/create operations are
never retried. A durable attempt lock is written before the first mutation; an
interrupted attempt must be reconciled by read-only provider inspection.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
APPROVAL_SCHEMA = ROOT / "references/transistor-draft-approval.schema.json"
RELEASE_SKILL = ROOT.parent / "podcast-release-package"
VALIDATOR = RELEASE_SKILL / "scripts/validate_release_package.py"


class DraftError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DraftError("INVALID_JSON", f"Cannot read valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DraftError("INVALID_JSON", f"Expected object: {path}")
    return value


def within_package(root: pathlib.Path, relative: str) -> pathlib.Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise DraftError("PATH_ESCAPE", f"Package path escapes root: {relative}") from exc
    if not candidate.is_file():
        raise DraftError("ARTIFACT_MISSING", f"Package artifact missing: {candidate}")
    return candidate


def local_contract(manifest_path: pathlib.Path, report_path: pathlib.Path) -> dict[str, Any]:
    manifest = read_json(manifest_path); report = read_json(report_path)
    deny_agent_draft(manifest, report)
    if not report.get("contract_passed") or not report.get("human_preview_ready") or not report.get("growth_ready"):
        raise DraftError("PACKAGE_NOT_ACCEPTED", "Acceptance report must be contract-passed, preview-ready, and growth-ready")
    if report.get("publish_authorized") is not False:
        raise DraftError("INVALID_PUBLISH_BOUNDARY", "Acceptance report must keep publish_authorized=false")
    gates = report.get("gates")
    prefixes = {str(item.get("id", ""))[:3] for item in gates} if isinstance(gates, list) else set()
    if (not isinstance(gates, list) or len(gates) != 12 or any(item.get("status") != "passed" for item in gates)
            or prefixes != {f"G{index:02d}" for index in range(1, 13)}):
        raise DraftError("PACKAGE_GATES_NOT_PASSED", "All unique G01-G12 release gates must pass")
    manifest_sha = sha256(manifest_path)
    if report.get("manifest_sha256") != manifest_sha:
        raise DraftError("MANIFEST_HASH_MISMATCH", "Acceptance report does not bind the live manifest")
    root = manifest_path.parent
    release = within_package(root, manifest["media"]["release_audio"])
    release_sha = sha256(release)
    if release_sha != manifest["media"]["release_audio_sha256"] or release_sha != report.get("release_audio_sha256"):
        raise DraftError("RELEASE_AUDIO_HASH_MISMATCH", "Manifest/report do not bind the live release MP3")
    payload_sha = manifest["approvals"]["release_candidate"]["payload_sha256"]
    if payload_sha != report.get("release_candidate_payload_sha256"):
        raise DraftError("PAYLOAD_HASH_MISMATCH", "Release-candidate payload hash mismatch")
    if manifest["provider"].get("name") != "transistor" or not str(manifest["provider"].get("show_id") or ""):
        raise DraftError("PROVIDER_INVALID", "Accepted package must declare a Transistor show_id")
    if manifest["provider"].get("episode_id") not in {None, ""}:
        raise DraftError("REMOTE_EPISODE_ALREADY_BOUND", "Manifest already binds a provider episode_id; refusing create")
    summary = within_package(root, manifest["episode"]["summary_file"])
    description = within_package(root, manifest["episode"]["description_file"])
    transcript = within_package(root, manifest["transcript"]["text_file"])
    identities = {str(manifest_path.resolve()): manifest_sha, str(report_path.resolve()): sha256(report_path),
                  str(release): release_sha,
                  str(summary): manifest["episode"]["summary_sha256"],
                  str(description): manifest["episode"]["description_sha256"],
                  str(transcript): manifest["transcript"]["text_sha256"]}
    verify_identities(identities)
    return {"manifest": manifest, "report": report, "manifest_sha256": manifest_sha,
            "acceptance_report_sha256": sha256(report_path), "release_audio": release,
            "release_audio_sha256": release_sha, "payload_sha256": payload_sha,
            "summary": summary, "description": description, "transcript": transcript,
            "input_identities": identities}


def verify_identities(identities: dict[str, str]) -> None:
    for name, expected in identities.items():
        if sha256(pathlib.Path(name)) != expected:
            raise DraftError("PAYLOAD_CHANGED_BEFORE_MUTATION", f"Live payload identity changed: {name}")


def deny_agent_draft(manifest: dict[str, Any], report: dict[str, Any]) -> None:
    for record in (manifest, report):
        if (record.get("review_mode", "human") != "human"
                or str(record.get("schema_version", "")).startswith("agent-draft")
                or str(record.get("contract_version", "")).startswith("agent-draft")):
            raise DraftError("AGENT_DRAFT_EXTERNAL_MUTATION_DENIED", "Local agent drafts cannot enter the distribution adapter")


def validate_approval(path: pathlib.Path, context: dict[str, Any]) -> dict[str, Any]:
    import jsonschema
    approval = read_json(path)
    jsonschema.validate(approval, read_json(APPROVAL_SCHEMA))
    manifest = context["manifest"]
    expected = {
        "episode_key": manifest["episode_key"],
        "show_id": str(manifest["provider"]["show_id"]),
        "acceptance_report_sha256": context["acceptance_report_sha256"],
        "manifest_sha256": context["manifest_sha256"],
        "release_candidate_payload_sha256": context["payload_sha256"],
        "release_audio_sha256": context["release_audio_sha256"],
    }
    mismatch = {key: {"expected": value, "actual": approval.get(key)} for key, value in expected.items()
                if approval.get(key) != value}
    if mismatch:
        raise DraftError("UPLOAD_APPROVAL_HASH_MISMATCH", json.dumps(mismatch, sort_keys=True))
    timestamp = dt.datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise DraftError("UPLOAD_APPROVAL_TIME_INVALID", "Approval timestamp must include timezone")
    return approval


def fresh_validate(manifest: pathlib.Path, supplied_report: pathlib.Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        fresh = pathlib.Path(directory) / "acceptance-report.json"
        result = subprocess.run([os.fspath(pathlib.Path(os.sys.executable)), os.fspath(VALIDATOR),
                                 "--manifest", os.fspath(manifest), "--report", os.fspath(fresh)],
                                capture_output=True, text=True)
        if result.returncode != 0 or not fresh.is_file():
            raise DraftError("FRESH_PACKAGE_VALIDATION_FAILED", result.stderr or result.stdout)
        supplied = read_json(supplied_report); current = read_json(fresh)
        for key in ("contract_passed", "human_preview_ready", "growth_ready", "manifest_sha256",
                    "release_candidate_payload_sha256", "release_audio_sha256"):
            if supplied.get(key) != current.get(key):
                raise DraftError("STALE_ACCEPTANCE_REPORT", f"Fresh validator differs at {key}")


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise DraftError("TRANSISTOR_CLI_FAILED", f"exit={result.returncode}; stderr={result.stderr.strip()}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DraftError("TRANSISTOR_OUTPUT_INVALID", "CLI stdout was not JSON") from exc
    if not isinstance(value, dict):
        raise DraftError("TRANSISTOR_OUTPUT_INVALID", "CLI output must be an object")
    return value


def resource_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    data = document.get("data", [])
    if isinstance(data, dict): return [data]
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def episode_id(document: dict[str, Any]) -> str:
    items = resource_items(document)
    if len(items) != 1 or not str(items[0].get("id") or ""):
        raise DraftError("CREATE_RESPONSE_INVALID", "Draft create did not return one episode ID")
    return str(items[0]["id"])


def episode_attributes(resource: dict[str, Any]) -> dict[str, Any]:
    value = resource.get("attributes", {})
    return value if isinstance(value, dict) else {}


def create_arguments(binary: str, context: dict[str, Any], audio_url: str, dry_run: bool) -> list[str]:
    manifest = context["manifest"]; episode = manifest["episode"]
    fields: list[tuple[str, object]] = [
        ("title", episode["title"]), ("author", episode["author"]),
        ("summary", context["summary"].read_text(encoding="utf-8")),
        ("description", context["description"].read_text(encoding="utf-8")),
        ("explicit", episode["explicit"]), ("type", episode["type"]),
        ("season", episode["season"]), ("number", episode["number"]),
        ("transcript_text", context["transcript"].read_text(encoding="utf-8")),
        ("audio_url", audio_url),
    ]
    command = [binary, "episodes", "create", "--show-id", str(manifest["provider"]["show_id"])]
    for key, value in fields:
        command.extend(["--set", f"{key}={str(value).lower() if isinstance(value, bool) else value}"])
    if dry_run: command.append("--dry-run")
    return command


def execute(context: dict[str, Any], approval: dict[str, Any], *, binary: str,
            receipt: pathlib.Path, attempt: pathlib.Path,
            runner: Callable[[list[str]], dict[str, Any]] = run_json) -> dict[str, Any]:
    deny_agent_draft(context["manifest"], context.get("report", {}))
    if receipt.resolve() == attempt.resolve():
        raise DraftError("OUTPUT_PATH_COLLISION", "Attempt and receipt must have distinct resolved paths")
    identities = context["input_identities"]
    if any(str(output.resolve()) in identities for output in (receipt, attempt)):
        raise DraftError("OUTPUT_PATH_COLLISION", "Attempt/receipt cannot overwrite an input")
    verify_identities(identities)
    # Private snapshots isolate provider argv/file reads from ordinary concurrent
    # edits of source paths. Not a defense against a hostile same-user process.
    with tempfile.TemporaryDirectory(prefix="podcast-upload-snapshot-") as directory:
        frozen = dict(context)
        snapshot_identities = {}
        for role in ("release_audio", "summary", "description", "transcript"):
            original = context[role].resolve()
            target = pathlib.Path(directory) / (role + original.suffix)
            shutil.copyfile(original, target)
            target.chmod(0o400)
            snapshot_identities[str(target)] = identities[str(original)]
            frozen[role] = target
        verify_identities(snapshot_identities)
        frozen["snapshot_identities"] = snapshot_identities
        return _execute_snapshot(frozen, approval, binary=binary, receipt=receipt, attempt=attempt, runner=runner)


def _execute_snapshot(context: dict[str, Any], approval: dict[str, Any], *, binary: str,
                      receipt: pathlib.Path, attempt: pathlib.Path,
                      runner: Callable[[list[str]], dict[str, Any]]) -> dict[str, Any]:
    if receipt.exists():
        raise DraftError("DRAFT_ALREADY_RECEIPTED", f"Refusing duplicate mutation: {receipt}")
    if attempt.exists():
        raise DraftError("AMBIGUOUS_PRIOR_ATTEMPT", f"Reconcile provider state before retry: {attempt}")
    manifest = context["manifest"]; title = manifest["episode"]["title"]; show_id = str(manifest["provider"]["show_id"])
    duplicate_doc = runner([binary, "episodes", "list", "--show-id", show_id, "--all-pages"])
    duplicates = [str(item.get("id")) for item in resource_items(duplicate_doc)
                  if episode_attributes(item).get("title") == title]
    if duplicates:
        raise DraftError("DUPLICATE_REMOTE_EPISODE", f"Exact-title remote episode(s): {', '.join(duplicates)}")
    # Probe latency is unbounded: refresh identities after it, before durable
    # attempt state or the first external mutation. Upload only frozen copies.
    verify_identities(context["input_identities"])
    verify_identities(context["snapshot_identities"])
    state = {"schema_version": "1.0", "status": "mutation_started_reconcile_before_retry",
             "episode_key": manifest["episode_key"], "show_id": show_id, "title": title,
             "manifest_sha256": context["manifest_sha256"], "release_audio_sha256": context["release_audio_sha256"],
             "approval_sha256": canonical_sha(approval), "publish_authorized": False}
    atomic_json(attempt, state)
    upload = runner([binary, "episodes", "upload", os.fspath(context["release_audio"])])
    audio_url = upload.get("audio_url")
    if not isinstance(audio_url, str) or not audio_url.startswith("https://"):
        raise DraftError("UPLOAD_RESPONSE_INVALID", "Integrated upload returned no safe public audio_url")
    state.update({"status": "audio_uploaded_create_pending", "upload_response_sha256": canonical_sha(upload),
                  "audio_url_sha256": hashlib.sha256(audio_url.encode()).hexdigest()}); atomic_json(attempt, state)
    dry = runner(create_arguments(binary, context, audio_url, True))
    state.update({"status": "create_dry_run_passed", "create_dry_run_sha256": canonical_sha(dry)}); atomic_json(attempt, state)
    created = runner(create_arguments(binary, context, audio_url, False)); remote_id = episode_id(created)
    state.update({"status": "draft_created_readback_pending", "remote_episode_id": remote_id,
                  "create_response_sha256": canonical_sha(created)}); atomic_json(attempt, state)
    readback = runner([binary, "episodes", "get", remote_id, "--include", "show"])
    item = resource_items(readback)
    if len(item) != 1:
        raise DraftError("READBACK_INVALID", "Provider readback did not return exactly one episode")
    attrs = episode_attributes(item[0])
    if attrs.get("title") != title or attrs.get("status") != "draft":
        raise DraftError("READBACK_MISMATCH", f"Expected exact title and draft status; got {attrs.get('title')!r}/{attrs.get('status')!r}")
    final = {"schema_version": "1.0", "status": "draft_created_and_verified", "episode_key": manifest["episode_key"],
             "show_id": show_id, "remote_episode_id": remote_id, "remote_status": "draft", "title": title,
             "manifest_sha256": context["manifest_sha256"], "acceptance_report_sha256": context["acceptance_report_sha256"],
             "release_candidate_payload_sha256": context["payload_sha256"], "release_audio_sha256": context["release_audio_sha256"],
             "upload_approval_sha256": canonical_sha(approval), "readback_response_sha256": canonical_sha(readback),
             "presigned_url_persisted": False, "publish_authorized": False}
    atomic_json(receipt, final); state.update({"status": "completed", "receipt_sha256": sha256(receipt)}); atomic_json(attempt, state)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--acceptance-report", type=pathlib.Path, required=True)
    parser.add_argument("--approval", type=pathlib.Path)
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--attempt", type=pathlib.Path)
    parser.add_argument("--transistor-bin", default="transistor")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        context = local_contract(args.manifest, args.acceptance_report)
        result: dict[str, Any] = {"status": "local_package_verified_h6_required", "episode_key": context["manifest"]["episode_key"],
            "show_id": str(context["manifest"]["provider"]["show_id"]), "manifest_sha256": context["manifest_sha256"],
            "acceptance_report_sha256": context["acceptance_report_sha256"], "release_audio_sha256": context["release_audio_sha256"],
            "release_candidate_payload_sha256": context["payload_sha256"], "publish_authorized": False}
        if args.execute:
            if not args.approval or not args.receipt:
                raise DraftError("EXECUTE_ARGS_REQUIRED", "--approval and --receipt are required with --execute")
            fresh_validate(args.manifest, args.acceptance_report)
            approval = validate_approval(args.approval, context)
            attempt = args.attempt or args.receipt.with_name(args.receipt.stem + "-attempt.json")
            result = execute(context, approval, binary=args.transistor_bin, receipt=args.receipt, attempt=attempt)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)); return 0
    except (DraftError, KeyError, TypeError) as exc:
        code = exc.code if isinstance(exc, DraftError) else "PACKAGE_STRUCTURE_INVALID"
        print(json.dumps({"ok": False, "error": {"code": code, "message": str(exc)}, "publish_authorized": False}, ensure_ascii=False), file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
