# 2026-10-18 设计讨论：将 V9 五类 PXRD 扰动复用于 Forward Loss 参数反演

> **Current status (2026-10-23): ARCHIVED / INACTIVE.** This document is retained as a historical proposal or task record. It is superseded by the sole active PXRD seven-crystal-system classification direction and the three evaluation axes in [CURRENT_STATE](CURRENT_STATE.md) and [the scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md). Do not execute or reactivate this route based on its earlier wording.
>
> The old V9 Forward Loss proposal and its earlier execution language are not current authorization to train.

**原始状态（2026-10-18）：DISCUSSION / PROPOSED / NOT IMPLEMENTED / NO NEW EXPERIMENTS。当前状态（2026-10-23）：ARCHIVED / INACTIVE。** 本文保留当时的 A/B 候选设计与门槛；它不批准重开 V9、修改旧数据或执行训练，也不证明真实域泛化。

## 1. 为什么此时提出

- 用户在看到仅使用一个 HfCd 已知四方结构、512 个参数扰动样例的 PR #11 后，意识到新任务还没有充分利用 V9 的物理测量扰动能力；提出把先前的在线扰动模拟器接入模型。
- 当前 Draft PR #11 使用新 `xrd_forward_loss/src/pxrd_forward_loss/data.py` 中的**Poisson counts＋100–200 count 线性背景**输入，零点偏移固定 0、FWHM 固定 0.08°，且 `losses.py` 将 B 的重构谱直接与**带噪观测输入**作 MSE。只验证已知单结构连续参数模拟任务。
- V9 已具备有来源的五类扰动与在线种子/记录机制。参照 [五扰动物理证据索引](PXRD_PERTURBATION_EVIDENCE.md)、`xrd_robustness/src/xrd_robustness/simulator.py`、`physics.py`、`preferred_orientation.py` 和 frozen config `xrd_robustness/configs/simulation.method_transfer.frozen.json`。
- 复用的目的是**检验新任务在测量失配下的参数反演和 Forward Loss 是否有增量价值**，而不是为了复制 V9 一万多个 CIF 的规模，也不是为了“刷出 B 必胜的结果”。

## 2. 物理标签 vs nuisance 必须严格分开

建议一次模拟样本同时存三类信息：

1. `theta_true`：真实结构/连续晶格参数，如已确认单相的 `a,c`、或既有正交化 `du,dv`。**只有更改结构/晶格参数才改变这份标签**。
2. `clean_profile = F(H, theta_true, eta_ref)`：经过物理验证的理想参考谱，`eta_ref` 为固定参考测量状态；作为不同扰动 realization 的共同“干净谱”。
3. `observed_profile = T(clean_profile, nuisance, seed)`：带随机测量状态的网络输入，另存 `nuisance`、随机种子、启用扰动、强度及模拟器版本。

目标关系：`same structure + same theta_true -> multiple independent observed profiles`，但**不再学习晶系不变标签，而是稳定预测同一组连续参数**。两个相同母结构但不同 `theta_true` 的模拟谱不应被误认为监督一致的对象。

## 3. V9 五类操作及新任务的风险等级

| V9 扰动 | 现有 V9 Train 范围（历史冻结配置；新任务不得机械照抄） | 反演任务的注意点 |
|---|---|---|
| Poisson–Gaussian counts/electronic noise | Poisson count scale 2500–40000, read noise 0–2 counts | 最适合第一批接入；保留 `theta_true` 不变，可直接生成有噪 `observed_profile`。 |
| 平滑背景 | 三阶多项式；peak ratio 0–0.02、启用概率 0.5 | 可早期接入；若 B 将 Forward clean 输出直接对 noisy+background 计算 MSE，背景会带来与目标不一致的梯度。 |
| FWHM 展宽 | U(0.08,0.20)°，p=1 | 应先审计 clean renderer 的 FWHM/归一化约定是否一致；展宽是独立 nuisance，不等于晶格变化。 |
| 全谱零点偏移 | U(-0.2,+0.2)°，p=0.5 | **高风险**：改变峰位置却不改变真实晶格参数，若 B 的 F 固定 zero-shift=0 且直接拟合 observed，会诱导错误的 `a,c` 以补偿偏移。必须在参数中显式估计/提供 nuisance，或者让重构目标为 clean reference，或采用经过验证的 nuisance-robust objective。 |
| March–Dollase 择优取向 | r U(0.8,1.0)，p=0.7；低指数反射方向 | **后加**：影响结构相关相对峰强，需有正确 reflection hkl/multiplicity/方向元数据，不能简单独立乱乘各峰。旧 NumPy 实现并不自动令新的 Forward Loss 可微。 |

上述 `p` 是模拟采样概率，**不是实验仪器发生概率**；旧 frozen 范围属于旧晶系分类任务，并非已证明适合学长未来铁电陶瓷真实谱。

## 4. 重构 Loss 应该对什么比较？这是新增设计 Gate

原 PR #11：`L_B = L_param + lambda * D(F(theta_pred, eta_ref), observed_profile)`。当 `observed_profile` 含背景/零点偏移/纹理，且 `F` 不含对应 nuisance 时，物理正确参数可能因不能解释 nuisance 而受到错误惩罚。

**建议先测试更一致、易实现的选项：**
`L_B = L_param + lambda * D(F(theta_pred, eta_ref), clean_profile)`。
训练时 clean target 由模拟器提供，不依赖真实谱标签，能让梯度聚焦结构参数；真实谱推理时没有 clean 谱也可以预测参数，但**不能说已经在真实谱上计算同样的训练损失**。此方案可视为 simulator-provided privileged reconstruction target / physics-weighted parameter supervision；准确描述而非伪装通用无监督真实谱重构。

**另一方案（以后再讨论）**：`F(theta_pred, eta_sampled/estimated)` 对同一测量状态重构 `observed_profile`；需显式 nuisance 建模、可微的已知 measurement operator 或稳健剖面优化，避免自由度补偿与不可辨识问题。

**关键判据：** 不论使用哪一种，都应先检查对真实 `theta_true` 的重构梯度是否被扰动系统性推离真值，尤其 zero shift。更换 Loss target 属于新科学实验协议，**不得在 PR #11 上悄悄改好数字**。

## 5. 最小实验（不做“CV 式”无界消融）

用户偏好借鉴已有 XRD workflow，不需要数十种模型。推荐 **一个主要 A/B 对照 + 小型两域评价**：

- **训练**：A 和 B 同一个 ResNet、相同 `theta_true` 和 `observed_profile`、相同训练预算/seed；先接 background+Poisson–Gaussian noise，再在数值通过时加 broadening 与 zero shift，最后按真实需求决定是否打开 March–Dollase。
- **验证**：固定少量代表结构与参数范围；验证集选择必要超参数，预留独立 test，不用 test/真实谱调参。模拟测试可按 **in-range** 和 **stronger measured-domain mismatch/OOD** 报告；如需清洁谱参照，可作为已知“easy ceiling”结果，不用搞全面组合矩阵。
- **输出**：`a,c`（Å）和归一化坐标 MAE，clean+noisy 谱图差异、噪声/偏移分层误差、失败例子、时间、物理初值/局部精修价值（若已实现）。新 `lambda`/target 仅在 validation 上选；不同材料/独立结构须先做 split/prototype 审计。
- **最低成本 Gate**：在目前单 HfCd 工程 Pilot 的**独立新 run_id**上做极小 smoke，用一套旧 nuisance 的输入 + clean 和 observed 同时输出，检查增强前后 `theta_true` 恒定，Forward/Jacobian/训练梯度正常。此 smoke 只能检验工程迁移。然后等学长正式家族明确，再在至少一组可信的材料候选结构上做主实验。

## 6. 工程连接点与防误用

- 新代码应在 `xrd_forward_loss/` 或拟议 AutoLab 的独立分支中写 adapter，**读取/复用旧扰动算子和证据**，不要修改 `xrd_robustness/` 冻结训练协议。
- 旧 `simulator.py` 包括 **pymatgen 从结构生成理想峰表** + NumPy measurement processing；新 `xrd_inversion` 的 **可微** Forward 是另外一种 renderer。不能未经核验把旧模拟器直接插在 `predicted theta -> loss` 梯度路径里（NumPy 会断梯度），也不能拿某个固定 CIF 的峰表在随机晶格参数改变后继续使用而不更新实际 Bragg 峰位。需要明确区分“结构/峰表正向物理生成”和“后处理的测量扰动”，检查两者谱轴、强度、归一化约定。
- 若独立生成器 vs 可微 Forward 存在系统差异，应当记录并评价 renderer mismatch，不能自动把它当作模型失败或物理正则化收益。
- 保留 PR #11 的 512 张 HfCd、三 seed baseline 和最初退化运行结果；新扰动组合开启一个**新的、预先记录目的**的可复现实验，不覆盖原 Pilot。
- 真正应用到铁电陶瓷前，仍需学长给 nominal composition / candidate phases / 仪器扫描设置，明确不同相的 forward 数值正确性、训练与真实数据的有效边界。

## 7. 时间与科研叙事中的位置

思路演进：V9 利用五种测量 realization 的同母关系做晶系分类 → 新 PQ-Net/DRNets-inspired 项目缩到已知相条件参数反演，首个 HfCd Pilot 只加噪声和线性背景，谱图误差小降但平均参数无增益 → 用户提出**复用 V9 成熟五扰动模拟器，让新任务在更真实的测量变化中检验 Forward Loss**。这是一个值得优先验证的可行改进，但并不等于旧 JS 方法直接适用，亦不意味着增强一定提高真实谱表现。

**状态：FUTURE DESIGN CANDIDATE，awaiting scientific-protocol approval。**
