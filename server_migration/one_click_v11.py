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
        "source_records":131729, "training_parents":108483,"validation_parents":23246,
        "held_out_test_parents":23246, "test_and_rruff_access":"prohibited",
        "architecture":"ML4PXRDResNet1D(model_id=18) A0; stride 4/4/4, kernel 9",
        "train_mode":"dynamic_js_same_parent",
        "batch_size_parents":args.batch_size,
        "hpo_steps":args.hpo_steps,
        "confirmation_steps":args.confirm_steps,
        "eval_interval_steps":args.eval_every,
        "validation_per_class":args.validation_per_class,
        "validation_seed":20260721,
        "search_seed":20261103,
        "hpo_seed":20260711,
        "confirmation_seeds":[20261104,20261105],
        "max_new_trials":args.trials,
        "search_space":{"learning_rate":[5e-5,3e-4],"lambda_js":[15.,120.],
                        "weight_decay":[1e-6,1e-3],"scheduler":["cosine_5pct_floor","none"]},
        "selection":"highest mean 6 frozen simulated OOD Validation Macro-F1; independent-seed confirmation on same frozen subset",
        "full_validation_final":False,
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

def subset(records,per_class):
    by_class=defaultdict(list)
    for rec in records:by_class[rec.label].append(rec)
    rng=random.Random(20260721)
    selected=[]
    for label in range(7):
        rows=by_class[label]
        if len(rows)<per_class:raise ValueError(f"Class {label} has too few validation rows")
        selected.extend(rng.sample(rows,per_class))
    return sorted(selected,key=lambda row:row.material_id)

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

def validate(model,records,peaks,val_factory,device,libs,batch_size,profiles):
    np,torch,F,_,_,render_pair_batch,*tail=libs
    metrics=tail[-1]
    result={}
    model.eval()
    for profile in profiles:
        labels=[];probas=[]
        for at in range(0,len(records),batch_size):
            rows=records[at:at+batch_size]
            x1,x2,y=render_pair_batch(rows,peaks,val_factory,epoch=0,global_step=0,profile=profile)
            with torch.inference_mode():
                a=model(x1.to(device))["logits"].float()
                b=model(x2.to(device))["logits"].float()
                p=0.5*(torch.softmax(a,-1)+torch.softmax(b,-1))
            probas.append(p.cpu().numpy());labels.extend(y.tolist())
        probabilities=np.concatenate(probas,axis=0)
        pred=probabilities.argmax(axis=1).tolist()
        row=metrics(labels,pred,probabilities=probabilities,num_classes=7)
        result[profile]={"macro_f1":float(row["macro_f1"]),"accuracy":float(row["accuracy"]),"ece":float(row["ece"])}
    return result

def atomically_save_torch(path,object_to_save,torch):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".partial")
    torch.save(object_to_save,temp)
    os.replace(temp,path)

def trial_run(name,params,seed,max_steps,study_dir,train_records,val_records,peaks,sim,libs,argv):
    np,torch,F,_,_,render_pair_batch,build_online_view_factory,ML4PXRDResNet1D,ML4PXRDResNet1DConfig,PhysicsParameterSampler,metrics=libs
    root=study_dir/"trials"/name
    cfg={"params":params,"seed":seed,"max_steps":max_steps,"batch_size":argv.batch_size,
         "eval_every":argv.eval_every,"sim_config_sha256":digest(XRD/"configs/simulation.v11_tch_pseudo_voigt.json"),
         "validation_subset_ids_sha256":hashlib.sha256("\n".join(r.material_id for r in val_records).encode()).hexdigest()}
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
    profiles=("ood_shift_negative","ood_shift_positive","ood_broadening","ood_noise","ood_background","ood_texture")
    started=time.monotonic()
    while step<max_steps:
        idx=rng.choice(n,size=argv.batch_size,replace=False)
        rows=[train_records[int(i)] for i in idx]
        x1,x2,targets=render_pair_batch(rows,peaks,train_fac,
                epoch=(step*argv.batch_size//n),global_step=step,profile="train")
        x1=x1.to(device);x2=x2.to(device);targets=targets.to(device)
        for group in optimizer.param_groups:
            if params["scheduler"]=="none":group["lr"]=float(params["learning_rate"])
            else:
                group["lr"]=float(params["learning_rate"])*(.05+.95*.5*(1+math.cos(math.pi*step/max_steps)))
        optimizer.zero_grad(set_to_none=True)
        use_amp=torch.cuda.is_bf16_supported()
        with torch.autocast("cuda",dtype=torch.bfloat16,enabled=use_amp):
            a=model(x1)["logits"];b=model(x2)["logits"]
            loss,ce,js=loss_js(a,b,targets,float(params["lambda_js"]),torch,F)
        if not bool(torch.isfinite(loss).item()):
            raise RuntimeError(f"nonfinite loss {name} step {step+1}")
        loss.backward()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),max_norm=10.0,error_if_nonfinite=True)
        optimizer.step()
        step+=1
        if step%argv.eval_every==0 or step==max_steps:
            row=validate(model,val_records,peaks,val_fac,device,libs,argv.batch_size,profiles)
            score=sum(row[p]["macro_f1"] for p in profiles)/6.0
            if not math.isfinite(score):raise RuntimeError("nonfinite validation macro F1")
            history.append({"step":step,"mean_ood_macro_f1":score,"profiles":row,
                            "train_last_loss":float(loss.detach().cpu()),
                            "last_ce":float(ce.detach().cpu()),"last_js":float(js.detach().cpu()),
                            "lr":optimizer.param_groups[0]["lr"]})
            if score>best:
                best=score;best_step=step
                atomically_save_torch(root/"best.pt",{"model":model.state_dict(),"step":step,
                    "validation_ood_macro_f1":score,"contract":cfg},torch)
            atomically_save_torch(resume,{"model":model.state_dict(),"optimizer":optimizer.state_dict(),
                "step":step,"best":best,"best_step":best_step,"numpy_rng":rng.bit_generator.state,
                "torch_rng":torch.get_rng_state(),"cuda_rngs":torch.cuda.get_rng_state_all(),
                "history":history,"contract":cfg},torch)
            write_json(root/"history.json",history)
            event("trial_validation",name=name,step=step,score=round(score,6),
                  best=round(best,6),gpu_seconds=round(time.monotonic()-started,1))
    result={"status":"completed","name":name,"seed":seed,"architecture":"A0 ResNet-18-GN",
            "parameters":params,"completed_steps":step,"best_step":best_step,
            "best_validation_ood_macro_f1":best,"best_checkpoint_sha256":digest(root/"best.pt"),
            "last_checkpoint_sha256":digest(root/"last.pt"),
            "validation_sample_parents":len(val_records),"profiles":list(profiles),
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
    parser.add_argument("--eval-every",type=int,default=1540)
    parser.add_argument("--batch-size",type=int,default=16)
    parser.add_argument("--validation-per-class",type=int,default=128)
    parser.add_argument("--max-gpu-hours",type=float,default=12.0)
    args=parser.parse_args()
    if args.trials<2 or args.trials>12 or args.hpo_steps<1 or args.confirm_steps<args.hpo_steps:
        raise ValueError("bounded trials and training steps required")
    if args.validation_per_class<2 or args.validation_per_class>500:
        raise ValueError("validation-per-class out of bounded range")
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
        raise RuntimeError("Wrong parent-disjoint manifest sizes")
    val_small=subset(val,args.validation_per_class)
    peaks=load_peak_tables(train+val_small)
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
            row=trial_run(name,params,20260711,args.hpo_steps,study_dir,train,val_small,peaks,sim,libs,args)
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
        row=trial_run(name,params,seed,args.confirm_steps,study_dir,train,val_small,peaks,sim,libs,args)
        confirmation.append({"seed":seed,"score":row["best_validation_ood_macro_f1"],
                             "checkpoint_sha256":row["best_checkpoint_sha256"]})
    result={"status":"hpo_and_confirmation_completed","architecture":"A0 ResNet-18-GN",
            "simulator":"v11_tch_pseudo_voigt","dataset":"154975 MP ID, 108483 train; Validation subset only",
            "best_hpo_trial":best_trial.number,"best_hpo_validation_ood_f1":best_trial.value,
            "recommended_hyperparameters":best_trial.params,"confirmation":confirmation,
            "selection_warning":"Chosen on same frozen Validation used for TPE; confirmation seeds are not external Test/RRUFF validation.",
            "hpo_trial_count":len(complete),"contract_sha256":digest(contract_file)}
    write_json(study_dir/"final_recommendation.json",result)
    event("PIPELINE_COMPLETED",summary=str(study_dir/"final_recommendation.json"),best=best_trial.value)
if __name__=="__main__":
    main()
