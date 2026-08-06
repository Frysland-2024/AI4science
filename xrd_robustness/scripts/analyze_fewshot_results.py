"""
Comprehensive few-shot analysis: all deliverables requested by reviewer.
"""
import json
import numpy as np
from collections import defaultdict
import csv, os

with open(r"E:/AI4science/xrd_robustness/data/real_xrd/rruff70/results/fewshot_v2.json") as f:
    data = json.load(f)
results = data["results"]

CLASS_ORDER = ("triclinic","monoclinic","orthorhombic","tetragonal","trigonal","hexagonal","cubic")
OUT = r"E:/AI4science/xrd_robustness/data/real_xrd/rruff70/results"

# ═══════════════════════════════════════
# 1. Run-level CSV (150 rows)
# ═══════════════════════════════════════
with open(os.path.join(OUT, "fewshot_runs.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["K","episode_seed","train_seed","method","accuracy","epochs_used"])
    w.writeheader()
    for r in results:
        w.writerow({k: r[k] for k in ["K","episode_seed","train_seed","method","accuracy","epochs_used"]})

# ═══════════════════════════════════════
# 2. Paired comparison CSV (75 rows)
# ═══════════════════════════════════════
pairs = []
for K in [1,2,5]:
    for ep in sorted(set(r["episode_seed"] for r in results if r["K"]==K)):
        for ts in sorted(set(r["train_seed"] for r in results if r["K"]==K)):
            erm = [r for r in results if r["K"]==K and r["episode_seed"]==ep and r["train_seed"]==ts and r["method"]=="dynamic_erm"]
            js  = [r for r in results if r["K"]==K and r["episode_seed"]==ep and r["train_seed"]==ts and r["method"]=="js_lambda_60"]
            if erm and js:
                delta = js[0]["accuracy"] - erm[0]["accuracy"]
                pairs.append({"K": K, "episode_seed": ep, "train_seed": ts,
                              "ERM_acc": erm[0]["accuracy"], "JS_acc": js[0]["accuracy"],
                              "delta": delta, "ERM_epochs": erm[0]["epochs_used"], "JS_epochs": js[0]["epochs_used"]})

with open(os.path.join(OUT, "fewshot_paired_comparisons.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=pairs[0].keys())
    w.writeheader()
    for p in pairs:
        w.writerow(p)

# ═══════════════════════════════════════
# 3. Summary table per K
# ═══════════════════════════════════════
print("=" * 70)
print("PER-K SUMMARY")
print("=" * 70)
for K in [1,2,5]:
    k_pairs = [p for p in pairs if p["K"]==K]
    deltas = [p["delta"] for p in k_pairs]
    erm_accs = [p["ERM_acc"] for p in k_pairs]
    js_accs = [p["JS_acc"] for p in k_pairs]
    
    n_pos = sum(1 for d in deltas if d > 0)
    n_neg = sum(1 for d in deltas if d < 0)
    n_zero = sum(1 for d in deltas if d == 0)
    
    print(f"\nK={K}:")
    print(f"  Paired comparisons: {len(k_pairs)}")
    print(f"  ERM mean±SD:  {np.mean(erm_accs):.4f} ± {np.std(erm_accs, ddof=1):.4f}")
    print(f"  JS  mean±SD:  {np.mean(js_accs):.4f} ± {np.std(js_accs, ddof=1):.4f}")
    print(f"  Mean paired Δ: {np.mean(deltas):+.4f}")
    print(f"  Median paired Δ: {np.median(deltas):+.4f}")
    print(f"  Δ > 0: {n_pos}/{len(k_pairs)}  Δ < 0: {n_neg}/{len(k_pairs)}  Δ = 0: {n_zero}/{len(k_pairs)}")
    print(f"  Δ percentiles: 10%={np.percentile(deltas,10):+.4f}  25%={np.percentile(deltas,25):+.4f}  75%={np.percentile(deltas,75):+.4f}  90%={np.percentile(deltas,90):+.4f}")
    
    # Stratified by pretraining seed
    print(f"\n  By pretraining seed:")
    for ts in sorted(set(p["train_seed"] for p in k_pairs)):
        td = [p["delta"] for p in k_pairs if p["train_seed"]==ts]
        print(f"    seed {ts}: Δ={np.mean(td):+.4f} [{min(td):+.3f}, {max(td):+.3f}]")
    
    # Stratified by episode seed
    print(f"  By episode seed:")
    for ep in sorted(set(p["episode_seed"] for p in k_pairs)):
        ed = [p["delta"] for p in k_pairs if p["episode_seed"]==ep]
        print(f"    ep {ep}: Δ={np.mean(ed):+.4f} [{min(ed):+.3f}, {max(ed):+.3f}]")

# ═══════════════════════════════════════
# 4. Per-class analysis (JS only, K=5)
# ═══════════════════════════════════════
print("\n" + "=" * 70)
print("PER-CLASS JS F1 (K=5, all 25 runs)")
print("=" * 70)
k5_js = [r for r in results if r["K"]==5 and r["method"]=="js_lambda_60"]
print(f"Runs: {len(k5_js)}")
for cs in CLASS_ORDER:
    vals = [r["per_class"].get(cs, 0) for r in k5_js]
    print(f"  {cs:<12}: acc={np.mean(vals):.4f} ± {np.std(vals, ddof=1):.4f}")

# ═══════════════════════════════════════
# 5. 5x5 Delta matrices
# ═══════════════════════════════════════
TRAIN_SEEDS = sorted(set(p["train_seed"] for p in pairs))
EP_SEEDS = sorted(set(p["episode_seed"] for p in pairs))

print("\n" + "=" * 70)
print("5×5 PAIRED DELTA MATRICES")
print("=" * 70)
for K in [1,2,5]:
    print(f"\nK={K}:")
    print(f"     " + "".join(f"{ep:>8}" for ep in EP_SEEDS) + f"  {'mean':>8}")
    for ts in TRAIN_SEEDS:
        row = [next((p["delta"] for p in pairs if p["K"]==K and p["train_seed"]==ts and p["episode_seed"]==ep), None) for ep in EP_SEEDS]
        valid = [x for x in row if x is not None]
        row_str = "".join(f"{x:>+8.4f}" if x is not None else f"{'N/A':>8}" for x in row)
        print(f"  {ts} {row_str}  {np.mean(valid):>+8.4f}")
    col_means = []
    for ep in EP_SEEDS:
        col = [p["delta"] for p in pairs if p["K"]==K and p["episode_seed"]==ep and p["train_seed"] in TRAIN_SEEDS]
        col_means.append(np.mean(col) if col else 0)
    print(f"  {'mean':<12}" + "".join(f"{m:>+8.4f}" for m in col_means))

# ═══════════════════════════════════════
# 6. JS-only correct vs ERM-only correct (approximate from per-class)
# ═══════════════════════════════════════
print("\n" + "=" * 70)
print("JS vs ERM PER-CLASS GAIN (K=5)")
print("=" * 70)
k5_erm = [r for r in results if r["K"]==5 and r["method"]=="dynamic_erm"]
# Compute mean delta per class
for cs in CLASS_ORDER:
    js_vals = [r["per_class"].get(cs, 0) for r in k5_js]
    erm_vals = [r["per_class"].get(cs, 0) for r in k5_erm]
    delta = np.mean(js_vals) - np.mean(erm_vals)
    print(f"  {cs:<12}: JS={np.mean(js_vals):.4f}  ERM={np.mean(erm_vals):.4f}  Δ={delta:+.4f}")

# ═══════════════════════════════════════
# 7. Save epoch statistics
# ═══════════════════════════════════════
print("\n" + "=" * 70)
print("EPOCH STATISTICS")
print("=" * 70)
for K in [1,2,5]:
    for method in ["dynamic_erm", "js_lambda_60"]:
        epochs = [r["epochs_used"] for r in results if r["K"]==K and r["method"]==method]
        print(f"  K={K} {method}: epochs={np.mean(epochs):.0f}±{np.std(epochs):.0f} [{min(epochs)},{max(epochs)}]")

print(f"\nAll files saved to: {OUT}/")
print(f"  fewshot_runs.csv (150 rows)")
print(f"  fewshot_paired_comparisons.csv (75 rows)")
