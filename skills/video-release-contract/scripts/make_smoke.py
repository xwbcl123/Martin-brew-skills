"""Generate synthetic, local-only smoke-test package inputs."""

import argparse
import os
import subprocess
import uuid
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw

from package import assemble, atomic_write, canonical, create_seal, executable, profile_channel, render


def fixture(root, profile, channel, *, height=1080, loudness=.21, episode_key=None):
    root.mkdir(mode=0o700)
    nonce = uuid.uuid4().hex
    episode = episode_key or f"smoke-{nonce[:12]}"
    width = height * 16 // 9
    proc = subprocess.run([
        str(executable("ffmpeg")), "-nostdin", "-v", "error", "-hide_banner", "-f", "lavfi",
        "-i", f"color=c=0x172e45:s={width}x{height}:r=30:d=15", "-f", "lavfi",
        "-i", f"aevalsrc={loudness}*sin(2*PI*440*t)|{loudness}*sin(2*PI*440*t):s=48000:d=15",
        "-vf", ("drawgrid=w=iw/8:h=ih/4:t=2:c=0xf2ce75@0.6,drawbox=x=t*100:y=ih/2:"
                "w=iw/10:h=ih/8:c=0xecc46c:t=fill:eval=frame").replace(":eval=frame",""),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-threads", "4",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-metadata", f"comment=synthetic-{nonce}",
        str(root / "delivery.mp4"),
    ], capture_output=True)
    if proc.returncode:
        # Drawbox expressions are intentionally omitted as a fallback to a fixed validation card.
        subprocess.run([
            str(executable("ffmpeg")), "-y", "-nostdin", "-v", "error", "-f", "lavfi",
            "-i", f"testsrc2=s={width}x{height}:r=30:d=15", "-f", "lavfi",
            "-i", f"aevalsrc={loudness}*sin(2*PI*440*t)|{loudness}*sin(2*PI*440*t):s=48000:d=15",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-threads", "4",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-metadata", f"comment=synthetic-{nonce}",
            str(root / "delivery.mp4")
        ], check=True, capture_output=True)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=12)
    qr.add_data(f"ytpub-smoke-v2/{nonce}")
    image = Image.new("RGB", (1280, 720), "#172e45")
    mark = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")
    if mark.width < 360:
        mark = mark.resize((384,384),Image.Resampling.NEAREST)
    image.paste(mark, ((1280-mark.width)//2,(720-mark.height)//2))
    ImageDraw.Draw(image).text((42,46), "YTPUB / PRIVATE SMOKE", fill="#f1ce73")
    image.save(root / "thumbnail.png")
    (root/"track.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\n这是私有测试。\n\n"
                                 "2\n00:00:05,000 --> 00:00:07,000\n画面与音频用于验证。\n\n"
                                 "3\n00:00:09,000 --> 00:00:11,000\n测试结束。\n",encoding="utf-8")
    (root/"reading.md").write_text("这是合成测试视频。它用于验证上传、转码与字幕。\n\n测试结束。\n",encoding="utf-8")
    (root/"enrichment.md").write_text("## 标题候选\n- 私有视频冒烟\n- 视频合成验证\n\n"
                                    "## Chapters\n15 秒合成样本无章节。\n\n"
                                    "## Show Notes\n固定响度和音频源。\n\n"
                                    "## 推广文案\n内部验证素材，仅用于测试。\n",encoding="utf-8")
    (root/"credits.txt").write_text("Self-produced synthetic footage, test tone, and original thumbnail.\n",
                                   encoding="utf-8")
    return {
        "contract_version":"1.0","episode_key":episode,"channel_profile":profile,
        "target_channel_id":channel,"package_revision":1,"region_code":"US","format":"landscape",
        "delivery_video":"delivery.mp4","thumbnail":"thumbnail.png","reading_transcript":"reading.md",
        "enrichment_pack":"enrichment.md","credits":"credits.txt",
        "captions":[{"language":"zh-Hans","name":"Smoke ZH","isDraft":False,"file":"track.srt"}],
        "snippet":{"title":f"Private synthetic smoke {nonce[:8]}","description":"Synthetic private upload test.",
                   "tags":[],"categoryId":"22","defaultLanguage":"en","defaultAudioLanguage":"zh-Hans"},
        "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False,"containsSyntheticMedia":False},
        "paidProductPlacementDetails":{"hasPaidProductPlacement":False},
        "chapters":[],"chapter_exemption":None,"playlist_ids":[],
        "rights":{"third_party":False,"declaration_ref":"self-produced-synthetic-test"},
        "notifySubscribers":False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory",required=True,type=Path)
    parser.add_argument("--profile",default="smoke-test")
    parser.add_argument("--config",type=Path)
    parser.add_argument("--chapter-exemption")
    args=parser.parse_args()
    os.umask(0o077)
    channel=profile_channel(args.profile,args.config)
    args.directory.mkdir(mode=0o700,parents=True)
    package=args.directory/"package"
    request=fixture(package,args.profile,channel)
    request["chapter_exemption"]=args.chapter_exemption
    assemble(package,request,args.profile)
    report=create_seal(package,args.profile,config=args.config)
    if report["contract_passed"]:
        report=render(package,args.profile,args.directory/"video-release-preview.html",config=args.config)
    atomic_write(args.directory/"acceptance-report.json",canonical(report)+b"\n")
    print(canonical(report).decode())
    return 0 if report["contract_passed"] and report["human_preview_ready"] else 1


if __name__=="__main__":
    raise SystemExit(main())
