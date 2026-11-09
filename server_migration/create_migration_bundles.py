#!/usr/bin/env python3
"""Prepare private reproducible Linux migration archives; never mutate experiment inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import time
import zipfile
from payload_contract import (
    PAYLOAD_CONTRACT_VERSION,PAYLOAD_MANIFEST_MEMBER,PAYLOAD_REQUIRED_FILES,
)

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DEST=ROOT/"_local"/"server_migration_20261103"
DEFAULT_SOURCE=Path(r"D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103")
EXCLUDE={"__pycache__", ".pytest_cache", ".git", ".venvs", ".mypy_cache", "data", "outputs"}
NO_EXT={".ckpt",".npz",".npy",".db",".sqlite",".pt",".pth",".pkl",".zip",".tar",".gz",".csv"}
EXPECTED={"train":108483,"validation":23246,"test":23246}
def sha256(p):
    digest=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()
def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args],text=True,errors="replace").strip()
def included(root):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in EXCLUDE for part in p.parts):continue
        if p.suffix.lower() in NO_EXT or p.stat().st_size>12*1024*1024:continue
        yield p
def main():
    parser=argparse.ArgumentParser(description="Build private migration bundles from this worktree only")
    parser.add_argument("--destination",type=Path,default=DEFAULT_DEST)
    parser.add_argument("--source-splits",type=Path,default=DEFAULT_SOURCE)
    args=parser.parse_args()
    DEST=args.destination.resolve()
    SOURCE=args.source_splits.resolve()
    try:
        relative_destination=DEST.relative_to(ROOT.resolve())
    except ValueError as error:
        raise RuntimeError("Bundle destination must stay inside the current Git worktree") from error
    if not relative_destination.parts:
        raise RuntimeError("Refusing to use the Git worktree root as the bundle destination")
    PROJECT=ROOT/"xrd_robustness"
    PREPROCESSED=SOURCE.parent
    DEST.mkdir(parents=True,exist_ok=True)
    data=json.loads((SOURCE/"delivery_validation.json").read_text(encoding="utf-8"))
    assert data["status"]=="passed"
    assert data["material_id_records"]==154975 and data["parent_structure_groups"]==154968
    assert data["row_counts_by_split"]==EXPECTED
    print("Verifying source split SHA256 against frozen delivery_validation...")
    for filename,digest in data["sha256"].items():
        result=sha256(SOURCE/filename)
        if result!=digest:raise RuntimeError(f"upstream split hash mismatch: {filename}")
        print("VERIFIED",filename,(SOURCE/filename).stat().st_size)
    files={}
    for sub in ("src","scripts","configs","tests"):
        for p in included(PROJECT/sub):
            files[p]=p.relative_to(ROOT).as_posix()
    for name in ("pyproject.toml","README.md"):
        p=PROJECT/name
        if p.is_file():files[p]=p.relative_to(ROOT).as_posix()
    for name in ("README.md","AGENTS.md","LICENSE","THIRD_PARTY_NOTICES.md","CITATION.md"):
        p=ROOT/name
        if p.is_file():files[p]=p.relative_to(ROOT).as_posix()
    for name in ("CURRENT_STATE.md","PROJECT_HISTORY.md","SIMULATOR_V11_READINESS_20261103.md","STRUCTURE_LIBRARY_154975_TRAINING_ADAPTER.md","PXRD_CNN11_V10_NUMERICAL_DECISION_20261103.md","ISSUE61_LOCAL_PREFLIGHT_20261109.md"):
        p=ROOT/"docs"/name
        if p.is_file():files[p]=p.relative_to(ROOT).as_posix()
    for p in sorted((ROOT/"_local"/"resnet_joint_20261103").glob("*.py")):
        files[p]="reference_windows_resnet_joint/"+p.name
    for p in sorted((ROOT/"_local"/"resnet_joint_20261103"/"protocols").glob("*.json")):
        files[p]="reference_windows_resnet_joint/protocols/"+p.name
    for name in ("verify_payload.py","verify_peak_cache.py","one_click_v11.py","v11_prefetch.py","smoke_prefetch.py","start_server.sh","preflight.sh","build_peak_tables.sh","setup_linux.sh","README.md","payload_contract.py","verify_source_snapshot.py","create_migration_bundles.py"):
        p=ROOT/"server_migration"/name
        if not p.is_file():raise RuntimeError(f"Missing current-worktree migration source: {p}")
        files[p]=p.relative_to(ROOT).as_posix()
    for p in sorted((ROOT/"server_migration"/"tests").glob("test_*.py")):
        files[p]=p.relative_to(ROOT).as_posix()
    portable_doc=ROOT/"docs"/"PXRD_SERVER_MIGRATION_V11_ONECLICK_20261103.md"
    if portable_doc.is_file():
        files[portable_doc]="docs/PXRD_SERVER_MIGRATION_V11_ONECLICK_20261103.md"
    for name in ("acceptance_rerun_20261103.json","merged_154975_precompute_20261103.json","merged_154975_sample_20261103.json"):
        p=PROJECT/"reports"/"simulator_v11"/name
        if p.is_file():files[p]=p.relative_to(ROOT).as_posix()
    for name in ("summary.json","README.md"):
        p=ROOT/"_local"/"resnet_joint_20261103"/name
        if p.is_file():files[p]="reference_windows_resnet_joint/"+name
    code_path=DEST/"source_snapshot.zip"
    manifest_files={
        "AI4science/"+rel:sha256(file)
        for file,rel in sorted(files.items(),key=lambda item:item[1])
    }
    source_manifest={
        "schema":"pxrd-v11-source-snapshot-v1",
        "contract_version":PAYLOAD_CONTRACT_VERSION,
        "required_files":list(PAYLOAD_REQUIRED_FILES),
        "files":manifest_files,
        "source_git_commit":git("rev-parse","HEAD"),
    }
    with zipfile.ZipFile(code_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as zf:
        for file,rel in sorted(files.items(),key=lambda item:item[1]):
            zf.write(file,"AI4science/"+rel)
        zf.writestr(PAYLOAD_MANIFEST_MEMBER,json.dumps(source_manifest,sort_keys=True,indent=2)+"\n")
    data_files=sorted(SOURCE.glob("*"))
    audit_file=PREPROCESSED/"screening_report.md"
    if audit_file.is_file():data_files.append(audit_file)
    archive_path=DEST/"structure_shards.zip"
    with zipfile.ZipFile(archive_path,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as zf:
        for file in data_files:
            if not file.is_file():continue
            name=("source_screening_report.md" if file==audit_file else file.name)
            zf.write(file,"AI4science/structure_library/merged_154975_parent_split_20261103/"+name)
    cache_root=PROJECT/"data"/"merged_154975_v11"
    cache_zip=DEST/"peak_cache_bundle.zip"
    entries=[]
    for split in ("train","validation","test"):
        source=cache_root/split
        entries.extend(source.glob("manifests/*"))
        entries.extend(source.glob("mp_processed/peak_tables_v7_reflection/*.npz"))
    entries.extend(cache_root.glob("training_records.*"))
    files_only=sorted(p for p in entries if p.is_file())
    if len(files_only)<154980:
        raise RuntimeError(f"Incomplete cache files: found only {len(files_only)}")
    print("Archiving exact 154975 peak caches and runner manifest:",len(files_only),flush=True)
    with zipfile.ZipFile(cache_zip,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as zf:
        for index,file in enumerate(files_only,1):
            zf.write(file,"AI4science/"+file.relative_to(ROOT).as_posix())
            if index%30000==0:print("cache files archived",index,"/",len(files_only),flush=True)
    winner=PROJECT/"outputs"/"resnet_joint_convergence_20261103"/"A0_R1"/"A0_R1"/"seed_20260711"
    reference_path=DEST/"a0_reference_checkpoint.zip"
    ckpt=winner/"best.ckpt"
    if not ckpt.is_file():raise RuntimeError("Missing V10 A0_R1 chosen reference checkpoint")
    selected=ROOT/"_local"/"resnet_joint_20261103"/"summary.json"
    ref_files=[ckpt, winner/"resolved_config.json", winner/"validation_history.json", selected]
    with zipfile.ZipFile(reference_path,"w",compression=zipfile.ZIP_STORED,allowZip64=True) as zf:
        for file in ref_files:
            if not file.is_file():raise RuntimeError(f"Missing reference evidence {file}")
            zf.write(file,"AI4science/reference_a0_r1_v10/"+file.name)
    status=json.loads((ROOT/"_local"/"resnet_joint_20261103"/"campaign_state.json").read_text(encoding="utf-8"))
    payload={
        "schema_version":"pxrd-server-migration-audit-v1",
        "source_root":str(ROOT),
        "created_local_time":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_git_branch":git("branch","--show-current"),
        "source_git_commit":git("rev-parse","HEAD"),
        "source_git_status_lines":git("status","--short").splitlines(),
        "source_is_dirty":bool(git("status","--porcelain")),
        "data_original_source_drive":"D:/AI4science_external_data/pxrd_scale_sources_20261103/processed/merged_154975_parent_split_20261103",
        "dataset_ids":154975,
        "dataset_parent_groups":154968,
        "dataset_split_counts":EXPECTED,
        "dataset_integrity_source":"delivery_validation.json",
        "active_campaign_state_at_snapshot":status,
        "archives":{},
        "large_data_and_checkpoints_excluded_from_source_snapshot":True,
        "server_cuda_compatibility_not_tested":True,
         "full_154975_peak_caches_not_precomputed":False,
        "hpo_validation":"ALL 23245 frozen unique Validation parents, no 896-parent subset; profiles SHA-indexed",
        "final_model_training_runner_not_frozen":True
    }
    for label,path in (("source_snapshot.zip",code_path),("structure_shards.zip",archive_path),("peak_cache_bundle.zip",cache_zip),("a0_reference_checkpoint.zip",reference_path)):
        payload["archives"][label]={"size_bytes":path.stat().st_size,"sha256":sha256(path)}
    (DEST/"bundle_manifest.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    launcher=DEST/"start_server.sh"
    verifier=DEST/"verify_source_snapshot.py"
    payload_contract=DEST/"payload_contract.py"
    shutil.copy2(ROOT/"server_migration"/"start_server.sh",launcher)
    shutil.copy2(ROOT/"server_migration"/"verify_source_snapshot.py",verifier)
    shutil.copy2(ROOT/"server_migration"/"payload_contract.py",payload_contract)
    payload["scripts"]={
        "start_server.sh":{"sha256":sha256(launcher),"size_bytes":launcher.stat().st_size},
        "verify_source_snapshot.py":{"sha256":sha256(verifier),"size_bytes":verifier.stat().st_size},
        "payload_contract.py":{"sha256":sha256(payload_contract),"size_bytes":payload_contract.stat().st_size},
    }
    (DEST/"bundle_manifest.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=[entry["sha256"]+"  "+name+"\n" for name,entry in payload["archives"].items()]
    lines.append(payload["scripts"]["start_server.sh"]["sha256"]+"  start_server.sh\n")
    lines.append(payload["scripts"]["verify_source_snapshot.py"]["sha256"]+"  verify_source_snapshot.py\n")
    lines.append(payload["scripts"]["payload_contract.py"]["sha256"]+"  payload_contract.py\n")
    (DEST/"SHA256SUMS.txt").write_bytes("".join(lines).encode("ascii"))
    print(json.dumps({"archive_sha256":payload["archives"],"code_files":len(files),"snapshot_campaign":status,"source_dirty":payload["source_is_dirty"]},indent=2))
if __name__=="__main__":main()
