"""Local operator ledger. Real approval requires an interactive operator."""

import contextlib
import fcntl
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from identity import canonical, digest
from package import atomic_write, clean_identifier, json_data

HOUR = 3600
KEY = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}")
SCHEMA = Path(__file__).resolve().parents[1]/"references/authorization.schema.json"
OPS = {"upload_video","set_thumbnail","upload_captions","add_playlist","readback"}
PARAMETERS = ("episode_key","channel_profile","target_channel_id","package_revision",
              "manifest_sha256","payload_sha256","video_sha256","thumbnail_sha256",
              "captions_sha256","seal_sha256","contract_bundle_sha256","cli_identity_sha256",
              "playlist_ids","oauth_binding_sha256","target_privacy_status","publish_at",
              "notify_subscribers","mode")


class Stop(Exception):
    def __init__(self, reason, *, code=2, detail=None):
        super().__init__(reason)
        self.reason,self.code,self.detail=reason,code,detail or {}


def require(condition, reason, *, code=2):
    if not condition:
        raise Stop(reason,code=code)


def utc(value):
    require(isinstance(value,str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z",value),
            "invalid_utc")
    try:
        return datetime.fromisoformat(value[:-1]+"+00:00")
    except ValueError as exc:
        raise Stop("invalid_utc") from exc


def timestamp(when=None):
    return (when or datetime.now(timezone.utc)).isoformat().replace("+00:00","Z")


def validate_auth(value):
    valid=Draft202012Validator(json_data(SCHEMA.read_bytes()),format_checker=FormatChecker())
    require(valid.is_valid(value),"invalid_authorization_schema")
    for k in ("source_ref","authorization_id","episode_key","channel_profile","target_channel_id","expires_at"):
        require(clean_identifier(value[k]),"invalid_authorization_identifier")
    require(all(clean_identifier(k) for k in value["captions_sha256"]),"invalid_authorization_language")
    require(not value["revoked"],"authorization_revoked")
    expires=utc(value["expires_at"])
    if value["authorized_at"] is not None:
        require(utc(value["authorized_at"])<expires,"invalid_authorization_dates")
    return value


def safe_private(path, *, create=False):
    require(path.is_absolute() and not any(x in {".git","Life-OS",".."} for x in path.parts),
            "private_state_under_vault_or_git")
    if create:
        path.mkdir(mode=0o700,parents=True,exist_ok=True)
    for parent in path.parents:
        st=parent.lstat()
        require(stat.S_ISDIR(st.st_mode) and st.st_uid in (0,os.getuid()) and
                (not st.st_mode & 0o022 or bool(st.st_mode & stat.S_ISVTX)),"unsafe_state_parent")
    st=path.lstat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid==os.getuid() and stat.S_IMODE(st.st_mode)==0o700,
            "unsafe_private_directory")
    for directory in (path,*path.parents):
        marker=directory/".git"
        require(not marker.exists() and not marker.is_symlink(),"private_state_under_vault_or_git")


def safe_read(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,"rb") as f:
        st=os.fstat(f.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and st.st_nlink==1 and
                stat.S_IMODE(st.st_mode)==0o600 and st.st_size<=8_000_000,"unsafe_private_record")
        return f.read()


@contextlib.contextmanager
def lock_file(path, *, shared=False):
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        st=os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and st.st_nlink==1 and
                stat.S_IMODE(st.st_mode)==0o600,"unsafe_lock")
        fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX)|fcntl.LOCK_NB)
        yield fd
    except BlockingIOError as exc:
        raise Stop("job_locked") from exc
    finally:
        # Closing without explicit LOCK_UN leaves an inherited OFD locked until its child closes.
        os.close(fd)


class OperatorStore:
    def __init__(self,root):
        self.root=Path(root)

    def prepare(self):
        safe_private(self.root,create=True)
        for path in ("authorizations","revoked","resolutions"):
            safe_private(self.root/path,create=True)

    def _index(self, kind):
        p=self.root/f"{kind}-index.json"
        if p.exists() or p.is_symlink():
            index=json_data(safe_read(p))
            require(isinstance(index,dict),"invalid_operator_index")
            return index
        return {}

    def store(self,kind,key,value):
        require(kind in ("authorizations","resolutions") and KEY.fullmatch(key),"invalid_operator_record")
        self.prepare()
        raw=canonical(value)
        with lock_file(self.root/"operator.lock"):
            index=self._index(kind)
            require(key not in index,"operator_record_already_exists")
            if kind=="authorizations" and value.get("supersedes"):
                predecessor=value["supersedes"]
                require(index.get(predecessor["authorization_id"])==predecessor["authorization_sha256"],
                        "invalid_successor_predecessor")
                for old_key,checksum in index.items():
                    require(KEY.fullmatch(old_key),"invalid_operator_index")
                    raw_record=safe_read(self.root/kind/f"{old_key}.json")
                    require(digest(raw_record)==checksum,"operator_index_digest_mismatch")
                    require(json_data(raw_record).get("supersedes")!=predecessor,"authorization_branch_forbidden")
            atomic_write(self.root/kind/f"{key}.json",raw,exclusive=True)
            index[key]=digest(raw)
            atomic_write(self.root/f"{kind}-index.json",canonical(index))
        return index[key]

    def load(self,kind,key):
        require(isinstance(key,str) and KEY.fullmatch(key),"invalid_authorization_id")
        require(self.root.exists() or self.root.is_symlink(),"operator_record_not_registered")
        safe_private(self.root)
        safe_private(self.root/kind)
        index=self._index(kind)
        require(key in index,"operator_record_not_registered")
        raw=safe_read(self.root/kind/f"{key}.json")
        hashed=digest(raw)
        require(index[key]==hashed,"operator_index_digest_mismatch")
        return json_data(raw),hashed

    def revoke(self,key):
        self.load("authorizations",key)
        safe_private(self.root/"revoked")
        with lock_file(self.root/"operator.lock"):
            p=self.root/"revoked"/key
            if p.exists() and not p.is_symlink():
                return
            atomic_write(p,canonical({"revoked_at":timestamp()}),exclusive=True)

    def chain(self,key,binding,now):
        chain=[]
        while key is not None:
            require(len(chain)<32 and key not in {record["authorization_id"] for record,_ in chain},
                    "invalid_authorization_chain")
            value,hashed=self.load("authorizations",key)
            validate_auth(value)
            require(value["authorization_id"]==key and
                    not (self.root/"revoked"/key).exists() and not (self.root/"revoked"/key).is_symlink(),
                    "authorization_revoked_or_mismatched")
            require(all(value[k]==binding[k] for k in PARAMETERS),"authorization_binding_mismatch")
            require(value["authorized_at"] is None or utc(value["authorized_at"])<=now,"authorization_not_yet_valid")
            if chain:
                child,_=chain[-1]
                require(child["supersedes"]["authorization_sha256"]==hashed and
                        set(child["allowed_operations"])<=set(value["allowed_operations"]) and
                        (child["authorized_at"] is None or value["authorized_at"] is None or
                         utc(child["authorized_at"])>=utc(value["authorized_at"])),
                        "successor_expands_or_changes_authority")
            chain.append((value,hashed))
            predecessor=value["supersedes"]
            key=predecessor["authorization_id"] if predecessor else None
        return list(reversed(chain))
