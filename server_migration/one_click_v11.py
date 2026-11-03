#!/usr/bin/env python3
"""Portable V11/154975 ResNet-A0 + Dynamic JS bounded Optuna pipeline.

No locked Test/RRUFF access; old-data V10 supervisor is deliberately not used.
Use plan/smoke locally, and --mode run only on a CUDA Linux machine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from v11_prefetch import V11PairPrefetchPool, iter_prefetched_batches, enqueue_train_lookahead

ROOT=Path(os.environ.get("AI4SCIENCE_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
XRD=ROOT/"xrd_robustness"
sys.path.insert(0,str(XRD/"src"))

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

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
        "schema":"v11_154975_resnet_a0_js_optuna_v1",
        "source_manifest_sha256":expected_records,
        "simulator_config_sha256":digest(sim),
        "source_records":131729,
        "training_rows":108483, "training_parents":108478,
        "validation_rows":23246, "validation_parents":23245,
        "held_out_test_parents":23245, "test_and_rruff_access":"prohibited",
        "architecture":"ML4PXRDResNet1D(model_id=18) A0; stride 4/4/4, kernel 9",
        "train_mode":"dynamic_js_same_parent",
        "batch_size_parents":args.batch_size,
        "prefetch_workers":args.prefetch_workers,
        "prefetch_batches":args.prefetch_batches,
        "native_threads":args.native_threads,
        "worker_peak_cache":args.worker_peak_cache,
        "pipeline":"V11 deterministic multiprocessing, lazy PeakTable-LRU, BF16, pinned transfers, frozen Validation memmaps",
        "hpo_steps":args.hpo_steps,
        "confirmation_steps":args.confirm_steps,
        "eval_interval_steps":args.eval_every,
        "validation_mode":"FULL_PARENT_DISJOINT",
        "validation_rows":23246,
        "validation_parents":23245,
        "validation_seed":20260721,
        "search_seed":20261103,
        "hpo_seed":20260711,
        "confirmation_seeds":[20261104,20261105],
        "max_new_trials":args.trials,
        "search_space":{"learning_rate":[5e-5,3e-4],"lambda_js":[15.,120.],
                        "weight_decay":[1e-6,1e-3],"scheduler":["cosine_5pct_floor","none"]},
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
    parent_ids_hash=hashlib.sha256(
        "\n".join(rec.material_id for rec in records).encode("utf-8")
    ).hexdigest()
    identity={
        "version":"v11-full-validation-dual-view-cache-v1",
        "source_manifest_sha256":digest(XRD/"data/merged_154975_v11/training_records.v1.jsonl"),
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
        if index.get("identity")!=identity:
            raise RuntimeError("Existing Validation cache identity mismatch; refuse overwrite")
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
    for profile in VALIDATION_OOD_PROFILES:
        if profile not in sim["profiles"]:
            raise RuntimeError(f"Missing V11 validation profile: {profile}")
        names=(profile+".first.npy",profile+".second.npy")
        paths=[base/name for name in names]
        entry=index["entries"].get(profile)
        if entry is not None:
            for file,expected_hash in zip(paths,entry["sha256"]):
                if not file.exists() or digest(file)!=expected_hash:
                    raise RuntimeError(f"Frozen Validation cache corrupted: {file}")
            event("validation_panel_reused",profile=profile,parents=len(records))
        else:
            # Temporary files are never used as scored Validation evidence.
            temporary=[base/(profile+f".{view}.partial.npy") for view in ("first","second")]
            for item in temporary:
                if item.exists():item.unlink()
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
    if pool is not None:
        pool.close()
    return panels,digest(index_path)

def validate(model,records,peaks,val_factory,device,libs,batch_size,profiles,panels=None):
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
                                    enabled=device.type=="cuda" and torch.cuda.is_bf16_supported()):
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

def trial_run(name,params,seed,max_steps,study_dir,train_records,val_records,peaks,sim,libs,argv,
              validation_panels=None,validation_panel_index_sha256=None):
    np,torch,F,_,_,render_pair_batch,build_online_view_factory,ML4PXRDResNet1D,ML4PXRDResNet1DConfig,PhysicsParameterSampler,metrics=libs
    root=study_dir/"trials"/name
    cfg={"params":params,"seed":seed,"max_steps":max_steps,"batch_size":argv.batch_size,
         "eval_every":argv.eval_every,"sim_config_sha256":digest(XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
         "validation_mode":"FULL_PARENT_DISJOINT","validation_parent_count":len(val_records),
         "validation_parent_ids_sha256":hashlib.sha256("\n".join(r.material_id for r in val_records).encode()).hexdigest(),
         "training_parent_count":len(train_records),
         "validation_panel_index_sha256":validation_panel_index_sha256}
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
        if row.get("status")=="completed" and row["completed_steps"]==max_steps:
            event("reuse_completed_trial",name=name,score=row["best_validation_ood_macro_f1"])
            return row
        raise RuntimeError("Existing result is incomplete/changed")
    if not torch.cuda.is_available():raise RuntimeError("A CUDA server is required for real HPO")
    device=torch.device("cuda")
    # Seed BEFORE model initialization; otherwise multi-seed comparisons are invalid.
    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    model=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18")).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=float(params["learning_rate"]),weight_decay=float(params["weight_decay"]))
    if model.parameter_count<10000000 or model.parameter_count>20000000:
        raise RuntimeError("Unexpected A0 parameter count")
    train_fac=factory(sim,seed,PhysicsParameterSampler,build_online_view_factory)
    val_fac=factory(sim,20260721,PhysicsParameterSampler,build_online_view_factory)
    rng=np.random.default_rng(seed)
    step=0;best=-1.;best_step=0;history=[]
    resume=root/"last.pt"
    if resume.is_file():
        saved=torch.load(resume,map_location=device,weights_only=False)
        if saved["contract"]!=cfg:raise RuntimeError("Checkpoint protocol mismatch")
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        rng.bit_generator.state=saved["numpy_rng"]
        torch.set_rng_state(saved["torch_rng"].cpu())
        torch.cuda.set_rng_state_all([x.cpu() for x in saved["cuda_rngs"]])
        step=saved["step"];best=saved["best"];best_step=saved["best_step"];history=saved["history"]
        event("resumed",name=name,step=step)
    n=len(train_records)
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
    next_submit=step
    try:
        while step<max_steps:
            # CPU prepares upcoming spectra while GPU trains on the first
            # submitted step. Only the MAIN process advances the sampling RNG.
            next_submit=enqueue_train_lookahead(
                pool,rng,train_records,batch_size=argv.batch_size,
                start_step=step,next_submit=next_submit,max_steps=max_steps,
                committed_states=future_rng,
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
                if params["scheduler"]=="none":
                    group["lr"]=float(params["learning_rate"])
                else:
                    group["lr"]=float(params["learning_rate"])*(
                        .05+.95*.5*(1+math.cos(math.pi*step/max_steps))
                    )
            optimizer.zero_grad(set_to_none=True)
            use_amp=torch.cuda.is_bf16_supported()
            with torch.autocast("cuda",dtype=torch.bfloat16,enabled=use_amp):
                a=model(x1)["logits"];b=model(x2)["logits"]
                loss,ce,js=loss_js(a,b,targets,float(params["lambda_js"]),torch,F)
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError(f"nonfinite loss {name} step {step+1}")
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(
                model.parameters(),max_norm=10.0,error_if_nonfinite=True,
            )
            optimizer.step()
            step+=1
            if step%argv.eval_every==0 or step==max_steps:
                row=validate(
                    model,val_records,peaks,val_fac,device,libs,argv.batch_size,
                    profiles,panels=validation_panels,
                )
                score=sum(row[p]["macro_f1"] for p in profiles)/6.0
                if not math.isfinite(score):
                    raise RuntimeError("nonfinite validation macro F1")
                history.append({
                    "step":step,"mean_ood_macro_f1":score,"profiles":row,
                    "train_last_loss":float(loss.detach().cpu()),
                    "last_ce":float(ce.detach().cpu()),
                    "last_js":float(js.detach().cpu()),
                    "lr":optimizer.param_groups[0]["lr"],
                    "prefetch_workers":argv.prefetch_workers,
                    "prefetch_batches":argv.prefetch_batches,
                })
                if score>best:
                    best=score;best_step=step
                    atomically_save_torch(root/"best.pt",{
                        "model":model.state_dict(),"step":step,
                        "validation_ood_macro_f1":score,"contract":cfg,
                    },torch)
                atomically_save_torch(resume,{
                    "model":model.state_dict(),"optimizer":optimizer.state_dict(),
                    "step":step,"best":best,"best_step":best_step,
                    "numpy_rng":committed_rng_state,
                    "torch_rng":torch.get_rng_state(),
                    "cuda_rngs":torch.cuda.get_rng_state_all(),
                    "history":history,"contract":cfg,
                },torch)
                write_json(root/"history.json",history)
                event(
                    "trial_validation",name=name,step=step,
                    score=round(score,6),best=round(best,6),
                    gpu_seconds=round(time.monotonic()-started,1),
                )
    finally:
        pool.close()
    result={"status":"completed","name":name,"seed":seed,"architecture":"A0 ResNet-18-GN",
            "parameters":params,"completed_steps":step,"best_step":best_step,
            "best_validation_ood_macro_f1":best,"best_checkpoint_sha256":digest(root/"best.pt"),
            "last_checkpoint_sha256":digest(root/"last.pt"),
            "validation_unique_parents":len(val_records),"profiles":list(profiles),
            "gpu_seconds":time.monotonic()-started,
            "scope":"fixed simulated Validation only; no Test/RRUFF"}
    write_json(final,result)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["plan","smoke","run"],default="plan")
    parser.add_argument("--trials",type=int,default=6)
    parser.add_argument("--hpo-steps",type=int,default=6160)
    parser.add_argument("--confirm-steps",type=int,default=12320)
    parser.add_argument("--eval-every",type=int,default=6160)
    parser.add_argument("--batch-size",type=int,default=16)
    parser.add_argument("--prefetch-workers",type=int,default=4)
    parser.add_argument("--prefetch-batches",type=int,default=3)
    parser.add_argument("--native-threads",type=int,default=1)
    parser.add_argument("--worker-peak-cache",type=int,default=512)
    parser.add_argument("--max-gpu-hours",type=float,default=12.0)
    args=parser.parse_args()
    if args.trials<2 or args.trials>12 or args.hpo_steps<1 or args.confirm_steps<args.hpo_steps:
        raise ValueError("bounded trials and training steps required")
    if not (1<=args.prefetch_workers<=16 and 1<=args.prefetch_batches<=8
            and 1<=args.native_threads<=4 and 16<=args.worker_peak_cache<=8192):
        raise ValueError("Unbounded or invalid V11 prefetch resources")
    c=contract(args)
    study_dir=ROOT/"server_runs"/"v11_a0_js_optuna"
    contract_file=study_dir/"contract.json"
    if contract_file.is_file():
        if json.loads(contract_file.read_text(encoding="utf-8"))!=c:
            raise RuntimeError("Existing study contract changed; refuse overwrite")
    elif args.mode=="run":
        write_json(contract_file,c)
    if args.mode=="plan":
        event("PLAN_ONLY",contract=c,cache_root=str(XRD/"data/merged_154975_v11"),
              note="No GPU training or trial created. Unzip full caches and verify hashes before run.")
        return
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
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage="sqlite:///"+(study_dir/"optuna.sqlite3").as_posix()
    study=optuna.create_study(study_name="v11_154975_a0_sameparent_js",storage=storage,
                direction="maximize",load_if_exists=True,
                sampler=optuna.samplers.TPESampler(seed=20261103,n_startup_trials=3),
                pruner=optuna.pruners.NopPruner())
    if not study.trials:
        study.enqueue_trial({"learning_rate":2e-4,"lambda_js":60.0,
            "weight_decay":1e-4,"scheduler":"cosine_5pct_floor"})
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
            if len(params)!=4:raise RuntimeError("Incomplete stored trial params")
            number=frozen.number
        else:
            trial=study.ask()
            number=trial.number
            params={"learning_rate":trial.suggest_float("learning_rate",5e-5,3e-4,log=True),
                "lambda_js":trial.suggest_float("lambda_js",15.,120.),
                "weight_decay":trial.suggest_float("weight_decay",1e-6,1e-3,log=True),
                "scheduler":trial.suggest_categorical("scheduler",["cosine_5pct_floor","none"])}
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
    complete=sorted([t for t in study.trials if t.state==TrialState.COMPLETE],key=lambda t:-t.value)
    if not complete:raise RuntimeError("No valid completed HPO trial")
    best_trial=complete[0]
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
    result={"status":"hpo_and_confirmation_completed","architecture":"A0 ResNet-18-GN",
            "simulator":"v11_tch_pseudo_voigt","dataset":"154975 MP ID; 108478 unique train parents; ALL 23245 unique Validation parents",
            "best_hpo_trial":best_trial.number,"best_hpo_validation_ood_f1":best_trial.value,
            "recommended_hyperparameters":best_trial.params,"confirmation":confirmation,
            "validation_parent_audit":parent_audit,
            "selection_warning":"Chosen on ALL 23245 unique frozen Validation parents; confirmation seeds use same domain, not Test/RRUFF.",
            "hpo_trial_count":len(complete),"contract_sha256":digest(contract_file)}
    write_json(study_dir/"final_recommendation.json",result)
    event("PIPELINE_COMPLETED",summary=str(study_dir/"final_recommendation.json"),best=best_trial.value)
if __name__=="__main__":
    main()
