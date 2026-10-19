"""Optional Streamlit uploader and profile/residual plot."""

from __future__ import annotations

import sys
import os
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
from pxrd_router_mvp.rruff_local import load_local_example


st.set_page_config(page_title="PXRD Phase Router MVP", layout="wide")
st.title("Candidate limited PXRD router")
st.caption("Single phase, fixed CIF hypotheses and bounded lattice fitting. The reported rank is not a calibrated probability.")

with st.sidebar:
    wavelength = st.number_input("Wavelength (Å)", min_value=0.35, max_value=3.0, value=1.5406, step=0.0001, format="%.4f")
    mode = st.radio("Input", ["Upload spectrum", "Synthetic demonstration", "Local RRUFF adaptation demo"])
    chosen = st.selectbox("Synthetic CIF", available_candidates(), format_func=lambda c: c.name) if mode == "Synthetic demonstration" else None
    uploaded = st.file_uploader("CSV / TSV / XY / TXT", type=["csv", "tsv", "xy", "txt"]) if mode == "Upload spectrum" else None
    rruff_root = st.text_input("Local RRUFF-371 root (opt in)", os.environ.get("PXRD_RRUFF_ROOT", "")) if mode == "Local RRUFF adaptation demo" else ""
    rruff_id = st.selectbox("Adaptation sample", ["R050045", "R060745"]) if mode == "Local RRUFF adaptation demo" else None
    xcol = st.text_input("2theta column index or header", "0")
    ycol = st.text_input("Intensity column index or header", "1")
    use_classifier_prior = st.checkbox("Use optional weak seven-system prior", value=False)
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
elif mode == "Local RRUFF adaptation demo":
    if not rruff_root:
        st.info("Enter the path to your local, licensed RRUFF-371 data tree. No RRUFF files are bundled with this app.")
        st.stop()
    try:
        local_example = load_local_example(rruff_root, rruff_id)
        spectrum = local_example.spectrum
        st.info(f"Measured and resampled RRUFF spectrum: {rruff_id} {local_example.mineral}, {local_example.ideal_chemistry}. {local_example.provenance}. Source wavelength #{1}: {local_example.selected_wavelength_angstrom:.6f} Å; refinement reference wavelength: {local_example.refinement_reference_wavelength_angstrom:.6f} Å.")
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Local RRUFF adapter unavailable: {exc}")
        st.stop()
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
        prior_status = load_optional_prior(
            two_theta=spectrum.two_theta, intensity=spectrum.intensity,
            wavelength_angstrom=spectrum.wavelength_angstrom,
        )
        result = route(spectrum.two_theta, spectrum.intensity, spectrum.wavelength_angstrom,
                       crystal_system_prior=prior_status.prior if use_classifier_prior else None)
    st.caption(f"Symmetry prior: {prior_status.message}. Prior applied: {bool(use_classifier_prior and prior_status.available)}. The physical matcher evaluated {len(result.evaluated_candidate_ids)} candidates.")
    if result.warning:
        st.warning(result.warning)
    if mode == "Local RRUFF adaptation demo":
        best = result.results[0]
        a_ref, _, c_ref = local_example.refined_cell_angstrom
        c_fit = best.c_angstrom if best.c_angstrom is not None else best.a_angstrom
        errors = {"a_percent": 100 * (best.a_angstrom - a_ref) / a_ref,
                  "c_percent": 100 * (c_fit - c_ref) / c_ref}
        st.warning(f"real_demo_requires_better_forward: the bundled library does not contain {local_example.ideal_chemistry} {local_example.mineral}, and the simplified model does not reproduce the observed profile. Best listed candidate fit RMSE={best.score_rmse:.4f}; this is not sample identification.")
        st.caption(f"Posthoc refined cell: {local_example.refined_cell_angstrom} Å; relative difference: {errors}. This reference was excluded from initialization and ranking.")
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
