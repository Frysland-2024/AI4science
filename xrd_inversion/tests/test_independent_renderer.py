from __future__ import annotations

import hashlib
import inspect
import json
import math
from pathlib import Path

import numpy as np
from pymatgen.core import Lattice, Structure

import xrd_inversion.independent_renderer as independent_module
from xrd_inversion.independent_renderer import (
    IndependentGrid,
    IndependentTetragonalRenderer,
    enumerate_signed_tetragonal_hkls,
    q_to_tetragonal_physical,
    render_truncated_gaussian_profile,
    structure_factor_modulus_squared,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_q_mapping_preserves_requested_log_volume_and_distortion_offsets():
    reference_a, reference_c = 4.0, 6.0
    q = np.asarray([0.7, -0.4, 0.25, 0.0], dtype=np.float64)
    result = q_to_tetragonal_physical(
        q, reference_a=reference_a, reference_c=reference_c
    )
    reference_u = (2.0 * math.log(reference_a) + math.log(reference_c)) / 3.0
    reference_v = math.log(reference_c / reference_a)
    observed_u = (2.0 * math.log(result.a) + math.log(result.c)) / 3.0
    observed_v = math.log(result.c / result.a)
    assert math.isclose(observed_u, reference_u + 0.7 * 0.01)
    assert math.isclose(observed_v, reference_v - 0.4 * 0.01)
    assert math.isclose(result.delta_two_theta_deg, 0.25 * 0.2)
    assert math.isclose(result.fwhm_deg, math.sqrt(0.08 * 0.2))


def test_signed_hkl_enumeration_is_complete_and_respects_bragg_window():
    wavelength = 1.54184
    minimum, maximum = 10.0, 40.0
    hkls = enumerate_signed_tetragonal_hkls(
        a=4.0,
        c=6.0,
        wavelength_angstrom=wavelength,
        two_theta_range=(minimum, maximum),
    )
    reflection_set = {tuple(value) for value in hkls.tolist()}
    assert (1, 0, 0) in reflection_set
    assert (-1, 0, 0) in reflection_set
    assert (0, 0, 0) not in reflection_set
    assert all(tuple(-value for value in hkl) in reflection_set for hkl in reflection_set)
    reciprocal_length = np.sqrt(
        (hkls[:, 0] ** 2 + hkls[:, 1] ** 2) / 4.0**2
        + hkls[:, 2] ** 2 / 6.0**2
    )
    two_theta = np.degrees(
        2.0 * np.arcsin(wavelength * reciprocal_length / 2.0)
    )
    assert float(two_theta.min()) >= minimum - 1.0e-12
    assert float(two_theta.max()) <= maximum + 1.0e-12


def test_direct_structure_factor_reproduces_body_center_extinction():
    structure = Structure(
        Lattice.tetragonal(4.0, 4.0),
        ["Si", "Si"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
    )
    values = structure_factor_modulus_squared(
        structure,
        np.asarray([[1, 0, 0], [2, 0, 0]], dtype=np.int64),
        a=4.0,
        c=4.0,
    )
    assert values[0] < 1.0e-20
    assert values[1] > 100.0


def test_gaussian_integrated_strength_is_stable_across_fwhm():
    axis = np.arange(28.0, 32.0 + 0.0005, 0.001, dtype=np.float64)
    narrow = render_truncated_gaussian_profile(
        [30.0], [7.0], axis, fwhm_deg=0.08, normalize=False
    )
    broad = render_truncated_gaussian_profile(
        [30.0], [7.0], axis, fwhm_deg=0.2, normalize=False
    )
    narrow_area = float(np.trapezoid(narrow, axis))
    broad_area = float(np.trapezoid(broad, axis))
    assert abs(narrow_area / broad_area - 1.0) < 2.0e-6


def test_synthetic_renderer_shifts_every_peak_without_training_renderer_reuse():
    structure = Structure(Lattice.tetragonal(4.0, 6.0), ["Si"], [[0.0, 0.0, 0.0]])
    renderer = IndependentTetragonalRenderer(
        grid=IndependentGrid(
            two_theta_min=10.0,
            two_theta_max=60.0,
            step=0.02,
            wavelength_angstrom=1.54184,
            peak_calculation_padding_deg=1.0,
        )
    )
    nominal = renderer.ideal_peaks(structure, [0.0, 0.0, 0.0, -1.0])
    shifted = renderer.ideal_peaks(structure, [0.0, 0.0, 1.0, -1.0])
    np.testing.assert_allclose(shifted.positions - nominal.positions, 0.2, atol=1.0e-12)
    np.testing.assert_allclose(shifted.intensities, nominal.intensities)
    profile = renderer.render(structure, [0.0, 0.0, 0.0, -1.0])
    assert profile.shape == renderer.grid.axis.shape
    assert np.isfinite(profile).all()
    assert math.isclose(float(profile.max()), 1.0)

    source = inspect.getsource(independent_module)
    assert "from xrd_robustness" not in source
    assert "import xrd_robustness" not in source
    assert "from xrd_inversion.gpu_forward" not in source
    assert "from xrd_inversion.week1_pilot" not in source


def test_frozen_holdout_contract_contains_only_sealed_identity_metadata():
    config_path = (
        REPOSITORY_ROOT
        / "xrd_inversion"
        / "configs"
        / "independent_renderer_holdout.frozen.json"
    )
    manifest_path = (
        REPOSITORY_ROOT
        / "xrd_inversion"
        / "manifests"
        / "independent_renderer_holdout.frozen.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert config["status"] == manifest["status"] == "frozen_unopened"
    assert config["seal"]["profiles_rendered"] is False
    assert config["seal"]["metrics_computed"] is False
    assert config["seal"]["outcomes_opened"] is False
    assert config["seal"]["tuning_use_prohibited"] is True
    assert manifest["seal"]["candidate_structures_loaded"] is False
    assert manifest["seal"]["trial_q_values_materialized"] is False

    candidates = manifest["candidates"]
    assert manifest["candidate_count"] == len(candidates) == 24
    assert [row["rank"] for row in candidates] == list(range(1, 25))
    assert len({row["material_id"] for row in candidates}) == len(candidates)
    assert len({row["parent_structure_id"] for row in candidates}) == len(candidates)
    assert all(row["split"] == "validation" for row in candidates)
    assert all(row["crystal_system"] == "tetragonal" for row in candidates)

    renderer_path = REPOSITORY_ROOT / manifest["renderer_source"]["path"]
    renderer_hash = hashlib.sha256(renderer_path.read_bytes()).hexdigest()
    assert renderer_hash == config["renderer"]["source_sha256"]
    assert renderer_hash == manifest["renderer_source"]["sha256"]
    assert "profiles" not in manifest
    assert "metrics" not in manifest
