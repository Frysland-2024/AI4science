# XRD Robustness V9-T

本目录实现基于在线 PXRD 物理扰动的七晶系鲁棒分类。当前比较是 matched Dynamic ERM 与 Dynamic JS Consistency；选定配置为 ResNet-18-GN、identity preprocessing、AdamW、constant LR、`lambda_js=60`。

> 2026-08-23：Validation ten-run 与 frozen simulated Test 已完成，项目处于 evidence freeze / manuscript building。不要默认启动训练或重做方法选择。

## Scientific boundary

- 输出是 7 个晶系 logits，不是晶格常数、相分数、应变、织构或峰宽。
- 配对在线视图共享 parent-structure provenance；JS 项约束 measurement-equivalent views 的预测一致性。
- split 为 Train 9,842 / Validation 2,109 / Test 2,109，只支持 exact-parent-disjoint claim。
- frozen Test mean single-factor OOD Macro-F1 Δ `+0.054600`，5/5 seed pairs 为正；这是 aggregate synthetic-OOD 证据。
- RRUFF-301 只作为 retrospective validation。provenance 缺口是 claim limitation，不是当前 blocker。

完整状态见 [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)，工程交接见 [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)，冻结证据见 [`reports/EVIDENCE_INDEX.md`](reports/EVIDENCE_INDEX.md)。

## Code map

| Path | Purpose |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN backbone |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM/JS objectives |
| `src/xrd_robustness/simulator.py` | PXRD physical perturbations |
| `src/xrd_robustness/online_views.py` | deterministic paired views |
| `scripts/train_v7.py` | active shared training entrypoint despite legacy name |
| `scripts/run_v9_resnet_js_simulated_test.py` | frozen Test reference runner; do not rerun |
| `src/xrd_robustness/evaluation/rruff301_replay.py` | retrospective lineage/replay contract |

## Directory contract

- `src/` contains reusable implementation;
- `scripts/` contains no more than 10 direct current entrypoints;
- `configs/` contains no more than 10 direct frozen contracts;
- `reports/` contains no more than 10 direct evidence files, including the consolidated index;
- `tests/` retains high-value regressions and is grouped by topic, preferably no more than 10 direct files per directory.

Closed experimental branches, duplicate reports and one-off runners are summarized in `PROJECT_JOURNEY.md`/`reports/EVIDENCE_INDEX.md`; Git history remains the recovery archive.

## Install and test

```powershell
cd E:\AI4science\xrd_robustness
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pip install -e ".[test]"
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q
```

Read-only evidence checks:

```powershell
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_v9_simulated_test_class_metrics.py --check-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_formal_split_identity_overlap.py --check-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only
```

`run_rruff301_retrospective_replay.py run-replay` must stay fail-closed. The sealed future `(a,c)` inversion module is not part of V9-T and has no execution authorization.

## Data and Git policy

Do not commit datasets, raw outputs, generated spectra, checkpoints, optimizer state, caches, virtual environments, literature PDFs, external repositories or credentials. Stage explicit task paths only; never use `git add .` or `git add -A`.
