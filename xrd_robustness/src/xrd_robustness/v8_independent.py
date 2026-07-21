"""Executable V8 Independent Dynamic ERM baseline.

This module binds the factorized five-operator online sampler to the matched
two-view empirical-risk-minimization objective.  It deliberately contains no
shared sample, instrument, or acquisition latent state.
"""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from .online_views import OnlineViewFactory, TrainingMode
from .physics import PhysicsParameterSampler
from .perturbation_strategy import (
    INDEPENDENT_OPERATOR_NAMES,
    IndependentDynamicStrategy,
    strategy_descriptor,
)
from .training import dynamic_erm


class IndependentDynamicERM:
    """V8 algorithm: two independently sampled online views plus ERM."""

    algorithm_name = "independent_dynamic_erm"
    software_status = "software_ready_scientific_ranges_candidate"
    formal_training_allowed = False
    training_mode = TrainingMode.DYNAMIC_ERM
    views_per_structure_per_step = 2

    def __init__(
        self,
        sampler: PhysicsParameterSampler,
        *,
        simulation_config_hash: str,
        marginal_profile_source: str,
        code_version: str = "independent-dynamic-v8-1",
    ) -> None:
        if not simulation_config_hash:
            raise ValueError("simulation_config_hash cannot be empty")
        if not marginal_profile_source:
            raise ValueError("marginal_profile_source cannot be empty")
        self.sampler = sampler
        self.marginal_profile_source = str(marginal_profile_source)
        self.strategy = IndependentDynamicStrategy(
            sampler,
            config_hash=simulation_config_hash,
            code_version=code_version,
        )

    def build_view_factory(self, **factory_kwargs: Any) -> OnlineViewFactory:
        """Create an online factory that is locked to this algorithm's strategy."""
        if "strategy" in factory_kwargs:
            raise ValueError("IndependentDynamicERM owns the perturbation strategy")
        return OnlineViewFactory(
            self.sampler,
            strategy=self.strategy,
            **factory_kwargs,
        )

    @staticmethod
    def objective(
        model: nn.Module,
        x1: torch.Tensor,
        x2: torch.Tensor,
        target: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Average supervised cross-entropy over two independent online views."""
        return dynamic_erm(model, x1, x2, target)

    def descriptor(self) -> dict[str, Any]:
        """Return the auditable algorithm contract stored with each run."""
        return {
            "algorithm_name": self.algorithm_name,
            "software_status": self.software_status,
            "formal_training_allowed": self.formal_training_allowed,
            "training_mode": self.training_mode.value,
            "views_per_structure_per_step": self.views_per_structure_per_step,
            "training_objective": "mean_cross_entropy_over_two_views",
            "sampling_distribution": "product_of_operator_marginals",
            "shared_measurement_state": False,
            "operator_names": list(INDEPENDENT_OPERATOR_NAMES),
            "marginal_profile_source": self.marginal_profile_source,
            "perturbation_strategy": strategy_descriptor(self.strategy),
        }
