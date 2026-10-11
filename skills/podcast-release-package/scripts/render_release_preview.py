#!/usr/bin/env python3
"""Render a deterministic human preview from an accepted podcast package."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

from validate_release_package import canonical_payload_sha256, resolve_inside, sha256_file, validate


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def plain_html(source: str) -> str:
    source = re.sub(r"<\s*br\s*/?>", "\n", source, flags=re.IGNORECASE)
    source = re.sub(r"</\s*(p|li|h[1-6])\s*>", "\n", source, flags=re.IGNORECASE)
    source = re.sub(r"<[^>]+>", "", source)
    return html.escape(source.strip()).replace("\n", "<br>")


def rel_url(output: Path, target: Path) -> str:
    relative = os.path.relpath(target, output.parent)
    return "/".join(quote(part) for part in Path(relative).parts)


def format_time(seconds: float) -> str:
    whole = max(0, int(round(seconds)))
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def render(manifest_path: Path, report_path: Path, output_path: Path) -> str:
    manifest = load_json(manifest_path)
    report = load_json(report_path)
    root = manifest_path.parent.resolve()
    expected_output = resolve_inside(root, manifest["preview"]["output_file"], must_exist=False)
    if output_path.resolve() != expected_output:
        raise ValueError(f"output must match manifest preview.output_file: {expected_output}")
    if not report.get("contract_passed") or not report.get("human_preview_ready"):
        raise ValueError("acceptance report is not contract-passed and human-preview-ready")
    live_report = validate(manifest_path)
    if not live_report.get("contract_passed"):
        failed = [g["id"] for g in live_report.get("gates", []) if g.get("status") == "failed"]
        raise ValueError(f"package no longer passes live validation: {', '.join(failed)}")
    manifest_sha = sha256_file(manifest_path)
    if report.get("manifest_sha256") != manifest_sha:
        raise ValueError("manifest SHA-256 no longer matches acceptance report")
    payload_sha = canonical_payload_sha256(manifest)
    if report.get("release_candidate_payload_sha256") != payload_sha:
        raise ValueError("release-candidate payload SHA-256 no longer matches acceptance report")

    media = resolve_inside(root, manifest["media"]["release_audio"])
    if sha256_file(media) != report.get("release_audio_sha256"):
        raise ValueError("release audio SHA-256 no longer matches acceptance report")
    artwork = resolve_inside(root, manifest["artwork"]["episode_file"])
    summary = text(resolve_inside(root, manifest["episode"]["summary_file"]))
    description = text(resolve_inside(root, manifest["episode"]["description_file"]))
    transcript = text(resolve_inside(root, manifest["transcript"]["text_file"]))
    launch_copy = text(resolve_inside(root, manifest["promo"]["launch_copy_file"]))
    chapter_doc = load_json(resolve_inside(root, manifest["chapters"]["file"]))
    chapters = chapter_doc.get("chapters", [])
    participants = manifest["episode"]["participants"]
    metrics = report.get("audio_metrics", {})
    artwork_gate = next((gate for gate in report.get("gates", []) if gate.get("id") == "G09_ARTWORK"), {})
    artwork_probe = artwork_gate.get("evidence", {}).get("probe", {})
    artwork_approval = manifest["approvals"]["artwork"]

    participant_html = "".join(
        f'<span class="person"><b>{html.escape(p["name"])}</b> · {html.escape(p["role"])}</span>'
        for p in participants
    )
    chapter_html = "".join(
        f'<li><button data-seek="{float(c["start_seconds"]):.3f}">{format_time(float(c["start_seconds"]))}</button>'
        f'<span>{html.escape(str(c["title"]))}</span></li>'
        for c in chapters
    )
    gate_html = "".join(
        f'<tr><td><code>{html.escape(g["id"])}</code></td><td><span class="pass">PASS</span></td></tr>'
        for g in report["gates"]
    )
    approval_html = "".join(
        f'<tr><td>{html.escape(name.replace("_", " ").title())}</td>'
        f'<td>{html.escape(value["approved_by"])}</td><td>{html.escape(value["approved_at"])}</td></tr>'
        for name, value in manifest["approvals"].items()
    )
    transcript_excerpt = transcript[:6000] + ("\n\n[…]" if len(transcript) > 6000 else "")
    audio_url = rel_url(output_path, media)
    art_url = rel_url(output_path, artwork)

    document = f'''<!doctype html>
<html lang="{html.escape(manifest["show"]["language"])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{html.escape(manifest["episode"]["title"])} — Final Preflight</title>
<style>
:root{{--bg:#081126;--panel:#101d3d;--line:#27385f;--text:#eaf5ff;--muted:#9fb2cc;--cyan:#29ddda;--mint:#16ffbb;--amber:#ffd166}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(145deg,#050a1c,#0b1734);color:var(--text);font:16px/1.6 system-ui,-apple-system,sans-serif}}
main{{max-width:1100px;margin:auto;padding:36px 20px 80px}} .hero,.card{{background:rgba(16,29,61,.94);border:1px solid var(--line);border-radius:18px;padding:24px;margin-bottom:20px}}
.hero{{display:grid;grid-template-columns:minmax(220px,320px) 1fr;gap:28px}} .cover{{width:100%;aspect-ratio:1;border-radius:14px;object-fit:cover}}
.visual-grid{{display:grid;grid-template-columns:minmax(260px,480px) 1fr;gap:26px;align-items:start}} .visual-proof{{width:100%;aspect-ratio:1;object-fit:cover;border-radius:16px;border:1px solid var(--line)}}
h1{{font-size:clamp(28px,5vw,52px);line-height:1.1;margin:10px 0 18px}} h2{{margin-top:0}} .eyebrow,code{{font:12px/1.5 ui-monospace,SFMono-Regular,monospace;color:var(--cyan)}}
.people{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}} .person,.badge{{border:1px solid var(--line);border-radius:999px;padding:5px 10px;color:var(--muted)}}
audio{{width:100%;margin-top:18px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} .prose{{color:#dbe8f3}} .muted{{color:var(--muted)}}
ol{{padding-left:0;list-style:none}} li{{display:flex;gap:14px;padding:10px 0;border-bottom:1px solid var(--line)}} button{{background:#152c55;color:var(--cyan);border:1px solid #31517d;border-radius:8px;padding:5px 9px;cursor:pointer}}
table{{width:100%;border-collapse:collapse}} td,th{{padding:9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} .pass{{color:var(--mint);font-weight:700}}
pre{{white-space:pre-wrap;max-height:420px;overflow:auto;background:#071025;padding:18px;border-radius:12px;color:#dbe8f3}} .boundary{{border-color:#8e6829;background:#2b2214;color:#ffe5a6}}
@media(max-width:760px){{.hero,.grid,.visual-grid{{grid-template-columns:1fr}}.cover{{max-width:320px}}}}
</style>
</head>
<body><main>
<section class="hero">
  <img class="cover" src="{art_url}" alt="Episode artwork">
  <div><div class="eyebrow">FINAL PREFLIGHT · CONTRACT 12/12 · {html.escape(manifest["show"]["title"])} · S{manifest["episode"]["season"]}E{manifest["episode"]["number"]} · {html.escape(manifest["episode_key"])}</div>
  <h1>{html.escape(manifest["episode"]["title"])}</h1>
  <p>{html.escape(summary)}</p><div class="people">{participant_html}</div>
  <audio id="episodeAudio" controls preload="metadata" src="{audio_url}"></audio></div>
</section>
<section class="card boundary"><b>Release quality accepted; publication not authorized.</b> This page proves package completeness only. A separate approval bound to the hashes below is required before Transistor publish.</section>
<section class="card"><h2>Visual Assets</h2><div class="visual-grid">
  <img class="visual-proof" src="{art_url}" alt="Approved episode artwork for {html.escape(manifest['episode']['title'])}">
  <table>
    <tr><td>Role</td><td>Episode artwork</td></tr>
    <tr><td>File</td><td><code>{html.escape(manifest['artwork']['episode_file'])}</code></td></tr>
    <tr><td>Dimensions</td><td>{html.escape(str(artwork_probe.get('width')))} × {html.escape(str(artwork_probe.get('height')))} px</td></tr>
    <tr><td>Bytes</td><td>{html.escape(str(artwork_probe.get('bytes')))}</td></tr>
    <tr><td>RGB verified</td><td>{html.escape(str(artwork_probe.get('colorspace_rgb')))}</td></tr>
    <tr><td>SHA-256</td><td><code>{html.escape(manifest['artwork']['episode_sha256'])}</code></td></tr>
    <tr><td>Approved by</td><td>{html.escape(artwork_approval['approved_by'])} · {html.escape(artwork_approval['approved_at'])}</td></tr>
    <tr><td>Public image URL</td><td>{html.escape(str(manifest['artwork'].get('public_image_url') or 'pending until provider draft'))}</td></tr>
  </table>
</div></section>
<div class="grid">
  <section class="card"><h2>Show Notes</h2><div class="prose">{plain_html(description)}</div></section>
  <section class="card"><h2>Chapters</h2><ol>{chapter_html}</ol></section>
</div>
<div class="grid">
  <section class="card"><h2>Technical QC</h2><table>
    <tr><td>Duration</td><td>{format_time(float(metrics.get("duration_seconds",0)))}</td></tr>
    <tr><td>Codec</td><td>{html.escape(str(metrics.get("codec")))}</td></tr>
    <tr><td>Sample rate</td><td>{html.escape(str(metrics.get("sample_rate_hz")))} Hz</td></tr>
    <tr><td>Bitrate</td><td>{int(metrics.get("bit_rate_bps",0))//1000} kbps</td></tr>
    <tr><td>Integrated loudness</td><td>{html.escape(str(metrics.get("integrated_lufs")))} LUFS</td></tr>
    <tr><td>True peak</td><td>{html.escape(str(metrics.get("true_peak_dbtp")))} dBTP</td></tr>
  </table></section>
  <section class="card"><h2>Acceptance Gates</h2><table>{gate_html}</table></section>
</div>
<section class="card"><h2>Approvals</h2><table><tr><th>Gate</th><th>Approved by</th><th>Approved at</th></tr>{approval_html}</table></section>
<section class="card"><h2>Transcript excerpt</h2><pre>{html.escape(transcript_excerpt)}</pre></section>
<section class="card"><h2>Launch copy</h2><pre>{html.escape(launch_copy)}</pre></section>
<section class="card"><h2>Audit identity</h2><table>
  <tr><td>Manifest SHA-256</td><td><code>{manifest_sha}</code></td></tr>
  <tr><td>Release payload SHA-256</td><td><code>{payload_sha}</code></td></tr>
  <tr><td>Release audio SHA-256</td><td><code>{html.escape(report["release_audio_sha256"])}</code></td></tr>
  <tr><td>Contract</td><td><span class="pass">v1.0 PASS</span></td></tr>
  <tr><td>Publish authorized</td><td><b>FALSE</b></td></tr>
</table></section>
</main>
<script>const audio=document.getElementById('episodeAudio');document.querySelectorAll('[data-seek]').forEach(b=>b.addEventListener('click',()=>{{audio.currentTime=Number(b.dataset.seek);audio.play();}}));</script>
</body></html>'''
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--acceptance-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        content = render(args.manifest.resolve(), args.acceptance_report.resolve(), args.output.resolve())
        atomic_text(args.output.resolve(), content)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    result = {"output": str(args.output.resolve()), "sha256": hashlib.sha256((content + "\n").encode()).hexdigest()}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
