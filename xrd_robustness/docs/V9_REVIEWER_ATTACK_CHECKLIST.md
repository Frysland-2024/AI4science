# V9 Reviewer Attack Checklist

Use this before interpreting any formal result. An item is closed only by a current artifact or hash, not by intent.

| Likely challenge | Required answer/evidence | Current status before formal runs |
|---|---|---|
| Did one method simply see more spectra? | Shared structure exposures, paired-view exposures, optimizer steps, accepted parameter pairs, and pair-schedule hashes. | Interface ready; formal evidence pending. |
| Why these λ values? | Registered engineering candidates plus Train-only numerical scale audit; final choice on unified Validation only. | Scale audit complete; selection pending. |
| Is there structure leakage? | Parent-structure and structure-fingerprint split audits. | Current parent-structure split audit passes with zero overlap. |
| Does checkpoint resume change the experiment? | Uninterrupted versus resumed future IDs, parameter pairs, loss, global step, stream snapshot, and model hash. | Closed by `reports/v9_resume_determinism_audit.json`. |
| Is Residual better only because it has an extra head? | Same backbone and training-view budget; auxiliary parameter count reported; direct Residual–JS paired comparison. | Analysis contract ready; formal comparison pending. |
| Was real XRD used for tuning? | Disabled contract, absent/unfrozen manifest, preprocessing-only audit, explicit unlock record. | Locked; no spectra or model loaded. |
| Are simulator frequencies claimed to be real prevalence? | State that `apply_probability` controls training exposure only. | Wording frozen. |
| Does the residual represent a physical measurement variable? | Make no such identification claim; report only class leakage, probe behavior, scale, rank, and generalization. | Wording frozen. |
| Are three seeds enough for bootstrap? | Resample paired independent parent-structure clusters within each seed; average across all registered seeds; show every seed delta. | Implemented; formal rows pending. |
| Was only mean OOD reported while ID collapsed? | Always report paired ID delta and label an OOD-gain/ID-loss tradeoff. | Conclusion rule tested synthetically. |
| Was Residual superiority inferred indirectly? | Compute the direct `Residual - JS` contrast and hierarchical 95% interval. | Implemented. |
| Did quality-gate retries bias methods differently? | Same accepted rows and retry algorithm; stream hashes and rejection counts. | Formal evidence pending. |
| Were negative smoke results used to redesign the hypothesis? | Smoke and numerical audits are engineering evidence only. | Prohibited by protocol. |
| Can the result be replayed on a new machine? | Migration manifest, hash verification, first-boot acceptance, self-contained checkpoint stream state. | Laptop rehearsal required after final changes. |

## Stop conditions

Stop interpretation and do not publish a comparison if any method differs in split, evaluation manifest, pair schedule, accepted parameter pairs, compute budget, source/config hash, or test-lock state. Stop real-test work if its manifest/hash/overlap audit is not frozen or explicit authorization is absent.
