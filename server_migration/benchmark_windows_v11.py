#!/usr/bin/env python3
"""Bounded, train-only V11 physical batch vs microbatch GPU throughput benchmark.

This runs disposable optimizer steps on the verified Train split, does not
write HPO studies/checkpoints or access Test/RRUFF, and makes no claims about
whole-run throughput. Pass --cases 4:4,8:8,16:8 for safe 8GB laptop tests.
"""
from __future__ import annotations

import argparse
import gc
import json
import shutil
import statistics
import time
from pathlib import Path
import numpy as np

import one_click_v11 as v11
from v11_prefetch import V11PairPrefetchPool
from train_microbatch import paired_optimizer_step


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",default="4:4,8:8,16:16")
    p.add_argument("--warmup",type=int,default=1)
    p.add_argument("--steps",type=int,default=3)
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--cache",type=int,default=128)
    p.add_argument("--output",type=Path,default=None)
    a=p.parse_args()
    cases=[]
    for entry in a.cases.split(","):
        batch,micro=map(int,entry.split(":"))
        if not 1<=micro<=batch<=32:
            raise ValueError("Case must be EFFECTIVE_BATCH:MICROBATCH, each 1..32")
        cases.append((batch,micro))
    if not 1<=len(cases)<=4 or not 1<=a.steps<=10 or not 0<=a.warmup<=4 or not 1<=a.workers<=4:
        raise ValueError("Bounded benchmarking cases/steps/workers required")
    np_lib,torch,F,load_peak_records,*tail=v11.ctx_libraries()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable: cannot benchmark V11 GPU")
    records_path=v11.XRD/"data/merged_154975_v11/training_records.v1.jsonl"
    records=load_peak_records(records_path)
    train,valid,_=v11.full_parent_disjoint_records(records_path,records)
    if len(train)!=108478 or len(valid)!=23245:
        raise RuntimeError("Unexpected frozen parent counts")
    sim=json.loads((v11.XRD/"configs/simulation.v11_tch_pseudo_voigt.json").read_text(encoding="utf-8"))
    from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,ML4PXRDResNet1DConfig
    started_at=time.time()
    result={"status":"ENGINEERING_ONLY_NOT_FULL_STAGE0","gpu":torch.cuda.get_device_name(0),
            "train_parents_available":len(train),"validation_parents_not_scored":len(valid),
            "no_test_rruff":True,"warmup":a.warmup,"measured_steps":a.steps,
            "results":[]}
    for batch,micro in cases:
        output={"effective_parent_batch":batch,"microbatch_parents":micro}
        pool=None
        model=None
        optimizer=None
        try:
            torch.cuda.empty_cache()
            model=ML4PXRDResNet1D(ML4PXRDResNet1DConfig(model_id="18")).to("cuda").train()
            optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-4)
            torch.cuda.reset_peak_memory_stats()
            step_times=[]
            model_times=[]
            parent_count=0
            rng=np.random.default_rng(20260711)
            pool=V11PairPrefetchPool(sim,run_seed=20260711,workers=a.workers,
                 prefetch_batches=2,native_threads=1,max_cached_peaks=a.cache)
            total=a.warmup+a.steps
            def submit_step(step):
                idx=rng.choice(len(train),batch,replace=False)
                chosen=[train[int(i)] for i in idx]
                pool.submit(step,chosen,epoch=0,global_step=step,profile="train")
            for at in range(min(2,total)):
                submit_step(at)
            for step in range(total):
                start=time.perf_counter()
                first,second,labels=pool.get(step)
                future=step+2
                if future<total:
                    submit_step(future)
                x1=torch.from_numpy(first).to("cuda")
                x2=torch.from_numpy(second).to("cuda")
                y=torch.from_numpy(labels).to("cuda")
                forward_start=time.perf_counter()
                loss,ce,js,grad=paired_optimizer_step(
                    model,optimizer,x1,x2,y,lambda_js=60.,microbatch_size=micro,
                    loss_fn=v11.loss_js,torch=torch,F=F,amp=torch.cuda.is_bf16_supported())
                torch.cuda.synchronize()
                elapsed=time.perf_counter()-start
                if step>=a.warmup:
                    step_times.append(elapsed)
                    model_times.append(time.perf_counter()-forward_start)
                    parent_count+=len(labels)
            output.update(status="PASS",parents_measured=parent_count,
                  parent_per_second=round(parent_count/sum(step_times),2),
                  seconds_per_step_mean=round(statistics.mean(step_times),3),
                  seconds_per_step_p95=round(float(np.percentile(step_times,95)),3),
                  gpu_peak_allocated_gib=round(torch.cuda.max_memory_allocated()/1024**3,3),
                  gpu_peak_reserved_gib=round(torch.cuda.max_memory_reserved()/1024**3,3),
                  loss_last=round(float(loss),6))
            try:
                import psutil
                output["system_ram_percent_after"]=psutil.virtual_memory().percent
                output["ram_available_gib_after"]=round(psutil.virtual_memory().available/1024**3,2)
            except ImportError:
                # Stock Windows Python does not necessarily ship psutil.
                if __import__("os").name == "nt":
                    import ctypes
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_=[("dwLength",ctypes.c_ulong),
                                  ("dwMemoryLoad",ctypes.c_ulong),
                                  ("ullTotalPhys",ctypes.c_ulonglong),
                                  ("ullAvailPhys",ctypes.c_ulonglong),
                                  ("ullTotalPageFile",ctypes.c_ulonglong),
                                  ("ullAvailPageFile",ctypes.c_ulonglong),
                                  ("ullTotalVirtual",ctypes.c_ulonglong),
                                  ("ullAvailVirtual",ctypes.c_ulonglong),
                                  ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
                    memory=MEMORYSTATUSEX()
                    memory.dwLength=ctypes.sizeof(MEMORYSTATUSEX)
                    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                        output["system_ram_percent_after"]=int(memory.dwMemoryLoad)
                        output["ram_available_gib_after"]=round(memory.ullAvailPhys/1024**3,2)
                        output["ram_total_gib"]=round(memory.ullTotalPhys/1024**3,2)
                    else:
                        output["system_ram"]="Windows memory API unavailable"
                else:
                    output["system_ram"]="psutil unavailable"
            output["disk_free_gib"]=round(shutil.disk_usage(v11.ROOT).free/1024**3,2)
        except (torch.cuda.OutOfMemoryError,MemoryError) as error:
            output.update(status="OOM",error=type(error).__name__)
        except Exception as error:
            output.update(status="FAILED",error=repr(error)[:500])
        finally:
            if pool is not None:
                pool.close()
            del pool,model,optimizer
            gc.collect()
            torch.cuda.empty_cache()
        result["results"].append(output)
        print(json.dumps(output,ensure_ascii=False),flush=True)
    result["elapsed_seconds"]=round(time.time()-started_at,1)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=="__main__":
    main()
