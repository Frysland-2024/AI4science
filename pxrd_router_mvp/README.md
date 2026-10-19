# PXRD Phase Router MVP

This candidate-limited single-phase demo reads a two-theta/intensity spectrum, scores all three pinned CIF hypotheses, and refines lattice and profile nuisance parameters. It does not identify arbitrary phases or infer chemical composition.

## Run

From the repository root with Python 3.11 or newer:

```powershell
python -m pip install -e .
python -m pxrd_router_mvp.demo
python -m unittest discover -s pxrd_router_mvp/tests -v
```

Fit a spectrum with numeric CSV/XY/TXT columns or named CSV columns:

```powershell
python -m pxrd_router_mvp --input spectrum.csv --wavelength 1.5406 --x-column 0 --y-column 1
```

The x axis is 2theta in degrees and wavelength is required in Å. Input is capped at 10 MiB; duplicate/non-finite axes and negative intensities are rejected. Descending axes are reversed. Input is processed in memory and not saved.

Optional uploader and fit/residual plot:

```powershell
python -m pip install -e ".[ui]"
streamlit run pxrd_router_mvp/ui/streamlit_app.py
```

## Scope and provenance

Candidate CIFs are BaTiO₃ P4mm (COD 9014273), MgO rocksalt (COD 9000505), and CeO₂ fluorite (COD 9009008). Provenance and SHA-256 pins are in [`candidates/README.md`](candidates/README.md). The simplified renderer uses fixed CIF coordinates, neutral-atom `f(s)=Z` kinematic factors, a Lorentz-polarization term, and Gaussian peaks. It is not a Rietveld implementation and omits important instrument and specimen effects.

The seven-system classifier is optional and never gates candidate scoring. The deterministic demo is marked **SIMULATED**. See [`../reports/DEMO_VALIDATION.md`](../reports/DEMO_VALIDATION.md) and [`../reports/MVP_IMPLEMENTATION_STATUS.json`](../reports/MVP_IMPLEMENTATION_STATUS.json).

## Optional local RRUFF examples

The app can opt into two **adaptation_pool** RRUFF-371 measured/resampled profiles when pointed at a local licensed data tree. No RRUFF spectrum, DIF, refinement text, or private metadata is bundled or copied. The adapter enforces split membership and the manifest spectrum hash and accepts only R050045 Fluorite (CaF2) and R060745 Rutile (TiO2). See the metadata-only [real-demo audit](../reports/RRUFF_REAL_DEMO_AUDIT.md) for overlay outcomes and posthoc comparisons.

```powershell
python -m pxrd_router_mvp --rruff-root E:\AI4science\xrd_robustness\data\real_xrd\rruff371 --rruff-id R050045
python -m pxrd_router_mvp --rruff-root E:\AI4science\xrd_robustness\data\real_xrd\rruff371 --rruff-id R060745
```

The wavelength triplet is reported. Wavelength #1 (1.541838 Å) is used for the observed profile because that is the RRUFF DIF source wavelength and it matches the frozen simulator's CuKa wavelength (1.54184 Å). Refinement rows use wavelength #2 (1.540562 Å); the resulting cell is shown only as a posthoc reference. It never initializes, bounds, scores, or selects a candidate. The local records say spectra/refinement contents are retained for local research and redistribution rights are not asserted; cite Lafuente et al. (2016), DOI 10.1515/9783110417104-003. Frozen locked-test records are not accepted.

The bundled candidates do not include CaF2 or rutile. Until independent COD CIF snapshots can be fetched and verified in an environment with permitted network access, these real examples demonstrate ingestion, all-candidate overlays, residuals and honest `real_demo_requires_better_forward` behavior only. Local generated overlays stay in an ignored folder. CaF2 must not be read as CeO2 simply because both use a fluorite prototype.

## Optional frozen symmetry prior

If the local `xrd_robustness` source, PyTorch and verified Dynamic-JS checkpoint are available, the adapter checks the checkpoint, model-source and label-source SHA-256 values plus exact model config before CPU inference. It only accepts a 3501-point 10–80° axis at 0.02° spacing and the training simulator's CuKa wavelength of 1.54184 Å. Set `PXRD_CLASSIFIER_REPO` or `PXRD_CLASSIFIER_CHECKPOINT` to override local discovery. Otherwise the app reports `classifier unavailable`. Seven-system probabilities are only a weak optional prior, never a phase label or candidate filter.

The prior is off by default. Apply it explicitly with the UI checkbox or CLI flag `--use-classifier-prior`.
