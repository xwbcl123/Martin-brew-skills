"""Reproducible identity for a locked virtual environment."""

import base64
import hashlib
import importlib.metadata
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

DEV = {"pytest", "iniconfig", "pluggy", "pygments", "packaging"}
normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()


def locked_manifest(lock, project, *, verify=False):
    packages = tomllib.loads(Path(lock).read_text(encoding="utf-8"))["package"]
    versions = {(normalize(p["name"]),p["version"]):p for p in packages}
    tags = {tag:i for i,tag in enumerate(sys_tags())}
    result=[]
    prefix=Path(sys.prefix).resolve()
    for dist in importlib.metadata.distributions():
        name, version = normalize(dist.metadata["Name"]), dist.version
        if name in {normalize(project), "pip", "setuptools", "wheel"}:
            continue
        entry=versions.get((name,version))
        if entry is None:
            if name in DEV:
                continue
            raise ValueError("installed dependency is absent from the lock")
        wheels=[]
        for wheel in entry.get("wheels",[]):
            filename=unquote(urlsplit(wheel["url"]).path.rsplit("/",1)[-1])
            _,_,_,wheel_tags=parse_wheel_filename(filename)
            indexes=[tags[tag] for tag in wheel_tags if tag in tags]
            if indexes:
                wheels.append((min(indexes),filename,wheel["hash"].removeprefix("sha256:")))
        if not wheels:
            raise ValueError("dependency has no compatible locked wheel")
        actual_tags=set()
        for line in (dist.read_text("WHEEL") or "").splitlines():
            if line.startswith("Tag: "):
                actual_tags.add(line[5:])
        selected=[row for row in wheels if actual_tags.intersection(
            str(x) for x in parse_wheel_filename(row[1])[3])]
        if not selected:
            raise ValueError("installed wheel tags differ from the lock")
        if verify:
            for item in dist.files or ():
                if not item.hash:
                    continue
                path=dist.locate_file(item).resolve()
                if not path.is_relative_to(prefix):
                    raise ValueError("dependency RECORD points outside the environment")
                with path.open("rb") as stream:
                    raw=hashlib.file_digest(stream,item.hash.mode).digest()
                actual=base64.urlsafe_b64encode(raw).decode().rstrip("=")
                if actual != item.hash.value:
                    raise ValueError("installed wheel file differs from RECORD")
        result.append([name,version,min(selected)[2]])
    return sorted(result)


if __name__=="__main__":
    print(json.dumps(locked_manifest(sys.argv[1],sys.argv[2],verify="--verify" in sys.argv[3:]),
                     separators=(",",":"),ensure_ascii=False))
