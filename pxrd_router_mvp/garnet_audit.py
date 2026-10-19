"""Independent, read-only validation of the 44 previously shortlisted Garnet records.

This verifier deliberately reparses the official RRUFF ZIP members instead of
trusting the earlier audit's parsed fields. It writes only derived summaries;
it never extracts or copies spectra or source archives.
"""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


GARNET_IDS = (
    "R040001-1", "R040065-1", "R040066-1", "R040076-1", "R040079-1", "R040159-1",
    "R040168-1", "R050029-1", "R050036-1", "R050063-1", "R050081-1", "R050112-1",
    "R050113-1", "R050256-1", "R050311-1", "R050312-1", "R050377-1", "R050446-1",
    "R060125-1", "R060177-1", "R060278-1", "R060279-1", "R060350-1", "R060358-1",
    "R060382-1", "R060423-1", "R060441-1", "R060442-1", "R060443-1", "R060444-1",
    "R060445-1", "R060446-1", "R060447-1", "R060448-1", "R060449-1", "R060450-1",
    "R060451-1", "R060452-1", "R060453-1", "R060499-1", "R061041-1", "R070129-1",
    "R070551-1", "R080053-1",
)

ARCHIVE_URLS = {
    "XY_RAW.zip": "https://www.rruff.net/zipped_data_files/powder/XY_RAW.zip",
    "Refinement_Output_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Output_Data.zip",
    "Refinement_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Data.zip",
    "DIF.zip": "https://www.rruff.net/zipped_data_files/powder/DIF.zip",
    "cif.zip": "https://www.rruff.net/AMS/zipped_files/cif.zip",
}
ID_RE = re.compile(r"__(R\d{6}(?:-\d+)?)__", re.I)
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
REF_CELL_RE = re.compile(rf"(?<![A-Za-z])([A-Za-z]+)\s*=\s*({NUMBER})(?:\((\d+)\))?")
ELEMENTS_RE = re.compile(r"(?<![a-z])([A-Z][a-z]?)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact_id(member: str) -> str | None:
    match = ID_RE.search(member)
    return match.group(1).upper() if match else None


def base_id(sample_id: str) -> str:
    return sample_id.split("-", 1)[0]


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def element_symbols(value: str) -> set[str]:
    return set(ELEMENTS_RE.findall(value or ""))


def _header(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("##") and "=" in line:
            key, value = line[2:].split("=", 1)
            result[key.strip().upper()] = value.strip()
    return result


def _numeric_xy(text: str) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.replace(",", " ").split()
        if len(fields) < 2:
            continue
        try:
            x, y = float(fields[0]), float(fields[1])
        except ValueError:
            continue
        if math.isfinite(x) and math.isfinite(y):
            xs.append(x)
            ys.append(y)
    return xs, ys


def _trace_digest(xs: list[float], ys: list[float]) -> str:
    canonical = "\n".join(f"{x:.10g},{y:.10g}" for x, y in zip(xs, ys, strict=True))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def parse_refinement_output(text: str) -> dict[str, Any]:
    cell: dict[str, dict[str, float | None]] = {}
    for match in REF_CELL_RE.finditer(text):
        key = match.group(1).casefold()
        if key not in {"a", "b", "c", "alpha", "beta", "gamma"} or key in cell:
            continue
        value_s, esd_digits = match.group(2), match.group(3)
        value = float(value_s)
        esd = None
        if esd_digits is not None:
            decimals = len(value_s.split(".", 1)[1]) if "." in value_s else 0
            esd = int(esd_digits) * (10.0 ** (-decimals))
        cell[key] = {"value": value, "esd": esd}
    waves = [float(v) for v in re.findall(rf"Wavelength\s*#\d+\s*=\s*({NUMBER})", text, re.I)]
    machine = re.search(rf"MACHINE ERROR:\s*({NUMBER})", text, re.I)
    rmse = re.search(rf"\brmse\s*=\s*({NUMBER})", text, re.I)
    sys_match = re.search(r"Symmetry constraint is:\s*([^\r\n]+)", text, re.I)
    return {
        "cell": cell,
        "complete_six": all(k in cell and cell[k]["value"] is not None for k in ("a", "b", "c", "alpha", "beta", "gamma")),
        "complete_esd_six": all(k in cell and cell[k]["esd"] is not None for k in ("a", "b", "c", "alpha", "beta", "gamma")),
        "wavelengths": waves,
        "machine_error_deg": float(machine.group(1)) if machine else None,
        "rmse_raw": float(rmse.group(1)) if rmse else None,
        "reported_symmetry": sys_match.group(1).strip() if sys_match else "",
    }


def parse_refinement_data(text: str) -> tuple[str, int, list[float], dict[int, int]]:
    lines = text.splitlines()
    label = lines[1].strip() if len(lines) > 1 else ""
    wavelengths: list[float] = []
    if len(lines) > 2:
        try:
            wavelengths = [float(v) for v in lines[2].split()]
        except ValueError:
            wavelengths = []
    count = 0
    wave_indices: Counter[int] = Counter()
    for line in lines[3:]:
        fields = line.split()
        if len(fields) < 5:
            continue
        try:
            [float(v) for v in fields[:5]]
            count += 1
            wave_indices[int(float(fields[4]))] += 1
        except ValueError:
            continue
    return label, count, wavelengths, dict(sorted(wave_indices.items()))


def _cif_tags(text: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"\s*(_[A-Za-z0-9_.]+)\s+(.+?)\s*$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        tags.setdefault(match.group(1).lower(), value)
    return tags


def _number_tag(tags: dict[str, str], *names: str) -> float | None:
    for name in names:
        value = tags.get(name.lower())
        if value:
            value = re.sub(r"\([^)]*\)$", "", value.strip("'\""))
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _cif_system(tags: dict[str, str]) -> str:
    sg_number = _number_tag(tags, "_space_group_it_number", "_symmetry_int_tables_number")
    sg_symbol = " ".join(tags.get(k, "") for k in (
        "_space_group_name_h-m_alt", "_symmetry_space_group_name_h-m"
    )).casefold().replace(" ", "")
    a, b, c = (_number_tag(tags, f"_cell_length_{axis}") for axis in "abc")
    angles = tuple(_number_tag(tags, f"_cell_angle_{axis}") for axis in ("alpha", "beta", "gamma"))
    if sg_number is not None and sg_number >= 195:
        return "cubic"
    if "ia-3d" in sg_symbol or "fm-3m" in sg_symbol or "fd-3m" in sg_symbol:
        return "cubic"
    if None not in (a, b, c, *angles) and abs(a-b) < 0.02 and abs(b-c) < 0.02 and all(abs(v-90) < 0.02 for v in angles):
        return "cubic_geometry"
    return "unknown_or_non_cubic"


def _archive_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return [name for name in zf.namelist() if not name.endswith("/")]


def _member_text(zf: zipfile.ZipFile, name: str) -> tuple[str, bytes]:
    raw = zf.read(name)
    return raw.decode("latin-1", errors="replace"), raw


def _member_index(zf: zipfile.ZipFile) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for name in zf.namelist():
        sid = exact_id(name)
        if sid:
            result[sid].append(name)
    return result


def _find_cif_candidates(zf: zipfile.ZipFile, mineral: str, cell_a: float | None, ideal_chemistry: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    candidates: list[dict[str, Any]] = []
    target = normalized_name(mineral)
    ideal_elements = element_symbols(ideal_chemistry)
    prefix_hits = [name for name in zf.namelist() if name.casefold().startswith(mineral.casefold() + "__") and name.lower().endswith(".cif")]
    for name in prefix_hits:
        text, raw = _member_text(zf, name)
        tags = _cif_tags(text)
        cif_name = tags.get("_chemical_name_mineral", name.split("__", 1)[0])
        if normalized_name(cif_name) != target:
            continue
        cell = _number_tag(tags, "_cell_length_a")
        formula = tags.get("_chemical_formula_sum", tags.get("_chemical_formula_structural", ""))
        symbols = element_symbols(formula)
        system = _cif_system(tags)
        code_match = re.search(r"__(\d+)\.cif$", name, re.I)
        delta = abs(cell_a - cell) if cell_a is not None and cell is not None else None
        candidates.append({
            "member": name,
            "sha256": sha256_bytes(raw),
            "database_code": tags.get("_database_code_amcsd", code_match.group(1) if code_match else ""),
            "mineral": cif_name,
            "formula": formula,
            "cell_a_angstrom": cell,
            "cell_delta_from_refined_a_angstrom": delta,
            "crystal_system": system,
            "formula_element_symbols": sorted(symbols),
            "ideal_formula_element_missing_from_cif": sorted(ideal_elements - symbols),
            "authors": "; ".join(re.findall(r"^'([^']+)'\s*$", text, re.M)[:4]),
            "publication_title": tags.get("_publ_section_title", "").replace(";", " ").strip(),
        })
    compatible = [c for c in candidates if c["crystal_system"] in {"cubic", "cubic_geometry"} and not c["ideal_formula_element_missing_from_cif"]]
    ranked = sorted(compatible or candidates, key=lambda c: (float("inf") if c["cell_delta_from_refined_a_angstrom"] is None else c["cell_delta_from_refined_a_angstrom"], c["member"]))
    return candidates, ranked[0] if ranked else None


def _frozen_roles(manifest_path: Path | None, split_path: Path | None) -> dict[str, str]:
    roles: dict[str, str] = {}
    if manifest_path and manifest_path.exists():
        with manifest_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rid = row.get("rruff_id", "") or row.get("sample_id", "")
                if rid:
                    roles[base_id(rid)] = row.get("dataset_role", "legacy_manifest")
    if split_path and split_path.exists():
        with split_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rid = row.get("rruff_id", "")
                if rid:
                    roles[base_id(rid)] = row.get("split", "frozen_split")
    return roles


def audit_garnet_archives(archive_root: Path, *,
                          frozen_manifest: Path | None = None,
                          frozen_split: Path | None = None,
                          scope_ids: Iterable[str] = GARNET_IDS) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_root = Path(archive_root)
    paths = {name: archive_root / name for name in ARCHIVE_URLS}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing official archive(s): {', '.join(missing)}")
    frozen_checked = bool(frozen_manifest and frozen_manifest.is_file() and frozen_split and frozen_split.is_file())

    with zipfile.ZipFile(paths["XY_RAW.zip"]) as raw_zf, \
         zipfile.ZipFile(paths["Refinement_Output_Data.zip"]) as out_zf, \
         zipfile.ZipFile(paths["Refinement_Data.zip"]) as refine_zf, \
         zipfile.ZipFile(paths["DIF.zip"]) as dif_zf, \
         zipfile.ZipFile(paths["cif.zip"]) as cif_zf:
        raw_index = _member_index(raw_zf)
        out_index = _member_index(out_zf)
        refine_index = _member_index(refine_zf)
        dif_index = _member_index(dif_zf)
        all_ids_by_base: dict[str, set[str]] = defaultdict(set)
        trace_ids: dict[str, set[str]] = defaultdict(set)
        trace_member_counts: dict[str, int] = defaultdict(int)
        for name in raw_zf.namelist():
            sid = exact_id(name)
            if not sid:
                continue
            all_ids_by_base[base_id(sid)].add(sid)
            text, _ = _member_text(raw_zf, name)
            xs, ys = _numeric_xy(text)
            if len(xs) >= 2:
                digest = _trace_digest(xs, ys)
                trace_ids[digest].add(sid)
                trace_member_counts[digest] += 1

        roles = _frozen_roles(frozen_manifest, frozen_split)
        rows: list[dict[str, Any]] = []
        for sid in scope_ids:
            raw_names = raw_index.get(sid, [])
            record: dict[str, Any] = {
                "rruff_sample_id": sid,
                "rruff_base_id": base_id(sid),
                "sample_name": "",
                "ideal_chemistry": "",
                "measured_chemistry": "",
                "sample_description": "",
                "mixture_or_contamination_caveat": False,
                "raw_member_count_exact_id": len(raw_names),
                "raw_member": raw_names[0] if len(raw_names) == 1 else "|".join(raw_names),
                "raw_member_sha256": "",
                "raw_profile_sha256_numeric_trace": "",
                "raw_parse_status": "missing",
                "raw_valid_powder_profile": False,
                "raw_wavelength_metadata": "unknown_in_XY_RAW",
                "raw_cell_header_present_not_used_for_fit": False,
                "two_theta_min_deg": None,
                "two_theta_max_deg": None,
                "raw_point_count": 0,
                "related_exact_ids_same_base": "|".join(sorted(all_ids_by_base.get(base_id(sid), set()))),
                "duplicate_trace_exact_ids_archivewide": "",
                "duplicate_trace_member_count_archivewide": 0,
                "refinement_output_member_count": len(out_index.get(sid, [])),
                "refinement_output_member": "",
                "refinement_output_member_sha256": "",
                "refinement_parse_status": "missing",
                "refinement_system": "",
                "a_angstrom": None, "a_esd_angstrom": None,
                "b_angstrom": None, "b_esd_angstrom": None,
                "c_angstrom": None, "c_esd_angstrom": None,
                "alpha_deg": None, "alpha_esd_deg": None,
                "beta_deg": None, "beta_esd_deg": None,
                "gamma_deg": None, "gamma_esd_deg": None,
                "lattice_esd_triplet_present": False,
                "angles_symmetry_fixed_without_esd": False,
                "wavelengths_from_refinement_angstrom": "",
                "machine_error_deg": None,
                "refinement_rmse_raw_units": None,
                "refinement_data_member_count": len(refine_index.get(sid, [])),
                "refinement_data_member": "",
                "indexed_reflection_rows": None,
                "refinement_data_wavelengths_angstrom": "",
                "indexed_wavelength_index_counts": "",
                "dif_member_count": len(dif_index.get(sid, [])),
                "dif_member": "",
                "dif_member_sha256": "",
                "dif_space_group": "",
                "dif_cell_parameters": "",
                "dif_xray_wavelength_angstrom": None,
                "cif_exact_name_candidate_count": 0,
                "cif_compatible_candidate_count": 0,
                "cif_selected_reference_member": "",
                "cif_selected_database_code": "",
                "cif_selected_sha256": "",
                "cif_selected_formula": "",
                "cif_selected_cell_a_angstrom": None,
                "cif_template_delta_vs_sample_label_angstrom": None,
                "cif_template_system": "",
                "cif_measured_elements_missing_from_template": "",
                "cif_identity_is_same_specimen_confirmed": False,
                "frozen_dataset_role_by_base_id": roles.get(base_id(sid), "not_in_rruff371_master_or_301_split" if frozen_checked else "unknown_not_checked"),
                "audit_issue_codes": [],
            }
            trace_hash = ""
            if len(raw_names) == 1:
                raw_text, raw_bytes = _member_text(raw_zf, raw_names[0])
                header = _header(raw_text)
                xs, ys = _numeric_xy(raw_text)
                trace_hash = _trace_digest(xs, ys) if len(xs) >= 2 else ""
                valid_xy = len(xs) >= 100 and all(b > a for a, b in zip(xs, xs[1:])) and max(ys, default=0) > min(ys, default=0)
                record.update({
                    "sample_name": header.get("NAMES", raw_names[0].split("__", 1)[0]),
                    "ideal_chemistry": header.get("IDEAL CHEMISTRY", ""),
                    "measured_chemistry": header.get("MEASURED CHEMISTRY", ""),
                    "sample_description": header.get("DIFFRACTION SAMPLE DESCRIPTION", ""),
                    "mixture_or_contamination_caveat": any(token in header.get("DIFFRACTION SAMPLE DESCRIPTION", "").casefold() for token in ("mixture", "contamination", "two phase", "two-phase")),
                    "raw_member_sha256": sha256_bytes(raw_bytes),
                    "raw_profile_sha256_numeric_trace": trace_hash,
                    "raw_parse_status": "valid" if valid_xy else "invalid_monotonic_or_constant_or_short",
                    "raw_valid_powder_profile": valid_xy and header.get("DIFFRACTION SAMPLE DESCRIPTION", "").casefold().startswith("powder"),
                    "raw_cell_header_present_not_used_for_fit": "CELL PARAMETERS" in header,
                    "two_theta_min_deg": min(xs) if xs else None,
                    "two_theta_max_deg": max(xs) if xs else None,
                    "raw_point_count": len(xs),
                })
                if trace_hash:
                    duplicate_ids = sorted(trace_ids.get(trace_hash, set()))
                    record["duplicate_trace_exact_ids_archivewide"] = "|".join(duplicate_ids)
                    record["duplicate_trace_member_count_archivewide"] = trace_member_counts.get(trace_hash, 0)
            elif not raw_names:
                record["audit_issue_codes"].append("RAW_XY_MISSING")
            else:
                record["audit_issue_codes"].append("RAW_XY_MULTIPLE_MEMBERS_SAME_EXACT_ID")

            out_names = out_index.get(sid, [])
            if len(out_names) == 1:
                out_text, out_bytes = _member_text(out_zf, out_names[0])
                parsed = parse_refinement_output(out_text)
                record.update({
                    "refinement_output_member": out_names[0],
                    "refinement_output_member_sha256": sha256_bytes(out_bytes),
                    "refinement_parse_status": "complete_six" if parsed["complete_six"] else "incomplete_six",
                    "refinement_system": parsed["reported_symmetry"],
                    "wavelengths_from_refinement_angstrom": "|".join(f"{x:.6f}" for x in parsed["wavelengths"]),
                    "machine_error_deg": parsed["machine_error_deg"],
                    "refinement_rmse_raw_units": parsed["rmse_raw"],
                })
                for key, out_key in (("a", "a_angstrom"), ("b", "b_angstrom"), ("c", "c_angstrom"),
                                     ("alpha", "alpha_deg"), ("beta", "beta_deg"), ("gamma", "gamma_deg")):
                    val = parsed["cell"].get(key, {})
                    record[out_key] = val.get("value")
                    record[f"{out_key.removesuffix('_deg').removesuffix('_angstrom')}_esd_{'deg' if key in {'alpha','beta','gamma'} else 'angstrom'}"] = val.get("esd")
                if not parsed["complete_six"]:
                    record["audit_issue_codes"].append("REFINEMENT_CELL_INCOMPLETE")
                record["lattice_esd_triplet_present"] = all(parsed["cell"].get(k, {}).get("esd") is not None for k in ("a", "b", "c"))
                record["angles_symmetry_fixed_without_esd"] = all(parsed["cell"].get(k, {}).get("esd") is None and parsed["cell"].get(k, {}).get("value") == 90.0 for k in ("alpha", "beta", "gamma"))
            elif not out_names:
                record["audit_issue_codes"].append("REFINEMENT_OUTPUT_MISSING_EXACT_ID")
            else:
                record["audit_issue_codes"].append("REFINEMENT_OUTPUT_MULTIPLE_EXACT_ID")

            data_names = refine_index.get(sid, [])
            if len(data_names) == 1:
                text, _ = _member_text(refine_zf, data_names[0])
                _, peak_count, data_wavelengths, wave_index_counts = parse_refinement_data(text)
                record["refinement_data_member"] = data_names[0]
                record["indexed_reflection_rows"] = peak_count
                record["refinement_data_wavelengths_angstrom"] = "|".join(f"{v:.6f}" for v in data_wavelengths)
                record["indexed_wavelength_index_counts"] = "|".join(f"{k}:{v}" for k, v in wave_index_counts.items())
            elif not data_names:
                record["audit_issue_codes"].append("REFINEMENT_DATA_MISSING_EXACT_ID")

            dif_names = dif_index.get(sid, [])
            if len(dif_names) == 1:
                dif_text, dif_bytes = _member_text(dif_zf, dif_names[0])
                sg = re.search(r"SPACE GROUP:\s*([^\r\n]+)", dif_text, re.I)
                cell = re.search(r"CELL PARAMETERS:\s*([^\r\n]+)", dif_text, re.I)
                wave = re.search(rf"X-RAY WAVELENGTH:\s*({NUMBER})", dif_text, re.I)
                record.update({
                    "dif_member": dif_names[0],
                    "dif_member_sha256": sha256_bytes(dif_bytes),
                    "dif_space_group": sg.group(1).strip() if sg else "",
                    "dif_cell_parameters": cell.group(1).strip() if cell else "",
                    "dif_xray_wavelength_angstrom": float(wave.group(1)) if wave else None,
                })
            elif not dif_names:
                record["audit_issue_codes"].append("DIF_MISSING_EXACT_ID")

            mineral = str(record["sample_name"])
            cif_candidates, selected_cif = _find_cif_candidates(cif_zf, mineral, record["a_angstrom"], str(record["ideal_chemistry"]))
            compatible = [c for c in cif_candidates if c["crystal_system"] in {"cubic", "cubic_geometry"} and not c["ideal_formula_element_missing_from_cif"]]
            record["cif_exact_name_candidate_count"] = len(cif_candidates)
            record["cif_compatible_candidate_count"] = len(compatible)
            if selected_cif:
                observed_elements = element_symbols(str(record["measured_chemistry"]))
                template_elements = set(selected_cif["formula_element_symbols"])
                record.update({
                    "cif_selected_reference_member": selected_cif["member"],
                    "cif_selected_database_code": selected_cif["database_code"],
                    "cif_selected_sha256": selected_cif["sha256"],
                    "cif_selected_formula": selected_cif["formula"],
                    "cif_selected_cell_a_angstrom": selected_cif["cell_a_angstrom"],
                    "cif_template_delta_vs_sample_label_angstrom": selected_cif["cell_delta_from_refined_a_angstrom"],
                    "cif_template_system": selected_cif["crystal_system"],
                    "cif_measured_elements_missing_from_template": "|".join(sorted(observed_elements - template_elements)),
                })
            else:
                record["audit_issue_codes"].append("NO_COMPATIBLE_AMCSD_CIF_CANDIDATE")

            if len(record["related_exact_ids_same_base"].split("|")) > 1:
                record["audit_issue_codes"].append("RELATED_SUBNUMBERED_RECORDS_SHARE_BASE_ID")
            if int(record["duplicate_trace_member_count_archivewide"]) > 1 or len(str(record["duplicate_trace_exact_ids_archivewide"]).split("|")) > 1:
                record["audit_issue_codes"].append("EXACT_NUMERIC_TRACE_DUPLICATE_POSSIBLE_LEAKAGE")
            if not record["frozen_dataset_role_by_base_id"].startswith("not_in_"):
                if record["frozen_dataset_role_by_base_id"] == "unknown_not_checked":
                    record["audit_issue_codes"].append("FROZEN_BOUNDARY_NOT_CHECKED")
                else:
                    record["audit_issue_codes"].append("EXCLUDE_FROM_NEW_DEVELOPMENT_FROZEN_OR_PRIOR_BENCHMARK")
            if record["mixture_or_contamination_caveat"]:
                record["audit_issue_codes"].append("MULTIPHASE_OR_CONTAMINATION_CAVEAT_IN_RAW_DESCRIPTION")
            if not record["sample_description"].casefold().startswith("powder"):
                record["audit_issue_codes"].append("SAMPLE_DESCRIPTION_NOT_POWDER_OR_UNKNOWN")
            record["audit_issue_codes"] = sorted(set(record["audit_issue_codes"]))
            record["cif_identity_is_same_specimen_confirmed"] = False
            rows.append(record)

    archive_meta = {}
    for name, path in paths.items():
        archive_meta[name] = {"sha256": sha256_bytes(path.read_bytes()), "source_url": ARCHIVE_URLS[name], "bytes": path.stat().st_size}
    unique = {row["rruff_sample_id"]: row for row in rows}
    if len(unique) != len(rows):
        raise ValueError("scope contains duplicate exact RRUFF IDs")
    frozen_sources = {}
    for label, path in (("rruff371_master_manifest", frozen_manifest), ("rruff301_adaptation_test_split", frozen_split)):
        frozen_sources[label] = ({"filename": path.name, "sha256": sha256_bytes(path.read_bytes())}
                                 if path and path.is_file() else {"status": "not_provided_or_missing"})
    summary = {
        "audit_date": date.today().isoformat(),
        "audit_type": "independent row-level reparse from official RRUFF and AMCSD archives",
        "scope_count": len(rows),
        "unique_exact_sample_ids": len(unique),
        "raw_members_found": sum(bool(r["raw_member_sha256"]) for r in rows),
        "valid_powder_profiles": sum(bool(r["raw_valid_powder_profile"]) for r in rows),
        "complete_refinement_cells_six": sum(r["refinement_parse_status"] == "complete_six" for r in rows),
        "complete_lattice_parameter_esd_triplets_abc": sum(bool(r["lattice_esd_triplet_present"]) for r in rows),
        "symmetry_fixed_90_degree_angles_without_esd": sum(bool(r["angles_symmetry_fixed_without_esd"]) for r in rows),
        "compatible_name_symmetry_ideal_formula_cif_candidates": sum(int(r["cif_compatible_candidate_count"]) > 0 for r in rows),
        "same_specimen_cif_matches_confirmed": 0,
        "records_with_exact_trace_duplicates": sum("EXACT_NUMERIC_TRACE_DUPLICATE_POSSIBLE_LEAKAGE" in r["audit_issue_codes"] for r in rows),
        "records_with_related_subnumbered_ids": sum("RELATED_SUBNUMBERED_RECORDS_SHARE_BASE_ID" in r["audit_issue_codes"] for r in rows),
        "frozen_or_prior_benchmark_overlap_by_base_id": sum("EXCLUDE_FROM_NEW_DEVELOPMENT_FROZEN_OR_PRIOR_BENCHMARK" in r["audit_issue_codes"] for r in rows),
        "independent_for_new_development": (sum(r["frozen_dataset_role_by_base_id"].startswith("not_in_") for r in rows) if frozen_checked else None),
        "frozen_boundary_check_status": "complete_by_base_id" if frozen_checked else "not_checked",
        "frozen_boundary_sources": frozen_sources,
        "distinct_mineral_names": sorted({r["sample_name"] for r in rows if r["sample_name"]}),
        "samples_by_mineral": dict(sorted(Counter(r["sample_name"] for r in rows if r["sample_name"]).items())),
        "cubic_refinement_system_counts": dict(sorted(Counter(r["refinement_system"] for r in rows if r["refinement_system"]).items())),
        "refined_a_range_angstrom": [min(float(r["a_angstrom"]) for r in rows if r["a_angstrom"] is not None),
                                     max(float(r["a_angstrom"]) for r in rows if r["a_angstrom"] is not None)],
        "raw_point_count_distribution": dict(sorted(Counter(str(r["raw_point_count"]) for r in rows).items())),
        "raw_angle_range_distribution_deg": dict(sorted(Counter(f"{r['two_theta_min_deg']}..{r['two_theta_max_deg']}" for r in rows).items())),
        "raw_header_contains_cell_values_not_for_model_input": sum(bool(r["raw_cell_header_present_not_used_for_fit"]) for r in rows),
        "mixture_or_contamination_ids": [r["rruff_sample_id"] for r in rows if r["mixture_or_contamination_caveat"]],
        "missing_dif_auxiliary_ids": [r["rruff_sample_id"] for r in rows if not r["dif_member"]],
        "frozen_or_prior_benchmark_ids_and_roles": [{"rruff_sample_id": r["rruff_sample_id"], "role": r["frozen_dataset_role_by_base_id"]}
                                                     for r in rows if not r["frozen_dataset_role_by_base_id"].startswith("not_in_")],
        "independent_grossular_development_ids": [r["rruff_sample_id"] for r in rows
                                                   if r["sample_name"].casefold() == "grossular"
                                                   and r["frozen_dataset_role_by_base_id"].startswith("not_in_")
                                                   and not r["mixture_or_contamination_caveat"]],
        "measured_chemistry_element_set_fully_covered_by_selected_cif": sum(not r["cif_measured_elements_missing_from_template"] for r in rows),
        "measured_chemistry_element_mismatch_counts": dict(sorted(Counter(str(len([x for x in r["cif_measured_elements_missing_from_template"].split("|") if x])) for r in rows).items())),
        "refinement_indexed_wavelength_profile_count_by_index": dict(sorted(Counter(
            int(item.split(":", 1)[0])
            for r in rows for item in r["indexed_wavelength_index_counts"].split("|") if item
        ).items())),
        "refinement_indexed_reflection_row_count_distribution": dict(sorted(Counter(
            item for r in rows for item in r["indexed_wavelength_index_counts"].split("|") if item
        ).items())),
        "all_issue_codes": sorted({issue for r in rows for issue in r["audit_issue_codes"]}),
        "archives": archive_meta,
        "source_semantics": {
            "raw_xy": "Experimental powder profile source; header cell values are not used as model inputs.",
            "refinement_output": "Same-ID powder cell refinement estimates with reported wavelength choices and e.s.d.; reference estimates, not error-free truth.",
            "dif": "Same-ID diffraction record may combine paper structure coordinates with cell parameters refined from the powder pattern; not independent structure ground truth.",
            "amcsd_cif": "Reference crystal structure/template match only; no identity with the experimental RRUFF specimen is established.",
            "wavelength": "XY_RAW has no explicit wavelength field; output/DIF wavelengths are recorded separately and do not prove instrument metadata for the raw profile.",
        },
        "verdict": "REVIEW_REQUIRED" if any(any(code in r["audit_issue_codes"] for code in {"RAW_XY_MISSING", "RAW_XY_MULTIPLE_MEMBERS_SAME_EXACT_ID", "REFINEMENT_CELL_INCOMPLETE", "NO_COMPATIBLE_AMCSD_CIF_CANDIDATE"}) for r in rows) else "PASS_WITH_REPORTED_LIMITATIONS",
    }
    return rows, summary


def write_audit(rows: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "garnet44_independent_review.csv"
    fields = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "|".join(v) if isinstance(v, list) else v for k, v in row.items()})
    (output_dir / "garnet44_independent_review.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True, help="Directory containing the official RRUFF ZIP archives")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path)
    parser.add_argument("--frozen-split", type=Path)
    args = parser.parse_args()
    rows, summary = audit_garnet_archives(args.archive_root, frozen_manifest=args.frozen_manifest, frozen_split=args.frozen_split)
    write_audit(rows, summary, args.output_dir)
    print(json.dumps({k: v for k, v in summary.items() if k not in {"archives", "source_semantics"}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
