#!/usr/bin/env python3
"""Render a risk-sampled, mutually exclusive Origin-vs-Edited H2 review page."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile

from human_review_sampling import RATE, build_plan, canonical_hash, risk_tier


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(value); temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edl", type=pathlib.Path, required=True)
    parser.add_argument("--render-report", type=pathlib.Path, required=True)
    parser.add_argument("--original-audio", type=pathlib.Path, required=True)
    parser.add_argument("--edited-audio", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    edl = json.loads(args.edl.read_text(encoding="utf-8")); report = json.loads(args.render_report.read_text(encoding="utf-8"))
    for path in (args.original_audio, args.edited_audio, args.render_report):
        if not path.is_file() or not path.stat().st_size: raise SystemExit(f"missing/empty review input: {path}")
    if report.get("edl", {}).get("sha256") != sha256(args.edl): raise SystemExit("render report does not bind this EDL")
    if report.get("source_audio", {}).get("sha256") != sha256(args.original_audio): raise SystemExit("render report does not bind original audio")
    if report.get("output_audio", {}).get("sha256") != sha256(args.edited_audio): raise SystemExit("render report does not bind edited audio")
    transitions = report.get("mapping", {}).get("crossfade_transitions", [])
    if len(transitions) != len(edl["cuts"]): raise SystemExit("render report transition count does not match EDL cuts")
    plan = build_plan(edl); plan_sha = canonical_hash(plan); required = set(plan["required_review_cut_ids"])
    sample_group = {cut_id: stratum["stratum_id"] for stratum in plan["strata"] for cut_id in stratum["sample_cut_ids"]}
    targeted = set(plan["targeted_cut_ids"]); cuts = []
    for item, transition in zip(edl["cuts"], transitions):
        interval = item["applied_interval"]; source_start = interval["start_sample"] / RATE; source_end = interval["end_sample"] / RATE
        edited_join_start = transition["release_start_sample"] / RATE; edited_join_end = transition["release_end_sample"] / RATE
        cuts.append({"cut_id": item["cut_id"], "candidate_ids": item["candidate_ids"], "categories": item["categories"],
                     "risk_tier": risk_tier(item), "review_required": item["cut_id"] in required,
                     "review_reason": "targeted" if item["cut_id"] in targeted else sample_group.get(item["cut_id"], "optional"),
                     "source_start": source_start, "source_end": source_end, "duration": source_end - source_start,
                     "origin_clip_start": max(0, source_start - 1.0), "origin_clip_end": source_end + 1.5,
                     "edited_join_start": edited_join_start, "edited_join_end": edited_join_end,
                     "edited_clip_start": max(0, edited_join_start - 1.0), "edited_clip_end": edited_join_end + 1.5})
    payload = {"episode_id": edl["episode_id"], "edl_sha256": sha256(args.edl),
               "render_report_sha256": sha256(args.render_report), "edited_audio_sha256": sha256(args.edited_audio),
               "review_plan": plan, "review_plan_sha256": plan_sha, "cuts": cuts,
               "original_url": os.path.relpath(args.original_audio, args.output.parent),
               "edited_url": os.path.relpath(args.edited_audio, args.output.parent)}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Human Restore Review</title>
<style>:root{color-scheme:dark;--bg:#07111f;--card:#102238;--line:#294762;--text:#edf7ff;--muted:#9bb3c8;--ok:#5ee6a8;--warn:#ffca69;--bad:#ff8674}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px system-ui;line-height:1.5}main{max-width:1200px;margin:auto;padding:24px}.hero,.row,.protocol{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px}.players{display:grid;grid-template-columns:1fr 1fr;gap:14px}audio{width:100%}.row{display:grid;grid-template-columns:150px 1fr 260px;gap:14px;align-items:center}.mono{font-family:ui-monospace,monospace}.muted{color:var(--muted)}button{border:0;border-radius:8px;padding:9px 12px;cursor:pointer;margin:3px}.active{outline:2px solid var(--warn)}.restore{color:var(--warn);font-weight:700}.accept,.pass{color:var(--ok);font-weight:700}.fail{color:var(--bad);font-weight:700}.sticky{position:sticky;bottom:0;background:#07111fee;padding:12px;border-top:1px solid var(--line);z-index:5}.badge{padding:3px 7px;border-radius:10px;background:#294762}.required{border-color:#6c8ead}.listened{font-weight:700}input[type=text]{width:180px;padding:8px}@media(max-width:780px){.players,.row{grid-template-columns:1fr}}</style></head><body><main>
<section class=\"hero\"><h1>Origin vs. Edited · Risk-Sampled H2 Review</h1><p>默认只显示风险定向点与分层抽样点。每次播放固定短片段并自动暂停；Origin 与 Edited 永远互斥，不会混声。抽样层每层出现 <b>2 个及以上错剪即不通过</b>。</p><div class=\"players\"><div><b>ORIGIN</b><audio id=\"origin\" controls preload=\"metadata\"></audio></div><div><b>EDITED</b><audio id=\"edited\" controls preload=\"metadata\"></audio></div></div><button onclick=\"pauseAll()\">⏸ 全部暂停</button> <button id=\"toggle\">显示全部（可选）</button><p class=\"mono muted\" id=\"proof\"></p></section>
<section class=\"protocol\" id=\"protocol\"></section><section id=\"rows\"></section><section class=\"sticky\"><label>Reviewer <input id=\"reviewer\" type=\"text\" value=\"Martin\"></label> <button onclick=\"pauseAll()\">⏸ 暂停</button> <button id=\"export\" disabled>导出 H2 receipt.json</button> <span id=\"summary\"></span></section>
</main><script>const D=__DATA__,origin=document.querySelector('#origin'),edited=document.querySelector('#edited'),esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));origin.src=D.original_url;edited.src=D.edited_url;let timer=null,showAll=false;const byId=Object.fromEntries(D.cuts.map(c=>[c.cut_id,c]));
function pauseAll(){clearTimeout(timer);timer=null;origin.pause();edited.pause();document.querySelectorAll('.row').forEach(x=>x.classList.remove('active'))}origin.addEventListener('play',()=>{if(!edited.paused)edited.pause()});edited.addEventListener('play',()=>{if(!origin.paused)origin.pause()});function playClip(kind,id){pauseAll();const c=byId[id],player=kind==='origin'?origin:edited,start=kind==='origin'?c.origin_clip_start:c.edited_clip_start,end=kind==='origin'?c.origin_clip_end:c.edited_clip_end;document.querySelector(`[data-row=\"${id}\"]`).classList.add('active');player.currentTime=start;const stop=()=>{if(player.currentTime>=end){player.pause();player.removeEventListener('timeupdate',stop)}};player.addEventListener('timeupdate',stop);timer=setTimeout(()=>{player.pause();player.removeEventListener('timeupdate',stop)},Math.max(500,(end-start+0.4)*1000));player.play()}
function row(c,i){return `<article class=\"row ${c.review_required?'required':'optional'}\" data-row=\"${esc(c.cut_id)}\"><div><b class=\"mono\">${esc(c.cut_id)}</b><br><span class=\"badge\">${esc(c.risk_tier)} · ${esc(c.review_reason)}</span><br><span class=\"muted\">source ${c.source_start.toFixed(3)}–${c.source_end.toFixed(3)}s<br>edited join ${c.edited_join_start.toFixed(3)}s</span></div><div><b>${c.categories.map(esc).join(' / ')}</b><br><span class=\"muted\">${c.candidate_ids.map(esc).join(', ')} · cut ${c.duration.toFixed(3)}s</span><br><button onclick=\"playClip('origin','${esc(c.cut_id)}')\">▶ Origin 短听</button><button onclick=\"playClip('edited','${esc(c.cut_id)}')\">▶ Edited 短听</button><button onclick=\"pauseAll()\">⏸</button></div><div><label class=\"accept\"><input type=\"radio\" name=\"d${i}\" value=\"accept_cut\" checked> 接受剪切</label><br><label class=\"restore\"><input type=\"radio\" name=\"d${i}\" value=\"restore_source\"> 恢复原声</label><br><label class=\"listened\"><input type=\"checkbox\" class=\"heard\" data-id=\"${esc(c.cut_id)}\"> 已完成 A/B 试听</label><br><input class=\"note\" data-i=\"${i}\" placeholder=\"可选备注\"></div></article>`}
function decisions(){return D.cuts.map((c,i)=>{const heard=document.querySelector(`.heard[data-id=\"${c.cut_id}\"]`);return heard&&heard.checked?{cut_id:c.cut_id,action:document.querySelector(`input[name=d${i}]:checked`).value,listened:true,note:document.querySelector(`.note[data-i=\"${i}\"]`).value}:null}).filter(Boolean)}function evaluate(ds){const actions=Object.fromEntries(ds.map(x=>[x.cut_id,x.action]));const strata=D.review_plan.strata.map(s=>{const ids=s.sample_cut_ids.filter(id=>actions[id]==='restore_source');return {stratum_id:s.stratum_id,sample_count:s.sample_count,restore_count:ids.length,restored_cut_ids:ids,passed:ids.length<s.fail_at_restore_count}});const failed=strata.filter(x=>!x.passed).map(x=>x.stratum_id);return {strata,failed_strata:failed,sampling_passed:failed.length===0}}
function update(){const ds=decisions(),heard=new Set(ds.map(x=>x.cut_id)),missing=D.review_plan.required_review_cut_ids.filter(id=>!heard.has(id)),ev=evaluate(ds),restored=ds.filter(x=>x.action==='restore_source').length;document.querySelector('#summary').innerHTML=`${D.review_plan.required_review_count-missing.length}/${D.review_plan.required_review_count} required heard · ${restored} restored · <span class=\"${ev.sampling_passed?'pass':'fail'}\">${ev.sampling_passed?'sampling pass':'sampling fail: '+ev.failed_strata.join(', ')}</span>`;document.querySelector('#export').disabled=missing.length>0;return {ds,missing,ev}}
function visibility(){document.querySelectorAll('.optional').forEach(x=>x.hidden=!showAll);document.querySelector('#toggle').textContent=showAll?'只显示必审抽样点':'显示全部（可选）'}function draw(){document.querySelector('#rows').innerHTML=D.cuts.map((c,i)=>row(c,i)).join('');visibility();update()}document.querySelector('#toggle').onclick=()=>{pauseAll();showAll=!showAll;visibility()};document.addEventListener('change',e=>{if(e.target.matches('.heard,input[type=radio]'))update()});document.querySelector('#proof').textContent=`EDL ${D.edl_sha256} · RENDER ${D.render_report_sha256} · EDITED ${D.edited_audio_sha256} · PLAN ${D.review_plan_sha256}`;document.querySelector('#protocol').innerHTML=`<b>抽检协议</b>：${D.review_plan.required_review_count}/${D.review_plan.total_cut_count} 个必审点（targeted ${D.review_plan.targeted_cut_ids.length}；${D.review_plan.strata.map(s=>`${s.stratum_id} ${s.sample_count}`).join('；')}）。每个 sample stratum 最多允许 1 个 restore；第 2 个即失败并要求扩大复核或修改规则。`;
document.querySelector('#export').onclick=()=>{pauseAll();const who=document.querySelector('#reviewer').value.trim();if(!who)return alert('Reviewer required');const {ds,missing,ev}=update();if(missing.length)return alert('还有必审点未完成');const receipt={schema_version:'1.1',episode_id:D.episode_id,gate:'H2-human-restore-review',status:ev.sampling_passed?'approved':'failed',review_complete:true,edl_sha256:D.edl_sha256,render_report_sha256:D.render_report_sha256,edited_audio_sha256:D.edited_audio_sha256,review_plan_sha256:D.review_plan_sha256,review_protocol_id:D.review_plan.protocol_id,default_action:'accept_cut',decisions:ds,sampling_evaluation:ev,reviewed_by:who,reviewed_at:new Date().toISOString(),publish_authorized:false};const blob=new Blob([JSON.stringify(receipt,null,2)+'\\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${D.episode_id}-H2-human-restore-review.json`;a.click();URL.revokeObjectURL(a.href)};draw();</script></body></html>"""
    atomic_text(args.output, html.replace("__DATA__", data))
    print(json.dumps({"status": "review_required", "output": str(args.output), "sha256": sha256(args.output),
                      "cut_count": len(cuts), "required_review_count": plan["required_review_count"],
                      "targeted_count": len(plan["targeted_cut_ids"]),
                      "sample_counts": {item["stratum_id"]: item["sample_count"] for item in plan["strata"]},
                      "default_action": "accept_cut", "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
