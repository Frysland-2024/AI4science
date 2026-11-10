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
    """Three explicit HPO dimensions: JS lambda, middle stride and kernel."""
    if set(params)!={"lambda_js","middle_stride","kernel_size"}:
        raise ValueError("V11 trials must contain only lambda_js, middle_stride, kernel_size")
    middle_stride=params["middle_stride"]
    kernel=params["kernel_size"]
    if type(middle_stride) is not int or middle_stride not in (2,4):
        raise ValueError("middle_stride must be 2 or 4")
    if type(kernel) is not int or kernel not in (5,9):
        raise ValueError("kernel_size must be 5 or 9")
    architecture=next(
        (key for key,(strides,k) in V11_ARCHITECTURES.items()
         if strides==(4,middle_stride,4) and k==kernel),None)
    if architecture is None:
        raise ValueError("Unregistered PXRD architecture")
    weight=float(params["lambda_js"])
    if not math.isfinite(weight) or not 3.0<=weight<=120.0:
        raise ValueError("V11 lambda_js must be finite and within safety range 3..120")
    return {**V11_FIXED_OPTIMIZER,"lambda_js":weight,"architecture":architecture,
            "middle_stride":middle_stride,"kernel_size":kernel}

def v11_model_config(params, config_type):
    settings=resolve_v11_trial_params(params)
    return config_type(model_id="18",
        stage_transition_strides=(4,settings["middle_stride"],4),
        residual_kernel_size=settings["kernel_size"])

def v11_architecture_trial_params(architecture,weight):
    """Named A0–A3 presets are scientific controls; Optuna optimizes knobs."""
    strides,kernel=V11_ARCHITECTURES[architecture]
    return {"lambda_js":float(weight),"middle_stride":strides[1],
            "kernel_size":kernel}

# This is the measured V9 winning TRAIN-only gradient-scale anchor.
# V9 lambda=60 was SELECTED later on independent Validation; R was not
# measured on the final model, and R by itself does not prove gradient alignment.
V9_SELECTED_REFERENCE_R=1.754115194414842
V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA="7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020"
V11_SUPPLEMENTARY_SAFETY_REPORT_SHA="1d49b6df02179040f24819aad38e92bf47c6f5816283deed50be0380d9250322"
V11_ORIGINAL_GRADIENT_SCIENCE_ID="39eebfd9daff7e4d6a29ca069a605e49e1e44818c0fc4b6abb77c51c2162318d"


def derive_train_only_js_range(median_unweighted_ratio, *, previous_lambda=60.0):
    """Map measured Train-only A0 gradient R=lambda*r to lambda (R-first).

    The main design follows the FIRST whole-Train calibrated range, R targets
    0.05..2.0, clipped to the existing [3,120] implementation bounds.
    R<=2 is the chosen HPO *focus*, NOT a universal gradient-safety law.
    V9's Validation-winning R~1.754 anchors 4 matched architecture controls.
    """
    ratio=float(median_unweighted_ratio)
    if not math.isfinite(ratio) or ratio<=1e-9:
        raise ValueError("Learned-state JS gradient ratio is not identifiable")
    low=max(3.0,min(120.0,0.05/ratio))
    high=max(3.0,min(120.0,2.0/ratio))
    if high<low*2.0:
        raise ValueError("TRAIN-only R-calibrated search window lacks >=2x width")
    reference_lambda=V9_SELECTED_REFERENCE_R/ratio
    anchor=max(low,min(high,reference_lambda))
    bands={}
    for name,(r_low,r_high) in {
        "weak":(0.05,0.30),"medium":(0.30,1.0),"strong":(1.0,2.0)
    }.items():
        a=max(low,r_low/ratio)
        b=min(high,r_high/ratio)
        bands[name]=[float(a),float(b)] if b>a else None
    return {
        "low":float(low),"high":float(high),"anchor":float(anchor),
        "reference_lambda":float(previous_lambda),
        "train_reference_unweighted_ratio":ratio,
        "reference_R_range":[float(low*ratio),float(high*ratio)],
        "nominal_target_R_range":[0.05,2.0],
        "v9_selected_reference_R":V9_SELECTED_REFERENCE_R,
        "v9_R_equivalent_lambda":float(reference_lambda),
        "reference_R_anchor":float(anchor*ratio),
        "gradient_influence_bands":bands,
        "band_definition":"R=lambda*r_A0: weak 0.05..0.30; medium 0.30..1.0; strong 1.0..2.0",
        "lambda_limit_reason":"Original 108478-Train A0 gradient R calibration, not V9 lambda number",
        "R_upper_is_hpo_design_target_not_safety_law":True,
        "gradient_calibration_only":True,
        "validation_selects_lambda":True,
    }


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

def canonical_digest(value):
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    ).hexdigest()

def gradient_science_identity(contract_obj):
    """Portable TRAIN gradient contract, independent of host CPU and Optuna budget.

    Source/renderer/model/objective bytes and science settings must match.
    CPU worker count, GPU microbatch, HPO trial count and walltime may differ.
    """
    keys=("schema","payload_contract_version","implementation_sha256",
          "source_manifest_sha256","simulator_config_sha256",
          "training_rows","training_parents","architecture_presets",
          "fixed_optimizer","batch_size_parents","sampling_mode",
          "training_precision","gradient_gate_contract")
    missing=[k for k in keys if k not in contract_obj]
    if missing:
        raise RuntimeError("Gradient science identity missing: "+str(missing))
    return canonical_digest({k:contract_obj[k] for k in keys})

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
        "schema":"v11_154975_gradient_informed_three_parameter_v3",
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
        "search_space":{"lambda_js":"R_FIRST_WHOLE_TRAIN_A0_REFERENCE_TARGET_0P05_TO_2",
                        "middle_stride":[2,4],"kernel_size":[5,9]},
        "gradient_gate_contract":{"warmup_min_parent_epochs":5,"warmup_max_parent_epochs":20,
                                  "warmup_stratified_train_parents":20480,
                                  "whole_training_parent_gradient_sweep":108478,
                                  "full_backbone_gradient":True,
                                  "learned_state_min_accuracy":0.30,
                                  "learned_state_max_cross_entropy":1.85,
                                  "safety_lambda":[3.0,120.0],
                                  "target_R_hpo_focus":[0.05,2.0],
                                  "v9_selected_reference_R":V9_SELECTED_REFERENCE_R,
                                  "reference_architecture":"A0 only; R is not equalized per A1/A2/A3",
                                  "supporting_v9style_combined_gradient_safety":True,
                                  "gradient_direction":"batch_and_full_cohort_cosine",
                                  "impact_bands":{"weak":[0.05,0.3],
                                                  "medium":[0.3,1.0],
                                                  "strong":[1.0,2.0]}},
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


def train_state_ready(history):
    """Train-only evidence of non-random, sufficiently stable learned features.

    This is NOT a claim of full convergence or Validation performance.
    """
    if len(history)<5:
        return False
    last=history[-1]
    if last["accuracy"]<0.30 or last["mean_ce"]>1.85:
        return False
    earlier=history[-3]["mean_ce"]
    latest=last["mean_ce"]
    if not all(math.isfinite(x) and x>0 for x in (earlier,latest)):
        return False
    # Stable CE is ideal, but continuing to improve is NOT failed learning.
    # After a substantive 20-epoch, 20480-parent Train-only warmup, a
    # near-perfect learned classifier with very low CE can be audited even if
    # training loss still improves; this does NOT imply generalization.
    stable=(earlier>=latest and (earlier-latest)/earlier<=0.05)
    well_learned=(last.get("epoch",0)>=20
                  and last["accuracy"]>=0.95
                  and last["mean_ce"]<=0.20)
    return stable or well_learned


def validate_train_only_gradient_gate(gate, contract_obj, train_records):
    """Verify portable learned-Train evidence WITHOUT accessing Validation."""
    if not isinstance(gate,dict) or gate.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS":
        raise RuntimeError("Missing or incomplete learned-state TRAIN gradient gate")
    if gate.get("science_identity_sha256")!=gradient_science_identity(contract_obj):
        raise RuntimeError("TRAIN gradient gate science contract mismatch")
    expected=hashlib.sha256("\n".join(r.material_id for r in train_records).encode()).hexdigest()
    if gate.get("training_parent_ids_sha256")!=expected or gate.get("parents_scanned")!=len(train_records):
        raise RuntimeError("TRAIN gradient gate parent coverage/identity mismatch")
    if (gate.get("parents_scanned")!=108478
        or gate.get("warmup_train_parent_count")!=20480
        or not isinstance(gate.get("warmup_train_parent_ids_sha256"),str)
        or len(gate["warmup_train_parent_ids_sha256"])!=64
        or not 5<=gate.get("warmup_parent_epochs",0)<=20):
        raise RuntimeError("TRAIN-only gate lacks full parent coverage or learned-state warmup")
    if (gate.get("learned_state_accuracy",0)<0.30
        or gate.get("learned_state_ce",99)>1.85
        or gate.get("learned_state_stable") is not True):
        raise RuntimeError("TRAIN-only JS gradient gate measured before meaningful learning")
    window=derive_train_only_js_range(gate["median_per_batch_js_ce_gradient_ratio"])
    if gate.get("lambda_window")!=window:
        raise RuntimeError("TRAIN-only JS lambda window has changed")
    if gate.get("reference_whole_train_gradient_sha256")!=V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA:
        raise RuntimeError("TRAIN gate missing pinned original whole-Train reference")
    if gate.get("supporting_v9style_safety_sha256")!=V11_SUPPLEMENTARY_SAFETY_REPORT_SHA:
        raise RuntimeError("TRAIN gate missing pinned supplementary gradient-safety report")
    validate_v9style_safety(gate.get("v9style_train_safety_audit"))
    # Direction can oppose CE despite a large JS norm. Preserve signed evidence.
    for key in ("median_batch_trunk_cosine","q10_batch_trunk_cosine",
                "q90_batch_trunk_cosine","full_train_trunk_cosine",
                "full_train_whole_model_cosine"):
        value=gate.get(key)
        if not isinstance(value,(float,int)) or not math.isfinite(value) or not -1.000001<=value<=1.000001:
            raise RuntimeError("TRAIN gradient gate missing valid direction evidence: "+key)
    required_batches=(len(train_records)+contract_obj["batch_size_parents"]-1)//contract_obj["batch_size_parents"]
    if (gate.get("batches_scanned")!=required_batches
        or gate.get("full_train_expected_batches")!=required_batches
        or gate.get("whole_train_coverage_verified") is not True
        or gate.get("training_only") is not True
        or gate.get("validation_access") is not False):
        raise RuntimeError("TRAIN gradient gate incomplete cohort coverage/provenance")
    return window


def make_or_load_train_only_gradient_gate(study_dir,train_records,sim,libs,argv,contract_obj):
    """Automatic V9-style gate: learned A0 ERM then whole-TRAIN gradient audit.

    Read NO Validation spectra/metrics. All 108478 parents are inspected once
    at learned state, with FP32 CE/JS gradients over the entire backbone.
    The gradient result constrains lambda but NEVER selects model performance.
    """
    import numpy as np
    import torch
    from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,ML4PXRDResNet1DConfig
    gate_path=Path(study_dir)/"gradient_gate.json"
    if gate_path.is_file():
        gate=json.loads(gate_path.read_text(encoding="utf-8"))
        validate_train_only_gradient_gate(gate,contract_obj,train_records)
        return gate
    if len(train_records)!=108478 or not torch.cuda.is_available():
        raise RuntimeError("Whole-TRAIN gradient gate requires 108478 parents and CUDA")
    np_lib,torch_lib,F,*_=libs
    seed=20261110
    random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    model=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18")).cuda()
    optimizer=torch.optim.AdamW(model.parameters(),
        lr=V11_FIXED_OPTIMIZER["learning_rate"],
        weight_decay=V11_FIXED_OPTIMIZER["weight_decay"])
    # Train-only *representative warmup*, full Train *gradient measurement*:
    # limit expensive 4060 optimizer updates without reducing 108478-parent
    # gradient evidence. Every class has >=64 guaranteed unique examples
    # when available, then the remaining parents are drawn uniformly.
    sample_rng=np.random.default_rng(seed)
    by_class={k:[] for k in range(7)}
    for index,record in enumerate(train_records):
        by_class[record.label].append(index)
    if any(not rows for rows in by_class.values()):
        raise RuntimeError("TRAIN-only learned-state warmup lacks one or more crystal systems")
    mandatory=set()
    for class_indices in by_class.values():
        quota=min(64,len(class_indices))
        mandatory.update(int(i) for i in sample_rng.choice(
            class_indices,size=quota,replace=False))
    warmup_count=20480
    if len(mandatory)>warmup_count:
        raise RuntimeError("Warmup class strata exceed sample budget")
    remainder=[i for i in range(len(train_records)) if i not in mandatory]
    additional=sample_rng.choice(
        remainder,size=warmup_count-len(mandatory),replace=False)
    warmup_ids=sorted(mandatory|set(int(i) for i in additional))
    warmup_records=[train_records[i] for i in warmup_ids]
    if len(warmup_records)!=warmup_count or {r.label for r in warmup_records}!=set(range(7)):
        raise RuntimeError("TRAIN-only stratified warmup sample does not cover seven crystal systems")
    one_epoch=(warmup_count+argv.batch_size-1)//argv.batch_size
    max_steps=20*one_epoch
    base=Path(study_dir)/"gradient_gate_warmup.pt"
    gate_contract={"purpose":"TRAIN_ONLY_LEARNED_GRADIENT_V1",
                   "science_identity_sha256":gradient_science_identity(contract_obj),
                   "warmup_microbatch_size":argv.microbatch_size,
                   "warmup_parent_count":warmup_count,
                   "warmup_parent_ids_sha256":hashlib.sha256(
                       "\n".join(r.material_id for r in warmup_records).encode()).hexdigest(),
                   "maximum_warmup_parent_epochs":20,
                   "training_parent_sha256":hashlib.sha256(
                       "\n".join(r.material_id for r in train_records).encode()).hexdigest(),
                   "batch_size":argv.batch_size,"epoch_steps":one_epoch,"seed":seed}
    rng=np.random.default_rng(seed)
    step=0
    history=[]
    if base.is_file():
        expected_resume_contract=gate_contract
        # Audited one-time recovery of the 2026-11-10 20-epoch laptop
        # checkpoint. A prior strict CE plateau policy halted AFTER writing
        # this complete state. Changing that *decision rule* necessarily
        # changes the script fingerprint in the portable science contract.
        # Authorize only these exact pre-patch bytes, never a generic bypass.
        archived_checkpoint_sha="d7ebd5c742c4bec63171f019aad1516e49ce5407bb9b22377a8b4c663ae85f4a"
        archived_science_sha="12718b149cb2690e20c970cf47acfdbbc3554b9f13ddd5e5393b4b3beea0e62b"
        archived_resume=(digest(base)==archived_checkpoint_sha)
        if archived_resume:
            expected_resume_contract={
                **gate_contract,"science_identity_sha256":archived_science_sha}
            event("TRAIN_ONLY_WARMUP_PINNED_RESUME",checkpoint_sha256=archived_checkpoint_sha,
                  reason="Near-perfect learned-state reached epoch20; CE plateau policy overly strict")
        step,_,_,history=restore_trial_checkpoint(
            base,model=model,optimizer=optimizer,rng=rng,
            expected_contract=expected_resume_contract,device=torch.device("cuda"),torch=torch)
        if step%one_epoch!=0 or step>max_steps:
            raise RuntimeError("Invalid TRAIN-only learned-state checkpoint milestone")
    if not train_state_ready(history):
        model.train()
        pool=V11PairPrefetchPool(sim,run_seed=seed,
            workers=argv.prefetch_workers,prefetch_batches=argv.prefetch_batches,
            native_threads=argv.native_threads,max_cached_peaks=argv.worker_peak_cache)
        next_submit=step;future_rng={};permutation_cache={}
        right=0;seen=0;ce_acc=0.;measured=0
        try:
            while step<max_steps:
                next_submit=enqueue_train_lookahead(
                    pool,rng,warmup_records,batch_size=argv.batch_size,
                    start_step=step,next_submit=next_submit,max_steps=max_steps,
                    committed_states=future_rng,sampling_mode="epoch_shuffle",
                    sampling_seed=seed,permutation_cache=permutation_cache)
                first,second,labels=pool.get(step)
                committed_state=future_rng.pop(step)
                a=torch.from_numpy(first).to("cuda")
                b=torch.from_numpy(second).to("cuda")
                y=torch.from_numpy(labels).to("cuda")
                # Match HPO's 100-epoch LR time base, not a short warmup decay.
                for group in optimizer.param_groups:
                    group["lr"]=V11_FIXED_OPTIMIZER["learning_rate"]*(
                        .05+.95*.5*(1+math.cos(math.pi*step/(100*one_epoch))))
                _,ce,_,_=paired_optimizer_step(
                    model,optimizer,a,b,y,lambda_js=0.0,
                    microbatch_size=argv.microbatch_size,loss_fn=loss_js,
                    torch=torch,F=F,amp=torch.cuda.is_bf16_supported())
                # Bounded Train-only learned-state check on every 25th optimizer step.
                if step%25==0:
                    with torch.no_grad():
                        with torch.autocast("cuda",dtype=torch.bfloat16,
                                            enabled=torch.cuda.is_bf16_supported()):
                            logits=model(a)["logits"]
                        right+=int((logits.argmax(-1)==y).sum().item())
                        seen+=len(y)
                        ce_acc+=float(ce)
                        measured+=1
                step+=1
                if step%one_epoch==0:
                    epoch=step//one_epoch
                    score=right/max(1,seen)
                    ce_mean=ce_acc/max(1,measured)
                    history.append({"epoch":epoch,"step":step,
                                    "accuracy":score,"mean_ce":ce_mean,
                                    "sampled_train_parents":seen})
                    save_trial_checkpoint(
                        base,model=model,optimizer=optimizer,step=step,best=0.,
                        best_step=0,numpy_rng_state=committed_state,
                        history=history,contract=gate_contract,
                        device=torch.device("cuda"),torch=torch)
                    event("TRAIN_ONLY_LEARNED_STATE",epoch=epoch,
                          accuracy=round(score,5),mean_ce=round(ce_mean,5))
                    right=0;seen=0;ce_acc=0.;measured=0
                    if train_state_ready(history):
                        break
        finally:
            pool.close()
    if not train_state_ready(history):
        raise RuntimeError("TRAIN-only ERM did not reach stable learned-state gate within 20 epochs; block HPO")
    # Frozen learned model is NEVER used as a starting checkpoint for HPO trials.
    model.eval()
    named_params=[(name,p) for name,p in model.named_parameters() if p.requires_grad]
    params=tuple(p for _,p in named_params)
    # Measure ALL layers, but use the convolutional trunk for V9-comparable
    # lambda influence bounds; embedding/head can have different gradient scales.
    is_backbone=tuple(not name.startswith(("embedding.","head.")) for name,_ in named_params)
    full_ce=[torch.zeros_like(p,dtype=torch.float32) for p in params]
    full_js=[torch.zeros_like(p,dtype=torch.float32) for p in params]
    # The 20,480-parent warmup has a DIFFERENT epoch length from the
    # mandatory 108,478-parent whole-Train gradient pass. Never reuse
    # warmup one_epoch when scheduling the full-cohort scan.
    full_scan_steps=(len(train_records)+argv.batch_size-1)//argv.batch_size
    scan_seed=20261111
    scan_rng=np.random.default_rng(scan_seed)
    pool=V11PairPrefetchPool(sim,run_seed=scan_seed,
        workers=argv.prefetch_workers,prefetch_batches=argv.prefetch_batches,
        native_threads=argv.native_threads,max_cached_peaks=argv.worker_peak_cache)
    ratios=[];batch_cosines=[]
    seen=0;submitted=0
    audit_microbatch=min(argv.microbatch_size,4)  # 8 GiB RTX 4060 safe default
    future_rng={};permutation_cache={}
    try:
        for step in range(full_scan_steps):
            submitted=enqueue_train_lookahead(
                pool,scan_rng,train_records,batch_size=argv.batch_size,
                start_step=step,next_submit=submitted,max_steps=full_scan_steps,
                committed_states=future_rng,sampling_mode="epoch_shuffle",
                sampling_seed=scan_seed,permutation_cache=permutation_cache)
            first,second,labels=pool.get(step)
            future_rng.pop(step)
            a=torch.from_numpy(first).to("cuda")
            b=torch.from_numpy(second).to("cuda")
            y=torch.from_numpy(labels).to("cuda")
            # FP32 full-model audit with bounded GPU microbatches. Accumulate
            # exact parent-weighted gradients for the ORIGINAL effective batch.
            # GN has no running batch-statistics; microbatching is loss-equivalent.
            batch_ce=[torch.zeros_like(p,dtype=torch.float32) for p in params]
            batch_js=[torch.zeros_like(p,dtype=torch.float32) for p in params]
            for pos in range(0,len(y),audit_microbatch):
                stop=min(pos+audit_microbatch,len(y))
                batch_fraction=(stop-pos)/len(y)
                out_a=model(a[pos:stop])["logits"].float()
                out_b=model(b[pos:stop])["logits"].float()
                _,ce,js=loss_js(out_a,out_b,y[pos:stop],0.0,torch,F)
                grad_ce=torch.autograd.grad(ce,params,retain_graph=True,allow_unused=True)
                grad_js=torch.autograd.grad(js,params,allow_unused=True)
                with torch.no_grad():
                    for i,(gc,gj) in enumerate(zip(grad_ce,grad_js)):
                        if gc is not None:
                            batch_ce[i].add_(gc.detach().float(),alpha=batch_fraction)
                        if gj is not None:
                            batch_js[i].add_(gj.detach().float(),alpha=batch_fraction)
                del out_a,out_b,ce,js,grad_ce,grad_js
            ce_sq=torch.zeros((),device="cuda")
            js_sq=torch.zeros((),device="cuda")
            dot=torch.zeros((),device="cuda")
            fraction=len(y)/len(train_records)
            with torch.no_grad():
                for i,(gc,gj) in enumerate(zip(batch_ce,batch_js)):
                    if is_backbone[i]:
                        ce_sq+=gc.square().sum()
                        js_sq+=gj.square().sum()
                        dot+=(gc*gj).sum()
                    full_ce[i].add_(gc,alpha=fraction)
                    full_js[i].add_(gj,alpha=fraction)
                den=float(ce_sq.sqrt().item())
                num=float(js_sq.sqrt().item())
                cosine=float((dot/(ce_sq.sqrt()*js_sq.sqrt()).clamp_min(1e-20)).item())
            if not all(math.isfinite(x) for x in (den,num,cosine)) or min(den,num)<=1e-12:
                raise RuntimeError("Nonfinite/zero learned-state backbone gradients")
            ratios.append(num/den)
            batch_cosines.append(max(-1.0,min(1.0,cosine)))
            seen+=len(y)
    finally:
        pool.close()
    if seen!=len(train_records) or len(ratios)!=full_scan_steps:
        raise RuntimeError("TRAIN-only full gradient scan failed parent exposure "
            f"(seen={seen}, expected={len(train_records)}, "
            f"batches={len(ratios)}, expected_batches={full_scan_steps})")
    ce_total=float(torch.stack([t.square().sum() for t in full_ce]).sum().sqrt().item())
    js_total=float(torch.stack([t.square().sum() for t in full_js]).sum().sqrt().item())
    all_dot=sum(float((a*b).sum().item()) for a,b in zip(full_ce,full_js))
    all_cosine=all_dot/max(1e-20,ce_total*js_total)
    trunk_ce=math.sqrt(sum(float(a.square().sum().item())
                           for a,include in zip(full_ce,is_backbone) if include))
    trunk_js=math.sqrt(sum(float(a.square().sum().item())
                           for a,include in zip(full_js,is_backbone) if include))
    trunk_dot=sum(float((a*b).sum().item())
                  for a,b,include in zip(full_ce,full_js,is_backbone) if include)
    if min(trunk_ce,trunk_js)<=1e-12:
        raise RuntimeError("Full Train trunk gradient direction undefined")
    trunk_cosine=trunk_dot/(trunk_ce*trunk_js)
    if ce_total<=1e-12 or not all(math.isfinite(z) for z in (ce_total,js_total)):
        raise RuntimeError("Aggregate full-TRAIN backbone gradient not identifiable")
    ratio=float(np.median(ratios))
    window=derive_train_only_js_range(ratio)
    pinned_warmup_resume_sha256=(archived_checkpoint_sha
                                 if base.is_file() and 'archived_resume' in locals() and archived_resume
                                 else None)
    gate={"status":"TRAIN_ONLY_GRADIENT_GATE_PASS",
          "science_identity_sha256":gradient_science_identity(contract_obj),
          "training_parent_ids_sha256":gate_contract["training_parent_sha256"],
          "training_only":True,"validation_access":False,
          "parents_scanned":seen,"batches_scanned":len(ratios),
          "full_train_expected_batches":full_scan_steps,
          "whole_train_coverage_verified":True,
          "warmup_parent_epochs":history[-1]["epoch"],
          "warmup_train_parent_count":warmup_count,
          "warmup_train_parent_ids_sha256":gate_contract["warmup_parent_ids_sha256"],
          "learned_state_accuracy":history[-1]["accuracy"],
          "learned_state_ce":history[-1]["mean_ce"],
          "learned_state_stable":train_state_ready(history),
          "train_only_epoch_history":history,
          "pinned_legacy_epoch20_checkpoint_sha256":pinned_warmup_resume_sha256,
          "median_per_batch_js_ce_gradient_ratio":ratio,
          "lambda_calibration_gradient_scope":"ResNet stem+residual stages, excludes embedding/head",
          "whole_model_gradient_scope":"all trainable parameters incl embedding/head",
          "q10_per_batch_ratio":float(np.quantile(ratios,0.1)),
          "q90_per_batch_ratio":float(np.quantile(ratios,0.9)),
          "median_batch_trunk_cosine":float(np.median(batch_cosines)),
          "q10_batch_trunk_cosine":float(np.quantile(batch_cosines,0.1)),
          "q90_batch_trunk_cosine":float(np.quantile(batch_cosines,0.9)),
          "full_train_trunk_cosine":float(max(-1.,min(1.,trunk_cosine))),
          "full_train_whole_model_cosine":float(max(-1.,min(1.,all_cosine))),
          "cosine_interpretation":"positive aligns CE/JS; negative opposes; norm ratio does not determine update direction",
          "full_train_ce_gradient_norm":ce_total,
          "full_train_js_gradient_norm":js_total,
          "full_train_aggregate_ratio":js_total/ce_total,
          "lambda_window":window,
          "note":"Full backbone and whole Train split; gate defines lambda bounds, Validation decides the winner"}
    validate_train_only_gradient_gate(gate,contract_obj,train_records)
    write_json(gate_path,gate)
    event("TRAIN_ONLY_GRADIENT_GATE_FROZEN",parents=seen,
          median_ratio=round(ratio,6),lambda_window=window,
          full_train_aggregate_ratio=round(js_total/ce_total,6))
    return gate




def v9style_combined_gradient_metrics(raw_js_ce_ratio, ce_js_cosine, weight):
    """Exact gradient-vector identity; one Train batch, no optimizer step."""
    ratio=float(raw_js_ce_ratio)
    cosine=float(ce_js_cosine)
    weight=float(weight)
    if (not all(math.isfinite(x) for x in (ratio,cosine,weight))
        or ratio<=0 or weight<0 or not -1.000001<=cosine<=1.000001):
        raise ValueError("Invalid CE/JS full-backbone gradient geometry")
    cosine=max(-1.0,min(1.0,cosine))
    weighted=weight*ratio
    combined=math.sqrt(max(0.,1.+weighted**2+2.*weighted*cosine))
    if combined<1e-12:
        raise ValueError("Combined gradient is degenerate")
    return {"weighted_js_ce_ratio":weighted,
            "combined_to_ce_gradient_ratio":combined,
            "combined_ce_cosine":max(-1.,min(1.,(1.+weighted*cosine)/combined))}


def validate_v9style_safety(audit):
    """Original V9 pass rule: finite, no >50x combined norm, median CE descent."""
    if not isinstance(audit,dict) or audit.get("training_only") is not True:
        raise RuntimeError("V9-style safety audit must use only Train")
    if (audit.get("validation_access") is not False
        or audit.get("sampled_train_parents")!=704
        or audit.get("batches")!=44
        or not isinstance(audit.get("sampled_train_ids_sha256"),str)
        or len(audit["sampled_train_ids_sha256"])!=64):
        raise RuntimeError("V9-style safety sample and provenance incomplete")
    rows=audit.get("lambda_probes")
    if not isinstance(rows,list) or [r.get("lambda_js") for r in rows]!=[0.3,3.,30.,60.]:
        raise RuntimeError("V9-style candidate probes not locked")
    for row in rows:
        if (row.get("status")!="PASS" or row.get("n_batches")!=44
            or not all(math.isfinite(row.get(k,float("nan")))
                        for k in ("median_combined_ce_cosine","p10_combined_ce_cosine",
                                  "max_combined_to_ce_ratio"))
            or row["median_combined_ce_cosine"]<=0
            or row["max_combined_to_ce_ratio"]>50):
            raise RuntimeError("V9-style Train combined-gradient safety failed")
    return True


def make_v9style_gate_from_frozen_train_sweep(train_records,sim,libs,argv,contract_obj):
    """Reinterpret pinned full TRAIN sweep, then run new TRAIN-only V9 safety.

    The source 108478-parent scan remains byte-for-byte unchanged and pinned.
    No Validation spectra, Test, RRUFF, or HPO is read or executed here.
    """
    import numpy as np
    import torch
    from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,ML4PXRDResNet1DConfig
    frozen=ROOT/"server_migration/gradient_gate_v11_train_108478.json"
    original_sha="7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020"
    old_identity="39eebfd9daff7e4d6a29ca069a605e49e1e44818c0fc4b6abb77c51c2162318d"
    checkpoint=ROOT/"server_runs/v11_a0_js_optuna/gradient_gate_warmup.pt"
    ck_sha="d7ebd5c742c4bec63171f019aad1516e49ce5407bb9b22377a8b4c663ae85f4a"
    if digest(frozen)!=original_sha or digest(checkpoint)!=ck_sha:
        raise RuntimeError("Pinned original Train gradient scan/checkpoint SHA mismatch")
    prior=json.loads(frozen.read_text(encoding="utf-8"))
    parent_sha=hashlib.sha256("\n".join(r.material_id for r in train_records).encode()).hexdigest()
    if (prior.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS"
        or prior.get("science_identity_sha256")!=old_identity
        or prior.get("training_parent_ids_sha256")!=parent_sha
        or prior.get("parents_scanned")!=108478
        or prior.get("whole_train_coverage_verified") is not True
        or prior.get("batches_scanned")!=6780
        or not train_state_ready(prior.get("train_only_epoch_history",[]))):
        raise RuntimeError("Historical entire-Train gradient sweep cannot be reused")
    if not torch.cuda.is_available():
        raise RuntimeError("Train-only V9-style safety requires CUDA")
    # Trusted checkpoint is loaded only after exact digest verification.
    torch.set_num_threads(1)
    model=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18")).cuda()
    saved=torch.load(checkpoint,map_location="cpu",weights_only=False)
    if saved.get("step")!=20*1280:
        raise RuntimeError("Pinned A0 learned-state checkpoint has wrong step")
    model.load_state_dict(saved["model"],strict=True)
    model.eval()
    named=[(n,p) for n,p in model.named_parameters() if p.requires_grad
           and not n.startswith(("embedding.","head."))]
    params=tuple(p for n,p in named)
    # Independent, class-balanced TRAIN subset; V9 used 44 batches.
    rng=np.random.default_rng(20261110)
    by_label={k:[] for k in range(7)}
    for idx,row in enumerate(train_records):
        by_label[row.label].append(idx)
    selected=[]
    for k in range(7):
        if len(by_label[k])<100:raise RuntimeError("Insufficient TRAIN examples in class")
        selected.extend(int(i) for i in rng.choice(by_label[k],size=100,replace=False))
    remaining=[i for i in range(len(train_records)) if i not in set(selected)]
    selected.extend(int(i) for i in rng.choice(remaining,size=4,replace=False))
    rng.shuffle(selected)
    if len(selected)!=704 or len(set(selected))!=704:
        raise RuntimeError("Safety sample must have 704 unique Train parents")
    subset=[train_records[i] for i in selected]
    subset_sha=hashlib.sha256("\n".join(x.material_id for x in subset).encode()).hexdigest()
    pool=V11PairPrefetchPool(sim,run_seed=20261110,workers=argv.prefetch_workers,
        prefetch_batches=argv.prefetch_batches,native_threads=argv.native_threads,
        max_cached_peaks=argv.worker_peak_cache)
    results={weight:{"ratios":[],"directions":[]} for weight in (0.3,3.,30.,60.)}
    start=time.monotonic()
    audit_microbatch=min(argv.microbatch_size,4)
    try:
        for step in range(44):
            if step<min(44,argv.prefetch_batches):
                pool.submit(step,subset[step*16:(step+1)*16],epoch=0,
                            global_step=step,profile="train")
        for step in range(44):
            first,second,labels=pool.get(step)
            if step+argv.prefetch_batches<44:
                future=step+argv.prefetch_batches
                pool.submit(future,subset[future*16:(future+1)*16],epoch=0,
                            global_step=future,profile="train")
            a=torch.from_numpy(first).to("cuda")
            b=torch.from_numpy(second).to("cuda")
            y=torch.from_numpy(labels).to("cuda")
            grad_ce=[torch.zeros_like(p,dtype=torch.float32) for p in params]
            grad_js=[torch.zeros_like(p,dtype=torch.float32) for p in params]
            for pos in range(0,len(y),audit_microbatch):
                stop=min(pos+audit_microbatch,len(y))
                out_a=model(a[pos:stop])["logits"].float()
                out_b=model(b[pos:stop])["logits"].float()
                _,ce,js=loss_js(out_a,out_b,y[pos:stop],0.0,torch,torch.nn.functional)
                gce=torch.autograd.grad(ce,params,retain_graph=True,allow_unused=True)
                gjs=torch.autograd.grad(js,params,allow_unused=True)
                with torch.no_grad():
                    scale=(stop-pos)/len(y)
                    for i,(x,z) in enumerate(zip(gce,gjs)):
                        if x is not None:grad_ce[i].add_(x.float(),alpha=scale)
                        if z is not None:grad_js[i].add_(z.float(),alpha=scale)
                del out_a,out_b,ce,js,gce,gjs
            ce_sq=sum(float(x.square().sum().item()) for x in grad_ce)
            js_sq=sum(float(x.square().sum().item()) for x in grad_js)
            dot=sum(float((x*z).sum().item()) for x,z in zip(grad_ce,grad_js))
            if min(ce_sq,js_sq)<1e-20:raise RuntimeError("Degenerate batch gradient")
            ratio=math.sqrt(js_sq/ce_sq)
            cosine=max(-1.,min(1.,dot/math.sqrt(ce_sq*js_sq)))
            for weight,row in results.items():
                geo=v9style_combined_gradient_metrics(ratio,cosine,weight)
                row["ratios"].append(geo["combined_to_ce_gradient_ratio"])
                row["directions"].append(geo["combined_ce_cosine"])
            if (step+1)%11==0:
                event("TRAIN_ONLY_V9_STYLE_SAFETY_PROGRESS",batches=step+1,total=44)
    finally:
        pool.close()
    probes=[]
    for weight,values in results.items():
        align=np.asarray(values["directions"],dtype=float)
        impact=np.asarray(values["ratios"],dtype=float)
        row={"lambda_js":weight,"n_batches":44,
             "median_combined_ce_cosine":float(np.median(align)),
             "p10_combined_ce_cosine":float(np.quantile(align,.1)),
             "max_combined_to_ce_ratio":float(impact.max()),
             "median_combined_to_ce_ratio":float(np.median(impact))}
        row["status"]="PASS" if row["median_combined_ce_cosine"]>0 and row["max_combined_to_ce_ratio"]<=50 else "FAIL"
        probes.append(row)
    safety={"training_only":True,"validation_access":False,
            "sampled_train_parents":len(subset),"batches":44,
            "sampled_train_ids_sha256":subset_sha,
            "seed":20261110,"checkpoint_sha256":ck_sha,
            "gradient_scope":"ResNet conv trunk FP32 A0 learned-state",
            "lambda_probes":probes,"elapsed_seconds":round(time.monotonic()-start,2),
            "interpretation":"V9 criterion checks median combined CE descent and max 50x norm; individual opposing batches retained"}
    validate_v9style_safety(safety)
    gate={**prior,
          "science_identity_sha256":gradient_science_identity(contract_obj),
          "reference_whole_train_gradient_sha256":original_sha,
          "reference_old_science_identity_sha256":old_identity,
          "lambda_window":derive_train_only_js_range(prior["median_per_batch_js_ce_gradient_ratio"]),
          "v9style_train_safety_audit":safety,
          "note":"Entire original 108478 Train sweep reused by pinned SHA; new 704-parent trained-state Train-only V9 combined-gradient safety; cuifa Validation HPO selects lambda"}
    validate_train_only_gradient_gate(gate,contract_obj,train_records)
    return gate


def make_r_reference_gate_from_frozen_reports(contract_obj):
    """Deterministically build cuifa handoff gate from TWO immutable laptop reports.

    Only the FIRST whole-Train scan determines the R-based HPO search interval;
    the later 704-parent safety check is supplemental and does not expand it.
    Requires no GPU and does not access Validation, Test, or RRUFF.
    """
    original_file=ROOT/"server_migration/gradient_gate_v11_train_108478.json"
    supplementary_file=ROOT/"server_migration/gradient_gate_v11_v9style_train_108478.json"
    if digest(original_file)!=V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA:
        raise RuntimeError("Original whole-Train gradient report SHA changed")
    if digest(supplementary_file)!=V11_SUPPLEMENTARY_SAFETY_REPORT_SHA:
        raise RuntimeError("Supplementary V9-style safety report SHA changed")
    original=json.loads(original_file.read_text(encoding="utf-8"))
    supplementary=json.loads(supplementary_file.read_text(encoding="utf-8"))
    if (original.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS"
        or original.get("science_identity_sha256")!=V11_ORIGINAL_GRADIENT_SCIENCE_ID
        or original.get("training_only") is not True
        or original.get("validation_access") is not False
        or original.get("parents_scanned")!=108478
        or original.get("batches_scanned")!=6780
        or original.get("whole_train_coverage_verified") is not True
        or supplementary.get("reference_whole_train_gradient_sha256")!=V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA
        or supplementary.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS"):
        raise RuntimeError("Pinned Train gradient reports are inconsistent")
    safety=supplementary["v9style_train_safety_audit"]
    validate_v9style_safety(safety)
    ratio=original["median_per_batch_js_ce_gradient_ratio"]
    gate={**original,
          "science_identity_sha256":gradient_science_identity(contract_obj),
          "reference_whole_train_gradient_sha256":V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA,
          "supporting_v9style_safety_sha256":V11_SUPPLEMENTARY_SAFETY_REPORT_SHA,
          "v9style_train_safety_audit":safety,
          "lambda_window":derive_train_only_js_range(ratio),
          "note":"R-FIRST: original full 108478-parent Train A0 r defines main HPO R-range; subsequent 704-parent V9-style safety is supplementary only; cuifa Validation decides lambda"}
    return gate


def architecture_peak_preservation_screen(trials, *, expected_lambda):
    """Four matched-lambda, matched-budget ResNet contrasts.

    These are hypothesis tests inspired by the SimXRD comparison of
    convolution/pooling networks, NOT results claimed by Cao et al.
    """
    if len(trials)<4:
        raise ValueError("Complete four prespecified controls first")
    found={}
    for trial in trials[:4]:
        params=trial.params
        arch=resolve_v11_trial_params(params)["architecture"]
        if arch in found or not math.isclose(float(params["lambda_js"]),
                                              float(expected_lambda),abs_tol=1e-10):
            raise RuntimeError("Architecture screen controls are not comparable")
        if getattr(trial.state,"name",str(trial.state))!="COMPLETE":
            raise RuntimeError("Architecture screen attempted before all controls complete")
        found[arch]=float(trial.value)
    if set(found)!=set(V11_ARCHITECTURES):
        raise RuntimeError("Architecture screen lacks a balanced 2x2 design")
    for value in found.values():
        if not math.isfinite(value):
            raise RuntimeError("Architecture screen received nonfinite score")
    return {"status":"EXPLORATORY_SINGLE_SEED_MATCHED_ARCHITECTURE_SCREEN",
            "matched_lambda":expected_lambda,
            "scores_by_architecture":found,
            "stride_2_vs_4_at_kernel9":found["A1"]-found["A0"],
            "stride_2_vs_4_at_kernel5":found["A2"]-found["A3"],
            "kernel_5_vs_9_at_stride4":found["A3"]-found["A0"],
            "kernel_5_vs_9_at_stride2":found["A2"]-found["A1"],
            "stride_kernel_interaction":(found["A2"]-found["A1"])-(found["A3"]-found["A0"]),
            "note":"Synthetic Validation; one seed; smaller stride/kernel not presumed superior"}


def assert_gradient_lambda(params, gate):
    """No Optuna-selected lambda can escape the pre-Validation gradient gate."""
    value=resolve_v11_trial_params(params)["lambda_js"]
    w=gate["lambda_window"]
    if not w["low"]-1e-12<=value<=w["high"]+1e-12:
        raise RuntimeError("Trial lambda is outside frozen learned-gradient search range")
    return True


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
        ("v11-parent-epoch-microbatch-20261109.7",
         "v11-gradient-gated-optuna-20261110.10"),
        ("v11-parent-epoch-budget-20261109.8",
         "v11-gradient-gated-optuna-20261110.10"),
        ("v11-focused-science-cpu-20261109.9",
         "v11-gradient-gated-optuna-20261110.10"),
        ("v11-parent-epoch-microbatch-20261109.7",
         "v11-laptop-gradient-portable-20261110.11"),
        ("v11-parent-epoch-budget-20261109.8",
         "v11-laptop-gradient-portable-20261110.11"),
        ("v11-focused-science-cpu-20261109.9",
         "v11-laptop-gradient-portable-20261110.11"),
        ("v11-gradient-gated-optuna-20261110.10",
         "v11-laptop-gradient-portable-20261110.11"),
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
                # Same 100-parent-epoch cosine horizon in HPO and final:
                # a 50-epoch pilot must not decay to floor twice as fast.
                fixed_lr_horizon=100*steps_per_parent_epoch
                group["lr"]=resolved["learning_rate"]*(
                    .05+.95*.5*(1+math.cos(math.pi*step/fixed_lr_horizon))
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
                # Never rank a 10/20/30/40-epoch transient as an HPO winner.
                if step>=min_training_steps and score>best:
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
    result={"status":"completed","name":name,"seed":seed,"architecture":resolve_v11_trial_params(params)["architecture"]+" ResNet-18-GN",
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
    resolve_v11_trial_params(params)  # Reject legacy Optuna dimensions.
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
    gate_file=Path(study_dir)/"gradient_gate.json"
    if not gate_file.is_file():
        raise RuntimeError("Final training blocked: TRAIN-only gradient gate missing")
    gate_sha=digest(gate_file)
    gate=json.loads(gate_file.read_text(encoding="utf-8"))
    if (gate.get("status")!="TRAIN_ONLY_GRADIENT_GATE_PASS"
        or gate.get("science_identity_sha256")!=gradient_science_identity(contract_obj)):
        raise RuntimeError("Final training blocked: gradient prior contract invalid")
    if json.loads(contract_file.read_text(encoding="utf-8"))!=contract_obj:
        raise RuntimeError("Final training contract differs from original HPO")
    recommendation=json.loads(rec_path.read_text(encoding="utf-8"))
    if (recommendation.get("status")!="hpo_and_confirmation_completed"
        or recommendation.get("contract_sha256")!=contract_sha
        or recommendation.get("gradient_gate_sha256")!=gate_sha
        or recommendation.get("lambda_window")!=gate.get("lambda_window")
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
        assert_gradient_lambda(dict(trial.params),gate)
    if getattr(study,"user_attrs",{}).get("gradient_gate_sha256")!=gate_sha:
        raise RuntimeError("Final training blocked: Optuna gradient gate changed")
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
    if args.mode in ("gradient","run","final"):
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
    # Two explicit machines and stages: laptop gradient, cuifa HPO.
    # Never silently calculate a lambda prior on the HPO GPU.
    gate_path=study_dir/"gradient_gate.json"
    # Both immutable Train-only reports come from the completed laptop stage.
    # The FIRST entire-Train ratio is the only source of the HPO R interval.
    portable_gate=make_r_reference_gate_from_frozen_reports(c)
    validate_train_only_gradient_gate(portable_gate,c,train_unique)
    if args.mode=="gradient":
        event("GRADIENT_STAGE_COMPLETE_NO_GPU_WORK",
              original_report_sha256=V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA,
              supporting_safety_sha256=V11_SUPPLEMENTARY_SAFETY_REPORT_SHA,
              R_reference=portable_gate["lambda_window"]["reference_R_anchor"],
              lambda_window=portable_gate["lambda_window"],
              note="Laptop Train-only gradient tasks closed; cuifa Stage0/HPO NOT_RUN")
        return
    if not gate_path.is_file() and args.mode=="run":
        write_json(gate_path,portable_gate)
        event("LAPTOP_TRAIN_R_REFERENCE_IMPORTED",
              original_report_sha256=V11_ORIGINAL_WHOLE_TRAIN_REPORT_SHA,
              lambda_window=portable_gate["lambda_window"])
    if not gate_path.is_file():
        raise RuntimeError("HPO/final blocked: frozen Train-only R-reference gate missing")
    gate=json.loads(gate_path.read_text(encoding="utf-8"))
    validate_train_only_gradient_gate(gate,c,train_unique)
    if gate!=portable_gate:
        raise RuntimeError("Local HPO gradient gate differs from immutable TRAIN R-reference evidence")
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
            "model":"ResNet-18-GN "+resolve_v11_trial_params(params)["architecture"],"simulator":"v11_tch_pseudo_voigt",
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
                sampler=optuna.samplers.TPESampler(
                    seed=20261103,n_startup_trials=4,multivariate=True),
                pruner=optuna.pruners.NopPruner())
    gate_sha=digest(study_dir/"gradient_gate.json")
    prior_sha=study.user_attrs.get("gradient_gate_sha256")
    if prior_sha is not None and prior_sha!=gate_sha:
        raise RuntimeError("Refusing to resume Optuna with changed TRAIN gradient prior")
    if not study.trials:
        study.set_user_attr("gradient_gate_sha256",gate_sha)
        for arch in V11_ARCHITECTURES:
            study.enqueue_trial(v11_architecture_trial_params(
                arch,gate["lambda_window"]["anchor"]))
        # V9 reference R defines the matched A0-A3 anchor lambda.
        # TPE then searches the main R-derived interval via lambda=R/r_A0,
        # jointly with stride/kernel. Train gradients do not select the winner.
    elif prior_sha is None:
        raise RuntimeError("Old Optuna study lacks frozen TRAIN gradient gate identity")
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
            # Four pre-registered, equal-lambda architecture controls provide
            # interpretable physical evidence. Subsequent trials are free TPE
            # suggestions in the three frozen, gradient-informed dimensions.
            trial=study.ask()
            number=trial.number
            window=gate["lambda_window"]
            params={"lambda_js":trial.suggest_float(
                        "lambda_js",window["low"],window["high"],log=True),
                    "middle_stride":trial.suggest_categorical("middle_stride",[2,4]),
                    "kernel_size":trial.suggest_categorical("kernel_size",[5,9])}
        assert_gradient_lambda(params,gate)
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
    screen=architecture_peak_preservation_screen(
        study.trials,expected_lambda=gate["lambda_window"]["anchor"])
    write_json(study_dir/"architecture_screen.json",screen)
    best_trial=complete[0]
    assert_gradient_lambda(dict(best_trial.params),gate)
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
    result={"status":"hpo_and_confirmation_completed","architecture":resolve_v11_trial_params(best_trial.params)["architecture"]+" ResNet-18-GN",
            "simulator":"v11_tch_pseudo_voigt","dataset":"154975 MP ID; 108478 unique train parents; ALL 23245 unique Validation parents",
            "best_hpo_trial":best_trial.number,"best_hpo_validation_ood_f1":best_trial.value,
            "recommended_hyperparameters":best_trial.params,"confirmation":confirmation,
            "reference_r_A0":float(gate["median_per_batch_js_ce_gradient_ratio"]),
            "selected_reference_R_A0":float(best_trial.params["lambda_js"]*gate["median_per_batch_js_ce_gradient_ratio"]),
            "reference_R_definition":"lambda_js * A0 learned-state full-Train gradient norm ratio; not actual R of A1/A2/A3",
            "gradient_gate_sha256":gate_sha,
            "lambda_window":gate["lambda_window"],
            "architecture_screen":screen,
            "validation_parent_audit":parent_audit,
            "selection_warning":"Chosen on ALL 23245 unique frozen Validation parents; confirmation seeds use same domain, not Test/RRUFF.",
            "hpo_trial_count":len(complete),"contract_sha256":digest(contract_file),
            "validation_panel_index_sha256":panel_index_sha}
    write_json(study_dir/"final_recommendation.json",result)
    event("PIPELINE_COMPLETED",summary=str(study_dir/"final_recommendation.json"),best=best_trial.value)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["plan","smoke","gradient","run","final"],default="plan")
    parser.add_argument("--trials",type=int,default=8,
                        help="At least six: four matched-lambda architecture controls; further trials are fully automatic 3D Optuna TPE")
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
    if args.mode in ("gradient","run","final"):
        study_dir=ROOT/"server_runs"/"v11_a0_js_optuna"
        with exclusive_file_lock(study_dir/".study.lock"):
            run_pipeline(args)
    else:
        run_pipeline(args)

if __name__=="__main__":
    main()
