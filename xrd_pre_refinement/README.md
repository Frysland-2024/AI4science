# XRD pre-refinement · archived local pilot artifacts

**Status: synthetic engineering demonstration only. NOT a validated research result.**

This directory preserves five outputs from the local BaTiO3 pre-refinement pilot in reports/pilot_run_working/:

- run_manifest.json — simulation settings and provenance.
- pre_refinement_report.json — detailed engineering output.
- simulated_example.csv — synthetic diffraction example.
- synthetic_mix_stress_report.json — mixture stress test output.
- batio3_template_comparison.png — illustrative figure.

The manifest records run_kind=simulated_engineering_demo_not_scientific_result and working_tree_dirty_at_run=true.
These results are NOT measured spectra, quantitative scientific validation, or proven phase fractions.

**Reproducibility limitation:** The manifest names python xrd_pre_refinement/scripts/run_batio3_pilot.py,
but that script, source .py modules, tests and configs were not present in the local folder when
this archive was uploaded. Compiled .pyc caches and egg-info metadata are deliberately excluded.
This is an artifact archive, NOT a runnable package.

If sources are later recovered or reimplemented, add them with provenance and validation.
This does not alter frozen V9 results or authorize GPU training.
