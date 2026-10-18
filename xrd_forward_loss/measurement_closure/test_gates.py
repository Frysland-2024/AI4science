from pathlib import Path

import numpy as np
import pytest
import torch
from pymatgen.core import Structure

from measurement_closure.audit import expected_profile
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward

ROOT = Path(__file__).resolve().parents[2]
CFG = __import__("json").loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text())


@pytest.fixture(scope="module")
def forward():
    if not torch.cuda.is_available():
        pytest.skip("CUDA required by frozen differentiable forward")
    s = Structure.from_file(ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif")
    return CachedTetragonalGPUForward(s, grid_config=CFG["grid"], parameter_config=CFG["parameterization"], device="cuda", dtype=torch.float64)


def test_q_and_eta_are_independent_coordinates(forward):
    q = torch.tensor([0.1, -0.2], dtype=torch.float64, device="cuda")
    eta = torch.tensor([0.03, 0.12, 0.01, 0.02, 1.0], dtype=torch.float64, device="cuda")
    p1 = expected_profile(forward, q, eta)
    q2 = q.clone(); q2[0] += 0.1
    eta2 = eta.clone(); eta2[0] += 0.02
    p_q = expected_profile(forward, q2, eta)
    p_eta = expected_profile(forward, q, eta2)
    assert not torch.allclose(p1, p_q)
    assert not torch.allclose(p1, p_eta)
    assert torch.all(p1 >= 0)


def test_expected_profile_autograd_matches_finite_difference(forward):
    q = torch.tensor([0.12, -0.17], dtype=torch.float64, device="cuda", requires_grad=True)
    eta = torch.tensor([0.04, 0.12, 0.01, 0.02, 1.0], dtype=torch.float64, device="cuda")
    target = expected_profile(forward, q.detach() + torch.tensor([.01, -.01], device="cuda"), eta)
    loss = (expected_profile(forward, q, eta) - target).square().mean()
    grad, = torch.autograd.grad(loss, (q,))
    eps = 1e-4
    fd=[]
    for i in range(2):
        d=torch.zeros_like(q); d[i]=eps
        fd.append(((expected_profile(forward,q.detach()+d,eta)-target).square().mean() -
                   (expected_profile(forward,q.detach()-d,eta)-target).square().mean()).item()/(2*eps))
    assert np.allclose(grad.detach().cpu().numpy(), fd, rtol=1e-3, atol=1e-8)


def test_noise_draws_are_not_expected_profile_targets(forward):
    q=torch.tensor([0.0,0.0],dtype=torch.float64,device="cuda")
    eta=torch.tensor([0.02,.12,.01,.02,1.0],dtype=torch.float64,device="cuda")
    mu=expected_profile(forward,q,eta).detach().cpu().numpy()
    rng=np.random.default_rng(19)
    draws=np.stack([rng.poisson(np.maximum(mu,0)*30000)/30000 for _ in range(32)])
    assert np.mean(np.abs(draws.mean(axis=0)-mu)) < 2e-3
    assert not np.allclose(draws[0],mu,rtol=1e-5,atol=1e-7)
