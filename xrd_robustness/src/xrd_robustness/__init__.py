"""Structure-anchored Dynamic ERM/JS utilities for powder XRD."""

from .dynamic_pair_dataset import (
    DynamicPairBatch,
    DynamicPairDataset,
    DynamicPairItem,
    DynamicStructureSample,
    collate_dynamic_pairs,
    stable_pair_seed,
)
from .online_views import OnlineViewFactory, TrainingMode
from .perturbation_strategy import (
    IndependentDynamicStrategy,
    MeasurementState,
    PerturbationContext,
    PerturbationStrategy,
    strategy_descriptor,
)
from .physics import (
    PhysicsParameterSampler,
    PhysicsParameters,
    PhysicsParams,
    build_frozen_perturbation_manifest,
    parameter_registry_rows,
    stable_view_seed,
    validate_formal_simulation_config,
)
from .simulation_interfaces import IdealPeakCalculator, PeakTable, XRDRenderer
from .simulator import (
    GaussianProfileRenderer,
    PerturbationProvenance,
    PymatgenIdealPeakCalculator,
)
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

__all__ = [
    "DynamicPairBatch",
    "DynamicPairDataset",
    "DynamicPairItem",
    "DynamicStructureSample",
    "FrozenEvaluationManifest",
    "GaussianProfileRenderer",
    "IdealPeakCalculator",
    "IndependentDynamicStrategy",
    "MeasurementState",
    "OnlineViewFactory",
    "PERSISTED_STRUCTURE_FIELDS",
    "PeakTable",
    "PerturbationContext",
    "PerturbationProvenance",
    "PerturbationStrategy",
    "PhysicsParameterSampler",
    "PhysicsParameters",
    "PhysicsParams",
    "PymatgenIdealPeakCalculator",
    "SUPPORTED_DATASET_SIZES",
    "TrainingMode",
    "ViewManifestRow",
    "XRDRenderer",
    "assign_structure_splits",
    "build_frozen_perturbation_manifest",
    "build_offline_view_manifest",
    "build_parameter_stream",
    "build_structure_split_manifest",
    "collate_dynamic_pairs",
    "load_manifest",
    "parameter_registry_rows",
    "save_manifest",
    "select_nested_structure_records",
    "stable_pair_seed",
    "stable_view_seed",
    "strategy_descriptor",
    "validate_formal_simulation_config",
    "validate_no_split_leakage",
    "validate_persisted_structure_record",
    "validate_split_manifest",
]
