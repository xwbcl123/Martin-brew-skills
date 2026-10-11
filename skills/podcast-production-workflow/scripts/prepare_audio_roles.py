#!/usr/bin/env python3
"""Create and verify role-separated render and analysis audio for an episode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def probe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels,duration:format=duration,size",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "codec_name": stream.get("codec_name"),
        "sample_rate_hz": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "duration_seconds": float(stream.get("duration") or data["format"]["duration"]),
        "bytes": int(data["format"]["size"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source = Path(manifest["source"]["path"])
    if not source.is_file() or sha256_file(source) != manifest["source"]["sha256"]:
        raise SystemExit("source identity mismatch")
    source_probe = probe(source)
    if source_probe["sample_rate_hz"] != 48000 or source_probe["channels"] not in {1, 2}:
        raise SystemExit(f"unsupported source audio role: {source_probe}")

    analysis = Path(manifest["audio_roles"]["analysis_audio"]["path"])
    if not analysis.is_file() or sha256_file(analysis) != manifest["audio_roles"]["analysis_audio"]["sha256"]:
        raise SystemExit("analysis audio identity mismatch")
    analysis_probe = probe(analysis)
    if analysis_probe["sample_rate_hz"] != 16000 or analysis_probe["channels"] != 1:
        raise SystemExit(f"analysis proxy role mismatch: {analysis_probe}")

    render_spec = manifest["audio_roles"]["render_audio"]
    render = Path(render_spec["path"])
    ffmpeg_version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    run_key = canonical_sha256({
        "stage": "S01_EXTRACT_RENDER_AUDIO",
        "stage_version": "1.0",
        "source_sha256": manifest["source"]["sha256"],
        "codec": "pcm_s16le",
        "sample_rate_hz": source_probe["sample_rate_hz"],
        "channels": source_probe["channels"],
        "ffmpeg": ffmpeg_version,
    })

    cache = "miss"
    expected = render_spec.get("sha256")
    if render.is_file() and expected and sha256_file(render) == expected:
        cache = "verified_hit"
    else:
        render.parent.mkdir(parents=True, exist_ok=True)
        partial = render.parent / f".{render.name}.{run_key[:16]}.partial.wav"
        partial.unlink(missing_ok=True)
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-y", "-i", str(source),
            "-map", "0:a:0", "-vn", "-c:a", "pcm_s16le",
            "-ar", str(source_probe["sample_rate_hz"]), "-ac", str(source_probe["channels"]), str(partial),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0 or not partial.is_file():
            partial.unlink(missing_ok=True)
            raise SystemExit("ffmpeg render-audio extraction failed")
        partial_probe = probe(partial)
        if partial_probe["codec_name"] != "pcm_s16le" or partial_probe["sample_rate_hz"] != 48000 or partial_probe["channels"] != source_probe["channels"]:
            partial.unlink(missing_ok=True)
            raise SystemExit(f"render role verification failed: {partial_probe}")
        os.replace(partial, render)

    render_sha = sha256_file(render)
    render_probe = probe(render)
    manifest["audio_roles"]["render_audio"] = {
        "path": str(render),
        "sha256": render_sha,
        "duration_seconds": render_probe["duration_seconds"],
    }
    atomic_json(args.manifest, manifest)
    report = {
        "schema_version": "1.0",
        "stage": "S01_EXTRACT_AUDIO_ROLES",
        "status": "succeeded",
        "run_key": run_key,
        "cache": cache,
        "source": {"path": str(source), "sha256": manifest["source"]["sha256"], "probe": source_probe},
        "render_audio": {"path": str(render), "sha256": render_sha, "probe": render_probe, "role": "render-only"},
        "analysis_audio": {"path": str(analysis), "sha256": manifest["audio_roles"]["analysis_audio"]["sha256"], "probe": analysis_probe, "role": "analysis-only"},
        "tool": {"name": "ffmpeg", "version": ffmpeg_version},
        "publish_authorized": False,
    }
    atomic_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
