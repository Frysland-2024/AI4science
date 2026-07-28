# CNN Clean A/B/C diagnostic summary

**Scope:** development-only Validation evidence; no simulated Test or real XRD.

| Run | Preprocess | Optimizer | Schedule | level0 | in-range | mean single OOD | worst F1 | best epoch/step | decision |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| baseline | identity | adamw | constant | 0.6522 | 0.1827 | 0.4032 | 0.4950 | 100/61600 | SELECTED |
| A | sqrt | adamw | constant | 0.6455 | 0.2399 | 0.3423 | 0.4949 | 20/12320 | NOT_SELECTED |
| B | identity | adam | constant | 0.6200 | 0.1897 | 0.3843 | 0.4737 | 20/12320 | NOT_SELECTED |
| C | identity | adamw | linear_warmup_3080_steps_then_cosine_to_zero | 0.6108 | 0.1762 | 0.3902 | 0.4676 | 100/61600 | NOT_SELECTED |

## Decision

No A/B/C candidate reached the preregistered level0 threshold `0.6722`. The shared Clean configuration is therefore `ResNet-18-GN + identity + AdamW + constant LR`.

Clean hyperparameter search is closed. The only next authorized experiment is one matched ResNet Dynamic ERM diagnostic. The formal 7-run remains 0/7.

These results are not formal paper performance claims.
