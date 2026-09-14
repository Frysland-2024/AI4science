# -*- coding: utf-8 -*-
"""用主线模拟预训练模型（JS vs ERM）对谭启组 59 条真实 XRD 做表征嵌入，验证迁移"""
import sys, os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "E:/AI4science/xrd_robustness/src")
import torch
from xrd_robustness.experiment import load_checkpoint
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig

OUT = "E:/AI4science/outputs/tanlab_phase2"
CKPT = "E:/AI4science/xrd_robustness/outputs/simulated_test_checkpoints/checkpoints"

# ---------- 加载谭启组谱，预处理到 3501 点（10-80°） ----------
specs = np.load(os.path.join(OUT, "spectra.npy"))       # (59, 3001) 20-80°
grid_3001 = np.load(os.path.join(OUT, "grid.npy"))
grid_3501 = np.linspace(10.0, 80.0, 3501)
X = np.array([np.interp(grid_3501, grid_3001, s) for s in specs])  # 10-20° 边界外推
X = X / X.max(axis=1, keepdims=True)                     # max 归一化，与 CNRS 一致
print(f"输入 shape: {X.shape}")

# 聚类归属（今天的无监督聚类结果）
cl = []
with open(os.path.join(OUT, "cluster_assignment.csv"), encoding="utf-8-sig") as f:
    rd = csv.reader(f); next(rd)
    for row in rd:
        cl.append(int(row[3]))
cl = np.array(cl)

CLASS_ORDER = ["triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic"]


def embed(run_id):
    cfg = ML4PXRDResNet1DConfig(model_id="18")
    model = ML4PXRDResNet1D(cfg)
    load_checkpoint(os.path.join(CKPT, run_id, "best.ckpt"), model=model, map_location="cpu")
    model.eval()
    with torch.inference_mode():
        batch = torch.from_numpy(X.astype(np.float32))
        out = model(batch)
        emb = out["pooled_embedding"].numpy()   # (59, 256)
        logits = out["logits"].numpy()          # (59, 7)
        prob = torch.softmax(torch.from_numpy(logits), dim=-1).numpy()
    return emb, logits, prob


print("加载 JS checkpoint...")
emb_js, logits_js, prob_js = embed("seed_20260714_js_lambda_60")
print("加载 ERM checkpoint...")
emb_erm, logits_erm, prob_erm = embed("seed_20260714_dynamic_erm")

np.save(os.path.join(OUT, "emb_js.npy"), emb_js)
np.save(os.path.join(OUT, "emb_erm.npy"), emb_erm)
np.save(os.path.join(OUT, "prob_js.npy"), prob_js)
np.save(os.path.join(OUT, "prob_erm.npy"), prob_erm)

# ---------- 预测晶系分布 ----------
pred_js = prob_js.argmax(axis=1)
pred_erm = prob_erm.argmax(axis=1)
print("\n7 晶系预测分布（JS）:")
for i, name in enumerate(CLASS_ORDER):
    print(f"  {name}: {(pred_js == i).sum()}")
print("7 晶系预测分布（ERM）:")
for i, name in enumerate(CLASS_ORDER):
    print(f"  {name}: {(pred_erm == i).sum()}")

# ---------- PCA 可视化嵌入，按聚类着色 ----------
def pca(m):
    x = m - m.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(x, full_matrices=False)
    return U * S

colors = {1: "#e74c3c", 2: "#8e44ad", 3: "#e67e22", 4: "#7f8c8d"}
labels_c = {1: "non-perovskite", 2: "perovskite (PLZT)", 3: "perovskite (main)", 4: "perovskite (top/depol)"}

fig, axes = plt.subplots(1, 3, figsize=(20, 6.5))

# 图1: JS 嵌入
p_js = pca(emb_js)
ax = axes[0]
for c in sorted(set(cl)):
    idx = np.where(cl == c)[0]
    ax.scatter(p_js[idx, 0], p_js[idx, 1], s=60, color=colors[c], label=f"cluster {c} ({labels_c[c]})")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
ax.set_title("JS-consistency pretrained embedding")
ax.legend(fontsize=8)

# 图2: ERM 嵌入
p_erm = pca(emb_erm)
ax = axes[1]
for c in sorted(set(cl)):
    idx = np.where(cl == c)[0]
    ax.scatter(p_erm[idx, 0], p_erm[idx, 1], s=60, color=colors[c], label=f"cluster {c}")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
ax.set_title("ERM pretrained embedding")
ax.legend(fontsize=8)

# 图3: 对比 JS vs ERM 嵌入的簇间可分性（用 JS 嵌入的前2PC，标 ERM 的前2PC 距离）
ax = axes[2]
# 简单指标：每簇的类内散度 vs 类间距离（JS 相对 ERM）
def cluster_sep(emb):
    centers = []
    for c in sorted(set(cl)):
        idx = np.where(cl == c)[0]
        centers.append(emb[idx].mean(axis=0))
    centers = np.array(centers)
    # 平均类间距离
    d_inter = np.mean([np.linalg.norm(centers[i] - centers[j]) for i in range(len(centers)) for j in range(i + 1, len(centers))])
    # 平均类内散度
    d_intra = np.mean([np.mean([np.linalg.norm(emb[j] - centers[i]) for j in np.where(cl == c)[0]]) for i, c in enumerate(sorted(set(cl)))])
    return d_inter, d_intra, d_inter / (d_intra + 1e-9)

js_sep = cluster_sep(emb_js)
erm_sep = cluster_sep(emb_erm)
ax.bar(["inter-cluster dist", "intra-cluster spread"], 
       [js_sep[0], js_sep[1]], color="C0", alpha=0.7, label="JS")
ax.bar(["inter-cluster dist", "intra-cluster spread"],
       [erm_sep[0], erm_sep[1]], color="C1", alpha=0.7, label="ERM")
ax.set_title("Cluster separability (JS vs ERM)")
ax.legend()
ax.text(0.02, 0.95, f"JS sep ratio={js_sep[2]:.2f}\nERM sep ratio={erm_sep[2]:.2f}",
        transform=ax.transAxes, va="top", fontsize=9)

plt.tight_layout()
png = os.path.join(OUT, "embedding_transfer.png")
fig.savefig(png, dpi=140)
print("\nsaved:", png)
print(f"JS  sep ratio: {js_sep[2]:.3f}")
print(f"ERM sep ratio: {erm_sep[2]:.3f}")
