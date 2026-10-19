from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("donut_pxrd/src", "xrd_inversion/src", "xrd_forward_loss/src")]
from donut_pxrd.model import DonutPXRD
CKPT = Path(r"E:\AI4science_DONUT_checkpoints\donut_pxrd_four_stage_20261019")
DATA = ROOT / "donut_pxrd/results/study_v1"
SEEDS = (20261061, 20261062, 20261063)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    cfg_bytes = (ROOT / "donut_pxrd/configs/study_v1.json").read_bytes()
    prereg = json.loads((ROOT / "donut_pxrd/configs/preregistration_manifest.json").read_text(encoding="utf-8-sig"))
    assert hashlib.sha256(cfg_bytes).hexdigest() == prereg["config_sha256"]
    records = []
    parent_split = None
    for exp in ("exp1", "exp2", "exp3a", "exp3b", "exp3c"):
        data = DATA / exp
        npz = data / "data_arrays.npz"
        assert npz.is_file(), npz
        arrays = dict(np.load(npz))
        manifest = json.loads((data / "data_manifest.json").read_text())
        for key in ("train_indices", "validation_indices", "test_indices"):
            expected = manifest["arrays_sha256"][key]
            actual = hashlib.sha256(str(arrays[key].dtype).encode() + json.dumps(arrays[key].shape).encode() + np.ascontiguousarray(arrays[key]).tobytes()).hexdigest()
            assert actual == expected, (exp, key, actual, expected)
        test = arrays["test_indices"].tolist()
        if exp == "exp3c":
            parent_split = {k: arrays[k].tolist() for k in ("train_indices", "validation_indices", "test_indices")}
            assert len(test) == 77 and len(set(test)) == 77
        per_seed = json.loads((data / "test_per_seed.json").read_text())
        assert {int(r["seed"]) for r in per_seed} == set(SEEDS)
        assert all(r["test_indices"] == test for r in per_seed)
        for rec in per_seed:
            path = Path(rec["checkpoint"])
            if not path.is_absolute():
                path = CKPT / path.name
            actual_sha = sha(path)
            assert actual_sha == rec["checkpoint_sha256"], (exp, rec["seed"], actual_sha, rec["checkpoint_sha256"])
            ck = torch.load(path, map_location="cpu", weights_only=False)
            assert ck["seed"] == rec["seed"] and ck["epoch"] == rec["best_epoch"]
            model = DonutPXRD(tuple(ck["latent_names"]), output_length=arrays["observed"].shape[1])
            model.load_state_dict(ck["state_dict"])
            records.append({"experiment": exp, "seed": rec["seed"], "checkpoint": str(path), "sha256": actual_sha,
                            "best_epoch": rec["best_epoch"], "training_seconds": rec["training_seconds"],
                            "mean_q_mae": rec["mean_q_mae"], "profile_rmse": rec["test_profile_rmse"], "checkpoint_reload": "PASS"})
    assert parent_split is not None
    # Verify that both branches backpropagate to encoder parameters on fixed
    # physics, without evaluating or tuning on held-out examples.
    from pymatgen.core import Structure
    from pxrd_forward_loss.measurement_closure import expected_profile
    from xrd_inversion.gpu_forward import CachedTetragonalGPUForward
    config = json.loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text(encoding="utf-8"))
    structure = Structure.from_file(ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif")
    forward = CachedTetragonalGPUForward(structure, grid_config=config["grid"], parameter_config=config["parameterization"], device="cuda", dtype=torch.float64)
    model = DonutPXRD(("du", "dv"), output_length=len(forward.axis)).cuda()
    x = torch.rand(2, 1, len(forward.axis), device="cuda")
    latent, decoded = model(x)
    decoder_grad = torch.autograd.grad(torch.nn.functional.smooth_l1_loss(decoded, x), model.encoder[-1].weight, retain_graph=True)[0]
    q = torch.stack((0.8 * latent[:, 0] / 1.7159, 0.8 * latent[:, 1] / 1.7159), dim=1).double()
    eta = torch.tensor([[0.0, 0.08, 200 / 30000]] * 2, device="cuda", dtype=torch.float64)
    physics = expected_profile(forward, q, eta, background_shape_mode="simple_linear_counts").float()
    physics_grad = torch.autograd.grad(torch.nn.functional.smooth_l1_loss(physics, x[:, 0, :]), model.encoder[-1].weight)[0]
    assert torch.isfinite(decoder_grad).all() and decoder_grad.abs().sum() > 0
    assert torch.isfinite(physics_grad).all() and physics_grad.abs().sum() > 0
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    out = {"status": "PASS", "frozen_config_sha256": prereg["config_sha256"], "source_fidelity_audit_sha256": prereg["source_fidelity_audit_sha256"],
           "exp3c_split_counts": {k: len(v) for k, v in parent_split.items()}, "exp3c_test_indices": parent_split["test_indices"],
           "checkpoint_count": len(records), "all_checkpoint_hashes_match": True, "all_checkpoints_load_state_dict": True,
           "decoder_loss_encoder_gradient": "PASS", "physics_loss_encoder_gradient": "PASS",
           "runs": records, "historical_gpu_training_seconds": sum(x["training_seconds"] for x in records)}
    (ROOT / "donut_pxrd/results/resume_audit.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("runs", "exp3c_test_indices")}, indent=2))


if __name__ == "__main__":
    main()
