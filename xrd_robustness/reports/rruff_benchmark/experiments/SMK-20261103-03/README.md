# SMK-20261103-03 — external-test-only interface smoke

This run verifies the inference-only path needed by zero-RRUFF-training protocols. It used the frozen Dynamic JS checkpoint and a test-only seven-spectrum split from the repository's explicitly smoke-only fixture. No RRUFF sample was used for training or validation; optimizer steps and new JS views were both zero.

- One test evaluation: Accuracy 0/7 = 0.0000, Macro-F1 0.0000, ECE-15 0.830781.
- Runtime was 0.9859 s; RTX 4060 Laptop GPU peak allocation was 64,485,376 bytes.
- This is a pipeline check, not a literature result or a training-parent curve point. The metric is shown to document the complete inference/export path, not as model evidence.
- `result.runner_output_raw.json` is the unchanged runner output. `result.json` only corrects the checkpoint field label because the initial inference-only serializer called the saved model “fine-tuned”; the original checkpoint SHA, metrics, and logs are unchanged. The runner now writes the accurate `final_model_checkpoint` field.
- No `training_steps.jsonl` exists because this run had zero training steps. Split manifest, sample IDs, raw vectors, and derived checkpoint remain local; predictions use SHA-256 IDs.

Files: raw and normalized JSON results, metric CSV, and hashed-ID prediction CSV.
