"""Reproducible, configuration-driven online physics parameter sampling."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .measurement_models import BACKGROUND_MODELS, NOISE_MODELS, NOISE_STAGES


PARAMETER_UNITS = {
    "delta_2theta_deg": "degree",
    "fwhm_deg": "degree",
    "background_to_peak_ratio": "ratio_to_normalized_peak_height",
    "noise_std_ratio": "ratio_to_normalized_peak_height",
}

PARAMETER_SOURCE_FIELDS = (
    "literature_source",
    "code_source",
    "physics_basis",
)

# These keys would bind a formal simulation configuration to one laboratory
# instrument or one calibration campaign. Generic physical operators such as a
# zero shift or Caglioti broadening remain allowed; device identity does not.
FORBIDDEN_INSTRUMENT_SPECIFIC_KEYS = frozenset(
    {
        "instrument_model",
        "instrument_model_name",
        "instrument_serial_number",
        "instrument_calibration_file",
        "laboratory_instrument_id",
        "standard_sample_id",
        "standard_sample_measurement",
    }
)

PROFILE_NON_PARAMETER_KEYS = frozenset({"severity_level"})


def stable_view_seed(
    run_seed: int,
    epoch: int,
    global_step: int,
    material_id: str,
    view_id: int,
) -> int:
    """Derive a reproducible RNG seed for one material view."""
    payload = (
        f"{int(run_seed)}:{int(epoch)}:{int(global_step)}:{material_id}:{int(view_id)}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


@dataclass(frozen=True)
class ParameterRange:
    distribution: str
    min_value: float
    max_value: float
    apply_probability: float = 1.0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ParameterRange":
        item = cls(
            distribution=str(value["distribution"]),
            min_value=float(value["min_value"]),
            max_value=float(value["max_value"]),
            apply_probability=float(value.get("apply_probability", 1.0)),
        )
        item.validate()
        return item

    def validate(self) -> None:
        if self.distribution not in {"fixed", "uniform", "log_uniform"}:
            raise ValueError(f"unsupported distribution: {self.distribution}")
        if self.max_value < self.min_value:
            raise ValueError("max_value must be >= min_value")
        if not 0.0 <= self.apply_probability <= 1.0:
            raise ValueError("apply_probability must be in [0, 1]")
        if self.distribution == "fixed" and self.min_value != self.max_value:
            raise ValueError("fixed ranges require equal min_value and max_value")
        if self.distribution == "log_uniform" and self.min_value <= 0.0:
            raise ValueError("log_uniform ranges require positive values")

    def sample_with_activity(
        self,
        rng: np.random.Generator,
        *,
        inactive_value: float = 0.0,
    ) -> tuple[float, bool]:
        """Sample one range and return its explicit activation state."""
        if rng.random() >= self.apply_probability:
            return float(inactive_value), False
        if self.distribution == "fixed":
            return self.min_value, True
        if self.distribution == "log_uniform":
            return float(
                np.exp(rng.uniform(np.log(self.min_value), np.log(self.max_value)))
            ), True
        return float(rng.uniform(self.min_value, self.max_value)), True

    def sample(self, rng: np.random.Generator, *, inactive_value: float = 0.0) -> float:
        """Backward-compatible value-only sampling helper."""
        value, _ = self.sample_with_activity(rng, inactive_value=inactive_value)
        return value


def _scalar_or_range(
    value: Any,
    *,
    default: float,
) -> tuple[float, ParameterRange | None]:
    """Parse a backward-compatible scalar or an auditable sampling range."""
    if value is None:
        return float(default), None
    if isinstance(value, Mapping):
        parameter_range = ParameterRange.from_mapping(value)
        if parameter_range.apply_probability != 1.0:
            raise ValueError("secondary measurement ranges require apply_probability=1")
        return float(default), parameter_range
    scalar = float(value)
    if not np.isfinite(scalar):
        raise ValueError("measurement parameter must be finite")
    return scalar, None


def _sample_scalar_or_range(
    scalar: float,
    parameter_range: ParameterRange | None,
    rng: np.random.Generator,
) -> float:
    if parameter_range is None:
        return float(scalar)
    return parameter_range.sample(rng, inactive_value=float(scalar))


def _registry_scalar_or_range(
    scalar: float,
    parameter_range: ParameterRange | None,
) -> float | str:
    if parameter_range is None:
        return float(scalar)
    return (
        f"{parameter_range.distribution}[{parameter_range.min_value},"
        f"{parameter_range.max_value}]"
    )


@dataclass(frozen=True)
class PhysicsParameters:
    """Measurement parameters; delta_2theta_deg is one global axis offset."""

    delta_2theta_deg: float
    fwhm_deg: float
    background_to_peak_ratio: float
    noise_std_ratio: float
    background_type: str
    severity_level: int
    zero_shift_active: bool = True
    broadening_active: bool = True
    background_active: bool = True
    noise_active: bool = True
    # Defaults define the stable V7 reference renderer. These fields make the
    # measurement model explicit and enable richer V7 representations.
    background_order: int = 2
    background_variation: float = 0.0
    background_anchor_count: int = 33
    background_gp_length_scale: float = 0.20
    background_floor_fraction: float = 0.0
    noise_model: str = "additive_gaussian"
    noise_stage: str = "before_normalization"
    poisson_count_scale: float = 1000.0
    electronic_noise_std_ratio: float = 0.0
    electronic_noise_std_counts: float = 0.0
    # r=1 is the random-powder identity and keeps texture disabled when the
    # preferred-orientation operator is not active.
    preferred_orientation_active: bool = False
    preferred_orientation_model: str = "march_dollase"
    march_parameter: float = 1.0
    preferred_axis_policy: str = "low_index_reflection"
    candidate_low_index_count: int = 16
    orientation_seed: int = 0
    preferred_hkl: tuple[int, int, int] | None = None
    preferred_orientation_apply_probability: float = 0.0

    def validate(self) -> None:
        values = np.asarray(
            (
                self.delta_2theta_deg,
                self.fwhm_deg,
                self.background_to_peak_ratio,
                self.noise_std_ratio,
                self.severity_level,
                self.background_variation,
                self.background_gp_length_scale,
                self.background_floor_fraction,
                self.poisson_count_scale,
                self.electronic_noise_std_ratio,
                self.electronic_noise_std_counts,
                self.march_parameter,
                self.orientation_seed,
                self.preferred_orientation_apply_probability,
            ),
            dtype=np.float64,
        )
        if not np.isfinite(values).all():
            raise ValueError("physics parameters must be finite")
        if self.fwhm_deg <= 0:
            raise ValueError("fwhm_deg must be positive")
        if self.background_to_peak_ratio < 0 or self.noise_std_ratio < 0:
            raise ValueError("background and noise magnitudes must be non-negative")
        if self.background_type not in BACKGROUND_MODELS:
            raise ValueError(f"unsupported background_type: {self.background_type}")
        if self.severity_level not in range(5):
            raise ValueError("severity_level must be in [0, 4]")
        if self.background_order not in range(7):
            raise ValueError("background_order must be in [0, 6]")
        if self.background_anchor_count < 8:
            raise ValueError("background_anchor_count must be at least 8")
        if self.noise_model not in NOISE_MODELS:
            raise ValueError(f"unsupported noise_model: {self.noise_model}")
        if self.noise_stage not in NOISE_STAGES:
            raise ValueError(f"unsupported noise_stage: {self.noise_stage}")
        if self.background_variation < 0:
            raise ValueError("background_variation must be non-negative")
        if self.background_gp_length_scale <= 0:
            raise ValueError("background_gp_length_scale must be positive")
        if not 0.0 <= self.background_floor_fraction <= 1.0:
            raise ValueError("background_floor_fraction must be in [0, 1]")
        if self.poisson_count_scale <= 0:
            raise ValueError("poisson_count_scale must be positive")
        if self.electronic_noise_std_ratio < 0:
            raise ValueError("electronic_noise_std_ratio must be non-negative")
        if self.electronic_noise_std_counts < 0:
            raise ValueError("electronic_noise_std_counts must be non-negative")
        if self.noise_model == "additive_gaussian" and self.electronic_noise_std_counts > 0:
            raise ValueError(
                "electronic_noise_std_counts requires a Poisson-based noise model"
            )
        if self.preferred_orientation_model != "march_dollase":
            raise ValueError("preferred_orientation_model must be 'march_dollase'")
        if self.march_parameter <= 0:
            raise ValueError("march_parameter must be positive")
        if self.preferred_axis_policy != "low_index_reflection":
            raise ValueError("preferred_axis_policy must be 'low_index_reflection'")
        if self.candidate_low_index_count <= 0:
            raise ValueError("candidate_low_index_count must be positive")
        if not 0.0 <= self.preferred_orientation_apply_probability <= 1.0:
            raise ValueError("preferred_orientation_apply_probability must be in [0, 1]")
        if self.preferred_hkl is not None:
            hkl = tuple(int(value) for value in self.preferred_hkl)
            if len(hkl) != 3 or hkl == (0, 0, 0):
                raise ValueError("preferred_hkl must be a non-zero integer triplet")

    @property
    def active_perturbation_count(self) -> int:
        return sum(
            (
                self.zero_shift_active,
                self.broadening_active,
                self.background_active,
                self.noise_active,
                self.preferred_orientation_active,
            )
        )

    @property
    def active_perturbation_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, active in (
                ("zero_shift", self.zero_shift_active),
                ("peak_broadening", self.broadening_active),
                ("background", self.background_active),
                ("noise", self.noise_active),
                ("preferred_orientation", self.preferred_orientation_active),
            )
            if active
        )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        output = asdict(self)
        output["active_perturbation_count"] = self.active_perturbation_count
        return output


# Concise public alias for the established parameter dataclass.
PhysicsParams = PhysicsParameters


@dataclass(frozen=True)
class ParameterProfile:
    delta_2theta_deg: ParameterRange
    fwhm_deg: ParameterRange
    background_to_peak_ratio: ParameterRange
    noise_std_ratio: ParameterRange
    background_type: str
    severity_level: int
    background_order: int = 2
    background_variation: float = 0.0
    background_variation_range: ParameterRange | None = None
    background_anchor_count: int = 33
    background_gp_length_scale: float = 0.20
    background_floor_fraction: float = 0.0
    noise_model: str = "additive_gaussian"
    noise_stage: str = "before_normalization"
    poisson_count_scale: float = 1000.0
    poisson_count_scale_range: ParameterRange | None = None
    electronic_noise_std_ratio: float = 0.0
    electronic_noise_std_counts: float = 0.0
    electronic_noise_std_counts_range: ParameterRange | None = None
    preferred_orientation: ParameterRange = ParameterRange("fixed", 1.0, 1.0, 0.0)
    preferred_orientation_enabled: bool = False
    preferred_orientation_model: str = "march_dollase"
    preferred_axis_policy: str = "low_index_reflection"
    candidate_low_index_count: int = 16

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ParameterProfile":
        required = {
            "delta_2theta_deg",
            "fwhm_deg",
            "background_to_peak_ratio",
            "noise_std_ratio",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"parameter profile is missing ranges: {sorted(missing)}")
        ranges = {name: ParameterRange.from_mapping(value[name]) for name in required}
        raw_orientation = value.get("preferred_orientation")
        if raw_orientation is None:
            orientation_range = ParameterRange("fixed", 1.0, 1.0, 0.0)
            orientation_enabled = False
            orientation_model = "march_dollase"
            orientation_axis_policy = "low_index_reflection"
            orientation_candidate_count = 16
        else:
            if not isinstance(raw_orientation, Mapping):
                raise ValueError("preferred_orientation must be a mapping")
            orientation_enabled = bool(raw_orientation.get("enabled", True))
            orientation_range = ParameterRange.from_mapping(
                {
                    "distribution": raw_orientation.get(
                        "distribution", raw_orientation.get("sampling_distribution", "uniform")
                    ),
                    "min_value": raw_orientation.get("min_value", 1.0),
                    "max_value": raw_orientation.get("max_value", 1.0),
                    "apply_probability": (
                        raw_orientation.get("apply_probability", 1.0)
                        if orientation_enabled
                        else 0.0
                    ),
                }
            )
            orientation_model = str(raw_orientation.get("model", "march_dollase"))
            orientation_axis_policy = str(
                raw_orientation.get("preferred_axis_policy", "low_index_reflection")
            )
            orientation_candidate_count = int(
                raw_orientation.get("candidate_low_index_count", 16)
            )
        background_variation, background_variation_range = _scalar_or_range(
            value.get("background_variation"),
            default=0.0,
        )
        poisson_count_scale, poisson_count_scale_range = _scalar_or_range(
            value.get("poisson_count_scale"),
            default=1000.0,
        )
        electronic_noise_std_counts, electronic_noise_std_counts_range = _scalar_or_range(
            value.get("electronic_noise_std_counts"),
            default=0.0,
        )
        profile = cls(
            **ranges,
            background_type=str(value["background_type"]),
            severity_level=int(value["severity_level"]),
            background_order=int(value.get("background_order", 2)),
            background_variation=background_variation,
            background_variation_range=background_variation_range,
            background_anchor_count=int(value.get("background_anchor_count", 33)),
            background_gp_length_scale=float(value.get("background_gp_length_scale", 0.20)),
            background_floor_fraction=float(value.get("background_floor_fraction", 0.0)),
            noise_model=str(value.get("noise_model", "additive_gaussian")),
            noise_stage=str(value.get("noise_stage", "before_normalization")),
            poisson_count_scale=poisson_count_scale,
            poisson_count_scale_range=poisson_count_scale_range,
            electronic_noise_std_ratio=float(value.get("electronic_noise_std_ratio", 0.0)),
            electronic_noise_std_counts=electronic_noise_std_counts,
            electronic_noise_std_counts_range=electronic_noise_std_counts_range,
            preferred_orientation=orientation_range,
            preferred_orientation_enabled=orientation_enabled,
            preferred_orientation_model=orientation_model,
            preferred_axis_policy=orientation_axis_policy,
            candidate_low_index_count=orientation_candidate_count,
        )
        if profile.background_type not in BACKGROUND_MODELS:
            raise ValueError(f"background_type must be one of {sorted(BACKGROUND_MODELS)}")
        if profile.severity_level not in range(5):
            raise ValueError("severity_level must be in [0, 4]")
        profile.validate()
        return profile

    def validate(self) -> None:
        background_variation = (
            self.background_variation_range.min_value
            if self.background_variation_range is not None
            else self.background_variation
        )
        poisson_count_scale = (
            self.poisson_count_scale_range.min_value
            if self.poisson_count_scale_range is not None
            else self.poisson_count_scale
        )
        electronic_noise_std_counts = (
            self.electronic_noise_std_counts_range.min_value
            if self.electronic_noise_std_counts_range is not None
            else self.electronic_noise_std_counts
        )
        PhysicsParameters(
            delta_2theta_deg=0.0,
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type=self.background_type,
            severity_level=self.severity_level,
            background_order=self.background_order,
            background_variation=background_variation,
            background_anchor_count=self.background_anchor_count,
            background_gp_length_scale=self.background_gp_length_scale,
            background_floor_fraction=self.background_floor_fraction,
            noise_model=self.noise_model,
            noise_stage=self.noise_stage,
            poisson_count_scale=poisson_count_scale,
            electronic_noise_std_ratio=self.electronic_noise_std_ratio,
            electronic_noise_std_counts=electronic_noise_std_counts,
            preferred_orientation_model=self.preferred_orientation_model,
            preferred_axis_policy=self.preferred_axis_policy,
            candidate_low_index_count=self.candidate_low_index_count,
        ).validate()
        if (
            self.poisson_count_scale_range is not None
            and self.poisson_count_scale_range.min_value <= 0.0
        ):
            raise ValueError("poisson_count_scale range must be positive")

    def sample(self, seed: int) -> PhysicsParameters:
        rng = np.random.default_rng(seed)
        delta, delta_active = self.delta_2theta_deg.sample_with_activity(rng)
        fwhm, broadening_active = self.fwhm_deg.sample_with_activity(
            rng,
            inactive_value=0.08,
        )
        background, background_active = self.background_to_peak_ratio.sample_with_activity(rng)
        noise, noise_active = self.noise_std_ratio.sample_with_activity(rng)
        background_variation = _sample_scalar_or_range(
            self.background_variation,
            self.background_variation_range,
            rng,
        )
        poisson_count_scale = _sample_scalar_or_range(
            self.poisson_count_scale,
            self.poisson_count_scale_range,
            rng,
        )
        electronic_noise_std_counts = _sample_scalar_or_range(
            self.electronic_noise_std_counts,
            self.electronic_noise_std_counts_range,
            rng,
        )
        march_parameter, orientation_active = self.preferred_orientation.sample_with_activity(
            rng, inactive_value=1.0
        )
        params = PhysicsParameters(
            delta_2theta_deg=delta,
            fwhm_deg=fwhm,
            background_to_peak_ratio=background,
            noise_std_ratio=noise,
            background_type=self.background_type,
            severity_level=self.severity_level,
            zero_shift_active=delta_active,
            broadening_active=broadening_active,
            background_active=background_active,
            noise_active=noise_active,
            background_order=self.background_order,
            background_variation=background_variation,
            background_anchor_count=self.background_anchor_count,
            background_gp_length_scale=self.background_gp_length_scale,
            background_floor_fraction=self.background_floor_fraction,
            noise_model=self.noise_model,
            noise_stage=self.noise_stage,
            poisson_count_scale=poisson_count_scale,
            electronic_noise_std_ratio=self.electronic_noise_std_ratio,
            electronic_noise_std_counts=electronic_noise_std_counts,
            preferred_orientation_active=(
                self.preferred_orientation_enabled and orientation_active
            ),
            preferred_orientation_model=self.preferred_orientation_model,
            march_parameter=march_parameter,
            preferred_axis_policy=self.preferred_axis_policy,
            candidate_low_index_count=self.candidate_low_index_count,
            orientation_seed=int(seed),
            preferred_orientation_apply_probability=self.preferred_orientation.apply_probability,
        )
        params.validate()
        return params


class PhysicsParameterSampler:
    """Sample named train/in-range/OOD profiles without implicit defaults."""

    def __init__(
        self,
        profiles: Mapping[str, ParameterProfile],
        *,
        run_seed: int,
    ):
        self.profiles = dict(profiles)
        self.run_seed = int(run_seed)

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "PhysicsParameterSampler":
        raw_profiles = config.get("profiles")
        if not isinstance(raw_profiles, Mapping) or not raw_profiles:
            raise ValueError("config must define at least one explicit parameter profile")
        profiles = {
            str(name): ParameterProfile.from_mapping(value)
            for name, value in raw_profiles.items()
            if value is not None
        }
        if not profiles:
            raise ValueError("all parameter profiles are unresolved")
        return cls(
            profiles,
            run_seed=int(config["run_seed"]),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "PhysicsParameterSampler":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_mapping(json.load(handle))

    def sample(
        self,
        profile: str,
        *,
        epoch: int,
        global_step: int,
        material_id: str,
        view_id: int,
    ) -> tuple[PhysicsParameters, int]:
        if profile not in self.profiles:
            raise ValueError(
                f"profile {profile!r} is not configured; freeze evidence-backed ranges first"
            )
        seed = stable_view_seed(
            self.run_seed,
            epoch,
            global_step,
            material_id,
            view_id,
        )
        return self.profiles[profile].sample(seed), seed


def validate_formal_simulation_config(
    config: Mapping[str, Any],
    *,
    train_profile: str,
    in_range_profile: str,
    ood_profiles: list[str],
) -> None:
    """Reject non-traceable or instrument-bound configs before formal training."""
    purpose = str(config.get("purpose", "")).lower()
    if "smoke" in purpose or "test only" in purpose or "software" in purpose:
        raise ValueError("formal training requires a non-smoke simulation config")
    raw_strategy = config.get("perturbation_strategy")
    if raw_strategy is not None:
        if not isinstance(raw_strategy, Mapping):
            raise ValueError("perturbation_strategy must be a mapping")
        strategy_name = str(raw_strategy.get("name", ""))
        if strategy_name != "independent_dynamic":
            raise ValueError(f"unsupported perturbation strategy: {strategy_name!r}")
    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("formal simulation config must define named profiles")
    required = [train_profile, in_range_profile, *ood_profiles]
    missing = sorted(set(required).difference(raw_profiles))
    if missing:
        raise ValueError(f"formal simulation config is missing profiles: {missing}")
    if not ood_profiles:
        raise ValueError("formal training requires at least one OOD profile")
    for name in required:
        if raw_profiles[name] is None:
            raise ValueError(f"formal profile {name!r} is unresolved")
        ParameterProfile.from_mapping(raw_profiles[name])
    validate_parameter_evidence(config)
    validate_instrument_agnostic_config(config)


def _has_source_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(isinstance(item, str) and item.strip() for item in value)
    return False


def _source_value_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item).strip() for item in value)
    return ""


def validate_parameter_evidence(config: Mapping[str, Any]) -> None:
    """Require source metadata for every configured perturbation parameter."""
    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("config must define parameter profiles before evidence can be checked")
    parameter_names: set[str] = set()
    for profile_name, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, Mapping):
            raise ValueError(f"profile {profile_name!r} is unresolved")
        parameter_names.update(
            str(name) for name in raw_profile if str(name) not in PROFILE_NON_PARAMETER_KEYS
        )
    raw_evidence = config.get("parameter_evidence")
    if not isinstance(raw_evidence, Mapping):
        raise ValueError("formal simulation config must define parameter_evidence")
    missing = sorted(parameter_names.difference(str(name) for name in raw_evidence))
    if missing:
        raise ValueError(f"perturbation parameters are missing source metadata: {missing}")
    invalid: list[str] = []
    for parameter_name in sorted(parameter_names):
        entry = raw_evidence.get(parameter_name)
        if not isinstance(entry, Mapping) or not any(
            _has_source_value(entry.get(field)) for field in PARAMETER_SOURCE_FIELDS
        ):
            invalid.append(parameter_name)
    if invalid:
        fields = ", ".join(PARAMETER_SOURCE_FIELDS)
        raise ValueError(
            "perturbation source metadata must provide at least one of "
            f"{fields}: {invalid}"
        )


def validate_instrument_agnostic_config(config: Mapping[str, Any]) -> None:
    """Reject fields that identify one instrument or one local calibration."""
    hits: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                key = str(raw_key)
                child_path = f"{path}.{key}"
                if key.lower() in FORBIDDEN_INSTRUMENT_SPECIFIC_KEYS:
                    hits.append(child_path)
                visit(child, child_path)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(config, "config")
    if hits:
        raise ValueError(
            "formal simulation config must remain instrument-agnostic; "
            f"remove instrument-specific fields: {sorted(hits)}"
        )


def parameter_registry_rows(
    config: Mapping[str, Any],
    *,
    source_config: str,
    config_sha256: str,
) -> list[dict[str, Any]]:
    """Flatten the active parameter profiles into an auditable table."""
    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("config must define parameter profiles")
    status = str(config.get("status", "unversioned_candidate"))
    raw_evidence = config.get("parameter_evidence", {})
    rows: list[dict[str, Any]] = []
    for profile_name, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, Mapping):
            raise ValueError(f"profile {profile_name!r} is unresolved")
        profile = ParameterProfile.from_mapping(raw_profile)
        if profile_name == "level0":
            role = "software_reference"
        elif profile_name == "train":
            role = "training"
        elif profile_name == "in_range":
            role = "evaluation_in_range"
        else:
            role = "evaluation_ood"
        for parameter_name, unit in PARAMETER_UNITS.items():
            parameter_range = getattr(profile, parameter_name)
            evidence = raw_evidence.get(parameter_name, {})
            if not isinstance(evidence, Mapping):
                evidence = {}
            rows.append(
                {
                    "profile": str(profile_name),
                    "role": role,
                    "severity_level": profile.severity_level,
                    "background_type": profile.background_type,
                    "background_order": profile.background_order,
                    "background_variation": _registry_scalar_or_range(
                        profile.background_variation,
                        profile.background_variation_range,
                    ),
                    "background_anchor_count": profile.background_anchor_count,
                    "background_gp_length_scale": profile.background_gp_length_scale,
                    "background_floor_fraction": profile.background_floor_fraction,
                    "noise_model": profile.noise_model,
                    "noise_stage": profile.noise_stage,
                    "poisson_count_scale": _registry_scalar_or_range(
                        profile.poisson_count_scale,
                        profile.poisson_count_scale_range,
                    ),
                    "electronic_noise_std_ratio": profile.electronic_noise_std_ratio,
                    "electronic_noise_std_counts": _registry_scalar_or_range(
                        profile.electronic_noise_std_counts,
                        profile.electronic_noise_std_counts_range,
                    ),
                    "parameter": parameter_name,
                    "unit": unit,
                    "distribution": parameter_range.distribution,
                    "min_value": parameter_range.min_value,
                    "max_value": parameter_range.max_value,
                    "apply_probability": parameter_range.apply_probability,
                    "literature_source": _source_value_to_text(
                        evidence.get("literature_source")
                    ),
                    "code_source": _source_value_to_text(evidence.get("code_source")),
                    "physics_basis": _source_value_to_text(evidence.get("physics_basis")),
                    "status": status,
                    "run_seed": int(config["run_seed"]),
                    "source_config": source_config,
                    "config_sha256": config_sha256,
                }
            )
    return rows


def build_frozen_perturbation_manifest(
    material_ids: list[str],
    sampler: PhysicsParameterSampler,
    *,
    profile: str,
    views_per_material: int = 2,
) -> list[dict[str, Any]]:
    """Freeze validation/test parameters without persisting generated spectra."""
    if views_per_material <= 0:
        raise ValueError("views_per_material must be positive")
    manifest: list[dict[str, Any]] = []
    for material_id in sorted(material_ids):
        for view_id in range(1, views_per_material + 1):
            params, seed = sampler.sample(
                profile,
                epoch=0,
                global_step=0,
                material_id=material_id,
                view_id=view_id,
            )
            parameter_values = params.to_dict()
            active = list(params.active_perturbation_names)
            manifest.append(
                {
                    "material_id": material_id,
                    "view_id": view_id,
                    "simulation_seed": seed,
                    "perturbation_type": active,
                    "perturbation_parameters": parameter_values,
                    "severity_level": params.severity_level,
                }
            )
    return manifest
