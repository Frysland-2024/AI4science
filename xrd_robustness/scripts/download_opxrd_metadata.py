#!/usr/bin/env python3
"""
opXRD Metadata Extractor v1
============================
Extracts metadata from opXRD experimental PXRD JSON files into a
structured, machine-readable manifest without downloading any data.

This script reads the locally cached opXRD dataset (92,552 JSON files)
and produces a single metadata manifest CSV.

Usage:
    python download_opxrd_metadata.py --help
    python download_opxrd_metadata.py --input-root <path> --output <manifest.csv>
    python download_opxrd_metadata.py --dry-run
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------------------------------------
# Constants
# ----------------------------------------------------------
DEFAULT_INPUT_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "01_literature", "data_resources", "opxrd_zenodo_14254270"
)
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "real_xrd", "opxrd"
)

MANIFEST_VERSION = "opxrd-metadata-manifest-v1"
SOURCE_ZENODO_RECORD = "14254270"
SOURCE_DOI = "10.1002/aidi.202500044"

MANIFEST_COLUMNS = [
    "scan_id",
    "contributor",
    "source_file",
    "file_sha256",
    "file_size_bytes",
    "two_theta_count",
    "intensity_count",
    "two_theta_min",
    "two_theta_max",
    "two_theta_monotonic",
    "intensity_nonzero_fraction",
    "is_simulated",
    "num_phases",
    "chemical_composition",
    "composition_source",
    "space_group_number",
    "space_group_symbol",
    "lattice_params",
    "crystal_system_from_lattice",
    "full_structure_present",
    "has_basis",
    "label_source",
    "crystallite_size_nm",
    "temp_K",
    "primary_wavelength",
    "institution",
    "contributor_name",
    "original_file_format",
    "measurement_date",
    "tags",
    "xrdpattern_version",
    "label_raw",
    "metadata_raw",
    "parse_error",
    "quality_warnings",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="opXRD Metadata Extractor v1 — extract structured metadata "
                    "from opXRD JSON files into a CSV manifest."
    )
    parser.add_argument(
        "--input-root",
        default=DEFAULT_INPUT_ROOT,
        help="Root directory containing opXRD contributor subdirectories "
             f"(default: {DEFAULT_INPUT_ROOT})"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV manifest path (default: <output-dir>/opxrd_metadata_manifest_v1.csv)"
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate paths and count files without extracting metadata."
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process (for testing; default: all)."
    )
    parser.add_argument(
        "--contributors",
        nargs="*",
        default=None,
        help="Specific contributor directories to include (default: all)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)."
    )
    return parser.parse_args()


def safe_json_parse(raw: Any) -> Tuple[Optional[Dict], Optional[str]]:
    """Safely parse a JSON string or return a dict. Returns (parsed, error)."""
    if raw is None:
        return None, "null_value"
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as e:
            return None, f"json_decode_error: {e}"
    return None, f"unexpected_type: {type(raw).__name__}"


def lattice_to_crystal_system(lat_str: str) -> Optional[str]:
    """Infer crystal system from lattice parameters string '(a,b,c,alpha,beta,gamma)'."""
    try:
        nums = [float(x.strip()) for x in lat_str.strip("()[]").split(",")]
        if len(nums) != 6:
            return None
        a, b, c, alpha, beta, gamma = nums
    except (ValueError, IndexError):
        return None

    tol_angle = 1.5
    tol_len = 0.02
    a90 = all(abs(x - 90) < tol_angle for x in [alpha, beta, gamma])
    eq_ratio = lambda x, y: abs(x - y) < tol_len * max(abs(x), abs(y), 1.0)
    a_eq_b = eq_ratio(a, b)
    b_eq_c = eq_ratio(b, c)
    a_eq_c = eq_ratio(a, c)
    all90_except_gamma = abs(alpha - 90) < tol_angle and abs(beta - 90) < tol_angle

    if a90:
        if a_eq_b and b_eq_c:
            return "cubic"
        elif a_eq_b and not b_eq_c:
            return "tetragonal"
        elif not a_eq_b and not b_eq_c and not a_eq_c:
            return "orthorhombic"
        elif not a_eq_b and not b_eq_c and a_eq_c:
            return "tetragonal"
        else:
            return "orthorhombic"
    elif all90_except_gamma and a_eq_b:
        if abs(gamma - 120) < tol_angle:
            return "hexagonal"
        return "monoclinic"
    elif sum(1 for x in [alpha, beta, gamma] if abs(x - 90) > tol_angle) >= 2:
        return "triclinic"
    else:
        return "monoclinic"


def extract_elements_from_basis(basis_raw: Any) -> Optional[str]:
    """Extract element symbols from atomic basis data. Returns sorted formula fragment."""
    if basis_raw is None:
        return None
    if isinstance(basis_raw, str):
        parsed, _ = safe_json_parse(basis_raw)
        if parsed is not None:
            basis_raw = parsed
    if not isinstance(basis_raw, list):
        return None

    elements = {}
    for atom in basis_raw[:500]:  # sample first 500 atoms
        if isinstance(atom, str):
            a, _ = safe_json_parse(atom)
            if a is not None:
                atom = a
        if isinstance(atom, dict):
            sym = atom.get("symbol", "")
            if sym and isinstance(sym, str):
                # Clean oxidation state: "Ba0+" -> "Ba", "O2-" -> "O"
                clean = re.sub(r'[0-9+\-]', '', sym).strip()
                if clean and len(clean) <= 2 and clean[0].isupper():
                    elements[clean] = elements.get(clean, 0) + 1

    if not elements:
        return None

    # Sort by element symbol
    sorted_elems = sorted(elements.items())
    formula_parts = []
    for elem, count in sorted_elems:
        if count == 1:
            formula_parts.append(elem)
        else:
            formula_parts.append(f"{elem}{count}")
    return "".join(formula_parts)


def extract_phase_info(phase_raw: Any) -> Dict[str, Any]:
    """Extract structured info from a single phase entry, handling nested JSON strings."""
    phase = phase_raw
    if isinstance(phase, str):
        parsed, _ = safe_json_parse(phase)
        if parsed is not None:
            phase = parsed
    if not isinstance(phase, dict):
        return {}

    result = {}
    # chemical_composition — explicit
    cc = phase.get("chemical_composition")
    if cc is not None and isinstance(cc, str) and cc.strip():
        result["chemical_composition"] = cc.strip()

    # spacegroup — can be int (number) or str (symbol)
    sg = phase.get("spacegroup")
    if sg is not None:
        if isinstance(sg, (int, float)):
            result["space_group_number"] = int(sg)
        elif isinstance(sg, str) and sg.strip():
            sg_str = sg.strip()
            try:
                result["space_group_number"] = int(sg_str)
            except ValueError:
                result["space_group_symbol"] = sg_str

    # lattice
    lattice = phase.get("lattice")
    if lattice is not None and isinstance(lattice, str) and lattice.strip():
        result["lattice_params"] = str(lattice)[:200]
        # Infer crystal system from lattice
        cs = lattice_to_crystal_system(lattice)
        if cs:
            result["crystal_system_from_lattice"] = cs
            # If we have crystal system but not spacegroup, use it
            if result.get("space_group_number") is None and result.get("space_group_symbol") is None:
                result["label_source"] = "lattice_parameters"

    # basis / atomic coordinates — extract elements
    basis = phase.get("basis")
    if basis is not None:
        result["has_basis"] = True
        elems = extract_elements_from_basis(basis)
        if elems and not result.get("chemical_composition"):
            result["chemical_composition"] = elems
            result["composition_source"] = "basis_elements"
    else:
        result["has_basis"] = False

    # full structure = has lattice + basis + (SG or CC)
    result["full_structure_present"] = (
        result.get("lattice_params") is not None and
        result.get("has_basis", False)
    )

    return result


def extract_label_info(label_raw: Any) -> Dict[str, Any]:
    """Extract structured information from the label field."""
    result = {
        "is_simulated": None,
        "num_phases": 0,
        "chemical_composition": None,
        "composition_source": None,
        "space_group_number": None,
        "space_group_symbol": None,
        "lattice_params": None,
        "crystal_system_from_lattice": None,
        "full_structure_present": False,
        "has_basis": False,
        "label_source": None,
        "crystallite_size_nm": None,
        "temp_K": None,
        "primary_wavelength": None,
    }
    # NOTE: these default False values are overwritten by phase_info below

    label, parse_err = safe_json_parse(label_raw)
    if parse_err:
        result["parse_error"] = f"label_{parse_err}"
        return result

    if not isinstance(label, dict):
        return result

    # Flags
    result["is_simulated"] = label.get("is_simulated", None)
    result["crystallite_size_nm"] = label.get("crystallite_size_nm", None)
    result["temp_K"] = label.get("temp_K", None)

    # X-ray info
    xray = label.get("xray_info")
    if xray is not None:
        xray_parsed, _ = safe_json_parse(xray)
        if isinstance(xray_parsed, dict):
            result["primary_wavelength"] = xray_parsed.get("primary_wavelength", None)

    # Phases
    phases = label.get("phases", [])
    if isinstance(phases, list):
        result["num_phases"] = len(phases)
        if phases:
            phase_info = extract_phase_info(phases[0])
            # Apply phase_info: for nullable fields, only overwrite if result is None;
            # for boolean fields (full_structure_present, has_basis), always overwrite
            nullable_keys = {"chemical_composition", "space_group_number", "space_group_symbol",
                             "lattice_params", "crystal_system_from_lattice",
                             "label_source", "composition_source"}
            for k, v in phase_info.items():
                if v is not None:
                    if k in nullable_keys:
                        if result.get(k) is None:
                            result[k] = v
                    else:
                        result[k] = v

    return result


def check_quality(two_theta: List[float], intensities: List[float]) -> Dict[str, Any]:
    """Run quality checks on spectrum data. Returns dict with warnings."""
    warnings = []

    n = len(two_theta)
    if n < 50:
        warnings.append(f"insufficient_points:{n}")

    if n > 0:
        tmin, tmax = two_theta[0], two_theta[-1]
        if tmax - tmin < 5.0:
            warnings.append(f"narrow_range:{tmax - tmin:.1f}")

        # Monotonic check
        for i in range(1, n):
            if two_theta[i] <= two_theta[i - 1]:
                warnings.append("non_monotonic_axis")
                break

    # Intensity checks
    if intensities:
        nonzero = sum(1 for v in intensities if v != 0)
        zero_frac = 1.0 - nonzero / len(intensities)
        if zero_frac > 0.95:
            warnings.append(f"too_many_zeros:{zero_frac:.3f}")
        if nonzero == 0:
            warnings.append("all_zero_intensity")

        # Finite check
        try:
            finite_count = sum(1 for v in intensities if v == v and v != float('inf') and v != float('-inf'))
            if finite_count < len(intensities):
                warnings.append(f"non_finite_intensity:{len(intensities) - finite_count}")
        except (TypeError, OverflowError):
            warnings.append("intensity_type_error")

    return {
        "two_theta_count": n,
        "intensity_count": len(intensities) if intensities else 0,
        "two_theta_min": round(two_theta[0], 4) if n > 0 else None,
        "two_theta_max": round(two_theta[-1], 4) if n > 0 else None,
        "two_theta_monotonic": "non_monotonic_axis" not in str(warnings),
        "intensity_nonzero_fraction": round(nonzero / len(intensities), 4) if intensities and len(intensities) > 0 else None,
        "quality_warnings": ";".join(warnings) if warnings else None,
    }


def extract_metadata(raw_metadata: Any) -> Dict[str, Any]:
    """Extract structured metadata from the metadata field."""
    result = {
        "institution": None,
        "contributor_name": None,
        "original_file_format": None,
        "measurement_date": None,
        "tags": None,
        "xrdpattern_version": None,
    }

    meta, parse_err = safe_json_parse(raw_metadata)
    if parse_err:
        result["parse_error"] = f"metadata_{parse_err}"
        return result

    if isinstance(meta, dict):
        result["institution"] = meta.get("institution", None)
        result["contributor_name"] = meta.get("contributor_name", None)
        result["original_file_format"] = meta.get("original_file_format", None)
        result["measurement_date"] = meta.get("measurement_date", None)
        tags = meta.get("tags", None)
        if isinstance(tags, list):
            result["tags"] = ";".join(str(t) for t in tags)
        result["xrdpattern_version"] = meta.get("xrdpattern_version", None)

    return result


def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest().upper()


def process_one_file(filepath: str, contributor: str) -> Dict[str, Any]:
    """Process a single opXRD JSON file and extract all metadata."""
    filename = os.path.basename(filepath)
    scan_id = f"{contributor}/{filename}"

    result = {
        "scan_id": scan_id,
        "contributor": contributor,
        "source_file": filename,
        "file_sha256": None,
        "file_size_bytes": None,
        "parse_error": None,
        "quality_warnings": None,
    }

    try:
        file_size = os.path.getsize(filepath)
        result["file_size_bytes"] = file_size
    except OSError:
        pass

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError, PermissionError) as e:
        result["parse_error"] = f"file_read_error:{type(e).__name__}"
        return result

    # Quality checks
    two_theta = data.get("two_theta_values", [])
    intensities = data.get("intensities", [])
    quality = check_quality(two_theta, intensities)
    result.update(quality)

    # Label extraction
    label_info = extract_label_info(data.get("label"))
    label_parse_err = label_info.pop("parse_error", None)
    if label_parse_err and not result.get("parse_error"):
        result["parse_error"] = label_parse_err
    result.update(label_info)

    # Metadata extraction
    meta_info = extract_metadata(data.get("metadata"))
    meta_parse_err = meta_info.pop("parse_error", None)
    if meta_parse_err and not result.get("parse_error"):
        result["parse_error"] = meta_parse_err
    result.update(meta_info)

    # Store raw strings for provenance
    result["label_raw"] = str(data.get("label", ""))[:500]
    result["metadata_raw"] = str(data.get("metadata", ""))[:500]

    # Compute file hash
    try:
        result["file_sha256"] = compute_file_hash(filepath)
    except Exception:
        pass

    return result


def find_json_files(input_root: str, contributors: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Find all JSON files in contributor directories. Returns list of (contributor, filepath)."""
    files = []
    if not os.path.isdir(input_root):
        print(f"ERROR: Input root not found: {input_root}", file=sys.stderr)
        sys.exit(1)

    all_contributors = [
        d for d in os.listdir(input_root)
        if os.path.isdir(os.path.join(input_root, d))
    ]

    target_contributors = contributors if contributors else all_contributors
    target_contributors = [c for c in target_contributors if c in all_contributors]

    if not target_contributors:
        print(f"ERROR: No valid contributor directories found in {input_root}", file=sys.stderr)
        sys.exit(1)

    for contrib in sorted(target_contributors):
        contrib_dir = os.path.join(input_root, contrib)
        for root, dirs, filenames in os.walk(contrib_dir):
            for fn in sorted(filenames):
                if fn.endswith(".json"):
                    files.append((contrib, os.path.join(root, fn)))

    return files


def generate_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary of the extracted metadata."""
    total = len(records)
    simulated = sum(1 for r in records if r.get("is_simulated") is True)
    experimental = sum(1 for r in records if r.get("is_simulated") is False)
    unknown_sim = sum(1 for r in records if r.get("is_simulated") is None)
    with_sg = sum(1 for r in records if r.get("space_group_number") is not None or r.get("space_group_symbol") is not None)
    with_cc = sum(1 for r in records if r.get("chemical_composition") is not None)
    with_quality_warnings = sum(1 for r in records if r.get("quality_warnings"))
    parse_errors = sum(1 for r in records if r.get("parse_error"))

    by_contributor = {}
    for r in records:
        c = r.get("contributor", "unknown")
        if c not in by_contributor:
            by_contributor[c] = 0
        by_contributor[c] += 1

    return {
        "manifest_version": MANIFEST_VERSION,
        "source_zenodo_record": SOURCE_ZENODO_RECORD,
        "source_doi": SOURCE_DOI,
        "total_files": total,
        "simulated_count": simulated,
        "experimental_count": experimental,
        "unknown_simulation_status": unknown_sim,
        "files_with_space_group": with_sg,
        "files_with_composition": with_cc,
        "files_with_quality_warnings": with_quality_warnings,
        "files_with_parse_errors": parse_errors,
        "by_contributor": by_contributor,
        "extraction_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main():
    args = parse_args()

    # Validate input
    input_root = os.path.abspath(args.input_root)
    print(f"Input root: {input_root}")

    files = find_json_files(input_root, args.contributors)
    print(f"Found {len(files)} JSON files across {len(set(c for c, _ in files))} contributor(s)")

    if args.max_files:
        files = files[:args.max_files]
        print(f"Limited to {len(files)} files (--max-files={args.max_files})")

    if args.dry_run:
        print("DRY RUN — no metadata extraction.")
        by_contrib = {}
        for c, _ in files:
            by_contrib[c] = by_contrib.get(c, 0) + 1
        for c, count in sorted(by_contrib.items()):
            print(f"  {c}: {count} files")
        print("Dry run complete. Use without --dry-run to extract metadata.")
        return

    # Process files
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = args.output or os.path.join(args.output_dir, "opxrd_metadata_manifest_v1.csv")

    records = []
    start_time = time.time()
    for i, (contrib, filepath) in enumerate(files):
        if (i + 1) % 5000 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  Processed {i+1}/{len(files)} files ({rate:.0f}/s)...")

        record = process_one_file(filepath, contrib)
        records.append(record)

    elapsed = time.time() - start_time
    print(f"Processed {len(records)} files in {elapsed:.1f}s ({len(records)/elapsed:.0f}/s)")

    # Write CSV
    print(f"Writing manifest to: {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    # Write summary JSON
    summary_path = output_path.replace(".csv", "_summary.json")
    summary = generate_summary(records)
    summary["output_manifest"] = output_path
    summary["manifest_sha256"] = compute_file_hash(output_path)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary written to: {summary_path}")

    # Print summary to stdout
    print(f"\n=== Extraction Summary ===")
    print(f"Total files:        {summary['total_files']}")
    print(f"Experimental:       {summary['experimental_count']}")
    print(f"Simulated:          {summary['simulated_count']}")
    print(f"Unknown sim status: {summary['unknown_simulation_status']}")
    print(f"With space group:   {summary['files_with_space_group']}")
    print(f"With composition:   {summary['files_with_composition']}")
    print(f"Quality warnings:   {summary['files_with_quality_warnings']}")
    print(f"Parse errors:       {summary['files_with_parse_errors']}")
    print(f"\nBy contributor:")
    for c, count in sorted(summary["by_contributor"].items()):
        print(f"  {c}: {count}")


if __name__ == "__main__":
    main()
