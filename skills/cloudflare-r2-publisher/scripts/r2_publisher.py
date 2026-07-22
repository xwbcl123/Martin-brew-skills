#!/usr/bin/env python3
"""Publish immutable artifact bundles to Cloudflare R2 with lifecycle records."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterable


REQUIRED_ENV = (
    "HERMES_R2_ACCESS_KEY_ID",
    "HERMES_R2_SECRET_ACCESS_KEY",
    "HERMES_R2_BUCKET_NAME",
    "HERMES_R2_ENDPOINT",
    "HERMES_R2_PUBLIC_URL",
)
EVENT_SCHEMA = "hermes-r2-publication-event/v1"
PLAN_SCHEMA = "hermes-r2-cleanup-plan/v1"
MANIFEST_SCHEMA = "hermes-r2-task-manifest/v1"


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now_utc()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(exit_code)


def fail(message: str, **details: Any) -> None:
    emit({"status": "error", "error": message, **details}, 1)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._").lower()
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("value cannot be converted to a safe slug")
    return cleaned[:120]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def discover_root() -> Path:
    override = os.environ.get("LIFE_OS_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if (root / "AGENTS.md").is_file():
            return root
        raise RuntimeError("LIFE_OS_ROOT does not point to a Life-OS root")
    starts = [Path.cwd().resolve(), Path(__file__).resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "AGENTS.md").is_file() and (candidate / ".agents").is_dir():
                return candidate
    raise RuntimeError("cannot discover Life-OS root; set LIFE_OS_ROOT")


def paths(root: Path) -> tuple[Path, Path]:
    base = root / ".automation" / "r2-publisher"
    return base / "publications.jsonl", base / "cleanup-plans"


def append_event(registry: Path, event: dict[str, Any]) -> None:
    registry.parent.mkdir(parents=True, exist_ok=True)
    event = {"schema": EVENT_SCHEMA, "event_at": iso(), **event}
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    with registry.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def read_events(registry: Path) -> list[dict[str, Any]]:
    if not registry.exists():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(registry.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid registry JSON at line {number}: {exc}") from exc
        if event.get("schema") != EVENT_SCHEMA:
            raise RuntimeError(f"unexpected registry schema at line {number}")
        events.append(event)
    return events


def registry_hash(registry: Path) -> str:
    return sha256_file(registry) if registry.exists() else sha256_bytes(b"")


def current_state(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for event in events:
        publication_id = event.get("publication_id")
        if not publication_id:
            continue
        action = event.get("event")
        if action == "published":
            state[publication_id] = dict(event["publication"])
            state[publication_id]["lifecycle"] = "active"
        elif publication_id in state and action == "pinned":
            state[publication_id]["pinned"] = True
        elif publication_id in state and action == "unpinned":
            state[publication_id]["pinned"] = False
        elif publication_id in state and action == "deleted":
            state[publication_id]["lifecycle"] = "deleted"
            state[publication_id]["deleted_at"] = event.get("event_at")
    return state


def load_env_file() -> None:
    home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    env_path = Path(home) / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in REQUIRED_ENV or key in {"HERMES_R2_UPLOAD_PREFIX", "LIFE_OS_ROOT"}:
            os.environ.setdefault(key, value.strip().strip("'\""))


def config(require: bool = True) -> dict[str, str]:
    load_env_file()
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing and require:
        raise RuntimeError("missing R2 environment variables: " + ", ".join(missing))
    return {
        "access_key": os.environ.get("HERMES_R2_ACCESS_KEY_ID", ""),
        "secret_key": os.environ.get("HERMES_R2_SECRET_ACCESS_KEY", ""),
        "bucket": os.environ.get("HERMES_R2_BUCKET_NAME", ""),
        "endpoint": os.environ.get("HERMES_R2_ENDPOINT", "").rstrip("/"),
        "public_url": os.environ.get("HERMES_R2_PUBLIC_URL", "").rstrip("/"),
        "prefix": os.environ.get("HERMES_R2_UPLOAD_PREFIX", "deep-research").strip("/"),
    }


def client(cfg: dict[str, str]):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("boto3 and botocore are required in the Hermes venv") from exc
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    value = guessed or "application/octet-stream"
    if value in {"text/html", "text/css", "application/javascript", "application/json", "image/svg+xml"}:
        value += "; charset=utf-8"
    return value


def source_files(source: Path) -> tuple[list[tuple[Path, str]], str]:
    source = source.resolve()
    if not source.exists():
        raise RuntimeError(f"source does not exist: {source}")
    if source.is_symlink():
        raise RuntimeError("source symlinks are not allowed")
    forbidden_names = {".env", "auth.json", "credentials.json", "service-account.json", "id_rsa", "id_ed25519"}
    forbidden_suffixes = {".pem", ".key", ".p12", ".pfx"}
    if source.is_file():
        if source.name.lower() in forbidden_names or source.suffix.lower() in forbidden_suffixes:
            raise RuntimeError("refusing to publish a credential-like file")
        name = "index.html" if source.suffix.lower() in {".html", ".htm"} else slug(source.name)
        return [(source, name)], name
    if not source.is_dir():
        raise RuntimeError("source must be a regular file or directory")
    items: list[tuple[Path, str]] = []
    for item in sorted(source.rglob("*")):
        if item.is_symlink():
            raise RuntimeError(f"bundle contains symlink: {item}")
        if item.is_file():
            relative = item.relative_to(source).as_posix()
            if any(part.startswith(".") for part in Path(relative).parts):
                continue
            if item.name.lower() in forbidden_names or item.suffix.lower() in forbidden_suffixes:
                raise RuntimeError(f"bundle contains credential-like file: {relative}")
            items.append((item, relative))
    if not items:
        raise RuntimeError("source directory contains no regular files")
    names = {relative for _, relative in items}
    entrypoint = "index.html" if "index.html" in names else items[0][1]
    html_count = sum(name == "index.html" for name in names)
    if html_count > 1:
        raise RuntimeError("bundle must contain only one root index.html")
    return items, entrypoint


def aggregate_digest(files: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        [{"relative_path": f["relative_path"], "sha256": f["sha256"], "bytes": f["bytes"]} for f in files],
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256_bytes(canonical)


def public_readback(url: str, expected_size: int, attempts: int = 5) -> dict[str, Any]:
    last_error = ""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, method="GET", headers={"User-Agent": "Hermes-R2-Publisher/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read()
                if response.status == 200 and len(data) == expected_size:
                    return {"status": response.status, "bytes": len(data), "verified": True}
                last_error = f"HTTP {response.status}, bytes {len(data)} expected {expected_size}"
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"public readback failed: {last_error}")


def update_task_manifest(package_dir: Path | None, publication: dict[str, Any]) -> str | None:
    if package_dir is None:
        return None
    package = package_dir.expanduser().resolve()
    if not package.is_dir():
        raise RuntimeError(f"package directory does not exist: {package}")
    path = package / "publish-manifest.json"
    payload: dict[str, Any] = {"schema": MANIFEST_SCHEMA, "task_id": publication["task_id"], "latest": None, "publications": []}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != MANIFEST_SCHEMA:
            raise RuntimeError("unexpected task publish manifest schema")
    existing = {item["publication_id"] for item in payload.get("publications", [])}
    if publication["publication_id"] not in existing:
        payload.setdefault("publications", []).append(publication)
    payload["latest"] = publication["publication_id"]
    payload["updated_at"] = iso()
    atomic_json(path, payload)
    return str(path)


def mark_task_deleted(manifest_path: str | None, publication_id: str) -> None:
    if not manifest_path:
        return
    path = Path(manifest_path)
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload.get("publications", []):
        if item.get("publication_id") == publication_id:
            item["lifecycle"] = "deleted"
            item["deleted_at"] = iso()
    active = [item for item in payload.get("publications", []) if item.get("lifecycle", "active") == "active"]
    payload["latest"] = active[-1]["publication_id"] if active else None
    payload["updated_at"] = iso()
    atomic_json(path, payload)


def mark_task_pinned(manifest_path: str | None, publication_id: str, pinned: bool) -> None:
    if not manifest_path:
        return
    path = Path(manifest_path)
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload.get("publications", []):
        if item.get("publication_id") == publication_id:
            item["pinned"] = pinned
    payload["updated_at"] = iso()
    atomic_json(path, payload)


def find_publication(state: dict[str, dict[str, Any]], target: str) -> tuple[str, dict[str, Any]]:
    if target in state:
        return target, state[target]
    matches = [(key, value) for key, value in state.items() if value.get("public_url") == target]
    if len(matches) != 1:
        raise RuntimeError("target must match exactly one publication ID or immutable URL")
    return matches[0]


def remote_inventory(s3, cfg: dict[str, str]) -> dict[str, Any]:
    objects: dict[str, int] = {}
    token: str | None = None
    while True:
        request: dict[str, Any] = {"Bucket": cfg["bucket"], "Prefix": cfg["prefix"] + "/"}
        if token:
            request["ContinuationToken"] = token
        response = s3.list_objects_v2(**request)
        for item in response.get("Contents", []):
            objects[item["Key"]] = int(item.get("Size", 0))
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
        if not token:
            raise RuntimeError("R2 inventory pagination did not return a continuation token")
    return {"objects": objects, "object_count": len(objects), "bytes": sum(objects.values())}


def cmd_preflight(args: argparse.Namespace) -> None:
    cfg = config(require=True)
    root = discover_root()
    registry, plans = paths(root)
    result: dict[str, Any] = {
        "status": "configured",
        "bucket": cfg["bucket"],
        "public_url": cfg["public_url"],
        "upload_prefix": cfg["prefix"],
        "registry": str(registry),
        "cleanup_plans": str(plans),
        "remote_verified": False,
    }
    if args.remote:
        response = client(cfg).head_bucket(Bucket=cfg["bucket"])
        result["remote_verified"] = response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200
    emit(result)


def cmd_publish(args: argparse.Namespace) -> None:
    cfg = config(require=True)
    root = discover_root()
    registry, _ = paths(root)
    source = Path(args.source).expanduser()
    files, entrypoint = source_files(source)
    records = [
        {
            "path": str(path.resolve()),
            "relative_path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "content_type": content_type(path),
        }
        for path, relative in files
    ]
    digest = aggregate_digest(records)
    timestamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    version = f"v{timestamp}-{digest[:10]}-{uuid.uuid4().hex[:6]}"
    task_id = slug(args.task_id)
    publication_id = f"{task_id}:{version}"
    prefix = "/".join(part for part in (cfg["prefix"], task_id, version) if part)
    for record in records:
        record["object_key"] = f"{prefix}/{record['relative_path']}"
        record["public_url"] = f"{cfg['public_url']}/{record['object_key']}"
    s3 = client(cfg)
    uploaded: list[str] = []
    registry_published = False
    publication: dict[str, Any] | None = None
    try:
        for record in records:
            with Path(record["path"]).open("rb") as handle:
                s3.put_object(
                    Bucket=cfg["bucket"],
                    Key=record["object_key"],
                    Body=handle,
                    ContentType=record["content_type"],
                    CacheControl="public, max-age=31536000, immutable",
                    Metadata={"sha256": record["sha256"], "publication-id": publication_id},
                )
            uploaded.append(record["object_key"])
        entry = next(record for record in records if record["relative_path"] == entrypoint)
        readback = public_readback(entry["public_url"], entry["bytes"])
        publication = {
            "publication_id": publication_id,
            "task_id": task_id,
            "version": version,
            "published_at": iso(),
            "lifecycle": "active",
            "pinned": bool(args.pinned),
            "source": str(source.resolve()),
            "package_manifest": None,
            "bucket": cfg["bucket"],
            "object_prefix": prefix,
            "entrypoint": entrypoint,
            "public_url": entry["public_url"],
            "public_base_url": cfg["public_url"],
            "bytes": sum(record["bytes"] for record in records),
            "sha256": digest,
            "objects": records,
            "readback": readback,
        }
        package_dir = Path(args.package_dir).expanduser().resolve() if args.package_dir else None
        if package_dir is not None:
            if not package_dir.is_dir():
                raise RuntimeError(f"package directory does not exist: {package_dir}")
            publication["package_manifest"] = str(package_dir / "publish-manifest.json")
        append_event(registry, {"event": "published", "publication_id": publication_id, "publication": publication})
        registry_published = True
        update_task_manifest(package_dir, publication)
    except Exception:
        if uploaded:
            try:
                s3.delete_objects(Bucket=cfg["bucket"], Delete={"Objects": [{"Key": key} for key in uploaded], "Quiet": True})
            except Exception:
                pass
        if registry_published:
            try:
                append_event(registry, {"event": "deleted", "publication_id": publication_id, "reason": "publish-rollback", "s3_verified": False})
            except Exception:
                pass
        raise
    assert publication is not None
    emit({"status": "published", "publication_id": publication_id, "version": version, "url": publication["public_url"], "bytes": publication["bytes"], "objects": len(records), "manifest": publication["package_manifest"]})


def lifecycle_event(action: str, target: str) -> None:
    root = discover_root()
    registry, _ = paths(root)
    state = current_state(read_events(registry))
    publication_id, publication = find_publication(state, target)
    if publication.get("lifecycle") != "active":
        raise RuntimeError("publication is not active")
    if action == "pinned" and publication.get("pinned"):
        emit({"status": "unchanged", "publication_id": publication_id, "pinned": True})
    if action == "unpinned" and not publication.get("pinned"):
        emit({"status": "unchanged", "publication_id": publication_id, "pinned": False})
    append_event(registry, {"event": action, "publication_id": publication_id})
    mark_task_pinned(publication.get("package_manifest"), publication_id, action == "pinned")
    emit({"status": action, "publication_id": publication_id, "url": publication["public_url"]})


def delete_publication(publication_id: str, publication: dict[str, Any], reason: str, plan_id: str | None = None) -> dict[str, Any]:
    cfg = config(require=True)
    if cfg["bucket"] != publication.get("bucket"):
        raise RuntimeError("configured Bucket differs from the publication record")
    root = discover_root()
    registry, _ = paths(root)
    s3 = client(cfg)
    keys = [record["object_key"] for record in publication["objects"]]
    if keys:
        response = s3.delete_objects(Bucket=cfg["bucket"], Delete={"Objects": [{"Key": key} for key in keys], "Quiet": False})
        if response.get("Errors"):
            raise RuntimeError(f"R2 delete returned {len(response['Errors'])} object errors")
    remaining: list[str] = []
    for key in keys:
        try:
            s3.head_object(Bucket=cfg["bucket"], Key=key)
            remaining.append(key)
        except Exception as exc:
            status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if status != 404 and code not in {"404", "NoSuchKey", "NotFound"}:
                raise
    if remaining:
        raise RuntimeError(f"S3 deletion verification failed for {len(remaining)} objects")
    append_event(registry, {"event": "deleted", "publication_id": publication_id, "reason": reason, "plan_id": plan_id, "s3_verified": True})
    mark_task_deleted(publication.get("package_manifest"), publication_id)
    return {"publication_id": publication_id, "url": publication["public_url"], "bytes": publication["bytes"], "objects": len(keys), "s3_verified": True}


def cmd_unpublish(args: argparse.Namespace) -> None:
    root = discover_root()
    registry, _ = paths(root)
    state = current_state(read_events(registry))
    publication_id, publication = find_publication(state, args.target)
    if publication.get("lifecycle") != "active":
        raise RuntimeError("publication is not active")
    emit({"status": "deleted", **delete_publication(publication_id, publication, "explicit-unpublish")})


def parse_cutoff(args: argparse.Namespace) -> dt.datetime:
    if args.before:
        return dt.datetime.strptime(args.before, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    months = {"3m": 3, "9m": 9, "1y": 12}[args.age]
    today = now_utc()
    year = today.year
    month = today.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(today.day, 28)
    return today.replace(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)


def cmd_inventory(args: argparse.Namespace) -> None:
    root = discover_root()
    registry, _ = paths(root)
    state = current_state(read_events(registry))
    active = [value for value in state.values() if value.get("lifecycle") == "active"]
    payload = {
        "status": "ok",
        "active_publications": len(active),
        "pinned_publications": sum(bool(value.get("pinned")) for value in active),
        "recorded_bytes": sum(int(value.get("bytes", 0)) for value in active),
        "publications": [{"publication_id": value["publication_id"], "published_at": value["published_at"], "pinned": value.get("pinned", False), "bytes": value["bytes"], "url": value["public_url"]} for value in active],
    }
    if args.remote:
        cfg = config(require=True)
        remote = remote_inventory(client(cfg), cfg)
        recorded_keys = {record["object_key"] for value in active for record in value["objects"]}
        remote_keys = set(remote["objects"])
        payload["remote"] = {
            "object_count": remote["object_count"],
            "bytes": remote["bytes"],
            "untracked_objects": sorted(remote_keys - recorded_keys),
            "missing_recorded_objects": sorted(recorded_keys - remote_keys),
        }
    emit(payload)


def cmd_cleanup_plan(args: argparse.Namespace) -> None:
    root = discover_root()
    registry, plan_dir = paths(root)
    cfg = config(require=True)
    remote = remote_inventory(client(cfg), cfg)
    remote_keys = set(remote["objects"])
    events = read_events(registry)
    state = current_state(events)
    cutoff = parse_cutoff(args)
    candidates: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for publication_id, publication in sorted(state.items()):
        published = dt.datetime.fromisoformat(publication["published_at"].replace("Z", "+00:00"))
        if publication.get("lifecycle") == "active" and not publication.get("pinned") and published < cutoff:
            object_keys = [record["object_key"] for record in publication["objects"]]
            missing = sorted(set(object_keys) - remote_keys)
            if missing:
                exclusions.append({"publication_id": publication_id, "reason": "recorded objects missing from R2", "missing_object_keys": missing})
                continue
            candidates.append({
                "publication_id": publication_id,
                "task_id": publication["task_id"],
                "version": publication["version"],
                "published_at": publication["published_at"],
                "url": publication["public_url"],
                "bytes": publication["bytes"],
                "object_keys": object_keys,
            })
    created = now_utc()
    plan_id = f"cleanup-{created.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    plan = {
        "schema": PLAN_SCHEMA,
        "plan_id": plan_id,
        "status": "pending",
        "created_at": iso(created),
        "expires_at": iso(created + dt.timedelta(hours=24)),
        "cutoff": iso(cutoff),
        "selector": args.age or f"before={args.before}",
        "registry_sha256": registry_hash(registry),
        "remote_inventory": {"object_count": remote["object_count"], "bytes": remote["bytes"]},
        "untracked_object_keys": sorted(remote_keys - {record["object_key"] for value in state.values() if value.get("lifecycle") == "active" for record in value["objects"]}),
        "candidate_count": len(candidates),
        "total_bytes": sum(item["bytes"] for item in candidates),
        "candidates": candidates,
        "exclusions": exclusions,
    }
    path = plan_dir / f"{plan_id}.json"
    atomic_json(path, plan)
    append_event(registry, {"event": "cleanup_planned", "plan_id": plan_id, "cutoff": plan["cutoff"], "candidate_count": len(candidates), "total_bytes": plan["total_bytes"]})
    emit({"status": "dry-run", "plan_id": plan_id, "expires_at": plan["expires_at"], "cutoff": plan["cutoff"], "remote_inventory": plan["remote_inventory"], "untracked_object_keys": plan["untracked_object_keys"], "candidate_count": len(candidates), "total_bytes": plan["total_bytes"], "candidates": candidates, "exclusions": exclusions, "confirm_command": f"cleanup-confirm --plan-id {plan_id}"})


def cmd_cleanup_confirm(args: argparse.Namespace) -> None:
    root = discover_root()
    registry, plan_dir = paths(root)
    path = plan_dir / f"{slug(args.plan_id)}.json"
    if not path.is_file():
        raise RuntimeError("cleanup plan does not exist")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema") != PLAN_SCHEMA or plan.get("plan_id") != args.plan_id:
        raise RuntimeError("invalid cleanup plan")
    if plan.get("status") != "pending":
        raise RuntimeError("cleanup plan is not pending")
    if now_utc() > dt.datetime.fromisoformat(plan["expires_at"].replace("Z", "+00:00")):
        raise RuntimeError("cleanup plan has expired")
    state = current_state(read_events(registry))
    checked: list[tuple[str, dict[str, Any]]] = []
    for candidate in plan["candidates"]:
        publication_id = candidate["publication_id"]
        publication = state.get(publication_id)
        if not publication or publication.get("lifecycle") != "active" or publication.get("pinned"):
            raise RuntimeError(f"cleanup plan is stale for {publication_id}")
        keys = [record["object_key"] for record in publication["objects"]]
        if keys != candidate["object_keys"] or publication.get("bytes") != candidate["bytes"]:
            raise RuntimeError(f"cleanup plan content changed for {publication_id}")
        checked.append((publication_id, publication))
    plan["status"] = "executing"
    plan["execution_started_at"] = iso()
    atomic_json(path, plan)
    deleted: list[dict[str, Any]] = []
    try:
        for publication_id, publication in checked:
            deleted.append(delete_publication(publication_id, publication, "age-cleanup", plan["plan_id"]))
    except Exception as exc:
        plan["status"] = "partial_failure"
        plan["failed_at"] = iso()
        plan["error"] = f"{type(exc).__name__}: {exc}"
        plan["deleted"] = deleted
        atomic_json(path, plan)
        append_event(registry, {"event": "cleanup_failed", "plan_id": plan["plan_id"], "deleted_count": len(deleted), "error_type": type(exc).__name__})
        raise
    plan["status"] = "executed"
    plan["executed_at"] = iso()
    plan["deleted"] = deleted
    atomic_json(path, plan)
    append_event(registry, {"event": "cleanup_executed", "plan_id": plan["plan_id"], "deleted_count": len(deleted), "deleted_bytes": sum(item["bytes"] for item in deleted)})
    emit({"status": "executed", "plan_id": plan["plan_id"], "deleted_count": len(deleted), "deleted_bytes": sum(item["bytes"] for item in deleted), "deleted": deleted})


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--remote", action="store_true")
    preflight.set_defaults(func=cmd_preflight)
    publish = commands.add_parser("publish")
    publish.add_argument("--source", required=True)
    publish.add_argument("--task-id", required=True)
    publish.add_argument("--package-dir")
    publish.add_argument("--pinned", action="store_true")
    publish.set_defaults(func=cmd_publish)
    inventory = commands.add_parser("inventory")
    inventory.add_argument("--remote", action="store_true")
    inventory.set_defaults(func=cmd_inventory)
    for name, action in (("pin", "pinned"), ("unpin", "unpinned")):
        item = commands.add_parser(name)
        item.add_argument("--target", required=True)
        item.set_defaults(func=lambda args, action=action: lifecycle_event(action, args.target))
    unpublish = commands.add_parser("unpublish")
    unpublish.add_argument("--target", required=True)
    unpublish.set_defaults(func=cmd_unpublish)
    cleanup = commands.add_parser("cleanup-plan")
    group = cleanup.add_mutually_exclusive_group(required=True)
    group.add_argument("--age", choices=("3m", "9m", "1y"))
    group.add_argument("--before")
    cleanup.set_defaults(func=cmd_cleanup_plan)
    confirm = commands.add_parser("cleanup-confirm")
    confirm.add_argument("--plan-id", required=True)
    confirm.set_defaults(func=cmd_cleanup_confirm)
    return root


def main() -> None:
    try:
        load_env_file()
        args = parser().parse_args()
        args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        fail(str(exc), error_type=type(exc).__name__)


if __name__ == "__main__":
    main()
