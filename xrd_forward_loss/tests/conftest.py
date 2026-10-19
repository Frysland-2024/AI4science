from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from pymatgen.core import Structure

from xrd_inversion.gpu_forward import CachedTetragonalGPUForward


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def closure_context():
    if not torch.cuda.is_available():
        pytest.skip("Issue #19 numerical Gates require CUDA")
    config_path = ROOT / "xrd_inversion/configs/week1_formal_gate.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    structure = Structure.from_file(
        ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif"
    )
    forward = CachedTetragonalGPUForward(
        structure,
        grid_config=config["grid"],
        parameter_config=config["parameterization"],
        device="cuda",
        dtype=torch.float64,
    )
    return ROOT, config, structure, forward
