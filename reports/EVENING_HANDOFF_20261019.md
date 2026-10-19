# Final bounded review and evening handoff

**Date:** 2026-10-19  
**Branch:** `codex/phase-router-inversion-mvp-20261019`  
**Review scope:** final acceptance and critical-fix pass only. No scientific model, frozen classifier, original data, or candidate library was changed.

## Acceptance

| Area | Result | Evidence and boundary |
|---|---|---|
| Candidate-limited synthetic prototype | **PASS** | All three fixed-CIF synthetic CLI demos ranked their generating candidate first. Recovered lattice parameters were within the intended synthetic perturbations; RMSE was approximately 0.003. All candidates were evaluated, independent of filename and optional classifier prior. This is renderer self-consistency only, not measured-spectrum accuracy or general phase identification. |
| Local RRUFF demo | **PARTIAL** | The read-only adapter accepted only the two adaptation-pool examples, verified manifest spectrum hashes, parsed source wavelength #1 as 1.541838 Å, and evaluated all candidates. Both ranked MgO first despite being CaF2 and rutile; rutile's top fit did not converge. The report and residual plots show clear mismatch. Status is `real_demo_requires_better_forward`; real-spectrum phase validation is **NOT DONE**. Locked-test records were not used. |
| Streamlit UI | **PASS** | Isolated Streamlit 1.66.0 started headlessly and `/_stcore/health` returned HTTP 200 `ok`. The UI shares measured/model/residual diagnostics. No browser visual inspection was performed. |

The 12 unit/integration tests passed with both the local RRUFF root and the read-only frozen Dynamic-JS checkpoint enabled. The checkpoint inferred both adaptation spectra but returned triclinic as the top class for both; the optional prior stays off by default and does not remove candidates. Locked-test ID rejection passed.

All three bundled CIF snapshots have source records and pinned SHA-256 values in [`pxrd_router_mvp/candidates/README.md`](../pxrd_router_mvp/candidates/README.md); the test loader verified the hashes. No independently verified CaF2 or rutile CIF was available, so those materials remain unsupported. RRUFF spectra, DIF/refinement records, derived metadata and local plots are absent from Git; the overlay directory is ignored. The existing RRUFF audit contains sample-level posthoc comparisons and the redistribution caveat.

## Commands and results

Run from the repository root in PowerShell. The test command below used the prepared scientific venv read-only; Streamlit used its isolated local venv.

```powershell
$env:PXRD_RRUFF_TEST_ROOT='E:\AI4science\xrd_robustness\data\real_xrd\rruff371'
$env:PXRD_CLASSIFIER_CHECKPOINT='E:\AI4science\xrd_robustness\outputs\simulated_test_checkpoints\checkpoints\seed_20260711_js_lambda_60\best.ckpt'
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m unittest discover -s pxrd_router_mvp/tests -v
```

Result: `Ran 12 tests ... OK`; optional local RRUFF and checkpoint checks were enabled and passed.

```powershell
$py='E:\AI4science\.venvs\xrd_test\Scripts\python.exe'
$py -m pxrd_router_mvp.demo --candidate batio3_p4mm_cod9014273
$py -m pxrd_router_mvp.demo --candidate mgo_rocksalt_cod9000505
$py -m pxrd_router_mvp.demo --candidate ceo2_fluorite_cod9009008
```

Each command ranked its source CIF first; each evaluated all three candidates.

```powershell
$py -m pxrd_router_mvp --rruff-id R050045 --rruff-root 'E:\AI4science\xrd_robustness\data\real_xrd\rruff371'
$py -m pxrd_router_mvp --rruff-id R060745 --rruff-root 'E:\AI4science\xrd_robustness\data\real_xrd\rruff371'
```

Both commands completed with `real_demo_requires_better_forward`, all three candidates scored, no locked-test input, and source wavelength 1.541838 Å. R050045's MgO fit converged (RMSE 0.055150); R060745's MgO fit reached its evaluation cap (RMSE 0.047882). These fit errors are uncalibrated and do not establish a good match.

```powershell
E:\AI4science\_local\.venvs\phase_router\Scripts\python.exe -m streamlit run pxrd_router_mvp/ui/streamlit_app.py --server.headless true --server.port 8769
Invoke-WebRequest -Uri 'http://127.0.0.1:8769/_stcore/health' -UseBasicParsing
```

Health result: HTTP 200, body `ok`. Stop the local server with Ctrl+C.

Additional acceptance checks: filename-independence and optional-prior non-exclusion unit cases passed; the locked-test ID rejection unit case passed; the two local observed-versus-fit/residual plots were visually inspected; candidate CIF SHA-256 checks passed; `git ls-files` showed no RRUFF sample data or local overlays; `git diff --check` passed.

## Launch

Install the package and UI extras in an isolated Python 3.11+ environment, then run:

```powershell
python -m pip install -e '.[ui]'
python -m streamlit run pxrd_router_mvp/ui/streamlit_app.py
```

Or run a synthetic CLI example without Streamlit:

```powershell
python -m pxrd_router_mvp.demo --candidate batio3_p4mm_cod9014273
```

For measured CSV/XY input, use the app's upload path or `python -m pxrd_router_mvp --input <spectrum.csv> --wavelength <angstrom>`. The local RRUFF selector requires the user's own authorized RRUFF-371 tree and is not bundled.

## Limitations

The system is a three-CIF, single-phase hypothesis router with simplified neutral-atom scattering and Gaussian broadening. It is not a database-wide search, composition identifier, Rietveld refinement, calibrated confidence model, or validated real-spectrum phase classifier. The local RRUFF examples are exploratory adaptation-pool ingestion/diagnostics only; their same-sample refinements are posthoc references and not independent ground truth. No classifier retraining, test-set use, parameter tuning, or GPU work was performed.

## Delivery

This review updates the stage statuses in [`MVP_IMPLEMENTATION_STATUS.json`](MVP_IMPLEMENTATION_STATUS.json). The branch is to be pushed after this report is committed. A Draft PR attempt against `codex/donut-pxrd-four-stage-20261019` and its result will be recorded in that status file; no merge is authorized.
