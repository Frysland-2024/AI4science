#!/usr/bin/env python3
"""Build an optional, verified, portable full V11 Validation panel ZIP.

Source must be the locally completed six-profile, 23245 unique-parent
fixed Validation cache. Does not train, modify frozen source data, or
touch the locked Test/RRUFF. Optional ZIP is extracted by start_server.sh
into the exact canonical HPO study directory on Linux.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile

PROFILES=("ood_shift_negative","ood_shift_positive","ood_broadening",
          "ood_noise","ood_background","ood_texture")
ARCHIVE_PREFIX="AI4science/server_runs/v11_a0_js_optuna/validation_panels_v11/"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(2**20),b""):
            h.update(chunk)
    return h.hexdigest()

def package(panel_dir: Path, dest: Path, *, expected_parents:int=23245) -> dict:
    import numpy as np
    panel_dir=panel_dir.resolve()
    dest=dest.resolve()
    index_path=panel_dir/"panel_index.json"
    index=json.loads(index_path.read_text(encoding="utf-8"))
    identity=index.get("identity",{})
    if (identity.get("version")!="v11-full-validation-dual-view-cache-v1"
        or identity.get("parent_count")!=expected_parents
        or tuple(identity.get("profiles",[]))!=PROFILES
        or sorted(index.get("entries",{}))!=sorted(PROFILES)):
        raise ValueError("Frozen Validation panel identity is incomplete/changed")
    selected=[]
    for profile in PROFILES:
        entry=index["entries"][profile]
        if entry.get("n_parents")!=expected_parents or entry.get("profile")!=profile:
            raise ValueError(f"Wrong frozen OOD panel contract: {profile}")
        expected_hashes=entry.get("sha256")
        if not isinstance(expected_hashes,list) or len(expected_hashes)!=2:
            raise ValueError(f"Missing V11 paired array SHA256: {profile}")
        for view,expected_hash in zip(("first","second"),expected_hashes):
            path=panel_dir/(profile+"."+view+".npy")
            if not path.is_file() or sha(path)!=expected_hash:
                raise ValueError(f"Corrupt frozen panel SHA: {path}")
            obj=np.load(path,mmap_mode="r",allow_pickle=False)
            if obj.shape!=(expected_parents,3501) or obj.dtype!=np.float32:
                raise ValueError(f"Wrong frozen panel shape/dtype: {path}")
            del obj
            selected.append(path)
    # This is an optional archive, not a replacement for a needed structure ZIP.
    # Put the manifest LAST so interrupted extraction does not appear complete.
    temp=dest.with_name(dest.name+".partial")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1,allowZip64=True) as z:
        for path in selected:
            z.write(path,ARCHIVE_PREFIX+path.name)
            print(f"PACKED {path.name}",flush=True)
        z.write(index_path,ARCHIVE_PREFIX+"panel_index.json")
    with zipfile.ZipFile(temp) as z:
        expected_names={ARCHIVE_PREFIX+p.name for p in selected}
        expected_names.add(ARCHIVE_PREFIX+"panel_index.json")
        if set(z.namelist())!=expected_names:
            raise ValueError("Validation bundle archive member mismatch")
        damaged=z.testzip()
        if damaged:
            raise ValueError(f"Validation bundle CRC error: {damaged}")
    os.replace(temp,dest)
    return {
        "status":"PASS","source_parent_count":expected_parents,"source_profiles":list(PROFILES),
        "zip_file":dest.name,"zip_bytes":dest.stat().st_size,"zip_sha256":sha(dest),
        "original_index_sha256":sha(index_path),
        "original_uncompressed_bytes":sum(p.stat().st_size for p in selected),
    }

def update_private_kit(kit:Path,archive:Path,metadata:dict)->None:
    manifest_path=kit/"bundle_manifest.json"
    data=json.loads(manifest_path.read_text(encoding="utf-8"))
    data["archives"][archive.name]={
        "size_bytes":archive.stat().st_size,"sha256":metadata["zip_sha256"]
    }
    data["optional_frozen_validation_bundle"]="23,245 independent parents, 6 profiles, reusable on Linux if source identity hashes match; NOT Test/RRUFF"
    data["frozen_validation_panel_index_sha256"]=metadata["original_index_sha256"]
    lines=[item["sha256"]+"  "+name+"\n" for name,item in data["archives"].items()]
    lines.extend(
        data["scripts"][name]["sha256"]+"  "+name+"\n"
        for name in ("start_server.sh","verify_source_snapshot.py","payload_contract.py")
    )
    manifest_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (kit/"SHA256SUMS.txt").write_bytes("".join(lines).encode("ascii"))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--panels",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    p.add_argument("--expected-parents",type=int,default=23245)
    p.add_argument("--update-kit",type=Path)
    args=p.parse_args()
    result=package(args.panels,args.destination,expected_parents=args.expected_parents)
    if args.update_kit is not None:
        kit=args.update_kit.resolve()
        if args.destination.resolve().parent!=kit:
            raise ValueError("Optional validation ZIP must be placed in the private kit directory")
        update_private_kit(kit,args.destination.resolve(),result)
    print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__":
    main()
