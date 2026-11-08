#!/usr/bin/env bash
# Cloud GPU Python image with compatible preinstalled torch is required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON=python3
"$PYTHON" - <<'PY'
import torch
if not torch.cuda.is_available():
    raise SystemExit("BLOCKED: select a GPU-enabled PyTorch image compatible with this NVIDIA driver")
print("GPU PyTorch",torch.__version__,torch.version.cuda,torch.cuda.get_device_name(0))
PY
"$PYTHON" -m pip install --no-deps -e "$ROOT/xrd_robustness"
"$PYTHON" -m pip install "optuna>=4,<5" "pymatgen==2026.5.4" "numpy>=1.24" "scipy>=1.10" "spglib>=2.0" "pytest>=8" "PyYAML>=6"
"$PYTHON" -m pytest -q "$ROOT/xrd_robustness/tests/training/test_training_objectives.py"
echo "Python/CUDA/Optuna setup pass."
