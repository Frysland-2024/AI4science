"""Structure-anchored online XRD robustness utilities."""

from .online_views import OnlineViewFactory, TrainingMode, training_objective
from .dynamic_pair_dataset import (
    DynamicPairBatch,
    DynamicPairDataset,
    DynamicPairItem,
    DynamicStructureSample,
    collate_dynamic_pairs,
    stable_pair_seed,
)
from .physics import (
    PhysicsParameterSampler,
    PhysicsParams,
    PhysicsParameters,
    build_frozen_perturbation_manifest,
    parameter_registry_rows,
    stable_view_seed,
    validate_formal_simulation_config,
)
from .perturbation_strategy import (
    IndependentDynamicStrategy,
    MeasurementState,
    PerturbationContext,
    PerturbationStrategy,
    StructuredDynamicStrategy,
    StructuredStrategyNotFrozenError,
    strategy_descriptor,
)
from .v8_independent import IndependentDynamicERM
from .splitting import build_structure_split_manifest, validate_split_manifest
from .structure_data import (
    PERSISTED_STRUCTURE_FIELDS,
    SUPPORTED_DATASET_SIZES,
    assign_structure_splits,
    select_nested_structure_records,
    validate_no_split_leakage,
    validate_persisted_structure_record,
)
from .view_manifest import (
    FrozenEvaluationManifest,
    ViewManifestRow,
    build_offline_view_manifest,
    build_parameter_stream,
    load_manifest,
    save_manifest,
)
from .simulation_interfaces import IdealPeakCalculator, PeakTable, XRDRenderer
from .simulator import (
    GaussianProfileRenderer,
    PerturbationProvenance,
    PymatgenIdealPeakCalculator,
)

__all__ = [
    "OnlineViewFactory",
    "DynamicPairBatch",
    "DynamicPairDataset",
    "DynamicPairItem",
    "DynamicStructureSample",
    "FrozenEvaluationManifest",
    "GaussianProfileRenderer",
    "IdealPeakCalculator",
    "PeakTable",
    "PERSISTED_STRUCTURE_FIELDS",
    "SUPPORTED_DATASET_SIZES",
    "PhysicsParameterSampler",
    "PhysicsParams",
    "PhysicsParameters",
    "IndependentDynamicStrategy",
    "IndependentDynamicERM",
    "MeasurementState",
    "PerturbationContext",
    "PerturbationStrategy",
    "PerturbationProvenance",
    "PymatgenIdealPeakCalculator",
    "TrainingMode",
    "StructuredDynamicStrategy",
    "StructuredStrategyNotFrozenError",
    "XRDRenderer",
    "assign_structure_splits",
    "build_frozen_perturbation_manifest",
    "parameter_registry_rows",
    "build_offline_view_manifest",
    "build_structure_split_manifest",
    "stable_view_seed",
    "select_nested_structure_records",
    "validate_formal_simulation_config",
    "training_objective",
    "validate_no_split_leakage",
    "validate_persisted_structure_record",
    "validate_split_manifest",
    "ViewManifestRow",
    "build_parameter_stream",
    "collate_dynamic_pairs",
    "load_manifest",
    "save_manifest",
    "stable_pair_seed",
    "strategy_descriptor",
]
