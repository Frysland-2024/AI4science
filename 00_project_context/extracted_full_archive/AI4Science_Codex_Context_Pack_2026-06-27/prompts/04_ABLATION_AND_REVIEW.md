# Codex Task — Ablation, Reliability Metrics, and Review

Prerequisite: clean baseline and vetted perturbation framework.

Read `AGENTS.md`, `context/03_EXPERIMENT_PROTOCOL.md`, `context/04_PHYSICAL_VALIDITY.md`, and `context/12_REPRODUCIBILITY_OUTPUT_CONTRACT.md`.

Task:

1. Implement E0–E3 exactly as defined in the experiment protocol.
2. Implement paired-view metrics: clean/perturbed accuracy, FlipRate, JS/KL disagreement, confidence change, ECE, and churn across K views.
3. Build result tables stratified by perturbation family, severity, and class.
4. Store per-sample prediction records and generate reproducible figures from result tables.
5. Prepare a `reports/experiment_review.md` template that forces discussion of:
   - clean accuracy;
   - robustness/stability;
   - calibration;
   - augmentation-only control;
   - possible collapse/trivial predictions;
   - limitations and unverified physical assumptions.

No conclusion should claim that consistency learning is better merely because one aggregate metric improved.
