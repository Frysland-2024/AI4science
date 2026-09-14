# -*- coding: utf-8 -*-
"""谭启组 perovskite XRD 聚类可视化 v2：清晰的四联图"""
import os, csv, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

OUT = "E:/AI4science/outputs/tanlab_phase2"
specs = np.load(os.path.join(OUT, "spectra.npy"))
grid = np.load(os.path.join(OUT, "grid.npy"))

labels = []
with open(os.path.join(OUT, "manifest.csv"), encoding="utf-8-sig") as f:
    rd = csv.reader(f)
    next(rd)
    for row in rd:
        labels.append(row[1])

def short_name(rel):
    base = os.path.basename(rel)
    base = re.sub(r"\.(rasx|txt)$", "", base, flags=re.I)
    base = base.replace("_1250_6h(2.0)", "").replace("(2.0)", "")
    return base.strip()

def series_of(rel):
    top = os.path.normpath(rel).split(os.sep)[0]
    return top

short = [short_name(l) for l in labels]
series = [series_of(l) for l in labels]
N = len(short)

# ---------- PCA ----------
X = specs - specs.mean(axis=0, keepdims=True)
U, S, Vt = np.linalg.svd(X, full_matrices=False)
pcs = U * S
evr = (S ** 2) / (S ** 2).sum()

# ---------- 聚类（相关系数距离 + average linkage）----------
corr = np.corrcoef(specs)
corr = (corr + corr.T) / 2.0
corr = np.clip(corr, -1.0, 1.0)
dist = 1 - corr
np.fill_diagonal(dist, 0.0)
Z = linkage(dist, method="average")
K = 4
cl = fcluster(Z, K, criterion="maxclust")

# ---------- 系列配色 ----------
series_names = sorted(set(series))
series_colors = {s: plt.cm.tab10(i) for i, s in enumerate(series_names)}
cluster_colors = {c: plt.cm.Set1((c - 1) / max(K - 1, 1)) for c in range(1, K + 1)}

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

# 图1: 谱叠加，按系列着色
ax = axes[0, 0]
for s in series_names:
    idx = [j for j in range(N) if series[j] == s]
    for j in idx:
        ax.plot(grid, specs[j], color=series_colors[s], alpha=0.45, lw=0.7)
ax.set_xlabel("2θ (deg)"); ax.set_ylabel("normalized intensity")
ax.set_title(f"All {N} spectra — colored by series")
ax.legend(handles=[plt.Line2D([0], [0], color=series_colors[s], lw=2, label=s) for s in series_names],
          fontsize=9, loc="upper right")

# 图2: PCA 散点，按聚类着色
ax = axes[0, 1]
for c in range(1, K + 1):
    idx = [j for j in range(N) if cl[j] == c]
    ax.scatter(pcs[idx, 0], pcs[idx, 1], s=55, alpha=0.85,
               color=cluster_colors[c], label=f"cluster {c} (n={len(idx)})")
ax.set_xlabel(f"PC1 ({evr[0]*100:.1f}%)"); ax.set_ylabel(f"PC2 ({evr[1]*100:.1f}%)")
ax.set_title("PCA — colored by cluster (K=4)")
ax.legend(fontsize=9)
ax.axhline(0, color="gray", lw=0.5); ax.axvline(0, color="gray", lw=0.5)

# 图3: 每簇平均谱
ax = axes[1, 0]
for c in range(1, K + 1):
    idx = [j for j in range(N) if cl[j] == c]
    mean_spec = specs[idx].mean(axis=0)
    ax.plot(grid, mean_spec, color=cluster_colors[c], lw=1.8,
            label=f"cluster {c} mean (n={len(idx)})")
ax.set_xlabel("2θ (deg)"); ax.set_ylabel("normalized intensity")
ax.set_title("Cluster mean spectra")
ax.legend(fontsize=9)

# 图4: dendrogram
ax = axes[1, 1]
dendrogram(Z, labels=short, leaf_font_size=5, orientation="left", ax=ax,
           color_threshold=Z[-K + 1, 2] if K > 1 else 0)
ax.set_title("Hierarchical clustering (correlation distance, average linkage)")
ax.set_xlabel("distance")

plt.tight_layout()
out_png = os.path.join(OUT, "clustering_v2.png")
fig.savefig(out_png, dpi=140)
print("saved:", out_png)

# 保存聚类结果
with open(os.path.join(OUT, "cluster_assignment.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["short_name", "rel_path", "series", "cluster_k4"])
    for j in range(N):
        w.writerow([short[j], labels[j], series[j], int(cl[j])])
print("saved:", os.path.join(OUT, "cluster_assignment.csv"))

# 打印每簇成员
print(f"\n===== K={K} 分组 =====")
for c in range(1, K + 1):
    members = [short[j] for j in range(N) if cl[j] == c]
    print(f"cluster {c} (n={len(members)}): {', '.join(members[:12])}{' ...' if len(members)>12 else ''}")
