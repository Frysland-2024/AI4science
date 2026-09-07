# XRD structure–measurement factorization — archived Stage 1

**Archive date:** 2026-09-07  
**Status:** ARCHIVED / inactive  
**Stage-1 decision:** NO-GO  
**Exact pre-cleanup snapshot:** branch `archive/xrd-factorization-stage1-20260907` at commit `93da7d9f5cb3b2389439243d636bba6dcd5f68f9`

## Why this branch existed

The quantitative-inversion project originally considered a simple four-parameter route:

```text
PXRD -> (a, c, zero shift, FWHM)
```

A later literature check reduced the novelty weight of `prediction -> differentiable forward reconstruction` and refinement initialization, because closely related ideas already existed. The project therefore asked a more specific physics question:

> Can a model distinguish changes caused by the sample structure from changes caused by the measurement system?

This led to the supervised 2×2 intervention design:

```text
same structure + different measurement
same measurement + different structure
```

with two output groups:

- structure state: `(u, v)` / decoded `(a, c)`;
- measurement state: `(delta, w)` / decoded `(zero shift, FWHM)`.

The intended contribution was not a new two-head architecture. It was the problem formulation: using simulator-controlled interventions as relation supervision for structure–measurement factorization.

## What was tested

The finite Stage-1 mechanism Pilot was deliberately Train-only and preregistered before formal training.

- 32 conventional-tetragonal Train parents;
- 512 factorial blocks / 2048 spectra;
- 3 fixed training seeds;
- matched baseline vs paired model;
- identical data, initialization policy, optimizer, training steps, and batch schedule;
- only difference: `lambda_pair = 0` vs `lambda_pair = 1`.

The tiny-overfit engineering Gate passed before the formal Pilot.

## Result and why it was stopped

The paired model moved both cross-factor leakage metrics in the desired direction:

- measurement -> structure leakage: relative reduction **9.51%**, improved in **3/3** seeds;
- structure -> measurement leakage: relative reduction **4.20%**, improved in **3/3** seeds.

However, the preregistered Gate required substantially larger leakage reduction while protecting the underlying physical regression. The formal result was therefore **NO-GO**. In addition, the `a` MAE degraded by about **5.43%**, while other parameters showed mixed behavior.

The important interpretation is:

> The intervention supervision showed a real directional effect, but not a sufficiently strong and clean factorization benefit to justify expanding it into the active main line.

No rescue hyperparameter search, backbone search, forward-reconstruction loss, real spectra, refinement, or post-hoc task redefinition was used to overturn the Gate.

## Repository cleanup decision

To keep `main` readable, Stage-1 factorization implementation and generated evidence were removed from the active tree after the archive branch was created. This includes the factorization-specific:

- config / interface contract;
- factorial manifests;
- model, parameterization, dataset, losses, metrics, training, pilot runner;
- factorization tests;
- Stage-1 reports and figure-data JSON;
- stale `NEXT_*` planning documents that treated factorization as the active next step.

The exact code, reports, manifests, and old planning documents remain permanently available on:

```text
archive/xrd-factorization-stage1-20260907
```

The active `xrd_inversion/` tree keeps the numerical forward/recoverability infrastructure, GPU forward path, independent renderer holdout, structural audit, and Week-1 evidence.

## Project-development record for future applications

This branch should remain part of the project history because it records a useful research transition:

1. start from direct parameter prediction and forward reconstruction;
2. correct novelty claims after literature review;
3. reformulate the problem around controllable physical interventions;
4. turn simulator provenance into a supervised factorization hypothesis;
5. design a finite 2×2 mechanism test and preregister a GO/NO-GO Gate;
6. observe partial directional improvement but fail the frozen Gate;
7. stop instead of rescuing the idea after seeing the result.

This is an archived hypothesis, not an erased failure.

## Reactivation rule

Do **not** silently resume `factorization-interface-v1` as an active task. Any future revival must begin as a new version with:

- a materially new scientific hypothesis or factorization formulation;
- a new interface/config version;
- a new preregistered finite Gate;
- an explicit explanation of why the new design addresses the Stage-1 failure mode.
