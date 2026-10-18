# 科研工单 · 测量一致的 PXRD Forward 闭环纠偏（2026-10-18）

**状态：NEW TASK / AWAITING IMPLEMENTATION AND PHYSICS GATES。** 用户在讨论 PR #11、#16、#17 后明确质疑重构目标，2026-10-18 选择优先核查 **Forward 重建的目标与测量模型是否一致**，取代原 Issue #18 的“直接迁移 clean-reference loss 再训练”优先级。此任务不声称已证明方法有效或真实谱精修适用。

## 一个核心研究问题

既有模型：输入带测量扰动的 PXRD，ResNet 预测固定已知四方结构模板的两个晶格参数坐标 `q=[du,dv]`（对应 a,c）。原 PR #11/#16 B Loss 为
`L_param + lambda * D(F_clean(q_pred, eta_ref), x_observed)`；
该比较把 **未纳入零点、宽度、背景的 clean Forward** 与 **已加入零点、宽度、背景、Poisson–Gaussian 噪声的 observed** 直接配对，nuisance 未建模可能使晶格预测偏离真实值以补偿仪器偏移。

PR #17 改成 `L_param + lambda * D(F_clean(q_pred,eta_ref),x_clean_true)`。
这是 **simulator-provided privileged clean-target supervision**（数值自洽），但其目标不是直接解释观测谱；对真实实验谱无法假定已知 `x_clean_true`。

本工单新增的研究对象是 **measurement-aware expected forward**：
`mu(q,eta) = M(F_crystal(q), eta)`，
`x_obs ~ P(x | mu(q_true,eta_true))`。
eta 最小包含全谱 2theta zero shift、物理一致的 FWHM broadening、smooth nonnegative background（必要时单位强度/scale）。Poisson/readout 是观测噪声统计，**不能要求模型精确复现某一次随机噪声 realization**。观测谱重构的目标是预测测量期望谱 `mu` 或恰当的 likelihood/deviance / 加权谱误差（说明预处理和规范），不是伪造与每个噪声点完全一致。

## 仓库起点及严格边界

1. 阅读 `AGENTS.md`、`docs/CURRENT_STATE.md`、`docs/PROJECT_HISTORY.md`，保留原 V9 分类所有 frozen 数据结果、旧 NO-GO 归档和现存负结果。
2. 基础 Pilot PR #11：`feat/physics-guided-pxrd-inversion-pilot`；既有 V9 扰动适配器 PR #17：`codex/forward-loss-v9-reuse`（推荐为**独立新开发分支**的父分支）；公开 BaTiO3 CIF 与说明 PR #16：`feat/public-batio3-forward-ab`，COD 9014273，P4mm，历史参照晶格 a≈3.986 Å, c≈4.026 Å。只挑必要来源文件引入，不自动合并以上 PR。
3. 现有 `xrd_inversion/src/xrd_inversion/gpu_forward.py` 的 clean Torch Forward 可微，允许作为 `F_crystal` 基础；`xrd_robustness` 的 V9 NumPy 后处理仅供独立数据生成/物理参照，**不要把 NumPy 插在预测参数至 Loss 的梯度路径**。注意结构模板的固定分数原子坐标/占位，不能叫全结构 Rietveld 精修。
4. **本轮优先交付可验证的 Forward 闭环，不是把旧 B 的 MAE 刷高。** 未通过物理 Gate 不得启动正式 A/B；不因为云端/本地有 GPU 就进行无边界训练。

## Codex 具体工作（按序）

### P0 · 审核已有实现、复现错误重构目标

- 写一份最小数学/代码映射：`q_true`、`eta_true`、`F_clean`、`mu`、`x_clean`、`x_observed` 在旧 PR #11、#16、#17 中分别是什么，以及 `paired_losses` / `clean_reference_paired_losses` 具体 target、固定 `compose_full_q` 仍将零点/FWHM 固定为多少。不得把“重建错目标”和“物理晶体模型生成错谱”混为一谈。
- 使用公开 BaTiO3（PR #16 CIF），或者若实在受限用 HfCd 并明确材料局限。验证 structure/空间群/CIF 出处、波长/2theta 轴、基本反射和干净模型；至少对数个 q 探针做 Pymatgen / V9 clean renderer 与 Torch clean Forward 的 **定量强度和整谱 parity**，而不只给出峰位命中率。出现明显系统失配先报告阻塞。

### P1 · 可微的测量一致期望谱

- 在独立模块实现 `expected_profile(q,eta)`：结构 q 影响 Bragg 峰位/强度；eta 显式控制全谱 zero shift、峰展宽、非负平滑背景、需要时相对 scale。优先复用现有可微 Torch Forward 的 `delta` 和 `fwhm` 参数化，重用/小幅扩展其接口；背景 Torch 可微实现，不需要复杂大框架。保持每项物理单位与归一化位置明确。
- 同时提供 `observed_profile`（真实/synthetic 输入）与 `expected_profile`（确定性重建）区分；训练 loss 对已知噪声分布选合理的 profile likelihood 或 weighted spectral mismatch，若工程预算只能 MSE，解释其限制；禁止在 loss 中反向拟合随机噪声种子本身。
- **两个清晰分层的闭环**：
  (i) oracle diagnostic：使用已知 eta_true 作为数值/物理上限，验证真 q 的谱残差、对 q 的 loss 梯度/有限差分接近零（预期意义上的，带有限噪声须统计重复/平均，不能武断要求单谱梯度零）；注意 q 与 eta 的可辨识性；
  (ii) deployable diagnostic：eta 未知时由限定参数约束下的 optimize/profile 或简单预测途径估计，**不得在推理时偷用 eta_true**。对 nuisance 的自由度和退化解作审计。可以只做小数值实验，不要求上线完整 NN。
- 至少一个故意错配对照 `F_clean(q,eta_ref)` vs `x_observed` 以显示 zero shift 可能如何诱导 q 梯度偏置。对比 `F_expected(q,eta_true)`，记录 **梯度方向、有限差分、真实 q 附近最小值位置**，用图或表展示，不能凭主观描述“偏”。

### P2 · 小规模验收，无边界扩张停止

- 首先写 pytest 测试：theta_true 与 nuisance 独立；在干净/带宽度/带零点/带背景几种少量 q 情况的闭环；模型重建相对独立 V9/Pymatgen 参照的谱误差和单位一致性；GPU autograd vs finite difference；噪声期望 vs 单次随机样本区分；限制未知 nuisance 时避免用 truth 的代码路径。记录命令与测试数。
- 若 P0/P1 通过，再允许 **一个有界的小型 numerical recovery / optimization smoke**（例如 few q × few eta，数分钟量级）。本任务**不授权大规模 NN A/B、正式 test 调参或任何真实谱结论**。失败则出 `BLOCKED` 技术报告，停止。
- 成果：新的 `xrd_forward_loss/measurement_closure/` 或相邻独立模块、单独 config、tests、`docs/MEASUREMENT_AWARE_FORWARD_CLOSURE_REPORT_20261018.md`、可运行的最短命令、结果 JSON/表和必要的质控图。冻结旧 Pilot 的 report/results 不可改动。
- 在**新独立分支**提交并 push，创建 **Draft PR**（base 优先 PR #17 对应的 `codex/forward-loss-v9-reuse` 分支；如技术差异需要调整则记录原因），PR 描述写清楚已执行/未执行的实验、Gate 与科学边界；不自动 merge。

## 研究者关注的三个判断

1. 现有 Forward 是否把理想谱错误地直接拟合了扰动观测谱？
2. 以测量一致 forward 替代后，`q_true` 的梯度是否避免了零点偏移造成的系统性偏差（在约定测量模型、期望/统计意义下）？
3. 当仪器 nuisance **未知**时，`q` 与 `eta` 在局部是否仍可辨识？如果不可辨识，必须诚实说明这是物理限制而非通过换 Loss 就能解决。

最后在 `docs/PROJECT_HISTORY.md` 以“用户提出质疑→实证检查→是否改协议”的形式**追加**一段证据/结论，保留时间线，不篡改旧提案。别给项目强加无关 CV 的标准或改写 V9 主线。

**权限合同：** 用户本次明确授权 Codex 在新的隔离分支完成代码、有限数学和物理测试并准备 Draft PR；不得动 `main` 科研结果，不得自行 merge，不得上传私密材料，不得发起大规模 GPU 训练，不得提高后台只读 `research_bridge` 的权限。既有 Issue #18 的 clean-target A/B 方案暂停，待此 Gate 审查后重新讨论。
