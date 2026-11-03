#!/usr/bin/env python
"""Local one-shot A1 -> A2 -> compare -> GitHub PR workflow. No Codex quota required."""
from __future__ import annotations
import base64
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT=Path(r"E:\AI4science")
PROJ=ROOT/"xrd_robustness"
LOCAL=ROOT/"_local"
A1_SCRIPT=LOCAL/"run_resnet_guided_a1_20261103.py"
A2_SCRIPT=LOCAL/"run_resnet_guided_a2_20261103.py"
RUNNER=PROJ/"scripts"/"run_simxrd_architecture_pilot.py"
REP=PROJ/"reports"
OUT=PROJ/"outputs"
A0_REPORT=REP/"simxrd_architecture_pilot_20261103"
A0_OUT=OUT/"simxrd_architecture_pilot_20261103"
BRANCH="experiments/resnet-a1-a2-20261103"
REPO="Frysland-2024/AI4science"
EXPDIR="experiments/resnet_simxrd_guided_20261103"
STATE=LOCAL/"a1_a2_orchestrator_state_20261103.json"
LOG=LOCAL/"a1_a2_orchestrator_20261103.log"
SUMMARY=LOCAL/"resnet_a0_a1_a2_summary_20261103.json"
REPORT=LOCAL/"resnet_a0_a1_a2_report_20261103.md"
FIRST_SEED=20260711
MAX_STEPS=12320

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:break
            h.update(chunk)
    return h.hexdigest().upper()
def emit(tag,**kw):
    row={"time_utc":now(),"event":tag,**kw}
    print(json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
    with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
def save_state(status,**kw):
    data={"updated_at":now(),"status":status,**kw}
    STATE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def loadj(path):return json.loads(path.read_text(encoding="utf-8"))
def validate_metrics(vals):
    for v in vals:
        if not isinstance(v,(float,int)) or not math.isfinite(v):raise ValueError("Nonfinite validation metric")

def windows_python_running(fragment):
    script=("Get-CimInstance Win32_Process | Where-Object "
        "{ $_.Name -eq 'python.exe' -and $_.CommandLine -like '*"+fragment+"*' } | "
        "Select-Object -ExpandProperty ProcessId")
    p=subprocess.run(["powershell","-NoProfile","-Command",script],capture_output=True,text=True,timeout=25)
    if p.returncode!=0:raise RuntimeError("Process probe failed: "+p.stderr[:300])
    return [int(q) for q in p.stdout.strip().split() if q.isdigit()]
def run_path(key):
    name={"A0":"simxrd_architecture_pilot_20261103","A1":"resnet_simxrd_guided_A1_20261103","A2":"resnet_simxrd_guided_A2_20261103"}[key]
    config={"A0":"resnet18gn_v10","A1":"resnet18gn_A1_stride424_kernel9","A2":"resnet18gn_A2_stride424_kernel5"}[key]
    return (OUT/name, REP/name, config)
def read_experiment(key):
    out,report,config=run_path(key)
    file=report/("resnet18gn_v10_training_results.json" if key=="A0" else f"{key}_training_results.json")
    if not file.is_file():raise FileNotFoundError(file)
    meta=loadj(file)
    runs=[r for r in meta["runs"] if int(r["training_seed"])==FIRST_SEED]
    if len(runs)!=1:raise ValueError(f"{key} expected one training record of seed {FIRST_SEED}")
    rec=runs[0]
    expected_status="completed" if key=="A0" else "diagnostic_partial"
    if rec["status"]!=expected_status:raise ValueError(f"{key} bad status {rec['status']}")
    if key=="A0":
        if int(rec["optimizer_steps"])!=49280:raise ValueError("A0 incomplete")
    elif int(rec["completed_optimizer_steps"])!=MAX_STEPS:
        raise ValueError(f"{key} not completed {MAX_STEPS} steps")
    train_dir=out/config/f"seed_{FIRST_SEED}"
    ckpt=train_dir/"best.ckpt"
    if not ckpt.is_file() or digest(ckpt)!=rec["checkpoint_sha256"]:
        raise ValueError(f"{key} checkpoint hash mismatch: {ckpt}")
    history_file=train_dir/"validation_history.json"
    history=loadj(history_file)
    scores={int(x["step"]):float(x["ood_macro_f1"]) for x in history}
    checkpoints=(6160,12320)
    if not all(s in scores for s in checkpoints):
        raise ValueError(f"{key} missing matching validation checks: {sorted(scores)}")
    validate_metrics([scores[s] for s in checkpoints])
    expected_fields=("official_split_manifest_sha256","train_parent_ids_sha256",
        "evaluation_panel_index_sha256","simulator_config_sha256",
        "source_records_sha256","peak_cache_manifest_sha256",
        "lambda_js","learning_rate","batch_size_parents")
    return {"name":key,"summary_record":rec,"scores":scores,"history_file":history_file,
        "training_result_file":file,"checkpoint_file":ckpt,
        "validation_hash":digest(history_file),"log":report/"logs"/config/f"seed_{FIRST_SEED}.jsonl",
        "fields":{k:rec[k] for k in expected_fields}}

def gh_api(endpoint, method="GET", data=None):
    cmd=["gh","api","--method",method,endpoint]
    inp=None
    if data is not None:
        cmd.extend(["--input","-"])
        inp=json.dumps(data,ensure_ascii=False)
    ret=subprocess.run(cmd,input=inp,text=True,encoding="utf-8",errors="replace",
                       capture_output=True,timeout=120)
    if ret.returncode:
        raise RuntimeError("GitHub API "+endpoint+" failed: "+ret.stderr[-700:])
    return json.loads(ret.stdout)

def publish_artifacts(summary, report_text, results):
    # Upload to dedicated branch only; never stage, clean or change dirty local Git working tree.
    ref=gh_api(f"repos/{REPO}/git/ref/heads/main")
    base=ref["object"]["sha"]
    gh_api(f"repos/{REPO}/git/refs","POST",{"ref":f"refs/heads/{BRANCH}","sha":base})
    emit("github_branch_created",branch=BRANCH,base_sha=base)
    artifacts={
        "README.md":REPORT,
        "summary.json":SUMMARY,
        "code/run_resnet_guided_a1_20261103.py":A1_SCRIPT,
        "code/run_resnet_guided_a2_20261103.py":A2_SCRIPT,
        "code/supervise_resnet_a1_a2_20261103.py":Path(__file__),
        "source_snapshot/run_simxrd_architecture_pilot.py":RUNNER,
        "source_snapshot/simulator_v10.py":PROJ/"src"/"xrd_robustness"/"simulator_v10.py",
        "source_snapshot/ml4pxrd_resnet1d.py":PROJ/"src"/"xrd_robustness"/"models"/"ml4pxrd_resnet1d.py",
        "config/v10_line_profile.json":PROJ/"configs"/"simulation.simxrd_v10_pilot.20261103.json",
        "config/v10_architecture_protocol.json":PROJ/"configs"/"simxrd_cnn11_pilot.20261103.json",
        "config/A1_protocol.json":LOCAL/"resnet_simxrd_guided_A1_protocol_20261103.json",
        "config/A2_protocol.json":LOCAL/"resnet_simxrd_guided_A2_protocol_20261103.json",
    }
    for key in ("A1","A2"):
        r=results[key]
        artifacts[f"results/{key}_training_results.json"]=r["training_result_file"]
        artifacts[f"results/{key}_validation_history.json"]=r["history_file"]
        artifacts[f"results/{key}_training_log.jsonl"]=r["log"]
    links={}
    for rel,file in artifacts.items():
        if not file.is_file():
            raise FileNotFoundError(f"Missing mandatory evidence {rel}: {file}")
        if file.stat().st_size>2*1024*1024:
            raise ValueError(f"unexpected >2MiB upload file: {file}")
        content=base64.b64encode(file.read_bytes()).decode("ascii")
        path=f"{EXPDIR}/{rel}"
        obj=gh_api(f"repos/{REPO}/contents/{path}","PUT",{
            "message":f"exp(A1/A2): add {rel}",
            "content":content,
            "branch":BRANCH
        })
        links[rel]=obj["content"]["html_url"]
        emit("github_file_pushed",name=rel,sha=obj["content"]["sha"])
    pr=gh_api(f"repos/{REPO}/pulls","POST",{
        "title":"[Experiment] SimXRD-guided ResNet A0/A1/A2 12k-step ablation",
        "head":BRANCH,"base":"main",
        "body":"Bounded 2026-11-03 Stage-2 screening, single seed 20260711, 12320 optimizer steps for A1/A2. Compares validation OOD only. No RRUFF/Test tuning. Frozen baseline A0 at same steps. Contains code snapshots, configurations, integrity hashes and completed results. This is NOT a final multi-seed, full-budget or real-domain claim. See README.md within experiments/resnet_simxrd_guided_20261103."
    })
    message=(
        "A1→A2 自动实验已完成并上传 GitHub。\n"
        f"PR: {pr['html_url']}\n"
        f"A0/A1/A2 @ 12320 steps Validation OOD Macro-F1: "+
        ", ".join(f"{k}={results[k]['scores'][12320]:.5f}" for k in ("A0","A1","A2"))+
        "\n仅为单种子、12320步初筛；完整结果见 PR。"
    )
    gh_api(f"repos/{REPO}/issues/55/comments","POST",{"body":message})
    return {"pr_url":pr["html_url"],"branch":BRANCH,
            "files":links,"commit_url":f"https://github.com/{REPO}/tree/{BRANCH}"}

def make_summary(results):
    common=results["A0"]["fields"]
    for key in ("A1","A2"):
        if results[key]["fields"]!=common:
            raise ValueError(f"Protocol leak/confound in {key}: {results[key]['fields']}")
    observations={}
    for key,r in results.items():
        rec=r["summary_record"]
        observations[key]={
            "steps":{str(k):r["scores"][k] for k in (6160,12320)},
            "parameter_count":rec["parameter_count"],
            "training_elapsed_seconds":rec["elapsed_seconds"],
            "peak_cuda_allocated_bytes":rec.get("peak_cuda_allocated_bytes"),
            "checkpoint_sha256":rec["checkpoint_sha256"],
            "validation_history_sha256":r["validation_hash"],
            "completed_optimizer_steps":rec.get("completed_optimizer_steps",49280),
            "training_status":rec["status"],
            "simulator_version":rec["simulator_version"],
        }
    observations["A1"]["delta_to_A0_12320"]=results["A1"]["scores"][12320]-results["A0"]["scores"][12320]
    observations["A2"]["delta_to_A1_12320"]=results["A2"]["scores"][12320]-results["A1"]["scores"][12320]
    return {
        "schema_version":"resnet-paper-guided-A0-A1-A2-v1",
        "created_utc":now(),
        "status":"completed_two_bounded_12k_screening_trials",
        "scientific_scope":"same-seed matched-step Validation OOD Macro-F1, not full multi-seed RRUFF or Test",
        "common_data_protocol":common,
        "architecture":{
            "A0":{"stage_transition_strides":[4,4,4],"residual_kernel":9},
            "A1":{"stage_transition_strides":[4,2,4],"residual_kernel":9},
            "A2":{"stage_transition_strides":[4,2,4],"residual_kernel":5},
        },
        "seed":FIRST_SEED,"screens_steps":[6160,12320],
        "experiments":observations,
        "disclosure":["A1/A2 have only 12320 steps each vs A0 full 49280 steps; compare only matched step checkpoints",
          "A2 kernel change also changes parameter count and receptive field; isolate as combination, not causal physical proof",
          "A1/A2 use one seed, cannot support significance/stability",
          "Do not use already-seen RRUFF-70 or Test for model selection",
          "This is local Python pilot code snapshotted into a separate GitHub experimental branch; no historical files overwritten."]
    }

def render_report(summary):
    obs=summary["experiments"]
    lines=[
        "# SimXRD-inspired ResNet A0/A1/A2 — bounded validation-only experiment",
        "",
        f"Generated {summary['created_utc']}; dataset: 14,060 unique CIF parents, fixed parent-disjoint V10 protocol.",
        "",
        "## Tested configurations",
        "",
        "| Variant | Residual stage strides | Residual kernel | Parameters | OOD Macro-F1 @ 6,160 | OOD Macro-F1 @ 12,320 | Time (s, training done) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for key in ("A0","A1","A2"):
        m=obs[key];v=summary["architecture"][key]
        lines.append(f"| {key} | {'/'.join(map(str,v['stage_transition_strides']))} | {v['residual_kernel']} | {m['parameter_count']:,} | {m['steps']['6160']:.5f} | {m['steps']['12320']:.5f} | {m['training_elapsed_seconds']:.1f} |")
    lines+=["", "## Interpretation (bounded, no RRUFF-driven selection)", "",
        f"- A1 vs A0 at 12,320 steps: {obs['A1']['delta_to_A0_12320']:+.5f} Macro-F1.",
        f"- A2 vs A1 at 12,320 steps: {obs['A2']['delta_to_A1_12320']:+.5f} Macro-F1.",
        "- Differences are descriptive for one seed and one short budget. No statistically supported final winner.",
        "- A2 changes kernel/receptive field **and model parameter count**; check memory and compute before scaling.",
        "- Existing A0 was trained for 49,280 steps; only its 6,160- and 12,320-step checkpoints are used here.",
        "- All models use identical 14,060-parent dataset/split, V10 simulator, validation panels, paired views, CE+JS lambda=60, LR=1e-4, batch 16 and seed.",
        "- This is NOT a final full-budget three-seed result and does NOT establish RRUFF advantage.",
        "- Original historical checkpoints and failed CNN11 pilot have not been altered.",
        "",
        "## Suggested next scientific decision",
        "",
        "Consider the one-seed validation differences together with increased/decreased train cost. Only a promising candidate should receive full 49,280-step multi-seed validation, and still not select on RRUFF/Test.",
        "",
        "## Reproducibility",
        "",
        "- Code launchers, copied runner and simulation/model source snapshots, resolved protocols, per-seed histories/logs, model checkpoint hashes and summary.json are in this PR.",
        "- No 8GB GPU weight/checkpoint files, CIF structures, private RRUFF spectra or large cached validation panels were uploaded.",
        "- The runner snapshot imports local xrd_robustness modules; this is a record of the exact local experiment environment, not a self-contained installable package.",
        ]
    return "\n".join(lines)+"\n"

def wait_for_A1():
    deadline=time.time()+3600*2
    consecutive_missing=0
    while time.time()<deadline:
        file=run_path("A1")[1]/"A1_training_results.json"
        if file.exists():
            r=read_experiment("A1")
            if windows_python_running("run_resnet_guided_a1_20261103.py"):
                emit("a1_result_written_waiting_for_process_exit")
                time.sleep(8);continue
            return r
        procs=windows_python_running("run_resnet_guided_a1_20261103.py")
        if procs:consecutive_missing=0
        else:consecutive_missing+=1
        if consecutive_missing>=3:
            raise RuntimeError("A1 process exited without a complete validated A1_training_results.json")
        time.sleep(20)
    raise TimeoutError("A1 timed out without completed artifacts; A2 not launched")

def main():
    if STATE.exists():
        raise FileExistsError(f"Supervisor state already exists: {STATE}; refuse duplicate launch")
    save_state("waiting_A1")
    emit("watching_A1",max_steps=MAX_STEPS)
    try:
        a1=wait_for_A1()
        emit("a1_completed",score_12320=a1["scores"][12320],
             checkpoint_sha=a1["summary_record"]["checkpoint_sha256"])
        save_state("A1_passed_A2_pending",a1_score_12320=a1["scores"][12320])
        a0=read_experiment("A0")
        if a1["fields"]!=a0["fields"]:
            raise RuntimeError("A1 protocol differs from A0; abort A2")
        if windows_python_running("run_resnet_guided_a2_20261103.py"):
            raise RuntimeError("A2 already started separately; refusing concurrent duplicate")
        if windows_python_running("run_resnet_guided_a1_20261103.py"):
            raise RuntimeError("A1 still running; refuse overlapping GPU")
        if run_path("A2")[1].exists() or run_path("A2")[0].exists():
            raise FileExistsError("A2 artifacts already exist; refuse overwrite")
        save_state("launching_A2")
        emit("a2_launch")
        with (LOCAL/"a2_direct_training_20261103.log").open("w",encoding="utf-8") as stdout:
            result=subprocess.run([sys.executable,"-u",str(A2_SCRIPT),"--max-steps",str(MAX_STEPS)],
                   stdout=stdout,stderr=subprocess.STDOUT,timeout=3600*2)
        if result.returncode:raise RuntimeError(f"A2 exited {result.returncode}; read local A2 training log")
        a2=read_experiment("A2")
        emit("a2_completed",score_12320=a2["scores"][12320],
             checkpoint_sha=a2["summary_record"]["checkpoint_sha256"])
        results={"A0":a0,"A1":a1,"A2":a2}
        summary=make_summary(results)
        SUMMARY.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        REPORT.write_text(render_report(summary),encoding="utf-8")
        save_state("completed_awaiting_github")
        published=publish_artifacts(summary,REPORT.read_text(encoding="utf-8"),results)
        emit("github_upload_complete",pr=published["pr_url"],branch=published["branch"])
        save_state("completed_and_published",**published)
    except Exception as exc:
        info={"error_type":type(exc).__name__,"error":str(exc),
              "traceback":traceback.format_exc()[-4500:]}
        emit("orchestration_failed",**info)
        save_state("failed",**info)
        raise

if __name__=="__main__":main()
