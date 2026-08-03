# V9 simulated-Test checkpoint audit

**Recorded:** 2026-08-02 12:43 +08:00  
**Environment:** Tencent Cloud Shanghai, `/root/AI4science`  
**Status:** checkpoint-specific preflight gates passed; full Test preflight still required.

The migrated server contains the ten frozen Validation-selected `best.ckpt` files. Each file was loaded read-only on CPU. Its stored epoch and global step matched the frozen simulated-Test contract exactly.

| Run | SHA-256 | Epoch | Global step |
|---|---|---:|---:|
| seed_20260711_dynamic_erm | `e8bde2871520aede1502e99b1ba5b761358c63b0a98ebac36db384b276f3d40b` | 80 | 49280 |
| seed_20260711_js_lambda_60 | `3ee1beb8831e46a8d7014352d5c1adfac49b7fe8959894811c1cb559b2cc6b49` | 40 | 24640 |
| seed_20260712_dynamic_erm | `f8a025902a72e75dfa7aed00796912a3ef49c6b1bfeb320eb4c32fdcb71668c9` | 90 | 55440 |
| seed_20260712_js_lambda_60 | `af06d30712879bdfe02d9c82e6c713be6a66f1bd50937b2954ec66ee7a11171c` | 80 | 49280 |
| seed_20260713_dynamic_erm | `87b7c264b5818f45e388293fa03e9bcfbe165182b2b75fce0304a6911339ef98` | 100 | 61600 |
| seed_20260713_js_lambda_60 | `2fcf8698e07d47d15b78c6b61a0986dc3976f8960aab26f633306f27e1e5638a` | 80 | 49280 |
| seed_20260714_dynamic_erm | `149c20e32d35565d305b3cccf3ca981118ecc5bcbbba29b04f99fd7c0cec4c4fb` | 90 | 55440 |
| seed_20260714_js_lambda_60 | `c3ac158084fe6b2e1e2a28eb8b010c43532f7612e6c99f1b6c305f66a374be18` | 30 | 18480 |
| seed_20260715_dynamic_erm | `a52a34aee62b71365e45e39742da55e76648c32099eb8d1d7f0deb854f0a33ac` | 80 | 49280 |
| seed_20260715_js_lambda_60 | `87f2516402635ea010af00e987172560bb178f024937e2f57a57c9db331df0d6` | 60 | 36960 |

Checkpoint binaries, optimizer states, datasets, generated spectra, outputs, and caches remain outside Git by repository policy.

Before inference, the full fail-closed preflight must still record the source/evaluation-code hash, verify the 2,109-structure Test split and zero split overlap, generate and freeze the three Test-manifest hashes, verify a clean empty Test output root, verify no previous Test access, and match the authorization file to the frozen contract.

This audit contains no Test prediction and no Test metric.
