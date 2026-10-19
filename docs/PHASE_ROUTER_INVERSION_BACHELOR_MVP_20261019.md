# PHASE ROUTER + PXRD INVERSION — Bachelor MVP implementation plan (2026-10-19)

Status: **USER-APPROVED TO IMPLEMENT NOW**. This is a NEW applied-characterization system prototype, independent of the frozen seven-crystal-system research claims and the DONUT four-stage science experiment.

## 0. Outcome / boundaries

Deliver a runnable, testable, visually understandable **single-phase, candidate-limited PXRD assistant**:
**Upload/choose measured 2theta–intensity spectrum (+ wavelength) → existing seven-crystal-system prediction as an OPTIONAL soft prior → independent candidate-structure phase ranking → per-candidate lattice-parameter refinement → physically generated XRD overlay/residual → guarded report.**

**Never claim universal phase identification, chemical composition identification, Rietveld equivalence, real-spectrum accuracy, or confidence calibration that has not been demonstrated.** A reference CIF library is a *restricted hypothesis set*, not a whole database.

Candidate starting set: **BaTiO3 tetragonal P4mm (existing public CIF), MgO rocksalt cubic Fm-3m, CeO2 fluorite cubic Fm-3m**. MgO/CeO2 are proposed additional families, not already validated models: obtain pinned reputable CIF files if publicly accessible, record source license/provenance and lattice constants. If external sources are unavailable, implement configurable candidate interface and ship BaTiO3 only with other candidates clearly NOT_AVAILABLE, rather than fabricate CIFs or real measurements. Two cubic examples distinguish the different chemical phase candidates even though the crystal-system prior cannot distinguish them. BaTiO3 structure and its previously validated forward/checkpoints are already in this branch.

Important: the user's previous research model is **7 crystal system classification, NOT phase ID**. Use frozen ResNet18-GN + Dynamic JS checkpoint if safely available as the initial symmetry *probability* distribution (never train it or relabel it). Real CNRS zero-shot Macro-F1 roughly 0.207; do not hard-gate candidates on its output! The 7-class probabilities can give an explicitly optional, transparent, weak candidate re-rank/explanation, but the phase matcher must always evaluate all candidates. If no compatible verified weights/normalizer are available, show `classifier unavailable` and continue with the independent phase matcher (do NOT substitute untrained random weights or fake scores). The classification model is never retrained or overwritten.

## 1. Architecture and semantics

Use dedicated new `pxrd_router_mvp/` module (or equally clear top-level app); keep scientific source trees and frozen classifiers unchanged:
- `candidates/`: named verified single-phase CIFs + material labels, crystal system, symmetry/lattice degrees of freedom, stable identifier, source metadata; fixed prototype atomic positions and symmetry, not a general structure determination system.
- `io.py`: safe local CSV/XY/TXT reader with user-specified 2theta/intensity columns, wavelength (Å), optional axis range; validate 2theta strictly monotonic, finite nonnegative intensity, duplicates, axis units; no reliance on filename/composition as ground truth; safe upload caps, errors, proper interpolation/resampling with no blind renormalization.
- `classifier_adapter.py`: read-only load of verified frozen prior, preprocessing identical to trained domain, label mapping, trained resolution/wavelength compatibility; expose provenance and real-domain limitation. Graceful fallback if unavailable. **No hard filtering** or treating crystal-system label as phase.
- `router.py`: deterministic candidate-ranking based on physically simulated reflection peak positions + normalized profile fit under instrument params. Normalize intensity carefully, account for zero shift and width/background nuisance within bounded ranges, report match scores and runner-ups. Top-3 only; preserve scored alternatives, ambiguous/OOD/unsupported rejection.
- `refine.py`: physics-guided constrained optimization of (a,c for tetragonal, a for cubic), optional zero shift, simple width/background with reasonable bounds, fixed angle wavelength; L-BFGS-B/least_squares allowed. Explicit transparent physics forward; phase hypothesis known, not refining arbitrary chemical structure. If existing cached BaTiO3 tetragonal forward is only capable of BaTiO3, do not pretend it supports MgO/CeO2: add a general fixed-CIF XRDCalculator/peak profile renderer or a verified dependency. Include synthetic peak render parity sanity tests and robust handling of missing reflections/scattering. Keep solver fit-success flags, parameter bounds, residual diagnostics. No invented accuracy.
- `ui/streamlit_app.py`: upload user CSV/XY and enter wavelength, optional 2theta range; optionally generate built-in synthetic examples labelled SIMULATED; display symmetry prior if available, Top-3 candidates, fitted a,c (+ angle/width if fit), measured vs predicted plot + residual, unidentifiable/unsupported/low-quality warning, how-to-run notes.
- `tests/`: synthetic spectra BaTiO3, MgO, CeO2 with known controlled lattice constants and tested robustness to mild perturbation; verify no content leakage from CSV filename, classifier prior can't hard-exclude right phase, flag mismatch, invalid input rejection, saved test reproducibility. Include at least one end-to-end headless pipeline check. A real spectrum is only tested if there is documented permissible experimental source and wavelength metadata; otherwise clearly mark REAL EXPERIMENTAL VALIDATION NOT DONE.
- `reports/DEMO_VALIDATION.md`, `README.md`, dependencies, starter command. Installation should work in a clean environment with explicit dependencies; test with existing installed environment first.

Prefer code reuse from `xrd_inversion`, `xrd_forward_loss`, `donut_pxrd`, `xrd_robustness` where interfaces genuinely apply. Existing DONUT exp4 showed supervised A direct normalized q MAE ~0.0345 on BaTiO3 simulated and traditional multi-start optimization q MAE ~0.0003586. Those are narrow one-CIF synthetic results, **not** claims on new materials, nor on real spectra. Can expose existing supervised A as an optional fast-initializer if exact architecture, normalization and checkpoint SHA verified; physics-only initial candidates/refinement must work without it.

## 2. Work order — STRICT

Gate A: inventory code/dependencies/available frozen classifier checkpoints and verify candidate CIF provenance; create truthful support matrix (available/missing).
Gate B: implement headless CLI/API and synthetic end-to-end minimal path FIRST. Start with BaTiO3, then MgO, CeO2 only from verified CIFs. Gate on reasonable forward/refinement performance for in-range synthetic tests; fail honest if not.
Gate C: connect the original classification model adapter (or explicit graceful `unavailable`) and demonstrate its optional soft usage; make sure it cannot suppress correct physical candidate.
Gate D: build Streamlit interactive UI and diagnostic plot, with no fake example labelled experimental. Startup smoke/usage tests.
Gate E: documented tests, failure cases, measured real data disclaimer, source hashes/provenance. Commit, push dev branch and open a **Draft PR** against `codex/donut-pxrd-four-stage-20261019`; do not merge.
No GPU retraining by default. No sweeping model search. Use deterministic seed and cap test/training compute. No manipulating held-out test sets.

## 3. Execution restrictions

- Worktree only: `E:\AI4science\_local\worktrees\phase_router_mvp_20261019` on branch `codex/phase-router-inversion-mvp-20261019`. Do not modify `E:\AI4science` active worktree, DONUT baseline or frozen V9/ResNet classifiers or any other active task. Do not `git reset/clean` other worktrees. Preserve checkpoint and raw evidence.
- All new runtime, logs, generated assets and local checkpoints stay UNDER `E:\AI4science\_local`; NEVER create new `E:\AI4science_*` roots; don't commit raw uploaded spectra or private credentials.
- Before downloading data verify provenance and license; if missing state `candidate template only`, don't fabricate reference CIF/experimental spectrum.
- Limited scientific capability is acceptable for bachelor MVP; **honest functionality over broad false generality**. Original classification model weak on genuine zero-shot data, display provenance and uncertainty.
- Run and record unit/integration tests and reproducible demo; if Streamlit not installed, install in isolated `_local` venv if possible, or provide requirement and record untested environment; no package installer changes to global Python without necessity.
- If blocked by dependencies or lack of reference CIF and all no-internet alternatives, report blockers and implement narrower functioning MVP; don't claim all three supported without demonstration.

## 4. Completion and reporting

New package/application, executable demo, clear launch instructions, test logs, `reports/MVP_IMPLEMENTATION_STATUS.json` with per-stage truthful PASS/PARTIAL/BLOCKED, `reports/DEMO_VALIDATION.md`, limitations. Preserve project history: append dated note to `docs/PROJECT_HISTORY.md` describing transition from crystal-system recognition to symmetry prior → candidate phase router → conditional lattice fitting (without pretending prior classifier was phase-id). Separate successful engineering deliverables from scientific validation. No unauthorized main merge or publishing real private experimental data.
