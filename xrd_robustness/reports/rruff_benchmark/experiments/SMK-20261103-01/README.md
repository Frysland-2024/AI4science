# SMK-20261103-01 — pipeline smoke only

This run checks the new split → Dynamic JS checkpoint load → real-spectrum CE fine-tune → single inference → metrics/export path. It is not a paper comparison and is excluded from the RRUFF accuracy vs. synthetic-parent curve.

- Input: local `rruff_pipeline_test` fixture, five records per crystal system; generated split is 21 train / 7 validation / 7 test. The split manifest includes sample IDs and stays in the local ignored output tree; the split hash is recorded in `result.json`.
- Initial model: existing frozen Dynamic JS ResNet-18-GN checkpoint; SHA-256 is recorded in `result.json`.
- New training in this smoke: 21 real spectra, one CE-only epoch, 11 optimizer steps, no synthetic parent additions, zero online-generated JS views, and no real-spectrum JS pairs.
- Outcome: Accuracy 1/7 (0.142857), Macro-F1 0.095238, 15-bin ECE 0.579367. The test set has only seven samples; these values diagnose code flow only.
- Resource use: 282,638,848 peak allocated GPU bytes; 1.7349 s fine-tuning stage; 12.10 real training spectra/s. Device: NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB.
- `test_predictions.csv` contains SHA-256 sample identifiers rather than raw RRUFF IDs. Raw measured vectors and the 52 MB derived checkpoint are not committed. The local full output remains under ignored `outputs/rruff_js_benchmark/SMK-20261103-01/`.

Files: `result.json` (run record), `result_metrics.csv` (metric row), `training_steps.jsonl` (per-step losses), `test_predictions.csv` (hashed-ID predictions).