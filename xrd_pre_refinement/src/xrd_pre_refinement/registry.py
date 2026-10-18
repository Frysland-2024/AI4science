"""Metadata-first material-family registry and routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RouteResult:
    status: str
    family_id: str | None
    composition_status: str
    review_required: bool
    message: str


@dataclass(frozen=True)
class FamilyRouter:
    families: dict[str, dict[str, Any]]

    def route(self, family_id: str | None, nominal_composition: str | None = None) -> RouteResult:
        """Route only from user-supplied metadata; never infer family from a spectrum."""
        if not family_id or family_id not in self.families:
            return RouteResult(
                "FAMILY_UNKNOWN", family_id, "NOT_CHECKED", True,
                "Provide or verify the material family before candidate ranking.",
            )
        family = self.families[family_id]
        if family.get("status") != "active_demo":
            return RouteResult(
                "FAMILY_UNCONFIGURED", family_id, "NOT_CHECKED", True,
                "This family is a schema scaffold and has no validated candidate library.",
            )
        expected = family.get("nominal_composition", {}).get("formula")
        if nominal_composition is None:
            return RouteResult(
                "ROUTED_WITH_REVIEW", family_id, "NOT_PROVIDED", True,
                "Family was selected from metadata, but nominal composition was not supplied.",
            )
        if expected and nominal_composition != expected:
            return RouteResult(
                "FAMILY_MISMATCH", family_id, "MISMATCH", True,
                f"Supplied composition {nominal_composition!r} does not match the configured demo formula {expected!r}.",
            )
        return RouteResult("ROUTED", family_id, "MATCH", False, "Family selected from supplied metadata.")


def validate_family(family: dict[str, Any]) -> None:
    required = {"family_id", "status", "nominal_composition", "instrument", "candidates"}
    missing = required - family.keys()
    if missing:
        raise ValueError(f"family is missing required fields: {sorted(missing)}")
    if not isinstance(family["family_id"], str) or not family["family_id"].strip():
        raise ValueError("family_id must be a non-empty string")
    if family["status"] not in {"active_demo", "unconfigured"}:
        raise ValueError("status must be active_demo or unconfigured")
    if not isinstance(family["candidates"], list):
        raise ValueError("candidates must be a list")
    if family["status"] == "unconfigured" and family["candidates"]:
        raise ValueError("unconfigured family must not contain candidate structures")
    if family["status"] == "active_demo" and not family["candidates"]:
        raise ValueError("active_demo family must contain at least one candidate")
    instrument = family["instrument"]
    for key in ("wavelength_angstrom", "two_theta_min_deg", "two_theta_max_deg", "step_deg"):
        if key not in instrument:
            raise ValueError(f"instrument is missing {key}")
    if float(instrument["wavelength_angstrom"]) <= 0:
        raise ValueError("wavelength_angstrom must be positive")
    if float(instrument["two_theta_max_deg"]) <= float(instrument["two_theta_min_deg"]):
        raise ValueError("two_theta_max_deg must exceed two_theta_min_deg")
    if float(instrument["step_deg"]) <= 0:
        raise ValueError("step_deg must be positive")
    seen: set[str] = set()
    for candidate in family["candidates"]:
        for key in ("candidate_id", "phase_id", "composition", "space_group", "cif_path", "cif_source", "validity"):
            if key not in candidate:
                raise ValueError(f"candidate is missing {key}")
        if candidate["candidate_id"] in seen:
            raise ValueError(f"duplicate candidate_id: {candidate['candidate_id']}")
        seen.add(candidate["candidate_id"])
        ranges = candidate.get("parameterization", {}).get("allowed_range", {})
        for name, bounds in ranges.items():
            if len(bounds) != 2 or float(bounds[0]) >= float(bounds[1]):
                raise ValueError(f"invalid parameter range for {name}")


def load_registry(index_path: str | Path) -> tuple[FamilyRouter, Path]:
    """Read a registry index and referenced family configs without remote access."""
    index_path = Path(index_path).resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema_version") != "xrd-pre-refinement-registry-v1":
        raise ValueError("unsupported registry schema_version")
    families: dict[str, dict[str, Any]] = {}
    for entry in index.get("families", []):
        config_path = (index_path.parent / entry["config"]).resolve()
        family = json.loads(config_path.read_text(encoding="utf-8"))
        validate_family(family)
        if family["family_id"] != entry["family_id"]:
            raise ValueError(f"registry index/config family_id mismatch: {config_path}")
        families[family["family_id"]] = family
    if len(families) != len(index.get("families", [])):
        raise ValueError("duplicate family_id in registry index")
    return FamilyRouter(families), index_path.parent
