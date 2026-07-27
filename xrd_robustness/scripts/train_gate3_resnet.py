#!/usr/bin/env python3
"""Run the existing V7 trainer with the preregistered Gate-3 ML4pXRDs ResNet-18.

This wrapper deliberately reuses the mature data, rendering, evaluation,
checkpoint, provenance, and early-stopping implementation in ``train_v7.py``.
Only the two model-construction globals are replaced before ``train_v7.main`` is
entered. The wrapper accepts exactly the same command-line arguments as
``train_v7.py``; Gate 3 is restricted to ``--mode clean_erm``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.models.ml4pxrd_resnet1d import (  # noqa: E402
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)


def _argument_value(name: str) -> str | None:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        raise SystemExit(f"{name} requires a value")
    return sys.argv[index + 1]


def _gate3_config_factory(*args: Any, **kwargs: Any) -> ML4PXRDResNet1DConfig:
    unexpected = set(kwargs) - {"variant"}
    if unexpected:
        raise TypeError(f"unexpected Gate-3 config arguments: {sorted(unexpected)}")
    if len(args) > 1:
        raise TypeError("Gate-3 config factory accepts at most the legacy variant argument")
    return ML4PXRDResNet1DConfig(model_id="18")


def _load_train_v7_module():
    path = PROJECT_ROOT / "scripts" / "train_v7.py"
    spec = importlib.util.spec_from_file_location("xrd_gate3_train_v7", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import training entry point: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    mode = _argument_value("--mode")
    if mode != "clean_erm":
        raise SystemExit("Foundation Gate 3 permits only --mode clean_erm")
    if _argument_value("--variant") not in {None, "b3"}:
        raise SystemExit("Gate-3 wrapper requires the frozen legacy argument --variant b3")

    train_v7 = _load_train_v7_module()
    train_v7.PAMPTConfig = _gate3_config_factory
    train_v7.PAMPT = ML4PXRDResNet1D
    return int(train_v7.main())


if __name__ == "__main__":
    raise SystemExit(main())
