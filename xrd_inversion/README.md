# PXRD quantitative inversion

This directory contains the repaired smoke and formal Week-1 numerical gates
for the known-phase, single-phase, tetragonal inversion V0. It reads the frozen `xrd_robustness` structures,
authoritative parent split, reflection cache, and measurement configuration
without modifying that project.

The current implementation covers:

- tetragonal parent/split/cell audit;
- P0 forward correctness, cache identity, Bragg-metric, zero-shift, and FWHM checks;
- a cached CUDA float64 forward with strict CPU-P0 profile parity;
- P1 multi-anchor autograd Jacobians plus a fixed finite-difference step sweep;
- P2-R deterministic multistart recoverability and P2-L nominal-start local capture;
- a full-parameter unmodelled-nuisance diagnostic that does not enter the clean Gate;
- a structural near-duplicate audit and an independent renderer holdout frozen unopened.

It deliberately does not start neural-network training. The exact formal run
passes P0, CUDA parity, P1, and all 288/288 clean P2-R cases across the three
staircases. P2-L passes only 181/288 clean cases, preserving the intended
nominal-basin diagnostic rather than turning it into a numerical Gate failure.
Five non-conventional stored cells are explicitly quarantined for V0. The
structural audit found no same-composition candidate pairs in its proxy scope,
but did find broad anonymous-prototype overlap across the current split; that
overlap must be handled as a pre-ML split-policy issue.

Run from the repository root with the existing science environment:

```powershell
& '.venvs\xrd_test\Scripts\python.exe' 'xrd_inversion\scripts\run_week1_pilot.py'
```

Run the exact formal 24-parent x 4-trial numerical Gate with:

```powershell
& '.venvs\xrd_test\Scripts\python.exe' 'xrd_inversion\scripts\run_week1_pilot.py' `
  --config 'xrd_inversion\configs\week1_formal_gate.json'
```

Outputs are written to `xrd_inversion/reports/` and
`xrd_inversion/manifests/`. The frozen pilot choices live in
`xrd_inversion/configs/week1_repaired_smoke.json` and
`xrd_inversion/configs/week1_formal_gate.json`. Formal P2 writes ignored,
atomic per-parent checkpoints under `xrd_inversion/checkpoints/week1_formal/`
and validates their config/source/manifest contract before resuming.

## Execution policy

All tensorizable forward rendering, residual evaluation, and Jacobians are
GPU-first on the local RTX 4060. Week-1 numerical physics uses CUDA float64
with TF32 and autocast disabled. Candidate banks are scored in batches of 16;
formal candidate counts are frozen at S1=256, S2=512, and S3=1024 from one
nested scrambled-Sobol design. CPU is limited to the authoritative P0 oracle,
one-time nuisance observations, SciPy trust-region control flow, and
file/provenance audits.
