"""Offline video-package validation, sealing, and local preview."""

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import langcodes
import regex
from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"
MANIFEST = "video-package.json"
PAYLOAD = "youtube_payload.json"
SEAL = "seal.json"
CSP = ("default-src 'none'; img-src file:; media-src file:; style-src 'none'; "
       "script-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; "
       "base-uri 'none'; form-action 'none'")
ROLES = ("delivery_video", "thumbnail", "reading_transcript", "enrichment_pack", "credits", "youtube_payload")
GATES = (
    "SCHEMA_SEMANTICS", "ARTIFACT_HASH_CLOSURE", "VIDEO_TECHNICAL_QC", "AUDIO_LOUDNESS_QC",
    "SNIPPET_METADATA", "CHAPTERS_INTEGRITY", "STATUS_COMPLIANCE", "LOCALIZATIONS", "THUMBNAIL_SPEC",
    "DUAL_TRACK_SUBTITLES", "ENRICHMENT_SEPARATION", "RIGHTS_CREDITS_SAFETY", "CHANNEL_PROFILE_MATCH",
    "PREVIEW_PREFLIGHT",
)
FILEPATH = re.compile(r"(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*[A-Za-z0-9_-][A-Za-z0-9._-]*")
CHANNEL = re.compile(r"UC[A-Za-z0-9_-]{22}")
PROTECTED = re.compile(
    r"(?i)(?:\bBearer\s+[\w.~+/=-]{8,}|\bya29\.[\w.-]+|\bGOCSPX-[\w-]+|"
    r"\b1//[\w-]{8,}|(?:access_token|refresh_token|client_secret|upload_id|"
    r"x-goog-signature)\s*[=:]\s*[^\s&]{5,})"
)
STAMP = re.compile(r"(?P<time>\d{1,4}:\d\d(?::\d\d)?)\s+(?:[-–—]\s+)?(?P<title>\S.*)")
TIMING = re.compile(r"(\d{2,}:\d\d:\d\d[,.]\d{3}|\d\d:\d\d\.\d{3})\s+-->\s+"
                    r"(\d{2,}:\d\d:\d\d[,.]\d{3}|\d\d:\d\d\.\d{3})")


class Invalid(Exception):
    def __init__(self, gate, reason, location=None):
        super().__init__(reason)
        self.gate, self.reason, self.location = gate, reason, location


def demand(condition, gate, reason, location=None):
    if not condition:
        raise Invalid(gate, reason, location)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object field")
        value[key] = item
    return value


def json_data(data):
    def invalid(_):
        raise ValueError("non-finite JSON")

    value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates, parse_constant=invalid)
    canonical(value)
    return value


def sync_directory(path):
    fd = os.open(path, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, data, *, exclusive=False):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".video-")
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if exclusive:
            os.link(temporary, path)
            os.unlink(temporary)
        else:
            if path.is_symlink():
                raise OSError("symbolic output path")
            os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def clean_identifier(value):
    return (value == value.strip() and bool(value) and
            not any(unicodedata.category(c) == "Cc" or c in "\u2028\u2029" for c in value))


def valid_rel(relative):
    return isinstance(relative, str) and FILEPATH.fullmatch(relative) and clean_identifier(relative)


def artifact_open(root, relative):
    demand(valid_rel(relative), 1, "invalid_artifact_path")
    parts = PurePosixPath(relative).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        root_dev = os.fstat(fd).st_dev
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            demand(st.st_dev == root_dev and st.st_uid == os.getuid() and not st.st_mode & 0o022,
                   1, "unsafe_artifact_directory")
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        st = os.fstat(file_fd)
        if not (stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_dev == root_dev and
                st.st_uid == os.getuid() and not st.st_mode & 0o022):
            os.close(file_fd)
            raise Invalid(1, "unsafe_artifact")
        return os.fdopen(file_fd, "rb")
    except OSError as exc:
        raise Invalid(1, "artifact_missing_or_unsafe") from exc
    finally:
        os.close(fd)


def local_bytes(root, filename, *, cap=2_000_000):
    with artifact_open(root, filename) as file:
        data = file.read(cap + 1)
    demand(len(data) <= cap, 1, "artifact_exceeds_local_read_limit")
    return data


def file_info(root, relative):
    with artifact_open(root, relative) as file:
        size = os.fstat(file.fileno()).st_size
        value = hashlib.file_digest(file, "sha256").hexdigest()
    return {"path": relative, "bytes": size, "sha256": value}


def load_json(path):
    return json_data(Path(path).read_bytes())


def config_profiles(path=None):
    selected = path or os.environ.get("VIDEO_SKILLS_CONFIG") or Path.home() / ".config/video-skills/config.json"
    values = load_json(selected)
    demand(isinstance(values, dict), 13, "profile_config_invalid")
    profiles = values.get("profiles", values)
    demand(isinstance(profiles, dict), 13, "profile_config_invalid")
    return profiles


def profile_channel(profile, path=None):
    try:
        channel = config_profiles(path).get(profile)
        if isinstance(channel, dict):
            channel = channel.get("channel_id")
        demand(isinstance(channel, str) and CHANNEL.fullmatch(channel), 13, "profile_channel_unconfigured")
        return channel
    except (OSError, ValueError, TypeError) as exc:
        raise Invalid(13, "profile_config_missing_or_invalid") from exc


def wire_payload(manifest):
    snippet = {k: v for k, v in manifest["snippet"].items() if k != "defaultAudioLanguage"}
    if not snippet.get("tags"):
        snippet.pop("tags", None)
    return {"snippet": snippet, "status": manifest["status"],
            "paidProductPlacementDetails": manifest["paidProductPlacementDetails"],
            **({"localizations": manifest["localizations"]} if "localizations" in manifest else {})}


def records(manifest):
    return ([(role, manifest[role]) for role in ROLES] +
            [("caption:" + item["language"], item["file"]) for item in manifest["captions"]])


def fixture_projection(root, request):
    value = dict(request)
    for role in (name for name in ROLES if name != "youtube_payload"):
        descriptor = request[role]
        relative = descriptor if isinstance(descriptor, str) else descriptor["path"]
        value[role] = file_info(root, relative)
    value["captions"] = []
    for track in request["captions"]:
        path = track["file"] if isinstance(track["file"], str) else track["file"]["path"]
        value["captions"].append({**track, "file": file_info(root, path),
                                  "aligned_video_sha256": value["delivery_video"]["sha256"]})
    payload = canonical(wire_payload(value))
    value["youtube_payload"] = {"path": PAYLOAD, "bytes": len(payload), "sha256": digest(payload)}
    return value, payload


def assemble(root, request, profile):
    demand(request.get("channel_profile") == profile, 13, "profile_mismatch")
    demand(not (root / SEAL).exists(), 2, "sealed_revision_exists")
    value, payload = fixture_projection(root, request)
    diagnostics = schema_diagnostics(value)
    if diagnostics:
        raise diagnostics[0]
    atomic_write(root / PAYLOAD, payload, exclusive=True)
    try:
        atomic_write(root / MANIFEST, canonical(value), exclusive=True)
    except BaseException:
        # Only roll back the payload just created by this invocation.
        (root / PAYLOAD).unlink()
        sync_directory(root)
        raise
    return {"manifest_sha256": digest(canonical(value)), "payload_sha256": digest(payload)}


def schema_diagnostics(value):
    schema = load_json(REFERENCES / "video-package.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    diagnostics = []
    for exc in validator.iter_errors(value):
        nodes = list(exc.absolute_path)
        first = nodes[0] if nodes else None
        if exc.validator == "required" and isinstance(exc.instance, dict):
            missing = set(exc.validator_value) - set(exc.instance)
            if first is None and missing.intersection({"status", "paidProductPlacementDetails", "notifySubscribers"}):
                first = "status"
        mapping = {"snippet":5, "status":7, "paidProductPlacementDetails":7, "notifySubscribers":7,
                   "localizations":8, "chapters":6, "chapter_exemption":6, "captions":10}
        gate = mapping.get(first, 1)
        if exc.validator == "pattern" and "path" in nodes:
            gate = 1
        diagnostics.append(Invalid(gate, f"schema_{exc.validator}", "/" + "/".join(map(str, nodes))))
    return diagnostics


def sequence_identity(files):
    return digest(canonical([[name, sha_file(path)] for name, path in
                            sorted(files, key=lambda x: x[0].encode("utf-8"))]))


def runtime_inputs(directory, prefix):
    items = []
    for path in directory.rglob("*"):
        if "__pycache__" in path.parts or path.name.endswith(".pyc"):
            continue
        demand(not path.is_symlink(), 2, "runtime_link")
        if path.is_file():
            items.append((prefix + "/" + path.relative_to(directory).as_posix(), path))
        else:
            demand(path.is_dir(), 2, "unsafe_runtime_entry")
    return items


def executable(name):
    value = shutil.which(name)
    demand(value is not None, 3, "required_media_tool_unavailable")
    return Path(value).resolve(strict=True)


def bundle_files():
    files = runtime_inputs(ROOT / "scripts", "contract/scripts")
    files += runtime_inputs(REFERENCES, "contract/references")
    files += [("contract/uv.lock", ROOT / "uv.lock"), ("runtime/python", Path(sys.executable).resolve()),
              ("runtime/ffmpeg", executable("ffmpeg")), ("runtime/ffprobe", executable("ffprobe"))]
    return files


def bundle_hash():
    from dependencies import locked_manifest

    values = [[name, sha_file(path)] for name, path in bundle_files()]
    dependencies = locked_manifest(ROOT / "uv.lock", "video-release-contract")
    values.append(["runtime/contract-deps.lock", digest(canonical(dependencies))])
    return digest(canonical(sorted(values, key=lambda x: x[0].encode("utf-8"))))


def json_run(argv, *, timeout=120, fd=None):
    result = subprocess.run(argv, capture_output=True, timeout=timeout,
                            pass_fds=() if fd is None else (fd,))
    if result.returncode:
        raise ValueError("media tool rejected input")
    return json_data(result.stdout)


def probe_media(path):
    return json_run([str(executable("ffprobe")), "-v", "error", "-show_streams", "-show_format",
                     "-of", "json", str(path)])


def video_qc(path, spec, probe):
    video = [x for x in probe["streams"] if x.get("codec_type") == "video" and not x.get("disposition", {}).get("attached_pic")]
    demand(len(video) == 1, 3, "video_stream_count")
    stream = video[0]
    flags = probe["format"]
    container = flags.get("format_name", "").split(",")
    demand("mp4" in container and path.suffix.lower() in (".mp4", ".mov") and
           stream.get("codec_name") in {"h264", "hevc", "av1"}, 3, "video_container_or_codec")
    w, h = stream["width"], stream["height"]
    rotation = next((int(t["rotation"]) for t in stream.get("side_data_list", []) if "rotation" in t), 0)
    demand(rotation % 90 == 0 and stream.get("sample_aspect_ratio", "1:1") in ("1:1", "N/A"),
           3, "invalid_display_geometry")
    if rotation % 180:
        w, h = h, w
    matching = (w >= 1920 and h >= 1080 and w*9 == h*16) if spec == "landscape" else (
        w >= 1080 and h >= 1920 and w*16 == h*9)
    demand(matching, 3, "video_resolution_or_aspect")
    frame_rate = Fraction(stream["avg_frame_rate"])
    demand(frame_rate in {24, 25, 30, 50, 60} and frame_rate == Fraction(stream["r_frame_rate"]) and
           stream.get("field_order") == "progressive", 3, "video_scan_or_rate")
    seconds = float(stream.get("duration", flags["duration"]))
    demand(math.isfinite(seconds) and seconds > 0, 3, "invalid_video_duration")
    # Decode every frame under -xerror rather than trusting header metadata alone.
    result = subprocess.run([str(executable("ffmpeg")), "-nostdin", "-v", "error", "-xerror",
                             "-i", str(path), "-map", "0:v:0", "-an", "-f", "null", "-"],
                            capture_output=True, timeout=max(120, min(3600, seconds * 4)))
    demand(result.returncode == 0, 3, "video_decode_failure")
    return {"width": w, "height": h, "seconds": seconds, "fps": int(frame_rate),
            "codec": stream["codec_name"], "rotation": rotation}


def audio_qc(path, profile, probe):
    streams = [x for x in probe["streams"] if x.get("codec_type") == "audio"]
    demand(len(streams) == 1 and streams[0].get("channels") == 2 and
           streams[0].get("sample_rate") == "48000", 4, "audio_rate_or_channels")
    audio = streams[0]
    result = subprocess.run([str(executable("ffmpeg")), "-nostdin", "-hide_banner", "-v", "info",
                             "-xerror", "-i", str(path), "-map", "0:a:0", "-vn", "-af",
                             "ebur128=peak=true", "-f", "null", "-"], capture_output=True, timeout=3600)
    summary = result.stderr.decode("utf-8", errors="replace").rsplit("Summary:", 1)[-1]
    loud = re.search(r"\bI:\s*(-?[\d.]+)\s*LUFS", summary)
    peak = re.search(r"\bPeak:\s*(-?[\d.]+)\s*dBFS", summary)
    demand(result.returncode == 0 and loud and peak, 4, "audio_measurement_failed")
    value, tp = float(loud[1]), float(peak[1])
    target = -16 if profile == "asf-channel" else -14
    demand(abs(value-target) <= 1 and tp <= -1, 4, "loudness_or_true_peak")
    return {"integrated_lufs": value, "true_peak_dbtp": tp, "target_lufs": target,
            "stream": audio["index"]}


def title_description(title, description, gate):
    demand(bool(title.strip()) and 1 <= len(title) <= 100 and clean_identifier(title) and
           not any(x in title for x in "<>") and bool(description.strip()) and
           len(description.encode()) <= 5000 and not any(x in description for x in "<>\0"),
           gate, "metadata_text_budget_or_characters")


def language(code, gate):
    demand(clean_identifier(code) and langcodes.tag_is_valid(code), gate, "invalid_language")
    return langcodes.standardize_tag(code)


def snippet_check(snippet, region, policy):
    title_description(snippet["title"], snippet["description"], 5)
    tags = snippet["tags"]
    demand(all(t.strip() and not any(c in t for c in "<>\r\n\0") for t in tags) and
           sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags)-1) <= 500, 5, "tag_budget")
    demand(snippet["categoryId"] in policy["category_assignable"].get(region, []), 5, "category_not_assignable_in_snapshot")
    for field in ("defaultLanguage", "defaultAudioLanguage"):
        language(snippet[field], 5)


def parse_chapters(text):
    result = []
    for line in text.splitlines():
        m = STAMP.fullmatch(line.strip())
        if not m:
            continue
        parts = [int(x) for x in m["time"].split(":")]
        demand(parts[-1] < 60 and (len(parts) != 3 or parts[-2] < 60), 6, "invalid_chapter_time")
        seconds = sum(part * 60 ** i for i, part in enumerate(reversed(parts)))
        result.append({"start_seconds": seconds, "title": m["title"]})
    return result


def chapter_check(manifest, duration):
    chapters = manifest["chapters"]
    demand(parse_chapters(manifest["snippet"]["description"]) == chapters, 6, "chapter_description_drift")
    if not chapters:
        demand(duration < 120 or bool((manifest["chapter_exemption"] or "").strip()),
               6, "chapters_required")
        return
    times = [c["start_seconds"] for c in chapters]
    demand(len(times) >= 3 and times[0] == 0 and
           all(b-a >= 10 for a,b in zip(times, [*times[1:], duration])),
           6, "chapter_order_or_minimum_duration")


def status_check(manifest, now):
    status = manifest["status"]
    if "publishAt" in status:
        value = status["publishAt"]
        demand(clean_identifier(value) and status["privacyStatus"] == "private" and
               datetime.fromisoformat(value[:-1] + "+00:00") > now, 7, "publish_at_not_future_private")
    if manifest["channel_profile"] == "smoke-test":
        demand(status["privacyStatus"] == "private" and "publishAt" not in status and
               manifest["notifySubscribers"] is False, 7, "smoke_policy")


def localization_check(manifest):
    tags = set()
    for locale, value in manifest.get("localizations", {}).items():
        normalized = language(locale, 8).casefold()
        demand(normalized not in tags, 8, "duplicate_normalized_locale")
        tags.add(normalized)
        title_description(value["title"], value["description"], 8)


def thumbnail_check(path, size):
    demand(0 < size <= 50_000_000, 9, "thumbnail_size")
    try:
        with Image.open(path) as image:
            demand(image.format in {"PNG", "JPEG"}, 9, "thumbnail_format")
            demand(path.suffix.lower() in ((".jpg", ".jpeg") if image.format == "JPEG" else (".png",)) and
                   image.mode == "RGB" and getattr(image, "n_frames", 1) == 1, 9, "thumbnail_format_or_mode")
            w,h = image.size
            demand(w >= 1280 and h >= 720 and abs((w/h)/(16/9)-1) <= .01, 9, "thumbnail_resolution_or_aspect")
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise Invalid(9, "thumbnail_decode") from exc
    return {"width":w,"height":h,"bytes":size}, (["thumbnail_over_2_mib"] if size > 2**21 else [])


def milliseconds(value):
    parts = value.replace(",", ".").split(":")
    sec, ms = parts[-1].split(".")
    if int(sec) >= 60 or len(parts) == 3 and int(parts[-2]) >= 60:
        raise ValueError("timestamp parts")
    return 1000*(int(sec)+60*int(parts[-2])+3600*(int(parts[0]) if len(parts)==3 else 0))+int(ms)


def cues(data, extension):
    text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n[ \t]*\n", text)
    if extension == ".vtt":
        demand(blocks and re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0]), 10, "caption_vtt_header")
        blocks = blocks[1:]
    else:
        demand(extension == ".srt", 10, "caption_format")
    out = []
    for i, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        if extension == ".srt":
            demand(lines and lines[0] == str(i), 10, "caption_srt_index")
            lines = lines[1:]
        elif lines and "-->" not in lines[0]:
            lines = lines[1:]
        match = TIMING.fullmatch(lines[0]) if lines else None
        demand(len(lines) == 2 and match and lines[1].strip() and not re.search(r"[<>\0]", lines[1]),
               10, "caption_cue_not_single_line_plain_text")
        start, end = milliseconds(match[1]), milliseconds(match[2])
        demand(0 <= start < end and (not out or out[-1][1] <= start), 10, "caption_timeline")
        out.append((start, end, lines[1]))
    demand(out, 10, "caption_empty")
    return out


def subtitles_check(root, manifest, duration, policy):
    warnings, languages = set(), set()
    for track in manifest["captions"]:
        lang = language(track["language"], 10)
        demand(lang.casefold() not in languages and clean_identifier(track["name"]), 10, "caption_identity")
        languages.add(lang.casefold())
        path = track["file"]["path"]
        for start, stop, text in cues(local_bytes(root,path), Path(path).suffix.lower()):
            demand(stop <= duration*1000 and not any(x in text for x in policy["filler_terms"]) and
                   not any(re.search(rf"\b{re.escape(x)}\b",text) for x in policy["term_replacements"]),
                   10, "caption_out_of_bounds_or_unclean")
            if lang.split("-")[0] == "zh":
                count = len(regex.findall(r"\X", text.strip()))
                demand(count <= 18, 10, "caption_chinese_line_too_long")
                if count > 16:
                    warnings.add("caption_chinese_line_target")
            if not 1500 <= stop-start <= 3500:
                warnings.add("cue_duration_target")
    reading = local_bytes(root, manifest["reading_transcript"]["path"]).decode("utf-8")
    demand(Path(manifest["reading_transcript"]["path"]).suffix == ".md" and
           any(p.strip() and re.search(r"[。！？.!?][”'\"）)]?\s*$", p) for p in re.split(r"\n\s*\n", reading)),
           10, "reading_track_not_punctuated")
    return sorted(warnings)


def enrichment_check(root, m):
    value = local_bytes(root, m["enrichment_pack"]["path"]).decode("utf-8")
    pieces = re.split(r"(?m)^##\s+([^\n]+)\s*\n", value)
    sections = {k.strip():v.strip() for k,v in zip(pieces[1::2], pieces[2::2])}
    demand({"标题候选", "Chapters", "Show Notes", "推广文案"} <= sections.keys(),
           11, "enrichment_sections_missing")
    candidates = {re.sub(r"^(?:[-*]|\d+\.)\s+", "", x.strip()) for x in sections["标题候选"].splitlines() if x.strip()}
    demand(len(candidates) >= 2 and sections["Show Notes"] and sections["推广文案"] and
           sections["Chapters"] and parse_chapters(sections["Chapters"]) == m["chapters"],
           11, "enrichment_content_or_chapters")


def rights_check(root, m, policy):
    data = local_bytes(root, m["credits"]["path"]).decode("utf-8")
    demand(bool(data.strip()) and clean_identifier(m["rights"]["declaration_ref"]),
           12, "rights_declaration_or_credits")
    if m["rights"]["third_party"]:
        lines = [line for line in data.splitlines() if line.strip()]
        demand(all(len(line.split("|")) >= 5 and all(s.strip() for s in line.split("|")) for line in lines),
               12, "third_party_credit_fields")
    texts = [canonical(m).decode()]
    for name in ("reading_transcript", "enrichment_pack", "credits"):
        texts.append(local_bytes(root, m[name]["path"]).decode("utf-8"))
    for track in m["captions"]:
        texts.append(local_bytes(root, track["file"]["path"]).decode("utf-8"))
    demand(not any(PROTECTED.search(text) for text in texts), 1, "credential_like_content")
    demand(not any(term.casefold() in text.casefold()
                   for term in policy["blocked_terms"] for text in texts), 12, "blocked_rights_or_identity_term")


def close_artifacts(root, manifest, raw):
    roles = records(manifest)
    seen = set()
    names = {MANIFEST}
    index = []
    for role, item in roles:
        name = item["path"]
        demand(name not in (MANIFEST, SEAL) and name.casefold() not in seen, 1, "artifact_alias")
        seen.add(name.casefold())
        names.add(name)
        try:
            actual = file_info(root, name)
        except Invalid as exc:
            # A missing required credit file has a dedicated policy gate.
            if role == "credits" and not (root / name).exists() and not (root / name).is_symlink():
                raise Invalid(12, "credits_missing", role) from exc
            raise
        demand(actual == item, 2, "artifact_bytes_or_hash_changed", role)
        index.append([role, name, item["bytes"], item["sha256"]])
    present = set()
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        demand(not path.is_symlink(), 1, "package_symlink")
        if path.is_file():
            present.add(name)
        else:
            demand(path.is_dir(),1,"package_special_file")
    demand(present - {SEAL} == names and manifest["youtube_payload"]["path"] == PAYLOAD,
           2, "unexpected_package_artifacts")
    demand(all(track["aligned_video_sha256"] == manifest["delivery_video"]["sha256"]
               for track in manifest["captions"]), 2, "caption_video_alignment_hash")
    payload = local_bytes(root, PAYLOAD)
    demand(payload == canonical(wire_payload(manifest)), 2, "payload_byte_projection_mismatch")
    return {"contract_version":"1.0","episode_key":manifest["episode_key"],
            "package_revision":manifest["package_revision"],"manifest_sha256":digest(raw),
            "payload_sha256":digest(payload),
            "artifact_index_sha256":digest(canonical(sorted(index,key=lambda x:x[1].encode()))),
            "contract_bundle_sha256":bundle_hash()}


def check(root, profile, *, config=None, require_seal=False, now=None):
    gate_status = ["blocked"]*13 + ["pending"]
    details, warnings, failures = {}, {}, []
    result = {"schema_version":"1", "contract_passed":False,"human_preview_ready":False,
              "growth_ready":False,"publish_authorized":False, "details":details}
    now = now or datetime.now(timezone.utc)
    result["checked_at"] = now.isoformat()
    manifest, expected_seal = None, None
    try:
        raw = local_bytes(root, MANIFEST)
        manifest = json_data(raw)
        diagnostics = schema_diagnostics(manifest)
        if diagnostics:
            for item in diagnostics:
                failures.append(item)
        else:
            gate_status[0] = "pass"
    except (Invalid, ValueError, OSError) as exc:
        failures.append(exc if isinstance(exc, Invalid) else Invalid(1,"manifest_invalid"))

    def gate(num, callback):
        try:
            info = callback()
            if info is not None:
                details[f"G{num:02}"] = info
            gate_status[num-1] = "warn" if warnings.get(num) else "pass"
            return info
        except (Invalid, ValueError, OSError, subprocess.SubprocessError, KeyError, ZeroDivisionError) as exc:
            failures.append(exc if isinstance(exc, Invalid) else Invalid(num,"validation_input_or_tool_error"))
            return None

    if gate_status[0] == "pass":
        policy = load_json(REFERENCES / "policy.json")
        expected_seal = gate(2, lambda: close_artifacts(root, manifest, raw))
        if expected_seal is not None:
            def seal_check():
                if require_seal:
                    demand(expected_seal == json_data(local_bytes(root,SEAL)), 2, "seal_missing_or_changed")
                return expected_seal
            # Missing or unsafe seal is closure failure, not a missing manifest.
            if require_seal and not (root / SEAL).is_file():
                failures.append(Invalid(2,"seal_missing"))
            else:
                gate(2, seal_check)
            video_path = root / manifest["delivery_video"]["path"]
            probe = gate(3, lambda: probe_media(video_path))
            if probe is not None:
                video = gate(3, lambda: video_qc(video_path, manifest["format"], probe))
                gate(4, lambda: audio_qc(video_path, profile, probe))
            else:
                video = None
            gate(5, lambda: snippet_check(manifest["snippet"],manifest["region_code"],policy))
            if video:
                gate(6, lambda: chapter_check(manifest, video["seconds"]))
            gate(7, lambda: status_check(manifest, now))
            gate(8, lambda: localization_check(manifest))
            def thumbnail():
                info, warns = thumbnail_check(root / manifest["thumbnail"]["path"], manifest["thumbnail"]["bytes"])
                warnings[9] = warns
                return info
            gate(9, thumbnail)
            if video:
                def subtitle():
                    warnings[10] = subtitles_check(root,manifest,video["seconds"],policy)
                gate(10, subtitle)
            gate(11, lambda: enrichment_check(root,manifest))
            gate(12, lambda: rights_check(root,manifest,policy))
        def profile_check():
            demand(profile == manifest["channel_profile"] and
                   profile_channel(profile,config) == manifest["target_channel_id"], 13, "profile_mismatch")
        gate(13, profile_check)
    for exc in failures:
        gate_status[exc.gate-1] = "fail"
    result["gates"] = [
        {"id":f"G{i:02}_{name}","status":gate_status[i-1],
         "errors":[{"code":x.reason,"location":x.location} for x in failures if x.gate==i],
         "warnings":warnings.get(i,[])} for i,name in enumerate(GATES,1)]
    result["contract_passed"] = all(x in ("pass","warn") for x in gate_status[:13])
    result["growth_ready"] = bool(result["contract_passed"] and manifest["chapters"] and manifest["playlist_ids"])
    if expected_seal:
        result["binding"] = expected_seal
    return result, manifest


def create_seal(root, profile, *, config=None):
    result, _ = check(root,profile,config=config)
    if not result["contract_passed"]:
        return result
    value = canonical(result["binding"])
    if (root / SEAL).exists():
        demand(local_bytes(root, SEAL) == value, 2, "seal_collision")
    else:
        atomic_write(root / SEAL,value,exclusive=True)
    result["seal_sha256"] = digest(value)
    return result


def preview_html(root, output, report, m):
    seal_sha = digest(local_bytes(root,SEAL))
    describe=m["snippet"]["description"]
    def elt(value):
        return html.escape(str(value), quote=True)
    def src(role):
        return quote(os.path.relpath(root / m[role]["path"], output.parent), safe="/")
    gates = "".join(f"<li>{elt(x['id'])} · {elt('pass' if x['id'].startswith('G14') else x['status'])}</li>"
                    for x in report["gates"])
    tracks = "".join("<li>"+elt(t["language"])+" · "+elt(t["name"])+"<pre>"+elt(
        local_bytes(root,t["file"]["path"]).decode("utf-8")[:800])+"</pre></li>" for t in m["captions"])
    chapters = "".join(f"<li>{c['start_seconds']}s · {elt(c['title'])}</li>" for c in m["chapters"])
    reading = local_bytes(root,m["reading_transcript"]["path"]).decode()[:3000]
    credits = local_bytes(root,m["credits"]["path"]).decode()[:3000]
    rows = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        f"<meta http-equiv=\"Content-Security-Policy\" content=\"{elt(CSP)}\">",
        f"<meta name=\"seal-sha256\" content=\"{seal_sha}\"><title>{elt(m['snippet']['title'])}</title></head><body>",
        f"<h1>{elt(m['snippet']['title'])}</h1><p>{elt(m['channel_profile'])} · {elt(m['target_channel_id'])}</p>",
        f"<video controls preload=\"metadata\" width=\"640\" src=\"{src('delivery_video')}\"></video>",
        f"<h2>Thumbnail</h2><img width=\"480\" alt=\"Release thumbnail\" src=\"{src('thumbnail')}\">",
        f"<pre>{elt(canonical(m['thumbnail']).decode())}</pre>",
        f"<h2>Description</h2><p>{elt(describe[:180])}</p><details><summary>Full description</summary><pre>{elt(describe)}</pre></details>",
        f"<h2>Chapters</h2><ol>{chapters}</ol><h2>Caption tracks</h2><ul>{tracks}</ul>",
        f"<h2>Reading transcript</h2><pre>{elt(reading)}</pre><h2>Credits</h2><pre>{elt(credits)}</pre>",
        f"<h2>Visibility and disclosures</h2><pre>{elt(canonical(m['status']).decode())}</pre>",
        f"<p>Notify subscribers: {elt(m['notifySubscribers'])} · Paid placement: {elt(m['paidProductPlacementDetails']['hasPaidProductPlacement'])}</p>",
        f"<h2>Quality checks</h2><pre>{elt(canonical(report['details']).decode())}</pre><ul>{gates}</ul>",
        f"<p>contract_passed=true · human_preview_ready=true · growth_ready={'true' if report['growth_ready'] else 'false'} · publish_authorized=false</p>",
        "</body></html>",
    ]
    value = "\n".join(rows).encode("utf-8")
    demand(not PROTECTED.search(value.decode()),14,"preview_contains_credential_like_content")
    demand(output.parent.resolve() != root.resolve() and output.name.endswith(".html"),
           14,"invalid_preview_output")
    return value


def render(root, profile, output, *, config=None, write=True):
    result, manifest = check(root,profile,config=config,require_seal=True)
    if not result["contract_passed"]:
        return result
    try:
        data = preview_html(root, output, result, manifest)
        if write:
            atomic_write(output, data)
        demand(output.read_bytes() == data,14,"preview_bytes_or_seal_mismatch")
    except (Invalid, OSError, ValueError) as exc:
        result["gates"][-1].update(status="fail",errors=[{"code":exc.reason if isinstance(exc, Invalid) else "preview_io"}])
        return result
    result["gates"][-1]["status"]="pass"
    result["human_preview_ready"]=True
    result["preview_sha256"]=digest(data)
    return result


def command(argv=None):
    outer = argparse.ArgumentParser()
    inner = outer.add_subparsers(dest="action",required=True)
    for action in ("assemble","validate","seal","render_preview"):
        arguments = inner.add_parser(action)
        arguments.add_argument("--package",type=Path,required=True)
        arguments.add_argument("--profile",required=True)
        arguments.add_argument("--config",type=Path)
        arguments.add_argument("--report",type=Path)
        if action == "assemble":
            arguments.add_argument("--input",type=Path,required=True)
        if action == "validate":
            arguments.add_argument("--require-seal",action="store_true")
        if action == "render_preview":
            arguments.add_argument("--output",type=Path,required=True)
    args = outer.parse_args(argv)
    root = args.package.absolute()
    try:
        if args.action=="assemble":
            report = {"assembled":True, **assemble(root,load_json(args.input),args.profile)}
            healthy = True
        elif args.action=="validate":
            report,_ = check(root,args.profile,config=args.config,require_seal=args.require_seal)
            healthy = report["contract_passed"]
        elif args.action=="seal":
            report = create_seal(root,args.profile,config=args.config)
            healthy = report["contract_passed"]
        else:
            report=render(root,args.profile,args.output.absolute(),config=args.config)
            healthy = report["human_preview_ready"]
        if args.report:
            demand(not args.report.absolute().is_relative_to(root),1,"report_inside_seal")
            atomic_write(args.report,canonical(report)+b"\n")
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        report = {"contract_passed":False,"publish_authorized":False,"error_code":
                  exc.reason if isinstance(exc,Invalid) else "invalid_input","gate":
                  f"G{exc.gate:02}" if isinstance(exc,Invalid) else "G01"}
        healthy = False
    print(canonical(report).decode())
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(command())
