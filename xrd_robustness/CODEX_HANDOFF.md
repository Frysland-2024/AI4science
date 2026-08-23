# XRD Robustness V9-T — Current Handoff

**Status date:** 2026-08-23

**Mode:** evidence frozen; manuscript/figure construction

**Authority:** [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)

## Start here

不要把本仓库当作待继续调参的实验分支。V9-T 的方法选择、五组 paired Validation replication 和 frozen simulated Test 已完成；默认工作是核验现有证据、维护 claim boundary、完成论文和图表。

冻结方法：

- 7-class crystal-system classification；
- ResNet-18-GN；
- Dynamic ERM vs Dynamic JS Consistency；
- selected `lambda_js=60`；
- identity preprocessing、AdamW、constant LR；
- Train 9,842 / Validation 2,109 / Test 2,109；exact-parent-disjoint only。

## Frozen results

| Evidence | ERM → JS | Result |
|---|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 → 0.705064 | Δ `+0.046569`; 5/5 positive |
| Frozen simulated Test mean single-factor OOD Macro-F1 | 0.65074 → 0.70534 | Δ `+0.054600`; 5/5 positive |
| RRUFF-301 K=1/2/5 few-shot | see lineage audit | Δ `+0.0433/+0.0460/+0.0545` |

RRUFF-301 只能称为 retrospective validation。In manuscript terms, this is
**retrospective evidence, not confirmatory evidence**. 缺少完整历史 execution
provenance 是 **claim limitation**，不是当前 blocker，不授权补跑或重新包装历史结果。

## Active code entrypoints

| Path | Role |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN backbone |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM/JS objectives |
| `src/xrd_robustness/simulator.py` | PXRD perturbation simulator |
| `src/xrd_robustness/online_views.py` | deterministic paired online views |
| `scripts/train_v7.py` | shared V9-T training entrypoint; legacy filename, still active |
| `scripts/run_v9_resnet_js_simulated_test.py` | frozen Test runner; audit reference only, do not rerun |
| `src/xrd_robustness/evaluation/rruff301_replay.py` | retrospective audit/replay contract |

Repository cleanup deliberately keeps only active/reusable entrypoints. One-off runners and closed-branch implementations are summarized in the Journey/evidence index and recoverable from Git history.

## Evidence map

Start with [`reports/EVIDENCE_INDEX.md`](reports/EVIDENCE_INDEX.md). Machine-readable authorities are:

- `reports/v9_resnet_js_ten_run_summary.json`;
- `reports/v9_resnet_js_simulated_test_summary.json`;
- `reports/v9_resnet_js_simulated_test_audit.json`;
- `reports/v9_resnet_js_simulated_test_class_metric_correction.json`;
- `reports/v9_formal_split_identity_overlap_audit.json`;
- `reports/rruff301_existing_artifact_lineage_audit.json`.

The old named class-F1 diagnostic was wrong; the correction sidecar is authoritative. Aggregate Macro-F1, worst-class F1 and frozen Test summary remain unchanged.

## Hard locks

Without a new scientific question, explicit authorization and a new empty output root:

- do not train or tune;
- do not rerun frozen Test;
- do not replace checkpoints;
- do not infer confirmatory status from retrospective RRUFF artifacts;
- do not execute `run-replay`;
- do not execute sealed future modules.

`run_rruff301_retrospective_replay.py run-replay` must remain fail-closed before model or spectrum loading.

## Repository shape and data boundary

After the 2026-08-23 cleanup, `scripts/`, `configs/` and `reports/` each contain at most 10 direct files. `configs/provenance/` has three hash-bound contracts and `reports/provenance/` has eight hash-bound audits; neither is an overflow archive. Tests retain high-value regression coverage and are grouped so every maintained test directory contains at most 10 direct files.

Do not commit or clean away ignored datasets, raw outputs, generated spectra, checkpoints, optimizer state, virtual environments, PDFs, third-party repositories or credentials. These local evidence assets are outside the tracked-source cleanup.

## Verification

```powershell
cd E:\AI4science\xrd_robustness

# Full maintained suite
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q

# Frozen Test named-class correction; read-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_v9_simulated_test_class_metrics.py --check-only

# Exact-parent isolation and formula-overlap boundary; read-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_formal_split_identity_overlap.py --check-only

# Existing RRUFF artifact lineage; read-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only
```

## Known limitations and next work

- split claim is exact-parent only;
- simulated improvement is aggregate, not universal across classes/conditions;
- RRUFF evidence is retrospective because historical provenance is incomplete;
- V9-T is classification, not physical-parameter inversion.

The current blocker is unfinished manuscript/figure construction and claim-boundary review. The next command is the full pytest command above; after it passes, continue manuscript assembly from frozen evidence.

The known-template tetragonal `(a,c)` inversion design is registered at [`../00_project_context/future_modules/PXRD_ROBUST_LATTICE_PARAMETER_INVERSION.md`](../00_project_context/future_modules/PXRD_ROBUST_LATTICE_PARAMETER_INVERSION.md) as **SEALED_FUTURE_MODULE** and is not authorized for execution.
