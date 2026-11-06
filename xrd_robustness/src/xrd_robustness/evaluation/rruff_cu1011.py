"""Read the frozen Cu1011 scoring inputs without model inference."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path

import numpy as np

from ..structure_data import CRYSTAL_SYSTEMS

MANIFEST_SHA256 = "75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37"
INPUTS_SHA256 = "19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179"
SHAPE = (1011, 3501)
CLASS_COUNTS = (97, 334, 211, 45, 129, 76, 119)


def _verified_bytes(path: Path, expected_sha256: str) -> bytes:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"frozen SHA-256 mismatch: {path.name}")
    return data


def load_frozen_inputs(
    manifest_path: Path, inputs_path: Path
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    """Return the ordered primary IDs, input spectra and model class indices."""
    manifest = _verified_bytes(manifest_path, MANIFEST_SHA256)
    inputs = _verified_bytes(inputs_path, INPUTS_SHA256)
    rows = list(csv.DictReader(io.StringIO(manifest.decode("utf-8"), newline="")))
    ids = tuple(row["sample_variant_id"] for row in rows)
    systems = tuple(row["final_candidate_system"] for row in rows)
    indices = np.array([int(row["v11_label_index"]) for row in rows], dtype=np.int64)
    if len(ids) != SHAPE[0] or "" in ids or len(set(ids)) != SHAPE[0]:
        raise ValueError("primary manifest must contain 1011 unique nonempty sample IDs")
    if Counter(systems) != dict(zip(CRYSTAL_SYSTEMS, CLASS_COUNTS, strict=True)):
        raise ValueError("primary class counts differ from the frozen benchmark")
    if tuple(indices) != tuple(CRYSTAL_SYSTEMS.index(system) for system in systems):
        raise ValueError("manifest indices differ from the model class order")

    with np.load(io.BytesIO(inputs), allow_pickle=False) as bundle:
        if not np.array_equal(bundle["sample_ids"], ids):
            raise ValueError("input sample IDs differ from the ordered primary manifest")
        if not np.array_equal(bundle["crystal_system_labels"], systems):
            raise ValueError("input labels differ from the ordered primary manifest")
        spectra = bundle["xrd_input"]
        observed = bundle["observation_mask"]
    if spectra.shape != SHAPE or spectra.dtype != np.float32:
        raise ValueError("expected 1011 by 3501 float32 input spectra")
    if observed.shape != SHAPE or observed.dtype != np.bool_ or not observed.all():
        raise ValueError("every input bin must be marked as covered by source measurements")
    if not np.isfinite(spectra).all() or spectra.min() < 0:
        raise ValueError("spectra must be finite and nonnegative")
    if not np.allclose(spectra.max(axis=1), 1, rtol=0, atol=1e-6):
        raise ValueError("every spectrum must be max-normalized on the model grid")
    return ids, spectra, indices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    args = parser.parse_args()
    _, spectra, indices = load_frozen_inputs(args.manifest, args.inputs)
    print(json.dumps({
        "status": "FROZEN_INPUT_CONTRACT_PASSED",
        "shape": list(spectra.shape),
        "class_counts": dict(zip(CRYSTAL_SYSTEMS, np.bincount(indices).tolist(), strict=True)),
        "manifest_sha256": MANIFEST_SHA256,
        "inputs_sha256": INPUTS_SHA256,
    }))


if __name__ == "__main__":
    main()
