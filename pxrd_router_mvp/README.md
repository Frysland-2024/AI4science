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

The seven-system classifier is optional and unavailable in this worktree because no compatible checkpoint or PyTorch installation is present. It never gates candidate scoring. The deterministic demo is marked **SIMULATED**; no real measured spectrum was validated, so no measured-spectrum accuracy claim is supported. See [`../reports/DEMO_VALIDATION.md`](../reports/DEMO_VALIDATION.md) and [`../reports/MVP_IMPLEMENTATION_STATUS.json`](../reports/MVP_IMPLEMENTATION_STATUS.json).
