#!/usr/bin/env python
"""Run one full-budget V10 ResNet architecture x training recipe cell without Codex."""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, sys, torch
ROOT=Path(r"E:\AI4science")
PROJECT=ROOT/"xrd_robustness"
LOCAL=ROOT/"_local"/"resnet_joint_20261103"
sys.path.insert(0,str(ROOT/"_local"))
sys.path.insert(0,str(PROJECT/"src"))
from run_resnet_guided_a1_20261103 import A1Config,A1ResNet
from run_resnet_guided_a2_20261103 import A2Config,A2ResNet
from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,ML4PXRDResNet1DConfig
CODE=LOCAL/"joint_v10_runner.py"
OUT=PROJECT/"outputs"/"resnet_joint_convergence_20261103"
REPORT=PROJECT/"reports"/"resnet_joint_convergence_20261103"
VALIDATION_SRC=PROJECT/"outputs"/"simxrd_architecture_pilot_20261103"/"evaluation_cache"/"validation_v10_pseudo_voigt_caglioti_seed_20260721"
SEED=20260711
STEPS=49280
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
    return h.hexdigest().upper()
def make(variant):
    if variant=="A0":
        c=ML4PXRDResNet1DConfig(model_id="18")
        return ML4PXRDResNet1D(c),c
    if variant=="A1":
        c=A1Config()
        return A1ResNet(c),c
    if variant=="A2":
        c=A2Config()
        return A2ResNet(c),c
    raise ValueError(variant)
def run(variant,recipe,check=False):
    trial=f"{variant}_{recipe}"
    model,config=make(variant)
    with torch.inference_mode():
        logits=model(torch.zeros(1,3501))["logits"]
    assert logits.shape==(1,7) and torch.isfinite(logits).all()
    expected_k={"A0":9,"A1":9,"A2":5}[variant]
    assert model.stages[2][0].conv1.kernel_size==expected_k
    assert model.stages[2][0].conv1.stride==({"A0":4,"A1":2,"A2":2}[variant])
    print(json.dumps({"event":"model_check","trial":trial,"parameters":model.parameter_count,
                     "stage2_stride":model.stages[2][0].conv1.stride,
                     "kernel_size":expected_k}),flush=True)
    del model
    if check:return
    if not torch.cuda.is_available():raise RuntimeError("GPU unavailable; refuse CPU experiment")
    if torch.cuda.mem_get_info()[0] < 3*1024**3:raise RuntimeError("Insufficient GPU VRAM")
    protocol_path=LOCAL/"protocols"/f"{trial}.json"
    if not protocol_path.is_file():raise FileNotFoundError(protocol_path)
    proto=json.loads(protocol_path.read_text(encoding="utf-8"))
    tr=proto["training"]
    if tr["optimizer_steps_per_new_model"]!=STEPS or tr["seeds"]!=[SEED]:
        raise ValueError("Frozen full budget/seed mismatch")
    expected_lr=1e-4 if recipe=="R0" else 2e-4
    expected_schedule="none" if recipe=="R0" else "cosine_5pct_floor"
    assert float(tr["learning_rate"])==expected_lr
    assert tr["scheduler"]==expected_schedule and tr["lambda_js"]==60
    trial_out=OUT/trial
    trial_report=REPORT/trial
    if trial_out.exists() or trial_report.exists():
        raise FileExistsError("refusing implicit rerun or overwrite: "+trial)
    if sha(VALIDATION_SRC/"panel_index.json")!="5D71E77AA287252377FC851DEA4053D1C79BE5D9D4442BB9AF10C9422F31457A":
        raise RuntimeError("Validation reference panel hash changed")
    target=trial_out/"evaluation_cache"/VALIDATION_SRC.name
    target.mkdir(parents=True,exist_ok=False)
    for entry in VALIDATION_SRC.iterdir():
        if not entry.is_file():continue
        dst=target/entry.name
        if entry.suffix==".npy":os.link(entry,dst) # read-only by runner, no copy of 200+MB cache
        else:shutil.copy2(entry,dst)
    spec=importlib.util.spec_from_file_location("frozen_joint_v10_runner",CODE)
    pilot=importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(pilot)
    pilot.PROTOCOL_PATH=protocol_path
    pilot._make_model=lambda model_id:make(variant) if model_id=="resnet18gn" else (_ for _ in ()).throw(ValueError(model_id))
    _,_,sim=pilot._load_config()
    print(json.dumps({"event":"training_begin","trial":trial,"steps":STEPS,"seed":SEED,
                      "config_sha256":sha(protocol_path),"renderer":"V10"}),flush=True)
    result=pilot.train_model(model_id="resnet18gn",config_id=trial,
         simulator_version=pilot.SIMULATOR_VERSIONS["v10"],
         sim_config=sim,sim_config_path=pilot.V10_SIM_PATH,
         line_profile=sim["line_profile"],
         data_root=pilot.DEFAULT_DATA_ROOT,
         output_root=trial_out,report_root=trial_report,
         device=torch.device("cuda"),training_seeds=[SEED],max_steps=STEPS)
    pilot._write_json(trial_report/"training_results.json",result)
    r=result["runs"][0]
    if r["status"]!="completed" or r["completed_optimizer_steps"]!=STEPS:
        raise RuntimeError("training result not complete")
    print(json.dumps({"event":"trial_completed","trial":trial,
         "best_validation_ood_macro_f1":r["selected_validation_ood_macro_f1"],
         "selected_step":r["selected_step"],
         "checkpoint_sha256":r["checkpoint_sha256"]}),flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True,choices=["A0","A1","A2"])
    ap.add_argument("--recipe",required=True,choices=["R0","R1"])
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    run(args.variant,args.recipe,args.check)
