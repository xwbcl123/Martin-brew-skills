#!/usr/bin/env python3
"""Render a hash-verified cue-by-cue subtitle review page and H4 receipt exporter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import tempfile


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_ms(value: str) -> int:
    pieces = value.replace(",", ".").split(":")
    if len(pieces) == 2: hours = 0; minutes, seconds = pieces
    else: hours, minutes, seconds = pieces
    return round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)


def cues(path: pathlib.Path) -> list[dict]:
    text = path.read_text(encoding="utf-8"); timing = re.compile(r"(?m)^(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})")
    matches = list(timing.finditer(text)); output = []
    for index, match in enumerate(matches):
        limit = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        lines = [line.strip() for line in text[match.end():limit].splitlines() if line.strip() and not line.strip().isdigit()]
        output.append({"cue": index + 1, "start_ms": parse_ms(match.group(1)), "end_ms": parse_ms(match.group(2)), "text": "\n".join(lines)})
    return output


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(value); temporary = pathlib.Path(handle.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--validation-report", type=pathlib.Path, required=True)
    parser.add_argument("--subs", type=pathlib.Path, required=True); parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(); report = json.loads(args.validation_report.read_text(encoding="utf-8"))
    if report.get("stage") != "S11-postcut-text-validation": raise SystemExit("not an S11 validation report")
    if report["timed_subs"]["sha256"] != sha256(args.subs): raise SystemExit("subtitle bytes do not match validation report")
    video = report["delivery_profile"] == "video"; media_record = report["final_video"] if video else report["release_audio"]
    media = pathlib.Path(media_record["path"])
    if not media.is_file() or sha256(media) != media_record["sha256"]: raise SystemExit("review media identity mismatch")
    violations = report["timeline_qc"]["violations"]
    payload = {"episode_id": report["episode_id"], "delivery_profile": report["delivery_profile"], "video": video,
               "media_url": os.path.relpath(media, args.output.parent), "cues": cues(args.subs), "violations": violations,
               "identities": {"release_audio_sha256": report["release_audio"]["sha256"],
                   "raw_transcript_json_sha256": report["raw_transcript"]["raw_json"]["sha256"],
                   "verbatim_sha256": report["verbatim"]["sha256"], "timed_subs_sha256": report["timed_subs"]["sha256"],
                   "correction_ledger_sha256": report["correction_ledger"]["sha256"],
                   "subtitle_profile_sha256": report["subtitle_profile"]["sha256"]},
               "final_video_sha256": report["final_video"]["sha256"] if video else None,
               "qc_passed": report["timeline_qc"]["passed"]}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"); media_tag = "video" if video else "audio"
    html = """<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Subtitle Review</title><style>body{margin:0;background:#08121f;color:#edf7ff;font:16px system-ui}main{max-width:1100px;margin:auto;padding:26px}.card,.cue{background:#10243a;border:1px solid #2d4d68;border-radius:12px;padding:16px;margin:12px 0}MEDIA{width:100%;max-height:520px}.cue{display:grid;grid-template-columns:120px 1fr 120px;gap:14px}.bad{border-color:#ff8b75}.ok{color:#62e6aa}.warn{color:#ffcc70}button{padding:8px 11px}.sticky{position:sticky;bottom:0;background:#08121fee;padding:14px}.checks label{display:block;margin:6px}</style></head><body><main><section class=\"card\"><h1>Accurate Subtitle Review</h1><p>逐 cue 跳转复核；技术 QC 不能替代术语、speaker、语义、timing 和视觉审核。</p><MEDIA id=\"media\" controls preload=\"metadata\"></MEDIA><p id=\"qc\"></p></section><section id=\"cues\"></section><section class=\"sticky checks\"><label><input type=\"checkbox\" data-gate> 术语准确</label><label><input type=\"checkbox\" data-gate> Speaker attribution 准确</label><label><input type=\"checkbox\" data-gate> 语义忠实</label><label><input type=\"checkbox\" data-gate> Timing 已复核</label><label id=\"visualRow\"><input type=\"checkbox\" data-gate> 视频字幕视觉与 safe area 已复核</label><label>Reviewer <input id=\"reviewer\" value=\"Martin\"></label><button id=\"export\" disabled>导出 H4 approval</button></section></main><script>const D=__DATA__,m=document.querySelector('#media'),esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));m.src=D.media_url;document.querySelector('#qc').innerHTML=D.qc_passed?'<b class=\"ok\">Technical subtitle QC passed</b>':`<b class=\"warn\">QC violations: ${D.violations.length}</b>`;if(!D.video)document.querySelector('#visualRow').remove();const bad=new Set(D.violations.filter(v=>v.cue).map(v=>v.cue));document.querySelector('#cues').innerHTML=D.cues.map(c=>`<article class=\"cue ${bad.has(c.cue)?'bad':''}\"><div>#${c.cue}<br>${(c.start_ms/1000).toFixed(3)}s</div><div>${esc(c.text).replace(/\\n/g,'<br>')}</div><button onclick=\"m.currentTime=${c.start_ms/1000};m.play()\">▶ 跳转试听</button></article>`).join('');const boxes=[...document.querySelectorAll('[data-gate]')],button=document.querySelector('#export');document.addEventListener('change',()=>button.disabled=!D.qc_passed||!boxes.every(b=>b.checked));button.onclick=()=>{const who=document.querySelector('#reviewer').value.trim();if(!who)return alert('Reviewer required');const x={gate:'H4-postcut-text',status:'approved',episode_id:D.episode_id,delivery_profile:D.delivery_profile,...D.identities,terminology_review:'approved',speaker_review:'approved',semantic_review:'approved',timing_review:'approved',approved_by:who,approved_at:new Date().toISOString(),publish_authorized:false};if(D.video){x.final_video_sha256=D.final_video_sha256;x.subtitle_visual_review='approved'}const blob=new Blob([JSON.stringify(x,null,2)+'\\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${D.episode_id}-H4-postcut-text.json`;a.click();URL.revokeObjectURL(a.href)};</script></body></html>"""
    html = html.replace("MEDIA", media_tag).replace("__DATA__", data)
    atomic_text(args.output, html)
    print(json.dumps({"status": "review_required", "output": str(args.output), "sha256": sha256(args.output),
                      "cue_count": len(payload["cues"]), "technical_qc_passed": payload["qc_passed"],
                      "publish_authorized": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
