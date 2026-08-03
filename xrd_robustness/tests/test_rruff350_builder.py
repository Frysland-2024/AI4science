import importlib.util
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_rruff350.py"
SPEC = importlib.util.spec_from_file_location("build_rruff350", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_canonical_profile_uses_frozen_grid_and_max_normalization():
    x = np.array([9.0, 10.0, 45.0, 80.0, 81.0])
    y = np.array([0.0, 1.0, 4.0, 2.0, 0.0])

    profile = MODULE.canonical_profile(x, y)

    assert profile.shape == (3501,)
    assert np.isclose(profile.max(), 1.0)
    assert np.isclose(profile[0], 0.25)
    assert np.isclose(profile[-1], 0.5)


def test_xrd_confirmation_accepts_single_crystal_wording():
    statuses = (
        "The identification is confirmed by X-ray diffraction",
        "Confirmed by single-crystal X-ray diffraction and chemical analysis",
    )

    assert all(MODULE.is_xrd_confirmed(status) for status in statuses)


def test_classification_prefers_frozen_legacy_label():
    crystal_system, source = MODULE.classify_crystal_system(
        "", "", legacy_class="orthorhombic"
    )

    assert crystal_system == "orthorhombic"
    assert source == "frozen_rruff70_label"


def test_parse_dif_extracts_space_group_and_peaks():
    text = """SPACE GROUP: P 21/c
       20.100 100.0 4.410 1 0 0
       30.200  25.0 2.957 0 1 1
    """

    space_group, positions, intensities = MODULE.parse_dif(text)

    assert space_group == "P 21/c"
    assert np.allclose(positions, [20.1, 30.2])
    assert np.allclose(intensities, [100.0, 25.0])


def test_builder_exposes_balanced_collection_size_options():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'parser.add_argument("--target-per-class", type=int, default=50)' in source
    assert 'parser.add_argument("--dataset-version", type=int, default=1)' in source
    assert 'total_samples = target_per_class * len(CLASS_ORDER)' in source
    assert 'dataset_id = f"rruff-real-pxrd-{total_samples}-v{args.dataset_version}"' in source
