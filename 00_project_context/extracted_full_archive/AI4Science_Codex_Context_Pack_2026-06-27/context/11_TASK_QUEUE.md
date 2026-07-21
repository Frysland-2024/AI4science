# 11 — Current Task Queue

## P0 — Establish a safe foundation

1. Inventory repository/data assets and write `data_card.md`.
2. Verify source IDs, labels, data shape, coordinate grid, normalization, and source license.
3. Create leakage-safe structure-level split manifest.
4. Build a minimal deterministic loader and visualization script.
5. Implement an auditable clean 1D-CNN baseline with smoke tests.

## P1 — Build the perturbation framework

6. Create shift, broadening, noise, and background transforms with config-driven parameters.
7. Build an evidence-ledger schema and transform gallery.
8. Implement transform identity/zero-severity/sanity tests.
9. Implement paired-view datasets without cross-split leakage.

## P2 — Build reliability evaluation

10. Implement clean/perturbed accuracy, FlipRate, JS/KL disagreement, calibration metrics, and churn.
11. Generate per-perturbation/per-severity and class-wise reports.
12. Store per-sample prediction tables for later audit.

## P3 — Compare interventions

13. Implement E0–E3 ablation conditions.
14. Add config sweeps and multi-seed execution.
15. Produce paired statistical comparisons and failure galleries.

## P4 — Close the sim-to-real loop

16. Identify real-XRD data source and write a data card.
17. Implement conservative preprocessing adapter.
18. Run small external validation with explicit limitations.

## Expected Codex behavior

Complete tasks in dependency order. Do not jump to P3/P4 while P0 uncertainties remain unresolved.
