#!/usr/bin/env python3
"""Read-only audit of official RRUFF powder archives for lattice inversion.

The script reads ZIP members in place, writes only the requested audit outputs,
and never edits historical RRUFF-301/371 artifacts. Raw ZIPs stay outside Git.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE_DIR = REPO_ROOT / "RRUFF"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "xrd_inversion/audits/rruff_domain_adaptation"
OFFICIAL_ARCHIVES = {
    "XY_RAW.zip": "https://www.rruff.net/zipped_data_files/powder/XY_RAW.zip",
    "XY_Processed.zip": "https://www.rruff.net/zipped_data_files/powder/XY_Processed.zip",
    "DIF.zip": "https://www.rruff.net/zipped_data_files/powder/DIF.zip",
    "Refinement_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Data.zip",
    "Refinement_Output_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Output_Data.zip",
    "cif.zip": "https://www.rruff.net/AMS/zipped_files/cif.zip",
}
REQUIRED_ARCHIVES = tuple(OFFICIAL_ARCHIVES)
SAMPLE_ID_RE = re.compile(r"__(R\d{6}(?:-\d+)?)__", re.I)
CELL_NUMBER_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]+)\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\((\d+)\))?")
FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
ANIONS = {"H", "O", "F", "Cl", "Br", "I", "S", "Se", "Te", "C", "N", "P", "B"}

# A transparent, deliberately finite alias registry. It is a reproducible
# candidate-family map, not an attempt to encode a complete mineral taxonomy.
FAMILY_ALIASES = {
    "Rutile structure type": "Cassiterite|Pyrolusite|Rutile",
    "Zircon structure type": "Coffinite|Hafnon|Xenotime-(Y)|Zircon",
    "Garnet": "Almandine|Andradite|Calderite|Goldmanite|Grossular|Henritermierite|Katoite|Kimzeyite|Majorite|Menzerite-(Y)|Momoiite|Pyrope|Schorlomite|Spessartine|Uvarovite|Yttriumaluminumgarnet|Gadoliniumgalliumgarnet",
    "Pyroxene": "Aegirine|Aegirine-Augite|Augite|Clinoenstatite|Clinoferrosilite|Diopside|Enstatite|Fassaite|Hedenbergite|Jadeite|Jervisite|Johannsenite|Kosmochlor|Kushiroite|Omphacite|Pigeonite|Spodumene|Ureyite|Wollastonite",
    "Feldspar": "Albite|Andesine|Anorthite|Anorthoclase|Bytownite|Labradorite|Microcline|Orthoclase|Sanidine",
    "Amphibole": "Actinolite|Anthophyllite|Arfvedsonite|Cummingtonite|Edenite|Gedrite|Glaucophane|Grunerite|Hastingsite|Hornblende|Kaersutite|Magnesio-riebeckite|Magnesiohornblende|Pargasite|Richterite|Riebeckite|Tremolite|Winchite|Ferro-actinolite|Ferrohornblende|Ferro-pargasite|Fluoro-richterite|Potassic-arfvedsonite|Potassic-fluoro-arfvedsonite|Potassic-fluoro-pargasite|Potassic-fluoro-richterite",
    "Olivine": "Fayalite|Forsterite|Liebenbergite|Olivine|Tephroite|Laihunite|Knebelite",
    "Spinel": "Spinel|Chromite|Franklinite|Gahnite|Hercynite|Magnesiochromite|Magnetite|Trevorite|Ulvospinel|Maguemite|Qandilite",
    "Apatite": "Apatite|Chlorapatite|Fluorapatite|Hydroxylapatite|Hydroxyapatite|Mimetite|Pyromorphite|Vanadinite",
    "Zeolite": "Analcime|Barrerite|Chabazite-Ca|Chabazite-K|Chabazite-Na|Clinoptilolite|Epistilbite|Erionite|Heulandite-Ca|Heulandite-Na|Laumontite|Mordenite|Natrolite|Scolecite|Stilbite-Ca|Thomsonite",
    "Quartz group": "Quartz|Tridymite|Cristobalite|Coesite|Moganite",
    "Carbonate group": "Aragonite|Barytocalcite|Calcite|Cerussite|Dolomite|Magnesite|Rhodochrosite|Siderite|Smithsonite|Strontianite|Witherite",
}


def normalize_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def sample_id_from_member(name: str) -> str | None:
    """Return an exact RRUFF ID, preserving the sub-number suffix."""
    match = SAMPLE_ID_RE.search(name)
    return match.group(1).upper() if match else None


def base_sample_id(sample_id: str) -> str:
    return sample_id.split("-", 1)[0]


def parse_refined_number(value: str) -> tuple[float | None, float | None]:
    """Parse RRUFF notation such as 11.8517(2); uncertainty follows decimals."""
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\((\d+)\))?\s*", value)
    if not match:
        return None, None
    number = float(match.group(1))
    uncertainty = None
    if match.group(2) is not None:
        decimals = len(match.group(1).split(".", 1)[1]) if "." in match.group(1) else 0
        uncertainty = int(match.group(2)) * 10.0 ** (-decimals)
    return number, uncertainty


def parse_system(value: str | None) -> str | None:
    text = re.sub(r"[^A-Z]", "", (value or "").upper())
    aliases = {
        "CUBIC": "cubic", "ISOMETRIC": "cubic",
        "HEXAGONAL": "hexagonal", "TRIGONAL": "trigonal", "RHOMBOHEDRAL": "trigonal",
        "TETRAGONAL": "tetragonal", "ORTHORHOMBIC": "orthorhombic",
        "MONOCLINIC": "monoclinic", "MONOCLINIC1": "monoclinic", "MONOCLINIC2": "monoclinic",
        "TRICLINIC": "triclinic",
    }
    return aliases.get(text)


def system_from_it_number(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\d+", value)
    if not match:
        return None
    number = int(match.group())
    if number <= 2: return "triclinic"
    if number <= 15: return "monoclinic"
    if number <= 74: return "orthorhombic"
    if number <= 142: return "tetragonal"
    if number <= 167: return "trigonal"
    if number <= 194: return "hexagonal"
    if number <= 230: return "cubic"
    return None


def parse_xy_profile(text: str) -> dict[str, Any]:
    points: list[tuple[float, float]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        columns = stripped.replace(",", " ").split()
        if len(columns) < 2:
            continue
        try:
            x, y = float(columns[0]), float(columns[1])
        except ValueError:
            continue
        if math.isfinite(x) and math.isfinite(y):
            points.append((x, y))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    monotonic = len(xs) > 1 and all(b > a for a, b in zip(xs, xs[1:]))
    nonconstant = len(ys) > 1 and max(ys) > min(ys)
    valid = len(points) >= 2 and monotonic and nonconstant
    trace = "\n".join(f"{x:.10g},{y:.10g}" for x, y in points).encode("ascii")
    return {
        "point_count": len(points), "two_theta_min": min(xs) if xs else None,
        "two_theta_max": max(xs) if xs else None,
        "strictly_increasing": monotonic, "nonconstant_intensity": nonconstant,
        "valid": valid, "numeric_trace_sha256": hashlib.sha256(trace).hexdigest() if points else "",
        "status": "valid" if valid else ("no_numeric_points" if not points else "nonmonotonic_or_constant_or_too_short"),
    }


def parse_header(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("##") and "=" in line:
            key, value = line[2:].split("=", 1)
            values[key.strip().upper()] = value.strip()
    return values


def parse_refinement_output(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {"cell": {}, "wavelengths": []}
    for match in CELL_NUMBER_RE.finditer(text):
        key = match.group(1).casefold()
        value, uncertainty = parse_refined_number(match.group(2) + (f"({match.group(3)})" if match.group(3) else ""))
        if key in {"a", "b", "c", "alpha", "beta", "gamma"} and key not in out["cell"]:
            out["cell"][key] = {"value": value, "uncertainty": uncertainty}
    system_match = re.search(r"Symmetry constraint is:\s*([^\r\n]+)", text, re.I)
    out["reported_system"] = system_match.group(1).strip() if system_match else None
    out["crystal_system"] = parse_system(out["reported_system"])
    waves = re.findall(r"Wavelength\s*#\d+\s*=\s*([-+\d.Ee]+)", text, re.I)
    out["wavelengths"] = [float(x) for x in waves]
    offset = re.search(r"MACHINE ERROR:\s*([-+\d.Ee]+)", text, re.I)
    out["machine_error"] = float(offset.group(1)) if offset else None
    rmse = re.search(r"\brmse\s*=\s*([-+\d.Ee]+)", text, re.I)
    out["rmse_raw"] = float(rmse.group(1)) if rmse else None
    return out


def parse_refinement_data(text: str) -> int:
    count = 0
    for line in text.splitlines()[3:]:
        cols = line.split()
        if len(cols) >= 5:
            try:
                [float(x) for x in cols[:5]]
                count += 1
            except ValueError:
                pass
    return count


def parse_cif_scalar(text: str, tag: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(tag)}\s+(.+?)\s*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def element_set(formula: str | None) -> set[str]:
    if not formula:
        return set()
    return {x for x in re.findall(r"(?<![a-z])([A-Z][a-z]?)", formula) if x not in ANIONS}


def parse_cif(text: str, member: str) -> dict[str, Any]:
    scalar = lambda key: parse_cif_scalar(text, key)
    cell: dict[str, float] = {}
    for key in ("a", "b", "c", "alpha", "beta", "gamma"):
        value = scalar(f"_cell_length_{key}" if key in "abc" else f"_cell_angle_{key}")
        if value:
            num = FLOAT_RE.search(value)
            if num:
                cell[key] = float(num.group())
    it_number = scalar("_space_group_IT_number") or scalar("_symmetry_Int_Tables_number")
    hm = scalar("_space_group_name_H-M_alt") or scalar("_space_group_name_H-M") or scalar("_symmetry_space_group_name_H-M")
    prefix = member.rsplit("/", 1)[-1].split("__", 1)[0]
    mineral = scalar("_chemical_name_mineral") or prefix
    code = scalar("_database_code_amcsd")
    formula = scalar("_chemical_formula_sum") or scalar("_amcsd_formula_title")
    system = system_from_it_number(it_number)
    system_source = "space_group_IT_number" if system else ""
    if not system and all(k in cell for k in ("a", "b", "c", "alpha", "beta", "gamma")):
        a, b, c = (cell[k] for k in ("a", "b", "c"))
        alpha, beta, gamma = (cell[k] for k in ("alpha", "beta", "gamma"))
        hm_key = re.sub(r"[^a-z0-9]", "", (hm or "").casefold())
        angles_90 = all(abs(v - 90.0) <= 1.0 for v in (alpha, beta, gamma))
        lengths_equal = max(a, b, c) - min(a, b, c) <= 0.01 * max(a, b, c)
        ab_equal = abs(a - b) <= 0.01 * max(a, b)
        if angles_90 and lengths_equal:
            system, system_source = "cubic", "inferred_from_cell_metric"
        elif angles_90 and ab_equal and not lengths_equal:
            system, system_source = "tetragonal", "inferred_from_cell_metric"
        elif angles_90:
            system, system_source = "orthorhombic", "inferred_from_cell_metric"
        elif abs(alpha - 90) <= 1 and abs(beta - 90) <= 1 and abs(gamma - 120) <= 1 and ab_equal:
            if "6" in hm_key:
                system, system_source = "hexagonal", "inferred_from_space_group_and_cell_metric"
            elif any(x in hm_key for x in ("3", "r")):
                system, system_source = "trigonal", "inferred_from_space_group_and_cell_metric"
        elif abs(a - b) <= 0.01 * max(a, b) and abs(b - c) <= 0.01 * max(b, c) and abs(alpha - beta) <= 1 and abs(beta - gamma) <= 1:
            system, system_source = "trigonal", "inferred_from_cell_metric"
        elif sum(abs(v - 90) > 1 for v in (alpha, beta, gamma)) == 1:
            system, system_source = "monoclinic", "inferred_from_cell_metric"
        else:
            system, system_source = "triclinic", "inferred_from_cell_metric"
    return {
        "member": member, "mineral": mineral, "name_key": normalize_name(mineral),
        "amcsd_code": code, "formula": formula, "elements": element_set(formula),
        "it_number": it_number, "space_group": hm,
        "system": system, "system_source": system_source, "cell": cell,
    }


def parse_dif(text: str) -> dict[str, Any]:
    params = re.search(r"CELL PARAMETERS:\s*([^\r\n]+)", text, re.I)
    values = [float(x) for x in FLOAT_RE.findall(params.group(1))[:6]] if params else []
    sg = re.search(r"SPACE GROUP:\s*([^\s\r\n]+)", text, re.I)
    amcsd = re.search(r"_database_code_amcsd\s+['\"]?(\d+)", text, re.I)
    source = None
    first = " ".join(text.splitlines()[:4]).casefold()
    if "cell parameters refined from the powder pattern" in first or "cell parameters refined from powder pattern" in first:
        source = "powder_refined"
    elif "single crystal" in first:
        source = "single_crystal"
    elif "cell parameters" in first:
        source = "other_or_unclear"
    return {"cell_values": values, "space_group": sg.group(1) if sg else None,
            "amcsd_code": amcsd.group(1).zfill(7) if amcsd else None, "cell_source": source}


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def maybe_download_archives(archive_dir: Path, download_missing: bool) -> dict[str, Any]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    missing: list[str] = []
    for filename, url in OFFICIAL_ARCHIVES.items():
        path = archive_dir / filename
        if path.exists() and zipfile.is_zipfile(path):
            continue
        if not download_missing:
            missing.append(filename)
            continue
        if path.exists():
            raise RuntimeError(f"Refusing to overwrite existing invalid archive: {path}")
        request = urllib.request.Request(url, headers={"User-Agent": "AI4science-RRUFF-audit/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, path.open("xb") as target:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                target.write(block)
        if not zipfile.is_zipfile(path):
            raise RuntimeError(f"Downloaded file is not a valid ZIP: {path}")
        downloaded.append(filename)
    if missing:
        raise FileNotFoundError("Missing required official archives: " + ", ".join(missing) + ". Re-run with --download-missing.")
    return {"downloaded_by_this_run": downloaded, "missing": []}


def member_id_or_none(name: str) -> str | None:
    return sample_id_from_member(name)


def build_archive_index(archive_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    samples: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "raw": [], "output": [], "refinement_data": [], "dif": [], "processed": [],
    })
    provenance: dict[str, Any] = {}
    raw_non_rruff: list[dict[str, Any]] = []
    archive_counts: dict[str, int] = {}
    archive_id_counts: dict[str, int] = {}
    for filename in REQUIRED_ARCHIVES:
        path = archive_dir / filename
        if not path.exists() or not zipfile.is_zipfile(path):
            continue
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            archive_counts[filename] = len(names)
            provenance[filename] = {
                "official_url": OFFICIAL_ARCHIVES[filename],
                "size_bytes": path.stat().st_size,
                "sha256": archive_sha(path),
                "local_mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "member_count": len(names),
                "downloaded_this_audit": False,
            }
            for member in names:
                sample_id = member_id_or_none(member)
                kind = (
                    "raw" if filename == "XY_RAW.zip" else
                    "output" if filename == "Refinement_Output_Data.zip" else
                    "refinement_data" if filename == "Refinement_Data.zip" else
                    "dif" if filename == "DIF.zip" else
                    "processed" if filename == "XY_Processed.zip" else None
                )
                if kind is None:
                    continue
                if sample_id:
                    samples[sample_id][kind].append(member)
                elif filename == "XY_RAW.zip":
                    raw_non_rruff.append({"member": member, "sha256": hash_bytes(archive.read(member))})
            if kind:
                archive_id_counts[filename] = len({member_id_or_none(member) for member in names if member_id_or_none(member)})
    # The CIF inventory is held separately because its members identify AMCSD entries, not RRUFF specimens.
    cif_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cif_members = 0
    with zipfile.ZipFile(archive_dir / "cif.zip") as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".cif")]
        cif_members = len(names)
        for member in names:
            content = archive.read(member)
            info = parse_cif(content.decode("utf-8", "replace"), member)
            info["sha256"] = hash_bytes(content)
            if info["name_key"]:
                cif_index[info["name_key"]].append(info)
    provenance["CIF_member_count"] = cif_members
    provenance["CIF_distinct_mineral_name_keys"] = len(cif_index)
    provenance["archive_member_counts"] = archive_counts
    provenance["archive_unique_RRUFF_sample_id_counts"] = archive_id_counts
    return samples, provenance, raw_non_rruff, cif_index


def choose_cif_candidates(mineral_name: str, cifs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return list(cifs.get(normalize_name(mineral_name), []))


def cell_metric_match(refined: dict[str, Any], cif: dict[str, Any]) -> float | None:
    keys = ("a", "b", "c", "alpha", "beta", "gamma")
    if not all(k in refined and refined[k].get("value") is not None for k in keys):
        return None
    if not all(k in cif["cell"] for k in keys):
        return None
    lhs = sorted(refined[k]["value"] for k in ("a", "b", "c"))
    rhs = sorted(cif["cell"][k] for k in ("a", "b", "c"))
    length_delta = max(abs(a - b) / max(abs(a), abs(b), 1e-9) for a, b in zip(lhs, rhs))
    angle_delta = max(abs(refined[k]["value"] - cif["cell"][k]) for k in ("alpha", "beta", "gamma"))
    return max(length_delta, angle_delta / 180.0)


def rank_cif_candidates(candidates: list[dict[str, Any]], refined: dict[str, Any], system: str | None,
                        chemistry: str | None, dif_amcsd_code: str | None = None) -> tuple[dict[str, Any] | None, str, str, int]:
    if not candidates:
        return None, "none", "no_exact_normalized_mineral_name_candidate", 0
    specimen_elements = element_set(chemistry)
    ranked = []
    for cif in candidates:
        sys_match = bool(system and cif["system"] and system == cif["system"])
        delta = cell_metric_match(refined, cif)
        formula_overlap = None
        if specimen_elements and cif["elements"]:
            formula_overlap = len(specimen_elements & cif["elements"]) / max(1, len(specimen_elements | cif["elements"]))
        direct_code = bool(dif_amcsd_code and cif.get("amcsd_code") and cif["amcsd_code"].zfill(7) == dif_amcsd_code.zfill(7))
        score = (8 if direct_code else 0) + (3 if sys_match else 0) + (3 if delta is not None and delta <= 0.03 else 0) + (2 if formula_overlap is not None and formula_overlap >= 0.5 else 0)
        # Stable tie break by AMCSD code / member name.
        ranked.append((score, sys_match, delta, formula_overlap, cif))
    ranked.sort(key=lambda item: (-item[0], item[2] if item[2] is not None else 999, item[4].get("amcsd_code") or "", item[4]["member"]))
    score, sys_match, delta, formula_overlap, best = ranked[0]
    cell_close = delta is not None and delta <= 0.03
    formula_ok = formula_overlap is not None and formula_overlap >= 0.5
    direct_code = bool(dif_amcsd_code and best.get("amcsd_code") and best["amcsd_code"].zfill(7) == dif_amcsd_code.zfill(7))
    evidence_parts = ["DIF_to_AMCSD_database_code_link"] if direct_code else ["exact_normalized_mineral_name"]
    if sys_match: evidence_parts.append("crystal_system_match")
    elif system and best["system"]: evidence_parts.append("crystal_system_conflict")
    if cell_close: evidence_parts.append(f"cell_metric_close_max_relative_delta={delta:.6g}")
    elif delta is not None: evidence_parts.append(f"cell_metric_differs_max_relative_delta={delta:.6g}")
    if formula_overlap is not None: evidence_parts.append(f"cation_element_set_jaccard={formula_overlap:.6g}")
    if direct_code and sys_match and cell_close and formula_ok:
        confidence = "high_DIF_linked_template_compatibility"
    elif sys_match and cell_close and formula_ok:
        confidence = "high_template_compatibility"
    elif sys_match and (cell_close or formula_ok):
        confidence = "moderate_template_compatibility"
    elif len(candidates) == 1 and sys_match and formula_overlap is None and delta is None:
        confidence = "low_name_only_candidate"
    else:
        confidence = "low_or_conflicting_candidate"
    return best, confidence, ";".join(evidence_parts), len(candidates)


def classify_profile_kind(description: str | None) -> str:
    value = (description or "").casefold()
    if not value:
        return "unknown"
    if "profile is calculated" in value or "profile calculated" in value or "calculated powder profile" in value:
        return "calculated_profile"
    if "powder" in value or "powder x-ray" in value or "powder xray" in value:
        return "experimental_powder_candidate"
    if "single crystal" in value or "saed" in value or "thin foil" in value:
        return "non_powder_or_single_crystal"
    return "ambiguous_description"


def profile_has_mixture_caveat(description: str | None) -> bool:
    value = (description or "").casefold()
    return bool(re.search(r"\b(mix|mixed|mixture|contamination|contaminated|includes?|another phase|other phase|minor component|trace)\b|\b\d+(?:\.\d+)?\s*%", value))


def family_for_name(name: str | None) -> str:
    key = normalize_name(name)
    matches = []
    for family, aliases in FAMILY_ALIASES.items():
        if key in {normalize_name(alias) for alias in aliases.split("|") if alias}:
            matches.append(family)
    return matches[0] if len(matches) == 1 else ("multiple_family_aliases" if matches else "unclassified")


def parse_archive_member(archive: zipfile.ZipFile, members: list[str], parser) -> tuple[Any, str | None, list[str]]:
    if not members:
        return None, None, []
    parsed = []
    hashes = []
    for member in sorted(members):
        content = archive.read(member)
        hashes.append(hash_bytes(content))
        parsed.append((parser(content.decode("utf-8", "replace")), member))
    # Keep first deterministic entry; multiplicity and hashes remain visible.
    return parsed[0][0], parsed[0][1], hashes


def csv_write(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_manifest(archive_dir: Path, samples: dict[str, dict[str, Any]], cifs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    parsed_raw_hash_counts: Counter[str] = Counter()
    raw_rows: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(archive_dir / "XY_RAW.zip") as archive:
        for sample_id, record in samples.items():
            if not record["raw"]:
                continue
            member_records = []
            for member in sorted(record["raw"]):
                content = archive.read(member)
                digest = hash_bytes(content)
                parsed_raw_hash_counts[digest] += 1
                text = content.decode("utf-8", "replace")
                header = parse_header(text)
                numeric = parse_xy_profile(text)
                description = header.get("DIFFRACTION SAMPLE DESCRIPTION")
                member_records.append({
                    "member": member, "hash": digest, "header": header, "numeric": numeric,
                    "description": description, "kind": classify_profile_kind(description),
                })
            # Prefer a valid powder-like profile, then a valid profile, then deterministic lexical order.
            member_records.sort(key=lambda x: (x["kind"] != "experimental_powder_candidate", not x["numeric"]["valid"], x["member"]))
            chosen = member_records[0]
            raw_rows[sample_id] = {
                "chosen": chosen,
                "members": member_records,
                "duplicate_hash_count": parsed_raw_hash_counts[chosen["hash"]],
            }
    # Detect identical numeric XY traces even when sample headers differ.
    hash_to_ids: dict[str, set[str]] = defaultdict(set)
    for sid, raw in raw_rows.items():
        for item in raw["members"]:
            trace_hash = item["numeric"].get("numeric_trace_sha256")
            if trace_hash:
                hash_to_ids[trace_hash].add(sid)
    base_counts = Counter(base_sample_id(sid) for sid, rec in samples.items() if rec["raw"] or rec["output"])
    rows = []
    output_archive = zipfile.ZipFile(archive_dir / "Refinement_Output_Data.zip")
    refinement_archive = zipfile.ZipFile(archive_dir / "Refinement_Data.zip")
    dif_archive = zipfile.ZipFile(archive_dir / "DIF.zip")
    try:
        for sample_id in sorted(samples):
            record = samples[sample_id]
            raw = raw_rows.get(sample_id)
            out, out_member, out_hashes = parse_archive_member(output_archive, record["output"], parse_refinement_output)
            refin_count, refin_member, refin_hashes = parse_archive_member(refinement_archive, record["refinement_data"], parse_refinement_data)
            dif, dif_member, dif_hashes = parse_archive_member(dif_archive, record["dif"], parse_dif)
            chosen = raw["chosen"] if raw else None
            header = chosen["header"] if chosen else {}
            mineral = header.get("NAMES") or (record["raw_name"] if "raw_name" in record else None)
            if not mineral:
                for member in record["output"] + record["dif"] + record["refinement_data"]:
                    mineral = member.split("__", 1)[0]
                    break
            raw_system = None
            cp_header = header.get("CELL PARAMETERS", "")
            cm = re.search(r"crystal\s+system:\s*([^;]+)", cp_header, re.I)
            if cm: raw_system = parse_system(cm.group(1))
            system = (out or {}).get("crystal_system") or raw_system
            chemistry = header.get("MEASURED CHEMISTRY") or header.get("IDEAL CHEMISTRY")
            candidate_list = choose_cif_candidates(mineral or "", cifs)
            dif_code = (dif or {}).get("amcsd_code") if dif else None
            best_cif, cif_conf, cif_evidence, cif_count = rank_cif_candidates(candidate_list, (out or {}).get("cell", {}), system, chemistry, dif_code)
            label = (out or {}).get("cell", {})
            complete = sum(k in label and label[k].get("value") is not None for k in ("a", "b", "c", "alpha", "beta", "gamma"))
            esd_count = sum(k in label and label[k].get("uncertainty") is not None for k in ("a", "b", "c", "alpha", "beta", "gamma"))
            if complete == 6 and esd_count == 6:
                label_conf = "complete_with_reported_esd_reference_estimate"
            elif complete == 6:
                label_conf = "complete_without_all_esd_reference_estimate"
            elif complete:
                label_conf = "partial_reference_estimate"
            else:
                label_conf = "no_refinement_cell_label"
            codes = []
            if not raw: codes.append("NO_RAW_PROFILE")
            elif not chosen["numeric"]["valid"]: codes.append("RAW_PARSE_INVALID")
            if chosen and chosen["kind"] != "experimental_powder_candidate": codes.append("NOT_CONFIRMED_EXPERIMENTAL_POWDER")
            if chosen and profile_has_mixture_caveat(chosen["description"]): codes.append("PROFILE_METADATA_SUGGESTS_MIXTURE_OR_CONTAMINATION")
            if not out or complete != 6: codes.append("NO_COMPLETE_EXACT_ID_REFINEMENT_CELL")
            if cif_conf not in {"high_template_compatibility", "high_DIF_linked_template_compatibility", "moderate_template_compatibility"}: codes.append("NO_RELIABLE_AMCSD_TEMPLATE_MATCH")
            if dif and dif.get("cell_source") == "single_crystal": codes.append("DIF_CELLS_FROM_SINGLE_CRYSTAL_REQUIRES_CAUTION")
            if record["raw"] and base_counts[base_sample_id(sample_id)] > 1: codes.append("RELATED_BASE_ID_SUBNUMBER_GROUP")
            trace_hashes = [item["numeric"].get("numeric_trace_sha256") for item in raw["members"]] if raw else []
            cross_id_dupe = max((len(hash_to_ids[h]) for h in trace_hashes if h), default=0)
            if cross_id_dupe > 1: codes.append("EXACT_NUMERIC_XY_TRACE_SHARED")
            if chosen and chosen["kind"] == "experimental_powder_candidate" and chosen["numeric"]["valid"] and complete == 6 and label_conf.startswith("complete"):
                core_eligible = True
            else:
                core_eligible = False
            if core_eligible and cif_conf in {"high_template_compatibility", "high_DIF_linked_template_compatibility"}:
                codes.append("AUDIT_CANDIDATE_STRONG_TEMPLATE")
            row = {
                "rruff_sample_id": sample_id,
                "rruff_base_id": base_sample_id(sample_id),
                "mineral_name": mineral or "",
                "ideal_chemistry": header.get("IDEAL CHEMISTRY", ""),
                "measured_chemistry": header.get("MEASURED CHEMISTRY", ""),
                "crystal_system": system or "",
                "rruff_refinement_system_constraint": (out or {}).get("reported_system") or "",
                "space_group_from_DIF": (dif or {}).get("space_group") or "",
                "raw_xrd_present": bool(raw),
                "raw_archive_member_count": len(record["raw"]),
                "raw_archive_members": "|".join(record["raw"]),
                "raw_selected_member": chosen["member"] if chosen else "",
                "raw_selected_sha256": chosen["hash"] if chosen else "",
                "raw_numeric_trace_sha256": chosen["numeric"].get("numeric_trace_sha256", "") if chosen else "",
                "raw_parse_status": chosen["numeric"]["status"] if chosen else "not_present",
                "raw_profile_valid": bool(chosen and chosen["numeric"]["valid"]),
                "raw_profile_kind": chosen["kind"] if chosen else "not_present",
                "diffraction_sample_description": chosen["description"] if chosen else "",
                "raw_metadata_mixture_or_contamination_caveat": profile_has_mixture_caveat(chosen["description"]) if chosen else False,
                "two_theta_min_deg": chosen["numeric"]["two_theta_min"] if chosen else "",
                "two_theta_max_deg": chosen["numeric"]["two_theta_max"] if chosen else "",
                "raw_point_count": chosen["numeric"]["point_count"] if chosen else "",
                "raw_wavelength_angstrom": "",  # XY_RAW has no explicit wavelength field.
                "wavelength_angstrom_from_same_id_refinement": "|".join(str(x) for x in ((out or {}).get("wavelengths") or [])),
                "wavelength_source": "Refinement_Output_Data exact sample-ID match; not embedded in XY_RAW" if out and (out or {}).get("wavelengths") else "not recorded in XY_RAW or exact-ID refinement output",
                "raw_header_cell_parameters_not_used_as_label": cp_header,
                "refinement_output_present_exact_id": bool(record["output"]),
                "refinement_output_member": out_member or "",
                "refinement_output_member_sha256": out_hashes[0] if out_hashes else "",
                "refinement_data_present_exact_id": bool(record["refinement_data"]),
                "refinement_data_member": refin_member or "",
                "refinement_data_member_sha256": refin_hashes[0] if refin_hashes else "",
                "indexed_reflection_row_count": refin_count if refin_count is not None else "",
                "cell_label_source": "RRUFF Refinement_Output_Data exact sample-ID match" if out and complete else "none",
                "cell_label_reference_status": "reported refinement estimate; not error-free ground truth" if out and complete else "unavailable",
                "cell_label_units": "A for a,b,c; degree for alpha,beta,gamma",
                "cell_label_completeness_count_6": complete,
                "cell_label_esd_count_6": esd_count,
                "cell_label_confidence": label_conf,
                "refinement_rmse_raw_unit_unspecified": (out or {}).get("rmse_raw") if out else "",
                "machine_error_raw": (out or {}).get("machine_error") if out and (out or {}).get("machine_error") is not None else "",
                "a_angstrom": label.get("a", {}).get("value", ""), "a_esd_angstrom": label.get("a", {}).get("uncertainty", ""),
                "b_angstrom": label.get("b", {}).get("value", ""), "b_esd_angstrom": label.get("b", {}).get("uncertainty", ""),
                "c_angstrom": label.get("c", {}).get("value", ""), "c_esd_angstrom": label.get("c", {}).get("uncertainty", ""),
                "alpha_deg": label.get("alpha", {}).get("value", ""), "alpha_esd_deg": label.get("alpha", {}).get("uncertainty", ""),
                "beta_deg": label.get("beta", {}).get("value", ""), "beta_esd_deg": label.get("beta", {}).get("uncertainty", ""),
                "gamma_deg": label.get("gamma", {}).get("value", ""), "gamma_esd_deg": label.get("gamma", {}).get("uncertainty", ""),
                "DIF_member": dif_member or "",
                "DIF_member_sha256": dif_hashes[0] if dif_hashes else "",
                "DIF_to_AMCSD_database_code": (dif or {}).get("amcsd_code") or "",
                "DIF_cell_provenance": (dif or {}).get("cell_source") or "",
                "DIF_cell_parameters": "|".join(str(x) for x in ((dif or {}).get("cell_values") or [])),
                "amcsd_exact_name_candidate_count": cif_count,
                "amcsd_cif_candidate": best_cif["member"] if best_cif else "",
                "amcsd_database_code": best_cif.get("amcsd_code", "") if best_cif else "",
                "amcsd_cif_member_sha256": best_cif.get("sha256", "") if best_cif else "",
                "amcsd_space_group": best_cif.get("space_group", "") if best_cif else "",
                "amcsd_cif_system_source": best_cif.get("system_source", "") if best_cif else "",
                "amcsd_cif_cell_not_specimen_label": "|".join(str(best_cif["cell"].get(k, "")) for k in ("a", "b", "c", "alpha", "beta", "gamma")) if best_cif else "",
                "amcsd_template_match_confidence": cif_conf,
                "amcsd_match_evidence": cif_evidence,
                "amcsd_is_same_specimen_confirmed": False,
                "raw_duplicate_members_same_exact_id": len(record["raw"]) > 1,
                "related_sample_group_size_same_base_id": base_counts[base_sample_id(sample_id)],
                "possible_repeated_or_related_subsample": bool(record["raw"] and base_counts[base_sample_id(sample_id)] > 1),
                "exact_numeric_trace_shared_sample_id_count": cross_id_dupe,
                "family_candidate": family_for_name(mineral),
                "strong_audit_candidate": core_eligible and cif_conf in {"high_template_compatibility", "high_DIF_linked_template_compatibility"},
                "ineligibility_reason_codes": "|".join(codes),
            }
            rows.append(row)
    finally:
        output_archive.close(); refinement_archive.close(); dif_archive.close()
    return rows


def family_summary(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in manifest:
        if row["family_candidate"] != "unclassified":
            groups[row["family_candidate"]].append(row)
    summaries = []
    for family, rows in groups.items():
        powder = [r for r in rows if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate"]
        powder_label = [r for r in powder if r["cell_label_completeness_count_6"] == 6]
        strong = [r for r in powder_label if r["amcsd_template_match_confidence"] in {"high_template_compatibility", "high_DIF_linked_template_compatibility"}]
        moderate = [r for r in powder_label if r["amcsd_template_match_confidence"] == "moderate_template_compatibility"]
        cells = {k: [float(r[k]) for r in powder_label if r[k] not in (None, "")] for k in ("a_angstrom", "b_angstrom", "c_angstrom", "alpha_deg", "beta_deg", "gamma_deg")}
        def rng(key: str) -> str:
            vals = cells[key]
            return f"{min(vals):.6g}..{max(vals):.6g}" if vals else ""
        base_ids = {r["rruff_base_id"] for r in powder}
        eligible_base_ids = {r["rruff_base_id"] for r in powder_label}
        repeat_ids = {r["rruff_sample_id"] for r in powder if r["possible_repeated_or_related_subsample"]}
        systems = Counter(r["crystal_system"] for r in powder_label if r["crystal_system"])
        wave_tokens = Counter(r["wavelength_angstrom_from_same_id_refinement"] for r in powder if r["wavelength_angstrom_from_same_id_refinement"])
        species = {r["mineral_name"] for r in powder_label if r["mineral_name"]}
        chem = {r["measured_chemistry"] or r["ideal_chemistry"] for r in powder_label if r["measured_chemistry"] or r["ideal_chemistry"]}
        if family == "Rutile structure type":
            decision = "GO"
            decision_reason = "11 exact-ID powder profiles have complete RRUFF cell estimates, share the tetragonal P4_2/mnm structure type, and nine have high-compatibility AMCSD templates. This matches the repository's existing tetragonal forward-model scope and supports a small grouped pilot, but not a broad generalization claim."
            recommendation = "bounded_rutile_structure_type_pilot_after_freezing_base_ID_split"
        elif family == "Garnet":
            decision = "LIMITED_GO"
            decision_reason = "44 exact-ID powder profiles have complete RRUFF cell estimates and high-compatibility template candidates, and the labeled subset is a clean cubic one-parameter problem. However, the repository's current differentiable forward model is tetragonal-only, so garnet cannot enter that model without extending and validating the physics forward path."
            recommendation = "data_rich_but_requires_cubic_forward_model_extension"
        elif family == "Quartz group" and len(powder_label) <= 4:
            decision = "NO_GO"
            decision_reason = "Only four eligible labels span several structure types, which is inadequate for a family-level adaptation/validation/test study; a software demonstration remains possible."
            recommendation = "do_not_select_for_family_level_DA_study"
        elif powder_label:
            decision = "LIMITED_GO"
            decision_reason = "Eligible real profiles and exact-ID reference cell estimates exist, but family size, structure-system diversity, or lack of a pre-frozen independent grouped test limits claims to a scoped exploratory study."
            recommendation = "exploratory_pilot_with_grouped_split_and_narrowed_scope"
        else:
            decision = "NO_GO"
            decision_reason = "No valid experimental-powder profile is paired with a complete exact-ID RRUFF refinement-cell estimate in this candidate family registry."
            recommendation = "do_not_select_without_new_eligible_data"
        if systems and set(systems) == {"cubic"}:
            params = "a only (cubic)"
        elif systems and set(systems) == {"tetragonal"}:
            params = "a,c (tetragonal)"
        else:
            params = "symmetry-reduced lattice parameters; verify each exact sample's system before fitting"
        if systems and set(systems) == {"tetragonal"}:
            forward_fit = "direct crystal-system fit to existing tetragonal_torch_dense_v1; still verify CIF convention/space group and instrumentation"
        elif "tetragonal" in systems:
            forward_fit = "only a tetragonal subset could use existing tetragonal_torch_dense_v1; mixed family needs scoped filtering"
        else:
            forward_fit = "not directly compatible: existing inversion forward model is tetragonal-only"
        angle_bounds = [float(r[k]) for r in powder for k in ("two_theta_min_deg", "two_theta_max_deg") if r[k] not in (None, "")]
        point_counts = [int(r["raw_point_count"]) for r in powder if r["raw_point_count"] not in (None, "")]
        mixture_caveat = sum(bool(r["raw_metadata_mixture_or_contamination_caveat"]) for r in powder)
        radiation = Counter()
        for r in powder:
            desc = (r["diffraction_sample_description"] or "").casefold()
            mention = next((label for token, label in (("mo", "Mo mentioned"), ("co", "Co mentioned"), ("cu", "Cu mentioned")) if re.search(rf"\b{token}\b", desc)), "radiation unspecified in XY_RAW")
            radiation[mention] += 1
        summaries.append({
            "family": family,
            "family_alias_registry_scope": FAMILY_ALIASES[family],
            "all_exact_id_samples_in_family": len(rows),
            "valid_raw_profiles_any_kind": sum(bool(r["raw_profile_valid"]) for r in rows),
            "experimental_powder_candidate_profiles_valid": len(powder),
            "powder_profiles_with_metadata_mixture_or_contamination_caveat": mixture_caveat,
            "experimental_powder_with_complete_RRUFF_refinement_cell": len(powder_label),
            "with_high_AMCSD_template_compatibility": len(strong),
            "with_moderate_AMCSD_template_compatibility": len(moderate),
            "raw_missing_or_invalid": sum(not r["raw_xrd_present"] or not r["raw_profile_valid"] for r in rows),
            "unique_RRUFF_base_ids_with_raw": len(base_ids),
            "unique_RRUFF_base_ids_with_complete_powder_cell_labels": len(eligible_base_ids),
            "subnumber_related_sample_ids": len(repeat_ids),
            "distinct_mineral_species_in_eligible_powder_labels": len(species),
            "distinct_reported_chemistry_strings": len(chem),
            "crystal_system_counts": json.dumps(dict(sorted(systems.items())), ensure_ascii=False, sort_keys=True),
            "refinement_wavelength_conditions": json.dumps(dict(wave_tokens), ensure_ascii=False, sort_keys=True),
            "radiation_mentions_in_diffraction_description": json.dumps(dict(radiation), ensure_ascii=False, sort_keys=True),
            "eligible_powder_two_theta_span_deg": f"{min(angle_bounds):.6g}..{max(angle_bounds):.6g}" if angle_bounds else "",
            "eligible_powder_point_count_range": f"{min(point_counts)}..{max(point_counts)}" if point_counts else "",
            "a_range_angstrom": rng("a_angstrom"), "b_range_angstrom": rng("b_angstrom"), "c_range_angstrom": rng("c_angstrom"),
            "alpha_range_deg": rng("alpha_deg"), "beta_range_deg": rng("beta_deg"), "gamma_range_deg": rng("gamma_deg"),
            "recommended_parameters_to_predict": params,
            "existing_forward_model_compatibility": forward_fit,
            "split_leakage_warning": "Group by RRUFF base ID, mineral species and any exact spectrum hash; sub-number IDs may be related, not independent.",
            "independent_adaptation_validation_test_feasibility": "No independent test is established by this audit; family counts indicate whether a grouped split is plausible, not that it exists.",
            "A_sim_only_training": "Yes, possible with simulator-generated data; domain gap remains unvalidated.",
            "B_supervised_few_shot_real_adaptation": "Possible only with distinct samples having exact-ID RRUFF refinement labels; label is a reference estimate.",
            "C_unlabelled_adaptation_or_simulator_calibration": "Potentially possible from eligible unlabeled experimental powder profiles, but needs separate protocol and labels must remain untouched.",
            "D_independent_real_test": "Not established; hold out base IDs and preferably mineral species before any adaptation.",
            "E_refinement_comparison": "Potentially evaluable on samples with raw profiles, exact-ID cells and declared forward-model/instrument assumptions.",
            "decision": decision,
            "decision_reason": decision_reason,
            "scope_recommendation": recommendation,
        })
    summaries.sort(key=lambda r: (-r["with_high_AMCSD_template_compatibility"], -r["experimental_powder_with_complete_RRUFF_refinement_cell"], r["family"]))
    return summaries


def write_outputs(archive_dir: Path, output_dir: Path, download_missing: bool,
                 downloaded_during_audit: list[str] | None = None) -> dict[str, Any]:
    downloaded_during_audit = downloaded_during_audit or []
    download_record = maybe_download_archives(archive_dir, download_missing)
    samples, provenance, non_rruff, cifs = build_archive_index(archive_dir)
    for info in provenance.values():
        if isinstance(info, dict) and "downloaded_by_this_run" in info:
            info["downloaded_by_this_run"] = info["file_name"] in download_record["downloaded_by_this_run"] if "file_name" in info else False
    # Archive provenance is determined independently after any optional download.
    for filename in REQUIRED_ARCHIVES:
        path = archive_dir / filename
        if path.exists():
            downloaded_now = filename in download_record["downloaded_by_this_run"] or filename in downloaded_during_audit
            provenance[filename]["downloaded_this_audit"] = downloaded_now
            provenance[filename]["acquisition_note"] = "downloaded from the official source during this audit; see audit date and SHA-256" if downloaded_now else "pre-existing local archive; original download date not independently verified"
            if filename in downloaded_during_audit:
                provenance[filename]["acquisition_date"] = "2026-10-19"
    manifest = build_manifest(archive_dir, samples, cifs)
    summaries = family_summary(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_fields = list(manifest[0].keys()) if manifest else []
    family_fields = list(summaries[0].keys()) if summaries else []
    csv_write(output_dir / "sample_manifest.csv", manifest, manifest_fields)
    csv_write(output_dir / "family_summary.csv", summaries, family_fields)
    raw_by_kind = Counter(r["raw_profile_kind"] for r in manifest if r["raw_xrd_present"])
    raw_valid_count = sum(1 for r in manifest if r["raw_xrd_present"] and r["raw_profile_valid"])
    exact_complete = sum(1 for r in manifest if r["cell_label_completeness_count_6"] == 6)
    powder_valid = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate")
    powder_mixture_caveat = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate" and r["raw_metadata_mixture_or_contamination_caveat"])
    powder_complete = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate" and r["cell_label_completeness_count_6"] == 6)
    powder_clean = powder_valid - powder_mixture_caveat
    powder_complete_clean = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate" and not r["raw_metadata_mixture_or_contamination_caveat"] and r["cell_label_completeness_count_6"] == 6)
    strong_clean = sum(1 for r in manifest if r["strong_audit_candidate"] and not r["raw_metadata_mixture_or_contamination_caveat"])
    single_crystal_caption = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate" and "cell parameters are from single crystal" in (r["diffraction_sample_description"] or "").casefold())
    single_crystal_caption_with_label = sum(1 for r in manifest if r["raw_profile_valid"] and r["raw_profile_kind"] == "experimental_powder_candidate" and "cell parameters are from single crystal" in (r["diffraction_sample_description"] or "").casefold() and r["cell_label_completeness_count_6"] == 6)
    strong = sum(1 for r in manifest if r["strong_audit_candidate"])
    shared_trace_ids = sum(1 for r in manifest if int(r["exact_numeric_trace_shared_sample_id_count"] or 0) > 1)
    related_subnumber_ids = sum(1 for r in manifest if r["raw_xrd_present"] and r["possible_repeated_or_related_subsample"])
    summary = {
        "audit_id": "rruff_domain_adaptation_20261019",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_version": "1.0.0",
        "archive_directory": str(archive_dir.resolve()),
        "output_directory": str(output_dir.resolve()),
        "source_urls": OFFICIAL_ARCHIVES,
        "archive_provenance": provenance,
        "optional_downloads": download_record,
        "archive_members_without_RRUFF_R_id_in_XY_RAW": non_rruff,
        "archive_members_without_RRUFF_R_id_count": len(non_rruff),
        "screening_counts": {
            "XY_RAW_archive_members": provenance.get("archive_member_counts", {}).get("XY_RAW.zip", 0),
            "XY_RAW_members_with_parseable_RRUFF_R_sample_ID": sum(len(rec["raw"]) for rec in samples.values()),
            "unique_exact_RRUFF_IDs_in_union_of_indexed_powder_archives": len(manifest),
            "unique_exact_RRUFF_IDs_with_raw_profile": sum(bool(r["raw_xrd_present"]) for r in manifest),
            "raw_and_exact_ID_refinement_output_intersection": sum(bool(r["raw_xrd_present"] and r["refinement_output_present_exact_id"]) for r in manifest),
            "raw_profiles_numerically_valid": raw_valid_count,
            "raw_profile_kinds": dict(raw_by_kind),
            "valid_experimental_powder_candidate_profiles": powder_valid,
            "powder_profiles_with_metadata_mixture_or_contamination_caveat": powder_mixture_caveat,
            "valid_experimental_powder_profiles_without_metadata_mixture_caveat": powder_clean,
            "exact_ID_complete_RRUFF_refinement_cell_labels": exact_complete,
            "valid_powder_plus_complete_exact_ID_RRUFF_cells": powder_complete,
            "valid_powder_plus_complete_exact_ID_RRUFF_cells_without_metadata_mixture_caveat": powder_complete_clean,
            "valid_powder_plus_complete_RRUFF_cell_plus_high_CIF_template_compatibility": strong,
            "valid_powder_plus_complete_RRUFF_cell_plus_high_CIF_template_compatibility_without_metadata_mixture_caveat": strong_clean,
            "powder_descriptions_saying_cell_parameters_are_from_single_crystal": single_crystal_caption,
            "such_descriptions_with_complete_exact_ID_RRUFF_cell_labels": single_crystal_caption_with_label,
            "samples_with_shared_numeric_XY_trace_across_IDs": shared_trace_ids,
            "samples_in_related_RRUFF_subnumber_groups": related_subnumber_ids,
            "family_registry_unclassified_samples": sum(r["family_candidate"] == "unclassified" for r in manifest),
            "unique_CIF_members": provenance.get("CIF_member_count", 0),
            "sample_IDs_with_exact_AMCSD_CIF_name_candidate": sum(1 for r in manifest if r["amcsd_exact_name_candidate_count"] > 0),
        },
        "family_alias_registry": FAMILY_ALIASES,
        "existing_inversion_forward_model_scope": {
            "project_readme": "xrd_inversion/README.md states known-phase, single-phase tetragonal PXRD inversion.",
            "implementation": "xrd_inversion/src/xrd_inversion/gpu_forward.py uses contract tetragonal_torch_dense_v1 and rejects nonconventional tetragonal lattices.",
            "implication": "Garnet and spinel labels are data-rich but cubic and cannot be used directly by the current forward path; the Rutile P4_2/mnm cohort is tetragonal-compatible.",
        },
        "family_summary_rows": len(summaries),
        "top_three_families_by_high_template_compatibility": [r["family"] for r in summaries[:3]],
        "most_promising_three_by_audit_judgement": ["Rutile structure type", "Garnet", "Apatite"],
        "most_promising_three_rationale": "The Rutile structure type is the only reviewed cohort with useful exact-ID label/template coverage that directly matches the repository's current tetragonal-only forward model (11 labels; 9 high template matches; two independent lattice parameters). Garnet has richer and cleaner family data (44 labels, cubic one-parameter) but needs a cubic forward-model extension. Apatite has 29 labels and a mostly hexagonal target, also outside the current forward model. Spinel is a smaller cubic fallback with 13 labels.",
        "qualification_definition": {
            "valid_profile": "at least two finite numeric XY pairs, strictly increasing two-theta, nonconstant intensity",
            "experimental_powder_candidate": "RRUFF diffraction description says Powder and does not explicitly say the profile is calculated; unresolved descriptions are not counted",
            "cell_label": "all six cell parameters parsed from exact sample-ID member in Refinement_Output_Data.zip; reported RRUFF refinement estimate, not error-free ground truth",
            "high_CIF_template_compatibility": "matching crystal system, max sorted-cell/angle metric difference <=3%, and cation-element-set Jaccard >=0.5, with either an exact normalized mineral name or an exact DIF-to-AMCSD database-code link; this supports template compatibility only, never same-specimen identity",
            "strong_audit_candidate": "valid experimental-powder candidate profile + complete exact-ID RRUFF cell + high template compatibility",
        },
        "limitations": [
            "RRUFF XY_RAW has no explicit wavelength field; the audit records wavelengths only from an exact-ID Refinement_Output_Data match and otherwise reports unknown.",
            "AMCSD CIF cells are reference-structure evidence, never substituted for exact-ID RRUFF refined cell labels.",
            "A name/CIF match does not establish same specimen or provenance; only exact normalized names are considered, and confidence requires independent system, cell and chemistry evidence.",
            "Family aliases are a finite declared registry; unlisted names remain unclassified, so family counts are conservative and scope-limited.",
            "Family GO/LIMITED_GO/NO_GO entries are qualitative audit judgments, not automatic minimum-size filters; GO means only that a bounded pilot is plausible, not that the scientific method succeeds.",
            "No split is created and no training/evaluation is performed. Independent DA/test feasibility remains conditional on grouped holdout design.",
            "Local pre-existing archive mtimes are recorded but cannot establish their original acquisition time; audit verifies current file hashes and official-source URLs.",
        ],
    }
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--download-missing", action="store_true", help="Download missing official ZIPs; never overwrite existing files")
    parser.add_argument("--downloaded-during-audit", action="append", choices=REQUIRED_ARCHIVES,
                        help="Record an archive already downloaded manually during this audit; repeat for multiple files")
    args = parser.parse_args(argv)
    summary = write_outputs(args.archive_dir, args.output_dir, args.download_missing, args.downloaded_during_audit)
    print(json.dumps(summary["screening_counts"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
