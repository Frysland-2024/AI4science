from __future__ import annotations

from functools import partial

import numpy as np

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.physics import PhysicsParameterSampler, PhysicsParameters
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.training.runner import build_online_view_factory
from xrd_robustness.simulator import (
    SimulationGrid,
    render_gaussian_peaks,
    simulate_from_peak_table,
)
from xrd_robustness.simulator_v11 import (
    calculate_tch_width_components,
    make_peak_table_simulator,
    render_tch_pseudo_voigt_peaks,
    sample_line_profile_parameters,
    simulate_from_peak_table_v11,
)


LINE_PROFILE = {
    "kind": "tch_pseudo_voigt_v1",
    "wavelength_angstrom": 1.54184,
    "scherrer_shape_factor": 0.9,
    "caglioti_u_deg2": 0.0012,
    "caglioti_v_deg2": 0.0004,
    "crystallite_size_nm": {"distribution": "fixed", "min_value": 100.0, "max_value": 100.0},
    "microstrain": {"distribution": "fixed", "min_value": 0.0001, "max_value": 0.0001},
    "use_scherrer": True,
    "use_microstrain": True,
    "truncate_fwhm": 50.0,
}


def _quiet_parameters() -> PhysicsParameters:
    return PhysicsParameters(
        delta_2theta_deg=0.0,
        fwhm_deg=0.08,
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=0,
        zero_shift_active=False,
        broadening_active=True,
        background_active=False,
        noise_active=False,
    )


def _peak_table() -> PeakTable:
    return PeakTable(
        positions=np.asarray([24.31, 35.07, 51.82], dtype=np.float64),
        intensities=np.asarray([1.0, 0.62, 0.31], dtype=np.float64),
        hkls=np.asarray([[1, 0, 0], [1, 1, 0], [2, 0, 0]], dtype=np.int64),
        multiplicities=np.asarray([6, 12, 6], dtype=np.int64),
        reciprocal_vectors=np.asarray(
            [[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [2.0, 0.0, 0.0]],
            dtype=np.float64,
        ),
        reflection_peak_indices=np.arange(3, dtype=np.int64),
    )


def _sampler() -> PhysicsParameterSampler:
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 907,
            "profiles": {
                "train": {
                    "severity_level": 1,
                    "background_type": "polynomial",
                    "background_order": 2,
                    "background_variation": 0.0,
                    "background_floor_fraction": 0.0,
                    "noise_model": "poisson_gaussian",
                    "noise_stage": "before_normalization",
                    "poisson_count_scale": 40000.0,
                    "delta_2theta_deg": {
                        "distribution": "uniform",
                        "min_value": -0.15,
                        "max_value": 0.15,
                        "apply_probability": 1.0,
                    },
                    "fwhm_deg": {
                        "distribution": "uniform",
                        "min_value": 0.08,
                        "max_value": 0.12,
                        "apply_probability": 1.0,
                    },
                    "background_to_peak_ratio": {
                        "distribution": "fixed",
                        "min_value": 0.0,
                        "max_value": 0.0,
                        "apply_probability": 0.0,
                    },
                    "noise_std_ratio": {
                        "distribution": "fixed",
                        "min_value": 0.0,
                        "max_value": 0.0,
                        "apply_probability": 0.0,
                    },
                }
            },
        }
    )


def test_tch_profile_conserves_integrated_peak_area_and_peak_position() -> None:
    grid = SimulationGrid().values
    center = 37.437
    area = 11.25
    profile = render_tch_pseudo_voigt_peaks(
        [center],
        [area],
        grid,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=100.0,
        microstrain=0.0001,
        normalize=False,
    )
    step = float(grid[1] - grid[0])
    assert np.isfinite(profile).all()
    assert float(profile.min()) >= 0.0
    np.testing.assert_allclose(
        np.sum(profile, dtype=np.float64) * step,
        area,
        rtol=2e-7,
        atol=2e-7,
    )
    assert abs(float(grid[int(np.argmax(profile))]) - center) <= step / 2.0


def test_caglioti_size_and_microstrain_width_trends() -> None:
    narrow_angle = calculate_tch_width_components(
        20.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=1.0e8,
        microstrain=0.0,
    )
    wide_angle = calculate_tch_width_components(
        70.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=1.0e8,
        microstrain=0.0,
    )
    assert wide_angle["instrument_gaussian_fwhm_deg"] > narrow_angle[
        "instrument_gaussian_fwhm_deg"
    ]

    small_crystallites = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=50.0,
        microstrain=0.0001,
    )
    large_crystallites = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=400.0,
        microstrain=0.0001,
    )
    assert small_crystallites["scherrer_fwhm_deg"] > large_crystallites[
        "scherrer_fwhm_deg"
    ]
    assert small_crystallites["total_fwhm_deg"] > large_crystallites[
        "total_fwhm_deg"
    ]

    low_strain = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=100.0,
        microstrain=0.0,
    )
    high_strain = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=LINE_PROFILE,
        crystallite_size_nm=100.0,
        microstrain=0.0005,
    )
    assert high_strain["microstrain_fwhm_deg"] > low_strain[
        "microstrain_fwhm_deg"
    ]
    assert high_strain["total_fwhm_deg"] > low_strain["total_fwhm_deg"]


def test_seeded_line_profile_parameters_and_spectra_replay() -> None:
    varying = {
        **LINE_PROFILE,
        "crystallite_size_nm": {
            "distribution": "uniform",
            "min_value": 50.0,
            "max_value": 200.0,
        },
        "microstrain": {
            "distribution": "uniform",
            "min_value": 0.00001,
            "max_value": 0.0002,
        },
    }
    a = sample_line_profile_parameters(varying, rng_seed=1234)
    assert a == sample_line_profile_parameters(varying, rng_seed=1234)
    assert a != sample_line_profile_parameters(varying, rng_seed=4321)
    args = (_peak_table().positions, _peak_table().intensities, _quiet_parameters())
    spectrum_a = simulate_from_peak_table_v11(
        *args,
        rng_seed=1234,
        line_profile=varying,
    )
    spectrum_b = simulate_from_peak_table_v11(
        *args,
        rng_seed=1234,
        line_profile=varying,
    )
    assert np.array_equal(spectrum_a, spectrum_b)


def test_v11_peak_reference_scale_preserves_unit_peak_for_area_normalized_renderer() -> None:
    peaks = _peak_table()
    _, diagnostics = simulate_from_peak_table_v11(
        peaks.positions,
        peaks.intensities,
        _quiet_parameters(),
        rng_seed=73,
        normalize=False,
        return_diagnostics=True,
        reflection_table=peaks,
    )
    np.testing.assert_allclose(diagnostics["preclip_max"], 1.0, rtol=1e-7, atol=1e-7)


def test_legacy_gaussian_reference_scale_remains_default_and_validated() -> None:
    peaks = _peak_table()
    params = _quiet_parameters()
    implicit = simulate_from_peak_table(
        peaks.positions, peaks.intensities, params, rng_seed=18, normalize=False
    )
    explicit = simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        params,
        rng_seed=18,
        normalize=False,
        reference_scale_mode="legacy_gaussian",
    )
    assert np.array_equal(implicit, explicit)
    try:
        simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            params,
            rng_seed=18,
            reference_scale_mode="unknown",
        )
    except ValueError as exc:
        assert "reference_scale_mode" in str(exc)
    else:
        raise AssertionError("unsupported reference scale mode must be rejected")


def test_online_factory_generates_same_parent_dynamic_v11_views() -> None:
    config = {
        **LINE_PROFILE,
        "crystallite_size_nm": {
            "distribution": "uniform",
            "min_value": 50.0,
            "max_value": 200.0,
        },
    }
    factory = OnlineViewFactory(
        _sampler(),
        peak_table_simulator=partial(
            simulate_from_peak_table_v11,
            line_profile=config,
        ),
    )
    kwargs = {
        "material_id": "mp-test-cubic",
        "split": "train",
        "epoch": 3,
        "global_step": 17,
        "profile": "train",
    }
    pair = factory.make_pair_from_peaks(_peak_table(), **kwargs)
    replay = factory.make_pair_from_peaks(_peak_table(), **kwargs)
    assert pair.first.metadata["structure_id"] == "mp-test-cubic"
    assert pair.second.metadata["structure_id"] == "mp-test-cubic"
    assert pair.first.metadata["view_id"] == 1
    assert pair.second.metadata["view_id"] == 2
    assert pair.first.rng_seed != pair.second.rng_seed
    assert np.array_equal(pair.first.xrd, replay.first.xrd)
    assert np.array_equal(pair.second.xrd, replay.second.xrd)
    assert not np.array_equal(pair.first.xrd, pair.second.xrd)
    assert "line_profile" in pair.first.diagnostics
    assert "line_profile" in pair.second.diagnostics
    assert pair.first.xrd.shape == (3501,)
    assert np.isfinite(pair.first.xrd).all() and np.isfinite(pair.second.xrd).all()
    assert float(pair.first.xrd.min()) >= 0.0 and float(pair.second.xrd.min()) >= 0.0


def test_v9_default_renderer_is_unchanged_and_selectable() -> None:
    assert make_peak_table_simulator("v9_gaussian") is simulate_from_peak_table
    peaks = _peak_table()
    params = _quiet_parameters()
    old = simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        params,
        rng_seed=22,
        reflection_table=peaks,
    )
    explicit_old = simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        params,
        rng_seed=22,
        reflection_table=peaks,
        peak_renderer=render_gaussian_peaks,
    )
    assert np.array_equal(old, explicit_old)


def test_dynamic_training_factory_selects_v11_from_simulation_config() -> None:
    factory, version, resolved_profile = build_online_view_factory(
        _sampler(),
        {
            "simulator_version": "v11_tch_pseudo_voigt",
            "line_profile": LINE_PROFILE,
        },
    )
    assert version == "v11_tch_pseudo_voigt"
    assert resolved_profile["kind"] == "tch_pseudo_voigt_v1"
    pair = factory.make_pair_from_peaks(
        _peak_table(),
        material_id="runner-config-v11",
        split="train",
        epoch=0,
        global_step=0,
        profile="train",
    )
    assert pair.first.diagnostics["line_profile"]["simulator_version"] == version
    assert pair.second.diagnostics["line_profile"]["simulator_version"] == version
