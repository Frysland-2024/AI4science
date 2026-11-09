#!/usr/bin/env python3
"""Bounded native-Windows CUDA preflight for V11; NOT an HPO or Test run."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import one_click_v11 as v11


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 32:
        raise ValueError("Bounded CUDA smoke batch size must be 1..32")
    np, torch, F, load_peak_records, load_peak_tables, render_pair_batch, build_online_view_factory, ResNet, ResNetConfig, Sampler, _ = v11.ctx_libraries()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable on this Windows Python environment")
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    source = v11.XRD / "data/merged_154975_v11/training_records.v1.jsonl"
    # Source is frozen and read through the same parser as the real trainer.
    records = load_peak_records(source)
    train = [rec for rec in records if rec.split == "train"][:args.batch_size]
    valid = [rec for rec in records if rec.split == "validation"][:1]
    if len(train) != args.batch_size or not valid:
        raise RuntimeError("Frozen Train / Validation records missing")
    sim = json.loads((v11.XRD / "configs/simulation.v11_tch_pseudo_voigt.json").read_text(encoding="utf-8"))
    fac = v11.factory(sim, 20260721, Sampler, build_online_view_factory)
    peak_records = train + valid
    peaks = load_peak_tables(peak_records)
    start = time.perf_counter()
    with torch.no_grad():
        a, b, labels = render_pair_batch(train, peaks, fac, epoch=0, global_step=0, profile="train")
    render_seconds = time.perf_counter() - start
    model = ResNet(ResNetConfig(model_id="18")).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4)
    x1, x2 = a.to(device), b.to(device)
    y = labels.to(device)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast("cuda", dtype=torch.bfloat16, enabled=torch.cuda.is_bf16_supported()):
        p1, p2 = model(x1)["logits"], model(x2)["logits"]
        loss, ce, js = v11.loss_js(p1, p2, y, 60.0, torch, F)
    if not bool(torch.isfinite(loss).item()):
        raise RuntimeError("V11 two-view GPU loss is not finite")
    loss.backward()
    optimizer.step()
    torch.cuda.synchronize()
    step_seconds = time.perf_counter() - start
    with torch.inference_mode():
        va, vb, vy = render_pair_batch(valid, peaks, fac, epoch=0, global_step=0, profile="in_range")
        va, vb = va.to(device), vb.to(device)
        if not (torch.isfinite(model(va)["logits"]).all() and torch.isfinite(model(vb)["logits"]).all()):
            raise RuntimeError("V11 Validation GPU logits are not finite")
    free_vram, total_vram = torch.cuda.mem_get_info()
    result = {
        "status": "BOUNDED_GPU_SMOKE_PASS_NOT_FULL_STAGE0",
        "gpu": gpu_name,
        "vram_total_gib": round(total_vram / 1024**3, 2),
        "batch_parents": args.batch_size,
        "two_views_per_parent": True,
        "render_seconds_single_batch": round(render_seconds, 3),
        "train_step_seconds_single_batch": round(step_seconds, 3),
        "gpu_peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
        "gpu_free_after_step_gib": round(free_vram / 1024**3, 3),
        "loss": float(loss.detach().cpu()),
        "train_source": "frozen Train only",
        "validation_source": "one frozen Validation parent",
        "rruff_and_test_access": "none",
        "disclaimer": "No full 23245-parent six-profile Validation, throughput stability, disk/RAM headroom or checkpoint/prefetch recovery proven.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
