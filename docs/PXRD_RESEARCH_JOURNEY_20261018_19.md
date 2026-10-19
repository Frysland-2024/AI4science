# 2026-10-18—19 PXRD 定量反演研究决策全记录（含碰壁与负结果）

**性质：研究过程与证据索引（retrospective / decision log）；不是新实验报告，也不是正式获批毕设。**
**记录时间：2026-10-19。** 证据覆盖两日内已保存到 GitHub 的重要技术分支、项目规划与原始报告；零散聊天中未落地、无法核查的点子不包装为已完成的实验。按“当时要解决什么 → 设计 → 证据 → 为什么转向”记录。并行分支不一定严格先后发生，表中顺序是研究问题的逻辑演变，不是精确小时级时序。

## 一、起点：分类研究已成型，想向真实参数反演发展

原 PXRD 七晶系分类研究，利用同一母体结构在不同测量条件下的测量等价关系做 JS consistency；模拟测试、RRUFF few-shot、CNRS zero-shot 已完成，属于**独立、冻结、正在写作的主线**。下一阶段希望把“输出晶系标签”推进到“给定 XRD，得到可解释的晶格与测量参数”，但不希望投入大量湿实验，也不想做任意结构确定。

10 月 18 日之前已提出铁电陶瓷一个已知家族、模拟谱训练、Forward 解释、有限真实谱外部测试和预精修辅助的 12 周候选；包含 Top-K 假设、双相作为失配压力测试等拓展。当时存在两种竞争目标：A）研究训练时加入 Reconstruction Loss 是否提升参数回归；B）做一个人参与的可用参数反演/精修系统。它们不应混为一个科研 claim。

来源：[2026-10-08 原候选](FUTURE_UNDERGRAD_THESIS_PLAN.md)；[2026-10-18 的 12 周扩展候选](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)。

## 二、10 月 18 日：把“根据物理模拟重建谱，再比较差异”落实为可微训练

### 1. HfCd 初始 Forward Loss Pilot（PR #11）
- **想法：** 神经网络从谱直接预测两个连续晶格坐标 q；固定可微物理生成器 F(q) 重建衍射谱，使用 L_param + λ·D(F(q_pred), target) 更新网络。不是事后“画张谱对比”，重建 loss 真的参与反向传播。
- **已实现：** 一条已知四方母结构 HfCd、3 个配对 seeds，数值梯度检查通过。
- **关键结果：** 普通回归 A 的归一化 q-MAE 0.01495±0.00327；Forward Loss B 为 0.01509±0.00120；B 的 clean transformed-profile RMSE 0.008497，A 为 0.009008。**重建残差略好，不代表物理参数更准。**
- **实打实碰壁：** 首次回归头输出饱和到 +0.8；修正初始化后又更换了部分种子，不能说改善完全由初始化导致。
- **认识变化：** 原想法是能实现的，但“Loss 能回传”与“物理参数收益”是两回事。
- 证据：[PR #11](https://github.com/Frysland-2024/AI4science/pull/11)。

### 2. 迁移公开 BaTiO3（PR #16）
- **为什么：** HfCd 数据/结构来源不适合作为可公开、可解释的毕设演示，改用公开四方 BaTiO3 CIF（COD 9014273）。
- **初步结果：** 512 draws、一个 seed 中 A q-MAE 0.019204，B 0.026612；B 较差，且 λ=1.0 是继承值、未在新体系独立验证选择。只算早期负结果，不是 Forward Loss 普遍无效的证据。
- 证据：[PR #16](https://github.com/Frysland-2024/AI4science/pull/16)。

### 3. 复用 V9 测量扰动，但转成 clean-reference 目标（PR #17）
- **设计动机：** 原模拟输入考虑噪声、零点偏移、峰展宽、背景，重建器却可能只生成干净谱，直接把两者 MSE 可能迫使晶格参数代偿仪器误差。
- **修正尝试：** B 改为 L_param + λ·D(F(q_pred), 模拟器已知的 clean_profile)；HfCd 的 V9 q-MAE A 0.07293、B 0.06842，但 a 的 MAE 与 clean-spectrum RMSE 并非都改善。
- **后来发现的新问题：** 用模拟器私有的“干净谱真值”作为训练目标，是额外 privileged supervision，真实未知谱通常没有这个标签，也偏离了用户“用重建谱去解释输入观测谱”的初心。
- 证据：[PR #17](https://github.com/Frysland-2024/AI4science/pull/17)。

### 4. Measurement-aware observed-profile Forward 闭环（PR #21/#26）
- **纠偏：** 明确区分晶格 q=(du,dv) 与测量参数 eta=(2θ zero shift、FWHM、背景幅度)。物理生成观测期望谱 μ(q,eta)=M(F_crystal(q),eta)，拿 μ 与带噪的**实际输入谱**比较；不拟合某次噪声采样本身，也不在推理时偷看 eta_true。
- **数值 Gate：** 全谱 Torch/V9 parity、autograd vs finite difference、局部 Jacobian、无真值的局部物理恢复、噪声期望检查均通过。在更自由的背景形状版本中出现 condition number 约 3.06×10^16 的不可辨识失败，遂按原固定背景形状配置限制自由度；不是降低阈值。
- **PR #26 正式试跑：** single-CIF BaTiO3，三 seeds、358/77/77；simple A/B q-MAE 0.013533/0.013676，V9 A/B 0.032235/0.030554。闭环跑通，A/B 优势却不一致。
- **明确负结果/工程坑：** checkpoint RNG 恢复初次 CUDA 异常，已留存失败运行；原 A/B 的 observed-profile RMSE 评估给 A 加了测试时 nuisance 拟合，给 B 直接使用网络预测 eta，计算预算不等，旧残差表不能作为公平优劣论据。
- 证据：[PR #21](https://github.com/Frysland-2024/AI4science/pull/21)、[PR #26](https://github.com/Frysland-2024/AI4science/pull/26)、[PR #26 技术报告](https://github.com/Frysland-2024/AI4science/blob/codex/issue19-measurement-closure/xrd_forward_loss/measurement_closure/TECHNICAL_REPORT.md)。

## 三、10 月 18–19 日：停止“换算法救模型”，开始审计为什么没有收益

### 5. 公平 nuisance 拟合诊断（PR #33）
- 固定旧 A/B 的 q 预测，对每个测试样本两组都给予**相同**有界 eta-only L-BFGS-B 优化。Simple A/B profile RMSE 0.009456/0.009415；V9 A/B 0.016034/0.015621；三个 seed 方向混合，不支持稳定提升。
- B 的 V9 原生 zero-shift 预测 RMSE 约 0.032117°；同一 q 上把 B 预测 eta 换成独立物理优化 eta，残差明显降低。**测量参数头有可观差距，但不能由此断言它就是晶格误差的因果源头。**
- 证据：[PR #33](https://github.com/Frysland-2024/AI4science/pull/33)、[完整报告](https://github.com/Frysland-2024/AI4science/blob/codex/issue19-nuisance-diagnostic-20261018/xrd_forward_loss/measurement_closure/nuisance_diagnostic/TECHNICAL_REPORT.md)。

### 6. Issue #31：梯度冲突与 q-detach 训练
- 检查验证集发现：V9 中晶格监督与重建损失存在某些负向梯度，du/zero-shift 误差强相关（约 0.853–0.949）。**注意后续重新核验修正了计数分母：真实是 6/15 个 V9 验证批次，而不是旧文档中的 6/30；简单条件 0/15。**
- 预注册 C：重建分支对 q 做 detach，阻止其 gradient 干扰晶格监督，而 eta 仍通过重建学习；采用全新合成数据重新做配对 A/B/C。
- 新 simple direct q-MAE A/B/C 为 0.018986/0.019093/0.014692；V9 为 0.043128/0.037117/0.037760。Simple C 有提升，V9 C 不稳定优于 B；共同物理精修后结果几乎一致。
- **研究教训：** 观察到梯度冲突不等于它主导全部误差。不能把已做过的 detach q 再包装成新想法。
- 证据：[Issue #31 审计与重训](https://github.com/Frysland-2024/AI4science/blob/codex/issue31-pr26-fair-diagnostic/overnight_pr26_20261019/TECHNICAL_REPORT.md)。

### 7. DONUT：借鉴 2D 衍射物理自编码器，为何在我们的 1D PXRD 没有成功
- **为何尝试：** DONUT 原工作用 encoder 预测物理 latent，经 decoder 和可微 physics simulator 两路输出，与观测衍射图做 weighted SmoothL1；不是对照模拟器偷给的干净真值图。研究思路与“重建误差反传”一致。
- **我们做了什么：** 在 BaTiO3 单 CIF、1D PXRD 上重做其核心双分支机制，分四阶段：固定仪器 q 反演、连同零点偏移、测量扰动/texture 压力测试、与有监督 A/B/C、物理-only 优化进行并列评估。
- **正式报告：** Exp1 q-MAE 约 0.3162；Exp2 约 0.3313；Exp3c 约 0.2894。Exp4 相同 noisy profile 比较中，直接监督模型 q-MAE 约 0.034–0.037，DONUT 分支 D 约 0.289；A/B/C 网络初值经共同局部精修约 0.000359，而 D 初值精修约 0.0298。三起点 physics-only E 最好目标约 0.000358565。
- **不能得出的结论：** 不能说原 DONUT 论文失败——原对象是二维扫描纳米衍射，向一维粉末谱的物理模型与可辨识特征迁移没有等价性。不同实验阶段、OOD stress、初值协议的 q-MAE 不能随手横比；某些早期 PR 摘要数值与最终技术报告口径不同，以完整数据/固定协议为准。
- **最终认识：** 对当前小型受限单模板问题，复杂的无监督架构并不天然胜过成熟监督网络或传统求解器，没必要为“更像 AI”强行保留它。
- 证据：[PR #35 工程串行器](https://github.com/Frysland-2024/AI4science/pull/35)、[PR #36 四阶段正式实验](https://github.com/Frysland-2024/AI4science/pull/36)、[最终报告](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-four-stage-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md)、[Exp4 原始对照](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-four-stage-20261019/donut_pxrd/reports/EXPERIMENT_4.md)。

### 8. 第二轮系统归因 + 新 D 干预（2026-10-19）
- **已核对事实：** 前一轮误差耦合与梯度冲突存在，但不能归因为单一原因。旧 validation 的原生 zero-shift 预测较弱，怀疑这是 q 的主要瓶颈。
- **唯一新预注册干预 D：** 与 B 相同的 measurement-aware reconstruction-to-q 梯度链上，额外提供模拟器 zero-shift 标注监督；额外标签是信息优势，绝非“同监督信息公平对比”的等价替代方案。
- **30 个候选训练、全新 512 参数样本、三配对 seeds、24 epochs、simple/V9、测试一次：** V9 的 q-MAE A/B/D = 0.03531/0.03238/0.04618。D 的 zero-shift RMSE 0.01255° 好于 B 的 0.02676°（约改善 53.1%），但 q-MAE 相对 B **恶化约 42.6%，3/3 seeds 更差**；简单条件 D 的 a-MAE 也退化。**关键假设被实验否定，不能救成正结果。**
- **补充精修（事后附加评价，不能冒充预注册的主结果）：** V9 网络初值 A/B/D 经有界 q+eta L-BFGS-B 精修 q-MAE 0.000439/0.000400/0.000437。共 1386 次网络初值精修运行成功（= 3 方法×2 条件×3 seeds×77；不是 1386 个独立真实样品）。物理-only 从单一中性初值 V9 q-MAE 0.01664，77/77 收敛；但更早 DONUT Exp4 的**多起点**传统物理优化已经达到约 0.000359，因此绝不能宣称 AI 初始化已胜过强传统多起点 baseline。
- **风险仍然存在：** simple 中一部分拟合触到参数边界；所有漂亮的参数真值都来自同一 CIF 合成数据，Forward generator 与反演器高度匹配，无法代表真实仪器误差。
- 证据：[审计与归因](https://github.com/Frysland-2024/AI4science/blob/codex/reconstruction-rootcause-retrain-20261019/docs/reconstruction_rootcause_20261019/AUDIT.md)、[失败归因排序](https://github.com/Frysland-2024/AI4science/blob/codex/reconstruction-rootcause-retrain-20261019/docs/reconstruction_rootcause_20261019/CAUSE_RANKING.md)、[最终实验和附加精修](https://github.com/Frysland-2024/AI4science/blob/codex/reconstruction-rootcause-retrain-20261019/docs/reconstruction_rootcause_20261019/FRESH_RESULTS.md)、[机读汇总](https://github.com/Frysland-2024/AI4science/blob/codex/reconstruction-rootcause-retrain-20261019/docs/reconstruction_rootcause_20261019/final_summary.json)。

## 四、平行探索：想做本科可用系统，而不只是研究一个新 Loss

### 9. “人也加入工作流”：已知候选结构 + phase router（PR #37）
- **当时设计：** 人提供样品背景、测量谱、仪器波长、候选 CIF；原七晶系分类只能作**弱软先验**，不能充当具体物相识别，也不能硬筛掉物相；分别进行物理候选排序与条件参数拟合，展示重建谱和差谱。
- **动机：** 直接从任意谱反推出未知完整晶体结构过难，而实际实验者通常已知样品的制备及可能材料家族；缩小候选集合能使本科系统可落地。
- **状态：** WIP 工程分支，不能把初步页面、synthetic demo 当成真实域或未知物相的已验证成果；与“下一阶段科学主线”平行，后续是否合并由证据决定。
- 证据：[PR #37](https://github.com/Frysland-2024/AI4science/pull/37)、[限定路由器方案](https://github.com/Frysland-2024/AI4science/blob/codex/phase-router-inversion-mvp-20261019/docs/PHASE_ROUTER_INVERSION_BACHELOR_MVP_20261019.md)。

### 10. 真正接触真实谱后的碰壁：RRUFF 和 Garnet（PR #38/#40/#41）
- RRUFF 反演数据审计：3,256 条元信息，筛出 Rutile 精确 ID 有晶胞标签 11 条（排除标注混相后 10）；Garnet 标签相对多（44），但同一样品真实 CIF 归属/化学一致性仍存在风险。不能把 AMCSD 同矿物的 CIF 当作当前 RRUFF 实验谱同一样品真值。
- Garnet 的其中一条路线（PR #40）：3 条 Grossular 谱拟合的 a 看似离参考值只有约 0.09–0.11%，但五初值精修结果间 a 的跨度 **0.546–0.846 Å**，远超事前限定的 0.02 Å 稳定阈值，结论是 PHYSICS_MODEL_NOT_READY，不能接着训练并声称真实参数可恢复。
- 另一条固定仪器、仅释放一个晶格参数的路线（PR #41）：12 条预先指定的开发谱，所有强峰与残差 gate 通过；后验 a 参考 MAE 0.01985 Å，12/12 谱残差降低但参考误差只在 6/12 改善。它与 PR #40 所用模板、自由参数和协议不同，不能直接用“一个成功一个失败”作方法孰优的判断。
- **认识变化：** 真谱的结构模板、仪器参数、背景与多解稳定性比模拟中复杂；“谱图贴合”不自动意味着晶格参数可信。真实谱阶段必须先做 physics gate 和多起点一致性，**再决定有没有训练价值**。
- 证据：[PR #38 RRUFF 数据审计](https://github.com/Frysland-2024/AI4science/pull/38)、[PR #40 真实谱不稳定](https://github.com/Frysland-2024/AI4science/pull/40)、[PR #41 限制自由度的另一协议](https://github.com/Frysland-2024/AI4science/pull/41)。

## 五、2026-10-19 晚间形成的阶段性决策

**优先选定方向（候选毕设，尚未导师正式确认）：Known-phase neural initialization + bounded physics refinement。**

- 这不是新 Loss；直接反演模型的训练改善不稳定，DONUT-PXRD 的无监督迁移较差，而已有监督网络能给出有限误差的初值，在单 CIF 合成谱上与物理优化串联能得到很低参数误差。
- **关键反证必须同页并存：** 强的多初值传统物理优化也可以很好；目前只能说该混合闭环可执行，不能说 ML 优于传统方法。
- 先保留人指定材料家族/候选 CIF 的现实前提，真实谱先验证物理模型，不强行通用 phase ID，不在本科阶段无限扩张多相、高维结构、Transformer/LLM、DONUT 大一统平台。
- 研究问题由“能不能证明 Forward Loss 改善直接参数反演”改为“AI 初值在何种情况下能提高受限 PXRD 物理精修的可靠性、速度或操作便捷度，真实谱上有无增益？”。
- 立刻执行层面：**只记录方向和设计评价 protocol，不另起训练、不覆写已冻结数据/结果。** 配套：[下一阶段具体规划](PXRD_NEURAL_INITIALIZATION_REFINEMENT_NEXTSTEP_20261019.md)。

## 六、今后申请/汇报应如何诚实描述这段经历

- **不能写：**“提出原创可微精修算法并在真实 XRD 上显著超越传统 Rietveld”；“DONUT 已被证明不适用于 XRD”；“1,386 个不同实验样本验证”；“Forward Loss 使所有参数预测持续提高”。
- **可以写：**“从同源监督的 PXRD 分类进一步探索物理参数逆问题；复现并修正 Forward reconstruction 的观测目标，检查梯度、参数耦合、数据来源和公平比较；在多轮可审计的负实验中发现仅减小谱图残差无法确保参数更准，因而将研究问题转向人机结合的已知候选结构 AI 初始化＋数值精修；完成单结构合成验证，真实谱与强多初值传统 baseline 尚待独立检验。”
- **个人思路的转折：** 一开始担心没有成熟范式，尝试用新模型/Loss 展示方法创新；后来认识到“更复杂的 AI”不是科学增益，设计合理的 forward 与公平物理 baseline、找出失败原因、收窄可用任务，反而是适合继续发展的研究能力。
- **真实历史不是直线：** 前一日想做纯参数回归；然后误判“重建只是验货”并被纠正回“重建损失参与训练”；意识到已经做过 → 审计失败 → 发现梯度与 nuisance 问题 → 修正实验仍负面 → 转向用 AI 预测初值＋传统优化，同时并行探索 phase router 和真实谱的模型失配。应保留这种往返，而非事后改写为一开始就确定混合框架。

## 七、证据与状态说明

- 以上数字均为不同 protocol 下的**描述性证据**；不可把 q 的归一化 MAE 和 Å 误差混为一谈。
- 大多数成果停留在多分支 Draft PR / 技术报告状态；研究日志不合并这些分支，也不代替其原始运行 JSON、模型 checkpoint、来源哈希和真实谱数据。
- 过去“失败”分为：假设未获支持、物理模型不稳定、网络性能不佳、工程运行失败或仅结果尚未验证；不能统统叫科研失败。
- 对任一历史细节如发现 PR 摘要与机读报告不一致，应回到该实验版本及锁定 JSON 核查，不能跨分支修正旧数据。
