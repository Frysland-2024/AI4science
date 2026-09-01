# PXRD quantitative inversion

This directory contains a smoke-scale implementation of the Week-1 gates for
the known-phase, single-phase, tetragonal inversion V0. It reads the frozen `xrd_robustness` structures,
authoritative parent split, reflection cache, and measurement configuration
without modifying that project.

The current implementation covers:

- tetragonal parent/split/cell audit;
- P0 forward correctness, cache identity, Bragg-metric, zero-shift, and FWHM checks;
- P1 multi-anchor finite-difference Jacobian and identifiability checks for S1-S3;
- P2 paired, per-staircase clean recovery plus an unmodelled-nuisance stress diagnostic.

It deliberately does not start neural-network training. A passing smoke run is
not a formal Week-1 GO: the larger frozen sample, structural near-duplicate
audit, quarantined-cell resolution, and independent-renderer construction are
still required before P3.

Run from the repository root with the existing science environment:

```powershell
& '.venvs\xrd_test\Scripts\python.exe' 'xrd_inversion\scripts\run_week1_pilot.py'
```

Outputs are written to `xrd_inversion/reports/` and
`xrd_inversion/manifests/`. The frozen pilot choices live in
`xrd_inversion/configs/week1_pilot.json`.

## Execution policy

Follow-on work is GPU-first on the local RTX 4060: neural-network training,
batched spectral rendering, residuals, and Jacobians should run on CUDA when
they are tensorizable. CPU is reserved for file/provenance audits and
Pymatgen/SciPy operations that have no GPU implementation. The current strict
CPU P2 run is retained only as a small reference baseline and must not be
scaled to the formal sample count without a cached/vectorized GPU forward.
