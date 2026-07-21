# Codex Task — Clean Baseline

Prerequisite: the P0 data audit and split manifest exist.

Read `AGENTS.md`, `context/02_SIMXRD_XRD_RELIABILITY_SPEC.md`, `context/03_EXPERIMENT_PROTOCOL.md`, and `context/12_REPRODUCIBILITY_OUTPUT_CONTRACT.md`.

Task:

1. Implement a transparent, compact 1D-CNN clean ERM baseline (`E0`) for the verified label taxonomy.
2. Make all settings config-driven and record a complete run manifest.
3. Train only after confirming source-structure-level splits.
4. Export clean accuracy, class-wise accuracy, confusion matrix, NLL/Brier/ECE when applicable, and per-sample predictions.
5. Add smoke tests for a one-batch train/eval pass and deterministic inference under a fixed seed.
6. Write a short `reports/baseline_design.md` explaining all nontrivial preprocessing/model choices and what remains provisional.

Do not optimize architecture aggressively. Establish an auditable baseline first.
