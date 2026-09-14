# -*- coding: utf-8 -*-
"""解析谭启组 perovskite XRD 数据（.rasx / .txt），统一到 20-80 deg @ 0.02 = 3001 点。"""
import os, re, zipfile, csv
import numpy as np

ROOT = "E:/AI4science/04_external_lab_data/GTIIT/XRD/perovskite"
OUT = "E:/AI4science/outputs/tanlab_phase2"
GRID = np.arange(20.0, 80.0 + 1e-9, 0.02)  # 3001 点
os.makedirs(OUT, exist_ok=True)


def parse_rasx(path):
    """Rigaku .rasx = ZIP，内含 Data0/Profile0.txt（三列 TSV：2θ intensity flag）"""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        prof = next((n for n in names if n.endswith("Profile0.txt")), None)
        if prof is None:
            raise ValueError("no Profile0.txt in rasx")
        raw = z.read(prof).decode("utf-8-sig", errors="replace")
    rows = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            tth = float(parts[0].strip())
            i = float(parts[1].strip())
            rows.append((tth, i))
        except ValueError:
            continue
    if not rows:
        raise ValueError("empty profile")
    rows = sorted(rows)
    tth = np.array([r[0] for r in rows])
    i = np.array([r[1] for r in rows])
    return tth, i


def parse_txt(path):
    """Rigaku RAS_RAW 文本导出：跳过 *... 头部，取两列数值"""
    tth, i = [], []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("*"):
                continue
            parts = s.split()
            if len(parts) < 2:
                continue
            try:
                tth.append(float(parts[0]))
                i.append(float(parts[1]))
            except ValueError:
                continue
    if not tth:
        raise ValueError("empty txt")
    order = np.argsort(tth)
    return np.array(tth)[order], np.array(i)[order]


def to_grid(tth, intensity, grid=GRID):
    """线性插值到统一网格，并 max 归一化"""
    mask = (tth >= grid[0] - 0.05) & (tth <= grid[-1] + 0.05)
    tth = tth[mask]
    intensity = intensity[mask]
    if len(tth) < 2:
        raise ValueError("too few points in range")
    interp = np.interp(grid, tth, intensity)
    mx = interp.max()
    if mx > 0:
        interp = interp / mx
    return interp


def main():
    records = []
    failures = []
    # 收集所有 .rasx 和 .txt
    for dirpath, _, files in os.walk(ROOT):
        for fn in sorted(files):
            low = fn.lower()
            if not (low.endswith(".rasx") or low.endswith(".txt")):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            try:
                if low.endswith(".rasx"):
                    tth, i = parse_rasx(full)
                    src = "rasx"
                else:
                    tth, i = parse_txt(full)
                    src = "txt"
                spec = to_grid(tth, i)
                records.append({
                    "rel": rel,
                    "src": src,
                    "tth_min": round(float(tth.min()), 3),
                    "tth_max": round(float(tth.max()), 3),
                    "n_raw": len(tth),
                    "spec": spec,
                })
            except Exception as e:
                failures.append((rel, src if low.endswith(".rasx") else "txt", str(e)))

    print(f"成功解析: {len(records)} 条")
    print(f"失败: {len(failures)} 条")
    for rel, src, err in failures[:20]:
        print(f"  [FAIL] {src} {rel}: {err}")

    if not records:
        print("无可用数据，退出")
        return

    # 保存
    specs = np.stack([r["spec"] for r in records])
    np.save(os.path.join(OUT, "spectra.npy"), specs)
    np.save(os.path.join(OUT, "grid.npy"), GRID)

    with open(os.path.join(OUT, "manifest.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["idx", "rel_path", "src", "tth_min", "tth_max", "n_raw"])
        for idx, r in enumerate(records):
            w.writerow([idx, r["rel"], r["src"], r["tth_min"], r["tth_max"], r["n_raw"]])

    print(f"\n已保存: {OUT}/spectra.npy  shape={specs.shape}")
    print(f"已保存: {OUT}/grid.npy     shape={GRID.shape}")
    print(f"已保存: {OUT}/manifest.csv ({len(records)} 行)")

    # 统计各样品系列
    from collections import Counter
    series = Counter()
    for r in records:
        # 取顶层子目录作为系列名
        top = r["rel"].split("/")[0]
        series[top] += 1
    print("\n各系列解析数量:")
    for k, v in series.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
