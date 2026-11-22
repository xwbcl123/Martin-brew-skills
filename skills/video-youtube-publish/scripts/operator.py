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

from auth_store import OPS, OperatorStore, Stop, lock_file, require, safe_private, safe_read, timestamp, validate_auth
from package import CHANNEL, PROTECTED, Invalid, atomic_write, canonical, clean_identifier, json_data
from publish import CLI_ROOT, Client, Controller, local_authority_binding, secure_cli_env, settings


def prompt(message):
    return input(message).strip()


def print_json(value):
    print(canonical(value).decode())


def register_channel():
    home = Path.home()
    config = home / ".config/video-skills"
    safe_private(config, create=True)
    path = config / "config.json"
    with lock_file(config / "config.lock"):
        current = json_data(safe_read(path)) if path.exists() or path.is_symlink() else {"profiles": {}}
        require(isinstance(current, dict), "invalid_profile_map")
        profiles = current.get("profiles", current)
        require(isinstance(profiles, dict), "invalid_profile_map")
        previous = profiles.get("smoke-test")
        if previous is not None:
            channel = previous.get("channel_id") if isinstance(previous, dict) else previous
            require(isinstance(channel, str) and CHANNEL.fullmatch(channel), "invalid_existing_smoke_channel")
            return channel, path
        channel = prompt("Enter the exact intended YouTube channel ID (UC…): ")
        require(CHANNEL.fullmatch(channel), "invalid_smoke_channel_id")
        require(prompt(f"Type {channel} to confirm the target channel: ") == channel,
                "operator_confirmation_missing")
        profiles["smoke-test"] = {"channel_id": channel}
        atomic_write(path, canonical(current), exclusive=not path.exists())
        return channel, path


def login():
    channel, profile_map = register_channel()
    env = secure_cli_env()
    env["VIDEO_SKILLS_CONFIG"] = str(profile_map)
    env.setdefault("YTPUB_CLIENT_SECRET", str(Path.home() / ".config/ytpub/client_secret.json"))
    env.setdefault("YTPUB_TOKEN_PATH", str(Path.home() / ".config/ytpub/token.json"))
    return subprocess.run([
        str(CLI_ROOT / ".venv/bin/python"), "-I", "-B", "-m", "ytpub.cli",
        "auth", "login", "--profile", "smoke-test", "--cache-backend", "file",
        "--channel-id", channel,
    ], env=env, check=False).returncode


def approve(args, store, registry, state):
    package = args.package.absolute()
    preview = (args.preview or package.parent / "video-release-preview.html").absolute()
    safe_private(package)
    require(preview.parent == package.parent and not preview.is_symlink(), "preview_must_be_local_sibling")
    controller = Controller(package, preview, "smoke-test", Client(CLI_ROOT, "smoke-test", args.cache_backend),
                            store, registry, state, None)
    report, manifest = controller.local()
    require(controller.hash_contract() == report["binding"]["contract_bundle_sha256"],
            "contract_runtime_identity_mismatch")
    binding = local_authority_binding(package, manifest, report, controller.hash_cli(), controller.cli(["doctor"]))
    expected = OPS if binding["playlist_ids"] else OPS - {"add_playlist"}
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
    quote = "Authorize " + authorization_id + " for one private YouTube smoke package."
    print_json({**binding, "allowed_operations": sorted(operations), "review_preview": str(preview),
                "authorization_id": authorization_id, "supersedes": supersedes, "valid_hours": args.hours})
    require(prompt(f"Review the preview and binding. Type exactly: {quote}\n> ") == quote,
            "operator_confirmation_missing")
    now = datetime.now(timezone.utc)
    value = {**binding, "authorization_version": "2.0", "authorization_id": authorization_id,
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
    "resume_confirmed_suffix", "accept_observed_thumbnail",
}


def record_resolution(source, store):
    resolution = json_data(safe_read(source))
    require(not PROTECTED.search(canonical(resolution).decode()), "credential_like_resolution")
    required = {"episode_key", "package_revision", "seal_sha256", "target_channel_id", "expected_seq",
                "expected_digest", "op_key", "attempt_id", "decision", "observations"}
    optional = {"video_id", "session_handle", "confirmed_offset"}
    require(isinstance(resolution, dict) and required <= resolution.keys() <= required | optional,
            "invalid_resolution_fields")
    require(isinstance(resolution["decision"], str) and resolution["decision"] in DECISIONS,
            "invalid_resolution_decision")
    structured = {"observations", "confirmed_offset", "expected_seq", "package_revision"}
    require(all(clean_identifier(value) for key, value in resolution.items() if key not in structured),
            "invalid_resolution_value")
    require(isinstance(resolution["observations"], list) and resolution["observations"] and
            all(isinstance(row, dict) and {"source", "evidence_sha256"} <= row.keys() <=
                {"source", "evidence_sha256", "video_id"} and all(clean_identifier(v) for v in row.values())
                for row in resolution["observations"]), "invalid_resolution_observation")
    require(all(type(resolution[key]) is int and resolution[key] >= 0
                for key in structured - {"observations"} if key in resolution), "invalid_resolution_number")
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
    sub.add_parser("login", help="Register a channel and open the local Google OAuth approval")
    approval = sub.add_parser("approve", help="Interactively grant authority to a sealed package")
    approval.add_argument("--package", type=Path, required=True)
    approval.add_argument("--preview", type=Path)
    approval.add_argument("--cache-backend", choices=("keychain", "file"))
    approval.add_argument("--allow", choices=sorted(OPS), action="append")
    approval.add_argument("--supersedes")
    approval.add_argument("--hours", type=int, default=2)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("authorization")
    resolution = sub.add_parser("record-resolution")
    resolution.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    operator, registry, state = settings()
    store = OperatorStore(operator)
    try:
        require(sys.stdin.isatty() and sys.stdout.isatty(), "interactive_operator_required")
        if args.action == "login":
            return login()
        if args.action == "approve":
            return approve(args, store, registry, state)
        if args.action == "revoke":
            store.load("authorizations", args.authorization)
            require(prompt(f"Type {args.authorization} to revoke it: ") == args.authorization,
                    "operator_confirmation_missing")
            store.revoke(args.authorization)
            print_json({"revoked": args.authorization})
            return 0
        return record_resolution(args.input, store)
    except Stop as exc:
        print(canonical({"error_code": exc.reason}).decode(), file=sys.stderr)
        return exc.code
    except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, EOFError, KeyboardInterrupt):
        print('{"error_code":"operator_action_incomplete"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
