from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("xrd_inversion/src", "xrd_forward_loss/src", "donut_pxrd/src")]
from donut_pxrd.model import DonutPXRD, physical_latent
from pxrd_forward_loss.measurement_closure import expected_profile
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward


def test_decoder_is_latent_only_and_shape_matches():
    model = DonutPXRD(("du", "dv"), output_length=3501)
    observed = torch.rand(2, 1, 3501)
    latent, decoded = model(observed)
    assert latent.shape == (2, 2)
    assert decoded.shape == (2, 1, 3501)
    assert not any("skip" in name.lower() for name, _ in model.named_modules())


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA physics gradient integration gate")
def test_both_donut_losses_reach_encoder_through_fixed_physics():
    config = json.loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text())
    structure = Structure.from_file(ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif")
    forward = CachedTetragonalGPUForward(structure, grid_config=config["grid"], parameter_config=config["parameterization"], device="cuda", dtype=torch.float64)
    model = DonutPXRD(("du", "dv"), output_length=len(forward.axis)).cuda()
    x = torch.rand(2, 1, len(forward.axis), device="cuda")
    latent, decoded = model(x)
    dl = F.smooth_l1_loss(decoded, x)
    dl_grad = torch.autograd.grad(dl, model.encoder[-1].weight, retain_graph=True)[0]
    assert torch.isfinite(dl_grad).all() and dl_grad.abs().sum() > 0
    physical = physical_latent(latent, ("du", "dv"))
    q = torch.stack((physical["du"], physical["dv"]), dim=1).to(torch.float64)
    eta = torch.tensor([[0.0, 0.08, 200.0 / 30000.0]] * 2, device="cuda", dtype=torch.float64)
    physics = expected_profile(forward, q, eta, background_shape_mode="simple_linear_counts").float()
    pl = F.smooth_l1_loss(physics, x[:, 0, :])
    pl_grad = torch.autograd.grad(pl, model.encoder[-1].weight)[0]
    assert torch.isfinite(pl_grad).all() and pl_grad.abs().sum() > 0
