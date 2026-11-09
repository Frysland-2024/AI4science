# Research archive

This index preserves scientific provenance without turning the public README into a chronological incident log.

## Research trajectory

**FerroAI → seven-system PXRD classification → same-parent measurement consistency → exploratory quantitative inversion → return to classification.**

- [Project history](../docs/PROJECT_HISTORY.md): dated decisions and rationale.
- [Current scientific state](../docs/CURRENT_STATE.md): current evidence and pending work; newer decisions supersede older execution plans.
- [Frozen classification results](../xrd_robustness/reports/RESULTS.md): evidence and limitations.
- [Calibration](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md) and [parent-budget study](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).
- [Historic presentation assets](../docs/showcase/HISTORICAL_PRESENTATION.md).

## Historical work, not active tasks

Parameter inversion, DONUT-inspired PXRD, forward reconstruction and AutoLab are retained as historical research evidence, including negative outcomes. See closed PRs #36, #42, #43, #45 and #46 and their linked reports. Their existence does **not** authorize new experiments.

## Retired GitHub Actions (2026-11-09)

These two historical CI workflows were already removed from the active `main` tree before this inventory. They executed **CPU-only validation**, not production GPU experiments. The owner requested archiving their metadata before deleting the four GitHub Actions **run records** so that old workflow names no longer clutter the Actions sidebar. Their original YAML remains recoverable in Git history; deleting an Actions run removes its hosted log/artifacts and does not change scientific data or the Git commits.

| Historical workflow (Git source) | Purpose | Historical Git revision | Recorded runs (UTC, status) |
| --- | --- | --- | --- |
| `PXRD AutoLab P0` ([YAML at revision](https://github.com/Frysland-2024/AI4science/blob/e92066b2dab61b39aa8838674af789ccf4d8c52c/.github/workflows/pxrd-autolab-p0.yml)) | Install `pxrd_autolab[test]`, run failure/report tests and a CPU fixture smoke; **not** an actual research training result | `e92066b2dab61b39aa8838674af789ccf4d8c52c` | `39119567577` (2026-10-18 10:31:06, push, success), `39119583230` (2026-10-18 10:31:20, PR, success) |
| `Research Task Bridge tests` ([YAML at revision](https://github.com/Frysland-2024/AI4science/blob/0bbd3528baab92a49b0567f55368033b3b348959/.github/workflows/research-task-bridge.yml)) | Python unit tests for historical task bridge, with no GPU or scientific data | `0bbd3528baab92a49b0567f55368033b3b348959` | `39121396653` (2026-10-18 10:59:13, push, success), `39121412176` (2026-10-18 10:59:27, PR, success) |

**Deletion confirmed (2026-11-09):** all four run records above were checked as `completed/success`, then removed through GitHub Actions with name/path verification; subsequent individual GitHub REST lookups returned `404 Not Found`. Their Git source revisions and run metadata remain in this archive; hosted run logs/artifacts are not retained. **Current CI at the time of those two retirements** also included the merged-PR branch cleanup; that workflow was subsequently retired as described below.

### Merged-PR branch cleanup retirement (2026-11-09)

`Remove merged PR branches` was a temporary GitHub Actions workaround for the repository setting `delete_branch_on_merge=false`. The owner subsequently enabled GitHub's **native automatically delete head branches** setting; the repository API now reports `delete_branch_on_merge=true`. The standalone branch-deletion job is therefore **redundant and retired**. Historical YAML: [original workflow in Git history](https://github.com/Frysland-2024/AI4science/blob/52f5b2d9c5227131ff77db6a2984076abb2c22e4/.github/workflows/pr-merged-branch-cleanup.yml). It deleted only unchanged merged PR head branches and preserved in-use branches; it was not a research or GPU workflow.

Checked run inventory before retirement (UTC): `42504247434` (2026-11-08 17:17:53, success), `42505778135` (2026-11-08 17:36:06, success), `42506249341` (2026-11-08 17:41:56, skipped). All three GitHub-hosted Actions run records were deleted after per-run identity/status checks; subsequent REST lookups returned `404 Not Found` (verified 2026-11-09). Run IDs, outcomes, and the historical YAML revision remain preserved here. **Active CI going forward:** XRD tests, Docs Consistency (including PR Hygiene), and V11 server pipeline checks. GitHub's native branch deletion replaces the standalone workflow.

## Retention policy

Keep original results, immutable configs, data provenance, negative results, and relevant commits. Do not move or delete evidence files solely to simplify navigation. Summarize only major direction changes; routine ideas and abandoned brainstorming do not require new permanent documents. Active tasks live in [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61) and [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).
