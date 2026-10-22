import numpy as np

from pxrd_forward_loss.data import split_indices


def test_parameter_sample_splits_are_disjoint_and_complete():
    splits = split_indices(
        512,
        seed=20261026,
        train_fraction=0.70,
        validation_fraction=0.15,
    )
    assert {key: len(value) for key, value in splits.items()} == {
        "train": 358,
        "validation": 77,
        "test": 77,
    }
    merged = np.concatenate(list(splits.values()))
    assert len(np.unique(merged)) == 512
    assert np.array_equal(np.sort(merged), np.arange(512))
