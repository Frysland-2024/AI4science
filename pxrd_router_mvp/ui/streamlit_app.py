"""Optional Streamlit uploader and profile/residual plot."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

try:
    import streamlit as st
except ImportError as exc:  # clear setup message when optional dependency is absent
    raise SystemExit("Streamlit is not installed. Install with: python -m pip install -e '.[ui]'") from exc

import matplotlib.pyplot as plt
import numpy as np

from pxrd_router_mvp.candidates import available_candidates, candidate_by_id
from pxrd_router_mvp.classifier_adapter import load_optional_prior
from pxrd_router_mvp.crystal import render
from pxrd_router_mvp.io import read_spectrum_bytes, validate_spectrum
from pxrd_router_mvp.router import route


st.set_page_config(page_title="PXRD Phase Router MVP", layout="wide")
st.title("Candidate limited PXRD router")
st.caption("Single phase, fixed CIF hypotheses and bounded lattice fitting. The reported rank is not a calibrated probability.")

with st.sidebar:
    wavelength = st.number_input("Wavelength (Å)", min_value=0.35, max_value=3.0, value=1.5406, step=0.0001, format="%.4f")
    mode = st.radio("Input", ["Upload spectrum", "Synthetic demonstration"])
    chosen = st.selectbox("Synthetic CIF", available_candidates(), format_func=lambda c: c.name) if mode == "Synthetic demonstration" else None
    uploaded = st.file_uploader("CSV / TSV / XY / TXT", type=["csv", "tsv", "xy", "txt"]) if mode == "Upload spectrum" else None
    xcol = st.text_input("2theta column index or header", "0")
    ycol = st.text_input("Intensity column index or header", "1")
    min_angle, max_angle = st.slider("Optional 2theta range", 0.0, 120.0, (10.0, 80.0), step=1.0)

if mode == "Synthetic demonstration":
    crystal = chosen.load()
    axis = np.arange(10.0, 80.0001, 0.04)
    a_true = crystal.a * 1.004
    c_true = crystal.c * 0.997 if crystal.crystal_system == "tetragonal" else a_true
    values = render(crystal, axis, wavelength, a=a_true, c=c_true, zero_shift=0.025, fwhm=0.16)
    rng = np.random.default_rng(271828)
    values = np.clip(0.025 + 0.96 * values + rng.normal(0.0, 0.003, len(axis)), 0.0, None)
    spectrum = validate_spectrum(axis, values, wavelength, axis_range=(min_angle, max_angle), source_label="SIMULATED demo")
    st.info("SIMULATED profile generated from the selected CIF. This is a software demo, not an experimental measurement.")
elif uploaded is not None:
    def col(text):
        try:
            return int(text)
        except ValueError:
            return text
    try:
        spectrum = read_spectrum_bytes(uploaded.getvalue(), wavelength_angstrom=wavelength,
                                       x_column=col(xcol), y_column=col(ycol),
                                       axis_range=(min_angle, max_angle), source_label="uploaded data")
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    st.info("Upload a two-column spectrum or choose a labeled synthetic demonstration.")
    st.stop()

if st.button("Rank candidates and fit lattices", type="primary"):
    with st.spinner("Evaluating every verified candidate CIF…"):
        result = route(spectrum.two_theta, spectrum.intensity, spectrum.wavelength_angstrom)
    prior_status = load_optional_prior()
    st.caption(f"Symmetry prior: {prior_status.message}. The physical matcher evaluated {len(result.evaluated_candidate_ids)} candidates.")
    if result.warning:
        st.warning(result.warning)
    st.subheader("Top candidate fits")
    rows = [fit.summary() for fit in result.results[:3]]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    best = result.results[0]
    fig, (ax, resid) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    measured = spectrum.intensity / spectrum.intensity.max()
    ax.plot(spectrum.two_theta, measured, color="#222222", lw=1, label="input (normalized)")
    ax.plot(spectrum.two_theta, best.predicted, color="#d1495b", lw=1.2, label=f"{best.candidate} fit")
    ax.set_ylabel("Relative intensity")
    ax.legend()
    resid.axhline(0.0, color="gray", lw=0.8)
    resid.plot(spectrum.two_theta, best.residual, color="#00798c", lw=0.9)
    resid.set_xlabel("2theta (degrees)")
    resid.set_ylabel("Residual")
    st.pyplot(fig, clear_figure=True)
    st.warning("This restricted single-phase prototype does not establish chemical composition, universal phase ID, Rietveld equivalence, measured-spectrum accuracy, or calibrated confidence. Verify candidates and instrument corrections independently.")
