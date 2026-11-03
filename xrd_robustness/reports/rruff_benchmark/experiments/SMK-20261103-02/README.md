# SMK-20261103-02 — online Dynamic JS and CE smoke

This is the end-to-end smoke using the existing online simulator path. It is not a paper comparison and is excluded from the RRUFF Accuracy versus synthetic-parent curve.

- Synthetic stage: 7 distinct parents (one per crystal system) taken from the frozen historical training split; 1 epoch, batch size 2, 4 optimizer steps, Dynamic JS with `lambda_js=60`, and 14 views rendered online. Peak tables and split source remain local; their hashes are recorded in `result.json`.
- Real stage: 21 train / 7 validation / 7 test spectra from the explicitly smoke-only 35-spectrum fixture; 1 CE-only epoch, 11 steps, 21 real training spectra; no real JS pairs.
- One test evaluation: Accuracy 3/7 = 0.428571, Macro-F1 0.333333, 15-bin ECE 0.370327. The seven-item test is only a pipeline diagnostic.
- Compute: NVIDIA GeForce RTX 4060 Laptop GPU (8 GB); peak allocated memory 280,803,840 bytes. Dynamic JS stage elapsed 0.6536 s; real CE/evaluation stage elapsed 0.2786 s; 15 total optimizer steps. The command process wall time was 5.91 s including Python startup and data/model setup.
- The raw `result.json` was emitted before the runner's final timing/provenance-schema patch: its `runtime_seconds_total` field measures only the real fine-tune/evaluation/export segment and must not be read as full-run time. The raw file is kept unchanged. The current runner now records full invocation time and source/config hashes for subsequent runs.
- The 52 MB derived checkpoint and raw split manifest are not committed. Predictions use SHA-256 sample identifiers. The local full output is under ignored `xrd_robustness/outputs/rruff_js_benchmark/SMK-20261103-02_run/`.

Files: `result.json` (raw run record), `result_metrics.csv`, `training_steps.jsonl` (online JS and real CE per-step log), and `test_predictions.csv` (hashed-ID predictions).