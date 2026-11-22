import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from make_smoke import fixture
from package import assemble, canonical, check, create_seal, fixture_projection, render

CHANNEL="UC"+"A"*22


@pytest.fixture(scope="module")
def original(tmp_path_factory):
    root=tmp_path_factory.mktemp("release")
    media=root/"media"
    config=root/"profiles.json"
    config.write_bytes(canonical({"profiles":{"smoke-test":CHANNEL,"elsewhere":"UC"+"B"*22}}))
    source=fixture(media,"smoke-test",CHANNEL)
    assemble(media,source,"smoke-test")
    return media,config


def edit(root, edit_manifest):
    current=json.loads((root/"video-package.json").read_text())
    edit_manifest(current)
    m,payload=fixture_projection(root,current)
    (root/"video-package.json").write_bytes(canonical(m))
    (root/"youtube_payload.json").write_bytes(payload)


def test_positive_seal_preview(original,tmp_path):
    orig,config=original
    root=tmp_path/"package"
    shutil.copytree(orig,root)
    result=create_seal(root,"smoke-test",config=config)
    assert result["contract_passed"],result
    preview=tmp_path/"video-release-preview.html"
    result=render(root,"smoke-test",preview,config=config)
    assert result["human_preview_ready"] and not result["publish_authorized"],result
    assert "file:" in preview.read_text()
    assert render(root,"smoke-test",preview,config=config,write=False)["human_preview_ready"]
    preview.write_text("tampered")
    assert render(root,"smoke-test",preview,config=config,write=False)["gates"][-1]["status"]=="fail"


@pytest.mark.parametrize("case, gate",[
    ("missing_field",1),("path_escape",1),("newline_episode",1),("newline_path",1),
    ("symlink",1),("hash_drift",2),("unknown_file",2),("alignment_hash",2),("missing_seal",2),
    ("description",5),("title_newline",5),("tags",5),("category",5),("chapters",6),
    ("missing_disclosure",7),("scheduled",7),("localized_description",8),("square_thumb",9),
    ("multiline_srt",10),("long_srt",10),("filler_srt",10),("empty_reading",10),
    ("missing_enrichment",11),("missing_credits",12),("credential_canary",1),("wrong_profile",13)
])
def test_negative(original,tmp_path,case,gate):
    orig,config=original
    root=tmp_path/"package"
    shutil.copytree(orig,root)
    manifest=root/"video-package.json"
    def raw_change(callback):
        m=json.loads(manifest.read_text())
        callback(m)
        manifest.write_bytes(canonical(m))
    if case=="missing_field":
        raw_change(lambda m:m.pop("episode_key"))
    elif case=="path_escape":
        raw_change(lambda m:m["thumbnail"].update(path="../thumbnail.png"))
    elif case=="newline_episode":
        raw_change(lambda m:m.update(episode_key="bad\n"))
    elif case=="newline_path":
        raw_change(lambda m:m["thumbnail"].update(path="thumbnail.png\n"))
    elif case=="symlink":
        (root/"thumbnail.png").unlink()
        (root/"thumbnail.png").symlink_to(orig/"thumbnail.png")
    elif case=="hash_drift":
        with (root/"delivery.mp4").open("ab") as f:
            f.write(b"x")
    elif case=="unknown_file":
        (root/"note.txt").write_text("extra")
    elif case=="alignment_hash":
        raw_change(lambda m:m["captions"][0].update(aligned_video_sha256="0"*64))
    elif case=="description":
        edit(root,lambda m:m["snippet"].update(description="中"*1667))
    elif case=="title_newline":
        edit(root,lambda m:m["snippet"].update(title="Embedded\nnewline"))
    elif case=="tags":
        edit(root,lambda m:m["snippet"].update(tags=["a"*498,"b c"]))
    elif case=="category":
        edit(root,lambda m:m["snippet"].update(categoryId="666"))
    elif case=="chapters":
        edit(root,lambda m:m.update(chapters=[{"start_seconds":1,"title":"bad"}]))
    elif case=="missing_disclosure":
        raw_change(lambda m:m["status"].pop("containsSyntheticMedia"))
    elif case=="scheduled":
        edit(root,lambda m:m["status"].update(publishAt="2099-01-01T00:00:00Z"))
    elif case=="localized_description":
        edit(root,lambda m:m.update(localizations={"en":{"title":"Valid","description":"中"*1667}}))
    elif case=="square_thumb":
        Image.new("RGB",(1280,1280)).save(root/"thumbnail.png")
        edit(root,lambda m:None)
    elif case in {"multiline_srt","long_srt","filler_srt","empty_reading","missing_enrichment","credential_canary"}:
        files={
            "multiline_srt":("track.srt","1\n00:00:01,000 --> 00:00:03,000\nfirst\nsecond\n"),
            "long_srt":("track.srt","1\n00:00:01,000 --> 00:00:03,000\n"+"中"*19+"\n"),
            "filler_srt":("track.srt","1\n00:00:01,000 --> 00:00:03,000\n呃，测试。\n"),
            "empty_reading":("reading.md"," "),
            "missing_enrichment":("enrichment.md","# Incomplete"),
            "credential_canary":("reading.md","Secret: ya29.unit-test-fake-token.\n")}
        file,text=files[case]
        (root/file).write_text(text)
        edit(root,lambda m:None)
    elif case=="missing_credits":
        (root/"credits.txt").unlink()
    report,_=check(root,"elsewhere" if case=="wrong_profile" else "smoke-test",config=config,
                   require_seal=case=="missing_seal")
    assert not report["contract_passed"],(case,report)
    assert report["gates"][gate-1]["status"]=="fail",(case,report)


@pytest.mark.parametrize("height,loudness,gate",[(720,.21,3),(1080,.03,4)])
def test_decoded_technical_negatives(tmp_path,height,loudness,gate):
    root=tmp_path/"package"
    profile=tmp_path/"profiles.json"
    profile.write_bytes(canonical({"smoke-test":CHANNEL}))
    source=fixture(root,"smoke-test",CHANNEL,height=height,loudness=loudness)
    assemble(root,source,"smoke-test")
    report,_=check(root,"smoke-test",config=profile)
    assert report["gates"][gate-1]["status"]=="fail",report


def test_repeated_assembly_and_presentation(original, tmp_path):
    candidate, config = original
    package = tmp_path / "package"
    shutil.copytree(candidate, package)
    manifest = (package / "video-package.json").read_bytes()
    payload = (package / "youtube_payload.json").read_bytes()
    projected, request = fixture_projection(package, json.loads(manifest))
    assert canonical(projected) == manifest and request == payload
    assert create_seal(package, "smoke-test", config=config)["contract_passed"]
    sealed = (package / "seal.json").read_bytes()
    preview = tmp_path / "preview.html"
    first = render(package, "smoke-test", preview, config=config)
    preview_bytes = preview.read_bytes()
    second = render(package, "smoke-test", preview, config=config)
    assert first["preview_sha256"] == second["preview_sha256"]
    assert (package / "seal.json").read_bytes() == sealed and preview.read_bytes() == preview_bytes


@pytest.mark.parametrize("payload_artifact", ["track.srt", "youtube_payload.json"])
def test_sealed_byte_drift(original, tmp_path, payload_artifact):
    candidate, config = original
    package = tmp_path / "package"
    shutil.copytree(candidate, package)
    assert create_seal(package, "smoke-test", config=config)["contract_passed"]
    target = package / payload_artifact
    old = target.read_bytes()
    target.write_bytes(old + b" " if payload_artifact.endswith(".json") else old[:-1] + b" ")
    report, _ = check(package, "smoke-test", config=config, require_seal=True)
    assert not report["publish_authorized"] and report["gates"][1]["status"] == "fail"


@pytest.mark.parametrize(("span", "warning"), [(1499, True), (1500, False), (3500, False), (3501, True)])
def test_subtitle_warning_boundaries(original, tmp_path, span, warning):
    from package import subtitles_check

    candidate, _ = original
    package = tmp_path / "package"
    shutil.copytree(candidate, package)
    end = 1000 + span
    (package / "track.srt").write_text(
        f"1\n00:00:01,000 --> 00:00:{end//1000:02},{end%1000:03}\n校验字幕。\n", encoding="utf-8")
    manifest = json.loads((package / "video-package.json").read_bytes())
    assert ("cue_duration_target" in subtitles_check(
        package, manifest, 15, {"filler_terms": [], "term_replacements": {}})) is warning


def test_blocked_term_is_not_reported(original, tmp_path, monkeypatch):
    import package as contract

    candidate, config = original
    package = tmp_path / "package"
    shutil.copytree(candidate, package)
    term = "SyntheticCustomerCanary"
    edit(package, lambda m: m["snippet"].update(description=term))
    load_json = contract.load_json

    def injected_policy(path):
        value = load_json(path)
        return {**value, "blocked_terms": [term]} if Path(path).name == "policy.json" else value

    monkeypatch.setattr(contract, "load_json", injected_policy)
    report, _ = check(package, "smoke-test", config=config)
    assert report["gates"][11]["status"] == "fail" and term not in json.dumps(report)


def test_last_chapter_must_have_ten_seconds(original, tmp_path):
    import subprocess
    from package import executable

    candidate, config = original
    package = tmp_path / "package"
    shutil.copytree(candidate, package)
    temporary = tmp_path / "replacement.mp4"
    tone = ".21*sin(2*PI*440*t)"
    subprocess.run([str(executable("ffmpeg")), "-nostdin", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=0x172e45:s=1920x1080:r=30:d=130", "-f", "lavfi",
                    "-i", f"aevalsrc={tone}|{tone}:s=48000:d=130", "-c:v", "libx264", "-preset",
                    "ultrafast", "-pix_fmt", "yuv420p", "-threads", "4", "-c:a", "aac", str(temporary)],
                   check=True, capture_output=True)
    temporary.replace(package / "delivery.mp4")
    description = "0:00 First\n1:00 Second\n2:01 Third"
    with (package / "enrichment.md").open(encoding="utf-8") as stream:
        enrichment = stream.read()
    (package / "enrichment.md").write_text(enrichment.replace("15 秒合成样本无章节。", description))
    def chapters(m):
        m["snippet"]["description"] = description
        m["chapters"] = [{"start_seconds": value, "title": title}
                         for value, title in [(0, "First"), (60, "Second"), (121, "Third")]]
    edit(package, chapters)
    report, _ = check(package, "smoke-test", config=config)
    assert report["gates"][5]["status"] == "fail", report
    assert [row["code"] for row in report["gates"][5]["errors"]] == ["chapter_order_or_minimum_duration"]


def test_real_true_peak_fails_independently_of_loudness(original, tmp_path):
    import re
    import subprocess
    from package import audio_qc, executable, Invalid, probe_media

    source, _ = original
    candidate = tmp_path / "peak.mov"
    pulse = "if(between(t,5,5.005),0.944,0.21)*sin(2*PI*440*t)"
    generator = f"aevalsrc='{pulse}|{pulse}':s=48000:d=15"
    ffmpeg = str(executable("ffmpeg"))
    subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-i", str(source / "delivery.mp4"),
                    "-f", "lavfi", "-i", generator, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "pcm_s24le", str(candidate)],
                   check=True, capture_output=True)
    summary = subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-i", str(candidate),
                              "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"],
                             check=True, capture_output=True).stderr.decode().rsplit("Summary:", 1)[-1]
    assert abs(float(re.search(r"I:\s*(-?[\d.]+) LUFS", summary)[1]) + 14) <= 1
    assert float(re.search(r"Peak:\s*(-?[\d.]+) dBFS", summary)[1]) > -1
    with pytest.raises(Invalid, match="loudness_or_true_peak"):
        audio_qc(candidate, "smoke-test", probe_media(candidate))


@pytest.mark.parametrize("extension", ["gif", "bmp"])
def test_thumbnail_excludes_non_youtube_formats(tmp_path, extension):
    from package import Invalid, thumbnail_check

    file = tmp_path / ("test." + extension)
    Image.new("RGB", (1280, 720)).save(file)
    with pytest.raises(Invalid, match="thumbnail_format"):
        thumbnail_check(file, file.stat().st_size)


def test_thumbnail_size_boundary(original):
    from package import Invalid, thumbnail_check

    image = original[0] / "thumbnail.png"
    assert thumbnail_check(image, 50_000_000)[0]["width"] == 1280
    with pytest.raises(Invalid, match="thumbnail_size"):
        thumbnail_check(image, 50_000_001)
