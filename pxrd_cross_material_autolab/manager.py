"""Auditable, bounded, sequential cross-material experiment manager (stdlib)."""
from __future__ import annotations
import argparse, contextlib, csv, math, hashlib, importlib, json, os, platform, shutil, subprocess, sys, time, traceback
from pathlib import Path

STATES = {"PASS", "FAIL", "SKIPPED", "BLOCKED", "NOT_RUN"}
def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp."+str(os.getpid()))
    with temp.open("wb") as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)
def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def event(root, kind, **data):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    with (root/"events.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(dict({"time":time.time(),"kind":kind},**data),ensure_ascii=False,allow_nan=False)+"\n"); f.flush(); os.fsync(f.fileno())
def stage(root, name, status, **data):
    if status not in STATES: raise ValueError(status)
    record=dict(stage=name,status=status,time=time.time(),**data)
    atomic(Path(root)/"status.json",record); event(root,"stage",**record)
    return record

def command(root, args, timeout=30):
    """Every child process is logged including timeouts and missing executables."""
    started=time.time()
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)
        rec=dict(command=args,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:
        rec=dict(command=args,exit_code=None,error=str(exc))
    rec["seconds"]=time.time()-started; event(root,"subprocess",**rec)
    return rec

def inventory(root):
    result=dict(python=sys.version,platform=platform.platform(),disk_free_bytes=shutil.disk_usage(Path(root).resolve().anchor).free,
                gpu=command(root,["nvidia-smi","--query-gpu=name,memory.used,utilization.gpu","--format=csv,noheader,nounits"]),
                gpu_processes=command(root,["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv,noheader,nounits"]),
                git=command(root,["git","rev-parse","HEAD"]))
    atomic(Path(root)/"inventory.json",result); return result

def source_hashes():
    return {str(p):sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}

def freeze(root, config, prereg):
    root=Path(root); prereg=Path(prereg)
    if not prereg.is_file(): raise ValueError("Preregistration must exist before freezing")
    mats=config.get("materials",[])
    if not mats or len(mats)>12: raise ValueError("Require 1..12 attempted materials")
    ids=[m["id"] for m in mats]
    if len(set(ids))!=len(ids) or any(Path(i).name!=i or i in (".","..") for i in ids): raise ValueError("Unique safe material ids required")
    if len(config.get("training",{}).get("seeds",[0,1,2]))>3 or config.get("training",{}).get("epochs",24)>24: raise ValueError("Training budget exceeds authorization")
    if config.get("wall_budget_seconds",28800)>28800 or config.get("gpu_budget_seconds",14400)>14400: raise ValueError("Runtime budget exceeds authorization")
    cifs={m["id"]:sha(m["cif_path"]) if m.get("cif_path") and Path(m["cif_path"]).is_file() else None for m in mats}
    for m in mats:
        if cifs[m["id"]] is not None and m.get("cif_sha256") and m["cif_sha256"]!=cifs[m["id"]]: raise ValueError("CIF provenance hash mismatch: "+m["id"])
    identity=dict(config_sha256=hashlib.sha256(canonical(config)).hexdigest(),preregistration_sha256=sha(prereg),cif_sha256=cifs,source_sha256=source_hashes())
    if (root/"manifest.json").exists():
        old=read(root/"manifest.json")
        if old["identity"]!=identity: raise ValueError("Frozen manifest mismatch; use a distinct run directory, never change opened test")
        if read(root/"config.json")!=config: raise ValueError("Frozen config mismatch")
        return old
    root.mkdir(parents=True,exist_ok=True)
    manifest=dict(identity=identity,created=time.time(),preregistration_path=str(prereg.resolve()))
    atomic(root/"config.json",config); atomic(root/"manifest.json",manifest)
    event(root,"frozen",identity=identity); return manifest

def verify(root):
    root=Path(root); manifest=read(root/"manifest.json"); config=read(root/"config.json")
    freeze(root,config,manifest["preregistration_path"])
    for p in root.glob("materials/*/status.json"):
        if read(p)["status"] not in STATES: raise ValueError("Invalid state "+str(p))
    checked=[]
    for statusfile in root.glob("materials/*/status.json"):
        record=read(statusfile)
        if record.get("status")=="PASS" and record.get("result"):
            resultfile=Path(record["result"])
            if not resultfile.is_file(): raise ValueError("Missing experiment result: "+str(resultfile))
            result=read(resultfile); samplefile=resultfile.parent/"per_sample.jsonl"
            if not samplefile.is_file(): raise ValueError("Missing per-sample results: "+str(samplefile))
            rows=[json.loads(line) for line in samplefile.read_text(encoding="utf-8").splitlines() if line.strip()]
            summarize=importlib.import_module("pxrd_cross_material_autolab.experiment").summarize
            recomputed=summarize(rows)
            if not equivalent(recomputed,result["summary"]): raise ValueError("Metric recomputation mismatch: "+str(resultfile))
            artifactfile=resultfile.parent/"artifacts.json"
            if artifactfile.exists():
                for relative,digest in read(artifactfile).items():
                    path=resultfile.parent/relative
                    if not path.is_file() or sha(path)!=digest: raise ValueError("Artifact hash mismatch: "+str(path))
            checked.append(str(samplefile))
    return dict(status="PASS",identity=manifest["identity"],metrics_recomputed=checked)

def equivalent(left,right):
    if isinstance(left,dict): return isinstance(right,dict) and left.keys()==right.keys() and all(equivalent(v,right[k]) for k,v in left.items())
    if isinstance(left,list): return isinstance(right,list) and len(left)==len(right) and all(equivalent(a,b) for a,b in zip(left,right))
    if isinstance(left,(int,float)) and not isinstance(left,bool): return isinstance(right,(int,float)) and math.isclose(left,right,rel_tol=1e-10,abs_tol=1e-12)
    return left==right

def disk_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())

def budget(root, config):
    ledger=read(Path(root)/"budget.json") if (Path(root)/"budget.json").exists() else {}
    elapsed=time.time()-ledger.get("pilot_started",time.time())
    if elapsed>=config.get("wall_budget_seconds",28800): return "wall budget exhausted"
    if ledger.get("gpu_training_seconds",0)>=config.get("gpu_budget_seconds",14400): return "GPU training budget exhausted"
    if disk_bytes(root)>=min(config.get("disk_budget_bytes",10_000_000_000),10_000_000_000): return "disk budget exhausted"
    if shutil.disk_usage(root).free<config.get("minimum_free_bytes",1_000_000_000): return "insufficient disk space"
    return None

@contextlib.contextmanager
def lock(root):
    path=Path(root)/"manager.lock"; path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise RuntimeError("Manager lock exists; verify recorded PID is dead before removing stale lock")
    try:
        os.write(fd,str(os.getpid()).encode()); os.close(fd); yield
    finally: path.unlink(missing_ok=True)

def run(root,config,prereg,resume=False,dry=False):
    root=Path(root)
    if (root/"manifest.json").exists() and not resume: raise ValueError("Existing run requires --resume")
    with lock(root):
        freeze(root,config,prereg); verify(root)
        if dry: return stage(root,"dry-run","PASS",test_opened=False)
        hardware=inventory(root)
        processes=hardware["gpu_processes"]
        if processes.get("exit_code")==0 and any(line.strip() and (any(x in line.lower() for x in ("python", "cuda", "torch", "train")) or not any(x in line.lower() for x in ("n/a","not supported","no running"))) for line in processes.get("stdout","").splitlines()):
            return stage(root,"resource","BLOCKED",reason="Existing GPU compute processes; no jobs disturbed")
        physics=importlib.import_module("pxrd_cross_material_autolab.physics")
        valid=[]
        for material in config["materials"]:
            dest=root/"materials"/material["id"]; dest.mkdir(parents=True,exist_ok=True)
            gatefile=dest/"physical_gate.json"
            if not material.get("verified",False) or not material.get("cif_path") or not Path(material["cif_path"]).is_file():
                stage(dest,"source","SKIPPED",reason="Unverified or unavailable CIF; no physical model invented")
                continue
            if gatefile.exists(): gates=read(gatefile)
            else:
                try:
                    model=physics.PowderModel(material["cif_path"],grid_size=config.get("grid_size",1024))
                    gates=physics.gate(model)
                    expected=material.get("spacegroup")
                    actual=gates.get("details",{}).get("structure",{}).get("spacegroup")
                    if expected is not None and actual is not None and expected!=actual:
                        gates.update(status="FAIL",reason="Reported versus expanded CIF space group mismatch")
                except Exception as exc:
                    gates=dict(status="FAIL",reason=str(exc),traceback=traceback.format_exc())
                atomic(gatefile,gates); event(dest,"physical_gate",result=gates)
            if gates["status"]=="PASS": valid.append(material)
            else: stage(dest,"physical_gate","SKIPPED",reason=gates)
        # A failing independent renderer parity means the generalized simulator is unsafe.
        for p in (root/"materials").glob("*/physical_gate.json"):
            g=read(p)
            if g.get("halt_simulator",False): return stage(root,"physical_gate","BLOCKED",reason="Generalized simulator failed")
        experiment=importlib.import_module("pxrd_cross_material_autolab.experiment") if valid else None
        for material in valid[:10]:
            dest=root/"materials"/material["id"]
            if (dest/"status.json").exists():
                previous=read(dest/"status.json")
                if previous["status"] in ("PASS","FAIL"): continue
                if previous.get("stage")=="experiment":
                    stage(dest,"experiment","BLOCKED",reason="Interrupted experiment; no automatic test reopening")
                    continue
            reason=budget(root,config)
            if reason: return stage(root,"budget","BLOCKED",reason=reason)
            ledgerfile=root/"budget.json"
            ledger=read(ledgerfile) if ledgerfile.exists() else dict(pilot_started=time.time(),gpu_training_seconds=0)
            atomic(ledgerfile,ledger)
            verify(root)
            event(root,"test_authorization",material=material["id"],identity=read(root/"manifest.json")["identity"])
            stage(dest,"experiment","NOT_RUN",reason="Execution entered; interruption requires explicit audit before retry")
            attempt=dest/("attempt_"+str(time.time_ns())); attempt.mkdir()
            try:
                result=experiment.run_material(material,config,attempt)
                atomic(attempt/"result.json",result)
                ledger=read(ledgerfile)
                if not result.get("budget_recorded",False):
                    ledger["gpu_training_seconds"]+=result.get("gpu_training_seconds",result.get("training_seconds",0))
                    atomic(ledgerfile,ledger)
                artifacts={str(p.relative_to(attempt)):sha(p) for p in attempt.rglob("*") if p.is_file() and "private" not in p.relative_to(attempt).parts and p.name!="artifacts.json"}
                atomic(attempt/"artifacts.json",artifacts)
                stage(dest,"experiment",result.get("status","PASS"),attempt=str(attempt),result=str(attempt/"result.json"))
            except Exception as exc:
                failure=dict(reason=str(exc),traceback=traceback.format_exc())
                atomic(attempt/"failure.json",failure); event(root,"failure",material=material["id"],**failure)
                stage(dest,"experiment","FAIL",attempt=str(attempt),**failure)
        statuses=[read(p)["status"] for p in (root/"materials").glob("*/status.json")]
        return stage(root,"run","PASS" if statuses and all(s=="PASS" for s in statuses) else "BLOCKED",material_statuses=statuses)

def report(root):
    root=Path(root)
    records={p.parent.name:read(p) for p in root.glob("materials/*/status.json")}
    output=dict(status=read(root/"status.json") if (root/"status.json").exists() else {"status":"NOT_RUN"},materials=records)
    reportdir=root/"reports"; reportdir.mkdir(parents=True,exist_ok=True)
    atomic(reportdir/"status.json",output)
    summaries=[]
    for mid,record in records.items():
        if record.get("result") and Path(record["result"]).is_file():
            result=read(record["result"])
            rows=result.get("summary",result.get("summaries",[]))
            if isinstance(rows,dict): rows=[dict(method=k,**v) if isinstance(v,dict) else dict(method=k,value=v) for k,v in rows.items()]
            for row in rows: summaries.append(dict({"material":mid},**row))
    atomic(reportdir/"COMPARISON.json",summaries)
    fields=sorted({k for row in summaries for k in row}) or ["material","method","status"]
    with (reportdir/"COMPARISON.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(summaries)
    text="\u81ea\u52a8\u5b9e\u9a8c\u72b6\u6001" # ASCII escape ensures correct Windows source encoding.
    lines=["# PXRD "+text,"", "status: "+output["status"]["status"], ""]
    lines += [f"- {k}: {v['status']}" for k,v in records.items()]
    lines += ["", "\u7ed3\u679c\u4e0e\u5931\u8d25\u8bb0\u5f55", ""]
    for mid,record in records.items():
        if record.get("result") and Path(record["result"]).is_file():
            result=read(record["result"])
            lines.append(f"- {mid}: {result.get('decision','UNDETERMINED')}; "+str(result.get('training_device','unknown'))+"; training_seconds="+str(result.get('training_seconds',0)))
        elif record.get("reason"): lines.append(f"- {mid}: "+json.dumps(record['reason'],ensure_ascii=False))
    lines += ["", "\u6bd4\u8f83\u8868: [COMPARISON.csv](COMPARISON.csv) / [COMPARISON.json](COMPARISON.json)",
      "\u5f52\u4e00\u5316 q MAE \u4e0e\u6676\u683c\u8bef\u5dee (angstrom) \u5206\u5f00\u62a5\u544a\uff1b\u4e0d\u540c\u81ea\u7531\u5ea6\u4e0d\u6df7\u5408\u6c47\u603b\u3002",
      "P3 \u65f6\u95f4\u5305\u542b\u5168\u90e8\u4e09\u4e2a\u8d77\u70b9\uff1bN+A \u5305\u542b\u7f51\u7edc\u63a8\u7406\u4e0e\u7269\u7406\u7cbe\u4fee\uff0c\u8bad\u7ec3\u6210\u672c\u53e6\u5217\u3002",
      "\u6765\u6e90\u3001\u914d\u7f6e\u3001CIF \u4e0e\u4ee3\u7801 SHA256 \u89c1 ../manifest.json\uff1b\u5931\u8d25\u5386\u53f2\u89c1 ../events.jsonl \u548c\u5404\u6750\u6599\u76ee\u5f55\u3002"]
    lines += ["", "\u5408\u6210\u8c31\u7ed3\u679c\u4ec5\u8bf4\u660e\u9010\u6750\u6599\u6d41\u7a0b\uff0c\u4e0d\u8bc1\u660e\u771f\u5b9e\u5b9e\u9a8c\u8c31\u6216\u96f6\u6837\u672c\u6cdb\u5316\u3002", ""]
    (reportdir/"OVERVIEW.md").write_text("\n".join(lines),encoding="utf-8")
    return output

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["inventory","preflight","dry-run","run","status","verify","report"])
    parser.add_argument("--config",default="pxrd_cross_material_autolab/config.json")
    parser.add_argument("--root",default="pxrd_cross_material_autolab/runs/pilot_20261019")
    parser.add_argument("--preregistration",default="pxrd_cross_material_autolab/PREREGISTRATION.md")
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args(argv); root=Path(args.root)
    try:
        if args.command=="inventory": result=inventory(root)
        elif args.command=="verify": result=verify(root)
        elif args.command=="report": result=report(root)
        elif args.command=="status": result=read(root/"status.json") if (root/"status.json").exists() else {"status":"NOT_RUN"}
        elif args.command=="preflight": result=freeze(root,read(args.config),args.preregistration)
        else: result=run(root,read(args.config),args.preregistration,args.resume,args.command=="dry-run")
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result.get("status") not in ("FAIL","BLOCKED") else 2
    except Exception as exc:
        event(root,"manager_failure",reason=str(exc),traceback=traceback.format_exc())
        print(str(exc),file=sys.stderr); return 2
