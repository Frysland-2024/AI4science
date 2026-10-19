# DONUT-PXRD four-stage technical report

**Terminal status: all four experiments technically COMPLETE; the numeric findings include weak or negative DONUT-PXRD inversion performance.**

This is a single public BaTiO₃ P4mm (COD 9014273) synthetic conditional-q interpolation study. It adapts the dual-branch unsupervised mechanism from DONUT to 1D powder profiles; it does not reproduce the original 2D SXDM geometry or numerical figures and does not establish performance on real PXRD or unseen materials.

| Stage | Status | Evaluation | Result |
|---|---|---|---|
| 1 | COMPLETE | 3 seeds × 77 test parents | q mean MAE 0.3162; weak recovery |
| 2 | COMPLETE | 3 seeds × 77 test parents | q mean MAE 0.3313; shift MAE 0.0298°; weak recovery/confounding |
| 3 | COMPLETE | 3a/3b/3c each 3 seeds × 77; texture OOD on same parents | 3c q mean MAE 0.2894; texture remains generator-side nondifferentiable OOD stress |
| 4 | COMPLETE | 5 methods × same 77 parents; A–D have 3 seeds | E best-of-three q MAE 0.000358565; D direct q MAE 0.2894 ± 0.0375; see full table |

Experiments 1–3 were audited in place; none were rerun. All 15 pre-existing checkpoints retained their recorded SHA-256 and load successfully. Experiment 4 used the frozen exp3c spectra, split and pre-registration. A/B/C retraining used q labels only for their supervised q objective; reconstruction branches consumed only predicted q/eta and observed spectra. All methods share the 77 held-out parent identities. No test-driven tuning occurred.

The local physics gates passed forward-render parity, finite-difference gradients, parameter identifiability bounds and non-oracle recovery checks. Both DONUT decoder and physics losses backpropagate to its encoder. The scientific outcome is mixed: direct A/B/C networks recover q substantially better than D on this narrow synthetic condition, while the bounded optimizer reaches very low residuals from most starts. These results are not transferable beyond this fixed material/task without independent evaluation.

Training used 610.56 recorded GPU seconds in total (252.72 for the pre-existing stages plus 357.84 for exp4 A/B/C), below the 8 GPU-hour cap. Per-method details, raw outcomes, failures, runtimes, hashes, and limitations are in [Experiment 4](EXPERIMENT_4.md), stage reports, `../results/study_v1/exp4/summary.json`, `raw_paired_results.json`, and `validation.json`.

Recovery: the initial default-sandbox process failed to write new checkpoints to the explicitly designated external checkpoint directory. Its training duration was not retained and is excluded from the recorded compute total. The same frozen protocol was rerun under reviewed authorization; no existing checkpoint was overwritten. The 15 original checkpoint hashes were rechecked after completion. The recorded successful-run total is below the 8-hour cap; unrecorded time is not claimed as measured.

Source links: [Luo et al., DONUT (2025)](https://doi.org/10.1038/s41524-025-01860-7); [official DONUT code](https://github.com/AdvancedPhotonSource/DONUT), pinned at `090c10bdf99333d3670dc26e617a93364f714bdc`. The detailed source fidelity boundary is recorded in `SOURCE_FIDELITY_AUDIT.md`.
