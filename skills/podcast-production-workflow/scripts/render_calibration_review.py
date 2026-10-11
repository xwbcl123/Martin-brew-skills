#!/usr/bin/env python3
"""Render a local, audio-assisted Filmora calibration disagreement review page."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import tempfile


RATE = 48000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def reference_time(source_seconds: float, reference_cuts: list[dict]) -> float:
    removed = 0.0
    for cut in reference_cuts:
        start = cut["interval"]["start_sample"] / RATE
        end = cut["interval"]["end_sample"] / RATE
        if end <= source_seconds:
            removed += end - start
        elif start < source_seconds:
            removed += source_seconds - start
            break
        else:
            break
    return max(0.0, source_seconds - removed)


def timeline_sample(items: list[dict], cap: int) -> list[dict]:
    """Deterministic kind-stratified, timeline-spread review sample."""
    if len(items) <= cap:
        return items
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["kind"], []).append(item)
    selected: list[dict] = []
    kinds = sorted(groups)
    base, remainder = divmod(cap, len(kinds))
    for index, kind in enumerate(kinds):
        group = sorted(groups[kind], key=lambda x: x["source_interval"]["start_sample"])
        quota = min(len(group), base + (1 if index < remainder else 0))
        if quota == len(group):
            selected.extend(group)
        elif quota:
            indices = sorted({round(i * (len(group) - 1) / max(1, quota - 1)) for i in range(quota)})
            selected.extend(group[i] for i in indices)
    if len(selected) < cap:
        selected_ids = {item["delta_id"] for item in selected}
        remaining = [item for item in items if item["delta_id"] not in selected_ids]
        selected.extend(remaining[:cap - len(selected)])
    return sorted(selected, key=lambda x: x["source_interval"]["start_sample"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta-report", type=Path, required=True)
    parser.add_argument("--reference-edl", type=Path, required=True)
    parser.add_argument("--source-audio", type=Path, required=True)
    parser.add_argument("--filmora-audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-cap", type=int, default=60)
    args = parser.parse_args()
    report = json.loads(args.delta_report.read_text(encoding="utf-8"))
    reference = json.loads(args.reference_edl.read_text(encoding="utf-8"))
    if sha256_file(args.source_audio) != reference["provenance"]["source_render"]["sha256"]:
        raise SystemExit("source audio identity mismatch")
    if sha256_file(args.filmora_audio) != reference["provenance"]["filmora_reference"]["sha256"]:
        raise SystemExit("Filmora audio identity mismatch")
    all_review_items = [item for item in report["delta_items"] if item.get("review_required")]
    items = timeline_sample(all_review_items, args.sample_cap)
    rows = []
    outcomes = report["feedback_taxonomy"]["outcomes"]
    reasons = report["feedback_taxonomy"]["reasons"]
    for item in items:
        interval = item["source_interval"]
        source_start = interval["start_sample"] / RATE
        source_end = interval["end_sample"] / RATE
        ref_start = reference_time(source_start, reference["cuts"])
        clip = min(8.0, max(2.0, source_end - source_start + 2.0))
        rows.append(f'''<tr data-id="{html.escape(item['delta_id'])}">
<td><strong>{html.escape(item['delta_id'])}</strong><br><span class="pill">{html.escape(item['kind'])}</span></td>
<td>{source_start:.3f}s–{source_end:.3f}s<br><small>{html.escape(', '.join(item.get('auto_categories', [])) or '—')}</small></td>
<td><button onclick="playClip('source',{max(0,source_start-0.75):.3f},{clip:.3f})">▶ Source</button> <button onclick="playClip('filmora',{max(0,ref_start-0.75):.3f},{clip:.3f})">▶ Filmora</button> <button onclick="stopAll()">⏸</button></td>
<td><select class="outcome"><option value="">选择结论</option>{''.join(f'<option>{html.escape(x)}</option>' for x in outcomes)}</select><br><select class="reason"><option value="">选择原因</option>{''.join(f'<option>{html.escape(x)}</option>' for x in reasons)}</select></td>
<td><input class="note" placeholder="可选备注"></td>
</tr>''')
    metrics = report["metrics"]
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Filmora Calibration Review</title>
<style>body{{font:15px system-ui;margin:24px;max-width:1500px;color:#172033}}h1{{margin-bottom:6px}}.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}.card{{background:#f3f6fb;padding:10px 14px;border-radius:10px}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #d9dfeb;padding:9px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:white}}button,select,input{{padding:6px;margin:2px}}.pill{{background:#fff1ce;border-radius:10px;padding:2px 7px}}.players{{position:sticky;top:0;background:#fff;padding:10px 0;border-bottom:2px solid #172033}}audio{{width:47%;vertical-align:middle}}small{{color:#5b6475}}</style></head><body>
<h1>Filmora Golden Reference 差异复核</h1><p>按差异类型分层、沿时间轴均匀抽样；完整差异保留在机器 JSON。两个播放器互斥，片段自动停止；本页面仅积累校准标签，不批准生产剪辑。</p>
<div class="players"><b>Source</b> <audio id="source" controls preload="metadata" src="{html.escape(args.source_audio.resolve().as_uri())}"></audio><br><b>Filmora</b> <audio id="filmora" controls preload="metadata" src="{html.escape(args.filmora_audio.resolve().as_uri())}"></audio> <button onclick="stopAll()">⏸ 全部暂停</button></div>
<div class="stats"><div class="card">Precision<br><b>{metrics['precision']:.3f}</b></div><div class="card">Recall<br><b>{metrics['recall']:.3f}</b></div><div class="card">Auto-only<br><b>{metrics['auto_only_count']}</b></div><div class="card">Reference-only<br><b>{metrics['reference_only_count']}</b></div><div class="card">抽样 / 全部<br><b>{len(items)} / {len(all_review_items)}</b></div></div>
<button onclick="downloadLabels()">导出已填写 feedback JSON</button>
<table><thead><tr><th>ID / 类型</th><th>Source 时间</th><th>A/B 试听</th><th>标签</th><th>备注</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<script>
const players=[document.getElementById('source'),document.getElementById('filmora')];let timer=null;
players.forEach(p=>p.addEventListener('play',()=>players.filter(x=>x!==p).forEach(x=>x.pause())));
function stopAll(){{if(timer)clearTimeout(timer);players.forEach(p=>p.pause());}}
function playClip(id,start,duration){{stopAll();const p=document.getElementById(id);p.currentTime=start;p.play();timer=setTimeout(()=>p.pause(),duration*1000);}}
function downloadLabels(){{const labels=[...document.querySelectorAll('tbody tr')].map(r=>({{delta_id:r.dataset.id,kind:r.querySelector('.pill').textContent,outcome:r.querySelector('.outcome').value||null,reason:r.querySelector('.reason').value||null,note:r.querySelector('.note').value}}));const payload={{schema_version:'1.0',episode_id:{json.dumps(report['episode_id'])},delta_report_run_key:{json.dumps(report['run_key'])},labels,reviewer:null,reviewed_at:null}};const blob=new Blob([JSON.stringify(payload,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='filmora-calibration-feedback.json';a.click();URL.revokeObjectURL(a.href);}}
</script></body></html>'''
    atomic_text(args.output, page)
    print(json.dumps({"status": "succeeded", "output": str(args.output), "review_item_count": len(items), "sha256": sha256_file(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
