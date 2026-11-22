import copy
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish import Controller, local_authority_binding, matching_video
from auth_store import OPS, OperatorStore, Stop, lock_file, timestamp, validate_auth
from journal import Journal
from make_smoke import fixture
from package import MANIFEST, SEAL, assemble, canonical, create_seal, digest, json_data, render

CHANNEL = "UC" + "A" * 22
VIDEO = "aBCde123456"
CLI_HASH = "f" * 64
IDENTITY = {"channel_id": CHANNEL, "oauth_binding_sha256": "1" * 64, "identity_verified": True}
PLAYLIST = "PLfixture123456"
FAKE = Path(__file__).with_name("fake_cli.py")


class FakeClient:
    def __init__(self, root, title):
        self.root = root
        self.root.mkdir(mode=0o700)
        self.state = root / "provider.json"
        self.state.write_bytes(canonical({"title": title}))
        self.log = root / "requests.jsonl"

    def __call__(self, args, *, fds=(), lock=None, seconds=600, guard=None):
        if guard:
            guard()
        result = subprocess.run([sys.executable, "-I", "-B", str(FAKE), str(self.root), *args],
                                pass_fds=(*fds, lock) if lock is not None else fds,
                                capture_output=True, timeout=min(10, seconds))
        if result.returncode:
            value = json_data(result.stderr)
            raise Stop(value["error_code"], code=result.returncode, detail=value["safe_ids"])
        return json_data(result.stdout)["data"]

    def failure(self, value):
        self.state.write_bytes(canonical({**json_data(self.state.read_bytes()), "failure": value}))

    def requests(self, mode=None):
        rows = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return [row["operation"] for row in rows if mode is None or row["mode"] == mode]


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    root = tmp_path_factory.mktemp("publish-candidate").resolve()
    package = root / "package"
    config = root / "profiles.json"
    config.write_bytes(canonical({"profiles": {"smoke-test": CHANNEL}}))
    request = fixture(package, "smoke-test", CHANNEL)
    english = "1\n00:00:01,000 --> 00:00:03,000\nSmoke test.\n\n2\n00:00:05,000 --> 00:00:07,000\nAudio and image.\n"
    (package / "track-en.srt").write_text(english)
    request["captions"].append({"language": "en", "name": "Smoke EN", "isDraft": False, "file": "track-en.srt"})
    request["playlist_ids"] = [PLAYLIST]
    assemble(package, request, "smoke-test")
    report = create_seal(package, "smoke-test", config=config)
    assert report["contract_passed"], report
    return package, config


@pytest.fixture
def env(candidate, tmp_path, monkeypatch):
    old_mask = os.umask(0o077)
    root = tmp_path.resolve()
    package = root / "package"
    shutil.copytree(candidate[0], package)
    package.chmod(0o700)
    config = candidate[1]
    preview = root / "video-release-preview.html"
    result = render(package, "smoke-test", preview, config=config)
    assert result["human_preview_ready"], result
    manifest = json_data((package / MANIFEST).read_bytes())
    binding = local_authority_binding(package, manifest, result, CLI_HASH, IDENTITY)
    store = OperatorStore(root / "operator")
    clock = SimpleNamespace(now=datetime.now(timezone.utc))
    client = FakeClient(root / "provider", manifest["snippet"]["title"])
    settings = SimpleNamespace(root=root, package=package, preview=preview, store=store, client=client,
                               config=config, clock=clock, binding=binding, registry=root / "registry",
                               state=root / "state", manifest=manifest)
    settings.job = settings.state / digest(manifest["episode_key"].encode())
    def approval(key="first", operations=OPS, lifetime=timedelta(hours=1), **extra):
        value = {**binding, "authorization_id": key, "authorization_version": "2.0",
                 "source_ref_kind": "operator_terminal", "source_ref": key,
                 "original_user_quote": "Authorize synthetic test fixture.",
                 "authorized_at": timestamp(clock.now - timedelta(seconds=1)),
                 "expires_at": timestamp(clock.now + lifetime), "actor": "user", "revoked": False,
                 "supersedes": None, "allowed_operations": sorted(operations), **extra}
        validate_auth(value)
        return store.store("authorizations", key, value)
    def run(mode, auth="first", *, state=None, resolution=None):
        ctl = Controller(package, preview, "smoke-test", client, store, settings.registry,
                         state or settings.state, auth, config=config, clock=lambda: clock.now,
                         hash_cli=lambda: CLI_HASH, hash_contract=lambda: binding["contract_bundle_sha256"])
        return ctl.execute(mode, resolution=resolution)
    settings.approval, settings.run = approval, run
    try:
        yield settings
    finally:
        os.umask(old_mask)


def ledger(env):
    return Journal(env.job)


def test_plan_publish_restart_and_drift(env):
    env.approval()
    plan = env.run("plan")
    assert plan["status"] == "planned" and len(plan["operations"]) == 5
    assert not env.job.exists() and not env.client.requests("write")
    result = env.run("publish")
    assert result["status"] == "published_private" and result["video_id"] == VIDEO
    receipt = (env.job / "receipt.json").read_bytes()
    assert digest(receipt) == result["receipt_sha256"]
    assert env.client.requests("write") == ["videos/upload", "thumbnails/set", "captions/upload",
                                            "captions/upload", "playlists/items/add"]
    assert len(ledger(env).events("VERIFIED")) == 5
    assert env.run("publish")["status"] == "already_published_noop"
    assert len(env.client.requests("write")) == 5
    env.client.failure("audio_language")
    assert env.run("publish")["mutations"] == 0
    env.client.failure("caption_draft")
    with pytest.raises(Stop, match="caption_readback_not_serving"):
        env.run("publish")
    assert (env.job / "receipt.json").read_bytes() == receipt
    assert len(env.client.requests("write")) == 5


@pytest.mark.parametrize(("failure", "reason"), [
    ("seal_removed", "release_contract_or_preview_rejected"),
    ("package_drift", "release_contract_or_preview_rejected"),
    ("preview_drift", "release_contract_or_preview_rejected"),
    ("unknown_auth", "operator_record_not_registered"),
    ("tamper_auth", "operator_index_digest_mismatch"),
    ("revoked", "authorization_revoked_or_mismatched"),
    ("narrow_genesis", "genesis_authorization_requires_all_operations"),
    ("wrong_channel", "channel_identity_mismatch"),
    ("collision", "upload_title_collision_requires_operator"),
    ("expired", "writes_blocked_expired"),
])
def test_guard_cases_zero_writes(env, failure, reason):
    if failure != "unknown_auth":
        env.approval(operations={"readback", "upload_video"} if failure == "narrow_genesis" else OPS)
    if failure == "seal_removed":
        (env.package / SEAL).unlink()
    elif failure == "package_drift":
        with (env.package / "delivery.mp4").open("ab") as stream:
            stream.write(b"x")
    elif failure == "preview_drift":
        env.preview.write_text("<img src='https://example.test/track'/>")
    elif failure == "tamper_auth":
        with (env.store.root / "authorizations/first.json").open("ab") as stream:
            stream.write(b" ")
    elif failure == "revoked":
        env.store.revoke("first")
    elif failure == "expired":
        env.clock.now += timedelta(hours=2)
        assert env.run("plan")["status"] == "writes_blocked_expired"
    else:
        env.client.failure(failure)
    with pytest.raises(Stop, match=reason):
        env.run("publish")
    assert not env.client.requests("write") and not env.job.exists()
    if failure in {"seal_removed", "package_drift", "preview_drift", "unknown_auth", "tamper_auth",
                   "revoked", "narrow_genesis"}:
        assert not env.client.requests()


@pytest.mark.parametrize(("failure", "reconciles"), [
    ("lost_init", False), ("lost_final_missing", False), ("lost_final_partial", False),
    ("lost_final_complete", True), ("no_effect", False),
])
def test_ambiguous_or_rejected_upload_never_replays(env, failure, reconciles):
    env.approval()
    env.client.failure(failure)
    with pytest.raises(Stop):
        env.run("publish")
    with pytest.raises(Stop, match="reconciliation_required|prior_rejection_no_retry"):
        env.run("publish")
    assert env.client.requests("write") == ["videos/upload"]
    assert not (env.job / "receipt.json").exists()
    result = env.run("reconcile")
    assert result["mutations"] == 0
    assert (result["status"] == "reconciled_upload") is reconciles
    assert env.client.requests("write") == ["videos/upload"]
    if reconciles:
        env.client.failure("")
        assert env.run("publish")["video_id"] == VIDEO
        assert env.client.requests("write").count("videos/upload") == 1


@pytest.mark.parametrize("failure", ["processing", "known_partial", "readback_timeout", "privacy_drift",
                                     "default_thumbnail", "second_rejected",
                                     "lost_thumbnail", "lost_playlist", "truncated_playlist", "duplicate_caption"])
def test_partial_retains_durable_history(env, failure):
    env.approval()
    env.client.failure(failure)
    with pytest.raises(Stop):
        env.run("publish")
    assert env.client.requests("write").count("videos/upload") == 1
    assert not (env.job / "receipt.json").exists()
    assert ledger(env).events("ACK")[0]["video_id"] == VIDEO
    before = env.client.requests("write")
    env.client.failure("")
    if failure in {"second_rejected", "lost_thumbnail", "lost_playlist"}:
        with pytest.raises(Stop, match="reconciliation_required|prior_rejection_no_retry"):
            env.run("publish")
        assert env.client.requests("write") == before
    else:
        assert env.run("publish")["video_id"] == VIDEO
        assert env.client.requests("write").count("videos/upload") == 1


def test_expired_resume_with_narrow_successor(env):
    previous = env.approval()
    env.client.failure("processing")
    with pytest.raises(Stop, match="video_processing_pending"):
        env.run("publish")
    env.clock.now += timedelta(hours=2)
    env.client.failure("")
    with pytest.raises(Stop, match="writes_blocked_expired"):
        env.run("publish")
    assert env.client.requests("write") == ["videos/upload"]
    env.approval("second", {"readback", "set_thumbnail", "upload_captions", "add_playlist"},
                 supersedes={"authorization_id": "first", "authorization_sha256": previous})
    assert env.run("publish", "second")["video_id"] == VIDEO
    assert env.client.requests("write").count("videos/upload") == 1
    env.clock.now += timedelta(hours=2)
    assert env.run("publish", "second")["mutations"] == 0


def test_exclusive_episode_lock_and_database_origin(env):
    env.approval()
    assert env.run("plan")["status"] == "planned"
    lock = env.registry / "locks" / (env.job.name + ".lock")
    with lock_file(lock):
        with pytest.raises(Stop, match="job_locked"):
            env.run("publish")
    assert not env.client.requests("write")
    env.client.failure("processing")
    with pytest.raises(Stop, match="video_processing_pending"):
        env.run("publish")
    with pytest.raises(Stop, match="episode_registry_binding_conflict"):
        env.run("publish", state=env.root / "other-state")
    assert env.client.requests("write").count("videos/upload") == 1


class SimulatedCrash(BaseException):
    pass


@pytest.mark.parametrize(("boundary", "first_writes", "can_finish"), [
    ("after_intent", 0, False), ("before_ack", 1, False),
    ("after_ack", 1, True), ("before_finalize", 5, True),
])
def test_torn_commit_boundary(env, monkeypatch, boundary, first_writes, can_finish):
    env.approval()
    append = Journal.append
    def fail_at(journal, event, **data):
        upload = data.get("operation") == "upload_video"
        if (boundary == "before_ack" and upload and event == "ACK") or (
                boundary == "before_finalize" and event == "FINALIZED"):
            raise SimulatedCrash
        row = append(journal, event, **data)
        if upload and ((boundary == "after_intent" and event == "INTENT") or
                       (boundary == "after_ack" and event == "ACK")):
            raise SimulatedCrash
        return row
    with monkeypatch.context() as injected:
        injected.setattr(Journal, "append", fail_at)
        with pytest.raises(SimulatedCrash):
            env.run("publish")
    assert len(env.client.requests("write")) == first_writes
    if can_finish:
        assert env.run("publish")["video_id"] == VIDEO
        assert env.client.requests("write").count("videos/upload") == 1
        assert len(ledger(env).events("FINALIZED")) == 1
    else:
        with pytest.raises(Stop, match="reconciliation_required"):
            env.run("publish")
        assert len(env.client.requests("write")) == first_writes
        assert not (env.job / "receipt.json").exists()


def test_history_and_current_privacy_diagnosis_are_distinct():
    from datetime import date
    from publish import privacy_result

    current = privacy_result("public", "private")
    previous = privacy_result("public", "private", historical_evidence={
        "observed_on": date(2026, 11, 1), "source": "independent_provider_confirmation",
        "evidence_sha256": "a" * 64,
    })
    assert not current["matches"] and not previous["matches"]
    assert current["reason"] == "unknown" and current["privacy_locked_by_unverified_project"] is None
    assert previous["reason"] == "unverified_project_private_lock"
    assert previous["privacy_locked_by_unverified_project"] is True


def test_saved_job_refuses_corrupt_journal_before_mutations(env):
    env.approval()
    env.client.failure("processing")
    with pytest.raises(Stop, match="video_processing_pending"):
        env.run("publish")
    with (env.job / "journal.jsonl").open("ab") as target:
        target.write(b'{"torn"')
    with pytest.raises(Stop, match="journal_incomplete_last_line"):
        env.run("publish")
    assert env.client.requests("write") == ["videos/upload"]


def test_lock_is_held_by_child_until_parent_pipe_closes(tmp_path):
    lock_path = tmp_path / "job.lock"
    reader, writer = os.pipe()
    child = None
    try:
        with lock_file(lock_path) as held:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-c",
                                     "import os,sys;print('ready',flush=True);"
                                     "assert os.read(int(sys.argv[1]),1)==b''", str(reader)],
                                     pass_fds=(held, reader), stdout=subprocess.PIPE, text=True)
            assert child.stdout.readline().strip() == "ready"
        with pytest.raises(Stop, match="job_locked"):
            with lock_file(lock_path):
                pytest.fail("The lock cannot be reclaimed while the child owns it.")
        os.close(writer)
        writer = None
        assert child.wait(timeout=5) == 0
        with lock_file(lock_path):
            pass
    finally:
        if child and child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        if child and child.stdout:
            child.stdout.close()
        if writer is not None:
            os.close(writer)
        os.close(reader)


def test_live_client_guard_stops_a_slow_child(tmp_path):
    from publish import Client

    launcher = tmp_path / ".venv/bin/python"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    launcher.chmod(0o700)
    client = Client(tmp_path, "smoke-test")
    lock_path = tmp_path / "job.lock"

    def revoked():
        raise Stop("dispatch_authority_changed", code=10)

    with lock_file(lock_path) as held:
        with pytest.raises(Stop, match="dispatch_authority_changed"):
            client(["captions", "upload"], lock=held, seconds=2, guard=revoked)
    with lock_file(lock_path):
        pass


def test_successor_record_cannot_fork(env):
    previous = env.approval()
    supersedes = {"authorization_id": "first", "authorization_sha256": previous}
    env.approval("second", {"readback", "upload_captions"}, supersedes=supersedes)
    with pytest.raises(Stop, match="authorization_branch_forbidden"):
        env.approval("third", {"readback", "upload_captions"}, supersedes=supersedes)


def test_private_storage_rejects_git_worktree(tmp_path):
    from auth_store import safe_private

    root = tmp_path.resolve()
    (root / ".git").write_text("gitdir: /irrelevant/private/path\n")
    storage = root / "package"
    storage.mkdir(mode=0o700)
    with pytest.raises(Stop, match="private_state_under_vault_or_git"):
        safe_private(storage)


@pytest.fixture(scope="module")
def comparable_video(candidate):
    manifest = json_data((candidate[0] / MANIFEST).read_bytes())
    actual = {
        "snippet": {**manifest["snippet"], "channelId": manifest["target_channel_id"]},
        "status": {**manifest["status"]},
        "paidProductPlacementDetails": {**manifest["paidProductPlacementDetails"]},
        "contentDetails": {"duration": "PT15S"},
    }
    return manifest, actual


@pytest.mark.parametrize("expected", [True, False], ids=["expected-true", "expected-false"])
@pytest.mark.parametrize(("shape", "observed"), [
    ("true", True), ("false", False), ("omitted", None), ("explicit-null", None),
    ("zero", 0), ("one", 1), ("string", "false"), ("array", []), ("object", {}),
], ids=["true", "false", "omitted", "explicit-null", "zero", "one", "string", "array", "object"])
def test_synthetic_disclosure_truth_table(comparable_video, expected, shape, observed):
    manifest, actual = copy.deepcopy(comparable_video)
    key = "containsSyntheticMedia"
    manifest["status"][key] = expected
    present = shape != "omitted"
    if present:
        actual["status"][key] = observed
    else:
        del actual["status"][key]
    original = canonical(actual)
    if shape == "omitted" and expected is False:
        evidence_status = "api_omitted_false_default"
    elif observed is expected:
        evidence_status = "explicit_true" if expected else "explicit_false"
    else:
        with pytest.raises(Stop, match="video_field_readback_mismatch") as failure:
            matching_video(actual, manifest, 15)
        assert failure.value.code == 4
        assert canonical(actual) == original
        return
    evidence = matching_video(actual, manifest, 15)["fields"][key]
    assert evidence == {"expected": expected, "observed": observed, "wire_request_sent": expected,
                        "key_present": present, "status": evidence_status}
    assert canonical(actual) == original


@pytest.mark.parametrize(("part", "key"), [
    ("status", "selfDeclaredMadeForKids"), ("paidProductPlacementDetails", "hasPaidProductPlacement"),
])
def test_other_disclosures_still_require_explicit_readback(comparable_video, part, key):
    manifest, actual = copy.deepcopy(comparable_video)
    del actual[part][key]
    with pytest.raises(Stop, match="video_field_readback_mismatch") as failure:
        matching_video(actual, manifest, 15)
    assert failure.value.code == 4


def test_omitted_false_resumes_from_upload_ack_and_then_noops(env):
    env.approval()
    env.client.failure("processing")
    with pytest.raises(Stop, match="video_processing_pending"):
        env.run("publish")
    assert [(row["event"], row.get("operation")) for row in ledger(env).rows] == [
        ("GENESIS", None), ("INTENT", "upload_video"), ("ACK", "upload_video"),
    ]
    env.client.failure("disclosure_missing")
    result = env.run("publish")
    assert result["status"] == "published_private" and result["video_id"] == VIDEO
    data = json_data((env.job / "youtube-readback.json").read_bytes())
    uploaded = next(resource for resource in data["resources"] if resource["operation"] == "upload_video")
    assert uploaded["fields"]["containsSyntheticMedia"] == {
        "expected": False, "observed": None, "wire_request_sent": False,
        "key_present": False, "status": "api_omitted_false_default",
    }
    writes = env.client.requests("write")
    assert writes.count("videos/upload") == 1
    assert "videos/upload-status" not in env.client.requests("read")
    assert env.run("publish") == {"status": "already_published_noop", "video_id": VIDEO, "mutations": 0}
    assert env.client.requests("write") == writes


@pytest.mark.parametrize("when,value", [("first", None), ("final", True), ("final", None)])
def test_synthetic_disclosure_conflict_prevents_receipt(env, monkeypatch, when, value):
    env.approval()
    invoke = FakeClient.__call__

    def changed_disclosure(client, args, **kwargs):
        response = invoke(client, args, **kwargs)
        if args[:2] == ["videos", "get"] and (when == "first" or
                "playlists/items/add" in client.requests("write")):
            response["items"][0]["status"]["containsSyntheticMedia"] = value
        return response

    monkeypatch.setattr(FakeClient, "__call__", changed_disclosure)
    with pytest.raises(Stop, match="video_field_readback_mismatch") as failure:
        env.run("publish")
    assert failure.value.code == 4
    assert not (env.job / "receipt.json").exists()
    writes = env.client.requests("write")
    assert writes.count("videos/upload") == 1
    if when == "first":
        assert writes == ["videos/upload"]
    else:
        assert writes[-1] == "playlists/items/add"


def test_qr_evidence_reliable_on_known_legacy_opencv_edge_nonce_and_rejects_conflict(tmp_path):
    import qrcode
    from PIL import Image
    from publish import qr_evidence

    token = "ytpub-smoke-v2/3c94bf93dfb549ecbea5ef48c08349ee"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=12)
    qr.add_data(token)
    mark = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")
    canvas = Image.new("RGB", (1280, 720), "#172e45")
    canvas.paste(mark, ((1280 - mark.width) // 2, (720 - mark.height) // 2))
    png_path = tmp_path / "thumb.png"
    jpg_path = tmp_path / "thumb.jpg"
    canvas.save(png_path)
    canvas.save(jpg_path, format="JPEG", quality=75)

    expected_digest = digest(token.encode())
    assert qr_evidence(png_path) == (expected_digest, [1280, 720])
    assert qr_evidence(jpg_path) == (expected_digest, [1280, 720])

    conflict = Image.new("RGB", (1280, 720), "#172e45")
    for idx, suffix in enumerate(("11111111111111111111111111111111", "22222222222222222222222222222222")):
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=8)
        q.add_data(f"ytpub-smoke-v2/{suffix}")
        m = q.make_image(fill_color="black", back_color="white").get_image().convert("RGB")
        conflict.paste(m, (80 + idx * 620, 120))
    conflict_path = tmp_path / "conflict.png"
    conflict.save(conflict_path)
    with pytest.raises(Stop, match="thumbnail_marker_not_proven"):
        qr_evidence(conflict_path)
