#!/usr/bin/env python3
"""Generic S00-S01 bootstrap from an immutable audio/video intake declaration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        pathlib.Path(temporary_name).unlink(missing_ok=True)
        raise


def probe(path: pathlib.Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                             "-show_entries", "stream=codec_name,sample_rate,channels,channel_layout,duration:format=duration,size,format_name,bit_rate",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    fmt = data["format"]
    return {"codec_name": stream.get("codec_name"), "sample_rate_hz": int(stream["sample_rate"]),
            "channels": int(stream["channels"]), "channel_layout": stream.get("channel_layout"),
            "duration_seconds": float(stream.get("duration") or fmt["duration"]),
            "bytes": int(fmt["size"]), "format_name": fmt.get("format_name"),
            "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None}


def source_identity(path: pathlib.Path) -> dict:
    stat = path.stat()
    return {"path": str(path), "sha256": sha256(path), "bytes": stat.st_size,
            "inode": stat.st_ino, "mtime_ns": stat.st_mtime_ns}


def verified_cache(report_path: pathlib.Path, run_key: str, render: pathlib.Path,
                   analysis: pathlib.Path) -> bool:
    if not report_path.is_file() or not render.is_file() or not analysis.is_file():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return (report.get("run_key") == run_key
                and report["outputs"]["render_audio"]["sha256"] == sha256(render)
                and report["outputs"]["analysis_audio"]["sha256"] == sha256(analysis))
    except (KeyError, json.JSONDecodeError, OSError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--render", type=pathlib.Path, required=True)
    parser.add_argument("--analysis", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()

    intake = json.loads(args.intake.read_text(encoding="utf-8"))
    source = pathlib.Path(intake["source"]["path"])
    before = source_identity(source)
    if before["sha256"] != intake["source"]["sha256"] or before["bytes"] != intake["source"]["bytes"]:
        raise SystemExit("immutable source identity mismatch")
    source_probe = probe(source)
    if source_probe["sample_rate_hz"] != 48000 or source_probe["channels"] not in {1, 2}:
        raise SystemExit(f"unsupported source audio role: {source_probe}")
    ffmpeg_version = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    run_key = canonical_hash({"stage": "S00-S01-bootstrap-audio-roles", "version": "1.0",
                              "intake_sha256": sha256(args.intake), "source_sha256": before["sha256"],
                              "render": {"codec": "pcm_s16le", "sample_rate_hz": 48000,
                                         "channels": source_probe["channels"]},
                              "analysis": {"codec": "pcm_s16le", "sample_rate_hz": 16000, "channels": 1},
                              "ffmpeg": ffmpeg_version})
    cache = "verified_hit" if verified_cache(args.report, run_key, args.render, args.analysis) else "miss"
    if cache == "miss":
        args.render.parent.mkdir(parents=True, exist_ok=True)
        args.analysis.parent.mkdir(parents=True, exist_ok=True)
        partial_render = args.render.parent / f".{args.render.name}.{run_key[:16]}.partial.wav"
        partial_analysis = args.analysis.parent / f".{args.analysis.name}.{run_key[:16]}.partial.wav"
        partial_render.unlink(missing_ok=True); partial_analysis.unlink(missing_ok=True)
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                   "-map", "0:a:0", "-vn", "-map_metadata", "-1", "-c:a", "pcm_s16le", "-ar", "48000",
                   "-ac", str(source_probe["channels"]), str(partial_render),
                   "-map", "0:a:0", "-vn", "-map_metadata", "-1", "-c:a", "pcm_s16le", "-ar", "16000",
                   "-ac", "1", str(partial_analysis)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode or not partial_render.is_file() or not partial_analysis.is_file():
            partial_render.unlink(missing_ok=True); partial_analysis.unlink(missing_ok=True)
            raise SystemExit(f"ffmpeg role extraction failed: {result.stderr}")
        render_probe = probe(partial_render); analysis_probe = probe(partial_analysis)
        if (render_probe["codec_name"] != "pcm_s16le" or render_probe["sample_rate_hz"] != 48000
                or render_probe["channels"] != source_probe["channels"]):
            raise SystemExit(f"render role probe failed: {render_probe}")
        if analysis_probe["codec_name"] != "pcm_s16le" or analysis_probe["sample_rate_hz"] != 16000 or analysis_probe["channels"] != 1:
            raise SystemExit(f"analysis role probe failed: {analysis_probe}")
        os.replace(partial_render, args.render); os.replace(partial_analysis, args.analysis)

    after = source_identity(source)
    if after != before:
        raise SystemExit("immutable source changed during extraction")
    render_probe = probe(args.render); analysis_probe = probe(args.analysis)
    outputs = {
        "render_audio": {"path": str(args.render), "sha256": sha256(args.render), "role": "render-only",
                         "probe": render_probe},
        "analysis_audio": {"path": str(args.analysis), "sha256": sha256(args.analysis), "role": "analysis-only",
                           "probe": analysis_probe},
    }
    manifest = {"schema_version": "1.0", "episode_id": intake["episode_id"], "stage": "S00-S01-bootstrap-audio-roles",
                "run_key": run_key, "source": {**intake["source"], "live_identity": before, "probe": source_probe},
                "audio_roles": outputs, "timebase": {"basis": "source-audio", "sample_rate_hz": 48000},
                "external_judge_dispatch_authorized": False, "publish_authorized": False}
    report = {"schema_version": "1.0", "episode_id": intake["episode_id"], "stage": "S00-S01-bootstrap-audio-roles",
              "status": "succeeded", "run_key": run_key, "intake_path": str(args.intake),
              "intake_sha256": sha256(args.intake), "source_identity_before": before,
              "source_identity_after": after, "source_immutable": before == after, "outputs": outputs,
              "tool": {"name": "ffmpeg", "version": ffmpeg_version},
              "external_judge_dispatch_authorized": False, "publish_authorized": False}
    atomic_json(args.manifest, manifest); atomic_json(args.report, report)
    print(json.dumps({"status": "succeeded", "cache": cache, "run_key": run_key,
                      "manifest": str(args.manifest), "manifest_sha256": sha256(args.manifest),
                      "report": str(args.report), "report_sha256": sha256(args.report),
                      "outputs": {name: value["sha256"] for name, value in outputs.items()},
                      "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
