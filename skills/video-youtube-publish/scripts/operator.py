"""Human-only setup and authority for the private YouTube smoke workflow."""

import argparse
import os
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Isolated Python omits the script directory from its search path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_store import KEY, OPS, PRODUCTION_OPS, OperatorStore, Stop, binding_fields, lock_file, require
from auth_store import safe_private, safe_read, timestamp, validate_auth
from lineage import Lineage, SHA
from production import Production
from package import CHANNEL, PROTECTED, Invalid, atomic_write, canonical, clean_identifier, json_data
from publish import CLI_ROOT, Client, Controller, local_authority_binding, secure_cli_env, settings


def prompt(message):
    return input(message).strip()


def print_json(value):
    print(canonical(value).decode())


def register_channel(profile, *, allow_create=True):
    require(KEY.fullmatch(profile), "invalid_profile")
    path = Path(os.environ.get("VIDEO_SKILLS_CONFIG",
                               str(Path.home() / ".config/video-skills/config.json"))).expanduser().absolute()
    config = path.parent
    safe_private(config, create=allow_create)
    with lock_file(config / "config.lock"):
        current = json_data(safe_read(path)) if path.exists() or path.is_symlink() else {"profiles": {}}
        require(isinstance(current, dict), "invalid_profile_map")
        profiles = current.get("profiles", current)
        require(isinstance(profiles, dict), "invalid_profile_map")
        previous = profiles.get(profile)
        if profile in profiles:
            channel = previous.get("channel_id") if isinstance(previous, dict) else previous
            require(isinstance(channel, str) and CHANNEL.fullmatch(channel), "invalid_existing_channel")
            return channel, path
        require(allow_create, "scope_rebind_requires_registered_channel")
        channel = prompt("Enter the exact intended YouTube channel ID (UC…): ")
        require(CHANNEL.fullmatch(channel), "invalid_smoke_channel_id")
        require(prompt(f"Type {channel} to confirm the target channel: ") == channel,
                "operator_confirmation_missing")
        profiles[profile] = {"channel_id": channel}
        atomic_write(path, canonical(current), exclusive=not path.exists())
        return channel, path


def login(args):
    require(not args.rebind_scopes or args.relogin and args.scope_set == "console-production",
            "scope_rebind_requires_explicit_relogin")
    channel, profile_map = register_channel(args.profile, allow_create=not args.rebind_scopes)
    env = secure_cli_env()
    env["VIDEO_SKILLS_CONFIG"] = str(profile_map)
    backend = args.cache_backend or ("file" if args.profile == "smoke-test" else None)
    command = [str(CLI_ROOT / ".venv/bin/python"), "-I", "-B", "-m", "ytpub.cli",
               "auth", "login", "--profile", args.profile, "--channel-id", channel, "--scope-set", args.scope_set]
    if backend:
        command += ["--cache-backend", backend]
    for option in ("include_upload_scope", "relogin", "rebind_scopes"):
        if getattr(args, option):
            command.append("--" + option.replace("_", "-"))
    return subprocess.run(command, env=env, check=False).returncode


def approve(args, store, registry, state):
    package = args.package.absolute()
    preview = (args.preview or package.parent / "video-release-preview.html").absolute()
    safe_private(package)
    require(preview.parent == package.parent and not preview.is_symlink(), "preview_must_be_local_sibling")
    require(KEY.fullmatch(args.profile), "invalid_profile")
    base = (package, preview, args.profile, Client(CLI_ROOT, args.profile, args.cache_backend),
            store, registry, state, None)
    display = []
    if args.profile == "smoke-test":
        require(args.mode == "publish" and args.video_id is None and args.supersedes_revision is None,
                "private_smoke_policy")
        controller = Controller(*base)
        report, manifest = controller.local()
        require(controller.hash_contract() == report["binding"]["contract_bundle_sha256"],
                "contract_runtime_identity_mismatch")
        binding = local_authority_binding(package, manifest, report, controller.hash_cli(), controller.cli(["doctor"]))
        expected = OPS if binding["playlist_ids"] else OPS - {"add_playlist"}
    else:
        controller = Production(*base)
        if args.supersedes:
            previous, _ = store.load("authorizations", args.supersedes)
            validate_auth(previous)
            require(previous["authorization_version"] == "3.0" and ((args.mode == "update") ==
                    (previous["mode"] == "in_place_update")) and args.supersedes_revision is None and
                    args.video_id in (None, previous["target_video_id"]), "successor_mode_mismatch")
            actual = controller.local_candidate()
            binding = {key: previous[key] for key in binding_fields(previous)}
            binding.update(contract_version=previous["contract_version"], authorization_version="3.0")
            require(all(binding[k] == v for k, v in actual.items() if k != "mode"), "authorization_binding_mismatch")
            controller.binding = binding
            controller.load_episode()
            require(controller.row is not None and controller.row["candidate"] == binding and
                    controller.row["phase"] == "ready", "successor_requires_original_open_job")
            controller.check_plan()
            display = binding["operation_plan"]
        else:
            binding, display = controller.proposal(args.mode, video_id=args.video_id,
                                                  supersedes_revision=args.supersedes_revision)
        expected = {row["operation"] for row in binding["operation_plan"]} | {"readback"}
    operations = set(args.allow) if args.allow else expected
    supersedes = None
    if args.supersedes:
        chain = store.chain(args.supersedes, binding, datetime.now(timezone.utc))
        prior, checksum = chain[-1]
        supersedes = {"authorization_id": args.supersedes, "authorization_sha256": checksum}
        allowed = set(prior["allowed_operations"]) & expected
        operations = set(args.allow) if args.allow else allowed
        require(operations <= allowed, "successor_expands_authority")
    require("readback" in operations and operations <= expected, "invalid_requested_operations")
    require(args.supersedes or operations == expected, "genesis_authorization_requires_all_operations")
    require(0 < args.hours <= 24, "invalid_authorization_expiry")
    authorization_id = "approval-" + secrets.token_hex(12)
    parent = binding.get("parent")
    version = binding.get("authorization_version", "2.0")
    if version == "2.0":
        quote = "Authorize " + authorization_id + " for one private YouTube smoke package."
    else:
        target = binding.get("target_video_id") or (parent["video_id"] if parent else "new-video")
        quote = (f"Authorize {authorization_id} {binding['channel_profile']} {binding['mode']} "
                 f"revision {binding['package_revision']} target {target} plan {binding['plan_sha256']}.")
    print_json({**binding, "allowed_operations": sorted(operations), "review_preview": str(preview),
                "authorization_id": authorization_id, "supersedes": supersedes, "valid_hours": args.hours,
                "reviewed_operations": display, "prior_video_retained": parent["video_id"] if parent else None,
                "request_notifications": binding["notify_subscribers"] if args.mode == "publish" else "not_applicable"})
    require(prompt(f"Review the preview and binding. Type exactly: {quote}\n> ") == quote,
            "operator_confirmation_missing")
    now = datetime.now(timezone.utc)
    value = {**binding, "authorization_version": version, "authorization_id": authorization_id,
             "actor": "user", "source_ref_kind": "operator_terminal", "source_ref": authorization_id,
             "original_user_quote": quote, "authorized_at": timestamp(now),
             "expires_at": timestamp(now + timedelta(hours=args.hours)), "revoked": False,
             "allowed_operations": sorted(operations), "supersedes": supersedes}
    validate_auth(value)
    checksum = store.store("authorizations", authorization_id, value)
    print_json({"authorization_id": authorization_id, "authorization_sha256": checksum,
                "expires_at": value["expires_at"]})
    return 0


DECISIONS = {
    "abandoned_unknown_no_retry", "abandoned_no_effect", "claimed",
    "resume_confirmed_suffix", "accept_observed_thumbnail", "verified_thumbnail_rendition",
}

REVISION_DECISIONS = {"abandon_no_intent", "abandon_proven_none", "abandoned_unknown_no_retry",
                      "abandon_partial_known_effect"}


def record_resolution(source, store):
    resolution = json_data(safe_read(source))
    require(not PROTECTED.search(canonical(resolution).decode()), "credential_like_resolution")
    require(isinstance(resolution, dict), "invalid_resolution_fields")
    common = {"episode_key", "package_revision", "seal_sha256", "target_channel_id", "expected_seq",
              "expected_digest", "decision", "observations"}
    scope = resolution.get("scope")
    structured = {"observations", "confirmed_offset", "expected_seq", "package_revision", "attempts"}
    if scope is None:
        required = common | {"op_key", "attempt_id"}
        optional = {"video_id", "session_handle", "confirmed_offset", "source_sha256", "download_sha256"}
        require(required <= resolution.keys() <= required | optional and resolution["decision"] in DECISIONS,
                "invalid_resolution_fields")
        if resolution["decision"] == "verified_thumbnail_rendition":
            require({"source_sha256", "download_sha256", "video_id"} <= resolution.keys() and
                    all(SHA.fullmatch(resolution[key]) for key in ("source_sha256", "download_sha256")),
                    "invalid_resolution_fields")
    else:
        required = common | {"scope", "genesis_authorization_sha256", "attempts"}
        if scope == "legacy_revision":
            required |= {"legacy_row_sha256", "genesis_entry_sha256", "genesis_authorization_id"}
        require(scope in {"revision", "legacy_revision"} and resolution.keys() == required and
                resolution["decision"] in (REVISION_DECISIONS if scope == "revision" else {"import_abandoned_no_retry"}),
                "invalid_resolution_fields")
        require(isinstance(resolution["attempts"], list) and all(isinstance(row, dict) and
                row.keys() == {"op_key", "attempt_id"} and SHA.fullmatch(row["op_key"]) and
                clean_identifier(row["attempt_id"]) for row in resolution["attempts"]), "invalid_attempt_inventory")
        for key in required & {"legacy_row_sha256", "genesis_entry_sha256", "genesis_authorization_sha256"}:
            require(SHA.fullmatch(resolution[key]), "invalid_resolution_digest")
    require(all(clean_identifier(value) for key, value in resolution.items() if key not in structured),
            "invalid_resolution_value")
    require(isinstance(resolution["observations"], list) and resolution["observations"] and
            all(isinstance(row, dict) and {"source", "evidence_sha256"} <= row.keys() <=
                {"source", "evidence_sha256", "video_id"} and all(clean_identifier(v) for v in row.values())
                for row in resolution["observations"]), "invalid_resolution_observation")
    require(all(type(resolution[key]) is int and resolution[key] >= 0
                for key in structured - {"observations", "attempts"} if key in resolution), "invalid_resolution_number")
    resolution_id = "resolution-" + secrets.token_hex(12)
    value = {**resolution, "resolution_id": resolution_id, "actor": "user"}
    print_json(value)
    require(prompt(f"Type {resolution_id} to attest to these observations: ") == resolution_id,
            "operator_confirmation_missing")
    print_json({"resolution_id": resolution_id, "resolution_sha256": store.store("resolutions", resolution_id, value)})
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    login_parser = sub.add_parser("login", help="Register a channel and open the local Google OAuth approval")
    login_parser.add_argument("--profile", default="smoke-test")
    login_parser.add_argument("--cache-backend", choices=("keychain", "file"))
    login_parser.add_argument("--scope-set", choices=("default", "console-production"), default="default")
    for flag in ("include-upload-scope", "relogin", "rebind-scopes"):
        login_parser.add_argument("--" + flag, action="store_true")
    approval = sub.add_parser("approve", help="Interactively grant authority to a sealed package")
    approval.add_argument("--package", type=Path, required=True)
    approval.add_argument("--preview", type=Path)
    approval.add_argument("--cache-backend", choices=("keychain", "file"))
    approval.add_argument("--profile", default="smoke-test")
    approval.add_argument("--mode", choices=("publish", "update"), default="publish")
    approval.add_argument("--video-id")
    approval.add_argument("--supersedes-revision", type=int)
    approval.add_argument("--allow", choices=sorted(PRODUCTION_OPS), action="append")
    approval.add_argument("--supersedes")
    approval.add_argument("--hours", type=int, default=2)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("authorization")
    resolution = sub.add_parser("record-resolution")
    resolution.add_argument("--input", type=Path, required=True)
    migrate = sub.add_parser("migrate-registry")
    migrate.add_argument("--legacy-resolution", action="append", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    operator, registry, state = settings()
    store = OperatorStore(operator)
    try:
        require(sys.stdin.isatty() and sys.stdout.isatty(), "interactive_operator_required")
        if args.action == "login":
            return login(args)
        if args.action == "approve":
            return approve(args, store, registry, state)
        if args.action == "revoke":
            store.load("authorizations", args.authorization)
            require(prompt(f"Type {args.authorization} to revoke it: ") == args.authorization,
                    "operator_confirmation_missing")
            store.revoke(args.authorization)
            print_json({"revoked": args.authorization})
            return 0
        if args.action == "migrate-registry":
            lineage = Lineage(registry, store, lambda: datetime.now(timezone.utc))
            lineage.prepare()
            lineage.upgrade(args.legacy_resolution)
            print_json({"status": "registry_v2_ready", "mutations": 0})
            return 0
        return record_resolution(args.input, store)
    except Stop as exc:
        print(canonical({"error_code": exc.reason, "safe_ids": exc.detail}).decode(), file=sys.stderr)
        return exc.code
    except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, EOFError, KeyboardInterrupt):
        print('{"error_code":"operator_action_incomplete"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
