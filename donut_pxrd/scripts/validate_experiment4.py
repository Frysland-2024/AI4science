from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("xrd_inversion/src", "xrd_forward_loss/src")]
from pxrd_forward_loss.measurement_closure import expected_profile
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward

DATA = ROOT / "donut_pxrd/results/study_v1/exp3c/data_arrays.npz"
OUT = ROOT / "donut_pxrd/results/study_v1/exp4"
WEIGHT_DIR = Path(r"E:\AI4science_DONUT_checkpoints\donut_pxrd_four_stage_20261019")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lattice(q, structure, parameterization):
    v = np.asarray(q, dtype=np.float64)
    u0 = (2 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    u = u0 + v[..., 0] * parameterization["du_half_range"]
    vv = v0 + v[..., 1] * parameterization["dv_half_range"]
    return np.exp(u-vv/3), np.exp(u+2*vv/3)


def main():
    cfg = json.loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text(encoding="utf-8"))
    study = json.loads((ROOT / "donut_pxrd/configs/experiment4_preregistration.json").read_text(encoding="utf-8"))
    structure = Structure.from_file(ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif")
    forward = CachedTetragonalGPUForward(structure, grid_config=cfg["grid"], parameter_config=cfg["parameterization"], device="cuda", dtype=torch.float64)
    arrays = dict(np.load(DATA))
    raw = json.loads((OUT / "raw_paired_results.json").read_text(encoding="utf-8"))
    expected_ids = set(map(int, arrays["test_indices"]))
    assert sha(DATA) == study["dataset_sha256"]
    assert len(raw) == 1001
    for method in "ABCD":
        for seed in (20261061, 20261062, 20261063):
            rows = [r for r in raw if r["method"] == method and r["seed"] == seed]
            assert len(rows) == 77 and {r["q_parent_index"] for r in rows} == expected_ids
            assert len({r["q_parent_index"] for r in rows}) == 77
    erows = [r for r in raw if r["method"] == "E"]
    assert len(erows) == 77 and {r["q_parent_index"] for r in erows} == expected_ids
    assert all(r["classic_multistart_fits"] and len(r["classic_multistart_fits"]) == 3 for r in erows)
    # Deterministically score the already frozen direct predictions. This audit
    # does not select models, epochs, starts or solver settings.
    direct_rows = [r for r in raw if r["method"] in "ABCD"] + erows
    for method in "ABC":
        for seed in (20261061, 20261062, 20261063):
            p = WEIGHT_DIR / f"exp4_{method}_seed{seed}.pt"
            assert p.exists() and sha(p) == next(r["checkpoint_sha256"] for r in json.loads((OUT / "summary.json").read_text(encoding="utf-8"))["abc_training_records"] if r["method"] == method and r["seed"] == seed)
            checkpoint = torch.load(p, map_location="cpu", weights_only=False)
            assert checkpoint["method"] == method and checkpoint["seed"] == seed
    donut_runs = json.loads((ROOT / "donut_pxrd/results/study_v1/exp3c/test_per_seed.json").read_text(encoding="utf-8"))
    for rec in donut_runs:
        p = Path(rec["checkpoint"])
        assert p.exists() and sha(p) == rec["checkpoint_sha256"]
    for r in direct_rows:
        q = np.asarray(r["q_direct"], dtype=np.float64)
        et = np.asarray(r["eta_direct"], dtype=np.float64)
        a0, c0 = lattice(r["q_true_posthoc"], structure, cfg["parameterization"])
        ap, cp = lattice(q, structure, cfg["parameterization"])
        r["a_abs_error_direct_angstrom"] = float(abs(ap-a0))
        r["c_abs_error_direct_angstrom"] = float(abs(cp-c0))
        if r["method"] in "ABCD":
            jq = np.asarray(r["joint_refinement"]["x"][:2], dtype=float)
            aj, cj = lattice(jq, structure, cfg["parameterization"])
            r["a_abs_error_joint_angstrom"] = float(abs(aj-a0))
            r["c_abs_error_joint_angstrom"] = float(abs(cj-c0))
        else:
            best = r["optimizer_only_best_of_three"]["x"]
            an, cn = lattice(best[:2], structure, cfg["parameterization"])
            r["a_abs_error_joint_angstrom"] = float(abs(an-a0))
            r["c_abs_error_joint_angstrom"] = float(abs(cn-c0))
    # Profile RMSE for direct predictions, grouped into GPU batches.
    obs_lookup = {int(idx): arrays["observed"][idx] for idx in arrays["test_indices"]}
    for method in "ABCDE":
        mr = [r for r in direct_rows if r["method"] == method]
        vals = []
        with torch.no_grad():
            for start in range(0, len(mr), 16):
                batch = mr[start:start+16]
                q = torch.as_tensor([r["q_direct"] for r in batch], device="cuda", dtype=torch.float64)
                eta = torch.as_tensor([r["eta_direct"] for r in batch], device="cuda", dtype=torch.float64)
                target = torch.as_tensor([obs_lookup[r["q_parent_index"]] for r in batch], device="cuda", dtype=torch.float32)
                pred = expected_profile(forward, q, eta, background_shape_mode="v9_polynomial").float()
                vals.extend(torch.sqrt(torch.mean((pred-target)**2, dim=1)).cpu().tolist())
        for r, value in zip(mr, vals):
            r["direct_profile_rmse_posthoc"] = float(value)
    (OUT / "raw_paired_results.json").write_text(json.dumps(raw, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    # Integrity evidence is separate from raw metrics and includes all original
    # frozen weights plus the nine new A/B/C checkpoints.
    initial = json.loads((ROOT / "donut_pxrd/results/resume_audit.json").read_text(encoding="utf-8"))
    files = []
    for r in initial["runs"]:
        p = Path(r["checkpoint"])
        assert sha(p) == r["sha256"]
        files.append({"experiment": r["experiment"], "seed": r["seed"], "path": str(p), "sha256": r["sha256"], "bytes": p.stat().st_size})
    for m in "ABC":
        for seed in (20261061, 20261062, 20261063):
            p = WEIGHT_DIR / f"exp4_{m}_seed{seed}.pt"
            files.append({"experiment": "exp4", "seed": seed, "method": m, "path": str(p), "sha256": sha(p), "bytes": p.stat().st_size})
    validation = {"status": "PASS", "dataset_sha256": sha(DATA), "test_parent_count": len(expected_ids),
                  "raw_row_count": len(raw), "rows_by_method": {m: sum(r["method"] == m for r in raw) for m in "ABCDE"},
                  "same_test_parent_set_all_methods_and_seeds": True, "all_A_to_D_seed_pairs_have_77_rows": True,
                  "classic_E_multistart_count_per_parent": 3, "raw_metrics_recomputed_from_stored_predictions_only": True,
                  "test_used_for_no_selection_or_tuning": True, "checkpoint_count_unique": len(files), "checkpoint_manifest": files}
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in validation.items() if k != "checkpoint_manifest"}, indent=2))


if __name__ == "__main__":
    main()
