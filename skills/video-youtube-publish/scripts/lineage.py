"""Versioned local episode registry backed by immutable job history."""

import contextlib
import re
from pathlib import Path

from auth_store import Stop, lock_file, require, safe_private, safe_read, utc
from journal import Journal
from package import PAYLOAD, atomic_write, canonical, clean_identifier, digest, json_data, sync_directory

SHA = re.compile(r"[a-f0-9]{64}")
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
RESOURCE = re.compile(r"[A-Za-z0-9_.:-]{1,160}")
HANDLE = re.compile(r"[a-f0-9]{32}")
RECEIPT = "receipt.json"
READBACK = "youtube-readback.json"


def hashed(value):
    return digest(canonical(value))


def episode_key(candidate):
    return digest(candidate["episode_key"].encode())


def media_key(candidate):
    return hashed([candidate["target_channel_id"], candidate["video_sha256"]])


def current_header(candidate):
    return {"schema_version": "3", "mode": candidate["mode"], "episode_key": candidate["episode_key"],
            "package_revision": candidate["package_revision"], "profile": candidate["channel_profile"],
            "channel_id": candidate["target_channel_id"], "parent": candidate["parent"],
            "target_video_id": candidate["target_video_id"], "plan_sha256": candidate["plan_sha256"]}


def cleanup(candidate, video_id):
    profile = candidate["channel_profile"]
    return {"profile": profile, "video_id": video_id,
            "command": f"ytpub videos delete {video_id} --profile {profile} --yes"}


class Lineage:
    def __init__(self, root, store, clock):
        self.root = root
        self.store = store
        self.clock = clock
        self.path = root / "episodes.json"

    def prepare(self):
        safe_private(self.root, create=True)
        safe_private(self.root / "locks", create=True)

    def lock(self, key, *, shared=False):
        require(isinstance(key, str) and SHA.fullmatch(key), "invalid_episode_key")
        return lock_file(self.root / "locks" / f"{key}.lock", shared=shared)

    def read(self):
        if not self.path.exists() and not self.path.is_symlink():
            return {"registry_version": 2, "episodes": {}}
        safe_private(self.root)
        value = json_data(safe_read(self.path))
        require(isinstance(value, dict), "invalid_episode_registry")
        if "registry_version" not in value:
            for key, row in value.items():
                require(SHA.fullmatch(key) and isinstance(row, dict) and
                        row.keys() == {"root", "candidate", "media_key"} and
                        episode_key(row["candidate"]) == key and media_key(row["candidate"]) == row["media_key"],
                        "legacy_registry_integrity_error")
            return value
        require(value.keys() == {"registry_version", "episodes"} and value["registry_version"] == 2 and
                isinstance(value["episodes"], dict), "invalid_episode_registry")
        for key, episode in value["episodes"].items():
            self.validate_episode(key, episode)
        return value

    @staticmethod
    def validate_episode(key, episode):
        rows = episode["revisions"]
        require(SHA.fullmatch(key) and isinstance(rows, list) and bool(rows) and
                Path(episode["root"]).is_absolute(), "invalid_episode_registry")
        revisions = [r["revision"] for r in rows]
        require(all(type(r) is int and r > 0 for r in revisions) and revisions == sorted(set(revisions)),
                "invalid_revision_lineage")
        head = None
        pending = 0
        for row in rows:
            candidate = row["candidate"]
            require(row["revision"] == candidate["package_revision"] and episode_key(candidate) == key and
                    candidate["target_channel_id"] == episode["target_channel_id"] and
                    candidate["channel_profile"] == episode["channel_profile"] and
                    row["media_key"] == media_key(candidate) and row["layout"] in {"flat", "revision"} and
                    row["phase"] in {"reserved", "ready", "complete", "superseded", "abandoned"} and
                    type(row["media_hold"]) is bool, "invalid_revision_lineage")
            if row["phase"] in {"reserved", "ready"}:
                pending += 1
                require(row["receipt_sha256"] is None, "unfinished_revision_has_receipt")
            if row["phase"] == "complete":
                require(head is None, "multiple_lineage_heads")
                head = row["revision"]
            if row["phase"] in {"complete", "superseded"}:
                require(VIDEO.fullmatch(row["video_id"] or "") and SHA.fullmatch(row["receipt_sha256"] or ""),
                        "invalid_successful_revision")
        require(head == episode["head_revision"] and pending <= 1, "invalid_lineage_head")
        require(head is None or head == max(row["revision"] for row in rows
                                           if row["phase"] in {"complete", "superseded"}),
                "invalid_lineage_head")

    @staticmethod
    def episode(root, candidate):
        return {"root": str(root), "channel_profile": candidate["channel_profile"],
                "target_channel_id": candidate["target_channel_id"], "head_revision": None, "revisions": []}

    @staticmethod
    def row(candidate, layout, *, genesis=None):
        mode = candidate["mode"]
        return {"revision": candidate["package_revision"], "layout": layout, "candidate": candidate,
                "media_key": media_key(candidate), "kind": "initial_publish" if mode == "private_smoke" else mode,
                "phase": "reserved", "parent": candidate.get("parent"), "video_id": None,
                "receipt_sha256": None, "media_hold": mode != "in_place_update", "genesis_auth": genesis}

    def directory(self, episode, row):
        candidate = row["candidate"]
        root = Path(episode["root"])
        safe_private(root)
        base = root / episode_key(candidate)
        if row["layout"] == "flat":
            return base
        safe_private(base)
        group = base / "revisions"
        if group.exists() or group.is_symlink():
            safe_private(group)
        return group / str(row["revision"])

    def job_history(self, episode, row):
        job = Journal(self.directory(episode, row))
        job.ensure_snapshot()
        require(job.rows and job.rows[0]["event"] == "GENESIS" and
                job.rows[0]["candidate"] == row["candidate"], "journal_genesis_mismatch")
        snapshot = job.directory / "state.json"
        if snapshot.exists() or snapshot.is_symlink():
            require(json_data(safe_read(snapshot))["candidate"] == row["candidate"], "snapshot_candidate_mismatch")
        require(digest(safe_read(job.directory / PAYLOAD)) == row["candidate"]["payload_sha256"],
                "frozen_payload_mismatch")
        history = [job.rows[0], *job.events("AUTH_SUCCESSOR")]
        chain = self.store.chain(history[-1]["authorization_id"], row["candidate"], self.clock(), historical=True)
        require([(a["authorization_id"], h) for a, h in chain] ==
                [(e["authorization_id"], e["authorization_sha256"]) for e in history],
                "journal_authorization_chain_mismatch")
        if row.get("genesis_auth") is not None:
            require(row["genesis_auth"] == {"id": history[0]["authorization_id"],
                                           "sha256": history[0]["authorization_sha256"]},
                    "registry_authorization_chain_mismatch")
        return job

    def final(self, job, candidate, *, allow_unfinalized=False):
        receipt_raw = safe_read(job.directory / RECEIPT)
        readback_raw = safe_read(job.directory / READBACK)
        receipt, readback = json_data(receipt_raw), json_data(readback_raw)
        version = "3" if candidate.get("authorization_version") == "3.0" else "1"
        vid, seq = receipt["video_id"], receipt["journal_seq"]
        require(canonical(receipt) == receipt_raw and canonical(readback) == readback_raw and
                receipt["schema_version"] == readback["schema_version"] == version and
                VIDEO.fullmatch(vid) and receipt["candidate"] == candidate and
                readback["video_id"] == vid and readback["overall"] == "complete" and
                readback["profile"] == candidate["channel_profile"] and
                readback["channel_id"] == candidate["target_channel_id"] and
                receipt["readback_sha256"] == digest(readback_raw) and type(seq) is int and
                1 <= seq <= len(job.rows) and receipt["journal_sha256"] == hashed(job.rows[seq - 1]),
                "receipt_readback_digest_mismatch")
        authority = [row for row in job.rows[:seq] if row["event"] in {"GENESIS", "AUTH_SUCCESSOR"}][-1]
        require((receipt["authorization_id"], receipt["authorization_sha256"]) ==
                (authority["authorization_id"], authority["authorization_sha256"]),
                "receipt_authorization_mismatch")
        if candidate["mode"] == "in_place_update":
            require(vid == candidate["target_video_id"], "receipt_target_mismatch")
        else:
            require(any(row.get("operation") == "upload_video" and row.get("video_id") == vid and
                        row["event"] in {"ACK", "RECONCILED"} for row in job.rows[:seq]), "receipt_video_ack_missing")
        if version == "3":
            header = current_header(candidate)
            require(receipt.keys() == header.keys() | {"candidate", "video_id", "authorization_id",
                    "authorization_sha256", "readback_sha256", "journal_seq", "journal_sha256",
                    "completed_at", "cleanup_suggestion"} and
                    readback.keys() == header.keys() | {"video_id", "overall", "state", "requested_privacy",
                    "observed_privacy", "requested_publish_at", "observed_publish_at", "processing_status",
                    "package_notify_subscribers", "notification_effect", "notify_request_evidence", "resources",
                    "partial_reasons", "evidence_as_of", "observed_at", "provenance"} and
                    all(receipt[key] == readback[key] == value for key, value in header.items()),
                    "receipt_schema_mismatch")
            expected_cleanup = cleanup(candidate, candidate["parent"]["video_id"]) if (
                candidate["mode"] == "revision_republish") else None
            require(receipt["cleanup_suggestion"] == expected_cleanup and readback["state"] == "COMPLETE" and
                    readback["partial_reasons"] == [] and readback["processing_status"] == "succeeded" and
                    readback["requested_privacy"] == readback["observed_privacy"] == candidate["target_privacy_status"] and
                    readback["requested_publish_at"] == readback["observed_publish_at"] == candidate["publish_at"] and
                    readback["package_notify_subscribers"] is candidate["notify_subscribers"] and
                    readback["notification_effect"] == (
                        "not_applicable" if candidate["mode"] == "in_place_update" else "insert_query") and
                    readback["evidence_as_of"] == "finalized" and
                    readback["provenance"] == "owner_bound_independent_get_list_download",
                    "receipt_semantics_mismatch")
            utc(receipt["completed_at"])
            utc(readback["observed_at"])
            self.verify_current_evidence(job, candidate, readback, seq)
        finalized = job.events("FINALIZED")
        receipt_hash = digest(receipt_raw)
        if finalized:
            require(len(finalized) == 1 and finalized[0]["seq"] == seq + 1 == len(job.rows) and
                    finalized[0]["receipt_sha256"] == receipt_hash and finalized[0]["video_id"] == vid,
                    "receipt_finalization_mismatch")
        else:
            require(allow_unfinalized and seq == len(job.rows), "receipt_finalization_missing")
        return receipt, readback, receipt_hash

    @staticmethod
    def verify_current_evidence(job, candidate, readback, through):
        evidence = readback["notify_request_evidence"]
        require(isinstance(evidence, dict) and evidence.keys() == {"value", "source", "ref_sha256"} and
                (type(evidence["value"]) is bool or evidence["value"] == "unknown") and
                isinstance(evidence["ref_sha256"], str) and SHA.fullmatch(evidence["ref_sha256"]),
                "receipt_notification_evidence_invalid")
        if candidate["mode"] == "in_place_update":
            require(evidence["source"] == "parent_receipt" and
                    evidence["ref_sha256"] == candidate["parent"]["receipt_sha256"],
                    "receipt_notification_evidence_invalid")
        else:
            inserted = next((row for row in job.rows[:through] if row.get("operation") == "upload_video" and
                             row["event"] in {"ACK", "RECONCILED"} and hashed(row) == evidence["ref_sha256"]), None)
            require(inserted is not None and inserted["notify_subscribers"] == evidence["value"] and
                    (evidence["value"] is candidate["notify_subscribers"] and
                     evidence["source"] in {"initial_intent", "bound_session"} or
                     not candidate["effective_smoke"] and evidence["value"] == "unknown" and
                     evidence["source"] == "legacy_unknown"), "receipt_notification_evidence_invalid")
        resources = readback["resources"]
        require(isinstance(resources, list) and all(isinstance(proof, dict) and SHA.fullmatch(proof["op_key"])
                                                    for proof in resources), "receipt_verification_invalid")
        keys = [proof["op_key"] for proof in resources]
        actions = {hashed([candidate["episode_key"], candidate["package_revision"], candidate["plan_sha256"],
                           item["operation"], item["target"], item["input_sha256"]]): item
                   for item in candidate["operation_plan"]}
        require(len(set(keys)) == len(keys) and actions.keys() <= set(keys) and
                sum(proof["operation"] in {"upload_video", "update_video"} and
                    proof["provider_id"] == readback["video_id"] for proof in resources) == 1,
                "receipt_verification_missing")
        for proof in resources:
            verified = proof["verified_seq"]
            require(type(verified) is int and 1 <= verified <= through, "receipt_verification_missing")
            event = job.rows[verified - 1]
            require(event["event"] == "VERIFIED" and all(event.get(key) == value
                    for key, value in proof.items() if key != "verified_seq"), "receipt_verification_mismatch")
            created = proof["ack_seq"]
            dispatched = proof["intent_seq"]
            if created is None:
                require(dispatched is None and proof["evidence_origin"] == "satisfied_preexisting" and
                        (proof["op_key"] not in actions or proof["operation"] == "add_playlist" and
                         candidate["mode"] != "in_place_update"), "receipt_verification_missing")
                continue
            require(type(created) is int and type(dispatched) is int and 1 <= dispatched < created < verified,
                    "receipt_verification_missing")
            intent, ack = job.rows[dispatched - 1], job.rows[created - 1]
            descriptor = actions.get(proof["op_key"])
            require(descriptor and intent["event"] == "INTENT" and ack["event"] in {"ACK", "RECONCILED"} and
                    intent["op_key"] == ack["op_key"] == proof["op_key"] and
                    intent["attempt_id"] == ack["attempt_id"] and
                    intent["operation"] == ack["operation"] == proof["operation"] == descriptor["operation"] and
                    intent["input_sha256"] == descriptor["input_sha256"],
                    "receipt_verification_mismatch")

    def history(self, episode, row):
        require(row["phase"] in {"complete", "superseded"}, "revision_is_not_a_published_parent")
        receipt, readback, checksum = self.final(self.job_history(episode, row), row["candidate"])
        require(row["receipt_sha256"] == checksum and row["video_id"] == receipt["video_id"],
                "registry_receipt_mismatch")
        return receipt, readback

    @staticmethod
    def check_resolution(value, job, candidate, *, tail=None):
        seq = len(job.rows) if tail is None else tail
        intents = [{"op_key": e["op_key"], "attempt_id": e["attempt_id"]} for e in job.rows[:seq]
                   if e["event"] == "INTENT"]
        require(value["actor"] == "user" and value["episode_key"] == candidate["episode_key"] and
                value["package_revision"] == candidate["package_revision"] and
                value["target_channel_id"] == candidate["target_channel_id"] and
                value["seal_sha256"] == candidate["seal_sha256"] and
                value["genesis_authorization_sha256"] == job.rows[0]["authorization_sha256"] and
                value["expected_seq"] == seq and value["expected_digest"] == hashed(job.rows[seq - 1]) and
                value["attempts"] == intents, "resolution_binding_mismatch")
        require(isinstance(value.get("observations"), list) and bool(value["observations"]) and
                all(isinstance(observation, dict) and clean_identifier(observation.get("source")) and
                    isinstance(observation.get("evidence_sha256"), str) and
                    SHA.fullmatch(observation["evidence_sha256"]) for observation in value["observations"]),
                "resolution_observation_required")

    def upgrade(self, resolution_ids=()):
        original = self.read()
        if "registry_version" in original:
            if resolution_ids:
                closures = {r["closure"]["resolution_id"]: (e, r) for e in original["episodes"].values()
                            for r in e["revisions"] if r.get("closure", {}).get("origin") == "legacy_terminal_import"}
                require(len(set(resolution_ids)) == len(resolution_ids) and set(resolution_ids) == set(closures),
                        "legacy_resolution_conflict")
                for rid in resolution_ids:
                    ep, row = closures[rid]
                    self.verify_legacy_closure(ep, row)
            return
        original_bytes = safe_read(self.path)
        require(json_data(original_bytes) == original, "legacy_registry_changed")
        resolutions = {}
        for rid in resolution_ids:
            value, checksum = self.store.load("resolutions", rid)
            require(value.get("scope") == "legacy_revision" and value.get("decision") == "import_abandoned_no_retry" and
                    value.get("resolution_id") == rid, "invalid_legacy_resolution")
            key = episode_key(value)
            require(key in original and key not in resolutions, "legacy_resolution_conflict")
            resolutions[key] = value, checksum
        with contextlib.ExitStack() as leases:
            for key in sorted(original):
                leases.enter_context(self.lock(key))
            converted = {}
            inflight = []
            for key, legacy in original.items():
                ep = self.episode(Path(legacy["root"]), legacy["candidate"])
                row = self.row(legacy["candidate"], "flat")
                ep["revisions"].append(row)
                converted[key] = ep
                job = self.job_history(ep, row)
                if job.events("FINALIZED"):
                    require(key not in resolutions, "legacy_resolution_conflict")
                    receipt, _, checksum = self.final(job, row["candidate"])
                    row.update(phase="complete", video_id=receipt["video_id"], receipt_sha256=checksum)
                    ep["head_revision"] = row["revision"]
                elif key in resolutions:
                    require(not (job.directory / RECEIPT).exists() and not (job.directory / RECEIPT).is_symlink(),
                            "legacy_receipt_requires_original_finalizer")
                    value, checksum = resolutions[key]
                    self.check_resolution(value, job, row["candidate"])
                    require(value["legacy_row_sha256"] == hashed(legacy) and
                            value["genesis_entry_sha256"] == hashed(job.rows[0]) and
                            value["genesis_authorization_id"] == job.rows[0]["authorization_id"],
                            "legacy_resolution_origin_mismatch")
                    row.update(phase="abandoned", closure=self.legacy_closure(job, legacy, value, checksum))
                else:
                    inflight.append(key)
            if inflight:
                raise Stop("legacy_inflight_drain_required", detail={"legacy_keys": sorted(inflight), "mutations": 0})
            with lock_file(self.root / "index.lock"):
                require(safe_read(self.path) == original_bytes, "legacy_registry_changed")
                atomic_write(self.path, canonical({"registry_version": 2, "episodes": converted}))

    @staticmethod
    def legacy_closure(job, legacy, value, checksum):
        identifiers = []
        for event in job.rows:
            if event["event"] not in {"ACK", "RECONCILED", "ERROR"}:
                continue
            source = event.get("safe_ids", {}) if event["event"] == "ERROR" else event
            for field, pattern in (("video_id", VIDEO), ("caption_id", RESOURCE),
                                   ("item_id", RESOURCE), ("session_handle", HANDLE)):
                identifier = source.get(field)
                if isinstance(identifier, str) and pattern.fullmatch(identifier):
                    identifiers.append({"field": field, "id": identifier, "event_seq": event["seq"],
                                        "source": event["event"], "evidence_sha256": hashed(event)})
        return {"origin": "legacy_terminal_import", "resolution_id": value["resolution_id"],
                "resolution_sha256": checksum, "legacy_row_sha256": hashed(legacy),
                "genesis_entry_sha256": hashed(job.rows[0]), "legacy_seq": len(job.rows),
                "legacy_tail_sha256": job.tail, "decision": value["decision"],
                "retained_video_ids": sorted({item["id"] for item in identifiers if item["field"] == "video_id"}),
                "retained_resources": identifiers, "orphan_upload_ids": [], "cleanup_suggestions": []}

    def verify_legacy_closure(self, ep, row):
        job = self.job_history(ep, row)
        closure = row["closure"]
        value, checksum = self.store.load("resolutions", closure["resolution_id"])
        self.check_resolution(value, job, row["candidate"])
        original = {"root": ep["root"], "candidate": row["candidate"], "media_key": row["media_key"]}
        require(value["scope"] == "legacy_revision" and value["decision"] == "import_abandoned_no_retry" and
                value["legacy_row_sha256"] == hashed(original) and value["genesis_entry_sha256"] ==
                hashed(job.rows[0]) and value["genesis_authorization_id"] == job.rows[0]["authorization_id"] and
                row["phase"] == "abandoned" and row["media_hold"] is True and
                closure == self.legacy_closure(job, original, value, checksum), "legacy_terminal_import_mismatch")

    def update(self, apply):
        with lock_file(self.root / "index.lock"):
            database = self.read()
            require(database.get("registry_version") == 2, "legacy_inflight_drain_required")
            result = apply(database["episodes"])
            atomic_write(self.path, canonical(database))
            return result

    def activate(self, ep, row, payload):
        directory = self.directory(ep, row)
        directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        safe_private(directory.parent)
        job = Journal(directory, create=True)
        sync_directory(directory.parent)
        allowed = {"state.json", "journal.jsonl", PAYLOAD}
        require(all(x.name in allowed for x in directory.iterdir()), "foreign_reserved_job_files")
        source = directory / PAYLOAD
        require(digest(payload) == row["candidate"]["payload_sha256"], "frozen_payload_mismatch")
        if source.exists() or source.is_symlink():
            require(safe_read(source) == payload, "frozen_payload_mismatch")
        else:
            require(not job.rows, "frozen_payload_missing")
            atomic_write(source, payload, exclusive=True)
        auth = row["genesis_auth"]
        if not job.rows:
            job.append("GENESIS", candidate=row["candidate"], authorization_id=auth["id"],
                       authorization_sha256=auth["sha256"])
        require(len(job.rows) == 1 and job.rows[0]["event"] == "GENESIS" and
                job.rows[0]["candidate"] == row["candidate"] and
                job.rows[0]["authorization_id"] == auth["id"] and job.rows[0]["authorization_sha256"] == auth["sha256"],
                "journal_genesis_mismatch")
        job.snapshot(row["candidate"], "READY", row["candidate"].get("target_video_id"))
        self.change(row, "ready")
        return job

    def change(self, old, phase, **changes):
        key = episode_key(old["candidate"])
        def apply(episodes):
            ep = episodes[key]
            rows = ep["revisions"]
            index = next(i for i, row in enumerate(rows) if row["revision"] == old["revision"])
            desired = {**old, "phase": phase, **changes}
            if rows[index] == desired:
                return
            require(rows[index] == old, "revision_index_compare_failed")
            if phase == "complete":
                if old["kind"] != "in_place_update":
                    require(not any(desired["video_id"] == row.get("video_id") or desired["video_id"] in
                                    row.get("closure", {}).get("retained_video_ids", [])
                                    for episode in episodes.values() for row in episode["revisions"]
                                    if row["candidate"]["target_channel_id"] == ep["target_channel_id"]),
                            "republish_reused_video_id", code=11)
                head = ep["head_revision"]
                require(head == (old["parent"]["revision"] if old["parent"] else None), "lineage_head_changed")
                if head is not None:
                    for row in rows:
                        if row["revision"] == head:
                            row["phase"] = "superseded"
                ep["head_revision"] = old["revision"]
            rows[index] = desired
        self.update(apply)

    def reserve(self, root, candidate, genesis):
        key = episode_key(candidate)
        def apply(episodes):
            ep = episodes.setdefault(key, self.episode(root, candidate))
            require(ep["root"] == str(root) and ep["channel_profile"] == candidate["channel_profile"] and
                    ep["target_channel_id"] == candidate["target_channel_id"], "episode_registry_binding_conflict")
            rows = ep["revisions"]
            require(not rows or candidate["package_revision"] > rows[-1]["revision"], "revision_not_above_high_water")
            require(not any(row["phase"] in {"reserved", "ready"} for row in rows), "revision_already_in_progress")
            parent = candidate.get("parent")
            require(ep["head_revision"] == (parent["revision"] if parent else None), "lineage_head_changed")
            if parent:
                head = next(row for row in rows if row["revision"] == ep["head_revision"])
                require(head["receipt_sha256"] == parent["receipt_sha256"] and head["video_id"] == parent["video_id"],
                        "lineage_parent_changed")
            row = self.row(candidate, "revision" if rows else "flat", genesis=genesis)
            if row["media_hold"]:
                require(not any(old["media_hold"] and old["media_key"] == row["media_key"]
                                for episode in episodes.values() for old in episode["revisions"]),
                        "same_media_use_mode_update")
            require(not self.directory(ep, row).exists() and not self.directory(ep, row).is_symlink(),
                    "unregistered_state_exists")
            rows.append(row)
            return ep, row
        return self.update(apply)
