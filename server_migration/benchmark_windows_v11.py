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
from v11_prefetch import V11PairPrefetchPool, sample_parent_indices
from train_microbatch import paired_optimizer_step


def cpu_worker_sweep(args):
    """CPU-only paired-physics worker scaling, reproducible on another Windows host.

    This probes actual Train parents, compares rendered bytes, and never reads
    held-out Test/RRUFF, creates Optuna state or invokes GPU optimization.
    """
    import hashlib
    if not (8 <= args.steps <= 256 and 1 <= args.batch <= 32
            and 16 <= args.cache <= 1024):
        raise ValueError("CPU sweep must be bounded: 8..256 steps, batch 1..32")
    libs = v11.ctx_libraries()
    path = v11.XRD / "data/merged_154975_v11/training_records.v1.jsonl"
    records = libs[3](path)
    train, valid, _ = v11.full_parent_disjoint_records(path, records)
    if len(train) != 108478 or len(valid) != 23245:
        raise RuntimeError("Frozen parent counts changed")
    sim = json.loads((v11.XRD / "configs/simulation.v11_tch_pseudo_voigt.json").read_text(
        encoding="utf-8"))
    result = {"status":"CPU_ONLY_BENCHMARK_NOT_HPO",
              "train_parents_available":len(train),"test_rruff_access":"none",
              "sampling":"epoch_shuffle","effective_batch":args.batch,
              "steps_per_case":args.steps,"cache_per_worker":args.cache,
              "results":[]}
    for value in args.worker_cases.split(","):
        workers,depth = map(int,value.split(":"))
        if not (1 <= workers <= 16 and 1 <= depth <= 8):
            raise ValueError("Unsafe CPU worker sweep setting")
        rng = np.random.default_rng(20260711)
        permutations = {}
        signature = hashlib.sha256()
        times = []
        pool = V11PairPrefetchPool(
            sim,run_seed=20260711,workers=workers,
            prefetch_batches=depth,native_threads=1,
            max_cached_peaks=args.cache)
        start = time.perf_counter()
        def submit(step):
            indices,epoch = sample_parent_indices(
                rng,len(train),args.batch,step,sampling_mode="epoch_shuffle",
                sampling_seed=20260711,permutation_cache=permutations)
            pool.submit(step,[train[int(i)] for i in indices],epoch=epoch,
                        global_step=step,profile="train")
        try:
            for step in range(min(depth,args.steps)):
                submit(step)
            count = 0
            for step in range(args.steps):
                t0 = time.perf_counter()
                first,second,labels = pool.get(step)
                signature.update(first.tobytes())
                signature.update(second.tobytes())
                signature.update(labels.tobytes())
                count += len(labels)
                if step + depth < args.steps:
                    submit(step + depth)
                times.append(time.perf_counter()-t0)
        finally:
            pool.close()
        elapsed = time.perf_counter()-start
        row = {"workers":workers,"prefetch_batches":depth,
               "parents":count,"seconds":round(elapsed,3),
               "throughput_parents_per_sec":round(count/elapsed,2),
               "batch_p95_seconds":round(float(np.percentile(times,95)),3),
               "rendered_sha256":signature.hexdigest()}
        result["results"].append(row)
        print(json.dumps(row),flush=True)
    if len({x["rendered_sha256"] for x in result["results"]})!=1:
        raise RuntimeError("CPU worker sweep changed V11 paired-spectrum bytes")
    result["status"]="PASS_SHA256_IDENTICAL_CPU_ONLY"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"cases":len(result["results"])}),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",default="4:4,8:8,16:16")
    p.add_argument("--warmup",type=int,default=1)
    p.add_argument("--steps",type=int,default=3)
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--cache",type=int,default=128)
    p.add_argument("--cpu-only",action="store_true",
                   help="Profile Train-only CPU prefetch worker scaling; no GPU/HPO")
    p.add_argument("--worker-cases",default="2:2,4:2,8:4,12:4",
                   help="CPU-only worker:queue-depth pairs")
    p.add_argument("--batch",type=int,default=16,
                   help="Parent batch size for --cpu-only")
    p.add_argument("--output",type=Path,default=None)
    a=p.parse_args()
    if a.cpu_only:
        cpu_worker_sweep(a)
        return
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
