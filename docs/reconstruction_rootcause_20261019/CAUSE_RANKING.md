# Cause ranking

| Rank | Candidate cause | Evidence | Status / discriminating test |
|---|---|---|---|
| 1 | V9 zero-shift nuisance prediction is weak and coupled to q error | Old validation B shift MAE `0.02276–0.03156°`; du/shift-error correlation `0.853–0.949` across seeds. | Leading hypothesis, not causal proof. D adds zero-shift simulator labels. Support requires better held-out q and shift error under frozen criteria; lower shift error without q/a/c gain refutes the proposed causal link. |
| 2 | V9 multi-objective gradient conflict | Corrected raw audit: q gradients negative in 6/15 V9 batches; shared trunk negative in 4/15. Simple had no negative batches. | Measured intermittent mechanism, not established as the dominant cause. D retains the q reconstruction gradient so this effect remains observable. |
| 3 | Optimization/checkpoint variability | Three seeds only; prior histories vary in best epoch and final validation quality. | Plausible contributor. Report paired seed outcomes; do not infer population-level significance from three seeds. |
| 4 | Physical-model mismatch or nuisance non-identifiability | Fixed-shape Issue19 gates passed. Free background-shape parameters failed identifiability (`condition≈3.06e16`, correlation 1) and were excluded. | Not the leading explanation for the fixed-shape A/B/D comparison. Any source/config drift or gate regression stops training. |
| 5 | Old evaluation-compute mismatch / task mismatch | PR26 A/B used unequal post-hoc fitting compute; DONUT numbers mixed texture-OOD and ordinary noisy profiles with different initializations. | Reporting/design flaws explain those comparisons, not the underlying model's V9 q error. Fresh evaluation uses matched splits, architecture, selection, and profile-fit budget. |

The ordering is specific to the single-CIF synthetic V9 setup. The new D arm uses extra simulator labels; it tests whether this information addresses the observed bottleneck, not whether D is a fair equal-information replacement for B.
