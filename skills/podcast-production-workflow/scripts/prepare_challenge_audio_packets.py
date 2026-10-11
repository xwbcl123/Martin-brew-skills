#!/usr/bin/env python3
"""Create bounded local FLAC windows and audio-only candidate packets for a frozen challenge set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/candidate-packet.schema.json"
RATE = 48000


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def atomic_bytes(path: pathlib.Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(value)
        temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def duration_seconds(path: pathlib.Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=nw=1:nk=1", str(path)], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def main() -> None:
    import jsonschema
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=pathlib.Path, required=True)
    parser.add_argument("--challenge-set", type=pathlib.Path, required=True)
    parser.add_argument("--analysis-audio", type=pathlib.Path, required=True)
    parser.add_argument("--window-dir", type=pathlib.Path, required=True)
    parser.add_argument("--packet-dir", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--context-seconds", type=float, default=7.5)
    args = parser.parse_args()
    bundle = json.loads(args.candidates.read_text())
    by_id = {item["candidate_id"]: item for item in bundle["candidates"]}
    challenge = json.loads(args.challenge_set.read_text())
    if challenge["candidate_bundle_sha256"] != sha256(args.candidates):
        raise SystemExit("challenge set candidate bundle hash mismatch")
    if by_id[next(iter(by_id))]["analysis_audio_sha256"] != sha256(args.analysis_audio):
        raise SystemExit("analysis audio hash mismatch")
    total_samples = round(duration_seconds(args.analysis_audio) * RATE)
    schema = json.loads(SCHEMA.read_text())
    context_samples = round(args.context_seconds * RATE)
    entries = []
    ffmpeg_version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    for selected in challenge["candidates"]:
        source = by_id[selected["candidate_id"]]
        core = source["core_interval"]
        window_start = max(0, core["start_sample"] - context_samples)
        window_end = min(total_samples, core["end_sample"] + context_samples)
        window = args.window_dir / f"{source['candidate_id']}.flac"
        window.parent.mkdir(parents=True, exist_ok=True)
        partial = window.parent / f".{window.name}.partial.flac"
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                   "-ss", f"{window_start / RATE:.9f}", "-t", f"{(window_end-window_start) / RATE:.9f}",
                   "-i", str(args.analysis_audio), "-map", "0:a:0", "-map_metadata", "-1",
                   "-ac", "1", "-ar", "16000", "-c:a", "flac", "-compression_level", "8", str(partial)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            partial.unlink(missing_ok=True)
            raise SystemExit(f"audio window extraction failed for {source['candidate_id']}: {result.stderr}")
        if not window.exists() or sha256(window) != sha256(partial):
            os.replace(partial, window)
        else:
            partial.unlink()
        packet = dict(source)
        packet["audio_window"] = {"path": str(window), "sha256": sha256(window),
                                  "start_sample": window_start, "end_sample": window_end}
        packet["context"] = {"text_before": "", "candidate_text": source["category"],
                             "text_after": "", "protected_tokens": []}
        packet["detector_evidence"] = [{"detector": "category_and_declared_core_only",
                                        "category": source["category"]}]
        jsonschema.validate(packet, schema)
        packet_path = args.packet_dir / f"{source['candidate_id']}.json"
        value = canonical_bytes(packet)
        atomic_bytes(packet_path, value)
        entries.append({"candidate_id": source["candidate_id"], "path": str(packet_path),
                        "sha256": hashlib.sha256(value).hexdigest(), "audio_window_sha256": sha256(window)})
    index = {"schema_version": "1.0", "stage": "S05-challenge-audio-packets", "episode_id": bundle["episode_id"],
             "challenge_set_path": str(args.challenge_set), "challenge_set_sha256": sha256(args.challenge_set),
             "analysis_audio_path": str(args.analysis_audio), "analysis_audio_sha256": sha256(args.analysis_audio),
             "context_seconds_each_side": args.context_seconds, "tool": {"name": "ffmpeg", "version": ffmpeg_version},
             "packet_count": len(entries), "packets": entries, "dispatch_status": "blocked_pending_h1",
             "publish_authorized": False}
    atomic_bytes(args.index, canonical_bytes(index))
    print(json.dumps({"status": "audio_packets_ready_local_only", "packet_count": len(entries),
                      "index": str(args.index), "index_sha256": sha256(args.index)}, indent=2))


if __name__ == "__main__":
    main()
