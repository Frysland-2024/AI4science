# XRD Robustness V9-T

本目录实现基于在线物理扰动的七晶系 PXRD 鲁棒分类。核心比较是 matched Dynamic ERM 与 Dynamic JS Consistency；当前选择为 ResNet-18-GN、identity preprocessing、AdamW、constant LR、`lambda_js=60`。

> 当前模式：**evidence freeze / manuscript building**。不要默认启动训练、重跑 frozen Test 或重做方法选择。完整当前状态见 [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) 和 [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)。

## 科学边界

- 模型输出 7 个晶系 logits；当前代码没有晶格常数、相分数、应变、峰宽、织构等回归目标。
- 在线模拟器生成配对物理扰动视图；JS 项约束同一 parent structure 的预测一致性。
- active split 为 Train 9,842 / Validation 2,109 / Test 2,109，并且只证明 exact-parent-disjoint。
- frozen simulated Test 的主结果为 mean single-factor OOD Macro-F1 Δ `+0.054600`，5/5 training-seed pairs 为正。
- 旧 `per_crystal_system_f1` diagnostic 的实现有误；正确 class F1 已由 full-panel confusion matrix 复核，主 Macro-F1、worst-class F1 和 summary 不受影响。
- RRUFF-301 few-shot 结果可作为 retrospective validation；历史执行 provenance 不完整，不能表述为 confirmatory evidence。

## 代码地图

| 路径 | 作用 |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | 当前 ResNet-18-GN backbone |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM、JS 及归档目标函数 |
| `src/xrd_robustness/simulator.py` | PXRD forward perturbation simulator |
| `src/xrd_robustness/online_views.py` | 确定性配对在线视图 |
| `scripts/train_v7.py` | 当前共享训练入口；文件名旧但仍被 V9-T 使用，不能按版本名删除 |
| `scripts/run_v9_resnet_js_simulated_test.py` | frozen Test runner；当前 source hash 与历史执行绑定不同，不得借修复重跑 Test |
| `src/xrd_robustness/evaluation/rruff301_replay.py` | RRUFF-301 retrospective audit/replay contract |

PAMPT、Residual、V10 和 opXRD 相关文件保留失败机制、NO_GO 或未来重启条件，是科学记录而非当前论文主比较。

## 权威证据

| 文件 | 内容 |
|---|---|
| `reports/v9_resnet_js_ten_run_summary.json` | 五组 paired Validation replication |
| `reports/v9_resnet_js_simulated_test_summary.json` | frozen simulated Test 主汇总 |
| `reports/v9_resnet_js_simulated_test_audit.json` | Test checkpoint/panel/summary 绑定 |
| `reports/v9_resnet_js_simulated_test_class_metric_correction.json` | named class-F1 纠错 sidecar |
| `reports/v9_formal_split_identity_overlap_audit.json` | exact-parent 与 exact-formula 重叠边界 |
| `reports/rruff301_existing_artifact_lineage_audit.json` | RRUFF-301 各 artifact 的实际核验层级 |
| `reports/rruff301_retrospective_replay_episode_plan.json` | 新 retrospective plan；不是历史 episode plan，也未获执行授权 |

冻结 raw outputs、data、checkpoint 和生成谱图位于 Git 忽略区域，不得为“仓库清理”而修改、移动或提交。

## 安装与测试

```powershell
cd E:\AI4science\xrd_robustness
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pip install -e ".[test]"
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q
```

## 只读核验

```powershell
# frozen Test class metric correction；不改 raw JSON
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_v9_simulated_test_class_metrics.py --check-only

# exact-parent isolation 与 formula overlap 范围
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_formal_split_identity_overlap.py --check-only

# 已有 RRUFF-301 artifact lineage；缺少注册证据时非零退出
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only

# 只生成/核验新的 retrospective plan，不加载模型或谱图
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\run_rruff301_retrospective_replay.py plan-replay --check-only
```

`run_rruff301_retrospective_replay.py run-replay` 必须在模型或谱图加载前返回 `refused_execution_not_authorized`；提供 `--authorization` 路径也不能开启它。

## 贡献与数据规则

- 不提交 `data/`、`outputs/`、checkpoint、optimizer state、虚拟环境、文献 PDF、第三方仓库或凭据；
- 不使用 `git add .` 或 `git add -A`；
- 代码变更必须运行相关定向测试，交接前运行完整 pytest；
- 新实验需要单独科学理由、明确授权和新的空输出根目录；不能通过修改历史 artifact 或重命名旧结果来制造 confirmatory lineage。
