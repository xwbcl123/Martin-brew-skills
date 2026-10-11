#!/usr/bin/env python3
"""Validate existing local PCM review artifacts; never release, upload or publish."""
from __future__ import annotations

import argparse
import html
import json
import wave
from pathlib import Path
from urllib.parse import quote

import jsonschema

from validate_release_package import resolve_inside, sha256_file

SCHEMA = Path(__file__).resolve().parents[1] / "references/agent-draft.schema.json"


def document(path, definition=None):
    value = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if definition:
        schema = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    jsonschema.Draft202012Validator(schema).validate(value)
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bound_artifact(root, artifact):
    path = resolve_inside(root, artifact["path"])
    require(path.stat().st_size > 0, "Empty artifact")
    require(sha256_file(path) == artifact["sha256"], "Stale artifact hash: " + artifact["path"])
    return path


def validate(manifest_path, authorization_path, review_path, trusted_authorization_sha256):
    """The caller must obtain the trusted digest from the actual user task record."""
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent
    require(sha256_file(authorization_path) == trusted_authorization_sha256,
            "Authorization does not match trusted task digest")
    manifest_sha = sha256_file(manifest_path)
    review_sha = sha256_file(review_path)
    manifest = document(manifest_path)
    authorization = document(authorization_path, "authorization")
    review = document(review_path, "review")
    for record in (authorization, review):
        require(record["episode_key"] == manifest["episode_key"], "Wrong episode")
        require(record["manifest_sha256"] == manifest_sha, "Stale manifest binding")
    require(review["producer_id"] == manifest["producer_id"], "Producer mismatch")
    require(review["reviewer_id"].strip() != manifest["producer_id"].strip(), "Reviewer is not independent")
    hashes = {role: artifact["sha256"] for role, artifact in manifest["artifacts"].items()}
    require(review["artifact_hashes"] == hashes, "Incomplete or stale reviewer artifact coverage")
    paths = {role: bound_artifact(root, artifact) for role, artifact in manifest["artifacts"].items()}
    evidence_path = bound_artifact(root, review["evidence"])
    control_paths = {manifest_path, authorization_path.resolve(), review_path.resolve()}
    require(evidence_path not in set(paths.values()) | control_paths,
            "Review evidence must be separate from artifacts and control documents")
    require(review["evidence"]["sha256"] not in hashes.values(),
            "Review evidence cannot duplicate artifact content")
    evidence_stat = evidence_path.stat()
    require(all((evidence_stat.st_dev, evidence_stat.st_ino) !=
                (p.stat().st_dev, p.stat().st_ino) for p in set(paths.values()) | control_paths),
            "Review evidence cannot alias an artifact or control document")
    # Receipts, manifests and other machine-control JSON are never review prose.
    require(evidence_path.suffix.lower() in {".md", ".txt"}, "Review evidence must be a dedicated Markdown or text document")
    evidence_text = evidence_path.read_text(encoding="utf-8")
    require(bool(evidence_text.strip()), "Review evidence cannot be blank")
    try:
        json.loads(evidence_text)
    except json.JSONDecodeError:
        pass
    else:
        raise ValueError("JSON control data cannot substitute for reviewer evidence prose")
    audio = paths["review_audio"]
    require(audio.suffix.lower() == ".wav", "Draft v1 supports PCM WAV review audio only")
    with wave.open(str(audio), "rb") as wav:
        channels, width, rate, frames, compression, _ = wav.getparams()
        require(rate == 48000 and channels in (1, 2) and width in (2, 3, 4)
                and frames > 0 and compression == "NONE", "PCM review audio technical checks failed")
        # Detect truncated sample data, without rendering or processing media.
        remaining = frames
        while remaining:
            count = min(remaining, 65536)
            require(len(wav.readframes(count)) == count * channels * width, "Truncated PCM audio")
            remaining -= count
    for role in ("transcript", "notes"):
        if role in paths:
            require(bool(paths[role].read_text(encoding="utf-8").strip()), "Empty text artifact")
    # Recheck every identity after inspection; no cached review can survive byte changes.
    for artifact in manifest["artifacts"].values():
        bound_artifact(root, artifact)
    bound_artifact(root, review["evidence"])
    require(sha256_file(manifest_path) == manifest_sha and sha256_file(review_path) == review_sha
            and sha256_file(authorization_path) == trusted_authorization_sha256, "Inputs changed during validation")
    return {
        "contract_version": "agent-draft-v1", "review_mode": "agent_draft",
        "episode_key": manifest["episode_key"], "draft_contract_passed": True,
        "agent_draft_preview_ready": True, "contract_passed": False,
        "human_preview_ready": False, "growth_ready": False,
        "upload_authorized": False, "publish_authorized": False,
        "external_mutation_authorized": False, "manifest_sha256": manifest_sha,
        "authorization_sha256": trusted_authorization_sha256, "review_sha256": review_sha,
        "reviewer_evidence_sha256": review["evidence"]["sha256"],
        "artifact_hashes": hashes, "technical_checks": {
            "sample_rate_hz": rate, "channels": channels, "sample_width_bytes": width,
            "frames": frames, "duration_seconds": frames / rate, "pcm_data_complete": True},
        "limitations": manifest["limitations"] + [
            "Agent review is advisory draft evidence, not human listening, rights, consent or release acceptance.",
            "No loudness, semantic fidelity, subtitle timing or full production completion is certified."],
        "review_coverage": review["coverage"],
    }


def preview(manifest_path, report, output):
    root = manifest_path.resolve().parent
    require(output.resolve().parent == root, "Draft preview must be beside the manifest")
    manifest = document(manifest_path)
    require(sha256_file(manifest_path) == report["manifest_sha256"], "Stale preview manifest")
    audio = bound_artifact(root, manifest["artifacts"]["review_audio"])
    uri = quote(audio.relative_to(root).as_posix(), safe="/")
    return ('<!doctype html><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; media-src \'self\' file:;">'
            '<title>LOCAL AGENT DRAFT — NOT RELEASE ACCEPTED</title>'
            '<h1>LOCAL AGENT DRAFT — NOT RELEASE ACCEPTED</h1>'
            '<p>No upload, publishing, human approval, rights or consent authorization.</p>'
            f'<audio controls src="{html.escape(uri, quote=True)}"></audio>'
            '<pre>' + html.escape(json.dumps(report, ensure_ascii=False, indent=2)) + '</pre>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-mode", choices=("human", "agent_draft"), default="human")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    try:
        require(args.review_mode == "agent_draft", "Default human mode: use validate_release_package.py; opt in explicitly for a local agent draft")
        report = validate(args.manifest, args.authorization, args.review, args.authorization_sha256)
        outputs = [args.report] + ([args.preview] if args.preview else [])
        require(len({p.resolve() for p in outputs}) == len(outputs), "Output paths collide")
        for output in outputs:
            require(not output.exists() and not output.is_symlink(), "Refusing to overwrite any existing artifact")
        preview_text = preview(args.manifest, report, args.preview) if args.preview else None
        with args.report.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if args.preview:
            with args.preview.open("x", encoding="utf-8") as handle:
                handle.write(preview_text)
        return 0
    except (OSError, ValueError, EOFError, wave.Error, jsonschema.ValidationError) as exc:
        print(json.dumps({"draft_contract_passed": False, "contract_passed": False,
                          "upload_authorized": False, "publish_authorized": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
