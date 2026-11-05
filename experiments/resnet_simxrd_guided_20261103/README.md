# SimXRD-inspired ResNet A0/A1/A2 — bounded validation-only experiment

Generated 2026-11-03T04:50:19.637465+00:00; dataset: 14,060 unique CIF parents, fixed parent-disjoint V10 protocol.

## Tested configurations

| Variant | Residual stage strides | Residual kernel | Parameters | OOD Macro-F1 @ 6,160 | OOD Macro-F1 @ 12,320 | Time (s, training done) |
|---|---|---:|---:|---:|---:|---:|
| A0 | 4/4/4 | 9 | 13,008,839 | 0.57530 | 0.67228 | 1392.8 |
| A1 | 4/2/4 | 9 | 14,843,847 | 0.58945 | 0.63702 | 828.3 |
| A2 | 4/2/4 | 5 | 9,961,415 | 0.55845 | 0.64453 | 786.4 |

## Interpretation (bounded, no RRUFF-driven selection)

- A1 vs A0 at 12,320 steps: -0.03527 Macro-F1.
- A2 vs A1 at 12,320 steps: +0.00752 Macro-F1.
- Differences are descriptive for one seed and one short budget. No statistically supported final winner.
- A2 changes kernel/receptive field **and model parameter count**; check memory and compute before scaling.
- Existing A0 was trained for 49,280 steps; only its 6,160- and 12,320-step checkpoints are used here.
- All models use identical 14,060-parent dataset/split, V10 simulator, validation panels, paired views, CE+JS lambda=60, LR=1e-4, batch 16 and seed.
- This is NOT a final full-budget three-seed result and does NOT establish RRUFF advantage.
- Original historical checkpoints and failed CNN11 pilot have not been altered.

## Suggested next scientific decision

Consider the one-seed validation differences together with increased/decreased train cost. Only a promising candidate should receive full 49,280-step multi-seed validation, and still not select on RRUFF/Test.

## Reproducibility

- Code launchers, copied runner and simulation/model source snapshots, resolved protocols, per-seed histories/logs, model checkpoint hashes and summary.json are in this PR.
- No 8GB GPU weight/checkpoint files, CIF structures, private RRUFF spectra or large cached validation panels were uploaded.
- The runner snapshot imports local xrd_robustness modules; this is a record of the exact local experiment environment, not a self-contained installable package.
