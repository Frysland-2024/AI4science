# XRD Robustness V9-T

> 跨机器、跨 Codex 账号接管必须先完整阅读根目录 [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)，并运行 `scripts/verify_codex_account_handoff.py`。该交接不构成训练授权。

当前项目正式切换为 **V9-T：算法迁移主线**，不再使用 A/B/C2 或“先 Pilot、再选路线”的叙事。模拟器标签监督残差研究保留已有记录，并延期为 **V10：Simulator-Supervised Representation Learning**。

| 研究 | 优先级 | 核心问题 | 当前状态（2026-07-16） | 研究完成度 |
|---|---|---|---|---:|
| V9-T 算法迁移论文 | 当前唯一主线 | 显式建模同结构跨扰动视图关系，能否在单纯数据增广之上提高未知扰动与真实谱泛化 | family-aware 70/15/15 划分与统一 Validation 已冻结；方法语义 Gate 通过，现候选范围尺度 Gate 阻断；训练仍为 0/7 调参、0/15 正式实验 | 约 35% |
| V10 Simulator-Supervised Representation Learning | 延期 | 已知模拟器变量能否监督测量变化表征 | 只保留旧原型和研究备忘，不进入 V9-T | 约 15% |

百分比衡量的是完整研究交付物，不代表已有科学结论。算法迁移工程准备已完成，但没有训练结果，所以完整研究仍约为 35%。真实谱只用于最终 `real test`，不参与扰动参数定义、超参数选择、方法比较或 checkpoint 选择。

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

λ 调参结果尚未冻结，而且当前三点网格没有通过 Train-only 梯度尺度 Gate，因此 7-run 执行与 15 次正式计划都必须 fail-closed。新的统一 Validation 已冻结；旧的两个 Validation 子集已废止。本次更新不启动训练。simulated test 和 real test 也继续锁定，未经对应阶段的明确授权不得解除。

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
- `configs/v9_method_parameter_governance.json`；
- `docs/V9_METHOD_PARAMETER_GOVERNANCE.md`。

损失尺度审计只诊断数值作用强度，不选择 λ。新版 PAMPT-B3 128-step Train-only 报告给出 early/middle/late 的原始 loss、未加权 backbone 梯度、prediction JS、feature residual norm 和 residual-head entropy，并使用 128 个不重复配对 batch。结果显示分类主干到 late 段仍未优于随机，residual probe 也停留在随机水平；所以反推的几万至几十万只是不充分学习阶段的梯度补偿倍数，不能当作理论权重或正式网格。两组三点候选保持不变，必须先完成 Train-only 学习里程碑与 probe 能力复测。

该学习里程碑复测现已完成。`v9_learned_state_scale_audit.json` 使用完整 9,842 个 Train 结构训练一个五 epoch、classification-only Dynamic/Paired ERM PAMPT-B3，并在 epoch 1/3/5 使用三组互斥、各 700 个七类平衡 Train 结构分别完成 probe calibration、probe audit 和 scale audit。主机意外重启后，该审计以相同固定 seed 从 epoch 0 完整重跑，没有使用或声称断点恢复。epoch 3/5 的主干与 residual-probe Gate 均通过；epoch 5 的 Train CE/两视图 accuracy 为 1.62189/31.02%，互斥 probe audit 为 32.57% accuracy、28.92% Macro-F1、CE 1.85059。epoch-5 未加权 JS/分类与 Residual/分类 backbone 梯度比中位数分别为 0.05898 和 0.09738。该报告只证明已学习状态下存在可解释信号：不选择 λ、不改网格、不冻结 candidate range，也不授权 Validation tuning 或 7-run。当前两组三点仍是待审候选，下一步是人工决定是否使用唯一一次 pre-Validation 范围修订。

外部论文只提供方法与敏感性流程先例，不提供可直接搬用的数值：Hu et al. 的 SD3Net 正文/Table 5 使用 `lambda_3=1`，Fig. 12 又报告一个未明确映射到 `lambda_3`、约在 `1e-4` 最优的 regularization parameter。因此两者都不是 V9-T `lambda_res` 的数值权威；完整限制见参数治理文档与机器合同。
