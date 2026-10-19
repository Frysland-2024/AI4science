"""Minimal CIF reader and kinematic fixed-cell powder renderer.

The renderer calculates Bragg positions and atomic structure factors from CIF
coordinates. It uses f(s)=Z (neutral-atom zero-angle approximation), omits
temperature/anomalous corrections, preferred orientation and instrumental
resolution functions, and uses a Gaussian profile for the present MVP.
"""

from __future__ import annotations

import math
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ATOMIC_NUMBER = {"O": 8, "Mg": 12, "Ti": 22, "Ba": 56, "Ce": 58}


@dataclass(frozen=True)
class Atom:
    element: str
    fractional: tuple[float, float, float]
    occupancy: float


@dataclass(frozen=True)
class Crystal:
    path: Path
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float
    atoms: tuple[Atom, ...]
    tags: dict[str, str]

    @property
    def crystal_system(self) -> str:
        if abs(self.a - self.b) < 1e-5 and abs(self.b - self.c) < 1e-5:
            return "cubic"
        if abs(self.a - self.b) < 1e-5 and abs(self.alpha - 90) < 1e-5 and abs(self.beta - 90) < 1e-5 and abs(self.gamma - 90) < 1e-5:
            return "tetragonal"
        raise ValueError("MVP renderer supports orthogonal cubic and tetragonal cells only")


def _tokens(line: str) -> list[str]:
    return shlex.split(line, comments=False, posix=True)


def _scalar(value: str) -> float:
    value = value.strip().strip("'").strip('"')
    value = re.sub(r"\([^)]*\)$", "", value)
    return float(value)


def _expression_value(expression: str, xyz: tuple[float, float, float]) -> float:
    expr = expression.replace(" ", "").lower()
    terms = re.findall(r"[+-]?[^+-]+", expr)
    total = 0.0
    for term in terms:
        sign = -1.0 if term.startswith("-") else 1.0
        token = term.lstrip("+-")
        if token in ("x", "y", "z"):
            total += sign * xyz["xyz".index(token)]
        elif token:
            if "/" in token:
                num, den = token.split("/", 1)
                total += sign * float(num) / float(den)
            else:
                total += sign * float(token)
    return total % 1.0


def _parse_symmetry_operation(operation: str, xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    parts = operation.strip().strip("'").strip('"').split(",")
    if len(parts) != 3:
        raise ValueError(f"invalid CIF symmetry operation: {operation}")
    return tuple(_expression_value(part, xyz) for part in parts)  # type: ignore[return-value]


def parse_cif(path: str | Path) -> Crystal:
    """Read the scalar tags, symmetry operations, and atom loop of a CIF."""
    cif_path = Path(path)
    lines = cif_path.read_text(encoding="utf-8-sig").splitlines()
    tags: dict[str, str] = {}
    loops: list[tuple[list[str], list[list[str]]]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if line.lower() == "loop_":
            i += 1
            headers: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("_"):
                headers.append(lines[i].strip().split()[0].lower())
                i += 1
            values: list[str] = []
            while i < len(lines):
                row = lines[i].strip()
                if not row or row.startswith("#"):
                    i += 1
                    continue
                if row.lower() == "loop_" or row.lower().startswith("data_") or row.startswith("_"):
                    break
                if row.startswith(";"):
                    # CIF text fields do not normally occur in the loops used below.
                    i += 1
                    while i < len(lines) and not lines[i].startswith(";"):
                        i += 1
                    i += 1
                    continue
                values.extend(_tokens(row))
                i += 1
            relevant = any(name in headers for name in (
                "_space_group_symop_operation_xyz", "_symmetry_equiv_pos_as_xyz",
                "_atom_site_fract_x",
            ))
            if headers and relevant:
                if len(values) % len(headers):
                    raise ValueError(f"malformed CIF loop in {cif_path}")
                rows = [values[j:j + len(headers)] for j in range(0, len(values), len(headers))]
                loops.append((headers, rows))
            continue
        if line.startswith("_"):
            pieces = _tokens(line)
            key = pieces[0].lower()
            if len(pieces) > 1:
                tags[key] = pieces[1]
            elif i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt.startswith(";"):
                    block: list[str] = []
                    i += 2
                    while i < len(lines) and not lines[i].startswith(";"):
                        block.append(lines[i])
                        i += 1
                    tags[key] = " ".join(block)
                elif nxt:
                    tags[key] = _tokens(nxt)[0]
                    i += 1
            i += 1
            continue
        i += 1

    def tag_float(*names: str) -> float:
        for name in names:
            if name.lower() in tags:
                return _scalar(tags[name.lower()])
        raise ValueError(f"missing CIF cell value {names[0]}")

    symmetry: list[str] = ["x,y,z"]
    site_rows: list[tuple[str, float, float, float, float]] = []
    for headers, rows in loops:
        if any(name in headers for name in ("_space_group_symop_operation_xyz", "_symmetry_equiv_pos_as_xyz")):
            idx = next(headers.index(name) for name in ("_space_group_symop_operation_xyz", "_symmetry_equiv_pos_as_xyz") if name in headers)
            symmetry = [row[idx] for row in rows]
        xkey, ykey, zkey = "_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"
        if all(name in headers for name in (xkey, ykey, zkey)):
            element_key = "_atom_site_type_symbol" if "_atom_site_type_symbol" in headers else "_atom_site_label"
            occupancy_key = "_atom_site_occupancy" if "_atom_site_occupancy" in headers else None
            for row in rows:
                symbol = re.match(r"[A-Za-z]+", row[headers.index(element_key)]).group(0)  # type: ignore[union-attr]
                symbol = symbol[0].upper() + symbol[1:].lower()
                site_rows.append((symbol, _scalar(row[headers.index(xkey)]), _scalar(row[headers.index(ykey)]),
                                  _scalar(row[headers.index(zkey)]), _scalar(row[headers.index(occupancy_key)]) if occupancy_key else 1.0))
    if not site_rows:
        raise ValueError(f"no atom sites found in CIF {cif_path}")
    atoms: list[Atom] = []
    for symbol, x, y, z, occ in site_rows:
        if symbol not in ATOMIC_NUMBER:
            raise ValueError(f"no atomic scattering approximation registered for element {symbol}")
        for operation in symmetry:
            coord = _parse_symmetry_operation(operation, (x, y, z))
            atom = Atom(symbol, coord, occ)
            if not any(old.element == atom.element and old.fractional == atom.fractional for old in atoms):
                atoms.append(atom)
    return Crystal(cif_path, tag_float("_cell_length_a"), tag_float("_cell_length_b"), tag_float("_cell_length_c"),
                   tag_float("_cell_angle_alpha"), tag_float("_cell_angle_beta"), tag_float("_cell_angle_gamma"),
                   tuple(atoms), tags)


def _hkls_for(crystal: Crystal, a: float, c: float, wavelength: float, max_two_theta: float) -> np.ndarray:
    b = a if crystal.crystal_system == "cubic" else a
    dmax = wavelength / (2 * math.sin(math.radians(max_two_theta / 2)))
    hlim = min(30, int(math.ceil(max(a, b) / dmax)) + 1)
    llim = min(30, int(math.ceil(c / dmax)) + 1)
    return np.asarray([(h, k, l) for h in range(-hlim, hlim + 1) for k in range(-hlim, hlim + 1)
                       for l in range(-llim, llim + 1) if (h or k or l)], dtype=np.int16)


def render(crystal: Crystal, two_theta: np.ndarray, wavelength: float, *, a: float | None = None,
           c: float | None = None, zero_shift: float = 0.0, fwhm: float = 0.12) -> np.ndarray:
    """Generate a kinematic Gaussian powder profile from a fixed CIF prototype."""
    aa = float(a if a is not None else crystal.a)
    cc = float(c if c is not None else (aa if crystal.crystal_system == "cubic" else crystal.c))
    if aa <= 0 or cc <= 0 or wavelength <= 0 or fwhm <= 0:
        raise ValueError("lattice constants, wavelength, and width must be positive")
    if not 0.35 <= wavelength <= 3.0:
        raise ValueError("wavelength outside this X-ray MVP's safe range (0.35–3.0 A)")
    bb = aa
    axis = np.asarray(two_theta, dtype=np.float64)
    hkl = _hkls_for(crystal, aa, cc, wavelength, min(179.0, float(axis[-1]) + 2.0))
    h, k, l = hkl.T.astype(np.float64)
    g2 = (h*h + k*k)/(aa*aa) + l*l/(cc*cc)
    d = 1.0 / np.sqrt(g2)
    bragg_arg = wavelength / (2*d)
    valid = (bragg_arg > 0) & (bragg_arg < 1)
    if not np.any(valid):
        return np.zeros_like(axis)
    hkl, h, k, l, d, bragg_arg = hkl[valid], h[valid], k[valid], l[valid], d[valid], bragg_arg[valid]
    f_complex = np.zeros(len(hkl), dtype=np.complex128)
    coords = np.asarray([atom.fractional for atom in crystal.atoms], dtype=np.float64)
    factors = np.asarray([ATOMIC_NUMBER[atom.element] * atom.occupancy for atom in crystal.atoms], dtype=np.float64)
    phases = 2j * np.pi * (hkl @ coords.T)
    f_complex = np.exp(phases) @ factors
    angle = np.degrees(2 * np.arcsin(bragg_arg)) + zero_shift
    theta = np.radians(angle / 2)
    lorentz = (1 + np.cos(2*theta)**2) / np.maximum(np.sin(theta)**2 * np.cos(theta), 1e-9)
    intensity = (np.abs(f_complex)**2) * lorentz
    # Exact d-spacing degeneracies form one powder reflection; summing signed hkl
    # naturally supplies multiplicity, while this profile sum is equivalent.
    sigma = fwhm / (2 * math.sqrt(2 * math.log(2)))
    profile = np.zeros_like(axis)
    for center, amp in zip(angle, intensity, strict=True):
        if center < axis[0] - 5*sigma or center > axis[-1] + 5*sigma or amp <= 0:
            continue
        lo = max(0, int(np.searchsorted(axis, center - 5*sigma)))
        hi = min(len(axis), int(np.searchsorted(axis, center + 5*sigma, side="right")))
        if lo < hi:
            z = (axis[lo:hi] - center) / sigma
            profile[lo:hi] += amp * np.exp(-0.5*z*z)
    maximum = float(profile.max(initial=0))
    return profile / maximum if maximum > 0 else profile
