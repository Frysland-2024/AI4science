# Supplemental joint-refinement evaluation protocol

**Recorded:** 2026-10-19, after the primary preregistered test evaluation. This addendum addresses the task order's required joint q+eta refinement and neutral-start physics baseline, which were not included in the frozen preregistration. It is post-hoc secondary evaluation and cannot change model, lambda, checkpoint, or hypothesis decisions.

The fresh test split, selected checkpoints, and direct predictions remain frozen. For each of the 1,386 method/condition/seed/sample rows, run one bounded L-BFGS-B fit of normalized q=(du,dv) and eta against the transformed observed profile, initializing q from that row's network prediction and eta from [0, 0.105, 0.005]. Use the measurement-aware expected-profile forward model, MSE objective, q bounds [-0.8,0.8] per coordinate, eta bounds [(-0.06,0.06),(0.08,0.13),(0.0,0.01)], and options maxiter=60, ftol=1e-9, gtol=1e-7, maxls=20.

For the physics-only neutral baseline, run the same objective, bounds, and optimizer once for each of the 154 unique observed test profiles, initialized at q=[0,0] and eta=[0,0.105,0.005]. It does not depend on model seed. No q_true or eta_true is passed into either optimizer or its initialization; truth is used only after each optimization returns to compute metrics. All failures, iterations, bounds, and runtimes are retained.

This is a supplemental pass over the already-opened frozen test set, not a new test set or a new selection round. No hyperparameter search, restart, result-dependent change, or retraining is permitted. The unchanged primary decision remains based on the frozen preregistered direct q/a/c criteria.
