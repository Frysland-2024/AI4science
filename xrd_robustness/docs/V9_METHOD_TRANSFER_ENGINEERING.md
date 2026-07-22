# V9-T 算法迁移论文工程契约

状态日期：2026-07-22。项目当前正式身份为 **V9-T：算法迁移主线**，唯一目标是完成算法迁移论文。9,842 / 2,109 / 2,109 的 family-aware（家族分组）70/15/15 划分和统一 Validation 契约已经冻结。方法参数语义 Gate 与六候选 Train-only 梯度尺度 Gate 均已通过；JS `[0.3,3,30]`、Residual `[0.2,2,20]` 已在唯一一次人工修订后冻结。训练仍为 0/7 调参、0/15 正式开发实验，simulated test 0 次、real test 0 次；所有执行开关继续保持关闭，等待用户单独授权 7-run。

本研究没有 Pilot 阶段，也不使用 A/B/C2 命名。动态增广是单纯数据增广范式的一种强实现，同时负责生成成对视图，但不作为创新点；结构化扰动继续封存。Near-clean ERM 与离线物理增强只是参考基线。模拟器标签监督残差研究已延期为 **V10：Simulator-Supervised Representation Learning**，不属于当前论文、实验矩阵或资源计划。

## 论文核心问题与叙事（冻结）

### 一句话核心问题

在相同的晶体结构、物理扰动视图、模型和计算预算下，显式建模同一晶体结构不同扰动视图之间的关系——通过一致性训练或残差类别去相关——能否在单纯数据增广之上，提高 PXRD 模型对未知扰动和真实实验谱的泛化？

### 为什么这是一个论文问题

模拟 XRD 容易大规模生成，但实验测量中的零点偏移、峰展宽、背景、噪声和择优取向会造成模拟—真实差距。XRD 领域常见方案主要依赖数据增广：离线预生成大量扰动谱、在线动态生成扰动谱、扩大扰动种类与强度，或提高物理模拟真实性。它们的共同逻辑是扩大模型见过的输入覆盖；这一步必要，但通常把同一晶体结构的不同扰动视图分别当作分类样本，没有直接约束这些视图之间的预测或表征关系。

普通增广训练可写为 `T1(x) → y`、`T2(x) → y`：两个视图共享母结构和标签，却作为独立监督样本优化。V9-T 增加的不是更多扰动种类，而是跨视图学习目标。论文递进因此冻结为：

```text
单纯数据增广
→ 跨视图一致性
→ 差异感知的残差去相关
```

其他机器学习领域已经出现两类可迁移思路：一是要求同一对象的两个扰动视图保持预测一致；二是把两个视图的特征差定义为 residual，并减少 residual 中的类别信息。本论文不声称发明这两种通用算法，而是检验它们在 XRD 物理扰动场景中是否真的产生超越单纯数据增广范式的增益。

### 论文故事只走这一条线

1. **实际问题**：模拟谱训练的晶系分类器需要面对实验测量变化；
2. **现有范式与直接基线**：对照对象是单纯数据增广；Dynamic/Paired ERM 在相同成对动态扰动视图上只做普通监督训练，因此是最强、最公平的直接基线，Near-clean 和离线增强提供补充参考；
3. **方法迁移**：在相同配对视图上加入 JS Consistency，并重点检验 Residual Class Decorrelation；
4. **受控验证**：用家族互斥的统一 Validation、单因素 OOD、未见组合 OOD 和 matched-budget（匹配预算）审计排除数据与算力混杂；
5. **最终论证**：开发阶段最多选择一个主方法，冻结后依次进行 simulated test 和只使用一次的 real test。

### 论文贡献边界

允许主张的贡献是：

- 系统地把两种跨领域鲁棒学习机制适配到成对 XRD 物理扰动视图；
- 在完全匹配的数据、谱图流和计算预算下，分离数据增广覆盖与显式跨视图关系学习的净增益；
- 建立覆盖单因素、未见组合和真实谱的严格 sim-to-real 评测协议。

不得主张：创造了新的通用一致性理论、创造了新的通用 residual 学习算法、证明 residual 等价于测量因素，或已经证明模拟器标签监督有效。

### 结果出来后怎样讲，不能事后改题

- JS 在统一 Validation 上表现最好且配对证据支持：JS 是论文主方法，residual 去相关作为对照；
- residual 通过且直接配对统计稳定优于 JS：residual 去相关是主方法，允许讨论“保留合理测量差异、减少其中类别信息”的解释；
- residual 优于 Dynamic ERM、但没有稳定优于 JS：报告 residual 的正向增益，但不得声称其机制比一致性训练更先进；
- 两者都有效但直接差异不清楚：工程上仍冻结平均增益较高者进入最终测试，但论文写成同预算的一致性与 residual 鲁棒学习比较，不强行声称 residual 更先进；
- 两者都未显示可靠增益：先检查模拟器域差异、OOD 设计、backbone 与 split、真实谱预处理，不立即堆叠模块。

暂定论文定位可概括为：**一项检验显式跨视图关系学习能否在单纯数据增广之上改善 XRD 模拟—真实鲁棒性的受控跨领域方法迁移研究。**

## 三个论文主方法与两个参考基线

核心问题是：在相同 XRD 数据、物理扰动视图、模型、训练预算和固定评测面板下，从其他机器学习领域迁移来的 JS 一致性或残差类别去相关，是否能在单纯数据增广之上带来额外泛化收益？

论文主比较是 Dynamic/Paired ERM、JS Consistency 和 Residual Class Decorrelation。为交代领域基线，还保留 Near-clean ERM 与离线物理增强，因此工程上仍是五组、每组 3 个 seed，共 15 次：

1. `clean_erm_reference`：Near-clean ERM 参考基线，使用 `level0` 固定视图；`clean_erm` 仅作为兼容已有训练器和结果文件的内部句柄；
2. `offline_physical_augmentation_reference`：离线物理增强参考基线，每个结构冻结 4 个视图，每步配对使用 2 个；
3. `ordinary_dynamic_augmentation`：Dynamic/Paired ERM，是单纯数据增广范式中与两个迁移方法共享训练视图的最强直接基线；
4. `js_consistency_transfer`：JS consistency（一致性约束）候选；
5. `residual_decorrelation_transfer`：residual class decorrelation（残差类别去相关）候选。

`level0` 仍在 40,000 计数尺度下执行 Poisson 采样，因此它是低统计噪声、最小扰动参考，而不是严格无噪声的 ideal clean spectrum。论文、图表和结果讨论统一使用 **Near-clean ERM**；代码、配置和历史产物继续使用 `clean_erm`，避免破坏兼容性。

最终论文方法只从第 3、4、5 组中选择：若迁移方法未带来可靠收益，Dynamic/Paired ERM 可以成为诚实结论；若 JS 或 Residual 更优，则按统一 Validation 的预注册主指标选择得分最高者。Residual 是重点假设，但必须用相对 Dynamic ERM 和 JS 的直接配对证据决定能否支持更强主张。Near-clean 与离线增强不是额外研究路线。模拟器标签监督在本契约中必须保持 `false`。

## λ 的证据链与当前阻断状态

`lambda_js` 和 `lambda_res` 是辅助损失相对分类损失的数值权重。`1.0` 只表示损失公式中的系数为 1，不代表辅助目标与分类目标同等重要，也不代表它已经被验证为最佳值。方法参数的合法性链固定为：方法原理 → 损失数学尺度与 reduction → Train-only 数值审计 → 预注册 Validation 选择 → 三点敏感性与多 seed。

- JS 集合 `{0.1, 0.3, 1.0}` 来自旧工程文档和默认配置，是内部预注册起点，不是独立外部数值依据。
- 残差去相关集合 `{0.01, 0.1, 1.0}` 来自旧 YAML/default，同样不能作为自身合理性的证据。
- V9.2 第 424 行的 `{0.1, 0.3, 1.0}` 是模拟器标签监督研究的 `lambda_meas`，不得倒灌为算法迁移的 `lambda_res` 依据。
- Hu et al. 的 SD3Net 式 (17) 与 Table 5 把去相关权重写为 `lambda_3=1`，而 Fig. 12 另有一个约在 `1e-4` 最优、却没有明确映射到 `lambda_3` 的 regularization parameter `lambda`。该论文支持“相对损失比例 + 敏感性 + 消融”的程序，不支持把 `1e-4` 或 `1` 直接迁移为本项目 `lambda_res`。

新语义审计已证明 JS 的自然对数范围是 `[0, ln(2)]`，Residual 的 `KL(q || Uniform)=ln(7)-H(q)`，两者均为 batch mean；具体实现都是类别维求和后只除以 batch，并不存在重复 class mean。`lambda=0` 退化、交换语义、方向、数值稳定性、梯度流和调度也全部通过。

新版正式 B3、七类平衡 Train 子集、128-step 审计使用 128 个不重复配对 batch，并把监督分类头排除在 backbone 梯度范数之外。它显示 late 段分类准确率仅 `11.96%`（随机 `14.29%`）、`L_cls=1.9499`（均匀交叉熵 `ln(7)=1.94591`）；两个视图 top-1 却有 `99.34%` 一致，prediction JS 只有约 `2.97e-7`。Residual probe 的 late pre-update 准确率为 `14.62%`、交叉熵为 `1.94613`，也未证明具有类别预测能力。因此当前六个候选梯度比小首先是“主干与 probe 尚未学起来”的诊断信号，不能解释为合理权重应是几万。

梯度倒数得到的诊断补偿倍数约为 JS `2.874e5`、Residual `2.556e4`，但它们不是理论权重、不是网格提案，也没有进入正式配置。后续 learned-state 审计先证明主干和 residual probe 具有可解释信号；用户再批准唯一一次 decade-grid 修订，六候选 Gate 以真实 Train-only autograd 测量证明 JS `[0.3,3,30]` 与 Residual `[0.2,2,20]` 覆盖 weak/material/dominant。完整指标、审计工具修正和冻结政策见 `docs/V9_METHOD_PARAMETER_GOVERNANCE.md` 与 `configs/v9_method_parameter_governance.json`。Validation-only tuning execution 仍关闭，候选范围不得再次修改。

## 统一 Validation 的职责

Validation 固定为 2,109 个结构，不再拆分调参子集与独立方法判定子集。它与 Train、Test 在结构 ID、精确结构指纹和匿名 Wyckoff 家族代理层面均互斥，统一承担：

- λ 与其他预注册超参数选择；
- early stopping 与 checkpoint 选择；
- Dynamic/Paired ERM、JS Consistency、Residual Class Decorrelation 的开发阶段比较。

这会得到常规机器学习研究中可解释的开发估计，但不能被描述成独立验证复制。最终泛化证据只能来自完全锁定的 Test 和 External Real Test。

调参共 7 次完整预算运行：Dynamic/Paired ERM 直接基线 1 次、3 个 JS 权重、3 个残差权重。固定调参 seed 为 `20260710`，评测 seed 为 `20260720`。选择指标是六个单因素 OOD 的平均 Macro-F1，ID Macro-F1 相对基线下降不得超过 0.01；同分时选较小 λ。该过程名称固定为“Validation-only development tuning”，不称 Pilot。

调参结果必须写入带哈希的 `reports/v9_method_transfer_tuning_selection.json`，再把两个 λ 写回并冻结到算法契约。未完成这一步时，15 次正式计划会拒绝生成。

## 固定评测面板

所有方法和 seed 使用同一个评测 seed、同一个结构清单和同一组谱图 manifest：

- ID：`in_range`；
- 六个单因素 OOD：正/负零点偏移、峰展宽、噪声、背景、择优取向；
- 三个预注册未见组合：偏移+展宽、背景+噪声、择优取向+偏移；
- 综合压力条件：`ood_all`。

评测必须导出 Accuracy、Balanced Accuracy、Macro-F1、逐类 Recall/F1、混淆矩阵、worst-group F1 和 15-bin ECE。

每次运行还必须记录 run ID、研究/评测契约哈希、解析配置哈希、源代码树哈希、数据/子集/模拟/峰缓存/训练视图/评测视图/checkpoint 哈希、训练与评测 seed、Python/PyTorch/CUDA/GPU、optimizer steps、前向视图数、谱图曝光数、耗时、GPU-hours 和峰值显存。

## 公平性与统一 Validation 比较

三个核心组在相同 seed 下必须共享结构、动态 pair、训练谱图流、optimizer steps、backbone forward 数、谱图曝光数、最后固定预算 checkpoint 规则和评测面板。Near-clean 与离线基线的训练视图按定义不同，但计算预算和评测面板仍保持一致，其固定视图 manifest 单独保存哈希。

预注册的唯一选择主指标为六个单因素 OOD 的平均 Macro-F1。Dynamic/Paired ERM、JS 和 Residual 在 3 个 seed 上完成同预算比较后，按该指标的三 seed 平均值选择唯一最高者；仅在数值并列时选择复杂度更低者。不存在额外的 pass/fail 式方法判定。

为限制过度解释，JS 或残差候选相对 Dynamic/Paired ERM 的下列证据必须全部报告，但不作为“通过/失败”阈值：

- 六个单因素 OOD 的平均 Macro-F1 提升至少 0.01；
- 3 个 seed 的配对增益全部为正；
- 以母结构/family cluster 为独立单元、在各 seed 内配对重采样并跨全部注册 seed 汇总的 hierarchical bootstrap 95% 区间下界大于 0；禁止只对三个 seed 汇总值反复 bootstrap；
- ID Macro-F1 平均下降不超过 0.01；
- 任一单因素 OOD 平均下降不超过 0.01；
- 任一预注册组合 OOD 平均下降不超过 0.01。

此外，“Residual 稳定优于 JS”的论文主张必须单独计算 `Residual - JS` 的逐 seed 配对差：平均值为正、3 个 seed 全部为正、family-level hierarchical bootstrap 95% 区间下界大于 0。分别优于 Dynamic ERM 并不足以证明 Residual 优于 JS。

每个正式 run 必须导出并在 `results.json` 中以 SHA256 绑定 `prediction_rows.jsonl`。每行至少包含 seed、method ID、profile、material ID、family ID、label、prediction 和 probabilities；缺失、重复、方法/seed 不符、profile 不完整或哈希不符时，统一 Validation 比较必须 fail closed。

工程选择只看冻结的 Validation 主指标与并列规则；论文是否声称方法优越性仍由上述直接配对统计决定。真实谱不参与任何开发选择。

## simulated test 与 real test

simulated test 使用锁定的 2,109 个 Test 结构、3 个固定评测 seed 和完整扰动面板。这里的 IID 指“扰动范围与训练一致”，测试结构本身仍与 Train/Validation 家族互斥。它只能在统一 Validation 选出唯一方法并冻结 3 个 checkpoint 后单独授权，结果不得回流改变方法。

real test 只用于最终外部测试。真实谱清单必须包含来源、许可、相纯度、标签证据、结构标识和谱文件哈希；预处理固定为 10–80°、0.02°、线性插值、max normalization，不做基线扣除、平滑或人工改峰。真实谱不得参与模拟参数、λ、方法或 checkpoint 的选择。

## 机器可读入口

为避免破坏已经冻结的路径和哈希，现有文件名继续保留 `v9_method_transfer`；项目身份以契约中的 `program_id=V9-T` 为准。

- `configs/algorithm.v9.method_transfer.json`：研究、调参、五组实验、公平性与执行门禁；
- `configs/v9_method_parameter_governance.json`：方法参数来源、语义/尺度证据哈希、固定次要参数与范围 Gate；
- `configs/evaluation.v9.method_transfer.json`：开发、simulated test 与 real test 的独立契约；
- `configs/real_test.v9.method_transfer.template.json`：真实谱清单与预处理模板；
- `configs/simulation.v9.method_transfer.frozen.json`：冻结扰动及未见组合；
- `configs/data.v9.method_transfer.family_split.json`：冻结的数据划分契约；
- `data/formal_14060/manifests/split_manifest.v9t.family_v1.csv`：9,842 / 2,109 / 2,109 主划分；
- `data/formal_14060/manifests/v9_method_transfer_validation.csv`：统一 Validation 清单；
- `reports/v9_method_transfer_split_audit.json`：结构、指纹、家族和视图继承审计；
- `scripts/run_v9_method_transfer.py`：只读预检、计划、选择和 Validation 比较入口。

## 训练数据流与可重放审计

训练结构不再按固定排序循环。每个 epoch 使用训练 seed 控制的 `sha256-key-sort-v1` 确定性 shuffle（可重放洗牌），五种方法在相同 seed 下共享同一结构 batch 顺序。固定 step 预算下，epoch 尾部不足一个 batch 时只在该 epoch 的洗牌序列内确定性回绕，因此每一步仍保持 16 个结构。

在当前 9,842 个训练结构、batch size 16 和 30,650 个 optimizer steps 下，每次运行共有 490,400 次结构曝光，平均每结构 49.827 次。以冻结的调参 seed `20260710` 重放后，单个结构实际出现 49–52 次；因此论文只能报告平均值和审计得到的范围，不能声称每个结构恰好出现 49–50 次。

动态训练参数不再预生成 `全部结构 × 全部 epochs × 全部 steps × 2 views` 的 `train_view_manifest.jsonl`。训练器只为确定性预取窗口内的实际 batch 在线生成参数记录；桌面执行配置为 `batch_size=16`、`worker_processes=8`、`prefetch_batches=8`，因此任意时刻最多保留 `16 × 2 × 8 = 256` 条参数记录，而不是 606,267,200 条。worker 数量不改变驻留上限。完整流由训练 seed、物理配置哈希、采样协议和 batch 上下文重放。训练目录必须保存：

- `training_sampler_contract.json` 及其哈希：固定结构集合、seed、batch size、预算和 shuffle 算法；
- `train_view_stream_contract.json` 及其哈希：仅动态方法保存，固定在线参数流协议；
- `training_stream_audit.json`：逐 epoch 保存 shuffle 哈希，并增量累计结构顺序、pair 顺序和实际参数 pair 的流哈希；
- `results.json` 中的 `training_stream_audit` 与审计文件哈希：保存实际 optimizer steps、结构暴露量和谱图暴露量。

公平性门禁分三层解释：五种方法的 `sampler_hash` 和 `pair_schedule_hash` 必须相同；Dynamic/Paired ERM、JS、Residual 的 `parameter_pair_hash` 必须相同；Clean/Offline 的实际参数 pair 按定义不同，不得误报为与动态方法相同。调参或正式训练前运行 `scripts/audit_v9_training_stream.py`，以冻结的 9,842 个训练结构和 30,650-step 预算执行无模型、无谱图渲染的真实规模流审计。

动态谱图生成与质量门在单 run 使用 8 个持久 `spawn` worker；双 run 时每条分配 4 个，总预算仍为 8。结构通过 `sha256-material-id-mod-v1` 固定分片；每个 worker 只懒加载自己分片内的 peak table，并通过 `fixed-native-thread-env-v1` 把 NumPy/BLAS 等原生线程池限制为 1，避免多进程内部再次过度并行。完成顺序可以不同，但主进程必须按 `absolute-step-then-batch-offset` 重组，并重新验证结构顺序和成对 manifest。训练 batch 使用 pinned memory（页锁定内存）与 non-blocking H2D（非阻塞 CPU→GPU 传输），使 worker 在 GPU 前向/反向期间继续准备后续 batch。`scripts/audit_v9_dynamic_prefetch.py` 在正式数据上同时执行串行与多进程路径，要求谱图数组、实际接受参数行、质量门计数和 pair hash 完全一致，结果写入 `reports/v9_dynamic_prefetch_audit.json`。

## 当前可执行命令

```powershell
# 真实规模训练流审计，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_training_stream.py

# 正式 peak cache 上的串行/多进程等价性与吞吐审计，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_dynamic_prefetch.py --batches 16

# pinned memory / non-blocking H2D CUDA transfer audit; no training
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_cuda_transfer.py

# 只读预检
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py preflight

# 生成 7 次调参计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-plan

# 检查最终测试仍处于锁定状态
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py final-preflight

# 调参结果冻结前，这个命令必须拒绝生成正式计划
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py plan

# 单元测试
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -q
```

当前新 split 与统一 Validation 已冻结，但 7 次 Validation-only 调参尚未获得方法参数 Gate 的执行许可。旧的 40-epoch checkpoint 只作归档，不能续跑；迁移到台式机后也必须先完成候选范围复核和冻结，再由用户单独授权并从第 0 步开始。`development_tuning_execution_enabled=false`、`experiment_execution_enabled=false`、`simulated_test_enabled=false`、`real_test_enabled=false` 继续保持；15 次正式实验和两类最终测试仍需要各自独立授权。
