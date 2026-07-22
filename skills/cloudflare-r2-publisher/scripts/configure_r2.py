#!/usr/bin/env python3
"""Interactively store dedicated Hermes R2 settings without shell history leaks."""

from __future__ import annotations

import getpass
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlparse


def required(prompt: str, *, secret: bool = False, default: str | None = None) -> str:
    label = f"{prompt} [{default}]" if default else prompt
    value = (getpass.getpass(label + ": ") if secret else input(label + ": ")).strip()
    value = value or (default or "")
    if not value:
        raise SystemExit(f"Missing required value: {prompt}")
    if "\n" in value or "\r" in value:
        raise SystemExit(f"Invalid newline in: {prompt}")
    return value


def validate_url(label: str, value: str, suffix: str | None = None) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise SystemExit(f"{label} must be a plain https URL")
    normalized = value.rstrip("/")
    if suffix and not parsed.netloc.endswith(suffix):
        raise SystemExit(f"{label} must use a {suffix} host")
    return normalized


def main() -> None:
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if not hermes_home:
        raise SystemExit("Set HERMES_HOME explicitly before running this configurator")
    home = Path(hermes_home).expanduser().resolve()
    env_path = home / ".env"
    print("Configure the dedicated Hermes Cloudflare R2 Bucket. Values are written only to:")
    print(env_path)
    access_key = required("R2 Access Key ID", secret=True)
    secret_key = required("R2 Secret Access Key", secret=True)
    bucket = required("Bucket name", default="agent-public-artifacts")
    endpoint = validate_url("S3 endpoint", required("S3 endpoint"), ".r2.cloudflarestorage.com")
    public_url = validate_url("Public r2.dev URL", required("Public r2.dev URL"), ".r2.dev")
    prefix = required("Upload prefix", default="deep-research").strip("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise SystemExit("Bucket name is not valid")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", prefix) or ".." in prefix.split("/"):
        raise SystemExit("Upload prefix is not valid")
    from hermes_cli.config import save_env_value_secure

    values = {
        "HERMES_R2_ACCESS_KEY_ID": access_key,
        "HERMES_R2_SECRET_ACCESS_KEY": secret_key,
        "HERMES_R2_BUCKET_NAME": bucket,
        "HERMES_R2_ENDPOINT": endpoint,
        "HERMES_R2_PUBLIC_URL": public_url,
        "HERMES_R2_UPLOAD_PREFIX": prefix,
    }
    for key, value in values.items():
        result = save_env_value_secure(key, value)
        if not result.get("success"):
            raise SystemExit(f"Hermes secure writer failed for {key}")
    if stat.S_IMODE(env_path.stat().st_mode) != 0o600:
        env_path.chmod(0o600)
    print("Saved 6 R2 settings. Secret values were not printed.")
    print("Next: run r2_publisher.py preflight --remote")


if __name__ == "__main__":
    main()
