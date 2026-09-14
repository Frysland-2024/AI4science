"""
RRUFF-70 Few-Shot Adaptation v2 — GPU-optimized with early stopping.
"""
import torch
import numpy as np
import json, csv, os, sys
from collections import defaultdict

sys.path.insert(0, r"E:/AI4science/xrd_robustness/src")
from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D, ML4PXRDResNet1DConfig

DATA_DIR  = r"E:/AI4science/xrd_robustness/data/real_xrd/rruff70"
CKPT_DIR  = r"E:/AI4science/xrd_robustness/outputs/v9_resnet_js_simulated_test_checkpoints/checkpoints"
CLASS_ORDER = ("triclinic","monoclinic","orthorhombic","tetragonal","trigonal","hexagonal","cubic")
K_VALUES = [1, 2, 5]
EPISODE_SEEDS = [42, 123, 456, 789, 1024]
TRAIN_SEEDS = ["20260711","20260712","20260713","20260714","20260715"]
METHODS = ["dynamic_erm", "js_lambda_60"]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HEAD_LR = 1e-4          # Matches frozen simulated contract (AdamW, LR=1e-4)
HEAD_EPOCHS = 200
EARLY_STOP_PATIENCE = 20

print(f"Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")

# ── Load data ──
with open(os.path.join(DATA_DIR, "manifests", "rruff70_real_adaptation_split_v1.csv"), encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

samples_by_class = defaultdict(list)
for row in rows:
    cs = row["crystal_system"].strip().lower()
    if cs not in CLASS_ORDER:
        continue
    rid = row["rruff_id"]
    mn  = row["mineral_name"]
    sp  = os.path.join(DATA_DIR, "spectra_10_80_step_002", f"{rid}_{mn}.csv")
    if not os.path.exists(sp):
        import glob
        matches = glob.glob(os.path.join(DATA_DIR, "spectra_10_80_step_002", f"{rid}*.csv"))
        sp = matches[0] if matches else None
    if sp is None:
        continue
    data = np.loadtxt(sp, delimiter=",", skiprows=1, usecols=1).astype(np.float32)
    samples_by_class[cs].append({"id": rid, "data": data, "class": CLASS_ORDER.index(cs)})

for cs in CLASS_ORDER:
    print(f"  {cs}: {len(samples_by_class[cs])}")

# ── Load models ──
def load_model(ckpt_path):
    config = ML4PXRDResNet1DConfig(model_id="18", input_length=3501, num_classes=7)
    model = ML4PXRDResNet1D(config).to(DEVICE)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model

print("\nLoading checkpoints...")
models = {}
for seed in TRAIN_SEEDS:
    for method in METHODS:
        ckpt_path = os.path.join(CKPT_DIR, f"seed_{seed}_{method}", "best.ckpt")
        if os.path.exists(ckpt_path):
            models[f"{seed}_{method}"] = load_model(ckpt_path)
            print(f"  {seed}_{method} ✓")
# ── Fine-tune function ──
def finetune_and_eval(model, X_support, y_support, X_query, y_query):
    """Freeze backbone, train head, return accuracy."""
    # Clone model to avoid state leakage
    import copy
    head_state = {k: v.clone() for k, v in model.state_dict().items() 
                  if "head" in k or "embedding" in k}
    
    # Freeze backbone
    for name, param in model.named_parameters():
        param.requires_grad = ("head" in name or "embedding" in name)
    
    X_support = X_support.to(DEVICE)
    y_support = y_support.to(DEVICE)
    X_query = X_query.to(DEVICE)
    y_query = y_query.to(DEVICE)
    
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=HEAD_LR)
    criterion = torch.nn.CrossEntropyLoss()
    
    best_loss = float("inf")
    best_head_state = None
    patience_counter = 0
    
    for epoch in range(HEAD_EPOCHS):
        model.train()
        optimizer.zero_grad()
        output = model(X_support)
        logits = output["logits"] if isinstance(output, dict) else output
        loss = criterion(logits, y_support)
        loss.backward()
        optimizer.step()
        
        if loss.item() < best_loss - 1e-4:
            best_loss = loss.item()
            best_head_state = {k: v.clone() for k, v in model.state_dict().items()
                              if "head" in k or "embedding" in k}
            patience_counter = 0
        else:
            patience_counter += 1
        
        if patience_counter >= EARLY_STOP_PATIENCE and epoch >= 20:
            break
    
    # Restore best head
    if best_head_state:
        model.load_state_dict(best_head_state, strict=False)
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        output = model(X_query)
        logits = output["logits"] if isinstance(output, dict) else output
        preds = torch.argmax(logits, dim=1).cpu()
        yq_cpu = y_query.cpu()
        acc = (preds == yq_cpu).float().mean().item()
        per_class = {}
        for i, cs in enumerate(CLASS_ORDER):
            idx = (yq_cpu == i)
            if idx.sum() > 0:
                per_class[cs] = (preds[idx] == yq_cpu[idx]).float().mean().item()
    
    # Restore original head (for next run)
    model.load_state_dict(head_state, strict=False)
    return acc, per_class, min(epoch + 1, HEAD_EPOCHS)

# ── Main loop ──
all_results = []
total_runs = len(K_VALUES) * len(EPISODE_SEEDS) * len(TRAIN_SEEDS) * len(METHODS)
run_idx = 0

for K in K_VALUES:
    print(f"\n{'='*50}\nK = {K}\n{'='*50}")
    
    for ep_seed in EPISODE_SEEDS:
        import random
        random.seed(ep_seed)
        
        # Split
        support, query = {}, {}
        for cs in CLASS_ORDER:
            pool = samples_by_class[cs][:]
            random.shuffle(pool)
            support[cs] = pool[:K]
            query[cs] = pool[K:]
        
        X_query = torch.from_numpy(np.stack([s["data"] for cs in CLASS_ORDER for s in query[cs]]))
        y_query = torch.tensor([s["class"] for cs in CLASS_ORDER for s in query[cs]])
        
        for seed in TRAIN_SEEDS:
            for method in METHODS:
                key = f"{seed}_{method}"
                if key not in models:
                    continue
                
                model = models[key]
                
                X_support = torch.from_numpy(np.stack(
                    [s["data"] for cs in CLASS_ORDER for s in support[cs]]))
                y_support = torch.tensor([s["class"] for cs in CLASS_ORDER for s in support[cs]])
                
                acc, per_class, epochs_used = finetune_and_eval(
                    model, X_support, y_support, X_query, y_query)
                
                run_idx += 1
                print(f"  [{run_idx}/{total_runs}] K={K} epseed={ep_seed} {seed}_{method}: "
                      f"acc={acc:.3f} (took {epochs_used} epochs)")
                
                all_results.append({
                    "K": K, "episode_seed": ep_seed, "train_seed": seed,
                    "method": method, "accuracy": acc, "per_class": per_class,
                    "epochs_used": epochs_used
                })

# ── Summary ──
print(f"\n{'='*60}")
print("RESULTS")
print(f"{'='*60}")
for K in K_VALUES:
    for method_name, method_key in [("Dynamic ERM", "dynamic_erm"), ("JS λ=60", "js_lambda_60")]:
        accs = [r["accuracy"] for r in all_results if r["K"] == K and r["method"] == method_key]
        print(f"K={K} {method_name}: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    
    erm_accs = [r["accuracy"] for r in all_results if r["K"] == K and r["method"] == "dynamic_erm"]
    js_accs  = [r["accuracy"] for r in all_results if r["K"] == K and r["method"] == "js_lambda_60"]
    if erm_accs and js_accs:
        print(f"  Δ (JS-ERM): {np.mean(js_accs)-np.mean(erm_accs):+.4f}")

# Save
os.makedirs(os.path.join(DATA_DIR, "results"), exist_ok=True)
with open(os.path.join(DATA_DIR, "results", "fewshot_v2.json"), "w") as f:
    json.dump({"results": all_results, "config": {
        "K_values": K_VALUES, "episode_seeds": EPISODE_SEEDS,
        "train_seeds": TRAIN_SEEDS, "device": str(DEVICE),
        "head_lr": HEAD_LR, "head_epochs": HEAD_EPOCHS, "early_stop_patience": EARLY_STOP_PATIENCE,
    }}, f, indent=2)
print(f"\nSaved to {DATA_DIR}/results/fewshot_v2.json")
