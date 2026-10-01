# PXRD quantitative inversion

Experimental numerical infrastructure for a **known-phase, single-phase tetragonal PXRD inversion** study.

This is a secondary research line and is intentionally separated from the completed classification evidence in xrd_robustness.

## Status

A previous Stage-1 structure–measurement factorization proposal received a preregistered **NO-GO** and is archived. The surviving code focuses on numerical forward/inversion verification rather than reviving that factorization claim.

Current infrastructure includes:

- parent/split/cell audits;
- forward-model correctness checks;
- CUDA float64 / CPU parity checks;
- autograd Jacobian and finite-difference verification;
- deterministic multistart recoverability tests;
- local-capture diagnostics;
- nuisance diagnostics;
- structural near-duplicate auditing;
- an independent-renderer holdout contract.

The formal numerical run passed P0, CUDA parity, P1, and 288/288 clean P2-R recoverability cases. P2-L remained a diagnostic and passed 181/288 cases.

## Install

From the repository root:

~~~bash
python -m pip install -e "./xrd_inversion[gpu]"
~~~

Run the public tests:

~~~bash
python -m pytest -q xrd_inversion/tests
~~~

## Example execution

~~~bash
python xrd_inversion/scripts/run_week1_pilot.py --config xrd_inversion/configs/week1_formal_gate.json
~~~

Large historical per-trial JSON outputs and pairwise audit tables are intentionally omitted from the public tree. Compact Markdown reports, configs, and smaller audit artifacts remain under reports/ and manifests/.

## Scope boundary

This module should not be read as evidence for the main relationship-supervision classification claim. It is a separate numerical research track.
