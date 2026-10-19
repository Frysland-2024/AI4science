"""Optional, read-only adapter for the frozen 7-crystal-system checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import sys

import numpy as np

CLASSES = ("triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic")
EXPECTED_CHECKPOINT_SHA256 = "3ee1beb8831e46a8d7014352d5c1adfac49b7fe8959894811c1cb559b2cc6b49"
EXPECTED_MODEL_SOURCE_SHA256 = "2d048344865bbe5667bb235d8d3c851a9d6eea60fc1835f722bf0b10114ce276"
EXPECTED_LABEL_SOURCE_SHA256 = "745c020dacf4c4214d1f17edf902012784487240c56d02fd1c43e158c458b655"
EXPECTED_CONFIG = {
    "model_id": "18", "input_length": 3501, "num_classes": 7,
    "group_norm_groups": 32, "group_norm_eps": 0.001,
    "square_kernel_size_and_stride": True, "add_additional_dense_layer": True,
    "dense_width": 256, "embed_dim": 256,
}


@dataclass(frozen=True)
class ClassifierStatus:
    available: bool
    message: str
    classes: tuple[str, ...] = CLASSES
    checkpoint: str | None = None
    checkpoint_sha256: str | None = None
    probabilities: tuple[float, ...] | None = None
    input_contract: str = "3501 max-normalized samples on 10-80 deg, 0.02 deg step; simulator CuKa 1.54184 A"

    @property
    def prior(self) -> dict[str, float] | None:
        if not self.available or self.probabilities is None:
            return None
        return dict(zip(self.classes, self.probabilities, strict=True))


def _default_paths() -> tuple[Path, Path]:
    ai4science = Path(__file__).resolve().parents[4]
    repo = Path(os.environ.get("PXRD_CLASSIFIER_REPO", ai4science / "xrd_robustness"))
    checkpoint = Path(os.environ.get(
        "PXRD_CLASSIFIER_CHECKPOINT",
        repo / "outputs/simulated_test_checkpoints/checkpoints/seed_20260711_js_lambda_60/best.ckpt",
    ))
    return repo, checkpoint


def load_optional_prior(checkpoint: str | Path | None = None, *,
                        two_theta: np.ndarray | None = None,
                        intensity: np.ndarray | None = None,
                        wavelength_angstrom: float | None = None) -> ClassifierStatus:
    """Infer only on the checkpoint's exact 10-80 / 0.02 degree profile contract."""
    repo, default_checkpoint = _default_paths()
    ckpt = Path(checkpoint).resolve() if checkpoint else default_checkpoint.resolve()
    if not ckpt.is_file():
        return ClassifierStatus(False, "classifier unavailable: no local frozen checkpoint")
    try:
        digest = hashlib.sha256(ckpt.read_bytes()).hexdigest()
        if digest != EXPECTED_CHECKPOINT_SHA256:
            return ClassifierStatus(False, "classifier unavailable: frozen checkpoint SHA-256 mismatch", checkpoint=str(ckpt), checkpoint_sha256=digest)
        if two_theta is None or intensity is None:
            return ClassifierStatus(False, "classifier checkpoint verified; provide a measured profile on the exact training axis", checkpoint=str(ckpt), checkpoint_sha256=digest)
        axis = np.asarray(two_theta, dtype=np.float64)
        values = np.asarray(intensity, dtype=np.float64)
        exact_axis = np.linspace(10.0, 80.0, 3501, dtype=np.float64)
        if axis.shape != exact_axis.shape or values.shape != exact_axis.shape or not np.allclose(axis, exact_axis, rtol=0.0, atol=2e-5):
            return ClassifierStatus(False, "classifier unavailable: input does not match the 3501-point 10-80 degree 0.02 degree axis", checkpoint=str(ckpt), checkpoint_sha256=digest)
        if wavelength_angstrom is None or abs(float(wavelength_angstrom) - 1.54184) > 5e-6:
            return ClassifierStatus(False, "classifier unavailable: wavelength is outside the frozen simulator CuKa contract", checkpoint=str(ckpt), checkpoint_sha256=digest)
        if not np.isfinite(values).all() or np.any(values < 0) or float(values.max()) <= 0:
            return ClassifierStatus(False, "classifier unavailable: profile values are invalid", checkpoint=str(ckpt), checkpoint_sha256=digest)
        values = values / float(values.max())

        model_source = repo / "src/xrd_robustness/models/ml4pxrd_resnet1d.py"
        labels_source = repo / "src/xrd_robustness/structure_data.py"
        if not model_source.is_file() or hashlib.sha256(model_source.read_bytes()).hexdigest() != EXPECTED_MODEL_SOURCE_SHA256:
            return ClassifierStatus(False, "classifier unavailable: model source does not match verified implementation", checkpoint=str(ckpt), checkpoint_sha256=digest)
        if not labels_source.is_file() or hashlib.sha256(labels_source.read_bytes()).hexdigest() != EXPECTED_LABEL_SOURCE_SHA256:
            return ClassifierStatus(False, "classifier unavailable: crystal-system label source does not match verified mapping", checkpoint=str(ckpt), checkpoint_sha256=digest)

        import torch
        sys.path.insert(0, str((repo / "src").resolve()))
        from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D, ML4PXRDResNet1DConfig
        from xrd_robustness.structure_data import CRYSTAL_SYSTEMS

        if tuple(CRYSTAL_SYSTEMS) != CLASSES:
            return ClassifierStatus(False, "classifier unavailable: crystal-system class order differs from verified mapping", checkpoint=str(ckpt), checkpoint_sha256=digest)

        payload = torch.load(ckpt, map_location="cpu", weights_only=False)
        if payload.get("config") != EXPECTED_CONFIG:
            return ClassifierStatus(False, "classifier unavailable: checkpoint model configuration differs from verified contract", checkpoint=str(ckpt), checkpoint_sha256=digest)
        config = ML4PXRDResNet1DConfig(**payload["config"])
        model = ML4PXRDResNet1D(config)
        model.load_state_dict(payload["model"], strict=True)
        model.eval()
        with torch.inference_mode():
            probabilities = torch.softmax(model(torch.from_numpy(values.astype(np.float32)[None, :]))["logits"], dim=-1)[0].cpu().numpy()
        return ClassifierStatus(
            True,
            "frozen ResNet18-GN Dynamic JS prior; simulated-domain crystal-system probabilities only",
            checkpoint=str(ckpt), checkpoint_sha256=digest,
            probabilities=tuple(float(value) for value in probabilities),
        )
    except (ImportError, OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
        return ClassifierStatus(False, f"classifier unavailable: optional inference failed ({type(exc).__name__})", checkpoint=str(ckpt))


def soft_system_adjustment(system: str, prior: dict[str, float] | None, weight: float = 0.02) -> float:
    """Return a small optional ranking penalty; never filters a candidate."""
    if not prior:
        return 0.0
    if not 0 <= weight <= 0.05:
        raise ValueError("prior weight must be between zero and 0.05")
    probability = min(1.0, max(0.0, float(prior.get(system, 0.0))))
    return weight * (1.0 - probability)
