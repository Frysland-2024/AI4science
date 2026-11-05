#!/usr/bin/env python
"""Autonomous single-GPU joint V10 A0/A1/A2 x R0/R1 full-budget comparison."""
from __future__ import annotations
from pathlib import Path
import base64,hashlib,json,math,os,subprocess,sys,time,traceback
ROOT=Path(r"E:\AI4science")
PROJECT=ROOT/"xrd_robustness"
LOCAL=ROOT/"_local"/"resnet_joint_20261103"
SCRIPTS=ROOT/"_local"
BASE_PROTO=PROJECT/"configs"/"simxrd_cnn11_pilot.20261103.json"
BASE_RESULT=PROJECT/"reports"/"simxrd_architecture_pilot_20261103"/"resnet18gn_v10_training_results.json"
BASE_HIST=PROJECT/"outputs"/"simxrd_architecture_pilot_20261103"/"resnet18gn_v10"/"seed_20260711"/"validation_history.json"
BASE_CHECK=PROJECT/"outputs"/"simxrd_architecture_pilot_20261103"/"resnet18gn_v10"/"seed_20260711"/"best.ckpt"
RUNNER=LOCAL/"run_joint_trial.py"
STEPS=49280
SEED=20260711
TRIALS=["A0_R1","A1_R0","A1_R1","A2_R0","A2_R1"]
REPO="Frysland-2024/AI4science"
BRANCH="experiments/resnet-joint-a0-a1-a2-20261103"
SUBDIR="experiments/resnet_joint_20261103"
STATE=LOCAL/"campaign_state.json"
EVENTS=LOCAL/"campaign_events.jsonl"
LOCK=LOCAL/"campaign.lock"
SUMMARY=LOCAL/"summary.json"
REPORT=LOCAL/"README.md"
RESULTS=PROJECT/"reports"/"resnet_joint_convergence_20261103"
OUTPUTS=PROJECT/"outputs"/"resnet_joint_convergence_20261103"

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
    return h.hexdigest().upper()
def readj(path):return json.loads(path.read_text(encoding="utf-8"))
def writej(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".partial")
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    temp.replace(path)
def emit(event,**kw):
    v={"event":event,"time_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),**kw}
    print(json.dumps(v,ensure_ascii=False,sort_keys=True),flush=True)
    with EVENTS.open("a",encoding="utf-8") as f:f.write(json.dumps(v,ensure_ascii=False)+"\n")
def save(status,**kw):writej(STATE,{"status":status,"timestamp":time.time(),**kw})
def core(protocol,run_id,seed):
    assert int(protocol["training"]["optimizer_steps_per_new_model"])==STEPS
    assert int(seed)==SEED
    assert protocol["data"]["counts"]=={"train":9842,"validation":2109,"test":2109}
def prepare():
    base=readj(BASE_PROTO)
    if len(base["training"]["seeds"])!=3:raise ValueError("historical seeds changed")
    pdir=LOCAL/"protocols"
    pdir.mkdir(parents=True,exist_ok=True)
    for trial in TRIALS:
        p=pdir/f"{trial}.json"
        v,recipe=trial.split("_")
        obj=json.loads(json.dumps(base))
        train=obj["training"]
        train["seeds"]=[SEED]
        train["learning_rate"]=1e-4 if recipe=="R0" else 2e-4
        train["scheduler"]="none" if recipe=="R0" else "cosine_5pct_floor"
        obj["status"]="PREREGISTERED joint architecture-conditioned convergence, full 49280 step"
        obj["joint_trial"]={"trial_id":trial,"model":v,
             "stage_transition_strides":{"A0":[4,4,4],"A1":[4,2,4],"A2":[4,2,4]}[v],
             "kernel_size":{"A0":9,"A1":9,"A2":5}[v],
             "recipe":recipe,"reuses_v10_validation_panels":True,
             "only_selection_data":"validation","no_test_rruff_access":True,
             "planned_steps":STEPS,"scheduler_horizon":STEPS,
             "comparison":"all cells one matched seed; full 49,280-step convergence",
             "notes":"R1 changes LR and scheduler together; not a causal LR-only study"}
        core(obj,trial,SEED)
        if p.exists():
            if readj(p)!=obj:raise FileExistsError("pre-registered protocol differs: "+str(p))
        else:writej(p,obj)
    if not BASE_HIST.exists() or not BASE_RESULT.exists():raise FileNotFoundError("Historical A0 baseline missing")
def load_result(trial):
    if trial=="A0_R0":
        data=readj(BASE_RESULT)
        match=[r for r in data["runs"] if r["training_seed"]==SEED]
        if len(match)!=1:raise ValueError("baseline seed missing")
        rec=match[0]
        h=readj(BASE_HIST)
        cpath=BASE_CHECK
        hpath=BASE_HIST
        full_path=BASE_RESULT
    else:
        variant=trial
        path=RESULTS/variant/"training_results.json"
        data=readj(path)
        match=[r for r in data["runs"] if r["training_seed"]==SEED]
        if len(match)!=1:raise ValueError(f"missing {trial} seed record")
        rec=match[0]
        output_dir=OUTPUTS/variant/variant/f"seed_{SEED}"
        cpath=output_dir/"best.ckpt"
        hpath=output_dir/"validation_history.json"
        h=readj(hpath)
        full_path=path
        pr=readj(LOCAL/"protocols"/f"{trial}.json")
        if rec["protocol_config_sha256"]!=sha(LOCAL/"protocols"/f"{trial}.json"):
            raise ValueError(trial+" protocol hash mismatch")
        if rec["model_config"].get("kernel_size",9)!=({"A0":9,"A1":9,"A2":5}[variant[:2]]):
            raise ValueError(trial+" kernel mismatch")
    if rec["status"]!="completed" or int(rec.get("completed_optimizer_steps", rec["optimizer_steps"]))!=STEPS:
        raise ValueError(trial+" not full-budget completed")
    if rec["checkpoint_sha256"]!=sha(cpath):
        raise ValueError(trial+" corrupted checkpoint/hash")
    if len(h)!=8 or [x["step"] for x in h]!=[6160*i for i in range(1,9)]:
        raise ValueError(trial+" nonstandard validation schedule")
    scores={int(row["step"]):float(row["ood_macro_f1"]) for row in h}
    if any(not math.isfinite(v) for v in scores.values()):
        raise ValueError(trial+" nonfinite F1")
    selected=int(rec["selected_step"])
    if selected not in scores or abs(scores[selected]-rec["selected_validation_ood_macro_f1"])>1e-7:
        raise ValueError(trial+" checkpoint selection inconsistent")
    keys=("official_split_manifest_sha256","source_records_sha256",
          "peak_cache_manifest_sha256","simulator_config_sha256",
          "train_parent_ids_sha256","evaluation_panel_index_sha256",
          "validation_material_ids_sha256","lambda_js","weight_decay","batch_size_parents")
    comparable={k:rec[k] for k in keys}
    return {"trial":trial,"record":rec,"history":h,"scores":scores,
        "keyfields":comparable,"checkpoint_path":cpath,"history_path":hpath,
        "result_path":full_path}
def main_process():
    prepare()
    baseline=load_result("A0_R0")
    if baseline["record"]["learning_rate"]!=1e-4 or baseline["record"]["scheduler"]!="none":
        raise RuntimeError("Historical baseline is not R0")
    results={"A0_R0":baseline}
    save("running",finished=["A0_R0"],next_trial=TRIALS[0])
    for i,trial in enumerate(TRIALS):
        if (RESULTS/trial/"training_results.json").exists():
            r=load_result(trial)
            emit("reuse_verified_trial",trial=trial)
        else:
            v,recipe=trial.split("_")
            emit("trial_started",trial=trial,ordinal=i+1,total=len(TRIALS))
            logfile=LOCAL/f"{trial}_console.log"
            if logfile.exists():raise FileExistsError("old console log exists; cannot launch duplicate "+trial)
            args=[sys.executable,"-u",str(RUNNER),"--variant",v,"--recipe",recipe]
            with logfile.open("w",encoding="utf-8") as f:
                proc=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,
                    timeout=3600*3)
            if proc.returncode!=0:
                raise RuntimeError(f"{trial} exited {proc.returncode}; inspect {logfile}")
            r=load_result(trial)
            emit("trial_completed",trial=trial,score=r["record"]["selected_validation_ood_macro_f1"],
                 selected_step=r["record"]["selected_step"])
        if r["keyfields"]!=baseline["keyfields"]:
            raise RuntimeError("incomparable data/simulator/labels/λ/dataset in "+trial)
        if r["record"]["simulator_version"]!="v10_pseudo_voigt_caglioti":
            raise ValueError("simulator changed unexpectedly")
        results[trial]=r
        save("running",finished=list(results),next_trial=TRIALS[i+1] if i+1<len(TRIALS) else None)
    make_report(results)
    save("complete_awaiting_git",finished=list(results))
    try:
        pub=publish(results)
    except Exception as e:
        save("complete_git_failed",finished=list(results),reason=str(e))
        raise
    save("completed_and_published",finished=list(results),**pub)
    emit("complete_and_published",**pub)

def make_report(results):
    baseline=results["A0_R0"]["record"]["selected_validation_ood_macro_f1"]
    table=[]
    summary={"schema_version":"resnet-v10-architecture-conditioned-convergence-v1",
       "status":"six_cell_full_budget_single_seed_completed",
       "experiment_date":"2026-11-03","simulator":"v10_pseudo_voigt_caglioti",
       "seed":SEED,"optimizer_steps":STEPS,
       "scope":"validation-only; no RRUFF/Test training selection",
       "question":"Which architecture and co-adapted learning-rate/schedule achieves best validation after full horizon?",
       "comparison":"A0/A1/A2 x constant 1e-4 vs cosine 2e-4; all λJS60, same data/validation",
       "caveat":"single seed across cells; full convergence budget does not prove all models globally converged",
       "trials":{}}
    for name in ["A0_R0",*TRIALS]:
        r=results[name]
        rec=r["record"]
        vals={str(row["step"]):row["ood_macro_f1"] for row in r["history"]}
        best_idx=next(i for i,row in enumerate(r["history"]) if row["step"]==rec["selected_step"])
        profile=r["history"][best_idx]["metrics"]
        broadening=profile["ood_broadening"]
        out={
          "architecture":name[:2],
          "recipe":name[-2:],
          "learning_rate":rec["learning_rate"],
          "scheduler":rec["scheduler"],
          "stage_transition_strides":{"A0":[4,4,4],"A1":[4,2,4],"A2":[4,2,4]}[name[:2]],
          "kernel_size":{"A0":9,"A1":9,"A2":5}[name[:2]],
          "parameter_count":rec["parameter_count"],
          "best_validation_ood_macro_f1":rec["selected_validation_ood_macro_f1"],
          "best_step":rec["selected_step"],
          "final_49280_validation_ood_macro_f1":r["scores"][49280],
          "best_ood_broadening_macro_f1":broadening["macro_f1"],
          "best_inrange_macro_f1":rec["selected_validation_in_range_macro_f1"],
          "steps_scores":vals,
          "seconds_including_validation":rec["elapsed_seconds"],
          "throughput_steps_per_second":rec["optimizer_steps_per_second"],
          "peak_cuda_allocated_bytes":rec.get("peak_cuda_allocated_bytes"),
          "model_checkpoint_sha256":rec["checkpoint_sha256"],
          "validation_history_sha256":sha(r["history_path"]),
          "simulator_config_sha256":rec["simulator_config_sha256"],
          "source_records_sha256":rec["source_records_sha256"],
          "test_or_rruff_used":False}
        summary["trials"][name]=out
        table.append(f"| {name} | {'/'.join(map(str,out['stage_transition_strides']))} | {out['kernel_size']} | {rec['learning_rate']:.0e} | {out['scheduler']} | {rec['parameter_count']:,} | {out['best_validation_ood_macro_f1']:.5f} | {rec['selected_step']:,} | {out['final_49280_validation_ood_macro_f1']:.5f} | {out['seconds_including_validation']:.0f} |")
    order=sorted(summary["trials"].items(),key=lambda kv:kv[1]["best_validation_ood_macro_f1"],reverse=True)
    winner,win=order[0]
    diff=win["best_validation_ood_macro_f1"]-baseline
    summary["provisional_val_winner"]=winner
    summary["provisional_gain_vs_A0_R0"]=diff
    summary["interpretation"]=("Promising single-seed validation gain, requires independent-seed confirmation" if diff>=.01
      else "No large single-seed gain; original A0 baseline remains defensible, do not overclaim architecture supremacy")
    writej(SUMMARY,summary)
    lines=[
     "# ResNet A0 / A1 / A2 × R0 / R1: architecture-conditioned full-budget comparison",
     "",
     "Experiment is **V10-only** (all six cells same simulator, parent-disjoint 14,060-parent corpus, identical Validation panels, same seed 20260711).",
     "All new cells trained for **49,280 optimizer steps** with Validation every 6,160 steps; A0_R0 reuses its verified completed historical V10 training.",
     "",
     "**R0** = AdamW LR=1e-4, constant. **R1** = AdamW LR=2e-4, cosine decay to 5% floor over the entire 49,280-step horizon.",
     "All cells retain paired CE + same-parent JS λ=60, weight decay 1e-4, batch16 parents; there was no RRUFF or Test tuning.",
     "R1 is a *bundled* learning-rate-plus-scheduler recipe, not a factorial test separating those two mechanisms.",
     "",
     "| Cell | Stage strides | Kernel | Initial LR | Schedule | Parameters | Best Val OOD F1 | Best step | Val OOD F1 @49,280 | Training seconds |",
     "|---|---|---:|---:|---|---:|---:|---:|---:|---:|",
     *table,
     "",
     "## Provisional result (single seed)",
     "",
     f"- Highest Validation OOD Macro-F1: **{winner}**, score **{win['best_validation_ood_macro_f1']:.5f}**.",
     f"- Difference versus historical A0_R0 best Validation checkpoint: **{diff:+.5f}**.",
     "- All results are single-seed and descriptive; a strong architecture claim requires replicate seeds for the chosen pair.",
     "- Architecture and learning-rate/scheduler are compared jointly, not sequentially screening off an architecture at 12,320 steps.",
     "- The 49,280-step ceiling does not prove mathematical convergence. Compare full learning curves and select predeclared best Validation checkpoint.",
     "- A2 vs A1 changes residual kernel and model size, while A0 vs A1 changes stage stride and flatten-head size. Report compute cost too.",
     "- Simulator V11/PR #59 is **NOT** part of these comparisons; no cross-simulator score comparison is used.",
     "",
     "## Evidence and provenance",
     "",
     "- All reported scores derive from machine-readable per-trial full-run result JSON and eight fixed Validation evaluations.",
     "- Model checkpoint SHA256 recorded in summary; no trained weights or large validation matrices uploaded.",
     "- Original historical V10 files and previous A1/A2 12,320-step pilot remain unchanged.",
     "- This is an experiment snapshot that references local XRD package modules, not yet a production merge of trainer implementation.",
    ]
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    emit("final_report_built",winner=winner,gain=round(diff,6))
def gh(endpoint,method="GET",data=None,optional=False):
    command=["gh","api","--method",method,endpoint]
    payload=None
    if data is not None:
        payload=json.dumps(data,ensure_ascii=False)
        command+=["--input","-"]
    ret=subprocess.run(command,input=payload,text=True,encoding="utf-8",errors="replace",
                       capture_output=True,timeout=180)
    if ret.returncode:
        if optional and ("404" in ret.stderr or "Not Found" in ret.stderr):return None
        raise RuntimeError("GitHub API failed for "+endpoint+" "+ret.stderr[-600:])
    return json.loads(ret.stdout)
def publish(results):
    ref=gh(f"repos/{REPO}/git/ref/heads/{BRANCH}",optional=True)
    if not ref:
        main=gh(f"repos/{REPO}/git/ref/heads/main")
        gh(f"repos/{REPO}/git/refs",method="POST",
           data={"ref":f"refs/heads/{BRANCH}","sha":main["object"]["sha"]})
        emit("github_branch_created",branch=BRANCH)
    artifact={
      "README.md":REPORT,
      "summary.json":SUMMARY,
      "code/run_joint_campaign.py":Path(__file__),
      "code/run_joint_trial.py":RUNNER,
      "code/prepare_resnet_joint_20261103.py":SCRIPTS/"prepare_resnet_joint_20261103.py",
      "code/run_resnet_guided_a1_20261103.py":SCRIPTS/"run_resnet_guided_a1_20261103.py",
      "code/run_resnet_guided_a2_20261103.py":SCRIPTS/"run_resnet_guided_a2_20261103.py",
      "code/joint_v10_runner.py":LOCAL/"joint_v10_runner.py",
      "source_snapshot/original_run_simxrd_architecture_pilot.py":PROJECT/"scripts"/"run_simxrd_architecture_pilot.py",
      "source_snapshot/simulator_v10.py":PROJECT/"src"/"xrd_robustness"/"simulator_v10.py",
      "source_snapshot/ml4pxrd_resnet1d.py":PROJECT/"src"/"xrd_robustness"/"models"/"ml4pxrd_resnet1d.py",
      "source_snapshot/training_prefetch.py":PROJECT/"src"/"xrd_robustness"/"training_prefetch.py",
      "source_snapshot/training_objectives.py":PROJECT/"src"/"xrd_robustness"/"training"/"objectives.py",
      "config/V10_renderer.json":PROJECT/"configs"/"simulation.simxrd_v10_pilot.20261103.json",
      "config/original_pilot_protocol.json":BASE_PROTO,
      "reference/A0_R0_full_training_results.json":BASE_RESULT,
      "reference/A0_R0_validation_history.json":BASE_HIST,
      "execution_events.jsonl":EVENTS,
    }
    for name in TRIALS:
        artifact[f"protocols/{name}.json"]=LOCAL/"protocols"/f"{name}.json"
        artifact[f"results/{name}_training_results.json"]=RESULTS/name/"training_results.json"
        artifact[f"results/{name}_validation_history.json"]=results[name]["history_path"]
        artifact[f"results/{name}_training_events.jsonl"]=RESULTS/name/"logs"/name/f"seed_{SEED}.jsonl"
    for name,file in artifact.items():
        if not file.is_file():raise FileNotFoundError("missing Git artifact "+str(file))
        if file.stat().st_size>2200000:raise RuntimeError("unexpected oversized artifact "+name)
        loc=f"{SUBDIR}/{name}"
        already=gh(f"repos/{REPO}/contents/{loc}?ref={BRANCH}",optional=True)
        body={"message":f"exp(joint): archive {name}","content":base64.b64encode(file.read_bytes()).decode("ascii"),
               "branch":BRANCH}
        if already:body["sha"]=already["sha"]
        rs=gh(f"repos/{REPO}/contents/{loc}",method="PUT",data=body)
        emit("github_file_uploaded",name=name,content_sha=rs["content"]["sha"])
    summary=readj(SUMMARY)
    prs=gh(f"repos/{REPO}/pulls?state=open&head=Frysland-2024:{BRANCH}",optional=True) or []
    if isinstance(prs,list) and prs:
        pr=prs[0]
    else:
        pr=gh(f"repos/{REPO}/pulls",method="POST",data={
            "title":"[Full-budget experiment] ResNet A0/A1/A2 × two training recipes (V10)",
            "head":BRANCH,"base":"main",
            "body":"Evidence-backed single-seed full 49,280-step V10 joint architecture × training recipe comparison, A0/A1/A2 included. Same parent-disjoint corpus, validation panels, JS λ60, batch16. No RRUFF/Test tuning. Includes source snapshots, configs, SHA256, logs, all learning curves and report. This is a provisional validation result, not statistical multi-seed confirmation. See experiments/resnet_joint_20261103/README.md."})
    if not pr.get("html_url"):raise RuntimeError("No PR URL returned")
    comment=("Full-budget six-cell ResNet architecture × training strategy joint experiment **completed and archived**. "
         f"GitHub PR: {pr['html_url']}. "
         f"Single-seed 49,280 steps each (A0_R0 historical verified); provisional Val winner "
         f"{summary['provisional_val_winner']}, Val OOD Macro-F1 {summary['trials'][summary['provisional_val_winner']]['best_validation_ood_macro_f1']:.5f}; "
         "all A0/A1/A2 results and convergence curves in the report. Not a multi-seed or RRUFF result.")
    gh(f"repos/{REPO}/issues/55/comments",method="POST",data={"body":comment})
    return {"pr_url":pr["html_url"],"branch":BRANCH,"winner":summary["provisional_val_winner"],
            "summary_path":f"https://github.com/{REPO}/blob/{BRANCH}/{SUBDIR}/summary.json"}
if __name__=="__main__":
    LOCAL.mkdir(parents=True,exist_ok=True)
    if STATE.exists() or LOCK.exists():
        raise FileExistsError("Campaign already started; check state file instead of duplicating")
    fd=os.open(LOCK,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(f"PID {os.getpid()}\n")
    try:
        emit("campaign_started",trials=TRIALS,steps=STEPS,seed=SEED,
             a0_baseline="reuse historical completed full 49,280-step seed-20260711",
             new_gpu_runs=5,concurrency=1)
        main_process()
    except Exception as e:
        emit("campaign_failed",error=repr(e),traceback=traceback.format_exc()[-4500:])
        current=readj(STATE) if STATE.exists() else {}
        if current.get("status") not in ("complete_git_failed","completed_and_published"):
            save("failed",error=repr(e),last_status=current)
        raise
