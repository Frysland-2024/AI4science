# CNN11 numerical diagnosis — historical extraction (2026-11-09)

Source: [PR #63](https://github.com/Frysland-2024/AI4science/pull/63). This is a **historical evidence extraction**, not a claim that its implementation is merged into main.

## Supported observations

- The original V10 CNN11 training experienced non-finite numerical behavior. Its exact original trigger was **not proven**.
- A reproducible gradient vulnerability was demonstrated for extreme BF16 logits in the older JS/KL implementation. Merely casting logits to FP32 was insufficient; the tested stable FP32 CE/JS formulation using `logaddexp` passed the numerical regression.
- A partial, single-seed CNN11 recovery reached step 24,640 without nonfinite updates. On matched validation at that step, mean six-profile OOD Macro-F1 was **0.629091** for CNN11 versus **0.696204** for ResNet. This is not a matched full three-seed architecture comparison.
- The engineering decision was to **retain ResNet-18-GN + same-parent Dynamic JS** for the bounded study. No claim of universal CNN11 inferiority is justified.

## Code extraction gate

Before reusing code from #63, independently port only the stable FP32 CE/JS objective and its gradient regression tests to current main, verify compatibility with V11 and all existing objective tests, and confirm no old V10 renderer, obsolete experiment configuration, or frozen result is overwritten. The original PR is preserved for source and provenance. Do not call the code extracted/merged until those checks are completed.
