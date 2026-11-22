"""Offline process double. Its complete network surface is a private local fixture directory."""

import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
argv = sys.argv[2:]
state_file = root / "provider.json"
state = json.loads(state_file.read_text())
channel = "UC" + "A" * 22
video_id = "aBCde123456"
playlist_id = "PLfixture123456"
failure = state.get("failure", "")


def arg(name):
    return argv[argv.index(name) + 1]


def file_arg(name):
    with os.fdopen(os.dup(int(arg(name))), "rb") as stream:
        stream.seek(0)
        return stream.read()


def checksum(raw):
    return hashlib.sha256(raw).hexdigest()


def respond(data):
    print(json.dumps({"schema_version": "1", "profile": "smoke-test", "data": data}))


def fail(code, reason, **ids):
    print(json.dumps({"error_code": reason, "safe_ids": ids}), file=sys.stderr)
    raise SystemExit(code)


def update():
    target = state_file.with_suffix(".new")
    target.write_text(json.dumps(state))
    target.replace(state_file)


def event(mode, operation, **evidence):
    with (root / "requests.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"mode": mode, "operation": operation, **evidence}) + "\n")


cmd = "/".join(argv[:2]) if argv[0] != "doctor" else "doctor"
if argv[:2] == ["playlists", "items"]:
    cmd += "/" + argv[2]
mutations = {"videos/upload", "thumbnails/set", "captions/upload", "playlists/items/add"}
if cmd in mutations:
    media = file_arg("--media-fd") if "--media-fd" in argv else None
    digest = checksum(media) if media is not None else None
    if media is not None:
        assert digest == arg("--media-sha256")
    metadata = {}
    if cmd == "videos/upload":
        raw = file_arg("--metadata-fd")
        assert checksum(raw) == arg("--metadata-file-sha256")
        assert argv.count("--no-notify-subscribers") == 1
        metadata = json.loads(raw)
        assert metadata["status"]["privacyStatus"] == "private" and "publishAt" not in metadata["status"]
    dry = "--dry-run" in argv
    event("plan" if dry else "write", cmd, media_sha256=digest)
    if dry:
        respond({"dry_run": True, "metadata": metadata})
        raise SystemExit(0)
    if cmd == "videos/upload":
        if failure == "lost_init":
            fail(10, "transport_failure")
        if failure == "no_effect":
            fail(4, "provider_rejected")
        state["video"] = metadata
        update()
        if failure.startswith("lost_final"):
            fail(11, "mutation_response_unknown", session_handle="a" * 32)
        if failure == "known_partial":
            fail(7, "upload_readback_incomplete", video_id=video_id)
        respond({"video_id": video_id})
    elif cmd == "thumbnails/set":
        (root / "thumbnail.png").write_bytes(media)
        if failure == "lost_thumbnail":
            fail(10, "transport_failure")
        respond({"video_id": video_id})
    elif cmd == "captions/upload":
        tracks = state.setdefault("tracks", {})
        if failure == "second_rejected" and tracks:
            fail(4, "provider_rejected")
        cid = f"caption-{len(tracks)+1}"
        tracks[cid] = {"id": cid, "snippet": {"videoId": video_id, "language": arg("--language"),
                        "name": arg("--name"), "trackKind": "standard", "isDraft": False, "status": "serving"}}
        (root / (cid + ".srt")).write_bytes(media)
        update()
        respond({"caption_id": cid})
    else:
        state["member"] = True
        update()
        if failure == "lost_playlist":
            fail(10, "transport_failure")
        respond({"item_id": "membership-1"})
    raise SystemExit(0)

event("read", cmd)
if cmd == "doctor":
    respond({"channel_id": "UC" + "B" * 22 if failure == "wrong_channel" else channel,
             "oauth_binding_sha256": "1" * 64, "identity_verified": True})
elif cmd == "videos/list":
    rows = [{"snippet": {"title": state["title"]}}] if failure == "collision" else []
    respond({"complete": True, "items": rows})
elif cmd == "videos/get":
    if "video" not in state or failure == "video_missing":
        respond({"items": []})
    elif failure == "readback_timeout":
        fail(10, "transport_failure")
    else:
        actual = state["video"]
        actual["snippet"]["channelId"] = channel
        if failure == "privacy_drift":
            actual["status"]["privacyStatus"] = "unlisted"
        if failure == "disclosure_missing":
            actual["status"].pop("containsSyntheticMedia")
        if failure == "audio_language":
            actual["snippet"]["defaultAudioLanguage"] = "en"
        actual["contentDetails"] = {"duration": "PT15S", "hasCustomThumbnail":
                                    (root / "thumbnail.png").exists() and failure != "default_thumbnail"}
        actual["processingDetails"] = {"processingStatus": "processing" if failure == "processing" else "succeeded"}
        respond({"items": [{"id": video_id, **actual}]})
elif cmd == "videos/wait-processing":
    respond({"processing_status": "processing" if failure == "processing" else "succeeded"})
elif cmd == "videos/upload-status":
    if failure == "lost_final_missing":
        respond({"state": "unknown"})
    elif failure == "lost_final_partial":
        respond({"state": "incomplete", "offset": 262144})
    else:
        respond({"state": "complete", "video_id": video_id})
elif cmd == "thumbnails/fetch":
    data = (root / "thumbnail.png").read_bytes()
    Path(arg("--destination")).write_bytes(data)
    respond({"sha256": checksum(data)})
elif cmd == "captions/list":
    tracks = list(state.get("tracks", {}).values())
    if failure == "duplicate_caption" and tracks:
        tracks.append({**tracks[0], "id": "duplicate"})
    if failure == "caption_draft" and tracks:
        tracks[0]["snippet"]["isDraft"] = True
    respond({"complete": True, "items": tracks})
elif cmd == "captions/download":
    data = (root / (argv[2] + ".srt")).read_bytes()
    Path(arg("--destination")).write_bytes(data)
    respond({"sha256": checksum(data)})
elif cmd == "playlists/list":
    respond({"complete": True, "items": [{"id": playlist_id, "snippet": {"channelId": channel},
                                          "status": {"privacyStatus": "private"}}]})
elif cmd == "playlists/items/list":
    entry = {"id": "membership-1", "snippet": {"playlistId": playlist_id, "resourceId": {"videoId": video_id}}}
    respond({"complete": failure != "truncated_playlist", "items": [entry] if state.get("member") else []})
else:
    fail(2, "unexpected_fake_command")
