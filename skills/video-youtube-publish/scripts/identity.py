"""Inspect the exact CLI checkout and local contract runtime without credentials."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
CONTRACT=HERE.parents[1]/"video-release-contract"
sys.path.insert(0,str(CONTRACT/"scripts"))
from package import bundle_files, canonical, digest, json_data, runtime_inputs, sha_file


def environment(executable, lock, name, *, verify=False):
    args=[str(executable),"-I","-B",str(CONTRACT/"scripts/dependencies.py"),str(lock),name]
    if verify:
        args.append("--verify")
    completed=subprocess.run(args,capture_output=True,timeout=120)
    if completed.returncode:
        raise ValueError("Locked dependency identity failed.")
    return json_data(completed.stdout)


def entries(files):
    return [[name,sha_file(path)] for name,path in files]


def manifest(block):
    rows=sorted(block,key=lambda x:x[0].encode("utf-8"))
    return digest(canonical(rows)),rows


def cli_identity(root,*,verify=False):
    python=root/".venv/bin/python"
    checked=subprocess.run([str(python),"-I","-B","-c","import ytpub.cli; print(ytpub.cli.__file__)"],
                           capture_output=True,timeout=15)
    origin=Path(checked.stdout.decode().strip())
    if checked.returncode or not origin.samefile(root/"src/ytpub/cli.py"):
        raise ValueError("The CLI is not installed from the approved checkout.")
    records=entries(runtime_inputs(root/"src/ytpub","cli/src/ytpub")+
                    [("cli/pyproject.toml",root/"pyproject.toml"),("cli/uv.lock",root/"uv.lock"),
                     ("runtime/python",python.resolve(strict=True))])
    records.append(["runtime/cli-deps.lock",
                    digest(canonical(environment(python,root/"uv.lock","ytpub",verify=verify)))])
    return manifest(records)


def contract_identity(*,verify=False):
    from dependencies import locked_manifest
    records=entries(bundle_files())
    records.append(["runtime/contract-deps.lock",
                    digest(canonical(locked_manifest(CONTRACT/"uv.lock","video-release-contract",verify=verify)))])
    return manifest(records)


def command():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cli-root",type=Path,required=True)
    parser.add_argument("--contract-root",type=Path,default=CONTRACT)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    if not args.contract_root.samefile(CONTRACT):
        parser.error("The contract must be the paired local Skill.")
    cli_hash, cli_files=cli_identity(args.cli_root.resolve(),verify=True)
    bundle_hash, bundle_files_value=contract_identity(verify=True)
    print(canonical({"cli_identity_sha256":cli_hash,"contract_bundle_sha256":bundle_hash,
                     "cli_inputs":cli_files,"contract_inputs":bundle_files_value}).decode())
    return 0


if __name__=="__main__":
    raise SystemExit(command())
