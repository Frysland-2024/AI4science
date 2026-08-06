#!/usr/bin/env python3
"""Build RRUFF pipeline smoke-test set: stratified 5 per class, independent of RRUFF-371."""
import os, json, re, zipfile, hashlib, random
import numpy as np
from collections import Counter

CLASS_ORDER = ("triclinic","monoclinic","orthorhombic","tetragonal","trigonal","hexagonal","cubic")
GRID = 10.0 + np.arange(3501, dtype=np.float64) * 0.02
PER_CLASS = 5
SEED = 20260806
EVIDENCE_DIR = r"E:/AI4science/xrd_robustness/data/real_xrd/rruff371/evidence"
SOURCE_DIR  = r"E:/AI4science/xrd_robustness/data/real_xrd/rruff350/source_archives"
OUT_DIR     = r"E:/AI4science/xrd_robustness/data/real_xrd/rruff_pipeline_test"

# ── SG lookup table (H-M → crystal system) ──
_SG_TABLE = """
P1:triclinic P-1:triclinic P2:monoclinic P21:monoclinic C2:monoclinic Pm:monoclinic Pc:monoclinic Cm:monoclinic Cc:monoclinic
P2/m:monoclinic P21/m:monoclinic C2/m:monoclinic P2/c:monoclinic P21/c:monoclinic C2/c:monoclinic
P222:orthorhombic P2221:orthorhombic P21212:orthorhombic P212121:orthorhombic C2221:orthorhombic C222:orthorhombic F222:orthorhombic I222:orthorhombic I212121:orthorhombic
Pmm2:orthorhombic Pmc21:orthorhombic Pcc2:orthorhombic Pma2:orthorhombic Pca21:orthorhombic Pnc2:orthorhombic Pmn21:orthorhombic Pba2:orthorhombic Pna21:orthorhombic Pnn2:orthorhombic
Cmm2:orthorhombic Cmc21:orthorhombic Ccc2:orthorhombic Amm2:orthorhombic Abm2:orthorhombic Ama2:orthorhombic Aba2:orthorhombic Fmm2:orthorhombic Fdd2:orthorhombic Imm2:orthorhombic Iba2:orthorhombic Ima2:orthorhombic
Pmmm:orthorhombic Pnnn:orthorhombic Pccm:orthorhombic Pban:orthorhombic Pmma:orthorhombic Pnna:orthorhombic Pmna:orthorhombic Pcca:orthorhombic Pbam:orthorhombic Pccn:orthorhombic Pbcm:orthorhombic Pnnm:orthorhombic Pmmn:orthorhombic Pbcn:orthorhombic Pbca:orthorhombic Pnma:orthorhombic
Cmcm:orthorhombic Cmca:orthorhombic Cmmm:orthorhombic Cccm:orthorhombic Cmma:orthorhombic Ccca:orthorhombic Fmmm:orthorhombic Fddd:orthorhombic Immm:orthorhombic Ibam:orthorhombic Ibca:orthorhombic Imma:orthorhombic
P4:tetragonal P41:tetragonal P42:tetragonal P43:tetragonal I4:tetragonal I41:tetragonal P-4:tetragonal I-4:tetragonal
P4/m:tetragonal P42/m:tetragonal P4/n:tetragonal P42/n:tetragonal I4/m:tetragonal I41/a:tetragonal
P422:tetragonal P4212:tetragonal P4122:tetragonal P41212:tetragonal P4222:tetragonal P42212:tetragonal P4322:tetragonal P43212:tetragonal I422:tetragonal I4122:tetragonal
P4mm:tetragonal P4bm:tetragonal P42cm:tetragonal P42nm:tetragonal P4cc:tetragonal P4nc:tetragonal P4mc:tetragonal P42bc:tetragonal I4mm:tetragonal I4cm:tetragonal I41md:tetragonal I41cd:tetragonal
P-42m:tetragonal P-42c:tetragonal P-421m:tetragonal P-421c:tetragonal P-4m2:tetragonal P-4c2:tetragonal P-4b2:tetragonal P-4n2:tetragonal I-4m2:tetragonal I-4c2:tetragonal I-42m:tetragonal I-42d:tetragonal
P4/mmm:tetragonal P4/mcc:tetragonal P4/nbm:tetragonal P4/nnc:tetragonal P4/mbm:tetragonal P4/mnc:tetragonal P4/nmm:tetragonal P4/ncc:tetragonal P42/mmc:tetragonal P42/mcm:tetragonal P42/nbc:tetragonal P42/nnm:tetragonal P42/mbc:tetragonal P42/mnm:tetragonal P42/nmc:tetragonal P42/ncm:tetragonal I4/mmm:tetragonal I4/mcm:tetragonal I41/amd:tetragonal I41/acd:tetragonal
P3:trigonal P31:trigonal P32:trigonal R3:trigonal P-3:trigonal R-3:trigonal
P312:trigonal P321:trigonal P3112:trigonal P3121:trigonal P3212:trigonal P3221:trigonal R32:trigonal P3m1:trigonal P31m:trigonal P3c1:trigonal P31c:trigonal R3m:trigonal R3c:trigonal
P-31m:trigonal P-31c:trigonal P-3m1:trigonal P-3c1:trigonal R-3m:trigonal R-3c:trigonal
P6:hexagonal P61:hexagonal P65:hexagonal P62:hexagonal P64:hexagonal P63:hexagonal P-6:hexagonal
P6/m:hexagonal P63/m:hexagonal P622:hexagonal P6122:hexagonal P6522:hexagonal P6222:hexagonal P6322:hexagonal
P6mm:hexagonal P6cc:hexagonal P63cm:hexagonal P63mc:hexagonal P-6m2:hexagonal P-6c2:hexagonal P-62m:hexagonal P-62c:hexagonal
P6/mmm:hexagonal P6/mcc:hexagonal P63/mcm:hexagonal P63/mmc:hexagonal
P23:cubic F23:cubic I23:cubic P213:cubic I213:cubic
Pm-3:cubic Pn-3:cubic Fm-3:cubic Fd-3:cubic Im-3:cubic Pa-3:cubic Ia-3:cubic
P432:cubic P4232:cubic F432:cubic F4132:cubic I432:cubic P4332:cubic P4132:cubic I4132:cubic
P-43m:cubic F-43m:cubic I-43m:cubic P-43n:cubic F-43c:cubic I-43d:cubic
Pm-3m:cubic Pn-3n:cubic Pm-3n:cubic Pn-3m:cubic Fm-3m:cubic Fm-3c:cubic Fd-3m:cubic Fd-3c:cubic Im-3m:cubic Ia-3d:cubic
"""
SG_LOOKUP = {}
for tok in _SG_TABLE.strip().split():
    if ":" in tok:
        sg, cs = tok.split(":")
        SG_LOOKUP[sg] = cs
# Non-standard settings
SG_ALIASES = {"Pbnm": "Pnma", "Pnam": "Pnma", "Bbnm": "Cmcm", "Bmab": "Cmca"}

random.seed(SEED)

# ═══════════════════════════════════════
# STEP 1: get used IDs from RRUFF-371
# ═══════════════════════════════════════
print("Reading used IDs from evidence...")
used = {}
for fname in os.listdir(EVIDENCE_DIR):
    if not fname.endswith(".json"):
        continue
    with open(os.path.join(EVIDENCE_DIR, fname)) as f:
        d = json.load(f)
    headers = d.get("headers", {})
    rid = headers.get("RRUFFID", "")
    cell = headers.get("CELL PARAMETERS", "")
    m = re.search(r"crystal system:\s*(\w+)", cell)
    cs = m.group(1).lower() if m else ""
    if rid and cs in CLASS_ORDER:
        used[rid] = cs
print(f"  Used: {len(used)}  (per class: {dict(Counter(used.values()))})")

# ═══════════════════════════════════════
# STEP 2: scan DIF archive for unused
# ═══════════════════════════════════════
print("Scanning DIF archive...")
dif_z = zipfile.ZipFile(os.path.join(SOURCE_DIR, "DIF.zip"))
available = {}
no_sg = 0
for name in dif_z.namelist():
    m = re.search(r"(R\d{6})", name)
    if not m:
        continue
    rid = m.group(1)
    if rid in used or rid in available:
        continue
    text = dif_z.read(name).decode("utf-8", errors="replace")
    sg_m = re.search(r"SPACE GROUP:\s*(\S+)", text)
    if not sg_m:
        no_sg += 1
        continue
    sg = sg_m.group(1).strip()
    # Normalise
    sg_clean = sg.replace(" ", "")
    sg_clean = SG_ALIASES.get(sg_clean, sg_clean)
    cs = SG_LOOKUP.get(sg_clean)
    if cs:
        available[rid] = cs
dif_z.close()
print(f"  Available unused: {len(available)}  (skipped no-SG: {no_sg})")
for cs in CLASS_ORDER:
    print(f"    {cs}: {sum(1 for v in available.values() if v==cs)}")

# ═══════════════════════════════════════
# STEP 3: filter by RAW availability
# ═══════════════════════════════════════
print("Checking RAW availability...")
raw_z = zipfile.ZipFile(os.path.join(SOURCE_DIR, "XY_RAW.zip"))
has_raw = set()
for name in raw_z.namelist():
    m = re.search(r"(R\d{6})", name)
    if m and name.endswith(".txt"):
        has_raw.add(m.group(1))
raw_z.close()

valid = {rid: cs for rid, cs in available.items() if rid in has_raw}
print(f"  With RAW: {len(valid)}")

# ═══════════════════════════════════════
# STEP 4: stratified sample
# ═══════════════════════════════════════
selected = {}
for cs in CLASS_ORDER:
    pool = sorted([rid for rid, c in valid.items() if c == cs])
    n = min(PER_CLASS, len(pool))
    chosen = random.sample(pool, n)
    selected[cs] = chosen
    print(f"  Selected {cs}: {chosen}")

# ═══════════════════════════════════════
# STEP 5: extract + preprocess
# ═══════════════════════════════════════
os.makedirs(os.path.join(OUT_DIR, "spectra"), exist_ok=True)
raw_z = zipfile.ZipFile(os.path.join(SOURCE_DIR, "XY_RAW.zip"))
manifest_rows = []

for cs, ids in selected.items():
    for rid in ids:
        # find RAW
        raw_data = None
        for name in raw_z.namelist():
            if rid in name and name.endswith(".txt"):
                raw_data = raw_z.read(name)
                break
        if raw_data is None:
            print(f"  MISSING: {rid}")
            continue

        text = raw_data.decode("utf-8", errors="replace").replace("\r", "")
        x_vals, y_vals = [], []
        in_header = True
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("##"):
                in_header = False
                continue
            if in_header:
                continue
            # Comma-separated: 2θ, intensity
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    x_vals.append(float(parts[0].strip()))
                    y_vals.append(float(parts[1].strip()))
                except ValueError:
                    continue

        if len(x_vals) < 20:
            print(f"  TOO SHORT: {rid} ({len(x_vals)} pts)")
            continue

        x = np.array(x_vals, dtype=np.float64)
        y = np.array(y_vals, dtype=np.float64)
        order = np.argsort(x)
        x, y = x[order], y[order]
        mask = np.ones(len(x), dtype=bool)
        mask[1:] = np.diff(x) > 0
        x, y = x[mask], y[mask]

        profile = np.interp(GRID, x, y, left=0.0, right=0.0)
        pmax = float(profile.max())
        if pmax <= 0:
            print(f"  ZERO MAX: {rid}")
            continue
        profile = profile / pmax

        out_path = os.path.join(OUT_DIR, "spectra", f"{rid}.npy")
        np.save(out_path, profile.astype(np.float32))
        manifest_rows.append({
            "rruff_id": rid,
            "crystal_system": cs,
            "two_theta_min_original": round(float(x.min()), 4),
            "two_theta_max_original": round(float(x.max()), 4),
            "profile_sha256": hashlib.sha256(profile.tobytes()).hexdigest()[:16],
        })

raw_z.close()

# ── manifest ──
manifest = {
    "dataset_id": "rruff-pipeline-test-v1",
    "description": "Pipeline smoke test — 5/class stratified, independent of RRUFF-371",
    "seed": SEED,
    "total": len(manifest_rows),
    "crystal_systems": list(CLASS_ORDER),
    "preprocessing": {"two_theta_min": 10.0, "two_theta_max": 80.0, "step": 0.02, "points": 3501, "normalization": "max", "interpolation": "linear"},
    "role": "pipeline_smoke_test_only__no_paper_numbers",
    "samples": manifest_rows,
}
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"\nDone. {len(manifest_rows)} samples → {OUT_DIR}")
for cs in CLASS_ORDER:
    print(f"  {cs}: {sum(1 for r in manifest_rows if r['crystal_system']==cs)}")
