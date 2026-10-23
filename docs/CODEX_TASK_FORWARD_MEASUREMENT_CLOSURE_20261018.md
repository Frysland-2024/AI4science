# 科研工单 · 测量一致的 PXRD Forward 闭环纠偏（2026-10-18）

> **Current status (2026-10-23): ARCHIVED / INACTIVE.** This document is retained as a historical proposal or task record. It is superseded by the sole active PXRD seven-crystal-system classification direction and the three evaluation axes in [CURRENT_STATE](CURRENT_STATE.md) and [the scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md). Do not execute or reactivate this route based on its earlier wording.
>
> The historical 2026-10-18 bounded-training authorization is superseded and inactive. Do not run its gates or training as part of the current task.

**Original ticket status (2026-10-18): CODEX APPROVED — PHYSICS-GATE-CONDITIONAL BOUNDED GPU TRAINING / NOT YET EXECUTED。Current status (2026-10-23): ARCHIVED / INACTIVE; the earlier authorization is superseded.** 用户在讨论 PR #11、#16、#17 后明确质疑重构目标，2026-10-18 选择优先核查 **Forward 重建的目标与测量模型是否一致**，取代原 Issue #18 的“直接迁移 clean-reference loss 再训练”优先级。此任务不声称已证明方法有效或真实谱精修适用。

## 2026-10-18 用户补充授权：物理 Gate 通过后直接训练（优先级最高）

用户在派发后明确补充：“**让他直接在通过检测后进行训练**”。因此本段替换下方 P2 与旧权限合同中“本轮不授权训练 / 只做 numerical smoke”的限制；其他科学和权限边界保持不变。

**触发条件（全部需要通过且留痕）：**
- P0/P1 的 BaTiO3 CIF / P4mm 结构物理验证、Torch 与独立 Pymatgen/V9 clean 谱全谱（峰位、峰形、相对强度）对照、measurement-aware profile vs observed 期望的一致性、有限差分/自动微分梯度检查均通过。
- 明确 q=(du,dv)/a,c、测量参数 eta=(2theta zero-shift, FWHM, smooth background 等) 的来源与可辨识边界；oracle eta 真值**只用于诊断**，不能在报告最终新 B 的推理性能时偷用。
- 必须有 deployable 的 measurement-aware B loss 策略：例如与 A 相同的 q 输出、训练 B 时为当前 profile **估计或优化**受限 nuisance；或让 A/B 使用相同模型预测 q 与 eta 并清楚披露额外 nuisance 监督。若只能让 B 在测试时使用模拟 eta_true，请标注为 **ORACLE-ONLY**，不可将该结果作为正式有应用意义的 A/B 成果。
- 冻结 split、随机种子、物理参数范围和训练预算；新的输出目录，不覆盖 PR #11/#16/#17 的任何数据和旧 Pilot。

**Gate 通过即直接执行，不再等用户二次确认：**
1. 按脚本实现轻量级 smoke：128 条参数样本、1 seed、最多 4 epochs；确认 finite loss、loss 路径持续有梯度、训练时间和显存合理。可使用 RTX 4060。
2. smoke 通过则自动执行 **一个**受控正式 Pilot：**最多 512** 条 BaTiO3 同模板模拟参数样本，**3 个配对训练 seed、最多每 seed 24 epochs**，条件仅 simple vs V9 四扰动、方法 A supervised 与 B measurement-aware reconstruction。A/B 保持相同 backbone、训练输入和样本/更新预算；如添加 eta 预测头，需公平说明对应参数量和标签差异，且不能凭额外 oracle 信息占优。
3. B loss weight 可以事先固定，或在独立 validation 上从 **最多两个预注册候选**中选择；必须写清选择逻辑。绝不利用旧 Pilot 的 test 指标、新 Pilot 的 test 或真实谱标签挑选超参；本次已有公开测试历史，不能宣称全新未见 benchmark 的确认性评价。
4. 统一记录全部 seed 的 q-MAE、a/c Å MAE、观测谱期望重构误差及 clean 残差（仅辅助诊断）、运行时间、显存、可辨识失败和所有负结果。对预处理一致性和 loss 数值单位进行检查。若 B 未优于 A，也如实完成并提交。
5. **STOP**：如果物理 Gate、可辨识/部署假设、数据标签隔离或梯度检查失败，**不得强行启动大训练**；提交 BLOCKED 报告与下一步方案。若 512×3×2×2 在当前 GPU 预计过长，应做有据可查的缩减配置（保留成对 A/B）并标记 exploratory partial，绝不无限扩张、遍历超参或运行多材料大型训练。

**权限边界：** 仅授权本次隔离开发分支的 BaTiO3 单相测量闭环与上述有限 GPU 训练、测试、提交 Draft PR；**不授权更改旧实验、主分支、定时桥接器权限、自动 merge、真实材料结论或无限自动科研**。对比要明确这是单 CIF 条件插值与合成测量扰动，非真实实验谱验证。

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
4. **本轮优先交付可信的 Forward 闭环，而不是刷高旧 B 的 MAE。** 用户已明确批准：P0–P2 全部关键 Gate 通过后，Codex **无需再询问用户，立即按 P3 预算启动 GPU 训练**；阻断性 Gate 失败则停止并报告，不得自行放宽阈值。

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

### P2 · 训练前强制验收 Gate

- 写 pytest 测试：theta_true 与 nuisance 独立；干净/展宽/全谱零点/平滑背景的 Forward 闭环；与独立 V9 / Pymatgen 参照的整谱强度和形状一致性；autograd vs finite difference；Poisson–Gaussian **观测噪声与模型预测的测量期望**区分；未知 nuisance 条件下严防标签泄漏。
- 执行 few q × few eta 的数值恢复 smoke：包含已知 eta_true 的 oracle 物理上限和未知 eta 的 **non-oracle** 检查；明确梯度方向、真实参数附近最小值、q–eta 局部可辨识性、拟合自由度与退化解。带随机噪声的单谱梯度不要求严格为零，应按统计期望或重复测量解释。
- 将各项 Gate 的命令、阈值、实测数值、pass/fail 写到 `gate_report.json`；如果 P0/P1/本阶段任一关键 Gate 不通过，或未知 nuisance 无法合理估计/消除，则**不运行正式 A/B**，输出 `BLOCKED` 技术报告和下一步建议，绝不在同一次试验中悄悄放宽 Gate。
- Gate **全部通过**后，Codex **不需要再次请求用户批准**，直接执行下方 P3。为降低阻塞，先 1-seed NN smoke，之后在硬预算内自动运行主 Pilot。

### P3 · Gate PASS 后直接运行训练（本工单已预先授权）

**研究设计（只限已知公开 BaTiO3 四方相）：**

1. 使用 PR #16 的公开 BaTiO3 CIF（COD 9014273，P4mm），固定参考原子分数坐标及占位，学习 2 个晶格参数 `q=[du,dv]`，转换为 `a,c`。合成输入可以包含 zero-shift、FWHM、smooth background、Poisson–Gaussian noise（本轮 March–Dollase 不启用）。先核验单 CIF 来源、晶格变形范围以及对应 Forward 的完整谱形、梯度和边界。
2. **A：** 原始 ResNet-18-GN，参数监督 `L_param(q_pred,q_true)`。**B：** 相同晶格参数 backbone、训练数据、optimizer、拆分、seed 和参数训练预算，额外使用 `L_param + lambda*D(mu(q_pred,eta_est),x_observed)`。其中 `mu` 是可微、确定性的**测量期望谱**，不是理想无扰动谱，亦不拟合某一次随机噪声。若选择计数似然，需确保原始计数/归一化约定与噪声统计一致；如果使用加权 MSE，注明近似理由。
3. **主结果必须 non-oracle**：真实测试和训练主路径不能读取逐样本 `eta_true`。可以通过受界 profile fitting / 小型 nuisance 估计器合理估计 `eta_est`，但必须记录估计自由度、收敛与计算代价；防止 `a,c` 吸收零点偏移。若只能跑通 `eta_true` 的 oracle，**标记 `BLOCKED_NON_ORACLE`，不要用 oracle 的 B 当主结论**。oracle 可以作为独立物理诊断上限；旧 PR #17 clean-reference B 仅作历史比较，不替代新的 measurement-aware B。
4. 若 B 的 nuisance 估计引入额外训练参数或优化开销，明确记录相较 A 的复杂度及公平性局限。可以沿用 q-only 主网络与受界 nuisance profile optimization；不要为此扩大成通用 Rietveld、多相预测或多材料家族系统。

**硬预算（不再要求用户中途确认）：**

- 先冻结新 config / physics Gate manifest / 指标 / split / RNG seeds；最多 **512 个 q 样本**（不是 512 个母结构），按照约 **70/15/15** 分成 train/validation/test。先划分 q 再生成随机测量视图，严格避免同一 q 的不同扰动进入其他 split；留好 `theta_true`、`eta_true`、`expected_profile`、`observed_profile` 的单独记录。此前 BaTiO3 test 已经被研究者看过；本次为**探索性后续实验**，不得包装为未受历史信息影响的 confirmatory blind test。
- 运行 A+B **128 q 样本 × 1 seed × 最多 4 epoch** 的 NN smoke。若出现数值发散、物理不一致、泄漏或内存问题，停止并输出 `BLOCKED_SMOKE`。
- Smoke 通过后，允许正式执行 **最多 512 q 样本 × 24 epoch × 3 个配对 seeds** 的 A/B 小型 Pilot。B 的 lambda 在验证集从 **{0.1, 1.0}** 中按预先写明的规则选择；A 是 lambda=0。不能查看 test 后调整 lambda、seed、epoch 或材料，不无限补跑直至 B 获胜。保留训练成本，不混淆训练预算和墙钟开销。
- 累计实际训练和超参选择的墙钟预算 **最多 2 小时**；超时、GPU 不可用或足够可用显存不足时停止并标记 `BLOCKED_BUDGET` / `BLOCKED_NO_GPU`，提供复制可执行的本地 RTX 4060 命令及已完成证据。不得伪称训练完成。
- 不自动 merge，不修改 `main` 科研结果、不覆盖 PR #11/#16/#17 的历史原件；工作限于隔离分支 / 临时工作树及独立结果目录。

**报告与交付：** 必须保存物理与梯度 Gate（包括 nuisance 未知条件的可辨识性）、执行命令和 exit codes、配置+数据 SHA / seed / commit / 环境、train-val-test 计数、validation lambda 记录、A/B 的 `du,dv` normalized MAE、`a,c` Å MAE、observed 的合理谱残差与 clean 谱误差、3-seed 原值与均值±SD、nuisance 估计失配样例、计算耗时/显存、机器可读 JSON 和简短 `TECHNICAL_REPORT.md`。无论 B 是否优于 A，完整保存负结果。

**科研边界：** 单个已知 BaTiO3 CIF 的 conditional parameter interpolation ≠ 未见结构泛化，也不等于真实 XRD 精修。训练数据中的 synthetic nuisance truth 只能用于数据生成、元数据和 oracle diagnostics；不能在 non-oracle 主方法中借用。若 Gate 不通过，则**停止训练也是遵守任务成功**，不得为了自动跑完而强行绕过。

### P4 · 交付方式与历史记录

- 代码集中于 `xrd_forward_loss/measurement_closure/` 或相邻独立模块，包含 scripts / configs / tests / `docs/MEASUREMENT_AWARE_FORWARD_CLOSURE_REPORT_20261018.md`，保存真实输出 JSON 和必要质控图；输出位置新建、不得覆盖旧报告。
- 从 PR #17 的 `codex/forward-loss-v9-reuse` 创建**新隔离分支**；按需受控引入 PR #16 的公开 CIF，不盲目 merge。完成后提交并 push，建 **Draft PR**，逐项写明 Gate pass/fail、smoke/正式 Pilot 到哪一步、负结果与局限；不自动合并。
- 在 `docs/PROJECT_HISTORY.md` 追加本次“用户发现重构对象不符 → 物理纠偏 → 用户授权 Gate 通过即训练 → 实际证据”的时间线；不覆盖原历史。用户明确批准本次有界 GPU 实验，但**没有批准无限优化、学长私有数据读取或开放本地只读 research_bridge 的写权限**。

## 研究者关注的三个判断

1. 现有 Forward 是否把理想谱错误地直接拟合了扰动观测谱？
2. 以测量一致 forward 替代后，`q_true` 的梯度是否避免了零点偏移造成的系统性偏差（在约定测量模型、期望/统计意义下）？
3. 当仪器 nuisance **未知**时，`q` 与 `eta` 在局部是否仍可辨识？如果不可辨识，必须诚实说明这是物理限制而非通过换 Loss 就能解决。

最后在 `docs/PROJECT_HISTORY.md` 以“用户提出质疑→实证检查→是否改协议”的形式**追加**一段证据/结论，保留时间线，不篡改旧提案。别给项目强加无关 CV 的标准或改写 V9 主线。

**权限合同（最新用户授权）：** Codex 可在新隔离分支执行 P0–P2 物理验证，且全部 Gate PASS 后**无需额外询问直接自动执行 P3 的有界 GPU A/B 训练**，随后提交 Draft PR。不得超出 P3 预算、修改冻结历史、自动合并、接触私密实验谱或扩大本地只读 `research_bridge` 权限。既有 Issue #18 的 clean-reference 训练协议暂停，以本任务的新 measurement-aware 协议为准。
