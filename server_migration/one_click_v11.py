#!/usr/bin/env python3
"""Portable V11/154975 PXRD ResNet + Dynamic JS focused science pipeline.

No locked Test/RRUFF access; old-data V10 supervisor is deliberately not used.
Use plan/smoke locally, and --mode run only on a CUDA Linux machine.
"""
from __future__ import annotations
import argparse
import csv
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import threading
import time
from collections import defaultdict
from dataclasses import asdict
from v11_prefetch import V11PairPrefetchPool, iter_prefetched_batches, enqueue_train_lookahead
from train_microbatch import paired_optimizer_step
from payload_contract import PAYLOAD_CONTRACT_VERSION

ROOT=Path(os.environ.get("AI4SCIENCE_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
XRD=ROOT/"xrd_robustness"
sys.path.insert(0,str(XRD/"src"))

# Two science choices: same-parent JS strength and interpretable PXRD peak-preserving
# ResNet architecture. Keep the historically supported optimizer recipe fixed.
V11_FIXED_OPTIMIZER={"learning_rate":2e-4,"weight_decay":1e-4,
                     "scheduler":"cosine_5pct_floor"}
V11_ARCHITECTURES={
    "A0":((4,4,4),9),  # Historical ML4pXRDs source-style baseline.
    "A1":((4,2,4),9),  # V10 selective downsampling.
    "A2":((4,2,4),5),  # V10 selective downsampling + narrower kernel.
    "A3":((4,4,4),5),  # Missing kernel-only control for clean interpretation.
}

def resolve_v11_trial_params(params):
    """Restrict Optuna to JS lambda + discrete PXRD architecture presets."""
    if set(params)!={"lambda_js","architecture"}:
        raise ValueError("V11 trials must contain only lambda_js and architecture")
    architecture=params["architecture"]
    if architecture not in V11_ARCHITECTURES:
        raise ValueError(f"Unknown PXRD architecture preset: {architecture}")
    weight=float(params["lambda_js"])
    if not math.isfinite(weight) or not 15.0<=weight<=120.0:
        raise ValueError("V11 lambda_js must be finite and in the frozen 15..120 range")
    return {**V11_FIXED_OPTIMIZER,"lambda_js":weight,"architecture":architecture}

def v11_model_config(params, config_type):
    arch=resolve_v11_trial_params(params)["architecture"]
    strides,kernel=V11_ARCHITECTURES[arch]
    return config_type(model_id="18",stage_transition_strides=strides,
                       residual_kernel_size=kernel)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

def canonical_digest(value):
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    ).hexdigest()

_ACTIVE_LOCKS=set()
_ACTIVE_LOCKS_GUARD=threading.Lock()

@contextmanager
def exclusive_file_lock(path):
    """Cross-process, fail-fast lock that is released automatically on exit/crash."""
    path=Path(path).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    key=str(path)
    with _ACTIVE_LOCKS_GUARD:
        if key in _ACTIVE_LOCKS:
            raise RuntimeError(f"V11 lock is already held in this process: {path}")
        _ACTIVE_LOCKS.add(key)
    stream=None
    locked=False
    try:
        stream=path.open("a+b")
        if os.name=="nt":
            import msvcrt
            stream.seek(0,os.SEEK_END)
            if stream.tell()==0:
                stream.write(b"\0");stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as error:
                raise RuntimeError(f"Another V11 process holds the lock: {path}") from error
            locked=True
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError(f"Another V11 process holds the lock: {path}") from error
            locked=True
        yield path
    finally:
        if stream is not None and locked:
            try:
                if os.name=="nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
            except OSError:
                pass
        if stream is not None:
            stream.close()
        with _ACTIVE_LOCKS_GUARD:
            _ACTIVE_LOCKS.discard(key)

def implementation_fingerprints():
    paths={
        "server_migration/one_click_v11.py":Path(__file__).resolve(),
        "server_migration/v11_prefetch.py":Path(__file__).with_name("v11_prefetch.py").resolve(),
        "server_migration/train_microbatch.py":Path(__file__).with_name("train_microbatch.py").resolve(),
        "server_migration/payload_contract.py":Path(__file__).with_name("payload_contract.py").resolve(),
        "server_migration/verify_source_snapshot.py":Path(__file__).with_name("verify_source_snapshot.py").resolve(),
        "server_migration/verify_peak_cache.py":Path(__file__).with_name("verify_peak_cache.py").resolve(),
        "xrd_robustness/src/xrd_robustness/physics.py":XRD/"src/xrd_robustness/physics.py",
        "xrd_robustness/src/xrd_robustness/simulator_v11.py":XRD/"src/xrd_robustness/simulator_v11.py",
        "xrd_robustness/src/xrd_robustness/peak_cache.py":XRD/"src/xrd_robustness/peak_cache.py",
        "xrd_robustness/src/xrd_robustness/training_prefetch.py":XRD/"src/xrd_robustness/training_prefetch.py",
        "xrd_robustness/src/xrd_robustness/training/runner.py":XRD/"src/xrd_robustness/training/runner.py",
        "xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py":XRD/"src/xrd_robustness/models/ml4pxrd_resnet1d.py",
        "xrd_robustness/src/xrd_robustness/training/objectives.py":XRD/"src/xrd_robustness/training/objectives.py",
        "xrd_robustness/src/xrd_robustness/evaluation/metrics.py":XRD/"src/xrd_robustness/evaluation/metrics.py",
    }
    missing=[label for label,path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing files required by V11 experiment contract: {missing}")
    return {label:digest(path) for label,path in paths.items()}

def audit_validation_peak_inputs(records):
    """Bind reused panels to the frozen Validation PeakTable index and bytes."""
    from verify_peak_cache import AGG,COUNTS
    cache=XRD/"data/merged_154975_v11"
    split_root=cache/"validation"
    index_path=split_root/"manifests/peak_cache_manifest.v7.reflection.csv"
    summary_path=split_root/"manifests/peak_cache_summary.v7.reflection.json"
    if not index_path.is_file() or not summary_path.is_file():
        raise RuntimeError("Missing frozen Validation PeakTable manifest/summary")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("status")!="completed" or
        summary.get("completed_count")!=COUNTS["validation"] or
        summary.get("skipped_count")!=0 or
        summary.get("aggregate_cache_sha256")!=AGG["validation"]):
        raise RuntimeError("Frozen Validation PeakTable summary does not match its contract")
    index_sha=digest(index_path)
    if index_sha.lower()!=str(summary.get("manifest_sha256","")).lower():
        raise RuntimeError("Frozen Validation PeakTable manifest hash mismatch")
    indexed={}
    aggregate=[]
    with index_path.open(encoding="utf-8",newline="") as stream:
        reader=csv.DictReader(stream)
        required={"material_id","sha256","bytes","file"}
        if not required.issubset(set(reader.fieldnames or ())):
            raise RuntimeError("Frozen Validation PeakTable manifest schema mismatch")
        for row in reader:
            material_id=str(row["material_id"])
            if material_id in indexed:
                raise RuntimeError(f"Duplicate Validation PeakTable identity: {material_id}")
            indexed[material_id]=row
            aggregate.append(f"{material_id}:{row['sha256']}")
    aggregate_sha=hashlib.sha256("\n".join(aggregate).encode("utf-8")).hexdigest()
    if len(indexed)!=COUNTS["validation"] or aggregate_sha!=AGG["validation"]:
        raise RuntimeError("Frozen Validation PeakTable index does not match its aggregate hash")
    for record in records:
        row=indexed.get(record.material_id)
        if row is None:
            raise RuntimeError(f"Validation PeakTable missing from frozen index: {record.material_id}")
        declared=Path(str(row["file"]))
        expected_rel=Path("mp_processed")/"peak_tables_v7_reflection"/(record.material_id+".npz")
        if declared.is_absolute() or ".." in declared.parts or tuple(declared.parts[-3:])!=tuple(expected_rel.parts):
            raise RuntimeError(f"Unexpected Validation PeakTable path: {record.material_id}")
        path=Path(record.peak_table_path).resolve()
        expected_path=(split_root/expected_rel).resolve()
        if path!=expected_path or not path.is_file():
            raise RuntimeError(f"Validation PeakTable path mismatch or missing: {record.material_id}")
        if path.stat().st_size!=int(row["bytes"]) or digest(path).lower()!=str(row["sha256"]).lower():
            raise RuntimeError(f"Validation PeakTable bytes/SHA mismatch: {record.material_id}")
    return {"manifest_sha256":index_sha,"aggregate_cache_sha256":aggregate_sha}

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".partial")
    temp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,path)

def event(kind,**kwargs):
    print(json.dumps({"event":kind,"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),**kwargs},ensure_ascii=False),flush=True)

def contract(args):
    records=XRD/"data/merged_154975_v11/training_records.v1.jsonl"
    sim=XRD/"configs/simulation.v11_tch_pseudo_voigt.json"
    expected_records="7f169d555de18b4dd811e18a67196acee317733864a1232fa719a861104333dd"
    if not records.is_file() or digest(records)!=expected_records:
        raise RuntimeError("Missing or changed frozen 131729 train/validation manifest")
    if not sim.is_file():
        raise RuntimeError("V11 simulator config missing")
    obj=json.loads(sim.read_text(encoding="utf-8"))
    if obj.get("simulator_version")!="v11_tch_pseudo_voigt":
        raise RuntimeError("Unexpected simulator version")
    needed=("train","in_range","ood_shift_negative","ood_shift_positive","ood_broadening","ood_noise","ood_background","ood_texture")
    if not all(p in obj["profiles"] for p in needed):
        raise RuntimeError("Required V11 profiles missing")
    return {
        "schema":"v11_154975_pxrd_lambda_architecture_v2",
        "payload_contract_version":PAYLOAD_CONTRACT_VERSION,
        "implementation_sha256":implementation_fingerprints(),
        "source_manifest_sha256":expected_records,
        "simulator_config_sha256":digest(sim),
        "source_records":131729,
        "training_rows":108483, "training_parents":108478,
        "validation_rows":23246, "validation_parents":23245,
        "held_out_test_parents":23245, "test_and_rruff_access":"prohibited",
        "architecture":"ML4PXRDResNet1D ResNet-18-GN, frozen depth/width; selectable PXRD stride/kernel presets",
        "architecture_presets":{key:{"stage_transition_strides":list(value[0]),"residual_kernel_size":value[1]} for key,value in V11_ARCHITECTURES.items()},
        "fixed_optimizer":V11_FIXED_OPTIMIZER,
        "train_mode":"dynamic_js_same_parent",
        "batch_size_parents":args.batch_size,
        "microbatch_size_parents":getattr(args,"microbatch_size",args.batch_size),
        "sampling_mode":getattr(args,"sampling_mode","random_batch"),
        "prefetch_workers":args.prefetch_workers,
        "prefetch_batches":args.prefetch_batches,
        "native_threads":args.native_threads,
        "worker_peak_cache":args.worker_peak_cache,
        "training_precision":"bf16_if_supported_else_fp32",
        "validation_precision":"bf16" if args.validation_bf16 else "fp32",
        "pipeline":"V11 deterministic multiprocessing, lazy PeakTable-LRU, BF16, pinned transfers, frozen Validation memmaps",
        "hpo_steps":args.hpo_steps,
        "confirmation_steps":args.confirm_steps,
        "final_steps":args.final_steps,
        "final_seeds":[20261106,20261107,20261108],
        "eval_interval_steps":args.eval_every,
        "stopping_policy":{"min_parent_epochs":50,"max_parent_epochs":100,
                           "validation_every_parent_epochs":10,
                           "patience_validation_checks":3,"min_delta":0.002},
        "validation_mode":"FULL_PARENT_DISJOINT",
        "validation_rows":23246,
        "validation_parents":23245,
        "validation_seed":20260721,
        "search_seed":20261103,
        "hpo_seed":20260711,
        "confirmation_seeds":[20261104,20261105],
        "max_new_trials":args.trials,
        "search_space":{"lambda_js":[15.,120.],"architecture":list(V11_ARCHITECTURES)},
        "selection":"mean 6 simulated OOD Macro-F1 evaluated on ALL 23245 unique parent-disjoint Validation groups; fixed render seed, independent-seed confirmation",
        "full_validation_final":True,
        "max_gpu_hours":args.max_gpu_hours,
        "caveat":"New data/simulator protocol, not directly comparable to 14060 V10 scores; not final RRUFF ranking"
    }

def ctx_libraries():
    import numpy as np
    import torch
    from torch.nn import functional as F
    from xrd_robustness.training.runner import (
        load_peak_records,load_peak_tables,render_pair_batch,build_online_view_factory,
    )
    from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,ML4PXRDResNet1DConfig
    from xrd_robustness.physics import PhysicsParameterSampler
    from xrd_robustness.evaluation.metrics import classification_metrics
    return np,torch,F,load_peak_records,load_peak_tables,render_pair_batch,build_online_view_factory,ML4PXRDResNet1D,ML4PXRDResNet1DConfig,PhysicsParameterSampler,classification_metrics

def full_parent_disjoint_records(records_path, records, *, expected_rows=None, expected_parents=None):
    """Select one deterministic sample per unique train/validation parent, never sample Validation.

    Frozen manifest has 108483 train / 23246 val MP IDs, and 108478 / 23245
    unique parent fingerprints. Exact split/label/identity contract is audited.
    """
    expected_rows=expected_rows or {"train":108483,"validation":23246}
    expected_parents=expected_parents or {"train":108478,"validation":23245}
    row_counts={"train":0,"validation":0}
    selected={"train":{},"validation":{}}
    by_id={rec.material_id:rec for rec in records}
    if len(by_id)!=len(records):
        raise ValueError("Duplicate material_id in training manifest")
    seen_parent_split={}
    label_by_parent={}
    with Path(records_path).open(encoding="utf-8") as source:
        for raw in source:
            if not raw.strip():
                continue
            row=json.loads(raw)
            split=row.get("split")
            if split not in selected:
                raise ValueError(f"Unexpected non-train/validation row: {split}")
            mid=str(row.get("material_id",""))
            parent=str(row.get("parent_structure_id",""))
            if not parent or not mid or mid not in by_id:
                raise ValueError("Missing parent or unmatched material ID")
            rec=by_id.pop(mid)
            if split!=rec.split or int(row["label"])!=rec.label:
                raise ValueError(f"Split/label mismatch for {mid}")
            earlier=seen_parent_split.setdefault(parent,split)
            if earlier!=split:
                raise ValueError(f"Cross-split parent leakage: {parent}")
            earlier_label=label_by_parent.setdefault(parent,rec.label)
            if earlier_label!=rec.label:
                raise ValueError(f"Conflicting labels within parent: {parent}")
            previous=selected[split].get(parent)
            if previous is None or mid<previous.material_id:
                selected[split][parent]=rec
            row_counts[split]+=1
    if by_id:
        raise ValueError(f"Unexpected unmatched peak records: {len(by_id)}")
    if row_counts!=expected_rows:
        raise ValueError(f"Frozen split row count changed: {row_counts}")
    parent_counts={split:len(sets) for split,sets in selected.items()}
    if parent_counts!=expected_parents:
        raise ValueError(f"Frozen independent parent counts changed: {parent_counts}")
    canonical={
        split: sorted(selected[split].values(),key=lambda rec:rec.material_id)
        for split in ("train","validation")
    }
    for split,rows in canonical.items():
        if {r.label for r in rows}!=set(range(7)):
            raise ValueError(f"Missing crystal systems in {split}")
    fingerprints={
        split:hashlib.sha256(
            "\n".join(
                f"{parent}|{record.material_id}|{record.label}"
                for parent,record in sorted(selected[split].items())
            ).encode("utf-8")
        ).hexdigest()
        for split in ("train","validation")
    }
    return canonical["train"],canonical["validation"],{
        "raw_rows_by_split":row_counts,
        "independent_parents_by_split":parent_counts,
        "deduplicated_aliases":{
            split:row_counts[split]-parent_counts[split]
            for split in ("train","validation")
        },
        "frozen_parent_mapping_sha256":fingerprints,
        "validation_mode":"FULL_PARENT_DISJOINT",
    }


def factory(sim_config,seed,PhysicsParameterSampler,build_online_view_factory):
    sampler=PhysicsParameterSampler.from_mapping({**sim_config,"run_seed":seed})
    return build_online_view_factory(sampler,sim_config)[0]

def loss_js(logit1,logit2,targets,weight,torch,F):
    # All objective arithmetic in FP32; preserve same-parent JS mathematics.
    l1=logit1.float();l2=logit2.float()
    ce=0.5*(F.cross_entropy(l1,targets)+F.cross_entropy(l2,targets))
    p=F.log_softmax(l1,dim=-1)
    q=F.log_softmax(l2,dim=-1)
    m=torch.logaddexp(p,q)-math.log(2.0)
    js=0.5*((p.exp()*(p-m)).sum(-1).mean()+(q.exp()*(q-m)).sum(-1).mean())
    return ce+weight*js,ce,js

VALIDATION_OOD_PROFILES=("ood_shift_negative","ood_shift_positive","ood_broadening",
                         "ood_noise","ood_background","ood_texture")


def prepare_validation_panels(records, peaks, sim, libs, study_dir, *,
                              expected_parents=23245, workers=4, prefetch_batches=3,
                              native_threads=1, worker_peak_cache=512):
    base=Path(study_dir)/"validation_panels_v11"
    base.mkdir(parents=True,exist_ok=True)
    with exclusive_file_lock(base/".prepare.lock"):
        return _prepare_validation_panels_locked(
            records,peaks,sim,libs,study_dir,
            expected_parents=expected_parents,workers=workers,
            prefetch_batches=prefetch_batches,native_threads=native_threads,
            worker_peak_cache=worker_peak_cache,
        )

def remove_unindexed_validation_panel_files(base, profile):
    """Remove files left by a crash before the panel index was committed."""
    base=Path(base)
    names=[profile+".first.npy",profile+".second.npy",
           profile+".first.partial.npy",profile+".second.partial.npy"]
    for name in names:
        path=base/name
        if path.exists():
            path.unlink()


def legacy_validation_panel_identity_compatible(saved, current):
    """Reuse hashed Validation panels across explicitly audited training-only updates.

    .7->.8 changed epochs; .8->.9 changes training HPO/architecture, never
    the physical renderer, source input, Validation profile or seed.
    Frozen indexes may still be at .7 after read-only reuse under .8.
    Identity equality (apart from the enumerated payload version) and every
    panel file SHA256 remain mandatory. No arbitrary future-version bypass.
    """
    if not isinstance(saved, dict) or not isinstance(current, dict):
        return False
    old=saved.get("payload_contract_version")
    new=current.get("payload_contract_version")
    allowed={
        ("v11-parent-epoch-microbatch-20261109.7",
         "v11-parent-epoch-budget-20261109.8"),
        ("v11-parent-epoch-budget-20261109.8",
         "v11-focused-science-cpu-20261109.9"),
        ("v11-parent-epoch-microbatch-20261109.7",
         "v11-focused-science-cpu-20261109.9"),
    }
    if (old,new) not in allowed:
        return False
    without_payload=lambda x:{k:v for k,v in x.items() if k!="payload_contract_version"}
    return without_payload(saved)==without_payload(current)


def _prepare_validation_panels_locked(records, peaks, sim, libs, study_dir, *,
                              expected_parents=23245, workers=4, prefetch_batches=3,
                              native_threads=1, worker_peak_cache=512):
    """Freeze all full-Validation V11 realizations once, memory-mapped across HPO trials.

    This removes repeat CPU rendering of 23245 parents x 2 views x 6 profiles
    at every checkpoint. Panels stay private; hashes/IDs/seed/profiles frozen.
    Interrupted partial panels can be rebuilt, never silently overwrite
    a completed panel with unexpected input hashes.
    """
    np,torch,F,_,_,render_pair_batch,build_online_view_factory,*tail=libs
    PhysicsParameterSampler=tail[-2]
    if len(records)!=expected_parents:
        raise ValueError(f"Full Validation expected {expected_parents}, got {len(records)}")
    peak_source=audit_validation_peak_inputs(records)
    code_hashes=implementation_fingerprints()
    render_sources=(
        "server_migration/v11_prefetch.py",
        "server_migration/verify_peak_cache.py",
        "xrd_robustness/src/xrd_robustness/physics.py",
        "xrd_robustness/src/xrd_robustness/simulator_v11.py",
        "xrd_robustness/src/xrd_robustness/peak_cache.py",
        "xrd_robustness/src/xrd_robustness/training/runner.py",
    )
    parent_ids_hash=hashlib.sha256(
        "\n".join(rec.material_id for rec in records).encode("utf-8")
    ).hexdigest()
    identity={
        "version":"v11-full-validation-dual-view-cache-v1",
        "payload_contract_version":PAYLOAD_CONTRACT_VERSION,
        "render_source_sha256":{name:code_hashes[name] for name in render_sources},
        "source_manifest_sha256":digest(XRD/"data/merged_154975_v11/training_records.v1.jsonl"),
        "validation_peak_cache_source":peak_source,
        "simulation_config_sha256":digest(XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
        "parent_ids_sha256":parent_ids_hash,
        "parent_count":len(records),
        "render_epoch":0,"render_step":0,"render_seed":20260721,
        "profiles":list(VALIDATION_OOD_PROFILES),
        "data_shape":[len(records),3501],"dtype":"float32",
        "meaning":"simulated Validation only, no Test or RRUFF"
    }
    base=study_dir/"validation_panels_v11"
    base.mkdir(parents=True,exist_ok=True)
    index_path=base/"panel_index.json"
    if index_path.exists():
        index=json.loads(index_path.read_text(encoding="utf-8"))
        frozen_identity=index.get("identity") if isinstance(index,dict) else None
        version_only_compatible=legacy_validation_panel_identity_compatible(
            frozen_identity, identity)
        if (not isinstance(index,dict)
            or (frozen_identity!=identity and not version_only_compatible)
            or not isinstance(index.get("entries"),dict)
            or set(index["entries"]).difference(VALIDATION_OOD_PROFILES)):
            raise RuntimeError("Existing Validation cache identity mismatch; refuse overwrite")
        if version_only_compatible:
            event("validation_panel_budget_only_payload_compatibility",
                  from_version=frozen_identity["payload_contract_version"],
                  to_version=identity["payload_contract_version"],
                  note="Retain original frozen index and verify every .npy SHA256")
    else:
        index={"identity":identity,"entries":{}}
        write_json(index_path,index)
    # The same V11 renderer is used for both training and frozen Validation.
    # Start the worker pool only when one or more fixed panels are missing.
    missing=[p for p in VALIDATION_OOD_PROFILES if p not in index["entries"]]
    pool=(V11PairPrefetchPool(sim,run_seed=20260721,workers=workers,
                             prefetch_batches=prefetch_batches,
                             native_threads=native_threads,
                             max_cached_peaks=worker_peak_cache) if missing else None)
    panels={}
    try:
        for profile in VALIDATION_OOD_PROFILES:
            if profile not in sim["profiles"]:
                raise RuntimeError(f"Missing V11 validation profile: {profile}")
            names=(profile+".first.npy",profile+".second.npy")
            paths=[base/name for name in names]
            entry=index["entries"].get(profile)
            if entry is not None:
                hashes=entry.get("sha256") if isinstance(entry,dict) else None
                if (not isinstance(entry,dict) or entry.get("profile")!=profile
                    or entry.get("n_parents")!=len(records)
                    or not isinstance(hashes,list) or len(hashes)!=2
                    or any(not isinstance(item,str) or len(item)!=64 for item in hashes)):
                    raise RuntimeError(f"Frozen Validation cache index entry malformed: {profile}")
                for file,expected_hash in zip(paths,entry["sha256"]):
                    if not file.exists() or digest(file).lower()!=expected_hash.lower():
                        raise RuntimeError(f"Frozen Validation cache corrupted: {file}")
                event("validation_panel_reused",profile=profile,parents=len(records))
            else:
                # Temporary files are never used as scored Validation evidence.
                # With no index entry these files cannot be trusted as a
                # completed panel; remove them and regenerate under the cache lock.
                remove_unindexed_validation_panel_files(base,profile)
                temporary=[base/(profile+f".{view}.partial.npy") for view in ("first","second")]
                first=np.lib.format.open_memmap(temporary[0],mode="w+",dtype=np.float32,
                                                 shape=(len(records),3501))
                second=np.lib.format.open_memmap(temporary[1],mode="w+",dtype=np.float32,
                                                  shape=(len(records),3501))
                for at,(a,b,y) in iter_prefetched_batches(
                        pool,records,profile=profile,batch_size=64):
                    rows=records[at:at+len(y)]
                    if (a.shape!=(len(rows),3501) or b.shape!=(len(rows),3501)
                        or not np.isfinite(a).all() or not np.isfinite(b).all()):
                        raise RuntimeError(f"Nonfinite or invalid Validation panel {profile} at {at}")
                    if not np.array_equal(y,np.asarray([r.label for r in rows])):
                        raise RuntimeError("Validation label order mismatch")
                    first[at:at+len(rows)]=a
                    second[at:at+len(rows)]=b
                first.flush(); second.flush()
                del first,second
                for temp,dest in zip(temporary,paths):
                    if dest.exists():
                        raise RuntimeError(f"Unindexed Validation cache exists: {dest}")
                    os.replace(temp,dest)
                # Record complete caches only after hashes and atomic manifest write.
                entry={"sha256":[digest(paths[0]),digest(paths[1])],
                       "n_parents":len(records),"profile":profile}
                index["entries"][profile]=entry
                write_json(index_path,index)
                event("validation_panel_created",profile=profile,parents=len(records))
            panels[profile]=tuple(np.load(item,mmap_mode="r",allow_pickle=False)
                                  for item in paths)
            if any(arr.shape!=(len(records),3501) or arr.dtype!=np.float32
                   for arr in panels[profile]):
                raise RuntimeError(f"Frozen Validation panel shape/dtype mismatch: {profile}")
    finally:
        if pool is not None:
            pool.close()
    # Canonical JSON identity is portable across Windows CRLF and Linux LF.
    return panels,canonical_digest(json.loads(index_path.read_text(encoding="utf-8")))

def validate(model,records,peaks,val_factory,device,libs,batch_size,profiles,panels=None,*,use_bf16=False):
    np,torch,F,_,_,render_pair_batch,*tail=libs
    metrics=tail[-1]
    result={}
    model.eval()
    if len(records)==0:
        raise ValueError("Empty Validation set")
    for profile in profiles:
        labels=[];probas=[]
        for at in range(0,len(records),batch_size):
            rows=records[at:at+batch_size]
            if panels is not None:
                left,right=panels[profile]
                x1=torch.from_numpy(np.array(left[at:at+len(rows)],copy=True))
                x2=torch.from_numpy(np.array(right[at:at+len(rows)],copy=True))
                y=torch.tensor([r.label for r in rows],dtype=torch.long)
            else:
                x1,x2,y=render_pair_batch(rows,peaks,val_factory,epoch=0,global_step=0,profile=profile)
            if device.type=="cuda":
                x1=x1.pin_memory().to(device,non_blocking=True)
                x2=x2.pin_memory().to(device,non_blocking=True)
            else:
                x1=x1.to(device);x2=x2.to(device)
            with torch.inference_mode():
                with torch.autocast("cuda",dtype=torch.bfloat16,
                                    enabled=(use_bf16 and device.type=="cuda" and torch.cuda.is_bf16_supported())):
                    a=model(x1)["logits"]
                    b=model(x2)["logits"]
                a=a.float();b=b.float()
                p=0.5*(torch.softmax(a,-1)+torch.softmax(b,-1))
            probas.append(p.cpu().numpy());labels.extend(y.tolist())
        probabilities=np.concatenate(probas,axis=0)
        pred=probabilities.argmax(axis=1).tolist()
        row=metrics(labels,pred,probabilities=probabilities,num_classes=7)
        result[profile]={"macro_f1":float(row["macro_f1"]),"accuracy":float(row["accuracy"]),"ece":float(row["ece"]),
                         "evaluation_parents":len(records)}
    model.train()
    return result

def atomically_save_torch(path,object_to_save,torch):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".partial")
    torch.save(object_to_save,temp)
    os.replace(temp,path)

def save_trial_checkpoint(path,*,model,optimizer,step,best,best_step,
                          numpy_rng_state,history,contract,device,torch):
    """Persist the optimizer state plus the NumPy and Torch RNG states in use."""
    device=torch.device(device)
    if device.type=="cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA checkpoint save requested without CUDA")
    cuda_rngs=torch.cuda.get_rng_state_all() if device.type=="cuda" else []
    atomically_save_torch(path,{
        "model":model.state_dict(),"optimizer":optimizer.state_dict(),
        "step":step,"best":best,"best_step":best_step,
        "numpy_rng":numpy_rng_state,"torch_rng":torch.get_rng_state(),
        "cuda_rngs":cuda_rngs,"history":history,"contract":contract,
    },torch)

def restore_trial_checkpoint(path,*,model,optimizer,rng,expected_contract,device,torch):
    """Restore a trial checkpoint; CPU mode supports deterministic local regression tests."""
    device=torch.device(device)
    saved=torch.load(path,map_location=device,weights_only=False)
    required={"model","optimizer","step","best","best_step","numpy_rng",
              "torch_rng","cuda_rngs","history","contract"}
    missing=required.difference(saved)
    if missing:
        raise RuntimeError(f"Incomplete trial checkpoint; missing fields: {sorted(missing)}")
    if saved["contract"]!=expected_contract:
        raise RuntimeError("Checkpoint protocol mismatch")
    if device.type=="cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA checkpoint restore requested without CUDA")
        if len(saved["cuda_rngs"])!=torch.cuda.device_count():
            raise RuntimeError("Checkpoint CUDA device count mismatch")
    model.load_state_dict(saved["model"])
    optimizer.load_state_dict(saved["optimizer"])
    rng.bit_generator.state=saved["numpy_rng"]
    torch.set_rng_state(saved["torch_rng"].cpu())
    if device.type=="cuda":
        torch.cuda.set_rng_state_all([state.cpu() for state in saved["cuda_rngs"]])
    return saved["step"],saved["best"],saved["best_step"],saved["history"]

def trial_run(name,params,seed,max_steps,study_dir,train_records,val_records,peaks,sim,libs,argv,
              validation_panels=None,validation_panel_index_sha256=None):
    np,torch,F,_,_,render_pair_batch,build_online_view_factory,ML4PXRDResNet1D,ML4PXRDResNet1DConfig,PhysicsParameterSampler,metrics=libs
    root=study_dir/"trials"/name
    cfg={"params":params,"seed":seed,"max_steps":max_steps,"batch_size":argv.batch_size,
         "microbatch_size":argv.microbatch_size,"sampling_mode":argv.sampling_mode,
         "eval_every":argv.eval_every,"sim_config_sha256":digest(XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
         "validation_mode":"FULL_PARENT_DISJOINT","validation_parent_count":len(val_records),
         "validation_parent_ids_sha256":hashlib.sha256("\n".join(r.material_id for r in val_records).encode()).hexdigest(),
         "training_parent_count":len(train_records),
         "validation_panel_index_sha256":validation_panel_index_sha256,
         "experiment_contract_sha256":canonical_digest(contract(argv))}
    if name != "gpu_micro_smoke":
        if (len(train_records)!=108478 or len(val_records)!=23245):
            raise RuntimeError("Formal HPO requires all unique TRAIN/Validation parents")
        if validation_panels is None or not validation_panel_index_sha256:
            raise RuntimeError("Formal HPO requires frozen full Validation panel cache")
    if root.joinpath("contract.json").exists():
        if json.loads((root/"contract.json").read_text(encoding="utf-8"))!=cfg:
            raise RuntimeError("Refusing to overwrite modified trial contract")
    else:write_json(root/"contract.json",cfg)
    final=root/"result.json"
    if final.is_file():
        row=json.loads(final.read_text(encoding="utf-8"))
        if (row.get("status")=="completed"
            and (row["completed_steps"]==max_steps or row.get("stopped_early") is True)):
            validate_completed_trial_artifacts(
                study_dir,name,params,seed,max_steps,argv,
                canonical_digest(contract(argv)),validation_panel_index_sha256,
            )
            event("reuse_completed_trial",name=name,score=row["best_validation_ood_macro_f1"])
            return row
        raise RuntimeError("Existing result is incomplete/changed")
    if not torch.cuda.is_available():raise RuntimeError("A CUDA server is required for real HPO")
    device=torch.device("cuda")
    # Seed BEFORE model initialization; otherwise multi-seed comparisons are invalid.
    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    resolved=resolve_v11_trial_params(params)
    model=ML4PXRDResNet1D(v11_model_config(params,ML4PXRDResNet1DConfig)).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=resolved["learning_rate"],
                                weight_decay=resolved["weight_decay"])
    if model.parameter_count<5000000 or model.parameter_count>20000000:
        raise RuntimeError("Unexpected PXRD ResNet parameter count")
    train_fac=factory(sim,seed,PhysicsParameterSampler,build_online_view_factory)
    val_fac=factory(sim,20260721,PhysicsParameterSampler,build_online_view_factory)
    rng=np.random.default_rng(seed)
    step=0;best=-1.;best_step=0;history=[]
    resume=root/"last.pt"
    if resume.is_file():
        step,best,best_step,history=restore_trial_checkpoint(
            resume,model=model,optimizer=optimizer,rng=rng,
            expected_contract=cfg,device=device,torch=torch,
        )
        event("resumed",name=name,step=step)
    n=len(train_records)
    # Count *complete parent epochs*, never absolute tiny-step proxies.
    steps_per_parent_epoch=(n+argv.batch_size-1)//argv.batch_size
    min_training_steps=50*steps_per_parent_epoch
    meaningful_best=-math.inf
    stagnant_checks=0
    for item in history:
        if item["step"]>=min_training_steps:
            observed=float(item["mean_ood_macro_f1"])
            if observed>meaningful_best+0.002:
                meaningful_best=observed
                stagnant_checks=0
            else:
                stagnant_checks+=1
    stopped_early=False
    profiles=VALIDATION_OOD_PROFILES
    started=time.monotonic()
    # This pool is SHARED in design with full-Validation: the exact same V11
    # simulator, stable SHA256 worker sharding and bounded CPU workers.
    # Prefetching starts at the restored optimizer step (never at step zero).
    pool=V11PairPrefetchPool(
        sim,run_seed=seed,workers=argv.prefetch_workers,
        prefetch_batches=argv.prefetch_batches,
        native_threads=argv.native_threads,
        max_cached_peaks=argv.worker_peak_cache,
    )
    future_rng={}
    permutation_cache={}
    next_submit=step
    try:
        while step<max_steps:
            # CPU prepares upcoming spectra while GPU trains on the first
            # submitted step. Only the MAIN process advances the sampling RNG.
            next_submit=enqueue_train_lookahead(
                pool,rng,train_records,batch_size=argv.batch_size,
                start_step=step,next_submit=next_submit,max_steps=max_steps,
                committed_states=future_rng,
                sampling_mode=argv.sampling_mode, sampling_seed=seed,
                permutation_cache=permutation_cache,
            )
            batch_first,batch_second,batch_labels=pool.get(step)
            # DO NOT checkpoint the look-ahead RNG. It includes future batches
            # whose optimizer steps have not committed; resumed studies would
            # otherwise skip parents and change scientific sampling trajectories.
            committed_rng_state=future_rng.pop(step)
            x1=torch.from_numpy(batch_first)
            x2=torch.from_numpy(batch_second)
            targets=torch.from_numpy(batch_labels)
            if device.type=="cuda":
                x1=x1.pin_memory().to(device,non_blocking=True)
                x2=x2.pin_memory().to(device,non_blocking=True)
                targets=targets.pin_memory().to(device,non_blocking=True)
            else:
                x1=x1.to(device);x2=x2.to(device);targets=targets.to(device)
            for group in optimizer.param_groups:
                group["lr"]=resolved["learning_rate"]*(
                    .05+.95*.5*(1+math.cos(math.pi*step/max_steps))
                )
            use_amp=torch.cuda.is_bf16_supported()
            loss,ce,js,norm=paired_optimizer_step(
                model,optimizer,x1,x2,targets,
                lambda_js=resolved["lambda_js"],
                microbatch_size=argv.microbatch_size,
                loss_fn=loss_js,torch=torch,F=F,amp=use_amp,
            )
            step+=1
            if step%argv.eval_every==0 or step==max_steps:
                row=validate(
                    model,val_records,peaks,val_fac,device,libs,argv.batch_size,
                    profiles,panels=validation_panels,use_bf16=argv.validation_bf16,
                )
                score=sum(row[p]["macro_f1"] for p in profiles)/6.0
                if not math.isfinite(score):
                    raise RuntimeError("nonfinite validation macro F1")
                if step>=min_training_steps:
                    if score>meaningful_best+0.002:
                        meaningful_best=score
                        stagnant_checks=0
                    else:
                        stagnant_checks+=1
                stopped_early=(step<max_steps and step>=min_training_steps
                               and stagnant_checks>=3)
                history.append({
                    "step":step,"mean_ood_macro_f1":score,"profiles":row,
                    "train_last_loss":float(loss),
                    "last_ce":float(ce),
                    "last_js":float(js),
                    "lr":optimizer.param_groups[0]["lr"],
                    "prefetch_workers":argv.prefetch_workers,
                    "prefetch_batches":argv.prefetch_batches,
                    "sampling_mode":argv.sampling_mode,
                    "microbatch_size":argv.microbatch_size,
                    "last_parent_batch_count":int(targets.shape[0]),
                })
                if score>best:
                    best=score;best_step=step
                    atomically_save_torch(root/"best.pt",{
                        "model":model.state_dict(),"step":step,
                        "validation_ood_macro_f1":score,"contract":cfg,
                    },torch)
                save_trial_checkpoint(
                    resume,model=model,optimizer=optimizer,step=step,best=best,
                    best_step=best_step,numpy_rng_state=committed_rng_state,
                    history=history,contract=cfg,device=device,torch=torch,
                )
                write_json(root/"history.json",history)
                event(
                    "trial_validation",name=name,step=step,
                    score=round(score,6),best=round(best,6),
                    stagnant_checks=stagnant_checks,stopped_early=stopped_early,
                    gpu_seconds=round(time.monotonic()-started,1),
                )
                if stopped_early:
                    break
    finally:
        pool.close()
    result={"status":"completed","name":name,"seed":seed,"architecture":params["architecture"]+" ResNet-18-GN",
            "parameters":params,"completed_steps":step,"planned_max_steps":max_steps,
            "stopped_early":stopped_early,"best_step":best_step,
            "best_validation_ood_macro_f1":best,"best_checkpoint_sha256":digest(root/"best.pt"),
            "last_checkpoint_sha256":digest(root/"last.pt"),
            "validation_unique_parents":len(val_records),"profiles":list(profiles),
            "gpu_seconds":time.monotonic()-started,
            "scope":"fixed simulated Validation only; no Test/RRUFF"}
    write_json(final,result)
    return result

def validate_completed_trial_artifacts(
        study_dir,name,params,seed,max_steps,args,contract_sha,panel_sha,
        *,expected_score=None,expected_checkpoint_sha=None,verify_checkpoints=True):
    """Validate completed artifacts before reuse or final-stage selection."""
    root=Path(study_dir)/"trials"/name
    contract_path=root/"contract.json"
    result_path=root/"result.json"
    if not contract_path.is_file() or not result_path.is_file():
        raise RuntimeError(f"Completed trial artifacts missing: {name}")
    cfg=json.loads(contract_path.read_text(encoding="utf-8"))
    resolve_v11_trial_params(params)  # Reject legacy four-dimensional studies.
    row=json.loads(result_path.read_text(encoding="utf-8"))
    expected={
        "params":params,"seed":seed,"max_steps":max_steps,
        "batch_size":args.batch_size,"eval_every":args.eval_every,
        "microbatch_size":getattr(args,"microbatch_size",args.batch_size),
        "sampling_mode":getattr(args,"sampling_mode","random_batch"),
        "sim_config_sha256":digest(XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
        "validation_mode":"FULL_PARENT_DISJOINT",
        "validation_parent_count":23245,"training_parent_count":108478,
        "validation_panel_index_sha256":panel_sha,
        "experiment_contract_sha256":contract_sha,
    }
    if any(cfg.get(key)!=value for key,value in expected.items()):
        raise RuntimeError(f"Completed trial contract mismatch: {name}")
    score=row.get("best_validation_ood_macro_f1")
    actual_steps=row.get("completed_steps")
    early=(row.get("stopped_early") is True
           and isinstance(actual_steps,int) and actual_steps<max_steps
           and actual_steps>=50*((108478+args.batch_size-1)//args.batch_size)
           and actual_steps%args.eval_every==0)
    if (row.get("status")!="completed" or row.get("name")!=name
        or row.get("seed")!=seed or row.get("parameters")!=params
        or row.get("planned_max_steps",max_steps)!=max_steps
        or not (actual_steps==max_steps or early)
        or row.get("validation_unique_parents")!=23245
        or row.get("profiles")!=list(VALIDATION_OOD_PROFILES)
        or not isinstance(score,(int,float)) or not math.isfinite(float(score))):
        raise RuntimeError(f"Completed trial result metadata mismatch: {name}")
    if expected_score is not None and not math.isclose(
            float(score),float(expected_score),rel_tol=0.0,abs_tol=1e-12):
        raise RuntimeError(f"Optuna/result score mismatch: {name}")
    best_sha=row.get("best_checkpoint_sha256")
    if expected_checkpoint_sha is not None and str(best_sha).lower()!=str(expected_checkpoint_sha).lower():
        raise RuntimeError(f"Recommendation/checkpoint SHA mismatch: {name}")
    if verify_checkpoints:
        for field,filename in (("best_checkpoint_sha256","best.pt"),
                               ("last_checkpoint_sha256","last.pt")):
            checkpoint=root/filename
            expected_hash=row.get(field)
            if (not checkpoint.is_file() or not isinstance(expected_hash,str)
                or len(expected_hash)!=64 or digest(checkpoint).lower()!=expected_hash.lower()):
                raise RuntimeError(f"Completed trial checkpoint hash mismatch: {checkpoint}")
    return row


def validate_final_recommendation(study_dir,args,contract_file,contract_obj,*,prepared_panel_sha=None):
    """Fail before loading the full data/cache unless HPO and both confirmations are valid."""
    rec_path=Path(study_dir)/"final_recommendation.json"
    if not contract_file.is_file() or not rec_path.is_file():
        raise RuntimeError("Final training blocked: HPO+confirmation artifacts are missing")
    contract_sha=digest(contract_file)
    if json.loads(contract_file.read_text(encoding="utf-8"))!=contract_obj:
        raise RuntimeError("Final training contract differs from original HPO")
    recommendation=json.loads(rec_path.read_text(encoding="utf-8"))
    if (recommendation.get("status")!="hpo_and_confirmation_completed"
        or recommendation.get("contract_sha256")!=contract_sha
        or recommendation.get("hpo_trial_count")!=args.trials):
        raise RuntimeError("Final training blocked: recommendation contract/status/count mismatch")
    panel_index=Path(study_dir)/"validation_panels_v11"/"panel_index.json"
    if prepared_panel_sha is not None:
        panel_sha=prepared_panel_sha
    else:
        if not panel_index.is_file():
            raise RuntimeError("Final training blocked: frozen Validation panels are missing")
        panel_sha=canonical_digest(json.loads(panel_index.read_text(encoding="utf-8")))
    if recommendation.get("validation_panel_index_sha256")!=panel_sha:
        raise RuntimeError("Final training blocked: recommendation Validation panel hash mismatch")

    try:
        import optuna
        from optuna.trial import TrialState
    except ImportError as error:
        raise RuntimeError("Final training blocked: Optuna is unavailable") from error
    storage="sqlite:///"+(Path(study_dir)/"optuna.sqlite3").as_posix()
    try:
        study=optuna.load_study(study_name="v11_154975_a0_sameparent_js",storage=storage)
    except Exception as error:
        raise RuntimeError("Final training blocked: Optuna study cannot be loaded") from error
    trials=study.trials
    if len(trials)!=args.trials or any(t.state!=TrialState.COMPLETE for t in trials):
        raise RuntimeError("Final training blocked: every requested Optuna trial must be COMPLETE")
    for trial in trials:
        resolve_v11_trial_params(dict(trial.params))
    ordered=sorted(trials,key=lambda trial:(-float(trial.value),trial.number))
    best=ordered[0]
    params=dict(best.params)
    if (recommendation.get("best_hpo_trial")!=best.number
        or recommendation.get("recommended_hyperparameters")!=params
        or not math.isclose(float(recommendation.get("best_hpo_validation_ood_f1",float("nan"))),
                            float(best.value),rel_tol=0.0,abs_tol=1e-12)):
        raise RuntimeError("Final training blocked: recommendation does not match completed Optuna study")

    # Tie every Optuna value to its machine-readable result. Hash the selected
    # checkpoint and the independent confirmation checkpoints before reuse.
    for trial in trials:
        validate_completed_trial_artifacts(
            study_dir,f"hpo_{trial.number:03d}",dict(trial.params),contract_obj["hpo_seed"],
            args.hpo_steps,args,canonical_digest(contract_obj),panel_sha,
            expected_score=trial.value,
            verify_checkpoints=(trial.number==best.number),
        )
    confirmations=recommendation.get("confirmation")
    expected_seeds=list(contract_obj["confirmation_seeds"])
    if (not isinstance(confirmations,list)
        or [item.get("seed") for item in confirmations if isinstance(item,dict)]!=expected_seeds
        or len(confirmations)!=len(expected_seeds)):
        raise RuntimeError("Final training blocked: confirmation seeds are incomplete or changed")
    for item,seed in zip(confirmations,expected_seeds):
        if (not isinstance(item.get("score"),(int,float))
            or not math.isfinite(float(item["score"]))
            or not isinstance(item.get("checkpoint_sha256"),str)
            or len(item["checkpoint_sha256"])!=64):
            raise RuntimeError(f"Final training blocked: confirmation artifact metadata invalid for seed {seed}")
        row=validate_completed_trial_artifacts(
            study_dir,f"confirm_{seed}",params,seed,args.confirm_steps,args,
            canonical_digest(contract_obj),panel_sha,
            expected_score=item.get("score"),
            expected_checkpoint_sha=item.get("checkpoint_sha256"),
            verify_checkpoints=True,
        )
    return recommendation,params,panel_sha


def run_pipeline(args):
    if (args.trials<6 or args.trials>12 or args.hpo_steps<1
        or args.confirm_steps<args.hpo_steps or args.final_steps<args.confirm_steps):
        raise ValueError("bounded trials and training steps required")
    if (not (1 <= args.microbatch_size <= args.batch_size)
            or args.sampling_mode not in ("epoch_shuffle","random_batch")):
        raise ValueError("Invalid microbatch or parent sampling mode")
    one_epoch=(108478+args.batch_size-1)//args.batch_size
    if args.mode in ("run","final"):
        if args.sampling_mode!="epoch_shuffle":
            raise ValueError("Formal V11 training requires full parent epoch_shuffle")
        if (args.hpo_steps<50*one_epoch or args.confirm_steps<100*one_epoch
                or args.final_steps<100*one_epoch
                or args.eval_every!=10*one_epoch):
            raise ValueError("V11 min exposure: HPO>=50, confirmation/final>=100 full-parent epochs, Validation every 10")
    if not (1<=args.prefetch_workers<=16 and 1<=args.prefetch_batches<=8
            and 1<=args.native_threads<=4 and 16<=args.worker_peak_cache<=8192):
        raise ValueError("Unbounded or invalid V11 prefetch resources")
    c=contract(args)
    study_dir=ROOT/"server_runs"/"v11_a0_js_optuna"
    contract_file=study_dir/"contract.json"
    runtime_overrides={}
    if contract_file.is_file():
        saved=json.loads(contract_file.read_text(encoding="utf-8"))
        if args.mode=="final":
            # Workers, queue depth, CPU cache and wall-clock cap are machine
            # resources, not HPO-selected science. All other keys stay frozen.
            runtime_only={"prefetch_workers","prefetch_batches","native_threads",
                          "worker_peak_cache","max_gpu_hours"}
            changed={key for key in set(saved)|set(c) if saved.get(key)!=c.get(key)}
            forbidden=changed-runtime_only
            if forbidden:
                raise RuntimeError("Final training science contract mismatch: "+str(sorted(forbidden)))
            runtime_overrides={key:{"hpo":saved[key],"final":c[key]}
                               for key in sorted(changed)}
            c=saved
            if runtime_overrides:
                event("FINAL_RUNTIME_RESOURCE_OVERRIDES",changes=runtime_overrides)
        elif saved!=c:
            raise RuntimeError("Existing study contract changed; refuse overwrite")
    elif args.mode=="run":
        write_json(contract_file,c)
    if args.mode=="plan":
        event("PLAN_ONLY",contract=c,cache_root=str(XRD/"data/merged_154975_v11"),
              note="No GPU training or trial created. Unzip full caches and verify hashes before run.")
        return
    final_context=None
    if args.mode=="final":
        rec_path=study_dir/"final_recommendation.json"
        if not rec_path.is_file():
            raise RuntimeError("Final training blocked: frozen HPO recommendation missing")
        handoff_index=study_dir/"handoff_validation_panel_index.json"
        if handoff_index.is_file():
            # Imported Windows HPO keeps the indexed identity, not multi-GB arrays.
            expected=canonical_digest(json.loads(handoff_index.read_text(encoding="utf-8")))
            if json.loads(rec_path.read_text(encoding="utf-8")).get("validation_panel_index_sha256")!=expected:
                raise RuntimeError("Final training blocked: imported Validation identity mismatch")
        else:
            # Original same-machine final path keeps the early evidence check.
            final_context=validate_final_recommendation(study_dir,args,contract_file,c)
    libs=ctx_libraries()
    np,torch,F,load_peak_records,load_peak_tables,render_pair_batch,build_online_view_factory,ML4PXRDResNet1D,ML4PXRDResNet1DConfig,PhysicsParameterSampler,metrics=libs
    records_path=XRD/"data/merged_154975_v11/training_records.v1.jsonl"
    sim=json.loads((XRD/"configs/simulation.v11_tch_pseudo_voigt.json").read_text(encoding="utf-8"))
    if args.mode=="smoke":
        # Explicitly bounded tiny CPU smoke. No GPU allocation or Optuna study.
        import itertools
        import tempfile
        sample=[]
        with records_path.open(encoding="utf-8") as f:
            # Read first train and first validation, then immediately stop.
            found=set()
            for line in f:
                item=json.loads(line)
                if item["split"] not in found:
                    found.add(item["split"]);sample.append(item)
                if len(found)==2:break
        if len(sample)!=2:raise RuntimeError("Missing train/validation rows in manifest")
        from xrd_robustness.training.runner import PeakRecord
        mini=[]
        for row in sample:
            path=records_path.parent/row["peak_table_path"]
            mini.append(PeakRecord(row["material_id"],int(row["label"]),row["split"],path))
        peaks=load_peak_tables(mini)
        fac=factory(sim,20260721,PhysicsParameterSampler,build_online_view_factory)
        tensor_a,tensor_b,labels=render_pair_batch(mini[:1],peaks,fac,epoch=0,global_step=1,profile="train")
        model=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18"))
        model.train()
        with torch.enable_grad():
            a=model(tensor_a)["logits"];b=model(tensor_b)["logits"]
            total,ce,js=loss_js(a,b,labels,60.0,torch,F)
            if not torch.isfinite(total):raise RuntimeError("smoke loss not finite")
            total.backward()
        event("SMOKE_PASS",model_parameters=model.parameter_count,train_record=mini[0].material_id,
              val_record=mini[1].material_id,simulator="v11_tch_pseudo_voigt",
              objective=float(total.detach()),note="CPU one batch; not large-scale training")
        return
    if not torch.cuda.is_available():raise RuntimeError("CUDA not available; refusing HPO")
    if torch.cuda.mem_get_info()[0]<4*1024**3:
        raise RuntimeError("Insufficient free GPU memory for A0 ResNet (>=4 GiB required)")
    start=time.monotonic()
    # Storage requires enough CPU RAM for 131729 NPZ reflection tables.
    all_records=load_peak_records(records_path)
    train=[r for r in all_records if r.split=="train"]
    val=[r for r in all_records if r.split=="validation"]
    if len(train)!=108483 or len(val)!=23246:
        raise RuntimeError("Frozen raw train/validation row counts changed")
    train_unique,val_full,parent_audit=full_parent_disjoint_records(records_path,all_records)
    event("FULL_PARENT_SPLIT_VERIFIED",audit=parent_audit,
          validation_parents=len(val_full),train_parents=len(train_unique))
    # Workers load PeakTables on demand and cap per-worker RAM via LRU.
    # No eager 131k-file NPZ extraction in the HPO main process.
    peaks={}
    validation_panels,panel_index_sha=prepare_validation_panels(
        val_full,peaks,sim,libs,study_dir,
        workers=args.prefetch_workers,prefetch_batches=args.prefetch_batches,
        native_threads=args.native_threads,worker_peak_cache=args.worker_peak_cache)
    event("FULL_VALIDATION_READY",parents=len(val_full),profiles=len(VALIDATION_OOD_PROFILES),
          index_sha256=panel_index_sha)
    if args.mode=="final":
        # Regenerated Linux panels must exactly match Windows HPO's frozen
        # canonical index and each underlying paired-spectrum SHA256.
        if (study_dir/"handoff_validation_panel_index.json").is_file():
            expected=canonical_digest(json.loads((study_dir/"handoff_validation_panel_index.json").read_text(encoding="utf-8")))
            if panel_index_sha!=expected:
                raise RuntimeError("Final training blocked: regenerated Validation differs from Windows HPO")
        final_context=validate_final_recommendation(
            study_dir,args,contract_file,c,prepared_panel_sha=panel_index_sha)
        # Separate explicit final-stage command; it reuses the exact same
        # prefetch, full frozen Validation and checkpoint/replay engine.
        recommendation,params,expected_panel_sha=final_context
        if panel_index_sha!=expected_panel_sha:
            raise RuntimeError("Final training blocked: Validation panels changed after eligibility check")
        final_runs=[]
        for final_seed in c["final_seeds"]:
            if time.monotonic()-start>args.max_gpu_hours*3600:
                event("FINAL_BUDGET_STOP",seed=final_seed,status="resume_safe")
                return
            item=trial_run(
                f"final_{final_seed}",params,final_seed,args.final_steps,
                study_dir,train_unique,val_full,peaks,sim,libs,args,
                validation_panels=validation_panels,
                validation_panel_index_sha256=panel_index_sha,
            )
            final_runs.append({
                "seed":final_seed,
                "validation_ood_macro_f1":item["best_validation_ood_macro_f1"],
                "best_step":item["best_step"],
                "checkpoint_sha256":item["best_checkpoint_sha256"],
            })
        write_json(study_dir/"final_training_summary.json",{
            "status":"final_three_seed_training_completed",
            "model":"ResNet-18-GN "+params["architecture"],"simulator":"v11_tch_pseudo_voigt",
            "training_parent_groups":len(train_unique),
            "validation_parent_groups":len(val_full),
            "final_steps":args.final_steps,"runs":final_runs,
            "selected_hpo_contract_sha256":digest(contract_file),
            "final_runtime_resource_overrides":runtime_overrides,
            "sampling_mode":args.sampling_mode,
            "effective_batch_parents":args.batch_size,
            "microbatch_parents":args.microbatch_size,
            "selection_scope":"simulated frozen Validation only, not Test/RRUFF",
        })
        event("FINAL_TRAINING_FINISHED",seeds=len(final_runs))
        return
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage="sqlite:///"+(study_dir/"optuna.sqlite3").as_posix()
    study=optuna.create_study(study_name="v11_154975_a0_sameparent_js",storage=storage,
                direction="maximize",load_if_exists=True,
                sampler=optuna.samplers.TPESampler(seed=20261103,n_startup_trials=4),
                pruner=optuna.pruners.NopPruner())
    if not study.trials:
        for arch in V11_ARCHITECTURES:
            study.enqueue_trial({"lambda_js":60.0,"architecture":arch})
    from optuna.trial import TrialState
    while True:
        done=[t for t in study.trials if t.state in (TrialState.COMPLETE,TrialState.FAIL,TrialState.PRUNED)]
        pending=[t for t in study.trials if t.state==TrialState.RUNNING]
        if len(done)>=args.trials and not pending:break
        if time.monotonic()-start>args.max_gpu_hours*3600:
            event("BUDGET_STOP",hours=args.max_gpu_hours,status="resume_safe")
            return
        if pending:
            if len(pending)!=1:raise RuntimeError("Multiple RUNNING trials; cannot resume unambiguously")
            frozen=pending[0]
            params=dict(frozen.params)
            resolve_v11_trial_params(params)  # Detect legacy four-dimensional HPO states.
            number=frozen.number
        else:
            # Sequential budget allocation: compare four architectures at
            # common historical lambda=60 for >=50 full parent epochs FIRST.
            # Then spend two more >=50-epoch runs bracketing JS strength on
            # the best architecture. No 5/10-epoch early ranking.
            if len(study.trials)==4 and len(done)==4:
                reference_winner=max(done,key=lambda t:(float(t.value),-t.number))
                focus_arch=reference_winner.params["architecture"]
                for weight in (30.0,90.0):
                    study.enqueue_trial({"lambda_js":weight,"architecture":focus_arch})
                event("HPO_LAMBDA_FOCUS_ENQUEUED",architecture=focus_arch,weights=[30,90])
            trial=study.ask()
            number=trial.number
            params={"lambda_js":trial.suggest_float("lambda_js",15.,120.),
                    "architecture":trial.suggest_categorical("architecture",list(V11_ARCHITECTURES))}
        name=f"hpo_{number:03d}"
        try:
            row=trial_run(name,params,20260711,args.hpo_steps,study_dir,train_unique,val_full,peaks,sim,libs,args,
                            validation_panels=validation_panels,
                            validation_panel_index_sha256=panel_index_sha)
            study.tell(number,row["best_validation_ood_macro_f1"])
        except Exception as err:
            event("TRIAL_FAILED_STOP",trial=name,error=repr(err),
                  note="Safe stop, resolve blocker before --mode run resume")
            # Preserve RUNNING trial and checkpoint for exact resume instead of trying a new trial.
            raise
    if len(study.trials)!=args.trials or any(t.state!=TrialState.COMPLETE for t in study.trials):
        raise RuntimeError("HPO cannot recommend: every requested trial must be COMPLETE")
    complete=sorted([t for t in study.trials if t.state==TrialState.COMPLETE],
                    key=lambda t:(-float(t.value),t.number))
    if not complete:raise RuntimeError("No valid completed HPO trial")
    best_trial=complete[0]
    resolve_v11_trial_params(dict(best_trial.params))
    confirmation=[]
    for seed in c["confirmation_seeds"]:
        if time.monotonic()-start>args.max_gpu_hours*3600:
            event("BUDGET_STOP_BEFORE_CONFIRMATION",seed=seed,status="resume_safe")
            return
        params=dict(best_trial.params)
        name=f"confirm_{seed}"
        row=trial_run(name,params,seed,args.confirm_steps,study_dir,train_unique,val_full,peaks,sim,libs,args,
                            validation_panels=validation_panels,
                            validation_panel_index_sha256=panel_index_sha)
        confirmation.append({"seed":seed,"score":row["best_validation_ood_macro_f1"],
                             "checkpoint_sha256":row["best_checkpoint_sha256"]})
    result={"status":"hpo_and_confirmation_completed","architecture":best_trial.params["architecture"]+" ResNet-18-GN",
            "simulator":"v11_tch_pseudo_voigt","dataset":"154975 MP ID; 108478 unique train parents; ALL 23245 unique Validation parents",
            "best_hpo_trial":best_trial.number,"best_hpo_validation_ood_f1":best_trial.value,
            "recommended_hyperparameters":best_trial.params,"confirmation":confirmation,
            "validation_parent_audit":parent_audit,
            "selection_warning":"Chosen on ALL 23245 unique frozen Validation parents; confirmation seeds use same domain, not Test/RRUFF.",
            "hpo_trial_count":len(complete),"contract_sha256":digest(contract_file),
            "validation_panel_index_sha256":panel_index_sha}
    write_json(study_dir/"final_recommendation.json",result)
    event("PIPELINE_COMPLETED",summary=str(study_dir/"final_recommendation.json"),best=best_trial.value)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["plan","smoke","run","final"],default="plan")
    parser.add_argument("--trials",type=int,default=6,
                        help="At least six: four architecture references at lambda=60, then lambda=30/90 on the winning architecture")
    parser.add_argument("--hpo-steps",type=int,default=None)
    parser.add_argument("--confirm-steps",type=int,default=None)
    parser.add_argument("--final-steps",type=int,default=None)
    parser.add_argument("--eval-every",type=int,default=None)
    parser.add_argument("--batch-size",type=int,default=16)
    parser.add_argument("--microbatch-size",type=int,default=None,
                        help="GPU microbatch in parents; optimizer effective batch remains --batch-size")
    parser.add_argument("--sampling-mode",choices=["epoch_shuffle","random_batch"],
                        default="epoch_shuffle")
    # Unified CPU prefetch default across Windows, Linux and cloud runners.
    # Runtime-only flags can be overridden per host without changing science.
    parser.add_argument("--prefetch-workers",type=int,default=12)
    parser.add_argument("--prefetch-batches",type=int,default=4)
    parser.add_argument("--native-threads",type=int,default=1)
    parser.add_argument("--worker-peak-cache",type=int,default=64)
    parser.add_argument("--validation-bf16",action="store_true",help="Opt-in only after BF16 vs FP32 Validation parity checks")
    parser.add_argument("--max-gpu-hours",type=float,default=12.0)
    args=parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    args.microbatch_size=args.batch_size if args.microbatch_size is None else args.microbatch_size
    default_steps=(108478+args.batch_size-1)//args.batch_size if args.sampling_mode=="epoch_shuffle" else 6160
    # Scientific anti-short-exposure rule: >=50 full parent epochs for each
    # HPO candidate. Independent confirmation/final use 100; Validation every 10.
    # In random_batch provenance mode, default_steps is a legacy step unit,
    # not an actual complete parent epoch; epoch_shuffle remains the default.
    args.hpo_steps=50*default_steps if args.hpo_steps is None else args.hpo_steps
    args.confirm_steps=100*default_steps if args.confirm_steps is None else args.confirm_steps
    args.final_steps=100*default_steps if args.final_steps is None else args.final_steps
    args.eval_every=10*default_steps if args.eval_every is None else args.eval_every
    if args.mode in ("run","final"):
        study_dir=ROOT/"server_runs"/"v11_a0_js_optuna"
        with exclusive_file_lock(study_dir/".study.lock"):
            run_pipeline(args)
    else:
        run_pipeline(args)

if __name__=="__main__":
    main()
