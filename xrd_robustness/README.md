# XRD Robustness V9-T

> 跨机器、跨 Codex 账号接管必须先完整阅读根目录 [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)，并运行 `scripts/verify_codex_account_handoff.py`。该交接不构成训练授权。

当前项目正式切换为 **V9-T：算法迁移主线**，不再使用 A/B/C2 或“先 Pilot、再选路线”的叙事。模拟器标签监督残差研究保留已有记录，并延期为 **V10：Simulator-Supervised Representation Learning**。

| 研究 | 优先级 | 核心问题 | 当前状态（2026-07-16） | 研究完成度 |
|---|---|---|---|---:|
| V9-T 算法迁移论文 | 当前唯一主线 | 显式建模同结构跨扰动视图关系，能否在单纯数据增广之上提高未知扰动与真实谱泛化 | family-aware 70/15/15 划分已冻结；方法语义与 Train-only 候选范围 Gate 通过，网格已冻结但 tuning 尚未授权；训练仍为 0/7 调参、0/15 正式实验 | 约 40% |
| V10 Simulator-Supervised Representation Learning | 延期 | 已知模拟器变量能否监督测量变化表征 | 只保留旧原型和研究备忘，不进入 V9-T | 约 15% |

百分比衡量的是完整研究交付物，不代表已有科学结论。候选网格的 Train-only 合法性证据已经闭合，但没有 Validation 调参或正式性能结果，所以完整研究仍约为 40%。真实谱只用于最终 `real test`，不参与扰动参数定义、超参数选择、方法比较或 checkpoint 选择。

## 当前论文的核心叙事

模拟 XRD 数据充足，但测量扰动造成模拟—真实差距。现有方法主要依赖**单纯数据增广**：通过离线预生成、在线动态生成、扩大扰动覆盖或提高模拟真实性，让模型见到更多、更接近实验条件的输入。这些实现形式不同，但都只规定模型“看到了什么”，通常没有显式规定同一晶体结构的不同扰动视图之间应学习什么关系。

V9-T 的递进固定为：**单纯数据增广 → 跨视图一致性 → 差异感知的残差去相关**。Dynamic/Paired ERM 是单纯数据增广范式中最强、最公平的直接基线，同时提供成对视图基础设施；JS Consistency 显式约束预测稳定，Residual Class Decorrelation 则允许测量差异存在，同时减少残差中的晶系类别信息。动态增广本身不是论文要挑战的对象，也不作为创新点。

论文贡献定位为“严格的跨领域方法迁移与 XRD 特定验证”，不声称创造新的通用机器学习理论，也不包含模拟器标签监督。

## 文档入口

- `docs/V9_METHOD_TRANSFER_ENGINEERING.md`：算法迁移研究的范围、λ 来源、五组实验、公平性、Validation 比较和执行门禁。
- `docs/V9_SIMULATOR_SUPERVISED_RESIDUAL_ENGINEERING.md`：延期研究备忘；不属于当前论文和执行入口。
- `docs/DATA_AND_SIMULATION_CONTRACT.md`：两项研究共享的数据、物理模拟、证据来源和真实谱红线。
- `data/README.md`：当前数据目录与清单入口。

机器可读配置和 JSON/CSV 报告优先于叙事文档。若文档与配置冲突，执行入口必须拒绝运行并先修复冲突。

## 共享数据与流程

```text
Materials Project 晶体结构
  -> formal_14060：Train 9,842 / Validation 2,109 / Test 2,109；七晶系分层、家族代理分组
  -> 理想反射缓存（峰位、积分强度、hkl、多重性、倒易矢量）
  -> 同一母结构在线生成配对扰动视图
  -> PAMPT 骨干与对应研究损失
  -> Validation ID / development-OOD
  -> 方法与 checkpoint 冻结
  -> simulated test
  -> real test
```

渲染谱不作为独立结构样本持久化。背景与噪声是两个物理效应，观测链保持“Bragg 峰 + 背景，再采样噪声”的加性顺序。

## 当前可执行命令

算法迁移只读预检与 7 次调参计划生成：

```powershell
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py preflight
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-plan
```

检查最终测试锁：

```powershell
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py final-preflight
```

λ 最终值尚未由 Validation 选择；候选网格 JS `[0.3,3,30]` 与 Residual `[0.2,2,20]` 已通过 Train-only 梯度尺度 Gate 并冻结，但两个 tuning execution switches 仍为 `false`，因此 7-run 与 15 次正式计划都必须 fail-closed。新的统一 Validation 已冻结；旧的两个 Validation 子集已废止。本次更新不启动训练。simulated test 和 real test 也继续锁定，未经对应阶段的明确授权不得解除。

仓库测试：

```powershell
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

台式机硬件配置只读审计（不训练）：

```powershell
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_desktop_hardware_config.py
```

台式机迁移与首启入口见 `docs/V9_DESKTOP_MIGRATION_HANDOFF.md`。迁移后依次运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_v9_desktop_environment.ps1
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1 -PlanOnly
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1
```

这些命令只建立环境并运行工程验收，不启动训练。即使最终状态为 `ready_for_explicit_tuning_authorization`，完整 7-run 仍需用户另行明确授权。

## 笔记本阶段闭环工具（2026-07-22）

以下命令只做工程/统计准备，不授权正式训练或任何 Test 访问：

```powershell
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_resume_determinism.py --device cuda
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_method_parameter_semantics.py --device cpu
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_loss_and_gradient_scale.py --device cuda --steps 128 --burn-in-steps 64
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_test_preprocessing.py
```

正式 run 将输出带 SHA256 绑定的 `prediction_rows.jsonl`。结果冻结后，使用 `scripts/analyze_v9_results.py` 对多个 run 的逐谱文件做 family-level paired hierarchical bootstrap；不得仅对三个 seed 汇总值 bootstrap。机制诊断入口为 `scripts/analyze_v9_mechanisms.py`，真实谱合同继续保持 disabled。

当前方法参数相关的机器可读证据与治理合同：

- `reports/v9_method_semantics_audit.json`；
- `reports/v9_loss_gradient_scale_audit.json`；
- `reports/v9_learned_state_scale_audit.json`；
- `reports/v9_candidate_grid_gate.json`；
- `configs/v9_method_parameter_governance.json`；
- `docs/V9_METHOD_PARAMETER_GOVERNANCE.md`。

损失尺度审计只诊断数值作用强度，不选择 λ。PAMPT-B3 128-step Train-only 报告显示分类主干和 residual probe 尚未学会，因此其几万至几十万梯度倒数只保留为 initialization/chance-state 报警证据，不能当作理论权重或正式网格。

学习里程碑复测随后完成：`v9_learned_state_scale_audit.json` 使用完整 9,842 个 Train 结构训练五 epoch 的 classification-only Dynamic/Paired ERM PAMPT-B3，并以三组互斥、各 700 个七类平衡 Train 结构完成 probe calibration、probe audit 和 scale audit。主机意外重启后从固定 seed、epoch 0 完整重跑，没有声称 checkpoint 恢复。epoch 3/5 的主干与 residual-probe Gate 均通过；epoch-5 未加权 JS/分类与 Residual/分类 backbone 梯度比中位数分别为 0.05898 和 0.09738。

用户随后批准唯一一次 pre-Validation 网格修订：JS `[0.3, 3, 30]`，Residual `[0.2, 2, 20]`。`v9_candidate_grid_gate.json` 再次从 epoch 0 重建同一类 Train-only learned state，并对六个候选分别执行加权辅助目标和总目标的真实 autograd 测量，而非只做线性外推。实测中位辅助/分类 backbone 梯度比分别为 JS `0.02283/0.22842/2.28533`、Residual `0.02581/0.25854/2.58715`，两者均覆盖 weak、material non-dominant、dominant，且有限性、梯度存在性、方向与失控保护全部通过。候选范围现已冻结，但 `development_tuning.execution_enabled=false` 与 `development_tuning_execution_enabled=false` 仍保持关闭；7-run 仍为 `0/7`，只有用户另行明确授权后才能启动。

外部论文只提供方法与敏感性流程先例，不提供可直接搬用的数值：Hu et al. 的 SD3Net 正文/Table 5 使用 `lambda_3=1`，Fig. 12 又报告一个未明确映射到 `lambda_3`、约在 `1e-4` 最优的 regularization parameter。因此两者都不是 V9-T `lambda_res` 的数值权威；完整限制见参数治理文档与机器合同。
