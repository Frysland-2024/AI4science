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
from pxrd_router_mvp.garnet_local import (
    COD_RECORD,
    WAVELENGTH_SOURCE,
    available_garnet_samples,
    find_archive_root,
    run_garnet_pilot,
)
from pxrd_router_mvp.io import read_spectrum_bytes, validate_spectrum
from pxrd_router_mvp.router import route
from pxrd_router_mvp.rruff_local import load_local_example


st.set_page_config(page_title="PXRD Phase Router MVP", layout="wide")
st.title("Candidate limited PXRD router")
st.caption("Single phase, fixed CIF hypotheses and bounded lattice fitting. The reported rank is not a calibrated probability.")

with st.sidebar:
    mode = st.radio("Input", ["Upload spectrum", "Synthetic demonstration", "Local RRUFF adaptation demo", "Garnet real-spectrum pilot"])
    wavelength = st.number_input("Wavelength (Å)", min_value=0.35, max_value=3.0, value=1.5406, step=0.0001, format="%.4f", disabled=(mode == "Garnet real-spectrum pilot"))
    chosen = st.selectbox("Synthetic CIF", available_candidates(), format_func=lambda c: c.name) if mode == "Synthetic demonstration" else None
    uploaded = st.file_uploader("CSV / TSV / XY / TXT", type=["csv", "tsv", "xy", "txt"]) if mode == "Upload spectrum" else None
    rruff_root = st.text_input("Local RRUFF-371 root (opt in)", os.environ.get("PXRD_RRUFF_ROOT", "")) if mode == "Local RRUFF adaptation demo" else ""
    rruff_id = st.selectbox("Adaptation sample", ["R050045", "R060745"]) if mode == "Local RRUFF adaptation demo" else None
    try:
        default_archive_root = str(find_archive_root())
    except OSError:
        default_archive_root = os.environ.get("PXRD_RRUFF_ARCHIVE_ROOT", "")
    garnet_archive_root = st.text_input("Official local RRUFF archive directory", default_archive_root) if mode == "Garnet real-spectrum pilot" else ""
    garnet_sample = st.selectbox("Grossular sample", available_garnet_samples(), format_func=lambda sample: f"{sample.sample_id} — {sample.locality}") if mode == "Garnet real-spectrum pilot" else None
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
elif mode == "Garnet real-spectrum pilot":
    st.info(
        f"Selected measured powder sample: {garnet_sample.sample_id} {garnet_sample.mineral_name}; "
        f"measured composition: {garnet_sample.measured_chemistry}. Independent template: COD {COD_RECORD}, "
        "Grossular Ca₃Al₂Si₃O₁₂, Ia-3d. The reference cell is not loaded until fitting finishes."
    )
    st.caption(WAVELENGTH_SOURCE)
    spectrum = None
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

button_label = "Fit selected Grossular sample" if mode == "Garnet real-spectrum pilot" else "Rank candidates and fit lattices"
if st.button(button_label, type="primary"):
    if mode == "Garnet real-spectrum pilot":
        cif_path = ROOT / "pxrd_router_mvp" / "candidates" / "Grossular_COD_9001871.cif"
        output_root = ROOT / "reports" / "_local_garnet_pilot"
        try:
            with st.spinner("Loading the numeric profile, fitting the independent CIF, then opening the posthoc reference…"):
                fit, reference, evaluation, output_path = run_garnet_pilot(
                    garnet_sample.sample_id, garnet_archive_root, cif_path, output_root
                )
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            st.error(f"Garnet pilot stopped: {exc}")
            st.stop()
        from pxrd_router_mvp.garnet_local import load_garnet_spectrum
        spectrum = load_garnet_spectrum(garnet_sample.sample_id, garnet_archive_root)
        st.subheader(evaluation.status)
        st.write({
            "sample_id": evaluation.sample_id,
            "COD CIF": f"{fit.cif_formula}, {fit.cif_space_group}; a₀={fit.cif_cell_a_angstrom:.4f} Å",
            "predicted a": f"{evaluation.fitted_a_angstrom:.5f} Å",
            "RRUFF posthoc reference a": f"{evaluation.reference_a_angstrom:.5f} Å",
            "a residual": f"{evaluation.a_error_angstrom:+.5f} Å ({evaluation.a_error_percent:+.3f}%)",
            "profile RMSE": f"{fit.best.rmse:.5f}",
            "strong-peak matches": f"{evaluation.matched_strong_peak_count}/{evaluation.observed_strong_peak_count} ({evaluation.peak_match_fraction:.1%})",
            "solver": fit.best.solver_message,
            "diagnostics": str(output_path),
        })
        st.caption("The same-sample refined a was opened only after all optimization attempts completed; it was not used for initialization, bounds, fitting, or template selection.")
        rows = [fit.initial_cell_fit.summary(), *(attempt.summary() for attempt in fit.multi_start_attempts)]
        rows = [{key: value for key, value in row.items() if key not in ("predicted", "residual")} for row in rows]
        st.subheader("CIF baseline and physical multi-start fits")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        fig, (ax, resid) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        measured = spectrum.intensity / spectrum.intensity.max()
        ax.plot(spectrum.two_theta, measured, color="#222222", lw=0.9, label="RRUFF measured profile")
        ax.plot(spectrum.two_theta, fit.initial_cell_fit.predicted, color="#e09f3e", lw=1.0,
                label=f"COD a₀ fixed ({fit.cif_cell_a_angstrom:.4f} Å)")
        ax.plot(spectrum.two_theta, fit.best.predicted, color="#d1495b", lw=1.1,
                label=f"multi-start fit (a={fit.best.a_angstrom:.4f} Å)")
        ax.set_ylabel("Relative intensity")
        ax.legend()
        resid.axhline(0.0, color="gray", lw=0.8)
        resid.plot(spectrum.two_theta, fit.best.residual, color="#00798c", lw=0.9)
        resid.set_xlabel("2theta (degrees)")
        resid.set_ylabel("Residual")
        st.pyplot(fig, clear_figure=True)
        if evaluation.status == "PHYSICS_MODEL_NOT_READY":
            st.error("PHYSICS_MODEL_NOT_READY: stop before simulated training or few-shot adaptation. Inspect the residual and failed readiness checks in the local diagnostic record.")
        else:
            st.success("Physics pilot passed the predeclared screening checks for this sample. This does not establish generalization to other Garnet compositions.")
    else:
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
