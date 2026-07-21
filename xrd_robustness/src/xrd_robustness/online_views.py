"""Online multi-view generation and matched experiment objectives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

import numpy as np

from .physics import PhysicsParameterSampler, PhysicsParameters
from .peak_cache import PeakTable, PeakTableCache
from .perturbation_strategy import (
    IndependentDynamicStrategy,
    PerturbationContext,
    PerturbationStrategy,
)
from .preferred_orientation import resolve_preferred_orientation
from .simulator import (
    SimulationGrid,
    ideal_peak_table,
    simulate_from_peak_table,
    simulate_structure,
)
from .view_manifest import ViewManifestRow


class TrainingMode(str, Enum):
    CLEAN_ERM = "clean_erm"
    OFFLINE_ERM = "offline_erm"
    FIXED_VIEW_ERM = "offline_erm"
    DYNAMIC_ERM = "dynamic_erm"
    DYNAMIC_JS = "dynamic_js"
    DYNAMIC_CONSISTENCY = "dynamic_js"
    DYNAMIC_RESIDUAL = "dynamic_residual"
    PERTURBATION_SUPERVISED_RESIDUAL = "perturbation_supervised_residual"


@dataclass(frozen=True)
class GeneratedView:
    xrd: np.ndarray
    parameters: PhysicsParameters
    rng_seed: int
    diagnostics: dict[str, Any] = field(default_factory=dict)
    strategy_name: str = "independent_dynamic"
    measurement_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewPair:
    first: GeneratedView
    second: GeneratedView


class OnlineViewFactory:
    """Create transient views; validation/test epochs are frozen to zero."""

    def __init__(
        self,
        sampler: PhysicsParameterSampler,
        *,
        grid: SimulationGrid = SimulationGrid(),
        simulator: Callable[..., np.ndarray] = simulate_structure,
        peak_cache: PeakTableCache | None = None,
        quality_gate: bool = False,
        quality_gate_splits: tuple[str, ...] = ("train",),
        quality_gate_config: Mapping[str, Any] | None = None,
        strategy: PerturbationStrategy | None = None,
    ):
        self.sampler = sampler
        self.grid = grid
        self.simulator = simulator
        self.peak_cache = peak_cache
        self.quality_gate = bool(quality_gate)
        self.quality_gate_splits = frozenset(quality_gate_splits)
        self.quality_gate_config = dict(quality_gate_config or {})
        self.strategy = strategy or IndependentDynamicStrategy(sampler)
        self.quality_gate_checked_count = 0
        self.quality_gate_rejected_count = 0

    @staticmethod
    def effective_epoch(split: str, epoch: int) -> int:
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split: {split!r}")
        return int(epoch) if split == "train" else 0

    def _view(
        self,
        structure: Any,
        *,
        material_id: str,
        split: str,
        epoch: int,
        global_step: int,
        view_id: int,
        profile: str,
    ) -> GeneratedView:
        effective_epoch = self.effective_epoch(split, epoch)
        effective_step = int(global_step) if split == "train" else 0
        context = PerturbationContext(
            material_id=material_id,
            split=split,
            epoch=effective_epoch,
            global_step=effective_step,
            view_id=view_id,
            profile=profile,
        )

        def render(source: Any, params: PhysicsParameters, seed: int):
            if self.simulator is simulate_structure and (
                self.peak_cache is not None or params.preferred_orientation_active
            ):
                peaks = (
                    self.peak_cache.get_or_compute(material_id, source, self.grid)
                    if self.peak_cache is not None
                    else ideal_peak_table(source, self.grid)
                )
                resolved = resolve_preferred_orientation(peaks, params)
                xrd, diagnostics = simulate_from_peak_table(
                    peaks.positions,
                    peaks.intensities,
                    resolved,
                    rng_seed=seed,
                    grid=self.grid,
                    return_diagnostics=True,
                    reflection_table=peaks,
                )
                return xrd, resolved, diagnostics
            xrd = self.simulator(source, params, rng_seed=seed, grid=self.grid)
            return xrd, params, {}

        generated = self.strategy.generate(structure, context, renderer=render)
        return GeneratedView(
            xrd=generated.xrd,
            parameters=generated.parameters,
            rng_seed=generated.rng_seed,
            diagnostics=dict(generated.diagnostics),
            strategy_name=self.strategy.strategy_name,
            measurement_state=generated.measurement_state.to_dict(),
            metadata=dict(generated.metadata),
        )

    def make_pair(
        self,
        structure: Any,
        *,
        material_id: str,
        split: str,
        epoch: int,
        global_step: int,
        profile: str,
    ) -> ViewPair:
        return ViewPair(
            first=self._view(
                structure,
                material_id=material_id,
                split=split,
                epoch=epoch,
                global_step=global_step,
                view_id=1,
                profile=profile,
            ),
            second=self._view(
                structure,
                material_id=material_id,
                split=split,
                epoch=epoch,
                global_step=global_step,
                view_id=2,
                profile=profile,
            ),
        )

    def make_fixed_view(
        self,
        structure: Any,
        *,
        material_id: str,
        split: str,
        profile: str,
    ) -> GeneratedView:
        """Return the same per-structure view throughout Fixed-ERM."""
        return self._view(
            structure,
            material_id=material_id,
            split=split,
            epoch=0,
            global_step=0,
            view_id=0,
            profile=profile,
        )

    def _peak_view(
        self,
        peaks: PeakTable,
        *,
        material_id: str,
        split: str,
        epoch: int,
        global_step: int,
        view_id: int,
        profile: str,
    ) -> GeneratedView:
        effective_epoch = self.effective_epoch(split, epoch)
        effective_step = int(global_step) if split == "train" else 0
        context = PerturbationContext(
            material_id=material_id,
            split=split,
            epoch=effective_epoch,
            global_step=effective_step,
            view_id=view_id,
            profile=profile,
        )

        def render(source: PeakTable, params: PhysicsParameters, seed: int):
            resolved = resolve_preferred_orientation(source, params)
            xrd, diagnostics = simulate_from_peak_table(
                source.positions,
                source.intensities,
                resolved,
                rng_seed=seed,
                grid=self.grid,
                return_diagnostics=True,
                reflection_table=source,
            )
            return xrd, resolved, diagnostics

        generated = self.strategy.generate(peaks, context, renderer=render)
        return GeneratedView(
            xrd=generated.xrd,
            parameters=generated.parameters,
            rng_seed=generated.rng_seed,
            diagnostics=dict(generated.diagnostics),
            strategy_name=self.strategy.strategy_name,
            measurement_state=generated.measurement_state.to_dict(),
            metadata=dict(generated.metadata),
        )

    def make_pair_from_peaks(
        self,
        peaks: PeakTable,
        *,
        material_id: str,
        split: str,
        epoch: int,
        global_step: int,
        profile: str,
    ) -> ViewPair:
        """Preferred training path: dynamically render a cached ideal peak table."""
        return ViewPair(
            first=self._peak_view(
                peaks,
                material_id=material_id,
                split=split,
                epoch=epoch,
                global_step=global_step,
                view_id=1,
                profile=profile,
            ),
            second=self._peak_view(
                peaks,
                material_id=material_id,
                split=split,
                epoch=epoch,
                global_step=global_step,
                view_id=2,
                profile=profile,
            ),
        )

    def make_fixed_view_from_peaks(
        self,
        peaks: PeakTable,
        *,
        material_id: str,
        split: str,
        profile: str,
    ) -> GeneratedView:
        return self._peak_view(
            peaks,
            material_id=material_id,
            split=split,
            epoch=0,
            global_step=0,
            view_id=0,
            profile=profile,
        )

    def make_view_from_manifest(
        self,
        peaks: PeakTable,
        row: ViewManifestRow,
    ) -> GeneratedView:
        """Render one manifest row without resampling or persisting its spectrum."""
        parameters = row.physics_parameters()
        parameters = resolve_preferred_orientation(peaks, parameters)
        replay_context = PerturbationContext(
            material_id=row.material_id,
            split=row.split,
            epoch=row.epoch,
            global_step=row.global_step,
            view_id=row.view_id,
            profile="legacy_manifest_profile_not_recorded",
        )
        replay_state = self.strategy.sample_state(replay_context)

        def replay_metadata(applied_parameters: PhysicsParameters) -> dict[str, Any]:
            return self.strategy.metadata_for_parameters(
                replay_context,
                state=replay_state,
                parameters=applied_parameters,
                rng_seed=row.simulation_seed,
            )
        if self.quality_gate and row.split in self.quality_gate_splits:
            from .simulation_quality import inspect_perturbed_view

            base_parameters = PhysicsParameters(
                delta_2theta_deg=0.0,
                fwhm_deg=0.08,
                background_to_peak_ratio=0.0,
                noise_std_ratio=0.0,
                background_type="flat",
                severity_level=0,
            )
            base_profile = simulate_from_peak_table(
                peaks.positions,
                peaks.intensities,
                base_parameters,
                rng_seed=row.simulation_seed,
                grid=self.grid,
                normalize=False,
            )
            profile, diagnostics = simulate_from_peak_table(
                peaks.positions,
                peaks.intensities,
                parameters,
                rng_seed=row.simulation_seed,
                grid=self.grid,
                normalize=False,
                return_diagnostics=True,
                reflection_table=peaks,
            )
            quality = inspect_perturbed_view(
                base_profile,
                profile,
                peak_positions=peaks.positions,
                peak_intensities=peaks.intensities,
                grid=self.grid.values,
                parameters=parameters,
                recall_threshold=float(self.quality_gate_config.get("top20_peak_recall_min", 0.80)),
                retained_threshold=float(
                    self.quality_gate_config.get("retained_integrated_intensity_min", 0.95)
                ),
                clipping_fraction_max=float(
                    self.quality_gate_config.get("clipped_fraction_max", 0.55)
                ),
                simulation_diagnostics=diagnostics,
            )
            self.quality_gate_checked_count += 1
            if not quality["passed"]:
                self.quality_gate_rejected_count += 1
                raise ValueError(
                    "quality gate rejected training view "
                    f"{row.material_id}/{row.epoch}/{row.global_step}/{row.view_id}: "
                    f"{';'.join(quality['reasons'])}"
                )
            maximum = float(np.max(profile)) if profile.size else 0.0
            xrd = profile / maximum if maximum > 0 else np.zeros(profile.shape, dtype=np.float32)
            return GeneratedView(
                xrd=xrd.astype(np.float32),
                parameters=parameters,
                rng_seed=row.simulation_seed,
                diagnostics=diagnostics,
                strategy_name=self.strategy.strategy_name,
                measurement_state=replay_state.to_dict(),
                metadata=replay_metadata(parameters),
            )
        xrd, diagnostics = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            parameters,
            rng_seed=row.simulation_seed,
            grid=self.grid,
            return_diagnostics=True,
            reflection_table=peaks,
        )
        return GeneratedView(
            xrd=xrd,
            parameters=parameters,
            rng_seed=row.simulation_seed,
            diagnostics=diagnostics,
            strategy_name=self.strategy.strategy_name,
            measurement_state=replay_state.to_dict(),
            metadata=replay_metadata(parameters),
        )

    def make_pair_from_manifest(
        self,
        peaks: PeakTable,
        first: ViewManifestRow,
        second: ViewManifestRow,
    ) -> ViewPair:
        if first.material_id != second.material_id or first.view_id == second.view_id:
            raise ValueError("manifest pair must contain two view rows for one material")
        return ViewPair(
            first=self.make_view_from_manifest(peaks, first),
            second=self.make_view_from_manifest(peaks, second),
        )


def _softmax(logits: np.ndarray) -> np.ndarray:
    values = np.asarray(logits, dtype=np.float64)
    shifted = values - np.max(values, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def cross_entropy_from_logits(logits: np.ndarray, target: np.ndarray | int) -> float:
    probabilities = _softmax(logits)
    targets = np.asarray(target, dtype=np.int64).reshape(-1)
    probabilities = np.atleast_2d(probabilities)
    if probabilities.shape[0] != len(targets):
        raise ValueError("target count does not match batch size")
    selected = probabilities[np.arange(len(targets)), targets]
    return float(-np.mean(np.log(np.clip(selected, 1e-12, 1.0))))


def jensen_shannon_from_logits(first: np.ndarray, second: np.ndarray) -> float:
    p = np.atleast_2d(_softmax(first))
    q = np.atleast_2d(_softmax(second))
    if p.shape != q.shape:
        raise ValueError("consistency logits must have identical shapes")
    midpoint = 0.5 * (p + q)
    kl_p = np.sum(p * (np.log(np.clip(p, 1e-12, 1.0)) - np.log(midpoint)), axis=-1)
    kl_q = np.sum(q * (np.log(np.clip(q, 1e-12, 1.0)) - np.log(midpoint)), axis=-1)
    return float(np.mean(0.5 * (kl_p + kl_q)))


def training_objective(
    mode: TrainingMode,
    logits_first: np.ndarray,
    target: np.ndarray | int,
    *,
    logits_second: np.ndarray | None = None,
    consistency_weight: float = 0.0,
) -> dict[str, float]:
    """Compute matched objectives; no unsupported consistency-only branch exists."""
    if mode in {
        TrainingMode.DYNAMIC_RESIDUAL,
        TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL,
    }:
        raise ValueError(f"{mode.value} requires the differentiable torch training objective")
    first_loss = cross_entropy_from_logits(logits_first, target)
    if mode is TrainingMode.FIXED_VIEW_ERM:
        return {"classification": first_loss, "consistency": 0.0, "total": first_loss}
    if logits_second is None:
        raise ValueError(f"{mode.value} requires two supervised views")
    second_loss = cross_entropy_from_logits(logits_second, target)
    classification = 0.5 * (first_loss + second_loss)
    consistency = 0.0
    if mode is TrainingMode.DYNAMIC_CONSISTENCY:
        if consistency_weight < 0:
            raise ValueError("consistency_weight must be non-negative")
        consistency = jensen_shannon_from_logits(logits_first, logits_second)
    total = classification + consistency_weight * consistency
    return {
        "classification": classification,
        "consistency": consistency,
        "total": total,
    }
