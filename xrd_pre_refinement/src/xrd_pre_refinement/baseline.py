"""Small, explicitly uncalibrated template-matching baseline."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def _validated_profile(value: Any, *, name: str) -> np.ndarray:
    profile = np.asarray(value, dtype=np.float64)
    if profile.ndim != 1 or profile.size < 2 or not np.isfinite(profile).all():
        raise ValueError(f"{name} must be a finite one-dimensional profile with at least two points")
    return profile


def rank_single_phase_templates(
    observed: Any,
    templates: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Rank same-grid single-phase templates by normalized RMSE.

    This baseline emits no probability. RMSE values depend on preprocessing and
    the instrument configuration and are not a calibrated phase likelihood.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least one")
    target = _validated_profile(observed, name="observed")
    by_id = {item["candidate_id"]: item for item in candidates}
    if not templates:
        raise ValueError("at least one candidate template is required")
    unknown = set(templates) - by_id.keys()
    if unknown:
        raise ValueError(f"templates refer to unknown candidate ids: {sorted(unknown)}")
    ranked: list[dict[str, Any]] = []
    scale = max(float(np.sqrt(np.mean(np.square(target)))), 1e-12)
    for candidate_id, profile_value in templates.items():
        profile = _validated_profile(profile_value, name=f"template {candidate_id}")
        if profile.shape != target.shape:
            raise ValueError(f"template {candidate_id} has a different 2theta grid length")
        rmse = float(np.sqrt(np.mean(np.square(target - profile))))
        candidate = by_id[candidate_id]
        parameters = candidate.get("parameterization", {}).get("reference_values", {})
        ranked.append({
            "candidate_id": candidate_id,
            "phase_id": candidate["phase_id"],
            "composition": candidate["composition"],
            "space_group": candidate["space_group"],
            "reference_cif": candidate["cif_path"],
            "cif_source": candidate["cif_source"],
            "ranking_metric": "normalized_rmse",
            "ranking_score": rmse / scale,
            "single_phase_probability": None,
            "probability_status": "NOT_CALIBRATED",
            "conditional_parameters": {
                "status": "REFERENCE_INITIALIZATION_ONLY",
                "values": parameters,
                "interval": None,
                "interval_status": "NOT_ESTIMATED",
            },
            "forward_check": {
                "normalized_rmse": rmse / scale,
                "fit_status": "DIAGNOSTIC_ONLY",
                "reconstructed_profile_available": True,
                "reconstructed_profile": profile.astype(float).tolist(),
                "residual_observed_minus_reconstructed": (target - profile).astype(float).tolist(),
            },
        })
    ranked.sort(key=lambda row: (row["ranking_score"], row["candidate_id"]))
    for rank, row in enumerate(ranked[:top_k], start=1):
        row["rank"] = rank
    return ranked[:top_k]
