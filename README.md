# AI4Science

本仓库的当前研究主线位于 [`xrd_robustness/`](xrd_robustness/)，研究主题是：利用在线 PXRD 模拟器保留的 parent-structure provenance，为同一晶体的不同物理扰动视图提供 measurement-equivalence supervision。

## 当前结论（2026-08-11）

项目实现的是**七晶系 PXRD 鲁棒分类**，不是晶格常数、相分数、应变、织构或其他物理参数反演。当前配对比较为：

- backbone：ResNet-18-GN；
- baseline：Dynamic ERM；
- selected method：Dynamic JS Consistency，`lambda_js = 60`；
- split：Train 9,842 / Validation 2,109 / Test 2,109；
- split 边界：exact-parent-disjoint；不支持 formula、chemical-family、prototype 或 symmetry-equivalence disjoint 的表述。

| 证据 | ERM → JS | 配对结果 |
|---|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 → 0.705064 | Δ `+0.046569`，5/5 为正 |
| Frozen simulated Test mean single-factor OOD Macro-F1 | 0.65074 → 0.70534 | Δ `+0.054600`，5/5 为正 |
| RRUFF-301 few-shot Macro-F1，K=1/2/5 | 见 lineage audit | Δ `+0.0433/+0.0460/+0.0545` |

模拟 Test 支持 aggregate synthetic-OOD robustness 改善，但不代表所有晶系、所有压力条件都改善。RRUFF-301 的数值产物已在声明范围内复核，但原 runner、episode support IDs、独立执行授权、日志和代码/运行时绑定缺失，因此只能称为**retrospective validation**，不能称为 confirmatory evidence。

## 权威入口

| 文件 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前科学状态、证据边界、阻塞项和下一步 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 当前工程交接、关键报告和只读核验命令 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 代码、配置、报告和测试入口 |
| [`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md) | 不可改写的研究决策历史 |
| [`00_project_context/EVIDENCE_FREEZE_V1_20260808.md`](00_project_context/EVIDENCE_FREEZE_V1_20260808.md) | 2026-08-08 冻结快照；冲突处由 2026-08-11 审计取代 |

## 仓库结构

- `xrd_robustness/src/`：模型、在线物理视图、目标函数与评估实现；
- `xrd_robustness/scripts/`：训练入口、只读审计和受门禁执行器；
- `xrd_robustness/configs/`：冻结合同、授权边界与 replay 合同；
- `xrd_robustness/reports/`：Git 可跟踪的汇总、审计和科学记录；
- `00_project_context/`：当前状态、研究历程、申请叙事与未来模块；
- `outputs/`：本地用户交付物，不作为源代码目录。

数据、checkpoint、生成谱图、虚拟环境、文献 PDF 和第三方仓库不进入 Git。Residual、V10、PAMPT、opXRD 等负结果或已关闭分支保留为科学记录，不因退出当前主线而删除。

## 默认工作方式

当前阶段是 **evidence freeze → manuscript building**。默认不新增训练、不重跑 frozen Test、不根据 Test 调参、不替换 checkpoint。

```powershell
cd E:\AI4science\xrd_robustness
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_v9_simulated_test_class_metrics.py --check-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\audit_formal_split_identity_overlap.py --check-only
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s scripts\run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only
```

任何新的真实域 confirmatory claim 都需要单独评审、明确授权和新的空输出根目录，不能通过重新命名历史 RRUFF-301 结果获得。
