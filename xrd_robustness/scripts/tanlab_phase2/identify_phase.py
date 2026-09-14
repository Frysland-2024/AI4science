# -*- coding: utf-8 -*-
"""方案A：自动检峰 + 钙钛矿/烧绿石标准峰位对比，给 4 个簇判相"""
import os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

OUT = "E:/AI4science/outputs/tanlab_phase2"
specs = np.load(os.path.join(OUT, "spectra.npy"))
grid = np.load(os.path.join(OUT, "grid.npy"))
LAMBDA = 1.5406  # Cu Kα

# 读取聚类归属
short, rel, series, cl = [], [], [], []
with open(os.path.join(OUT, "cluster_assignment.csv"), encoding="utf-8-sig") as f:
    rd = csv.reader(f)
    next(rd)
    for row in rd:
        short.append(row[0]); rel.append(row[1]); series.append(row[2]); cl.append(int(row[3]))
short = np.array(short); cl = np.array(cl)
K = int(cl.max())


def d_to_2theta(d):
    return 2 * np.degrees(np.arcsin(np.clip(LAMBDA / (2 * d), -1, 1)))


def hkl_2theta(a, hkl):
    h, k, l = hkl
    d = a / np.sqrt(h * h + k * k + l * l)
    return d_to_2theta(d)


# 标准峰位表：伪立方钙钛矿 ABO3 (Pm-3m) + 烧绿石 (Fd-3m)
A_PERV = 4.04  # PZT/PNN 伪立方晶胞
A_PYRO = 10.4  # 烧绿石 Pb2Nb2O7 类
perv_hkl = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 1, 0), (2, 1, 1), (2, 2, 0), (3, 1, 0)]
pyro_hkl = [(2, 2, 2), (4, 0, 0), (4, 4, 0), (6, 2, 2), (4, 4, 4)]
# 用 a 精确算
perv_peaks = {hkl: hkl_2theta(A_PERV, hkl) for hkl in perv_hkl}
pyro_peaks = {hkl: hkl_2theta(A_PYRO, hkl) for hkl in pyro_hkl}

print("伪立方钙钛矿标准峰位 (a=4.04 Å):")
for hkl, v in perv_peaks.items():
    print(f"  {hkl}: {v:.2f}°")
print("烧绿石标准峰位 (a=10.4 Å):")
for hkl, v in pyro_peaks.items():
    print(f"  {hkl}: {v:.2f}°")


def detect_peaks(spec, prominence=0.04, min_dist_deg=0.5):
    dx = grid[1] - grid[0]
    min_dist = int(min_dist_deg / dx)
    pks, props = find_peaks(spec, prominence=prominence, distance=min_dist)
    return pks, props["prominences"]


def nearest(peak, table):
    """找峰位最近的已知标准峰，返回 (hkl, 标准2θ, Δ)"""
    best = None
    for key, tth in table.items():
        d = abs(peak - tth)
        if best is None or d < best[1]:
            best = (key, d, tth)
    return best  # (hkl, Δ, 标准2θ)


results = []
fig, axes = plt.subplots(2, 2, figsize=(17, 11))
axes = axes.ravel()

for c in range(1, K + 1):
    idx = np.where(cl == c)[0]
    mean_spec = specs[idx].mean(axis=0)
    pks, prom = detect_peaks(mean_spec)
    # 按强度（谱高）排序取前 12 个峰
    top = sorted(pks, key=lambda p: mean_spec[p], reverse=True)[:12]
    top = sorted(top)  # 按 2θ 排序

    # 匹配
    peak_rows = []
    has_pyro = False
    tetragonal_split = False
    for p in top:
        tth = grid[p]
        # 找最近的钙钛矿峰
        key_p, dp, tth_p = nearest(tth, perv_peaks)
        key_y, dy, tth_y = nearest(tth, pyro_peaks)
        tag = ""
        if dp < 0.8:
            tag = f"perovskite {key_p} (Δ={dp:+.2f}°)"
        elif dy < 0.8:
            tag = f"PYROCHLORE {key_y} (Δ={dy:+.2f}°)"
            has_pyro = True
        peak_rows.append((tth, mean_spec[p], tag))

    # 200 峰分裂判断：44-46° 之间是否有 >=2 个峰
    region = [p for p in pks if 43.5 <= grid[p] <= 46.0]
    tetragonal_split = len(region) >= 2

    # 非晶鼓包判断：20-26° 的均值背景相对峰值
    low = (grid >= 20) & (grid <= 26)
    amorphous = mean_spec[low].mean() > 0.25  # 归一化后，低角度持续高位 ≈ 非晶

    # 钙钛矿主峰强度：31.3°±0.5° 区间是否有强峰
    perv_main = [p for p in pks if 30.8 <= grid[p] <= 31.8]
    perv_main_strong = any(mean_spec[p] > 0.5 for p in perv_main)

    # 结论（英文，避免 matplotlib 中文字体缺失）
    if not perv_main_strong:
        verdict = "non-perovskite (amorphous/mixed oxide/pyrochlore)"
    elif has_pyro:
        verdict = "perovskite + pyrochlore impurity"
    else:
        sym = "tetragonal" if tetragonal_split else "pseudocubic/cubic"
        verdict = f"pure perovskite ({sym})"

    results.append({
        "cluster": c, "n": len(idx), "verdict": verdict,
        "n_peaks": len(pks), "tetragonal_split": tetragonal_split,
        "has_pyro": has_pyro, "amorphous": amorphous,
        "perv_main_strong": perv_main_strong,
        "members": ", ".join(sorted(set(short[idx]))[:8]),
    })

    # 画图
    ax = axes[c - 1]
    ax.plot(grid, mean_spec, "k-", lw=1.2, label="mean spectrum")
    ax.scatter(grid[top], mean_spec[top], color="red", s=30, zorder=5, label="detected peaks")
    for hkl, v in perv_peaks.items():
        ax.axvline(v, color="C0", ls="--", lw=0.8, alpha=0.6)
    for hkl, v in pyro_peaks.items():
        ax.axvline(v, color="C1", ls=":", lw=0.8, alpha=0.7)
    ax.set_xlabel("2θ (deg)"); ax.set_ylabel("intensity")
    ax.set_title(f"cluster {c} (n={len(idx)})\n{verdict}", fontsize=10)
    ax.legend(fontsize=7)
    ax.set_xlim(20, 80)

    print(f"\n===== cluster {c} (n={len(idx)}) =====")
    print(f"  结论: {verdict}")
    print(f"  200峰分裂(tetragonal): {tetragonal_split} | 烧绿石峰: {has_pyro} | 非晶鼓包: {amorphous}")
    for tth, h, tag in peak_rows:
        print(f"    {tth:6.2f}°  I={h:.2f}  {tag}")

# 图例说明
axes[0].text(0.98, 0.02, "blue dash=perovskite  red dot=pyrochlore", transform=axes[0].transAxes,
             ha="right", fontsize=8, color="gray")
plt.tight_layout()
png = os.path.join(OUT, "peak_identification.png")
fig.savefig(png, dpi=140)
print("\nsaved:", png)

# 保存结论
with open(os.path.join(OUT, "phase_verdict.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["cluster", "n", "verdict", "tetragonal_split", "has_pyro", "amorphous", "n_peaks", "members"])
    for r in results:
        w.writerow([r["cluster"], r["n"], r["verdict"], r["tetragonal_split"],
                    r["has_pyro"], r["amorphous"], r["n_peaks"], r["members"]])
print("saved:", os.path.join(OUT, "phase_verdict.csv"))
