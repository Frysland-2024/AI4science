"""Small, explicit readers for measured or simulated two-column PXRD data."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_POINTS = 50_000


@dataclass(frozen=True)
class Spectrum:
    two_theta: np.ndarray
    intensity: np.ndarray
    wavelength_angstrom: float
    source_label: str = "user supplied"


def validate_spectrum(two_theta: Sequence[float], intensity: Sequence[float], wavelength_angstrom: float,
                      *, axis_range: tuple[float, float] | None = None, source_label: str = "user supplied") -> Spectrum:
    x = np.asarray(two_theta, dtype=np.float64)
    y = np.asarray(intensity, dtype=np.float64)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) < 16:
        raise ValueError("expected at least 16 matching 2theta and intensity values")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("spectrum contains non-finite values")
    if np.any(y < 0):
        raise ValueError("intensity must be nonnegative")
    if not np.isfinite(wavelength_angstrom) or wavelength_angstrom <= 0:
        raise ValueError("wavelength must be a positive Angstrom value")
    if not 0.35 <= wavelength_angstrom <= 3.0:
        raise ValueError("wavelength outside this X-ray MVP's safe range (0.35–3.0 Å)")
    if len(x) > MAX_POINTS:
        raise ValueError(f"spectrum exceeds {MAX_POINTS} point limit")
    delta = np.diff(x)
    if np.all(delta < 0):
        x, y = x[::-1].copy(), y[::-1].copy()
    elif not np.all(delta > 0):
        raise ValueError("2theta axis must be strictly monotonic with no duplicates")
    if x[0] < 0 or x[-1] >= 180:
        raise ValueError("2theta must be in [0, 180) degrees")
    if axis_range is not None:
        low, high = axis_range
        if not (0 <= low < high < 180):
            raise ValueError("axis range must be ordered inside [0, 180)")
        keep = (x >= low) & (x <= high)
        x, y = x[keep], y[keep]
        if len(x) < 16:
            raise ValueError("selected axis range contains fewer than 16 points")
    if float(np.max(y)) <= 0:
        raise ValueError("intensity must contain at least one positive value")
    return Spectrum(x, y, float(wavelength_angstrom), source_label)


def read_spectrum_bytes(data: bytes, *, wavelength_angstrom: float, x_column: int | str = 0,
                        y_column: int | str = 1, delimiter: str | None = None,
                        axis_range: tuple[float, float] | None = None, source_label: str = "uploaded file") -> Spectrum:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"file exceeds {MAX_UPLOAD_BYTES} byte upload limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("file must be UTF-8 text") from exc
    # CSV is handled by DictReader when named columns are selected; otherwise numeric rows
    # may be comma, tab, or whitespace separated. Comment and blank lines are ignored.
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "!", ";"))]
    if not lines:
        raise ValueError("file contains no data rows")
    sep = delimiter
    if sep is None:
        sep = "," if "," in lines[0] else ("\t" if "\t" in lines[0] else None)
    rows: list[list[str]] = []
    if isinstance(x_column, str) or isinstance(y_column, str):
        if sep is None:
            raise ValueError("named columns require a delimited file with a header")
        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=sep)
        if not reader.fieldnames:
            raise ValueError("missing column header")
        names = {name.strip(): name for name in reader.fieldnames}
        if not isinstance(x_column, str) or not isinstance(y_column, str) or x_column not in names or y_column not in names:
            raise ValueError(f"named columns not found; available columns: {', '.join(names)}")
        try:
            records = list(reader)
            x = [float(row[names[x_column]]) for row in records]
            y = [float(row[names[y_column]]) for row in records]
        except (TypeError, ValueError) as exc:
            raise ValueError("selected columns contain a header or nonnumeric value") from exc
        return validate_spectrum(x, y, wavelength_angstrom, axis_range=axis_range, source_label=source_label)
    for line in lines:
        fields = line.split(sep) if sep else line.split()
        rows.append([field.strip() for field in fields])
    try:
        matrix = np.asarray(rows, dtype=np.float64)
        x = matrix[:, int(x_column)]
        y = matrix[:, int(y_column)]
    except (ValueError, IndexError) as exc:
        raise ValueError("could not read selected numeric columns; specify zero-based column indexes") from exc
    return validate_spectrum(x, y, wavelength_angstrom, axis_range=axis_range, source_label=source_label)


def read_spectrum_file(path: str | Path, **kwargs) -> Spectrum:
    p = Path(path)
    if p.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError(f"file exceeds {MAX_UPLOAD_BYTES} byte limit")
    return read_spectrum_bytes(p.read_bytes(), source_label=p.name, **kwargs)
