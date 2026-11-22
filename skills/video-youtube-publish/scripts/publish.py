"""Private YouTube publishing with sealed inputs, local authority, and durable intent."""

import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity import cli_identity, contract_identity
from auth_store import OPS, OperatorStore, Stop, lock_file, require, safe_private, safe_read, utc
from journal import Journal
from package import (MANIFEST, PAYLOAD, SEAL, Invalid, artifact_open, atomic_write,
                     canonical, check, cues, digest, json_data, local_bytes, records,
                     render, sha_file, sync_directory)

CLI_ROOT=Path(os.environ.get("YTPUB_CLI_ROOT",str(Path.home()/"Code/ytpub-cli"))).expanduser()
VIDEO_ID=re.compile(r"[A-Za-z0-9_-]{11}")
CAPTION_ID=re.compile(r"[A-Za-z0-9_.:-]{1,160}")
MARKER=re.compile(r"ytpub-smoke-v2/[a-f0-9]{32}")
ALLOWED_FAILURES={"transport_failure","dispatch_deadline","mutation_response_unknown",
                  "mutation_readback_incomplete","upload_readback_incomplete","privacy_mismatch",
                  "quota_or_rate_limit","provider_rejected","upload_session_unknown",
                  "partial_upload","unknown","scope_mismatch","channel_mismatch"}


def secure_cli_env():
    keep={"HOME","PATH","TMPDIR","SYSTEMROOT","LANG","LC_ALL","YTPUB_CLIENT_SECRET",
          "YTPUB_TOKEN_PATH","VIDEO_SKILLS_CONFIG"}
    return {key:value for key,value in os.environ.items() if key in keep}


class Client:
    def __init__(self,root,profile,backend=None):
        self.root=root
        self.profile=profile
        self.backend=backend

    def __call__(self,args,*,fds=(),lock=None,seconds=600,guard=None):
        command=[str(self.root/".venv/bin/python"),"-I","-B","-m","ytpub.cli",*args,
                 "--profile",self.profile]
        if self.backend:
            command+=["--cache-backend",self.backend]
        read_end=write_end=None
        if lock is not None:
            read_end,write_end=os.pipe()
            command+=["--lock-fd",str(lock),"--parent-fd",str(read_end),
                      "--deadline-seconds",str(min(600,max(.001,seconds)))]
            fds=(*fds,lock,read_end)
        try:
            proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  pass_fds=fds, env=secure_cli_env(),stdin=subprocess.DEVNULL)
            end=time.monotonic()+(seconds if lock is not None else 180)
            try:
                while True:
                    remaining=end-time.monotonic()
                    require(remaining>0,"ytpub_process_timeout",code=10)
                    try:
                        stdout,stderr=proc.communicate(timeout=min(.25,remaining) if guard else remaining)
                        break
                    except subprocess.TimeoutExpired:
                        if guard:
                            guard()
            finally:
                if proc.poll() is None:
                    if write_end is not None:
                        os.close(write_end)
                        write_end=None
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
        finally:
            for fd in (read_end,write_end):
                if fd is not None:
                    os.close(fd)
        if proc.returncode:
            try:
                failure=json_data(stderr)
                reason=failure.get("error_code")
                patterns={"video_id":VIDEO_ID,"caption_id":CAPTION_ID,"item_id":CAPTION_ID,
                          "session_handle":re.compile(r"[a-f0-9]{32}")}
                ids={k:v for k,v in failure.get("safe_ids",{}).items() if
                     k in patterns and isinstance(v,str) and patterns[k].fullmatch(v)}
            except (ValueError,TypeError,AttributeError):
                reason,ids="unknown",{}
            code=proc.returncode if proc.returncode in (2,3,4,5,7,10,11) else 11
            raise Stop(reason if reason in ALLOWED_FAILURES else "ytpub_failed",code=code,detail=ids)
        try:
            result=json_data(stdout)
            require(result.get("schema_version")=="1" and result.get("profile")==self.profile and
                    isinstance(result.get("data"),dict),"invalid_ytpub_response",code=11)
            return result["data"]
        except (ValueError,TypeError,AttributeError) as exc:
            raise Stop("invalid_ytpub_response",code=11) from exc


def local_authority_binding(root, manifest, report, cli_hash, identity):
    require(isinstance(identity.get("oauth_binding_sha256"),str) and
            re.fullmatch(r"[a-f0-9]{64}",identity["oauth_binding_sha256"]) and
            identity.get("identity_verified") is True and
            identity.get("channel_id")==manifest["target_channel_id"], "channel_identity_mismatch",code=3)
    require(manifest["channel_profile"]=="smoke-test" and
            manifest["status"]["privacyStatus"]=="private" and
            "publishAt" not in manifest["status"] and manifest["notifySubscribers"] is False,
            "private_smoke_policy")
    return {"contract_version":"1.0","mode":"private_smoke",
            "episode_key":manifest["episode_key"],"package_revision":manifest["package_revision"],
            "channel_profile":manifest["channel_profile"],"target_channel_id":manifest["target_channel_id"],
            "manifest_sha256":report["binding"]["manifest_sha256"],
            "payload_sha256":report["binding"]["payload_sha256"],
            "contract_bundle_sha256":report["binding"]["contract_bundle_sha256"],
            "video_sha256":manifest["delivery_video"]["sha256"],
            "thumbnail_sha256":manifest["thumbnail"]["sha256"],
            "captions_sha256":{x["language"]:x["file"]["sha256"] for x in manifest["captions"]},
            "seal_sha256":digest(local_bytes(root,SEAL)),"cli_identity_sha256":cli_hash,
            "oauth_binding_sha256":identity["oauth_binding_sha256"],
            "playlist_ids":manifest["playlist_ids"],"target_privacy_status":"private",
            "publish_at":None,"notify_subscribers":False}


def freeze_package(source,dest,manifest):
    dest.mkdir(mode=0o700)
    names={MANIFEST,SEAL,*(item["path"] for _,item in records(manifest))}
    for name in sorted(names):
        target=dest/name
        target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with artifact_open(source,name) as src:
            fd=os.open(target,os.O_WRONLY|os.O_NOFOLLOW|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"wb") as output:
                shutil.copyfileobj(src,output,1024*1024)
                output.flush()
                os.fsync(output.fileno())
        target.chmod(0o400)
        sync_directory(target.parent)
    sync_directory(dest)


def qr_evidence(path):
    frame=cv2.imread(str(path))
    require(frame is not None,"thumbnail_decode_failed",code=4)
    found, decoded, *_=cv2.QRCodeDetector().detectAndDecodeMulti(frame)
    require(found and len(decoded)==1 and MARKER.fullmatch(decoded[0]),
            "thumbnail_marker_not_proven",code=4)
    return digest(decoded[0].encode()),[int(frame.shape[1]),int(frame.shape[0])]


def privacy_result(requested, observed, *, historical_evidence=None):
    values={"private","unlisted","public"}
    observed=observed if isinstance(observed,str) and observed in values else None
    matched=requested==observed
    historical_lock=None
    if requested=="public" and observed=="private" and historical_evidence:
        when=historical_evidence.get("observed_on")
        source=historical_evidence.get("source")
        checksum=historical_evidence.get("evidence_sha256","")
        if (isinstance(when,date) and when<date(2026,11,2) and
                source=="independent_provider_confirmation" and re.fullmatch(r"[a-f0-9]{64}",checksum)):
            historical_lock=True
    return {"matches":matched,"requested_privacy":requested,"observed_privacy":observed,
            "privacy_locked_by_unverified_project":historical_lock,
            "reason":None if matched else "unverified_project_private_lock" if historical_lock else "unknown"}


def matching_video(actual, manifest, expected_seconds):
    expected=manifest["snippet"]
    snippet,status=actual.get("snippet",{}),actual.get("status",{})
    pairs={key:{"expected":expected[key],"observed":snippet.get(key)} for key in
           ("title","description","categoryId","defaultLanguage","tags")}
    if pairs["tags"]["observed"] is None and not expected["tags"]:
        pairs["tags"]["observed"]=[]
    pairs["channelId"]={"expected":manifest["target_channel_id"],"observed":snippet.get("channelId")}
    pairs.update({key:{"expected":manifest["status"][key],"observed":status.get(key)}
                  for key in ("privacyStatus","selfDeclaredMadeForKids")})
    pairs["publishAt"]={"expected":None,"observed":status.get("publishAt")}
    pairs["hasPaidProductPlacement"]={"expected":manifest["paidProductPlacementDetails"]["hasPaidProductPlacement"],
                                     "observed":actual.get("paidProductPlacementDetails",{}).get("hasPaidProductPlacement")}
    if manifest.get("localizations"):
        pairs["localizations"]={"expected":manifest["localizations"],"observed":actual.get("localizations")}
    mismatch=[key for key,value in pairs.items() if value["expected"]!=value["observed"] or
              type(value["expected"]) is not type(value["observed"])]
    require(not mismatch,"video_field_readback_mismatch",code=4)
    disclosure_key = "containsSyntheticMedia"
    expected_disclosure = manifest["status"][disclosure_key]
    disclosure_present = disclosure_key in status
    observed_disclosure = status.get(disclosure_key)
    if not disclosure_present and expected_disclosure is False:
        disclosure_status = "api_omitted_false_default"
    else:
        require(type(expected_disclosure) is bool and observed_disclosure is expected_disclosure,
                "video_field_readback_mismatch", code=4)
        disclosure_status = "explicit_true" if expected_disclosure else "explicit_false"
    pairs[disclosure_key] = {
        "expected": expected_disclosure,
        "observed": observed_disclosure,
        "wire_request_sent": expected_disclosure,
        "key_present": disclosure_present,
        "status": disclosure_status,
    }
    raw=actual.get("contentDetails",{}).get("duration","")
    match=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",raw)
    require(match is not None and abs(sum(int(v or 0)*scale for v,scale in zip(match.groups(),(3600,60,1)))-
                                      expected_seconds)<=1,"video_duration_readback_mismatch",code=4)
    audio=snippet.get("defaultAudioLanguage")
    return {"fields":pairs,"observed_duration":raw,"expected_seconds":expected_seconds,
            "default_audio_language":{"expected":expected["defaultAudioLanguage"],"observed":audio,
              "matches":audio==expected["defaultAudioLanguage"] if audio is not None else None,
              "status":"capability_observed" if audio is not None else "capability_unverified"}}


class Controller:
    def __init__(self,package,preview,profile,cli,store,registry,state_root,auth_id,
                 *, config=None,clock=None,hash_cli=None,hash_contract=None):
        self.root,self.preview=package,preview
        self.profile,self.cli,self.store=profile,cli,store
        self.registry,self.state_root=registry,state_root
        self.auth_id,self.config=auth_id,config
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.hash_cli=hash_cli or (lambda:cli_identity(cli.root,verify=True)[0])
        self.hash_contract=hash_contract or (lambda:contract_identity(verify=True)[0])
        self.binding=None
        self.job=None
        self.lock=None
        self.mode=None
        self.evidence={}
        self.scratch=None
        self.frozen=None

    def local(self):
        report=render(self.root,self.profile,self.preview,config=self.config,write=False)
        require(report.get("human_preview_ready") is True,"release_contract_or_preview_rejected")
        m=json_data(local_bytes(self.root,MANIFEST))
        require(self.profile=="smoke-test" and m["channel_profile"]==self.profile and
                m["status"]["privacyStatus"]=="private" and "publishAt" not in m["status"] and
                m["notifySubscribers"] is False,"private_smoke_policy")
        return report,m

    def execute(self,mode,*,resolution=None):
        self.mode=mode
        safe_private(self.root)
        require(not self.preview.is_symlink() and self.preview.parent==self.root.parent,
                "preview_must_be_local_sibling")
        # Validate the package before the first CLI invocation.
        report, m=self.local()
        require(self.hash_contract()==report["binding"]["contract_bundle_sha256"],
                "contract_runtime_identity_mismatch")
        self.manifest=m
        self.duration=report["details"]["G03"]["seconds"]
        self.cli_hash=self.hash_cli()
        approval,_=self.store.load("authorizations",self.auth_id)
        require(isinstance(approval,dict),"invalid_authorization_schema")
        self.binding=local_authority_binding(self.root,m,report,self.cli_hash,{
            "oauth_binding_sha256":approval.get("oauth_binding_sha256"),
            "identity_verified":True,"channel_id":m["target_channel_id"],
        })
        self.auth_chain=self.store.chain(self.auth_id,self.binding,self.clock())
        self.active,self.active_hash=self.auth_chain[-1]
        required_ops=OPS if m["playlist_ids"] else OPS-{"add_playlist"}
        require(set(self.auth_chain[0][0]["allowed_operations"])==required_ops,
                "genesis_authorization_requires_all_operations")
        identity=self.cli(["doctor"])
        require(local_authority_binding(self.root,m,report,self.cli_hash,identity)==self.binding,
                "live_oauth_binding_mismatch",code=3)
        known=[self.registry,self.state_root,self.store.root,self.root]
        for i,left in enumerate(known):
            require(all(not left.is_relative_to(right) and not right.is_relative_to(left) for right in known[i+1:]),
                    "state_package_or_operator_path_overlap")
        safe_private(self.registry,create=True)
        safe_private(self.state_root,create=True)
        locks=self.registry/"locks"
        safe_private(locks,create=True)
        self.key=digest(m["episode_key"].encode())
        self.media_key=digest(canonical([m["target_channel_id"],m["delivery_video"]["sha256"]]))
        directory=self.state_root/self.key
        with lock_file(locks/f"{self.key}.lock",shared=mode=="plan") as lock:
            self.lock=lock
            self.job=self.open_job(directory)
            if self.job:
                self.bind_auth_chain(write=mode!="plan")
            if mode=="plan":
                return self.plan()
            if mode=="reconcile":
                require(self.job is not None,"no_state_to_reconcile")
                return self.reconcile(resolution)
            if self.job is None:
                require(utc(self.active["expires_at"])>self.clock(),"writes_blocked_expired")
                require("upload_video" in self.active["allowed_operations"],"operation_not_authorized")
                require(len(self.auth_chain)==1,"initial_publish_requires_genesis_auth")
                self.check_new_video_conflict()
                self.job=self.create_job(directory)
            with tempfile.TemporaryDirectory(prefix=".snapshot-",dir=self.state_root) as temporary:
                self.scratch=Path(temporary)
                self.frozen=self.scratch/"package"
                freeze_package(self.root,self.frozen,self.manifest)
                try:
                    return self.publish()
                except Stop as exc:
                    code=exc.reason
                    if exc.code in (7,10,11):
                        state="RECONCILIATION_REQUIRED"
                    elif code in ("writes_blocked_expired","operation_not_authorized"):
                        state="AWAITING_AUTH"
                    else:
                        state="WAIT_READBACK" if exc.code==4 else "BLOCKED"
                    self.job.snapshot(self.binding,state,self.known_video())
                    if not (self.job.directory/"receipt.json").exists():
                        self.write_partial(state,code)
                    raise

    @property
    def registry_path(self):
        return self.registry/"episodes.json"

    def registered(self):
        if self.registry_path.exists() or self.registry_path.is_symlink():
            result=json_data(safe_read(self.registry_path))
            require(isinstance(result,dict),"invalid_episode_registry")
            return result
        return {}

    def open_job(self,directory):
        entries=self.registered()
        row=entries.get(self.key)
        if row is None:
            require(not directory.exists() and not directory.is_symlink(),"unregistered_state_exists")
            return None
        require(row=={"root":str(self.state_root),"candidate":self.binding,"media_key":self.media_key},
                "episode_registry_binding_conflict")
        require(directory.is_dir() and not directory.is_symlink(),"registered_state_missing")
        job=Journal(directory)
        require(job.rows and job.rows[0]["event"]=="GENESIS" and
                job.rows[0]["candidate"]==self.binding,"journal_genesis_mismatch")
        job.ensure_snapshot()
        require(safe_read(job.directory/PAYLOAD)==local_bytes(self.root,PAYLOAD),"frozen_payload_mismatch")
        return job

    def create_job(self,directory):
        with lock_file(self.registry/"index.lock"):
            entries=self.registered()
            require(self.key not in entries and
                    self.media_key not in {r["media_key"] for r in entries.values()},
                    "candidate_or_media_registered")
            entries[self.key]={"root":str(self.state_root),"candidate":self.binding,"media_key":self.media_key}
            atomic_write(self.registry_path,canonical(entries))
        # A crash between registration and genesis fails closed wherever it is resumed.
        job=Journal(directory,create=True)
        atomic_write(job.directory/PAYLOAD,local_bytes(self.root,PAYLOAD),exclusive=True)
        job.append("GENESIS",candidate=self.binding,authorization_id=self.auth_id,authorization_sha256=self.active_hash)
        job.snapshot(self.binding,"READY")
        return job

    def bind_auth_chain(self,*,write):
        genesis=self.job.rows[0]
        first,first_hash=self.auth_chain[0]
        require((genesis["authorization_id"],genesis["authorization_sha256"])==
                (first["authorization_id"],first_hash),"authorization_genesis_conflict")
        history=self.job.events("AUTH_SUCCESSOR")
        # Compare persisted head to the supplied chain, then allow at most one next link.
        links=[(x["authorization_id"],x["authorization_sha256"]) for x in [genesis,*history]]
        presented=[(item["authorization_id"],sha) for item,sha in self.auth_chain]
        require(len(links)<=len(presented)<=len(links)+1 and presented[:len(links)]==links,
                "authorization_head_conflict")
        if len(presented)>len(links):
            require(self.mode=="publish" and utc(self.active["expires_at"])>self.clock(),
                    "successor_requires_current_publish")
            if write:
                self.job.append("AUTH_SUCCESSOR",authorization_id=self.auth_id,authorization_sha256=self.active_hash,
                                previous_authorization_id=links[-1][0],previous_authorization_sha256=links[-1][1])

    def check_new_video_conflict(self):
        candidates=self.cli(["videos","list","--all-pages"])
        require(candidates.get("complete") is True,"uploads_listing_incomplete",code=4)
        title=self.manifest["snippet"]["title"]
        require(not any(row.get("snippet",{}).get("title")==title for row in candidates.get("items",[])),
                "upload_title_collision_requires_operator",code=4)

    def op_key(self,operation,target,sha):
        return digest(canonical([self.manifest["episode_key"],self.manifest["package_revision"],operation,target,sha]))

    def known_video(self):
        if self.job is None:
            return None
        return next((r.get("video_id") for r in reversed(self.job.rows)
                     if r.get("operation")=="upload_video" and r["event"] in ("ACK","RECONCILED")
                     and r.get("video_id")),None)

    def expired_seconds(self):
        return (utc(self.active["expires_at"])-self.clock()).total_seconds()

    def check_write(self,operation,*,refresh_local):
        if refresh_local:
            report,m=self.local()
            observed=self.cli(["doctor"])
            candidate=local_authority_binding(self.root,m,report,self.hash_cli(),observed)
            require(candidate==self.binding,"package_or_runtime_binding_changed")
            frozen,_=check(self.frozen,self.profile,config=self.config,require_seal=True)
            require(frozen.get("contract_passed") is True and frozen["binding"]==report["binding"],
                    "frozen_package_binding_changed")
        chain=self.store.chain(self.auth_id,self.binding,self.clock())
        require(chain[-1]==(self.active,self.active_hash),"authorization_head_changed")
        require(self.expired_seconds()>0,"writes_blocked_expired")
        require(operation in self.active["allowed_operations"],"operation_not_authorized")

    @contextlib.contextmanager
    def request_args(self,operation,target,*,plan=False,resume=None):
        media_root=self.root if plan else self.frozen
        with contextlib.ExitStack() as stack:
            descriptors=[]
            def media(item):
                handle=stack.enter_context(artifact_open(media_root,item["path"]))
                descriptors.append(handle.fileno())
                return ["--media-fd",str(handle.fileno()),"--media-sha256",item["sha256"]]
            if operation=="upload_video":
                metadata=stack.enter_context(artifact_open(media_root,PAYLOAD))
                descriptors.append(metadata.fileno())
                args=["videos","upload","--metadata-fd",str(metadata.fileno()),"--metadata-file-sha256",
                      self.binding["payload_sha256"],"--no-notify-subscribers",
                      *media(self.manifest["delivery_video"])]
                if resume:
                    args+=["--resume-handle",resume["handle"],"--offset",str(resume["offset"])]
            elif operation=="set_thumbnail":
                args=["thumbnails","set",target,*media(self.manifest["thumbnail"])]
            elif operation=="upload_captions":
                args=["captions","upload",target[0],"--language",target[1]["language"],"--name",
                      target[1]["name"],*media(target[1]["file"])]
            elif operation=="add_playlist":
                args=["playlists","items","add",target[1],"--video-id",target[0]]
            else:
                raise Stop("unknown_operation")
            yield args, tuple(descriptors)

    def plan(self):
        vid=self.known_video() or "pending____"
        intended=[("upload_video","video"),("set_thumbnail",vid)]
        intended += [("upload_captions",(vid,track)) for track in self.manifest["captions"]]
        intended += [("add_playlist",(vid,playlist)) for playlist in self.manifest["playlist_ids"]]
        previews=[]
        for op,target in intended:
            if op not in self.active["allowed_operations"]:
                continue
            with self.request_args(op,target,plan=True) as (args,fds):
                result=self.cli([*args,"--dry-run"],fds=fds)
            require(result.get("dry_run") is True,"unverified_dry_run")
            previews.append({"operation":op,"request":result})
        return {"status":"planned" if self.expired_seconds()>0 else "writes_blocked_expired",
                "profile":self.profile,"channel_id":self.binding["target_channel_id"],
                "seal_sha256":self.binding["seal_sha256"],
                "private":True,"notify_subscribers":False,"has_video":self.known_video() is not None,
                "operations":previews,
                "quota":{"upload_min":sum(row["operation"]=="upload_video" for row in previews),
                         "data_mutation_units":sum({"set_thumbnail":50,"upload_captions":400,"add_playlist":50}.get(x["operation"],0) for x in previews)}}

    def pending(self,key):
        if self.job.record(key,"ABANDONED"):
            raise Stop("abandoned_no_retry",code=7)
        ack=self.job.record(key,"ACK") or self.job.record(key,"RECONCILED")
        if ack:
            return ack
        intent=self.job.record(key,"INTENT")
        if intent:
            note=self.job.record(key,"ERROR")
            if note and note.get("effect")=="none":
                raise Stop("prior_rejection_no_retry",code=4)
            raise Stop("reconciliation_required",code=7)
        return None

    def mutation(self,operation,target,key,input_sha,*,baseline=None,resume=None):
        if resume is None:
            prior=self.pending(key)
            if prior:
                return prior
        self.check_write(operation,refresh_local=True)
        required={"upload_video":"video_id","upload_captions":"caption_id","add_playlist":"item_id",
                  "set_thumbnail":"video_id"}[operation]
        with self.request_args(operation,target,resume=resume) as (args,fds):
            plan=self.cli([*args,"--dry-run"],fds=fds)
            require(plan.get("dry_run") is True,"unverified_dry_run")
            self.check_write(operation,refresh_local=True)
            attempt=uuid.uuid4().hex
            self.job.append("INTENT",operation=operation,op_key=key,attempt_id=attempt,
                            input_sha256=input_sha,authorization_id=self.auth_id,
                            authorization_sha256=self.active_hash,baseline=baseline,wire_sha256=digest(canonical(plan)),
                            resumed=bool(resume))
            try:
                def guard():
                    try:
                        self.check_write(operation,refresh_local=False)
                    except (Stop,OSError,ValueError) as exc:
                        raise Stop("dispatch_authority_changed",code=10) from exc
                guard()
                result=self.cli(args,fds=fds,lock=self.lock,seconds=min(600,self.expired_seconds()),guard=guard)
                fields={}
                for field in ("video_id","caption_id","item_id","session_handle"):
                    if field in result:
                        pattern=VIDEO_ID if field=="video_id" else CAPTION_ID
                        require(isinstance(result[field],str) and pattern.fullmatch(result[field]),
                                "invalid_ack_identity",code=11)
                        fields[field]=result[field]
                require(required in fields,"missing_ack_identity",code=11)
                if operation=="upload_video":
                    fields["notify_subscribers"]=False
                return self.job.append("ACK",operation=operation,op_key=key,attempt_id=attempt,**fields)
            except Stop as exc:
                if exc.code==7 and required in exc.detail:
                    acknowledgement={required:exc.detail[required]}
                    if operation=="upload_video":
                        acknowledgement["notify_subscribers"]=False
                    self.job.append("ACK",operation=operation,op_key=key,attempt_id=attempt,
                                    **acknowledgement)
                self.job.append("ERROR",operation=operation,op_key=key,attempt_id=attempt,
                                error=exc.reason,effect="unknown" if exc.code in (7,10,11) else "none",
                                safe_ids=exc.detail)
                raise

    def read_video(self,vid):
        require(VIDEO_ID.fullmatch(vid),"invalid_video_id")
        data=self.cli(["videos","get",vid])
        rows=data.get("items",[])
        require(len(rows)==1 and rows[0].get("id")==vid,"video_readback_missing",code=4)
        v=rows[0]
        require(v.get("snippet",{}).get("channelId")==self.binding["target_channel_id"],
                "video_owner_mismatch",code=4)
        observed=privacy_result("private",v.get("status",{}).get("privacyStatus"))
        if not observed["matches"]:
            raise Stop("privacy_mismatch",code=4,detail={"video_id":vid,**observed})
        require("publishAt" not in v["status"],"video_schedule_mismatch",code=4)
        return v

    def read_thumbnail(self,vid,v):
        require(v.get("contentDetails",{}).get("hasCustomThumbnail") is True,
                "custom_thumbnail_readback_missing",code=4)
        destination=self.scratch/f"remote-{uuid.uuid4().hex}.png"
        receipt=self.cli(["thumbnails","fetch",vid,"--destination",str(destination)])
        expected,_=qr_evidence(self.frozen/self.manifest["thumbnail"]["path"])
        found,dimensions=qr_evidence(destination)
        require(found==expected and sha_file(destination)==receipt.get("sha256"),
                "thumbnail_marker_readback_mismatch",code=4)
        return {"provider_id":vid,"source_sha256":self.binding["thumbnail_sha256"],
                "rendition_sha256":receipt["sha256"],"dimensions":dimensions,
                "marker_sha256":found,"decoder":cv2.__version__}

    def caption_rows(self,vid):
        result=self.cli(["captions","list",vid,"--all-pages"])
        require(result.get("complete") is True,"caption_listing_incomplete",code=4)
        return result.get("items",[])

    def read_caption(self,vid,track,cid):
        candidates=[x for x in self.caption_rows(vid) if x.get("snippet",{}).get("language")==track["language"]
                    and x.get("snippet",{}).get("name")==track["name"]]
        require(len(candidates)==1 and candidates[0].get("id")==cid,"caption_identity_mismatch",code=4)
        status=candidates[0]["snippet"]
        require(status.get("videoId")==vid and status.get("trackKind")=="standard" and
                status.get("isDraft") is False and status.get("status")=="serving",
                "caption_readback_not_serving",code=4)
        fmt=Path(track["file"]["path"]).suffix
        destination=self.scratch/f"caption-{uuid.uuid4().hex}{fmt}"
        receipt=self.cli(["captions","download",cid,"--format",fmt[1:],"--destination",str(destination)])
        downloaded=destination.read_bytes()
        want=cues(local_bytes(self.frozen,track["file"]["path"]),fmt)
        got=cues(downloaded,fmt)
        require(want==got and receipt.get("sha256")==digest(downloaded),"caption_content_mismatch",code=4)
        return {"provider_id":cid,"source_sha256":track["file"]["sha256"],
                "download_sha256":digest(downloaded),"cue_sha256":digest(canonical(want)),
                "language":track["language"],"status":"serving"}

    def playlist_membership(self,vid,pid):
        page=self.cli(["playlists","list","--playlist-id",pid,"--all-pages"])
        items=page.get("items",[])
        require(page.get("complete") is True and len(items)==1 and items[0].get("id")==pid and
                items[0].get("snippet",{}).get("channelId")==self.binding["target_channel_id"] and
                items[0].get("status",{}).get("privacyStatus")=="private","playlist_owner_or_privacy_mismatch",code=4)
        rows=self.cli(["playlists","items","list",pid,"--video-id",vid,"--all-pages"])
        require(rows.get("complete") is True,"playlist_listing_incomplete",code=4)
        found=[]
        for obj in rows.get("items",[]):
            snippet=obj.get("snippet",{})
            require(snippet.get("playlistId")==pid and snippet.get("resourceId",{}).get("videoId")==vid and
                    isinstance(obj.get("id"),str) and CAPTION_ID.fullmatch(obj["id"]),"playlist_membership_mismatch",code=4)
            found.append(obj["id"])
        require(len(found)<=1,"duplicate_playlist_membership",code=4)
        return found

    def verify_event(self,key,operation,evidence):
        original=self.job.record(key,"INTENT")
        ack=self.job.record(key,"ACK") or self.job.record(key,"RECONCILED")
        proof={"op_key":key,"operation":operation,"intent_seq":original["seq"] if original else None,
               "ack_seq":ack["seq"] if ack else None,
               "evidence_origin":"provider_ack_and_get" if ack and ack["event"]=="ACK" else
                                 ("reconciled_and_get" if ack else "satisfied_preexisting"),**evidence}
        old=self.job.record(key,"VERIFIED")
        if not old:
            require(not self.finalized_receipt_present,"receipt_without_verification_history")
            old=self.job.append("VERIFIED",**proof)
        self.evidence[key]={**proof,"verified_seq":old["seq"]}

    def publish(self):
        prior_receipt=self.job.directory/"receipt.json"
        existing=prior_receipt.exists() or prior_receipt.is_symlink()
        self.finalized_receipt_present=existing
        m=self.manifest
        video_key=self.op_key("upload_video","video",m["delivery_video"]["sha256"])
        try:
            prior=self.pending(video_key)
        except Stop:
            confirmed=self.job.record(video_key,"RESUME_AUTHORIZED")
            active=self.job.record(video_key,"INTENT")
            if not confirmed or active["seq"]>=confirmed["seq"]:
                raise
            prior=self.mutation("upload_video","video",video_key,m["delivery_video"]["sha256"],
                                resume={"handle":confirmed["session_handle"],"offset":confirmed["offset"]})
        if not prior:
            require(not existing,"receipt_without_upload_ledger")
            prior=self.mutation("upload_video","video",video_key,m["delivery_video"]["sha256"])
            self.job.snapshot(self.binding,"VIDEO_KNOWN",prior["video_id"])
        vid=prior["video_id"]
        v=self.read_video(vid)
        processing=v.get("processingDetails",{}).get("processingStatus")
        if processing!="succeeded":
            require(processing not in ("failed","terminated"),"video_processing_failed",code=4)
            waited=self.cli(["videos","wait-processing",vid,"--timeout","120"])
            require(waited.get("processing_status")=="succeeded","video_processing_pending",code=4)
            v=self.read_video(vid)
        fields=matching_video(v,m,self.duration)
        self.verify_event(video_key,"upload_video",{"provider_id":vid,**fields,
                          "processing_status":v.get("processingDetails",{}).get("processingStatus"),
                          "notify_subscribers_request_evidence":prior.get("notify_subscribers") is False})
        key=self.op_key("set_thumbnail",vid,m["thumbnail"]["sha256"])
        ack=self.pending(key)
        if not ack:
            require(not existing,"receipt_without_thumbnail_ledger")
            marker,_=qr_evidence(self.frozen/m["thumbnail"]["path"])
            self.mutation("set_thumbnail",vid,key,m["thumbnail"]["sha256"],
                          baseline={"has_custom_thumbnail":v.get("contentDetails",{}).get("hasCustomThumbnail"),
                                    "source_marker_sha256":marker})
        v=self.read_video(vid)
        self.verify_event(key,"set_thumbnail",self.read_thumbnail(vid,v))
        for track in m["captions"]:
            key=self.op_key("upload_captions",[vid,track["language"],track["name"]],track["file"]["sha256"])
            ack=self.pending(key)
            if not ack:
                require(not existing,"receipt_without_caption_ledger")
                matches=[row for row in self.caption_rows(vid) if row.get("snippet",{}).get("language")==track["language"]
                         and row.get("snippet",{}).get("name")==track["name"]]
                require(not matches,"caption_already_exists_without_provenance",code=4)
                ack=self.mutation("upload_captions",(vid,track),key,track["file"]["sha256"],baseline={"matching_tracks":[]})
            self.verify_event(key,"upload_captions",self.read_caption(vid,track,ack["caption_id"]))
        for pid in m["playlist_ids"]:
            key=self.op_key("add_playlist",[pid,vid],m["delivery_video"]["sha256"])
            ack=self.pending(key)
            readback=self.playlist_membership(vid,pid)
            if not readback:
                require(not ack and not existing,"playlist_readback_missing",code=4)
                ack=self.mutation("add_playlist",(vid,pid),key,m["delivery_video"]["sha256"],baseline={"matching_items":[]})
                readback=self.playlist_membership(vid,pid)
            require(len(readback)==1 and (not ack or ack["item_id"]==readback[0]),
                    "playlist_readback_mismatch",code=4)
            self.verify_event(key,"add_playlist",{"provider_id":readback[0],"playlist_id":pid,"video_id":vid})
        latest=self.read_video(vid)
        require(latest.get("processingDetails",{}).get("processingStatus")=="succeeded","processing_readback_drift",code=4)
        matching_video(latest,m,self.duration)
        return self.finalize(vid,existing)

    def write_partial(self,state,reason):
        data={"schema_version":"1","overall":"unknown" if state=="RECONCILIATION_REQUIRED" else "partial",
              "video_id":self.known_video(),"channel_id":self.binding["target_channel_id"],"state":state,
              "partial_reasons":[reason],"resources":list(self.evidence.values())}
        atomic_write(self.job.directory/"youtube-readback.json",canonical(data))

    def finalize(self,vid,existing):
        readback={"schema_version":"1","overall":"complete","profile":self.profile,
                  "channel_id":self.binding["target_channel_id"],"video_id":vid,
                  "private":True,"publish_at":None,"notify_subscribers":False,
                  "resources":list(self.evidence.values()),"observed_at":self.clock().isoformat(),
                  "provenance":"owner_bound_independent_get_list_download"}
        filename=self.job.directory/"youtube-readback.json"
        receipt=self.job.directory/"receipt.json"
        if existing:
            raw=safe_read(filename)
            receipt_bytes=safe_read(receipt)
            saved=json_data(receipt_bytes)
            seq=saved["journal_seq"]
            require(saved["candidate"]==self.binding and saved["video_id"]==vid and
                    saved["readback_sha256"]==digest(raw) and type(seq) is int and
                    1<=seq<=len(self.job.rows) and saved["journal_sha256"]==digest(canonical(self.job.rows[seq-1])),
                    "receipt_readback_digest_mismatch")
            finalized=self.job.events("FINALIZED")
            if finalized:
                require(len(finalized)==1 and finalized[0]["seq"]==seq+1 and
                        finalized[0]["receipt_sha256"]==digest(receipt_bytes),"receipt_finalization_mismatch")
            else:
                require(seq==len(self.job.rows),"receipt_recovery_journal_conflict")
                self.job.append("FINALIZED",video_id=vid,receipt_sha256=digest(receipt_bytes))
            self.job.snapshot(self.binding,"COMPLETE",vid)
            return {"status":"already_published_noop","video_id":vid,"mutations":0}
        raw=canonical(readback)
        atomic_write(filename,raw)
        record={"schema_version":"1","candidate":self.binding,"video_id":vid,"privacy":"private",
                "processing_status":"succeeded","readback_sha256":digest(raw),"journal_sha256":self.job.tail,
                "journal_seq":len(self.job.rows),"authorization_id":self.auth_id,
                "authorization_sha256":self.active_hash,"completed_at":self.clock().isoformat(),
                "operations":list(self.evidence.values())}
        sealed=canonical(record)
        atomic_write(receipt,sealed,exclusive=True)
        self.job.append("FINALIZED",video_id=vid,receipt_sha256=digest(sealed))
        self.job.snapshot(self.binding,"COMPLETE",vid)
        return {"status":"published_private","video_id":vid,"receipt_sha256":digest(sealed)}

    def reconcile(self,record_id):
        latest={row["op_key"]:row for row in self.job.events("INTENT")}
        intents=[row for key,row in latest.items() if not
                 any(self.job.record(key,event) for event in ("ACK","RECONCILED","ABANDONED"))]
        if record_id is None:
            for intent in intents:
                error=self.job.record(intent["op_key"],"ERROR") or {}
                handle=error.get("safe_ids",{}).get("session_handle")
                if intent["operation"]=="upload_video" and handle:
                    status=self.cli(["videos","upload-status",handle])
                    if status.get("state")=="complete":
                        found=status.get("video_id","")
                        evidence=self.read_video(found)
                        matching_video(evidence,self.manifest,self.duration)
                        self.job.append("RECONCILED",operation="upload_video",op_key=intent["op_key"],
                                        attempt_id=intent["attempt_id"],video_id=found,notify_subscribers=False)
                        return {"status":"reconciled_upload","video_id":found,"mutations":0}
            return {"status":"reconciliation_required" if intents else "read_only",
                    "video_id":self.known_video(),"mutations":0}
        value,hashed=self.store.load("resolutions",record_id)
        for row in self.job.rows:
            if row.get("resolution_id")==record_id and row["event"] in (
                    "ABANDONED","RECONCILED","RESUME_AUTHORIZED"):
                require(row["resolution_sha256"]==hashed,"resolution_digest_mismatch")
                return {"status":row["decision"],"mutations":0}
        require(value["resolution_id"]==record_id and value["actor"]=="user" and
                value["episode_key"]==self.binding["episode_key"] and
                value["package_revision"]==self.binding["package_revision"] and
                value["seal_sha256"]==self.binding["seal_sha256"] and
                value["target_channel_id"]==self.binding["target_channel_id"] and
                value["expected_seq"]==len(self.job.rows) and value["expected_digest"]==self.job.tail,
                "resolution_binding_mismatch")
        intent=next((x for x in intents if x["op_key"]==value["op_key"] and x["attempt_id"]==value["attempt_id"]),None)
        require(intent is not None,"resolution_intent_mismatch")
        decision=value["decision"]
        good=value.get("observations",[])
        require(isinstance(good,list) and good and all(isinstance(x,dict) and x.get("source") and
                re.fullmatch(r"[a-f0-9]{64}",x.get("evidence_sha256","")) for x in good),
                "resolution_observation_required")
        event=None
        fields={}
        if decision=="abandoned_unknown_no_retry":
            event="ABANDONED"
            fields={"effect":"unknown"}
        elif decision=="abandoned_no_effect":
            error=self.job.record(intent["op_key"],"ERROR")
            require(error and error.get("effect")=="none","no_effect_is_not_proven")
            event="ABANDONED"
            fields={"effect":"none"}
        elif decision=="claimed":
            require(intent["operation"]=="upload_video" and any(x.get("source") in
                    ("provider_session_final","operator_first_hand_upload_record") and
                    x.get("video_id")==value.get("video_id") for x in good),"claim_requires_first_hand_identity")
            vid=value["video_id"]
            matching_video(self.read_video(vid),self.manifest,self.duration)
            event="RECONCILED"
            fields={"video_id":vid,"notify_subscribers":False}
        elif decision=="resume_confirmed_suffix":
            require(intent["operation"]=="upload_video","wrong_resolution_operation")
            handle,offset=value.get("session_handle"),value.get("confirmed_offset")
            error=self.job.record(intent["op_key"],"ERROR") or {}
            require(handle and handle==error.get("safe_ids",{}).get("session_handle"),"wrong_session_handle")
            probe=self.cli(["videos","upload-status",handle])
            require(probe.get("state")=="incomplete" and type(offset) is int and probe.get("offset")==offset,
                    "session_offset_unverified")
            event="RESUME_AUTHORIZED"
            fields={"session_handle":handle,"offset":offset}
        elif decision=="accept_observed_thumbnail":
            require(intent["operation"]=="set_thumbnail" and self.known_video() is not None and
                    intent.get("baseline",{}).get("has_custom_thumbnail") is False and
                    any(x.get("source")=="operator_isolated_write_window" for x in good),
                    "thumbnail_observation_does_not_prove_causality")
            vid=self.known_video()
            with tempfile.TemporaryDirectory(prefix=".reconcile-",dir=self.state_root) as temporary:
                self.scratch=Path(temporary)
                self.frozen=self.root
                fields=self.read_thumbnail(vid,self.read_video(vid))
            fields["video_id"]=vid
            event="RECONCILED"
        else:
            raise Stop("invalid_resolution_decision")
        self.job.append(event,operation=intent["operation"],op_key=intent["op_key"],
                        attempt_id=intent["attempt_id"],resolution_id=record_id,resolution_sha256=hashed,
                        decision=decision,**fields)
        self.job.snapshot(self.binding,"RECONCILED" if event=="RECONCILED" else
                          ("RESUME_AUTHORIZED" if event=="RESUME_AUTHORIZED" else decision.upper()),self.known_video())
        return {"status":decision,"mutations":0}


def settings():
    private=Path.home()/".config/ytpub"
    return private/"operator",private/"publish-registry",Path.home()/".local/state/ytpub/publish"


def arg_parser():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("plan","publish","reconcile"),required=True)
    parser.add_argument("--package",type=Path,required=True)
    parser.add_argument("--preview",type=Path)
    parser.add_argument("--profile",choices=("smoke-test",),required=True)
    parser.add_argument("--authorization",required=True,help="Registered operator authorization ID")
    parser.add_argument("--resolution",help="Registered operator resolution ID, reconcile only")
    parser.add_argument("--cache-backend",choices=("keychain","file"))
    return parser


def main(argv=None):
    os.umask(0o077)
    args=arg_parser().parse_args(argv)
    package=args.package.absolute()
    preview=(args.preview or package.parent/"video-release-preview.html").absolute()
    store,registry,state=settings()
    try:
        require(args.resolution is None or args.mode=="reconcile","resolution_requires_reconcile")
        controller=Controller(package,preview,args.profile,Client(CLI_ROOT,args.profile,args.cache_backend),
                              OperatorStore(store),registry,state,args.authorization)
        result=controller.execute(args.mode,resolution=args.resolution)
        print(canonical(result).decode())
        return 0
    except Stop as exc:
        print(canonical({"status":"blocked","error_code":exc.reason,"safe_ids":exc.detail}).decode(),file=sys.stderr)
        return exc.code
    except (Invalid,ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError):
        print('{"status":"blocked","error_code":"local_input_or_runtime_failure"}',file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
