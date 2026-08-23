"""Independent online perturbation sampling for public ResNet experiments."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .physics import PhysicsParameterSampler, PhysicsParameters


INDEPENDENT_GENERATION_ORDER = (
    "preferred_orientation",
    "zero_shift",
    "peak_broadening",
    "background",
    "noise",
    "normalization",
)

INDEPENDENT_OPERATOR_NAMES = (
    "zero_shift",
    "peak_broadening",
    "preferred_orientation",
    "background",
    "noise",
)


@dataclass(frozen=True)
class PerturbationContext:
    """Stable identity of one generated view."""

    material_id: str
    split: str
    epoch: int
    global_step: int
    view_id: int
    profile: str
    mother_pattern_id: str | None = None

    def validate(self) -> None:
        if not self.material_id:
            raise ValueError("material_id cannot be empty")
        if self.split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split: {self.split!r}")
        if self.epoch < 0 or self.global_step < 0 or self.view_id < 0:
            raise ValueError("epoch, global_step, and view_id must be non-negative")
        if not self.profile:
            raise ValueError("profile cannot be empty")


@dataclass(frozen=True)
class MeasurementState:
    """High-level virtual measurement state exposed by one strategy."""

    sample_state: Mapping[str, Any] = field(default_factory=dict)
    instrument_state: Mapping[str, Any] = field(default_factory=dict)
    acquisition_state: Mapping[str, Any] = field(default_factory=dict)
    status: str = "not_applicable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_state": dict(self.sample_state),
            "instrument_state": dict(self.instrument_state),
            "acquisition_state": dict(self.acquisition_state),
            "status": self.status,
        }


@dataclass(frozen=True)
class PerturbationDraw:
    """Sampled parameters before rendering."""

    parameters: PhysicsParameters
    rng_seed: int
    measurement_state: MeasurementState


@dataclass(frozen=True)
class StrategyGeneration:
    """One rendered view plus its complete in-memory render metadata."""

    xrd: Any
    parameters: PhysicsParameters
    rng_seed: int
    measurement_state: MeasurementState
    diagnostics: Mapping[str, Any]
    metadata: Mapping[str, Any]


# A renderer may resolve structure-dependent parameters, such as the selected
# preferred-orientation hkl, before returning the applied parameter record.
StrategyRenderer = Callable[
    [Any, PhysicsParameters, int],
    tuple[Any, PhysicsParameters, Mapping[str, Any]],
]


class PerturbationStrategy(ABC):
    """Unified V8 strategy contract for state sampling, parameters, and rendering."""

    strategy_name: str
    status: str
    formal_use_allowed: bool

    @abstractmethod
    def sample_state(self, context: PerturbationContext) -> MeasurementState:
        """Sample or describe the virtual measurement state for one view."""

    @abstractmethod
    def sample_parameters(
        self,
        state: MeasurementState,
        context: PerturbationContext,
    ) -> PerturbationDraw:
        """Map a state to the five-perturbation parameter set."""

    def apply(
        self,
        clean_pattern: Any,
        draw: PerturbationDraw,
        *,
        renderer: StrategyRenderer,
    ) -> StrategyGeneration:
        """Apply a sampled draw using the repository's established renderer."""
        xrd, applied_parameters, diagnostics = renderer(
            clean_pattern,
            draw.parameters,
            draw.rng_seed,
        )
        return StrategyGeneration(
            xrd=xrd,
            parameters=applied_parameters,
            rng_seed=draw.rng_seed,
            measurement_state=draw.measurement_state,
            diagnostics=dict(diagnostics),
            metadata={},
        )

    def generate(
        self,
        clean_pattern: Any,
        context: PerturbationContext,
        *,
        renderer: StrategyRenderer,
    ) -> StrategyGeneration:
        """Generate one view and attach the V8 reproducibility metadata."""
        context.validate()
        state = self.sample_state(context)
        draw = self.sample_parameters(state, context)
        generated = self.apply(clean_pattern, draw, renderer=renderer)
        metadata = self.metadata_for_parameters(
            context,
            state=generated.measurement_state,
            parameters=generated.parameters,
            rng_seed=generated.rng_seed,
        )
        return StrategyGeneration(
            xrd=generated.xrd,
            parameters=generated.parameters,
            rng_seed=generated.rng_seed,
            measurement_state=generated.measurement_state,
            diagnostics=generated.diagnostics,
            metadata=metadata,
        )

    def metadata_for_parameters(
        self,
        context: PerturbationContext,
        *,
        state: MeasurementState,
        parameters: PhysicsParameters,
        rng_seed: int,
    ) -> dict[str, Any]:
        """Build the same render record for direct generation or manifest replay."""
        context.validate()
        parameters.validate()
        return {
            "schema_version": "v8.0-interface",
            "structure_id": context.material_id,
            "mother_pattern_id": context.mother_pattern_id or context.material_id,
            "split": context.split,
            "epoch": context.epoch,
            "global_step": context.global_step,
            "view_id": context.view_id,
            "profile": context.profile,
            "rng_seed": int(rng_seed),
            "strategy_name": self.strategy_name,
            "strategy_status": self.status,
            "measurement_state": state.to_dict(),
            "perturbation_parameters": parameters.to_dict(),
            "perturbation_activation": {
                name: name in parameters.active_perturbation_names
                for name in (
                    "zero_shift",
                    "peak_broadening",
                    "preferred_orientation",
                    "background",
                    "noise",
                )
            },
            "generation_order": list(self.generation_order),
            "config_hash": self.config_hash,
            "code_version": self.code_version,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    @property
    @abstractmethod
    def generation_order(self) -> tuple[str, ...]:
        """Return the applied operator order, raising if it is not frozen."""

    @property
    @abstractmethod
    def config_hash(self) -> str:
        """Return the source configuration hash recorded with each view."""

    @property
    @abstractmethod
    def code_version(self) -> str:
        """Return the strategy implementation version recorded with each view."""


class IndependentDynamicStrategy(PerturbationStrategy):
    """Factorized operator-level online sampling used by Dynamic ERM and JS."""

    strategy_name = "independent_dynamic"
    status = "public_independent_dynamic"
    formal_use_allowed = True

    def __init__(
        self,
        sampler: PhysicsParameterSampler,
        *,
        config_hash: str = "unbound_config_hash",
        code_version: str = "independent-dynamic-v1",
    ):
        self.sampler = sampler
        self._config_hash = str(config_hash)
        self._code_version = str(code_version)
        if not self._config_hash or not self._code_version:
            raise ValueError("config_hash and code_version cannot be empty")

    def sample_state(self, context: PerturbationContext) -> MeasurementState:
        context.validate()
        return MeasurementState(
            sample_state={},
            instrument_state={},
            acquisition_state={},
            status="independent_baseline_no_shared_latent_state",
        )

    def sample_parameters(
        self,
        state: MeasurementState,
        context: PerturbationContext,
    ) -> PerturbationDraw:
        if state.status != "independent_baseline_no_shared_latent_state":
            raise ValueError("IndependentDynamicStrategy received an incompatible state")
        parameters, seed = self.sampler.sample(
            context.profile,
            epoch=context.epoch,
            global_step=context.global_step,
            material_id=context.material_id,
            view_id=context.view_id,
        )
        return PerturbationDraw(parameters, seed, state)

    @property
    def generation_order(self) -> tuple[str, ...]:
        return INDEPENDENT_GENERATION_ORDER

    @property
    def config_hash(self) -> str:
        return self._config_hash

    @property
    def code_version(self) -> str:
        return self._code_version


def strategy_descriptor(strategy: PerturbationStrategy) -> dict[str, Any]:
    """Return the serializable active sampler contract."""

    return {
        "strategy_name": strategy.strategy_name,
        "status": strategy.status,
        "formal_use_allowed": strategy.formal_use_allowed,
        "config_hash": strategy.config_hash,
        "code_version": strategy.code_version,
        "generation_order": list(strategy.generation_order),
        "sampling_model": "factorized_operator_level",
        "shared_measurement_state": False,
        "operator_names": list(INDEPENDENT_OPERATOR_NAMES),
    }
