"""Durable local intent and acknowledgement ledger."""

import os
from pathlib import Path

from auth_store import Stop, require, safe_private, safe_read, timestamp
from package import atomic_write, canonical, digest, json_data, sync_directory


class Journal:
    def __init__(self,directory,*,create=False):
        self.directory=Path(directory)
        safe_private(self.directory,create=create)
        self.file=self.directory/"journal.jsonl"
        self.rows=[]
        if self.file.exists() or self.file.is_symlink():
            data=safe_read(self.file)
            require(data.endswith(b"\n"),"journal_incomplete_last_line")
            for line in data.splitlines():
                row=json_data(line)
                require(row["seq"]==len(self.rows)+1 and row["prev_entry_sha256"]==self.tail and
                        line==canonical(row),"journal_chain_drift")
                self.rows.append(row)

    @property
    def tail(self):
        return digest(canonical(self.rows[-1])) if self.rows else None

    def append(self,event,**data):
        row={"seq":len(self.rows)+1,"prev_entry_sha256":self.tail,"event":event,
             "at":timestamp(),**data}
        flags=os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW
        initial=not self.rows
        if initial:
            flags|=os.O_CREAT|os.O_EXCL
        fd=os.open(self.file,flags,0o600)
        with os.fdopen(fd,"ab") as file:
            file.write(canonical(row)+b"\n")
            file.flush()
            os.fsync(file.fileno())
        if initial:
            sync_directory(self.directory)
        self.rows.append(row)
        return row

    def record(self,key,event):
        return next((r for r in reversed(self.rows) if r["event"]==event and r.get("op_key")==key),None)

    def events(self,event):
        return [r for r in self.rows if r["event"]==event]

    def snapshot(self, binding, state, value=None):
        result={"schema_version":"1","state":state,"candidate":binding,"last_seq":len(self.rows),
                "journal_sha256":self.tail,"video_id":value}
        atomic_write(self.directory/"state.json",canonical(result))
        return result

    def ensure_snapshot(self):
        path=self.directory/"state.json"
        if path.exists():
            snapshot=json_data(safe_read(path))
            seq=snapshot.get("last_seq",-1)
            require(type(seq) is int and 1<=seq<=len(self.rows),"snapshot_ahead_of_journal")
            require(digest(canonical(self.rows[seq-1]))==snapshot.get("journal_sha256"),
                    "snapshot_journal_mismatch")
