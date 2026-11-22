"""A persistent process double for the production release and recovery flows."""

import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
args = sys.argv[2:]
file = root / "state.json"
state = json.loads(file.read_text())
videos = state["videos"]
profile = state["profile"]
channel = state["channel"]
playlist_id = "PLfixture123456"


def arg(flag):
    return args[args.index(flag) + 1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(flag, checksum_flag):
    with os.fdopen(os.dup(int(arg(flag))), "rb") as stream:
        stream.seek(0)
        data = stream.read()
    assert sha(data) == arg(checksum_flag)
    return data


def save():
    staged = file.with_suffix(".new")
    staged.write_text(json.dumps(state))
    staged.replace(file)


def log(mode, command, **details):
    with (root / "requests.jsonl").open("a") as out:
        out.write(json.dumps({"mode": mode, "command": command, **details}) + "\n")


def reply(**data):
    print(json.dumps({"schema_version": "1", "profile": profile, "data": data}))
    raise SystemExit(0)


def fail(code, reason, effect="none", **ids):
    print(json.dumps({"error_code": reason, "safe_ids": ids, "effect": effect,
                      "reconciliation_required": effect != "none"}), file=sys.stderr)
    raise SystemExit(code)


command = "/".join(args[:2]) if args[0] != "doctor" else "doctor"
if command == "playlists/items":
    command += "/" + args[2]
methods = {"videos/upload": "POST", "videos/update": "PUT", "thumbnails/set": "POST", "captions/upload": "POST",
           "captions/update": "PUT", "captions/delete": "DELETE", "playlists/items/add": "POST"}
if command in methods:
    dry = "--dry-run" in args
    yes = "--yes" in args
    media = pinned("--media-fd", "--media-sha256") if "--media-fd" in args else None
    body = {}
    query = {}
    if command in {"videos/upload", "videos/update"}:
        raw = pinned("--metadata-fd", "--metadata-file-sha256")
        body = json.loads(raw)
    if command == "videos/upload":
        assert args.count("--notify-subscribers") + args.count("--no-notify-subscribers") == 1
        query["notifySubscribers"] = "--notify-subscribers" in args
    elif command == "thumbnails/set":
        query["videoId"] = args[2]
    elif command == "captions/upload":
        body = {"snippet": {"videoId": args[2], "language": arg("--language"),
                            "name": arg("--name"), "isDraft": False}}
    elif command == "captions/update":
        body = {"id": args[2]}
    elif command == "captions/delete":
        query["id"] = args[2]
    elif command == "playlists/items/add":
        body = {"snippet": {"playlistId": args[3], "resourceId": {"videoId": arg("--video-id")}}}
    log("plan" if dry else "write", command, yes=yes, query=query, body=body)
    if dry:
        assert not yes
        reply(dry_run=True, method=methods[command], identity_verified=False, complete=True, query=query,
              metadata=body, metadata_sha256=arg("--metadata-file-sha256") if "--metadata-file-sha256" in args else None,
              media={"sha256": sha(media)} if media is not None else None)
    if command == "videos/upload":
        assert yes == (body["status"]["privacyStatus"] != "private" or "publishAt" in body["status"] or
                       query["notifySubscribers"])
        serial = state.get("uploads", 0) + 1
        state["uploads"] = serial
        vid = f"V{serial:010d}"
        videos[vid] = {"metadata": body, "tracks": {}, "playlists": []}
        save()
        reply(video_id=vid, notify_subscribers=query["notifySubscribers"])
    if command == "videos/update":
        assert yes and "--notify-subscribers" not in args and "--no-notify-subscribers" not in args
        vid = args[2]
        assert body.pop("id") == vid
        metadata = videos[vid]["metadata"]
        metadata.update(body)
        save()
        reply(video_id=vid)
    if command == "thumbnails/set":
        if state.get("failure") == "thumbnail_rejected":
            fail(4, "provider_rejected")
        (root / f"{args[2]}-thumb").write_bytes(media)
        reply(video_id=args[2])
    if command == "captions/upload":
        vid = args[2]
        serial = state.get("captions", 0) + 1
        state["captions"] = serial
        cid = f"caption-{serial}"
        videos[vid]["tracks"][cid] = {"id": cid, "snippet": {**body["snippet"], "trackKind": "standard",
                                                             "status": "serving"}}
        (root / cid).write_bytes(media)
        save()
        reply(caption_id=cid)
    if command in {"captions/update", "captions/delete"}:
        cid = args[2]
        assert yes
        if state.get("failure") == "caption_interrupted":
            fail(10, "transport_failure", "unknown")
        video = next(row for row in videos.values() if cid in row["tracks"])
        if command == "captions/delete":
            video["tracks"].pop(cid)
            save()
        else:
            (root / cid).write_bytes(media)
            state["caption_updated"] = cid
            save()
        reply(caption_id=cid, deleted=command == "captions/delete")
    if command == "playlists/items/add":
        vid = arg("--video-id")
        videos[vid]["playlists"].append(args[3])
        save()
        reply(item_id=f"membership-{vid}")

log("read", command)
if command == "doctor":
    reply(channel_id=channel, oauth_binding_sha256="1" * 64, identity_verified=True,
          effective_smoke=state.get("protected", False))
if command == "videos/list":
    reply(complete=True, items=[{"id": f"upload-{vid}", "snippet": {
        "title": video["metadata"]["snippet"]["title"], "resourceId": {"videoId": vid}},
        "contentDetails": {"videoId": vid}} for vid, video in videos.items()])
if command == "videos/get":
    vid = args[2]
    if vid not in videos:
        reply(items=[])
    body = videos[vid]["metadata"]
    if body["status"].get("containsSyntheticMedia") is False:
        body["status"].pop("containsSyntheticMedia")
    reply(items=[{**body, "id": vid, "snippet": {**body["snippet"], "channelId": channel},
                  "contentDetails": {"duration": "PT15S", "hasCustomThumbnail": (root / f"{vid}-thumb").exists()},
                  "processingDetails": {"processingStatus": "succeeded"}}])
if command == "thumbnails/fetch":
    data = (root / f"{args[2]}-thumb").read_bytes()
    Path(arg("--destination")).write_bytes(data)
    reply(video_id=args[2], sha256=sha(data))
if command == "captions/list":
    reply(complete=True, items=list(videos[args[2]]["tracks"].values()))
if command == "captions/download":
    if state.get("failure") == "caption_readback_unavailable" and state.get("caption_updated") == args[2]:
        fail(4, "caption_readback_unavailable")
    data = (root / args[2]).read_bytes()
    Path(arg("--destination")).write_bytes(data)
    reply(caption_id=args[2], sha256=sha(data))
if command == "playlists/list":
    reply(complete=True, items=[{"id": playlist_id, "snippet": {"channelId": channel},
                                 "status": {"privacyStatus": state.get("playlist_privacy", "unlisted")}}])
if command == "playlists/items/list":
    vid, pid = arg("--video-id"), args[3]
    reply(complete=True, items=[{"id": f"membership-{vid}", "snippet": {
        "playlistId": pid, "resourceId": {"videoId": vid}}}] if pid in videos[vid]["playlists"] else [])
fail(2, "unexpected_fake_command")
