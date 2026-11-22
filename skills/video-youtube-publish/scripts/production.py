"""Hash-bound production profile releases and in-place YouTube updates."""

import contextlib
import os
import tempfile
import uuid
from pathlib import Path

import cv2

from auth_store import Stop, require, safe_private, safe_read, timestamp, utc, validate_auth
from lineage import READBACK, RECEIPT, SHA, cleanup, current_header, episode_key, hashed, media_key
from package import (MANIFEST, PAYLOAD, SEAL, artifact_open, atomic_write, canonical, check, close_artifacts, config_profiles,
                     cues, digest, json_data, local_bytes, sha_file)
from publish import CAPTION_ID, SESSION_HANDLE, VIDEO_ID, Controller, freeze_package, local_authority_binding
from publish import matching_video, qr_evidence

UPLOAD = "upload_video"
UPDATE = "update_video"
THUMB = "set_thumbnail"
CAP_ADD = "upload_captions"
CAP_UPDATE = "update_captions"
CAP_DELETE = "delete_captions"
PLAYLIST = "add_playlist"
ORDER = {name: i for i, name in enumerate((UPLOAD, UPDATE, THUMB, CAP_ADD, CAP_UPDATE, CAP_DELETE, PLAYLIST))}
PLACEHOLDER = "$uploaded"
PUBLISH_MODES = {"initial_publish", "revision_republish"}
UNKNOWN_NOTIFY = {"value": "unknown", "source": "unobserved", "ref_sha256": None}
SNIPPET_FIELDS = {"title", "description", "categoryId", "defaultLanguage", "tags"}
STATUS_FIELDS = {"privacyStatus", "publishAt", "selfDeclaredMadeForKids", "containsSyntheticMedia"}
PRESERVED_STATUS = {"embeddable", "license", "publicStatsViewable"}
READ_ONLY_FIELDS = {
    "snippet": {"channelId", "channelTitle", "publishedAt", "thumbnails", "localized",
                "defaultAudioLanguage", "liveBroadcastContent"},
    "status": {"uploadStatus", "failureReason", "rejectionReason", "madeForKids"},
    "paidProductPlacementDetails": set(),
}


def target_key(track):
    return track["language"], track["name"]


def requires_yes(binding, operation):
    if binding["effective_smoke"]:
        return False
    return ((operation == UPLOAD and (binding["target_privacy_status"] != "private" or
            binding["publish_at"] is not None or binding["notify_subscribers"])) or
            operation in {UPDATE, CAP_UPDATE, CAP_DELETE} or
            operation == THUMB and binding["mode"] == "in_place_update")


def operation_row(binding, operation, target, before, inputs):
    return {"operation": operation, "target": target, "baseline_sha256": hashed(before),
            "input_sha256": hashed(inputs), "yes": requires_yes(binding, operation)}


def writable_projection(video, part):
    value = video.get(part, {})
    require(isinstance(value, dict), "invalid_baseline_part", code=4)
    if part == "localizations":
        return dict(value)
    supported = {"snippet": SNIPPET_FIELDS, "status": STATUS_FIELDS | PRESERVED_STATUS,
                 "paidProductPlacementDetails": {"hasPaidProductPlacement"}}[part]
    require(value.keys() <= supported | READ_ONLY_FIELDS[part], "unsafe_part_replacement", code=4)
    return {key: item for key, item in value.items() if key in supported}


class Production(Controller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.episode = None
        self.row = None
        self.parent_receipt = None
        self.parent_readback = None
        self.parent_payload = {}
        self.write_count = 0
        self.last_video = None
        self.notification = dict(UNKNOWN_NOTIFY)

    def owned(self, video_id):
        require(isinstance(video_id, str) and VIDEO_ID.fullmatch(video_id), "invalid_video_id")
        result = self.cli(["videos", "get", video_id])
        rows = result.get("items")
        require(isinstance(rows, list) and len(rows) == 1 and not result.get("nextPageToken") and
                rows[0].get("id") == video_id and rows[0].get("snippet", {}).get("channelId") ==
                self.binding["target_channel_id"], "video_owner_mismatch", code=4)
        return rows[0]

    def read_video(self, vid):
        return self.owned(vid)

    def local_candidate(self, *, identity=None):
        safe_private(self.root)
        require(self.preview.parent == self.root.parent and not self.preview.is_symlink(),
                "preview_must_be_local_sibling")
        report, manifest = self.local()
        require(self.hash_contract() == report["binding"]["contract_bundle_sha256"],
                "contract_runtime_identity_mismatch")
        identity = self.cli(["doctor"]) if identity is None else identity
        base = local_authority_binding(self.root, manifest, report, self.hash_cli(), identity, production=True)
        smoke = identity.get("effective_smoke")
        require(type(smoke) is bool, "smoke_policy_identity_unverified", code=3)
        registered = config_profiles(self.config)
        smoke_row = registered.get("smoke-test")
        channel = smoke_row.get("channel_id") if isinstance(smoke_row, dict) else smoke_row
        if "smoke-test" in registered:
            from package import CHANNEL
            require(isinstance(channel, str) and CHANNEL.fullmatch(channel), "invalid_smoke_profile_binding")
        smoke = smoke or channel == manifest["target_channel_id"]
        if smoke:
            require(base["target_privacy_status"] == "private" and base["publish_at"] is None and
                    base["notify_subscribers"] is False, "private_smoke_policy")
        self.manifest = manifest
        self.duration = report["details"]["G03"]["seconds"]
        self.key = episode_key(base)
        self.media_key = media_key(base)
        return {**base, "authorization_version": "3.0", "effective_smoke": smoke,
                "preview_sha256": sha_file(self.preview)}

    def validate_paths(self):
        known = [self.registry, self.state_root, self.store.root, self.root]
        require(all(not left.is_relative_to(right) and not right.is_relative_to(left)
                    for i, left in enumerate(known) for right in known[i + 1:]),
                "state_package_or_operator_path_overlap")

    def load_episode(self):
        book = self.lineage.read()
        self.episode = book.get("episodes", {}).get(self.key) if "registry_version" in book else None
        self.row = None
        if self.episode is None and "registry_version" not in book and self.key in book:
            raise Stop("legacy_inflight_drain_required", detail={"legacy_keys": [self.key], "mutations": 0})
        if self.episode:
            require(self.episode["root"] == str(self.state_root) and
                    self.episode["channel_profile"] == self.profile and
                    self.episode["target_channel_id"] == self.binding["target_channel_id"],
                    "episode_registry_binding_conflict")
            self.row = next((row for row in self.episode["revisions"]
                             if row["revision"] == self.binding["package_revision"]), None)

    def head(self):
        if not self.episode or self.episode["head_revision"] is None:
            return None
        return next(row for row in self.episode["revisions"] if row["revision"] == self.episode["head_revision"])

    def bind_parent(self, *, historical=False):
        parent = self.binding.get("parent")
        if parent is None:
            require(historical or self.head() is None or self.row and self.row["phase"] == "complete",
                    "lineage_head_changed")
            return
        row = next((r for r in self.episode["revisions"] if r["revision"] == parent["revision"]), None) if self.episode else None
        require(row is not None and (historical or row == self.head()) and parent == self.parent_pointer(row),
                "lineage_parent_changed")
        self.parent_receipt, self.parent_readback = self.lineage.history(self.episode, row)
        self.parent_payload = json_data(safe_read(self.lineage.directory(self.episode, row) / PAYLOAD))
        if self.binding["mode"] == "in_place_update":
            require(self.binding["video_sha256"] == row["candidate"]["video_sha256"],
                    "video_changed_use_revision_republish")
            require(self.binding["target_video_id"] == row["video_id"], "update_target_binding_mismatch")
        else:
            require(self.binding["video_sha256"] != row["candidate"]["video_sha256"],
                    "same_media_use_mode_update")

    @staticmethod
    def parent_pointer(row):
        return {"revision": row["revision"], "video_id": row["video_id"],
                "receipt_sha256": row["receipt_sha256"], "video_sha256": row["candidate"]["video_sha256"]}

    @contextlib.contextmanager
    def workspace(self, *, frozen=False):
        with tempfile.TemporaryDirectory(prefix="ytpub-check-") as name:
            self.scratch = Path(name).resolve()
            self.frozen = self.root
            if frozen:
                self.frozen = self.scratch / "package"
                freeze_package(self.root, self.frozen, self.manifest)
            yield
        self.scratch = self.frozen = None

    def proposal(self, mode, *, video_id=None, supersedes_revision=None):
        self.validate_paths()
        self.binding = self.local_candidate()
        self.load_episode()
        if self.row is not None:
            require(mode != "update" or self.binding["video_sha256"] == self.row["candidate"]["video_sha256"],
                    "video_changed_use_revision_republish")
            raise Stop("revision_already_registered_use_original_authorization")
        head = self.head()
        if self.episode:
            require(self.binding["package_revision"] > self.episode["revisions"][-1]["revision"],
                    "revision_not_above_high_water")
            require(not any(row["phase"] in {"ready", "reserved"} for row in self.episode["revisions"]),
                    "revision_already_in_progress")
        if mode == "update":
            require(head is not None and supersedes_revision is None, "update_requires_published_revision")
            require(video_id in (None, head["video_id"]), "update_target_binding_mismatch")
            kind, target = "in_place_update", head["video_id"]
        elif head:
            require(self.binding["video_sha256"] != head["candidate"]["video_sha256"],
                    "same_media_use_mode_update")
            require(video_id is None and supersedes_revision == head["revision"],
                    "explicit_superseded_revision_required")
            kind, target = "revision_republish", None
        else:
            require(video_id is None and supersedes_revision is None, "unexpected_revision_target")
            kind, target = "initial_publish", None
        require(not self.binding["effective_smoke"] or kind == "initial_publish", "private_smoke_policy")
        self.binding.update(mode=kind, target_video_id=target, parent=self.parent_pointer(head) if head else None)
        self.bind_parent()
        with self.workspace():
            plans = self.plan_rows()
            display = [self.display_plan(row, baseline, inputs) for row, baseline, inputs in plans]
            if kind == "in_place_update" and plans and plans[0][0]["operation"] == UPDATE:
                _, _, body = self.update_body(target, self.owned(target))
                require(hashed(body) == plans[0][2]["body_sha256"], "plan_conflict", code=4)
                display[0]["metadata_after"] = body
        rows = [p[0] for p in plans]
        self.binding.update(plan_sha256=hashed(rows), operation_plan=rows)
        return self.binding, display

    @staticmethod
    def display_plan(row, baseline, inputs):
        summary = {"operation": row["operation"], "target": row["target"], "yes": row["yes"],
                   "baseline_sha256": row["baseline_sha256"], "input_sha256": row["input_sha256"],
                   "before": baseline, "request": inputs}
        return summary

    def check_plan(self):
        b = self.binding
        rows = b["operation_plan"]
        require(hashed(rows) == b["plan_sha256"], "operation_plan_digest_mismatch")
        targets = [(p["operation"], canonical(p["target"])) for p in rows]
        require(len(set(targets)) == len(targets) and [ORDER[t[0]] for t in targets] ==
                sorted(ORDER[t[0]] for t in targets), "invalid_operation_plan")
        track_keys = {target_key(track) for track in self.manifest["captions"]}
        for row in rows:
            op, target = row["operation"], row["target"]
            require(row["yes"] is requires_yes(b, op), "operation_confirmation_mismatch")
            if op == UPLOAD:
                require(target == {"episode_key": b["episode_key"]}, "operation_target_mismatch")
            else:
                expected = b["target_video_id"] if b["mode"] == "in_place_update" else PLACEHOLDER
                require(target["video_id"] == expected, "operation_target_mismatch")
            if op in {CAP_ADD, CAP_UPDATE}:
                require(target_key(target) in track_keys, "operation_target_mismatch")
            if op == PLAYLIST:
                require(target["playlist_id"] in b["playlist_ids"], "operation_target_mismatch")
        if b["mode"] in PUBLISH_MODES:
            require([r["operation"] for r in rows].count(THUMB) == 1 and
                    {target_key(r["target"]) for r in rows if r["operation"] == CAP_ADD} == track_keys and
                    {r["target"]["playlist_id"] for r in rows if r["operation"] == PLAYLIST} == set(b["playlist_ids"]),
                    "upload_asset_plan_incomplete")

    def playlist(self, playlist_id):
        result = self.cli(["playlists", "list", "--playlist-id", playlist_id, "--all-pages"])
        items = result.get("items")
        require(result.get("complete") is True and not result.get("nextPageToken") and isinstance(items, list) and
                len(items) == 1 and items[0].get("id") == playlist_id and
                items[0].get("snippet", {}).get("channelId") == self.binding["target_channel_id"],
                "playlist_owner_or_privacy_mismatch", code=4)
        privacy = items[0].get("status", {}).get("privacyStatus")
        require(privacy in {"private", "unlisted", "public"} and
                (not self.binding["effective_smoke"] or privacy == "private"),
                "playlist_owner_or_privacy_mismatch", code=4)
        return {"playlist_id": playlist_id, "channel_id": self.binding["target_channel_id"],
                "privacy_status": privacy}

    def membership(self, video_id, playlist_id):
        page = self.cli(["playlists", "items", "list", playlist_id, "--video-id", video_id, "--all-pages"])
        found = []
        require(page.get("complete") is True and not page.get("nextPageToken") and
                isinstance(page.get("items"), list), "playlist_listing_incomplete", code=4)
        for item in page["items"]:
            snippet = item.get("snippet", {})
            require(snippet.get("playlistId") == playlist_id and snippet.get("resourceId", {}).get("videoId") == video_id and
                    CAPTION_ID.fullmatch(item.get("id") or ""), "playlist_membership_mismatch", code=4)
            found.append(item["id"])
        require(len(found) <= 1, "duplicate_playlist_membership", code=4)
        return found

    def thumbnail_bytes(self, vid):
        dest = self.scratch / ("thumb-" + uuid.uuid4().hex)
        response = self.cli(["thumbnails", "fetch", vid, "--destination", str(dest)])
        checksum = sha_file(dest)
        require(response.get("video_id", vid) == vid and response.get("sha256") == checksum,
                "thumbnail_download_digest_mismatch", code=4)
        return dest, checksum

    def thumbnail_baseline(self, vid, current):
        custom = current.get("contentDetails", {}).get("hasCustomThumbnail")
        require(custom is None or type(custom) is bool, "invalid_thumbnail_baseline", code=4)
        return {"has_custom_thumbnail": custom is True,
                "rendition_sha256": self.thumbnail_bytes(vid)[1] if custom is True else None}

    def caption_rows(self, vid):
        rows = super().caption_rows(vid)
        require(isinstance(rows, list) and all(isinstance(row, dict) and CAPTION_ID.fullmatch(row.get("id") or "") and
                row.get("snippet", {}).get("videoId") == vid for row in rows) and
                len({row["id"] for row in rows}) == len(rows), "invalid_caption_listing", code=4)
        return rows

    def caption_cues(self, caption_id, fmt):
        path = self.scratch / f"caption-{uuid.uuid4().hex}{fmt}"
        receipt = self.cli(["captions", "download", caption_id, "--format", fmt[1:], "--destination", str(path)])
        data = path.read_bytes()
        require(receipt.get("caption_id", caption_id) == caption_id and receipt.get("sha256") == digest(data),
                "caption_download_digest_mismatch", code=4)
        return hashed(cues(data, fmt))

    def track_input(self, track):
        file = track["file"]
        fmt = Path(file["path"]).suffix
        return {"language": track["language"], "name": track["name"], "is_draft": track["isDraft"],
                "file_sha256": file["sha256"], "cue_sha256": hashed(cues(local_bytes(self.frozen, file["path"]), fmt))}

    def track_baseline(self, row, fmt):
        s = row["snippet"]
        require(s.get("trackKind") == "standard" and s.get("isDraft") is False and s.get("status") == "serving",
                "caption_readback_not_serving", code=4)
        return {"video_id": s["videoId"], "caption_id": row["id"], "language": s["language"], "name": s["name"],
                "track_kind": s["trackKind"], "is_draft": s["isDraft"], "status": s["status"],
                "cue_sha256": self.caption_cues(row["id"], fmt)}

    def matching_caption_rows(self, rows, target):
        return [row for row in rows if target_key(row["snippet"]) == target_key(target)]

    def prior_resource(self, operation, **fields):
        for proof in (self.parent_readback or {}).get("resources", []):
            if proof["operation"] == operation and all(proof.get(key) == value for key, value in fields.items()):
                return proof
        return None

    def managed_tracks(self):
        return {
            (p["language"], p["name"]): p for p in (self.parent_readback or {}).get("resources", [])
            if p["operation"] in {CAP_ADD, CAP_UPDATE} and p.get("name") and p.get("language")
        }

    def update_body(self, vid, current):
        payload = json_data(local_bytes(self.frozen, PAYLOAD))
        before = {}
        body = {"id": vid}
        clear_schedule = replace_locales = False
        for part in ("snippet", "status", "paidProductPlacementDetails", "localizations"):
            old = writable_projection(current, part)
            desired = dict(payload.get(part, {}))
            left = dict(old)
            if part == "localizations":
                managed = self.parent_payload.get("localizations", {}).keys()
                desired = {**{key: v for key, v in old.items() if key not in managed}, **desired}
                replace_locales = bool(old.keys() - desired.keys())
            elif part == "snippet" and ("tags" in old or "tags" in desired):
                left.setdefault("tags", [])
                desired.setdefault("tags", [])
            elif part == "status":
                desired = {**{key: old[key] for key in PRESERVED_STATUS if key in old}, **desired}
                if desired.get("containsSyntheticMedia") is False and "containsSyntheticMedia" not in old:
                    left["containsSyntheticMedia"] = False
                if "publishAt" in old and "publishAt" in desired and utc(old["publishAt"]) == utc(desired["publishAt"]):
                    left["publishAt"] = desired["publishAt"]
                clear_schedule = "publishAt" in old and "publishAt" not in desired
            if canonical(left) != canonical(desired):
                before[part] = old
                body[part] = desired
        baseline = {"id": vid, "channel_id": self.binding["target_channel_id"], "parts": before}
        inputs = {"body_sha256": hashed(body), "parts": sorted(before), "clear_publish_at": clear_schedule,
                  "replace_localizations": replace_locales}
        return baseline, inputs, body

    def upload_description(self):
        return ({"parent": self.binding["parent"], "media_key": self.media_key},
                {name: self.binding[name] for name in ("payload_sha256", "video_sha256", "notify_subscribers")})

    def plan_rows(self):
        b = self.binding
        planned = []
        def add(op, target, before, inputs):
            planned.append((operation_row(b, op, target, before, inputs), before, inputs))
        if b["mode"] in PUBLISH_MODES:
            add(UPLOAD, {"episode_key": b["episode_key"]}, *self.upload_description())
            add(THUMB, {"video_id": PLACEHOLDER}, None, {"thumbnail_sha256": b["thumbnail_sha256"]})
            for track in sorted(self.manifest["captions"], key=target_key):
                add(CAP_ADD, {"video_id": PLACEHOLDER, "language": track["language"], "name": track["name"]},
                    {"matching_ids": []}, self.track_input(track))
            for pid in sorted(b["playlist_ids"]):
                add(PLAYLIST, {"video_id": PLACEHOLDER, "playlist_id": pid},
                    {**self.playlist(pid), "matching_ids": []}, {"playlist_id": pid, "video_id": PLACEHOLDER})
            return planned

        vid = b["target_video_id"]
        current = self.owned(vid)
        require(current.get("processingDetails", {}).get("processingStatus") == "succeeded",
                "video_processing_pending", code=4)
        baseline, inputs, body = self.update_body(vid, current)
        if len(body) > 1:
            add(UPDATE, {"video_id": vid}, baseline, inputs)
        before_thumb = self.thumbnail_baseline(vid, current)
        proof = self.prior_resource(THUMB)
        if not (proof and proof["source_sha256"] == b["thumbnail_sha256"] and before_thumb["has_custom_thumbnail"] and
                proof["rendition_sha256"] == before_thumb["rendition_sha256"]):
            add(THUMB, {"video_id": vid}, before_thumb, {"thumbnail_sha256": b["thumbnail_sha256"]})
        rows = self.caption_rows(vid)
        managed = self.managed_tracks()
        desired = {target_key(track): track for track in self.manifest["captions"]}
        for key in sorted(desired):
            track = desired[key]
            selected = self.matching_caption_rows(rows, track)
            data = self.track_input(track)
            target = {"video_id": vid, "language": key[0], "name": key[1]}
            if not selected:
                require(key not in managed, "managed_caption_missing", code=4)
                add(CAP_ADD, target, {"matching_ids": []}, data)
                continue
            require(len(selected) == 1 and key in managed and selected[0]["id"] == managed[key]["provider_id"],
                    "caption_ownership_conflict", code=4)
            before = self.track_baseline(selected[0], Path(track["file"]["path"]).suffix)
            if before["cue_sha256"] != data["cue_sha256"]:
                add(CAP_UPDATE, {**target, "caption_id": selected[0]["id"]}, before, data)
        for key in sorted(managed.keys() - desired.keys()):
            proof = managed[key]
            selected = [row for row in rows if row["id"] == proof["provider_id"]]
            if not selected:
                continue
            require(target_key(selected[0]["snippet"]) == key, "caption_ownership_conflict", code=4)
            before = self.track_baseline(selected[0], ".srt")
            add(CAP_DELETE, {"video_id": vid, "language": key[0], "name": key[1], "caption_id": selected[0]["id"]},
                before, {"caption_id": selected[0]["id"], "absent_from_seal": True,
                         "parent_receipt_sha256": b["parent"]["receipt_sha256"]})
        for pid in sorted(b["playlist_ids"]):
            playlist = self.playlist(pid)
            if not self.membership(vid, pid):
                add(PLAYLIST, {"video_id": vid, "playlist_id": pid}, {**playlist, "matching_ids": []},
                    {"playlist_id": pid, "video_id": vid})
        return sorted(planned, key=lambda plan: ORDER[plan[0]["operation"]])

    def check_title(self):
        seen = set()
        allowed = set()
        for row in (self.episode or {}).get("revisions", []):
            if row["phase"] in {"complete", "superseded"}:
                receipt, _ = self.lineage.history(self.episode, row)
                allowed.add(receipt["video_id"])
            elif row["phase"] == "abandoned":
                closure = self.verify_closure(row)
                allowed.update(closure["orphan_upload_ids"])
        result = self.cli(["videos", "list", "--all-pages"])
        require(result.get("complete") is True and not result.get("nextPageToken") and
                isinstance(result.get("items"), list), "uploads_listing_incomplete", code=4)
        for row in result["items"]:
            snippet = row.get("snippet", {})
            require(isinstance(snippet.get("title"), str), "invalid_upload_listing", code=4)
            if snippet["title"] != self.manifest["snippet"]["title"]:
                continue
            detail = row.get("contentDetails", {}).get("videoId")
            resource = snippet.get("resourceId", {}).get("videoId")
            found = detail or resource
            require(isinstance(found, str) and VIDEO_ID.fullmatch(found) and found in allowed and
                    found not in seen and (detail is None or resource is None or detail == resource),
                    "upload_title_collision_requires_operator", code=4)
            seen.add(found)
            self.owned(found)

    def known_video(self):
        return self.binding.get("target_video_id") or super().known_video()

    def operation_key(self, row):
        return hashed([self.binding["episode_key"], self.binding["package_revision"],
                       self.binding["plan_sha256"], row["operation"], row["target"], row["input_sha256"]])

    def check_write(self, operation, *, refresh_local):
        if refresh_local:
            b = self.local_candidate()
            require(all(self.binding[key] == val for key, val in b.items() if key != "mode"),
                    "package_or_runtime_binding_changed")
            report, _ = check(self.frozen, self.profile, config=self.config, require_seal=True)
            require(report.get("contract_passed") and all(
                report["binding"][key] == self.binding[key] for key in ("manifest_sha256", "payload_sha256",
                                                                      "contract_bundle_sha256")),
                "frozen_package_binding_changed")
        chain = self.store.chain(self.auth_id, self.binding, self.clock())
        require(chain[-1] == (self.active, self.active_hash), "authorization_head_changed")
        require(self.expired_seconds() > 0, "writes_blocked_expired")
        require(operation in self.active["allowed_operations"], "operation_not_authorized")

    def current_inputs(self, descriptor, vid):
        op, target = descriptor["operation"], descriptor["target"]
        extra = {}
        if op == UPLOAD:
            before, inputs = self.upload_description()
        elif op == UPDATE:
            current = self.owned(vid)
            before, inputs, body = self.update_body(vid, current)
            extra = {"body": body, "snapshot": {
                "id": vid, "snippet": {"channelId": self.binding["target_channel_id"]},
                **before["parts"],
            }}
            extra["snapshot"]["snippet"] = {**extra["snapshot"].get("snippet", {}),
                                             "channelId": self.binding["target_channel_id"]}
        elif op == THUMB:
            current = self.owned(vid)
            observed = self.thumbnail_baseline(vid, current)
            before = observed if self.binding["mode"] == "in_place_update" else None
            require(before is not None or not observed["has_custom_thumbnail"],
                    "thumbnail_exists_without_provenance", code=4)
            inputs = {"thumbnail_sha256": self.binding["thumbnail_sha256"]}
        elif op in {CAP_ADD, CAP_UPDATE, CAP_DELETE}:
            selected = self.matching_caption_rows(self.caption_rows(vid), target)
            track = next((track for track in self.manifest["captions"] if target_key(track) == target_key(target)), None)
            if op == CAP_ADD:
                before = {"matching_ids": [entry["id"] for entry in selected]}
            else:
                require(len(selected) == 1 and selected[0]["id"] == target["caption_id"] and
                        self.managed_tracks().get(target_key(target), {}).get("provider_id") == target["caption_id"],
                        "caption_ownership_conflict", code=4)
                fmt = Path(track["file"]["path"]).suffix if track is not None else ".srt"
                before = self.track_baseline(selected[0], fmt)
            inputs = self.track_input(track) if track is not None else {
                "caption_id": target["caption_id"], "absent_from_seal": True,
                "parent_receipt_sha256": self.binding["parent"]["receipt_sha256"],
            }
            extra = {"track": track}
        elif op == PLAYLIST:
            playlist_id = target["playlist_id"]
            before = {**self.playlist(playlist_id), "matching_ids": self.membership(vid, playlist_id)}
            inputs = {"playlist_id": playlist_id, "video_id": target["video_id"]}
        else:
            raise Stop("unknown_operation")
        return before, inputs, extra

    @contextlib.contextmanager
    def command(self, descriptor, vid, metadata, *, preview=False, resume=None):
        op = descriptor["operation"]
        target = descriptor["target"]
        with contextlib.ExitStack() as stack:
            descriptors = []
            def media(record):
                stream = stack.enter_context(artifact_open(self.frozen, record["path"]))
                descriptors.append(stream.fileno())
                return ["--media-fd", str(stream.fileno()), "--media-sha256", record["sha256"]]
            if op == UPLOAD:
                stream = stack.enter_context(artifact_open(self.frozen, PAYLOAD))
                descriptors.append(stream.fileno())
                notify_flag = "--notify-subscribers" if self.binding["notify_subscribers"] else "--no-notify-subscribers"
                args = ["videos", "upload", "--metadata-fd", str(stream.fileno()), "--metadata-file-sha256",
                        self.binding["payload_sha256"], notify_flag, *media(self.manifest["delivery_video"])]
                if resume:
                    args += ["--resume-handle", resume["session_handle"], "--offset", str(resume["offset"])]
            elif op == UPDATE:
                body = canonical(metadata["body"])
                metadata_path = self.scratch / f"metadata-{uuid.uuid4().hex}.json"
                atomic_write(metadata_path, body, exclusive=True)
                stream = stack.enter_context(artifact_open(self.scratch, metadata_path.name))
                descriptors.append(stream.fileno())
                baseline = self.scratch / f"baseline-{uuid.uuid4().hex}.json"
                atomic_write(baseline, canonical({"items": [metadata["snapshot"]]}), exclusive=True)
                args = ["videos", "update", vid, "--metadata-fd", str(stream.fileno()),
                        "--metadata-file-sha256", digest(body), "--baseline-file", str(baseline)]
                for flag, active in (
                    ("--clear-publish-at", "publishAt" in metadata["snapshot"].get("status", {}) and
                     "status" in metadata["body"] and "publishAt" not in metadata["body"]["status"]),
                    ("--replace-localizations", "localizations" in metadata["body"] and bool(
                     metadata["snapshot"]["localizations"].keys() - metadata["body"]["localizations"].keys())),
                ):
                    if active:
                        args.append(flag)
            elif op == THUMB:
                args = ["thumbnails", "set", vid, *media(self.manifest["thumbnail"])]
            elif op == CAP_ADD:
                args = ["captions", "upload", vid, "--language", target["language"], "--name", target["name"],
                        *media(metadata["track"]["file"])]
            elif op == CAP_UPDATE:
                args = ["captions", "update", target["caption_id"], *media(metadata["track"]["file"])]
            elif op == CAP_DELETE:
                args = ["captions", "delete", target["caption_id"]]
            else:
                args = ["playlists", "items", "add", target["playlist_id"], "--video-id", vid]
            yield args + (["--dry-run"] if preview else ["--yes"] if descriptor["yes"] else []), tuple(descriptors)

    def confirm_preview(self, op, planned, actual, inputs, metadata, resume):
        require(planned.get("dry_run") is True and planned.get("identity_verified") is False,
                "unverified_dry_run")
        if resume:
            require(planned.get("method") == "PUT" and planned.get("resume") is True and planned.get("complete") is False and
                    planned.get("session_handle") == resume["session_handle"] and planned.get("offset") == resume["offset"],
                    "resume_preview_mismatch")
        else:
            require(planned.get("complete") is True, "unverified_dry_run")
        if op == UPLOAD:
            require(planned["metadata_sha256"] == self.binding["payload_sha256"] and planned["media"]["sha256"] ==
                    self.binding["video_sha256"] and (resume or planned.get("method") == "POST" and
                    planned["query"].get("notifySubscribers") is self.binding["notify_subscribers"]),
                    "upload_preview_mismatch")
        if op == UPDATE:
            require(planned.get("method") == "PUT" and planned.get("metadata_sha256") == inputs["body_sha256"] and
                    planned.get("metadata") == metadata["body"], "update_preview_mismatch")
        expected_media = (self.binding["thumbnail_sha256"] if op == THUMB else
                          inputs["file_sha256"] if op in {CAP_ADD, CAP_UPDATE} else None)
        if expected_media is not None:
            require(planned["media"]["sha256"] == expected_media, "asset_preview_mismatch")
        methods = {THUMB: "POST", CAP_ADD: "POST", CAP_UPDATE: "PUT", CAP_DELETE: "DELETE", PLAYLIST: "POST"}
        if op in methods:
            require(planned.get("method") == methods[op], "asset_preview_method_mismatch")
        query = planned.get("query", {})
        if op == THUMB:
            require(query.get("videoId") == actual, "thumbnail_preview_target_mismatch")
        if op == CAP_ADD:
            snippet = planned.get("metadata", {}).get("snippet", {})
            require(snippet.get("videoId") == actual and snippet.get("language") == inputs["language"] and
                    snippet.get("name") == inputs["name"] and snippet.get("isDraft") is False,
                    "caption_preview_target_mismatch")
        if op == CAP_DELETE:
            require(query.get("id") == inputs["caption_id"], "caption_preview_target_mismatch")
        if op == CAP_UPDATE:
            require(planned.get("metadata", {}).get("id") == metadata["caption_id"],
                    "caption_preview_target_mismatch")
        if op == PLAYLIST:
            snippet = planned.get("metadata", {}).get("snippet", {})
            require(snippet.get("playlistId") == inputs["playlist_id"] and
                    snippet.get("resourceId", {}).get("videoId") == actual, "playlist_preview_target_mismatch")

    def validate_ack(self, op, result, vid, target):
        key = {UPLOAD: "video_id", UPDATE: "video_id", THUMB: "video_id", CAP_ADD: "caption_id",
               CAP_UPDATE: "caption_id", CAP_DELETE: "caption_id", PLAYLIST: "item_id"}[op]
        value = result.get(key)
        pattern = VIDEO_ID if key == "video_id" else CAPTION_ID
        require(isinstance(value, str) and pattern.fullmatch(value), "invalid_ack_identity", code=11)
        if op in {UPDATE, THUMB}:
            require(value == vid, "invalid_ack_identity", code=11)
        if op in {CAP_UPDATE, CAP_DELETE}:
            require(value == target["caption_id"], "invalid_ack_identity", code=11)
        if op == UPLOAD:
            database = self.lineage.read()
            previous = {known for episode in database["episodes"].values() for row in episode["revisions"]
                        if row["candidate"]["target_channel_id"] == self.binding["target_channel_id"]
                        for known in [row.get("video_id"), *row.get("closure", {}).get("retained_video_ids", [])]
                        if known is not None}
            require(value not in previous, "republish_reused_video_id", code=11)
        answer = {key: value}
        if op == UPLOAD:
            if "session_handle" in result:
                require(SESSION_HANDLE.fullmatch(result["session_handle"]), "invalid_ack_identity", code=11)
                answer["session_handle"] = result["session_handle"]
            notify = result.get("notify_subscribers")
            require(notify is self.binding["notify_subscribers"] or
                    (notify == "unknown" and not self.binding["effective_smoke"]), "upload_notification_mismatch", code=11)
            answer["notify_subscribers"] = notify
        return answer

    def perform(self, descriptor, vid):
        op = descriptor["operation"]
        key = self.operation_key(descriptor)
        resume = None
        try:
            acknowledgement = self.pending(key)
        except Stop:
            active_intent = self.job.record(key, "INTENT")
            approved_suffix = self.job.record(key, "RESUME_AUTHORIZED")
            if op != UPLOAD or not approved_suffix or not active_intent or approved_suffix["seq"] <= active_intent["seq"]:
                raise
            acknowledgement, resume = None, approved_suffix
        if acknowledgement:
            return acknowledgement
        self.check_write(op, refresh_local=True)
        before, inputs, metadata = self.current_inputs(descriptor, vid)
        metadata["caption_id"] = descriptor["target"].get("caption_id")
        if op == PLAYLIST and self.binding["mode"] in PUBLISH_MODES and before["matching_ids"]:
            require(descriptor == operation_row(self.binding, op, descriptor["target"],
                    {**before, "matching_ids": []}, inputs), "plan_conflict", code=4)
            return None
        require(descriptor == operation_row(self.binding, op, descriptor["target"], before, inputs),
                "plan_conflict", code=4)
        if op == UPLOAD and not resume:
            self.check_title()
        with self.command(descriptor, vid, metadata, preview=True, resume=resume) as (args, fds):
            planned = self.cli(args, fds=fds)
        self.confirm_preview(op, planned, vid, inputs, metadata, resume)
        self.check_write(op, refresh_local=True)
        latest_before, latest_inputs, _ = self.current_inputs(descriptor, vid)
        require(descriptor == operation_row(self.binding, op, descriptor["target"], latest_before, latest_inputs),
                "plan_conflict", code=4)
        intent = self.job.append("INTENT", operation=op, op_key=key, attempt_id=uuid.uuid4().hex,
                                 input_sha256=descriptor["input_sha256"], baseline=before,
                                 request_body=metadata.get("body"), target=descriptor["target"],
                                 authorization_id=self.auth_id, authorization_sha256=self.active_hash,
                                 wire_sha256=hashed(planned), resumed=bool(resume),
                                 notify_subscribers=self.binding["notify_subscribers"] if op == UPLOAD else None)
        attempt = {"operation": op, "op_key": key, "attempt_id": intent["attempt_id"]}
        try:
            def guard():
                try:
                    self.check_write(op, refresh_local=False)
                except Stop as exc:
                    raise Stop("dispatch_authority_changed", code=10) from exc
            guard()
            with self.command(descriptor, vid, metadata, resume=resume) as (args, fds):
                result = self.cli(args, fds=fds, lock=self.lock, seconds=min(600, self.expired_seconds()), guard=guard)
            fields = self.validate_ack(op, result, vid, descriptor["target"])
            self.write_count += 1
            return self.job.append("ACK", **attempt, **fields)
        except Stop as exc:
            if op == UPLOAD and exc.code == 7 and exc.reason in {"upload_readback_incomplete", "privacy_mismatch"}:
                vid = exc.detail.get("video_id")
                if isinstance(vid, str) and VIDEO_ID.fullmatch(vid):
                    evidence = self.validate_ack(op, {**exc.detail,
                        "notify_subscribers": self.binding["notify_subscribers"] if not resume else "unknown"},
                        None, descriptor["target"])
                    self.job.append("ACK", **attempt, **evidence)
            self.job.append("ERROR", **attempt, error=exc.reason,
                            effect=exc.effect or ("unknown" if exc.code in {7, 10, 11} else "none"),
                            upload_init_dispatch=exc.upload_init_dispatch or "unproven", safe_ids=exc.detail)
            raise

    def thumbnail_proof(self, vid, actual, thumb_ack):
        require(actual.get("contentDetails", {}).get("hasCustomThumbnail") is True,
                "custom_thumbnail_readback_missing", code=4)
        if self.binding["effective_smoke"]:
            return super().read_thumbnail(vid, actual)
        dest, remote_hash = self.thumbnail_bytes(vid)
        source = self.frozen / self.manifest["thumbnail"]["path"]
        expected = self.binding["thumbnail_sha256"]
        frame = cv2.imread(str(dest))
        original = cv2.imread(str(source))
        require(frame is not None and original is not None, "thumbnail_decode_failed", code=4)
        provenance, marker = None, None
        if remote_hash == expected or frame.shape == original.shape and bool((frame == original).all()):
            provenance = "exact_image"
        if provenance is None:
            prior = self.prior_resource(THUMB)
            if prior and prior["source_sha256"] == expected and prior["rendition_sha256"] == remote_hash:
                provenance = "parent_rendition"
        if provenance is None:
            try:
                expected_marker, _ = qr_evidence(source)
                observed_marker, _ = qr_evidence(dest)
                require(expected_marker == observed_marker, "thumbnail_marker_readback_mismatch", code=4)
                previous = self.prior_resource(THUMB)
                if not previous or previous.get("marker_sha256") != expected_marker:
                    provenance, marker = "unique_marker", expected_marker
            except Stop:
                pass
        if provenance is None and thumb_ack:
            row = self.job.record(thumb_ack["op_key"], "THUMBNAIL_RENDITION_ATTESTED")
            if row and row["source_sha256"] == expected and row["download_sha256"] == remote_hash:
                provenance = "operator_rendition"
        if provenance is None:
            raise Stop("thumbnail_rendition_requires_operator", code=4,
                       detail={"video_id": vid, "source_sha256": expected, "download_sha256": remote_hash})
        return {"provider_id": vid, "source_sha256": expected, "rendition_sha256": remote_hash,
                "dimensions": [int(frame.shape[1]), int(frame.shape[0])], "marker_sha256": marker,
                "decoder": cv2.__version__, "rendition_evidence": provenance}

    def record_verified(self, op, target, proof, descriptor=None):
        key = (self.operation_key(descriptor) if descriptor else
               hashed([self.key, self.binding["package_revision"], "readback", op, target]))
        self.verify_event(key, op, proof)
        event = self.job.record(key, "VERIFIED")
        self.evidence[key] = {**{name: value for name, value in event.items()
                                if name not in {"seq", "event", "prev_entry_sha256", "at"}},
                              "verified_seq": event["seq"]}

    def verify_updated_parts(self, actual, intent):
        body = intent["request_body"]
        for part, expected in body.items():
            if part == "id":
                continue
            observed = writable_projection(actual, part)
            if part == "status":
                if expected.get("containsSyntheticMedia") is False and "containsSyntheticMedia" not in observed:
                    observed["containsSyntheticMedia"] = False
                if ("publishAt" in observed and "publishAt" in expected and
                        utc(observed["publishAt"]) == utc(expected["publishAt"])):
                    observed["publishAt"] = expected["publishAt"]
            if part == "snippet" and expected.get("tags") == []:
                observed.setdefault("tags", [])
            require(canonical(observed) == canonical(expected), "video_field_readback_mismatch", code=4)

    def verify_video(self, vid, descriptor, status_sent):
        current = self.owned(vid)
        processing = current.get("processingDetails", {}).get("processingStatus")
        if processing != "succeeded" and self.binding["mode"] in PUBLISH_MODES:
            require(processing not in {"failed", "terminated"}, "video_processing_failed", code=4)
            wait = self.cli(["videos", "wait-processing", vid, "--timeout", "120"])
            require(wait.get("processing_status") == "succeeded", "video_processing_pending", code=4)
            current = self.owned(vid)
        require(current.get("processingDetails", {}).get("processingStatus") == "succeeded",
                "processing_readback_drift", code=4)
        proof = matching_video(current, self.manifest, self.duration, production=True,
                               wire_disclosure=self.manifest["status"]["containsSyntheticMedia"] if status_sent else None)
        if descriptor and descriptor["operation"] == UPDATE:
            self.verify_updated_parts(current, self.job.record(self.operation_key(descriptor), "INTENT"))
        if not status_sent and self.parent_readback:
            prior = next((p for p in self.parent_readback["resources"] if "containsSyntheticMedia" in p.get("fields", {})), {})
            old = prior.get("fields", {}).get("containsSyntheticMedia", {})
            proof["fields"]["containsSyntheticMedia"]["wire_request_sent"] = old.get("wire_request_sent")
            proof["fields"]["containsSyntheticMedia"]["wire_evidence_parent"] = self.binding["parent"]["receipt_sha256"]
        self.last_video = current
        return current, proof

    def verify_all(self):
        vid = self.known_video()
        require(vid is not None, "video_identity_unproven", code=4)
        actions = self.binding["operation_plan"]
        same = lambda op, **fields: next((d for d in actions if d["operation"] == op and
                                         all(d["target"].get(k) == v for k, v in fields.items())), None)
        video_op = same(UPLOAD) or same(UPDATE)
        video_intent = self.job.record(self.operation_key(video_op), "INTENT") if video_op else None
        status_sent = video_op is not None and (video_op["operation"] == UPLOAD or
                                               "status" in (video_intent.get("request_body") or {}))
        current, proof = self.verify_video(vid, video_op, status_sent)
        self.record_verified(video_op["operation"] if video_op else UPDATE, vid, {
            "provider_id": vid, **proof, "processing_status": "succeeded",
        }, video_op)

        desc = same(THUMB)
        ack = self.job.record(self.operation_key(desc), "ACK") if desc else None
        self.record_verified(THUMB, vid, self.thumbnail_proof(vid, current, ack), desc)

        rows = self.caption_rows(vid)
        desired = set()
        for track in self.manifest["captions"]:
            lang, name = target_key(track)
            selected = self.matching_caption_rows(rows, track)
            require(len(selected) == 1, "caption_identity_mismatch", code=4)
            cid = selected[0]["id"]
            desc = same(CAP_UPDATE, language=lang, name=name) or same(CAP_ADD, language=lang, name=name)
            if desc is not None:
                ack = self.pending(self.operation_key(desc))
                require(ack and ack["caption_id"] == cid, "caption_identity_mismatch", code=4)
            elif self.managed_tracks():
                require(self.managed_tracks().get((lang, name), {}).get("provider_id") == cid,
                        "caption_ownership_conflict", code=4)
            evidence = super().read_caption(vid, track, cid)
            self.record_verified(desc["operation"] if desc else CAP_ADD, (lang, name), {
                **evidence, "name": name, "video_id": vid,
            }, desc)
            desired.add((lang, name))
        for key in self.managed_tracks().keys() - desired:
            cid = self.managed_tracks()[key]["provider_id"]
            require(all(row["id"] != cid for row in rows), "managed_caption_still_present", code=4)
            desc = same(CAP_DELETE, caption_id=cid)
            self.record_verified(CAP_DELETE, cid, {"provider_id": cid, "video_id": vid, "absent": True}, desc)
        for pid in self.binding["playlist_ids"]:
            self.playlist(pid)
            ids = self.membership(vid, pid)
            desc = same(PLAYLIST, playlist_id=pid)
            ack = self.pending(self.operation_key(desc)) if desc else None
            require(len(ids) == 1 and (not ack or ack["item_id"] == ids[0]), "playlist_readback_mismatch", code=4)
            self.record_verified(PLAYLIST, pid, {"provider_id": ids[0], "video_id": vid, "playlist_id": pid}, desc)
        self.verify_video(vid, video_op, status_sent)
        return vid

    def verify_operation(self, descriptor, ack):
        op, target = descriptor["operation"], descriptor["target"]
        vid = self.known_video()
        if op in {UPLOAD, UPDATE}:
            intent = self.job.record(self.operation_key(descriptor), "INTENT")
            _, proof = self.verify_video(vid, descriptor,
                                         op == UPLOAD or "status" in (intent.get("request_body") or {}))
            proof.update(provider_id=vid, processing_status="succeeded")
        elif op == THUMB:
            proof = self.thumbnail_proof(vid, self.owned(vid), ack)
        elif op in {CAP_ADD, CAP_UPDATE}:
            track = next(track for track in self.manifest["captions"] if target_key(track) == target_key(target))
            proof = {**super().read_caption(vid, track, ack["caption_id"]), "name": track["name"], "video_id": vid}
        elif op == CAP_DELETE:
            cid = target["caption_id"]
            require(ack["caption_id"] == cid and all(r["id"] != cid for r in self.caption_rows(vid)),
                    "managed_caption_still_present", code=4)
            proof = {"provider_id": cid, "video_id": vid, "absent": True}
        else:
            pid = target["playlist_id"]
            self.playlist(pid)
            ids = self.membership(vid, pid)
            require(len(ids) == 1 and (not ack or ids[0] == ack["item_id"]),
                    "playlist_readback_mismatch", code=4)
            proof = {"provider_id": ids[0], "video_id": vid, "playlist_id": pid}
        self.record_verified(op, target, proof, descriptor)

    def publish_production(self):
        receipt_path = self.job.directory / RECEIPT
        existing = receipt_path.exists() or receipt_path.is_symlink()
        self.finalized_receipt_present = existing
        if existing:
            receipt, _, checksum = self.lineage.final(self.job, self.binding, allow_unfinalized=True)
            self.verify_all()
            self.promote(receipt["video_id"], checksum)
            return self.noop(receipt, "current_owner_readback")
        require(not self.job.events("FINALIZED"), "missing_final_receipt")
        for item in self.binding["operation_plan"]:
            ack = self.perform(item, self.known_video())
            if item["operation"] == UPLOAD:
                self.job.snapshot(self.binding, "VIDEO_KNOWN", ack["video_id"])
            self.verify_operation(item, ack)
        vid = self.verify_all()
        if self.binding["mode"] == "in_place_update":
            prior = self.parent_readback.get("notify_request_evidence", UNKNOWN_NOTIFY)
            self.notification = {"value": prior["value"], "source": "parent_receipt",
                                 "ref_sha256": self.binding["parent"]["receipt_sha256"]}
        else:
            ack = next(row for row in reversed(self.job.rows) if row["event"] in {"ACK", "RECONCILED"} and
                       row.get("operation") == UPLOAD)
            notify = ack["notify_subscribers"]
            self.notification = {"value": notify, "source": "legacy_unknown" if notify == "unknown" else
                                 ("bound_session" if ack.get("session_handle") and self.job.record(
                                     ack["op_key"], "INTENT").get("resumed") else "initial_intent"),
                                 "ref_sha256": hashed(ack)}
        readback = canonical(self.readback("COMPLETE", []))
        atomic_write(self.job.directory / READBACK, readback)
        b = self.binding
        # No remote video is removed by a revision. The receipt can carry a manual hint.
        suggestion = cleanup(b, b["parent"]["video_id"]) if b["mode"] == "revision_republish" else None
        receipt = {**current_header(b), "candidate": b, "video_id": vid, "authorization_id": self.auth_id,
                   "authorization_sha256": self.active_hash, "readback_sha256": digest(readback),
                   "journal_seq": len(self.job.rows), "journal_sha256": self.job.tail,
                   "completed_at": timestamp(self.clock()), "cleanup_suggestion": suggestion}
        raw = canonical(receipt)
        atomic_write(receipt_path, raw, exclusive=True)
        _, _, checksum = self.lineage.final(self.job, b, allow_unfinalized=True)
        self.promote(vid, checksum)
        result = {"status": {"in_place_update": "updated", "revision_republish": "republished",
                             "initial_publish": "published"}[b["mode"]], "video_id": vid,
                  "mutations": self.write_count, "receipt_sha256": checksum,
                  "observed_privacy": self.last_video["status"]["privacyStatus"]}
        if suggestion:
            result["cleanup_suggestion"] = suggestion
        return result

    def promote(self, vid, checksum):
        if not self.job.events("FINALIZED"):
            self.job.append("FINALIZED", video_id=vid, receipt_sha256=checksum)
        if self.row["phase"] == "ready":
            self.job.snapshot(self.binding, "COMPLETE", vid)
            self.lineage.change(self.row, "complete", video_id=vid, receipt_sha256=checksum)

    def noop(self, receipt, as_of):
        return {"status": "already_updated_noop" if self.binding["mode"] == "in_place_update" else
                "already_published_noop", "video_id": receipt["video_id"], "mutations": 0,
                "evidence_as_of": as_of}

    def readback(self, state, reasons):
        complete = state == "COMPLETE"
        b = self.binding
        current = self.last_video or {}
        status = current.get("status", {})
        schedule = status.get("publishAt")
        if schedule and complete:
            schedule = b["publish_at"]
        return {**current_header(b), "video_id": self.known_video(), "overall": "complete" if complete else
                ("unknown" if state == "RECONCILIATION_REQUIRED" else "partial"), "state": state,
                "requested_privacy": b["target_privacy_status"], "observed_privacy": status.get("privacyStatus"),
                "requested_publish_at": b["publish_at"], "observed_publish_at": schedule,
                "processing_status": current.get("processingDetails", {}).get("processingStatus"),
                "package_notify_subscribers": b["notify_subscribers"], "notification_effect": (
                    "not_applicable" if b["mode"] == "in_place_update" else "insert_query"),
                "notify_request_evidence": self.notification, "resources": list(self.evidence.values()),
                "partial_reasons": reasons, "evidence_as_of": "finalized" if complete else "attempt",
                "observed_at": timestamp(self.clock()), "provenance": "owner_bound_independent_get_list_download"}

    def exact_inputs(self, candidate):
        safe_private(self.root)
        require(self.preview.parent == self.root.parent and not self.preview.is_symlink() and
                sha_file(self.preview) == candidate["preview_sha256"], "preview_binding_mismatch")
        raw = local_bytes(self.root, MANIFEST)
        manifest = json_data(raw)
        require(manifest["channel_profile"] == self.profile and
                manifest["target_channel_id"] == candidate["target_channel_id"] and
                digest(raw) == candidate["manifest_sha256"] and
                digest(local_bytes(self.root, PAYLOAD)) == candidate["payload_sha256"] and
                digest(local_bytes(self.root, SEAL)) == candidate["seal_sha256"], "candidate_artifacts_changed")
        seal = json_data(local_bytes(self.root, SEAL))
        artifacts = close_artifacts(self.root, manifest, raw)
        require(all(seal[name] == value for name, value in artifacts.items() if name != "contract_bundle_sha256"),
                "candidate_artifacts_changed")
        self.manifest = manifest
        self.key = episode_key(candidate)
        self.media_key = media_key(candidate)

    def execute(self, mode, *, resolution=None, video_id=None, inspect_effects=False):
        self.mode = mode
        self.validate_paths()
        approval, _ = self.store.load("authorizations", self.auth_id)
        validate_auth(approval)
        require(approval["authorization_version"] == "3.0" and approval["channel_profile"] == self.profile,
                "authorization_profile_mismatch")
        from auth_store import binding_fields
        candidate = {key: approval[key] for key in binding_fields(approval)}
        candidate.update(contract_version=approval["contract_version"], authorization_version="3.0")
        kind = candidate["mode"]
        require((mode == "update" and kind == "in_place_update") or (mode == "publish" and kind in PUBLISH_MODES) or
                mode in {"plan", "reconcile"}, "authorization_mode_mismatch")
        require(video_id is None or kind == "in_place_update" and video_id == candidate["target_video_id"],
                "update_target_binding_mismatch")
        self.binding = candidate
        resolution_value = self.store.load("resolutions", resolution) if resolution else None
        historical = resolution_value is not None and resolution_value[0].get("scope") == "revision"
        self.exact_inputs(candidate)
        self.load_episode()
        existing_completed = self.row and self.row["phase"] in {"complete", "superseded"}
        reserved_inspection = bool(inspect_effects and self.row and self.row["phase"] == "reserved")
        historical = historical or reserved_inspection or bool(existing_completed and (self.row["phase"] == "superseded" or
                        candidate["cli_identity_sha256"] != self.hash_cli() or candidate["publish_at"] and
                        utc(candidate["publish_at"]) <= self.clock())) or bool(self.row and self.row["phase"] == "abandoned")
        if not historical:
            actual = self.local_candidate()
            if kind == "in_place_update" and actual["video_sha256"] != candidate["parent"]["video_sha256"]:
                raise Stop("video_changed_use_revision_republish")
            require(all(candidate[key] == value for key, value in actual.items() if key != "mode"),
                    "authorization_binding_mismatch")
        self.check_plan()
        self.auth_chain = self.store.chain(self.auth_id, candidate, self.clock(), historical=historical)
        self.active, self.active_hash = self.auth_chain[-1]
        planned_ops = {row["operation"] for row in candidate["operation_plan"]} | {"readback"}
        require(set(self.auth_chain[0][0]["allowed_operations"]) == planned_ops,
                "genesis_authorization_requires_all_operations")
        if mode in {"publish", "update"}:
            self.lineage.prepare()
            safe_private(self.state_root, create=True)
            if self.row is None and not historical:
                require(self.expired_seconds() > 0 and len(self.auth_chain) == 1, "initial_write_requires_active_genesis")
            self.lineage.upgrade()
        if self.registry.exists():
            require(not self.registry.is_symlink(), "unsafe_registry_directory")
        can_lock = (self.registry / "locks").is_dir()
        lease = self.lineage.lock(self.key, shared=mode == "plan") if can_lock else contextlib.nullcontext(None)
        with lease as lock:
            self.lock = lock
            self.load_episode()
            if mode in {"publish", "update"} and not historical:
                self.repair_terminal()
                self.load_episode()
            if self.row is not None:
                require(self.row["candidate"] == self.binding, "episode_registry_binding_conflict")
                if self.row["phase"] == "abandoned":
                    closure = self.verify_closure(self.row)
                    if resolution_value:
                        record, checksum = resolution_value
                        require(record["resolution_id"] == closure["resolution_id"] and
                                checksum == closure["resolution_sha256"], "revision_terminal_resolution_conflict")
                    return {"status": "revision_abandoned_no_retry", "mutations": 0, "closure": closure}
                if historical and existing_completed:
                    receipt, _ = self.lineage.history(self.episode, self.row)
                    self.job = self.lineage.job_history(self.episode, self.row)
                    self.bind_auth_chain(write=False)
                    return self.noop(receipt, "finalized")
                if self.row["phase"] != "reserved":
                    self.job = self.lineage.job_history(self.episode, self.row)
                    self.bind_auth_chain(write=mode in {"publish", "update"} and not self.job.events("FINALIZED"))
            if reserved_inspection:
                require(mode == "reconcile" and lock is not None and self.row["phase"] == "reserved" and
                        len(self.auth_chain) == 1 and self.row["genesis_auth"] ==
                        {"id": self.auth_id, "sha256": self.active_hash}, "reserved_authority_mismatch")
                self.job = self.lineage.activate(self.episode, self.row, local_bytes(self.root, PAYLOAD))
                return self.inspect_effects()
            if historical:
                require(mode == "reconcile" and self.job is not None and resolution_value is not None,
                        "resolution_requires_registered_job")
                return self.abandon(*resolution_value)
            self.bind_parent(historical=bool(self.row and self.row["phase"] == "complete"))
            with self.workspace(frozen=mode in {"publish", "update"}):
                if mode == "plan":
                    if self.row is None:
                        require([row[0] for row in self.plan_rows()] == self.binding["operation_plan"],
                                "plan_conflict", code=4)
                    return {"status": "planned" if self.expired_seconds() > 0 else "writes_blocked_expired",
                            **current_header(self.binding), "operations": self.binding["operation_plan"],
                            "privacy": self.binding["target_privacy_status"], "publish_at": self.binding["publish_at"],
                            "notify_subscribers": self.binding["notify_subscribers"], "mutations": 0}
                if mode == "reconcile":
                    require(self.job is not None, "no_state_to_reconcile")
                    return self.inspect_effects() if inspect_effects else self.reconcile_production(resolution_value)
                if self.job is None:
                    require(self.expired_seconds() > 0 and len(self.auth_chain) == 1,
                            "initial_write_requires_active_genesis")
                    require([entry[0] for entry in self.plan_rows()] == self.binding["operation_plan"],
                            "plan_conflict", code=4)
                    if kind in PUBLISH_MODES:
                        self.check_title()
                    genesis = {"id": self.auth_id, "sha256": self.active_hash}
                    if self.row is None:
                        self.episode, self.row = self.lineage.reserve(self.state_root, self.binding, genesis)
                    require(self.row["phase"] == "reserved" and self.row["genesis_auth"] == genesis,
                            "reserved_authority_mismatch")
                    self.job = self.lineage.activate(self.episode, self.row, local_bytes(self.frozen, PAYLOAD))
                    self.row = {**self.row, "phase": "ready"}
                try:
                    return self.publish_production()
                except Stop as exc:
                    if not (self.job.directory / RECEIPT).exists() and not (self.job.directory / RECEIPT).is_symlink():
                        state = ("RECONCILIATION_REQUIRED" if exc.code in {7, 10, 11} and exc.effect != "none" else
                                 "AWAITING_AUTH" if exc.reason in {"writes_blocked_expired", "operation_not_authorized"} else
                                 "WAIT_READBACK" if exc.code == 4 else "BLOCKED")
                        self.job.snapshot(self.binding, state, self.known_video())
                        atomic_write(self.job.directory / READBACK, canonical(self.readback(state, [exc.reason])))
                    raise

    def repair_terminal(self):
        for entry in (self.episode or {}).get("revisions", []):
            if entry["phase"] != "ready":
                continue
            job = self.lineage.job_history(self.episode, entry)
            if job.events("REVISION_ABANDONED"):
                closure = self.verify_closure(entry, job)
                job.snapshot(entry["candidate"], "ABANDONED")
                self.lineage.change(entry, "abandoned", closure=closure,
                                    media_hold=closure["keep_upload_hold"])
            elif job.events("FINALIZED") or (job.directory / RECEIPT).exists() or (job.directory / RECEIPT).is_symlink():
                receipt, _, checksum = self.lineage.final(job, entry["candidate"], allow_unfinalized=True)
                if not job.events("FINALIZED"):
                    job.append("FINALIZED", video_id=receipt["video_id"], receipt_sha256=checksum)
                job.snapshot(entry["candidate"], "COMPLETE", receipt["video_id"])
                self.lineage.change(entry, "complete", video_id=receipt["video_id"], receipt_sha256=checksum)

    def reconcile_production(self, resolution):
        if self.job.events("FINALIZED"):
            return {"status": "read_only", "video_id": self.known_video(), "mutations": 0}
        pending = [row for row in self.job.events("INTENT") if not any(self.job.record(row["op_key"], event)
                   for event in ("ACK", "RECONCILED", "ABANDONED")) and
                   row == self.job.record(row["op_key"], "INTENT")]
        if resolution is None:
            for intent in pending:
                error = self.job.record(intent["op_key"], "ERROR") or {}
                handle = error.get("safe_ids", {}).get("session_handle")
                if intent["operation"] != UPLOAD or not handle:
                    continue
                found = self.cli(["videos", "upload-status", handle])
                if found.get("state") == "complete":
                    descriptor = next(row for row in self.binding["operation_plan"] if row["operation"] == UPLOAD)
                    ack = self.validate_ack(UPLOAD, found, None, descriptor["target"])
                    self.verify_video(ack["video_id"], descriptor, True)
                    self.job.append("RECONCILED", operation=UPLOAD, op_key=intent["op_key"],
                                    attempt_id=intent["attempt_id"], **ack)
                    return {"status": "reconciled_upload", "video_id": ack["video_id"], "mutations": 0}
            return {"status": "reconciliation_required" if pending else "read_only",
                    "video_id": self.known_video(), "mutations": 0}
        value, checksum = resolution
        rid = value["resolution_id"]
        last = next((row for row in self.job.rows if row.get("resolution_id") == rid), None)
        if last:
            require(last["resolution_sha256"] == checksum, "resolution_digest_mismatch")
            return {"status": value["decision"], "mutations": 0}
        require(value["actor"] == "user" and value["episode_key"] == self.binding["episode_key"] and
                value["package_revision"] == self.binding["package_revision"] and
                value["target_channel_id"] == self.binding["target_channel_id"] and
                value["seal_sha256"] == self.binding["seal_sha256"] and value["expected_seq"] == len(self.job.rows) and
                value["expected_digest"] == self.job.tail and bool(value["observations"]),
                "resolution_binding_mismatch")
        intent = next((row for row in self.job.events("INTENT") if row["op_key"] == value["op_key"] and
                       row["attempt_id"] == value["attempt_id"]), None)
        require(intent is not None, "resolution_intent_mismatch")
        identity = {"operation": intent["operation"], "op_key": intent["op_key"], "attempt_id": intent["attempt_id"],
                    "resolution_id": rid, "resolution_sha256": checksum}
        decision = value["decision"]
        if decision == "verified_thumbnail_rendition":
            ack = self.job.record(intent["op_key"], "ACK")
            vid = self.known_video()
            require(intent["operation"] == THUMB and ack and ack["attempt_id"] == intent["attempt_id"] and
                    ack["video_id"] == vid and value["video_id"] == vid and
                    value["source_sha256"] == self.binding["thumbnail_sha256"],
                    "thumbnail_resolution_binding_mismatch")
            self.owned(vid)
            require(self.thumbnail_bytes(vid)[1] == value["download_sha256"], "thumbnail_rendition_changed", code=4)
            self.job.append("THUMBNAIL_RENDITION_ATTESTED", **identity, source_sha256=value["source_sha256"],
                            download_sha256=value["download_sha256"])
        elif decision == "resume_confirmed_suffix":
            require(intent in pending and intent["operation"] == UPLOAD, "wrong_resolution_operation")
            error = self.job.record(intent["op_key"], "ERROR") or {}
            handle, offset = value.get("session_handle"), value.get("confirmed_offset")
            require(handle and handle == error.get("safe_ids", {}).get("session_handle"), "wrong_session_handle")
            status = self.cli(["videos", "upload-status", handle])
            require(status.get("state") == "incomplete" and status.get("offset") == offset and type(offset) is int and
                    (status.get("notify_subscribers") is self.binding["notify_subscribers"] or
                     status.get("notify_subscribers") == "unknown" and not self.binding["effective_smoke"]),
                    "unverified_session_offset")
            self.job.append("RESUME_AUTHORIZED", **identity, session_handle=handle, offset=offset)
        elif decision == "claimed":
            require(intent in pending and intent["operation"] == UPLOAD and any(
                o.get("source") == "operator_first_hand_upload_record" and o.get("video_id") == value.get("video_id")
                for o in value["observations"]), "claim_requires_first_hand_identity")
            descriptor = next(row for row in self.binding["operation_plan"] if row["operation"] == UPLOAD)
            require(not intent["resumed"], "resume_claim_requires_bound_session")
            ack = self.validate_ack(UPLOAD, {"video_id": value["video_id"],
                "notify_subscribers": intent["notify_subscribers"]}, None, descriptor["target"])
            self.verify_video(ack["video_id"], descriptor, True)
            self.job.append("RECONCILED", **identity, **ack)
        else:
            raise Stop("invalid_resolution_decision")
        return {"status": decision, "mutations": 0}

    def inspect_observation(self, intent, ack):
        op, target = intent["operation"], intent.get("target", {})
        key = {UPLOAD: "video_id", UPDATE: "video_id", THUMB: "video_id", CAP_ADD: "caption_id",
               CAP_UPDATE: "caption_id", CAP_DELETE: "caption_id", PLAYLIST: "item_id"}[op]
        resource_id = ack.get(key)
        vid = ack.get("video_id") if op == UPLOAD else self.known_video()
        owner = self.owned(vid)
        observation = {"video_id": vid, "channel_id": self.binding["target_channel_id"]}
        if op == UPDATE:
            body = intent.get("request_body") or {}
            matched = []
            for part, old in intent["baseline"]["parts"].items():
                projected = writable_projection(owner, part)
                for field, value in body[part].items():
                    if field in projected and canonical(projected[field]) == canonical(value) and (
                            field not in old or canonical(old[field]) != canonical(value)):
                        matched.append([part, field])
            require(bool(matched), "update_effect_unproven", code=4)
            observation["matched_changes"] = matched
        elif op == THUMB:
            proof = self.thumbnail_proof(vid, owner, ack)
            require(proof["rendition_sha256"] != (intent.get("baseline") or {}).get("rendition_sha256"),
                    "thumbnail_effect_unproven", code=4)
            observation["rendition_sha256"] = proof["rendition_sha256"]
        elif op in {CAP_ADD, CAP_UPDATE, CAP_DELETE}:
            rows = self.caption_rows(vid)
            if op == CAP_DELETE:
                require(all(row["id"] != resource_id for row in rows), "caption_effect_unproven", code=4)
                observation["absent"] = True
            else:
                track = next(track for track in self.manifest["captions"] if target_key(track) == target_key(target))
                proof = super().read_caption(vid, track, resource_id)
                observation["cue_sha256"] = proof["cue_sha256"]
        elif op == PLAYLIST:
            self.playlist(target["playlist_id"])
            require(self.membership(vid, target["playlist_id"]) == [resource_id],
                    "playlist_effect_unproven", code=4)
            observation["playlist_id"] = target["playlist_id"]
        kind = {UPLOAD: "video", UPDATE: "video", THUMB: "thumbnail", CAP_ADD: "caption",
                CAP_UPDATE: "caption", CAP_DELETE: "caption", PLAYLIST: "playlist_item"}[op]
        return kind, {"id": resource_id, "video_id": vid}, observation

    def inspect_effects(self):
        require(not self.job.events("FINALIZED") and not self.job.events("REVISION_ABANDONED"),
                "revision_is_terminal")
        for intent in self.job.events("INTENT"):
            ack = self.matching_event(intent, {"ACK", "RECONCILED"})
            if ack is None:
                continue
            try:
                kind, ids, observation = self.inspect_observation(intent, ack)
            except Stop as exc:
                if exc.code in {3, 4, 5}:
                    continue
                raise
            proof = {"op_key": intent["op_key"], "attempt_id": intent["attempt_id"], "ack_seq": ack["seq"],
                     "kind": kind, "resource_ids": ids, "observation": observation}
            checksum = hashed(proof)
            if not any(row.get("proof_sha256") == checksum for row in self.job.events("EFFECT_OBSERVED")):
                self.job.append("EFFECT_OBSERVED", **proof, proof_sha256=checksum)
        disposition = self.disposition(self.job)
        return {"status": "effects_inspected", "mutations": 0, "attempts": disposition,
                "expected_seq": len(self.job.rows), "expected_digest": self.job.tail}

    def matching_event(self, intent, events, *, job=None, through=None):
        source = job or self.job
        return next((row for row in reversed(source.rows[:through]) if row["event"] in events and
                    row.get("op_key") == intent["op_key"] and row.get("attempt_id") == intent["attempt_id"] and
                    row["seq"] > intent["seq"]), None)

    def disposition(self, job, *, through=None):
        result = []
        for intent in (row for row in job.rows[:through] if row["event"] == "INTENT"):
            find = lambda events: self.matching_event(intent, events, job=job, through=through)
            ack = find({"ACK", "RECONCILED"})
            effect = find({"EFFECT_OBSERVED"})
            error = find({"ERROR"})
            if effect:
                require(ack and effect["ack_seq"] == ack["seq"] and effect["seq"] > ack["seq"] and
                        effect["proof_sha256"] == hashed({key: effect[key] for key in (
                            "op_key", "attempt_id", "ack_seq", "kind", "resource_ids", "observation")}),
                        "revision_effect_proof_invalid")
                ids = effect["resource_ids"]
                status = {"kind": effect["kind"], **ids, "effect": "positive", "proof_sha256": effect["proof_sha256"]}
            elif ack:
                verified = next((row for row in job.rows[:through] if row["event"] == "VERIFIED" and
                                 row.get("op_key") == intent["op_key"] and row.get("ack_seq") == ack["seq"] and
                                 row.get("intent_seq") == intent["seq"]), None)
                status = {"kind": self.effect_kind(intent["operation"]), "id": verified.get("provider_id") if verified else
                          (ack.get("caption_id") or ack.get("item_id") or ack.get("video_id")),
                          "video_id": ack.get("video_id") or (verified or {}).get("video_id") or job.rows[0][
                              "candidate"].get("target_video_id"), "effect": "positive" if verified else "unknown",
                          "proof_sha256": hashed(verified) if verified else None}
            else:
                status = {"kind": self.effect_kind(intent["operation"]), "id": None, "video_id":
                          (error or {}).get("safe_ids", {}).get("video_id"),
                          "effect": "none" if error and error["effect"] == "none" else "unknown", "proof_sha256": None}
            result.append({"op_key": intent["op_key"], "attempt_id": intent["attempt_id"], **status})
        return result

    @staticmethod
    def effect_kind(operation):
        return {UPLOAD: "video", UPDATE: "video", THUMB: "thumbnail", CAP_ADD: "caption",
                CAP_UPDATE: "caption", CAP_DELETE: "caption", PLAYLIST: "playlist_item"}[operation]

    def closure_fields(self, job, value, checksum, *, through):
        disposition = self.disposition(job, through=through)
        effects = {record["effect"] for record in disposition}
        decision = ("abandon_no_intent" if not effects else "abandoned_unknown_no_retry" if "unknown" in effects else
                    "abandon_partial_known_effect" if "positive" in effects else "abandon_proven_none")
        require(value["decision"] == decision, "revision_disposition_mismatch")
        candidate = job.rows[0]["candidate"]
        video_ids = sorted({row["video_id"] for row in disposition if VIDEO_ID.fullmatch(row["video_id"] or "")})
        inserts = {(e["op_key"], e["attempt_id"]) for e in job.rows[:through]
                   if e["event"] == "INTENT" and e["operation"] == UPLOAD}
        orphans = sorted({row["video_id"] for row in disposition if row["effect"] == "positive" and
                          (row["op_key"], row["attempt_id"]) in inserts})
        hold = candidate["mode"] != "in_place_update"
        if hold and decision in {"abandon_no_intent", "abandon_proven_none"}:
            hold = any(self.matching_event(intent, {"ERROR"}, job=job, through=through).get(
                "upload_init_dispatch", "unproven") != "not_sent" for intent in job.rows[:through]
                if intent["event"] == "INTENT" and intent["operation"] == UPLOAD)
        return {"resolution_id": value["resolution_id"], "resolution_sha256": checksum, "decision": decision,
                "retained_video_ids": video_ids, "retained_resources": disposition, "orphan_upload_ids": orphans,
                "cleanup_suggestions": [] if candidate["effective_smoke"] else [cleanup(candidate, v) for v in orphans],
                "keep_upload_hold": hold}

    def verify_closure(self, row, job=None):
        if row.get("closure", {}).get("origin") == "legacy_terminal_import":
            self.lineage.verify_legacy_closure(self.episode, row)
            return row["closure"]
        job = job or self.lineage.job_history(self.episode, row)
        events = job.events("REVISION_ABANDONED")
        require(len(events) == 1 and events[0] == job.rows[-1], "revision_terminal_event_missing")
        event = events[0]
        value, checksum = self.store.load("resolutions", event["resolution_id"])
        self.lineage.check_resolution(value, job, row["candidate"], tail=event["seq"] - 1)
        closure = self.closure_fields(job, value, checksum, through=event["seq"] - 1)
        require(all(event.get(key) == value for key, value in closure.items()), "revision_terminal_event_mismatch")
        closure.update(event_seq=event["seq"], event_sha256=hashed(event))
        if row["phase"] == "abandoned":
            require(row["closure"] == closure and row["media_hold"] is closure["keep_upload_hold"],
                    "revision_terminal_index_mismatch")
        return closure

    def abandon(self, value, checksum):
        require(value["scope"] == "revision" and self.row["phase"] == "ready" and
                not (self.job.directory / RECEIPT).exists() and not (self.job.directory / RECEIPT).is_symlink() and
                not self.job.events("FINALIZED"), "revision_cannot_be_abandoned")
        if self.job.events("REVISION_ABANDONED"):
            closure = self.verify_closure(self.row, self.job)
            require(closure["resolution_id"] == value["resolution_id"] and closure["resolution_sha256"] == checksum,
                    "revision_terminal_resolution_conflict")
        else:
            self.lineage.check_resolution(value, self.job, self.binding)
            closure = self.closure_fields(self.job, value, checksum, through=len(self.job.rows))
            event = self.job.append("REVISION_ABANDONED", **closure)
            closure.update(event_seq=event["seq"], event_sha256=hashed(event))
        self.job.snapshot(self.binding, "ABANDONED", self.known_video())
        self.lineage.change(self.row, "abandoned", closure=closure, media_hold=closure["keep_upload_hold"])
        return {"status": "revision_abandoned_no_retry", "mutations": 0, "closure": closure}
