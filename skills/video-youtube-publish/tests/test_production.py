import copy
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

from test_publish import CHANNEL, CLI_HASH, PLAYLIST, candidate, env

from auth_store import OperatorStore, Stop, timestamp, validate_auth
from lineage import Lineage, hashed
from make_smoke import fixture
from package import MANIFEST, SEAL, assemble, bundle_hash, canonical, create_seal, digest, json_data, render
from production import Production

PROFILE = "production"
FAKE = Path(__file__).with_name("fake_production_cli.py")


class LocalProvider:
    def __init__(self, root, *, protected=False):
        self.root = root
        root.mkdir(mode=0o700)
        self.state = root / "state.json"
        self.state.write_bytes(canonical({"videos": {}, "channel": CHANNEL, "profile": PROFILE,
                                          "protected": protected}))
        self.log = root / "requests.jsonl"

    def change(self, **values):
        self.state.write_bytes(canonical({**json_data(self.state.read_bytes()), **values}))

    def __call__(self, args, *, fds=(), lock=None, seconds=600, guard=None):
        if guard:
            guard()
        proc = subprocess.run([sys.executable, "-I", "-B", str(FAKE), str(self.root), *args],
                              capture_output=True, timeout=min(12, seconds),
                              pass_fds=(*fds, lock) if lock is not None else fds)
        if proc.returncode:
            if not proc.stderr.startswith(b"{"):
                raise AssertionError(proc.stderr.decode())
            data = json_data(proc.stderr)
            raise Stop(data["error_code"], code=proc.returncode, detail=data["safe_ids"], effect=data["effect"])
        return json_data(proc.stdout)["data"]

    def writes(self):
        return [r for r in map(json.loads, self.log.read_text().splitlines()) if r["mode"] == "write"]


@pytest.fixture(scope="module")
def materials(tmp_path_factory):
    root = tmp_path_factory.mktemp("production-materials").resolve()
    seed = root / "seed"
    request = fixture(seed, PROFILE, CHANNEL, episode_key="episode-1")
    (seed / "track-en.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nTest caption.\n\n"
                                       "2\n00:00:05,000 --> 00:00:07,000\nMore evidence.\n")
    request["captions"].append({"language": "en", "name": "English", "isDraft": False, "file": "track-en.srt"})
    return seed, request


@pytest.fixture
def production(tmp_path, materials):
    root = tmp_path.resolve()
    previous = os.umask(0o077)
    config = root / "profiles.json"
    config.write_bytes(canonical({"profiles": {PROFILE: CHANNEL, "smoke-test": "UC" + "B" * 22}}))
    provider = LocalProvider(root / "provider")
    store, registry, state = OperatorStore(root / "operator"), root / "registry", root / "state"
    bundle = bundle_hash()
    clock = datetime.now(timezone.utc)

    def candidate(number, *, reedit=False, edit=None):
        folder = root / f"revision-{number}"
        folder.mkdir(mode=0o700)
        pack = folder / "package"
        shutil.copytree(materials[0], pack)
        if reedit:
            changed = folder / "revision.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(pack / "delivery.mp4"), "-c", "copy",
                            "-metadata", f"comment=revision-{number}", str(changed)], check=True)
            changed.replace(pack / "delivery.mp4")
        metadata = copy.deepcopy(materials[1])
        metadata["package_revision"] = number
        if edit:
            edit(pack, metadata)
        assemble(pack, metadata, PROFILE)
        assert create_seal(pack, PROFILE, config=config)["contract_passed"]
        preview = folder / "video-release-preview.html"
        assert render(pack, PROFILE, preview, config=config)["human_preview_ready"]
        return pack, preview

    def controller(package, authorization_id=None):
        return Production(*package, PROFILE, provider, store, registry, state, authorization_id,
                          config=config, clock=lambda: clock, hash_cli=lambda: CLI_HASH, hash_contract=lambda: bundle)

    def approve(package, id, mode="publish", **opts):
        ctl = controller(package)
        binding, display = ctl.proposal(mode, **opts)
        grant = {**binding, "authorization_id": id, "source_ref_kind": "operator_terminal", "source_ref": id,
                 "original_user_quote": "Synthetic release authorization.", "actor": "user", "revoked": False,
                 "authorized_at": timestamp(clock - timedelta(minutes=1)), "expires_at": timestamp(clock+timedelta(hours=1)),
                 "allowed_operations": sorted({row["operation"] for row in binding["operation_plan"]} | {"readback"}),
                 "supersedes": None}
        validate_auth(grant)
        store.store("authorizations", id, grant)
        return ctl, display

    try:
        yield candidate, controller, approve, provider, store, registry, state
    finally:
        os.umask(previous)


def test_production_update_and_revision_republish(production):
    candidate, controller, approve, provider, _, registry, state = production
    original = candidate(1, edit=lambda _, request: request.update(notifySubscribers=True))
    _, plan = approve(original, "initial")
    assert plan[0]["yes"] and plan[0]["request"]["notify_subscribers"] is True
    assert controller(original, "initial").execute("plan")["mutations"] == 0
    initial = controller(original, "initial").execute("publish")
    first_vid = initial["video_id"]
    assert initial["status"] == "published"
    first_receipt = state / digest(b"episode-1") / "receipt.json"
    original_receipt = first_receipt.read_bytes()

    def edited(pack, request):
        request["status"]["privacyStatus"] = "unlisted"
        request["snippet"]["title"] = "Updated video for production"
        request["notifySubscribers"] = False
        request["captions"] = request["captions"][:1]
        request["playlist_ids"] = [PLAYLIST]
        (pack / "track-en.srt").unlink()
        track = pack / "track.srt"
        track.write_text(track.read_text().replace("这是私有测试。", "这是更新后的内容。"))
        Image.new("RGB", (1280, 720), "#38556a").save(pack / "thumbnail.png")

    update = candidate(2, edit=edited)
    with pytest.raises(Stop, match="same_media_use_mode_update"):
        approve(update, "wrong-mode", supersedes_revision=1)
    with pytest.raises(Stop, match="update_target_binding_mismatch"):
        approve(update, "wrong-id", "update", video_id="V9999999999")
    _, operations = approve(update, "edit", "update", video_id=first_vid)
    assert [o["operation"] for o in operations] == [
        "update_video", "set_thumbnail", "update_captions", "delete_captions", "add_playlist",
    ]
    assert operations[0]["yes"] and operations[3]["yes"]
    write_count = len(provider.writes())
    result = controller(update, "edit").execute("update", video_id=first_vid)
    assert result["status"] == "updated" and result["video_id"] == first_vid
    update_writes = provider.writes()[write_count:]
    assert all(entry["command"] != "videos/upload" for entry in update_writes)
    assert update_writes[0]["body"]["status"]["containsSyntheticMedia"] is False
    assert controller(update, "edit").execute("update")["status"] == "already_updated_noop"
    assert len(provider.writes()) == write_count + 5

    replacement = candidate(3, reedit=True, edit=edited)
    with pytest.raises(Stop, match="video_changed_use_revision_republish"):
        approve(replacement, "changed-mp4", "update")
    with pytest.raises(Stop, match="explicit_superseded_revision_required"):
        approve(replacement, "missing-parent")
    approve(replacement, "republish", supersedes_revision=2)
    published = controller(replacement, "republish").execute("publish")
    assert published["status"] == "republished" and published["video_id"] != first_vid
    assert published["cleanup_suggestion"]["video_id"] == first_vid
    assert not any(row["command"] == "videos/delete" for row in provider.writes())
    assert first_vid in json_data(provider.state.read_bytes())["videos"]
    assert first_receipt.read_bytes() == original_receipt
    history = json_data((registry / "episodes.json").read_bytes())["episodes"][digest(b"episode-1")]
    assert [entry["phase"] for entry in history["revisions"]] == ["superseded", "superseded", "complete"]
    assert controller(original, "initial").execute("publish")["evidence_as_of"] == "finalized"
    count = len(provider.writes())
    assert controller(replacement, "republish").execute("publish")["status"] == "already_published_noop"
    assert len(provider.writes()) == count
    third_upload = candidate(4, reedit=True, edit=edited)
    approve(third_upload, "republish-again", supersedes_revision=3)
    assert controller(third_upload, "republish-again").execute("publish")["video_id"] == "V0000000003"
    assert len(json_data(provider.state.read_bytes())["videos"]) == 3


def test_protected_alias_is_strict(production):
    candidate, _, approve, provider, *_ = production
    provider.change(protected=True)
    package = candidate(1, edit=lambda _, request: request.update(notifySubscribers=True))
    with pytest.raises(Stop, match="private_smoke_policy"):
        approve(package, "unsafe-alias")
    assert not provider.writes() if provider.log.exists() else True


def test_abandon_revision_releases_slot_and_preserves_orphan(production):
    candidate, controller, approve, provider, store, registry, _ = production
    original = candidate(1)
    _, _ = approve(original, "partial")
    provider.change(failure="thumbnail_rejected")
    with pytest.raises(Stop, match="provider_rejected"):
        controller(original, "partial").execute("publish")
    ctl = controller(original, "partial")
    observation = ctl.execute("reconcile", inspect_effects=True)
    assert [row["effect"] for row in observation["attempts"]] == ["positive", "none"]
    key = digest(b"episode-1")
    journal = ctl.job
    candidate_binding = journal.rows[0]["candidate"]
    resolution = {"scope": "revision", "decision": "abandon_partial_known_effect",
                  "actor": "user", "resolution_id": "close-bound",
                  "episode_key": candidate_binding["episode_key"], "package_revision": 1,
                  "target_channel_id": CHANNEL, "seal_sha256": candidate_binding["seal_sha256"],
                  "genesis_authorization_sha256": journal.rows[0]["authorization_sha256"],
                  "expected_seq": len(journal.rows), "expected_digest": journal.tail,
                  "attempts": [{k: row[k] for k in ("op_key", "attempt_id")} for row in journal.events("INTENT")],
                  "observations": [{"source": "offline-owner-get", "evidence_sha256": "b" * 64}]}
    store.store("resolutions", "close-bound", resolution)
    closed = controller(original, "partial").execute("reconcile", resolution="close-bound")
    assert closed["closure"]["orphan_upload_ids"] == ["V0000000001"]
    registry_row = json_data((registry / "episodes.json").read_bytes())["episodes"][key]
    assert registry_row["head_revision"] is None and registry_row["revisions"][0]["media_hold"] is True
    assert controller(original, "partial").execute("publish")["status"] == "revision_abandoned_no_retry"
    replacement = candidate(2, reedit=True)
    provider.change(failure=None)
    approve(replacement, "fresh")
    assert controller(replacement, "fresh").execute("publish")["video_id"] == "V0000000002"


def test_legacy_terminal_import_keeps_v1_bytes(env):
    env.approval()
    env.client.failure("lost_final_missing")
    with pytest.raises(Stop):
        env.run("publish")
    lineage = Lineage(env.registry, env.store, lambda: env.clock.now)
    book = lineage.read()
    key = digest(env.manifest["episode_key"].encode())
    row = book["episodes"][key]["revisions"][0]
    legacy = {"root": str(env.state), "candidate": row["candidate"], "media_key": row["media_key"]}
    lineage.path.write_bytes(canonical({key: legacy}))
    before = lineage.path.read_bytes()
    job = lineage.job_history(book["episodes"][key], row)
    stable = {p.name: p.read_bytes() for p in job.directory.iterdir()}
    with pytest.raises(Stop, match="legacy_inflight_drain_required"):
        lineage.upgrade()
    assert lineage.path.read_bytes() == before
    genesis = job.rows[0]
    resolution = {"scope": "legacy_revision", "decision": "import_abandoned_no_retry", "actor": "user",
                  "resolution_id": "legacy-fixture", "episode_key": env.manifest["episode_key"],
                  "target_channel_id": CHANNEL, "package_revision": row["revision"],
                  "seal_sha256": row["candidate"]["seal_sha256"],
                  "genesis_authorization_sha256": genesis["authorization_sha256"],
                  "genesis_authorization_id": genesis["authorization_id"], "legacy_row_sha256": hashed(legacy),
                  "genesis_entry_sha256": hashed(genesis), "expected_seq": len(job.rows), "expected_digest": job.tail,
                  "observations": [{"source": "synthetic-legacy-ledger", "evidence_sha256": "f" * 64}],
                  "attempts": [{k: item[k] for k in ("op_key", "attempt_id")} for item in job.events("INTENT")]}
    env.store.store("resolutions", "legacy-fixture", resolution)
    lineage.upgrade(["legacy-fixture"])
    updated = lineage.read()["episodes"][key]
    assert updated["head_revision"] is None
    assert (updated["revisions"][0]["phase"], updated["revisions"][0]["media_hold"]) == ("abandoned", True)
    lineage.upgrade(["legacy-fixture"])
    assert {p.name: p.read_bytes() for p in job.directory.iterdir()} == stable


def test_update_ack_recovers_without_replaying_and_cancels_schedule(production):
    candidate, controller, approve, provider, _, _, state = production
    schedule = timestamp(datetime.now(timezone.utc) + timedelta(days=90))
    original = candidate(1, edit=lambda _, request: request["status"].update(publishAt=schedule))
    _, approval = approve(original, "scheduled")
    assert approval[0]["yes"]
    first = controller(original, "scheduled").execute("publish")
    vid = first["video_id"]
    assert provider.writes()[0]["body"]["status"]["publishAt"] == schedule

    def changed(pack, request):
        request["status"]["privacyStatus"] = "public"
        path = pack / "track-en.srt"
        path.write_text(path.read_text().replace("Test caption.", "Updated caption."))
    revision = candidate(2, edit=changed)
    _, approval = approve(revision, "update", "update")
    assert approval[0]["request"]["clear_publish_at"] is True and approval[0]["yes"]
    provider.change(failure="caption_readback_unavailable")
    with pytest.raises(Stop, match="caption_readback_unavailable"):
        controller(revision, "update").execute("update")
    written = len(provider.writes())
    ledger = state / digest(b"episode-1") / "revisions" / "2" / "journal.jsonl"
    events = [json.loads(row) for row in ledger.read_text().splitlines()]
    assert [(row["event"], row["operation"]) for row in events if "operation" in row] == [
        ("INTENT", "update_video"), ("ACK", "update_video"), ("VERIFIED", "update_video"),
        ("INTENT", "update_captions"), ("ACK", "update_captions"),
    ]
    provider.change(failure=None)
    result = controller(revision, "update").execute("update")
    assert result["status"] == "updated" and result["video_id"] == vid and result["mutations"] == 0
    assert len(provider.writes()) == written
    assert controller(revision, "update").execute("update")["mutations"] == 0
    assert [w["command"] for w in provider.writes()].count("videos/upload") == 1
    status = json_data(provider.state.read_bytes())["videos"][vid]["metadata"]["status"]
    assert status["privacyStatus"] == "public" and "publishAt" not in status


def test_approval_displays_bound_production_fields(production, monkeypatch, capsys):
    from types import SimpleNamespace
    import operator as standard_operator
    import importlib.util

    candidate, controller, _, provider, store, registry, state = production
    package = candidate(1, edit=lambda _, m: (
        m["status"].update(privacyStatus="public"), m.update(notifySubscribers=True)))
    entry = Path(__file__).resolve().parents[1] / "scripts" / "operator.py"
    spec = importlib.util.spec_from_file_location("ytpub_test_operator", entry)
    module = importlib.util.module_from_spec(spec)
    assert module is not standard_operator
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "Production", lambda root, preview, *_: controller((root, preview)))
    args = SimpleNamespace(package=package[0], preview=package[1], profile=PROFILE, cache_backend=None,
                           mode="publish", supersedes=None, supersedes_revision=None, video_id=None,
                           allow=None, hours=1)
    monkeypatch.setattr(module, "prompt", lambda _: "incorrect")
    with pytest.raises(Stop, match="operator_confirmation_missing"):
        module.approve(args, store, registry, state)
    assert not store.root.exists()
    capsys.readouterr()
    monkeypatch.setattr(module, "prompt", lambda text: text.split("Type exactly: ", 1)[1].splitlines()[0])
    assert module.approve(args, store, registry, state) == 0
    display, reference = (json.loads(line) for line in capsys.readouterr().out.splitlines())
    auth, checksum = store.load("authorizations", reference["authorization_id"])
    assert display["target_privacy_status"] == auth["target_privacy_status"] == "public"
    assert display["notify_subscribers"] is auth["notify_subscribers"] is True
    assert display["operation_plan"] == auth["operation_plan"] and auth["operation_plan"][0]["yes"]
    assert checksum == reference["authorization_sha256"]
    assert not provider.log.exists() or not provider.writes()


def test_reserved_revision_local_recovery_can_abandon_without_dispatch(production, monkeypatch):
    candidate, controller, approve, provider, store, _, _ = production
    package = candidate(1)
    approve(package, "reserved")

    def interrupted(*_):
        raise OSError("synthetic interruption after reservation")

    with monkeypatch.context() as injected:
        injected.setattr(Lineage, "activate", interrupted)
        with pytest.raises(OSError, match="synthetic interruption"):
            controller(package, "reserved").execute("publish")
    assert not provider.writes()
    ctl = controller(package, "reserved")
    inspected = ctl.execute("reconcile", inspect_effects=True)
    assert inspected["attempts"] == []
    approval = ctl.job.rows[0]
    record = {"scope": "revision", "decision": "abandon_no_intent", "actor": "user",
              "resolution_id": "release-unstarted", "episode_key": "episode-1", "package_revision": 1,
              "target_channel_id": CHANNEL, "seal_sha256": approval["candidate"]["seal_sha256"],
              "genesis_authorization_sha256": approval["authorization_sha256"],
              "expected_seq": inspected["expected_seq"], "expected_digest": inspected["expected_digest"],
              "attempts": [], "observations": [{"source": "offline-before-dispatch", "evidence_sha256": "b" * 64}]}
    store.store("resolutions", "release-unstarted", record)
    result = controller(package, "reserved").execute("reconcile", resolution="release-unstarted")
    assert result["closure"]["keep_upload_hold"] is False
    assert not provider.writes()
    reusable = candidate(2)
    approve(reusable, "reuse-after-no-dispatch")
    assert controller(reusable, "reuse-after-no-dispatch").execute("publish")["video_id"] == "V0000000001"
