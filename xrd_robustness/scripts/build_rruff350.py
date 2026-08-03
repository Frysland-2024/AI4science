#!/usr/bin/env python3
"""Build a provenance-preserving balanced RRUFF measured-PXRD collection.

The collection retains the frozen RRUFF-70 samples as a labelled legacy subset
and adds a configurable number of measured samples per crystal system. Selection
is model-blind: only source metadata, measurement quality, paired DIF/refinement
evidence, and pairwise spectrum redundancy are used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile

import numpy as np
from pymatgen.symmetry.groups import SpaceGroup
from scipy.ndimage import gaussian_filter1d, minimum_filter1d
from scipy.signal import find_peaks

CLASS_ORDER = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)
GRID = 10.0 + np.arange(3501, dtype=np.float64) * 0.02
SOURCE_ARCHIVES = (
    "XY_RAW.zip",
    "XY_Processed.zip",
    "DIF.zip",
    "Refinement_Data.zip",
    "Refinement_Output_Data.zip",
)
MAX_PER_MINERAL = 3
MAX_PAIRWISE_PEARSON = 0.98


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def decode(data: bytes) -> str:
    return data.decode("utf-8", "replace").replace("\r", "")


def parse_headers(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("##"):
            break
        if "=" in line[2:]:
            key, value = line[2:].split("=", 1)
            result[key.strip().upper()] = value.strip()
    return result


def is_xrd_confirmed(status: str) -> bool:
    normalized = status.lower()
    return "confirmed" in normalized and "x-ray diffraction" in normalized


def parse_raw_profile(text: str) -> tuple[np.ndarray, np.ndarray]:
    rows: list[tuple[float, float]] = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        try:
            x, y = line.split(",")[:2]
            rows.append((float(x), float(y)))
        except (ValueError, IndexError):
            continue
    if len(rows) < 2:
        raise ValueError("RAW profile contains fewer than two numeric rows")
    array = np.asarray(rows, dtype=np.float64)
    order = np.argsort(array[:, 0], kind="mergesort")
    x = array[order, 0]
    y = array[order, 1]
    x, unique_indices = np.unique(x, return_index=True)
    return x, y[unique_indices]


def canonical_profile(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    profile = np.interp(GRID, x, y, left=0.0, right=0.0)
    if not np.isfinite(profile).all():
        raise ValueError("profile contains non-finite values")
    maximum = float(profile.max())
    if maximum <= 0:
        raise ValueError("profile maximum is not positive")
    return np.asarray(profile / maximum, dtype=np.float64)


def parse_dif(text: str) -> tuple[str, np.ndarray, np.ndarray]:
    match = re.search(r"^\s*SPACE GROUP:\s*(.*?)\s*$", text, re.I | re.M)
    space_group = match.group(1).strip() if match else ""
    positions: list[float] = []
    intensities: list[float] = []
    pattern = re.compile(
        r"^\s*([0-9]+(?:\.[0-9]+)?)\s+"
        r"([0-9]+(?:\.[0-9]+)?)\s+"
        r"[0-9]+(?:\.[0-9]+)?\s+[-0-9]+\s+[-0-9]+\s+[-0-9]+\s*$"
    )
    for line in text.splitlines():
        peak = pattern.match(line)
        if peak:
            positions.append(float(peak.group(1)))
            intensities.append(float(peak.group(2)))
    return (
        space_group,
        np.asarray(positions, dtype=np.float64),
        np.asarray(intensities, dtype=np.float64),
    )


def cell_crystal_system(headers: dict[str, str]) -> str:
    match = re.search(
        r"crystal system:\s*([A-Za-z]+)", headers.get("CELL PARAMETERS", ""), re.I
    )
    return match.group(1).lower() if match else ""


def classify_crystal_system(
    space_group: str, raw_cell_system: str, *, legacy_class: str | None
) -> tuple[str, str]:
    if legacy_class:
        return legacy_class, "frozen_rruff70_label"
    if space_group:
        try:
            return str(SpaceGroup(space_group).crystal_system), "dif_space_group"
        except ValueError:
            pass
    if raw_cell_system in CLASS_ORDER and raw_cell_system != "hexagonal":
        return raw_cell_system, "raw_cell_plus_refinement_symmetry"
    return "", "insufficient_hexagonal_trigonal_disambiguation"


def theoretical_consistency(
    measured: np.ndarray, peak_x: np.ndarray, peak_i: np.ndarray
) -> dict[str, float]:
    keep = (peak_x >= GRID[0]) & (peak_x <= GRID[-1]) & np.isfinite(peak_i)
    peak_x = peak_x[keep]
    peak_i = peak_i[keep]
    if not len(peak_x) or float(peak_i.max(initial=0.0)) <= 0:
        return {
            "sqrt_pearson_best": -1.0,
            "weighted_theoretical_coverage_5pct": 0.0,
            "best_global_shift_deg": 0.0,
            "best_audit_fwhm_deg": 0.0,
        }
    peak_i = peak_i / peak_i.max()
    significant = peak_i >= 0.05
    baseline = minimum_filter1d(measured, size=251, mode="nearest")
    corrected = np.clip(measured - baseline, 0.0, None)
    corrected = gaussian_filter1d(corrected, sigma=2.0)
    corrected = np.sqrt(corrected / max(float(corrected.max()), 1e-12))
    measured_peak_indices, _ = find_peaks(corrected, prominence=0.025, distance=3)
    measured_peak_x = GRID[measured_peak_indices]
    best = (-2.0, -1.0, 0.0, 0.0, 0.0)
    for fwhm in (0.15, 0.25, 0.35):
        impulses = np.zeros_like(GRID)
        indices = np.rint((peak_x - GRID[0]) / 0.02).astype(int)
        valid = (indices >= 0) & (indices < len(GRID))
        np.add.at(impulses, indices[valid], peak_i[valid])
        rendered_zero = gaussian_filter1d(
            impulses, sigma=(fwhm / 2.354820045) / 0.02, mode="constant"
        )
        for shift in np.arange(-0.30, 0.3001, 0.02):
            rendered = np.interp(GRID - shift, GRID, rendered_zero, left=0.0, right=0.0)
            rendered = np.sqrt(rendered / max(float(rendered.max()), 1e-12))
            corr = float(np.corrcoef(corrected, rendered)[0, 1])
            if not np.isfinite(corr):
                corr = -1.0
            if measured_peak_x.size:
                distances = np.min(
                    np.abs(
                        (peak_x[significant] + shift)[:, None]
                        - measured_peak_x[None, :]
                    ),
                    axis=1,
                )
                weights = peak_i[significant]
                coverage = float(weights[distances <= 0.25].sum() / weights.sum())
            else:
                coverage = 0.0
            score = corr + 0.25 * coverage
            if score > best[0]:
                best = (score, corr, coverage, float(shift), float(fwhm))
    return {
        "sqrt_pearson_best": best[1],
        "weighted_theoretical_coverage_5pct": best[2],
        "best_global_shift_deg": best[3],
        "best_audit_fwhm_deg": best[4],
    }


def spectrum_qc(x: np.ndarray, y: np.ndarray, profile: np.ndarray) -> dict[str, Any]:
    in_range = (x >= 10.0) & (x <= 80.0)
    source = y[in_range]
    steps = np.diff(x)
    peak_count = int(len(find_peaks(profile, prominence=0.005, distance=2)[0]))
    return {
        "original_two_theta_min": float(x.min()),
        "original_two_theta_max": float(x.max()),
        "original_step_median": float(np.median(steps)) if len(steps) else 0.0,
        "contrast_q99_minus_q10": float(
            np.quantile(profile, 0.99) - np.quantile(profile, 0.10)
        ),
        "negative_fraction_10_80": float(np.mean(source < 0)) if source.size else 1.0,
        "detected_peak_count_qc": peak_count,
    }


def profile_csv_bytes(profile: np.ndarray) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("two_theta", "intensity"))
    writer.writerows(zip(GRID, profile, strict=True))
    return stream.getvalue().encode("utf-8")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def selection_key(candidate: dict[str, Any]) -> tuple[float, float, str]:
    quality = (
        candidate["qc"]["sqrt_pearson_best"]
        + 0.25 * candidate["qc"]["weighted_theoretical_coverage_5pct"]
    )
    stable = hashlib.sha256(candidate["rruff_id"].encode()).hexdigest()
    return (-quality, -candidate["qc"]["contrast_q99_minus_q10"], stable)


def max_correlation(profile: np.ndarray, selected: list[dict[str, Any]]) -> float:
    if not selected:
        return 0.0
    correlations = [
        float(np.corrcoef(profile, item["profile"])[0, 1]) for item in selected
    ]
    return max(correlations)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--legacy-manifest", type=Path, required=True)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-per-class", type=int, default=50)
    parser.add_argument("--dataset-version", type=int, default=1)
    args = parser.parse_args()
    if args.target_per_class < 10:
        raise ValueError("target-per-class cannot be smaller than frozen legacy count 10")
    if args.dataset_version < 1:
        raise ValueError("dataset-version must be positive")
    target_per_class = int(args.target_per_class)
    total_samples = target_per_class * len(CLASS_ORDER)
    collection_name = f"rruff{total_samples}"
    extension_role = f"{collection_name}_extension"
    dataset_id = f"rruff-real-pxrd-{total_samples}-v{args.dataset_version}"
    source_root = args.source_root.resolve()
    legacy_root = args.legacy_root.resolve()
    output_root = args.output_root.resolve()
    archive_paths = {name: source_root / name for name in SOURCE_ARCHIVES}
    missing = [str(path) for path in archive_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing source archives: {missing}")

    with args.legacy_manifest.open("r", encoding="utf-8", newline="") as handle:
        legacy_rows = list(csv.DictReader(handle))
    legacy_by_id = {row["rruff_id"]: row for row in legacy_rows}
    if len(legacy_by_id) != 70:
        raise ValueError("legacy manifest must contain 70 unique RRUFF IDs")

    with ZipFile(archive_paths["DIF.zip"]) as dif_zip:
        dif_members = {
            name.split("__DIF_File__")[0]: name
            for name in dif_zip.namelist()
            if "__DIF_File__" in name
        }
        dif_payloads = {name: dif_zip.read(name) for name in dif_members.values()}
    with ZipFile(archive_paths["Refinement_Output_Data.zip"]) as refinement_zip:
        refinement_members = {
            re.search(r"R\d{6}", name).group(0): name
            for name in refinement_zip.namelist()
            if re.search(r"R\d{6}", name)
        }
        refinement_payloads = {
            name: refinement_zip.read(name) for name in refinement_members.values()
        }

    candidates: list[dict[str, Any]] = []
    rejected: dict[str, int] = {}

    def reject(reason: str) -> None:
        rejected[reason] = rejected.get(reason, 0) + 1

    with ZipFile(archive_paths["XY_RAW.zip"]) as raw_zip:
        for raw_member in raw_zip.namelist():
            if "__Xray_Data_XY_RAW__" not in raw_member:
                continue
            prefix = raw_member.split("__Xray_Data_XY_RAW__")[0]
            raw_payload = raw_zip.read(raw_member)
            raw_text = decode(raw_payload)
            headers = parse_headers(raw_text)
            rruff_id = headers.get("RRUFFID", "")
            if headers.get("DIFFRACTION SAMPLE DESCRIPTION") != "Powder":
                reject("not_exact_measured_powder")
                continue
            if not is_xrd_confirmed(headers.get("STATUS", "")):
                reject("identification_not_xrd_confirmed")
                continue
            if prefix not in dif_members:
                reject("paired_dif_missing")
                continue
            dif_member = dif_members[prefix]
            dif_payload = dif_payloads[dif_member]
            space_group, peak_x, peak_i = parse_dif(decode(dif_payload))
            legacy = legacy_by_id.get(rruff_id)
            crystal_system, label_source = classify_crystal_system(
                space_group,
                cell_crystal_system(headers),
                legacy_class=legacy["crystal_system"] if legacy else None,
            )
            if crystal_system not in CLASS_ORDER:
                reject("crystal_system_not_auditable")
                continue
            try:
                x, y = parse_raw_profile(raw_text)
                profile = canonical_profile(x, y)
            except ValueError:
                reject("invalid_raw_profile")
                continue
            qc = spectrum_qc(x, y, profile)
            qc.update(theoretical_consistency(profile, peak_x, peak_i))
            if x.min() > 10.0 or x.max() < 80.0:
                reject("insufficient_10_80_coverage")
                continue
            if qc["contrast_q99_minus_q10"] < 0.02:
                reject("insufficient_contrast")
                continue
            if qc["negative_fraction_10_80"] > 0.05:
                reject("excessive_negative_intensity")
                continue
            if qc["detected_peak_count_qc"] < 5:
                reject("too_few_detected_peaks")
                continue
            refinement_member = refinement_members.get(rruff_id, "")
            candidates.append(
                {
                    "rruff_id": rruff_id,
                    "mineral_name": headers.get("NAMES", ""),
                    "crystal_system": crystal_system,
                    "label_source": label_source,
                    "space_group": space_group,
                    "raw_cell_crystal_system": cell_crystal_system(headers),
                    "headers": headers,
                    "raw_member": raw_member,
                    "raw_sha256": sha256_bytes(raw_payload),
                    "dif_member": dif_member,
                    "dif_sha256": sha256_bytes(dif_payload),
                    "dif_payload": dif_payload,
                    "refinement_member": refinement_member,
                    "refinement_sha256": (
                        sha256_bytes(refinement_payloads[refinement_member])
                        if refinement_member
                        else ""
                    ),
                    "refinement_payload": (
                        refinement_payloads[refinement_member]
                        if refinement_member
                        else b""
                    ),
                    "profile": profile,
                    "qc": qc,
                    "legacy": legacy is not None,
                }
            )

    # A frozen legacy sample can disappear from a later upstream snapshot. Preserve
    # it from the already-audited RRUFF-70 evidence instead of silently replacing it.
    recovered_ids = {item["rruff_id"] for item in candidates if item["legacy"]}
    for rruff_id, legacy in legacy_by_id.items():
        if rruff_id in recovered_ids:
            continue
        spectrum_path = legacy_root / legacy["spectrum_path"]
        dif_path = legacy_root / legacy["dif_evidence_path"]
        if sha256_file(spectrum_path) != legacy["spectrum_sha256"]:
            raise ValueError(f"legacy spectrum hash mismatch: {rruff_id}")
        if sha256_file(dif_path) != legacy["dif_member_sha256"]:
            raise ValueError(f"legacy DIF hash mismatch: {rruff_id}")
        spectrum = np.loadtxt(spectrum_path, delimiter=",", skiprows=1)
        if spectrum.shape != (len(GRID), 2) or not np.allclose(
            spectrum[:, 0], GRID, atol=1e-9
        ):
            raise ValueError(f"legacy canonical grid mismatch: {rruff_id}")
        profile = spectrum[:, 1]
        dif_payload = dif_path.read_bytes()
        candidates.append(
            {
                "rruff_id": rruff_id,
                "mineral_name": legacy["mineral_name"],
                "crystal_system": legacy["crystal_system"],
                "label_source": "frozen_rruff70_local_evidence",
                "space_group": legacy["space_group"],
                "raw_cell_crystal_system": legacy["rruff_cell_crystal_system"],
                "headers": {
                    "NAMES": legacy["mineral_name"],
                    "RRUFFID": rruff_id,
                    "IDEAL CHEMISTRY": legacy["ideal_formula_raw"],
                    "MEASURED CHEMISTRY": legacy["measured_chemistry_raw"],
                    "STATUS": legacy["identification_status"],
                    "URL": legacy["official_record_url"],
                    "DIFFRACTION SAMPLE DESCRIPTION": legacy["sample_description"],
                },
                "raw_member": legacy["raw_archive_member"],
                "raw_sha256": legacy["raw_member_sha256"],
                "dif_member": legacy["dif_archive_member"],
                "dif_sha256": legacy["dif_member_sha256"],
                "dif_payload": dif_payload,
                "refinement_member": "",
                "refinement_sha256": "",
                "refinement_payload": b"",
                "profile": profile,
                "qc": {
                    "original_two_theta_min": float(legacy["original_two_theta_min"]),
                    "original_two_theta_max": float(legacy["original_two_theta_max"]),
                    "original_step_median": float(legacy["original_step_median"]),
                    "contrast_q99_minus_q10": float(legacy["contrast_q99_minus_q10"]),
                    "negative_fraction_10_80": float(legacy["negative_fraction_10_80"]),
                    "detected_peak_count_qc": int(legacy["detected_peak_count_qc"]),
                    "sqrt_pearson_best": float(legacy["dif_consistency_sqrt_pearson"]),
                    "weighted_theoretical_coverage_5pct": float(
                        legacy["dif_weighted_peak_coverage_5pct"]
                    ),
                    "best_global_shift_deg": float(legacy["dif_best_global_shift_deg"]),
                    "best_audit_fwhm_deg": float(legacy["dif_best_audit_fwhm_deg"]),
                },
                "legacy": True,
            }
        )

    # The legacy subset is byte-frozen. Even when the current upstream RAW file is
    # available, use the previously frozen canonical CSV so all 70 spectrum hashes
    # remain stable across upstream archive revisions and floating-point reruns.
    for item in candidates:
        if not item["legacy"]:
            continue
        legacy = legacy_by_id[item["rruff_id"]]
        spectrum_path = legacy_root / legacy["spectrum_path"]
        spectrum_payload = spectrum_path.read_bytes()
        if sha256_bytes(spectrum_payload) != legacy["spectrum_sha256"]:
            raise ValueError(f"legacy spectrum hash mismatch: {item['rruff_id']}")
        spectrum = np.loadtxt(io.BytesIO(spectrum_payload), delimiter=",", skiprows=1)
        if spectrum.shape != (len(GRID), 2) or not np.allclose(
            spectrum[:, 0], GRID, atol=1e-9
        ):
            raise ValueError(f"legacy canonical grid mismatch: {item['rruff_id']}")
        item["profile"] = spectrum[:, 1]
        item["legacy_spectrum_payload"] = spectrum_payload

    by_id: dict[str, dict[str, Any]] = {}
    for item in sorted(candidates, key=selection_key):
        by_id.setdefault(item["rruff_id"], item)
    candidates = list(by_id.values())
    selected: list[dict[str, Any]] = []
    selection_relaxations: dict[str, list[str]] = {name: [] for name in CLASS_ORDER}
    for crystal_system in CLASS_ORDER:
        class_candidates = [
            x for x in candidates if x["crystal_system"] == crystal_system
        ]
        legacy_candidates = [x for x in class_candidates if x["legacy"]]
        if len(legacy_candidates) != 10:
            raise ValueError(
                f"{crystal_system}: expected 10 recoverable legacy samples, got {len(legacy_candidates)}"
            )
        class_selected = sorted(legacy_candidates, key=lambda x: x["rruff_id"])
        mineral_counts: dict[str, int] = {}
        for item in class_selected:
            mineral_counts[item["mineral_name"]] = (
                mineral_counts.get(item["mineral_name"], 0) + 1
            )
        pool = sorted(
            (x for x in class_candidates if not x["legacy"]), key=selection_key
        )
        for correlation_limit in (0.95, MAX_PAIRWISE_PEARSON, 0.995):
            if len(class_selected) >= target_per_class:
                break
            if correlation_limit > 0.95:
                selection_relaxations[crystal_system].append(
                    f"pairwise Pearson ceiling relaxed to {correlation_limit:.3f} to fill quota"
                )
            for item in pool:
                if len(class_selected) >= target_per_class or item in class_selected:
                    continue
                if mineral_counts.get(item["mineral_name"], 0) >= MAX_PER_MINERAL:
                    continue
                corr = max_correlation(item["profile"], class_selected)
                if corr >= correlation_limit:
                    continue
                item["max_selected_pearson_at_inclusion"] = corr
                class_selected.append(item)
                mineral_counts[item["mineral_name"]] = (
                    mineral_counts.get(item["mineral_name"], 0) + 1
                )
        if len(class_selected) < target_per_class:
            selection_relaxations[crystal_system].append(
                "maximum samples for one mineral name relaxed from 3 to 4; "
                "pairwise Pearson ceiling remains 0.995"
            )
            for item in pool:
                if len(class_selected) >= target_per_class or item in class_selected:
                    continue
                if mineral_counts.get(item["mineral_name"], 0) >= 4:
                    continue
                corr = max_correlation(item["profile"], class_selected)
                if corr >= 0.995:
                    continue
                item["max_selected_pearson_at_inclusion"] = corr
                class_selected.append(item)
                mineral_counts[item["mineral_name"]] = (
                    mineral_counts.get(item["mineral_name"], 0) + 1
                )
        if len(class_selected) != target_per_class:
            raise RuntimeError(
                f"{crystal_system}: quality/diversity rules selected "
                f"{len(class_selected)}, not {target_per_class}"
            )
        selected.extend(class_selected)

    spectra_dir = output_root / "spectra_10_80_step_002"
    evidence_dir = output_root / "evidence"
    structure_dir = output_root / "structure_refs"
    manifest_dir = output_root / "manifests"
    contracts_dir = output_root / "contracts"
    for directory in (
        spectra_dir,
        evidence_dir,
        structure_dir,
        manifest_dir,
        contracts_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    for item in sorted(
        selected, key=lambda x: (CLASS_ORDER.index(x["crystal_system"]), x["rruff_id"])
    ):
        stem = f"{item['rruff_id']}_{safe_name(item['mineral_name'])}"
        spectrum_path = spectra_dir / f"{stem}.csv"
        spectrum_payload = item.get(
            "legacy_spectrum_payload", profile_csv_bytes(item["profile"])
        )
        spectrum_path.write_bytes(spectrum_payload)
        dif_target = structure_dir / f"{stem}_DIF.txt"
        dif_target.write_bytes(item["dif_payload"])
        refinement_target = ""
        if item["refinement_member"]:
            target = structure_dir / f"{stem}_refinement_output.txt"
            target.write_bytes(item["refinement_payload"])
            refinement_target = str(target.relative_to(output_root)).replace("\\", "/")
        evidence = {
            "dataset_role": (
                "legacy_rruff70" if item["legacy"] else extension_role
            ),
            "dif_archive_member": item["dif_member"],
            "dif_sha256": item["dif_sha256"],
            "headers": item["headers"],
            "label_source": item["label_source"],
            "model_outputs_used_for_selection": False,
            "qc": item["qc"],
            "raw_archive_member": item["raw_member"],
            "raw_sha256": item["raw_sha256"],
            "refinement_archive_member": item["refinement_member"],
            "refinement_sha256": item["refinement_sha256"],
        }
        evidence_path = evidence_dir / f"{stem}.json"
        write_json(evidence_path, evidence)
        manifest_rows.append(
            {
                "sample_id": f"RRUFF-{item['rruff_id']}",
                "rruff_id": item["rruff_id"],
                "mineral_name": item["mineral_name"],
                "crystal_system": item["crystal_system"],
                "dataset_role": evidence["dataset_role"],
                "spectrum_path": str(spectrum_path.relative_to(output_root)).replace(
                    "\\", "/"
                ),
                "spectrum_sha256": sha256_bytes(spectrum_payload),
                "source": "RRUFF official XY_RAW and DIF archives",
                "official_record_url": item["headers"].get("URL", ""),
                "identification_status": item["headers"].get("STATUS", ""),
                "ideal_chemistry": item["headers"].get("IDEAL CHEMISTRY", ""),
                "measured_chemistry": item["headers"].get("MEASURED CHEMISTRY", ""),
                "space_group": item["space_group"],
                "raw_cell_crystal_system": item["raw_cell_crystal_system"],
                "label_source": item["label_source"],
                "raw_archive_member": item["raw_member"],
                "raw_member_sha256": item["raw_sha256"],
                "dif_path": str(dif_target.relative_to(output_root)).replace("\\", "/"),
                "dif_member_sha256": item["dif_sha256"],
                "refinement_path": refinement_target,
                "evidence_path": str(evidence_path.relative_to(output_root)).replace(
                    "\\", "/"
                ),
                "sqrt_pearson_best": item["qc"]["sqrt_pearson_best"],
                "weighted_theoretical_coverage_5pct": item["qc"][
                    "weighted_theoretical_coverage_5pct"
                ],
                "max_selected_pearson_at_inclusion": item.get(
                    "max_selected_pearson_at_inclusion", "legacy_frozen"
                ),
                "selection_status": f"FROZEN_RRUFF{total_samples}_MASTER",
            }
        )

    manifest_path = manifest_dir / f"{collection_name}_master_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    archive_hashes = {name: sha256_file(path) for name, path in archive_paths.items()}
    class_counts = {name: 0 for name in CLASS_ORDER}
    role_counts = {"legacy_rruff70": 0, extension_role: 0}
    for row in manifest_rows:
        class_counts[row["crystal_system"]] += 1
        role_counts[row["dataset_role"]] += 1
    new_correlations = [
        float(row["max_selected_pearson_at_inclusion"])
        for row in manifest_rows
        if row["dataset_role"] == extension_role
    ]
    mineral_counts: dict[tuple[str, str], int] = {}
    for row in manifest_rows:
        key = (row["crystal_system"], row["mineral_name"])
        mineral_counts[key] = mineral_counts.get(key, 0) + 1
    legacy_hashes_preserved = all(
        next(
            row["spectrum_sha256"]
            for row in manifest_rows
            if row["rruff_id"] == legacy["rruff_id"]
        )
        == legacy["spectrum_sha256"]
        for legacy in legacy_rows
    )
    contract = {
        "schema_version": f"{collection_name}-measured-pxrd-v{args.dataset_version}",
        "dataset_id": dataset_id,
        "status": "FROZEN_MODEL_BLIND_DATASET",
        "sample_count": len(manifest_rows),
        "class_counts": class_counts,
        "role_counts": role_counts,
        "source_archive_sha256": archive_hashes,
        "manifest_sha256": sha256_file(manifest_path),
        "selection_unit": "unique_RRUFF_sample_id",
        "selection_rules": {
            "exact_measured_powder_description": True,
            "xrd_confirmed_identification": True,
            "paired_dif_required": True,
            "canonical_grid": "10-80 degrees, 0.02 degree step, max normalized",
            "maximum_samples_per_mineral_name": (
                "3 normally; one class may relax to 4 only when recorded in "
                "selection_relaxations"
            ),
            "pairwise_pearson_policy": "greedy 0.95, then 0.98/0.995 only if quota requires",
            "model_outputs_used": False,
        },
        "selection_relaxations": selection_relaxations,
        "integrity": {
            "unique_rruff_ids": len({row["rruff_id"] for row in manifest_rows}),
            "legacy_spectrum_hashes_preserved": legacy_hashes_preserved,
            "maximum_new_sample_correlation_at_inclusion": max(new_correlations),
            "maximum_samples_for_one_class_mineral_pair": max(mineral_counts.values()),
        },
        "real_test_execution_authorized": False,
        "redistribution_rights_asserted": False,
    }
    write_json(contracts_dir / "dataset_contract.json", contract)
    citation = (
        "# Citation and release policy\n\n"
        "This local collection uses data from the RRUFF Project. Cite Lafuente et al., "
        "The power of databases: The RRUFF project (2016), DOI: "
        "10.1515/9783110417104-003.\n\n"
        "Spectra and DIF/refinement contents are retained for local research use. "
        "Redistribution rights are not asserted. A public package must be metadata-only.\n"
    )
    (output_root / "CITATION_AND_RELEASE_POLICY.md").write_text(
        citation, encoding="utf-8"
    )
    report = {
        "schema_version": f"{collection_name}-build-audit-v{args.dataset_version}",
        "status": (
            "pass"
            if len(manifest_rows) == total_samples
            and set(class_counts.values()) == {target_per_class}
            else "fail"
        ),
        "dataset_id": contract["dataset_id"],
        "sample_count": len(manifest_rows),
        "class_counts": class_counts,
        "role_counts": role_counts,
        "candidate_count_after_qc": len(candidates),
        "rejected_counts": rejected,
        "source_archive_sha256": archive_hashes,
        "manifest_sha256": contract["manifest_sha256"],
        "selection_relaxations": selection_relaxations,
        "integrity": contract["integrity"],
        "model_loaded": False,
        "model_outputs_used": False,
        "real_xrd_inference_run": False,
        "output_root": str(output_root),
    }
    write_json(args.report.resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
