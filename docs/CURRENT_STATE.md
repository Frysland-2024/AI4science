# AI4science 当前状态

**状态日期：** 2026-08-28

**阶段：** 模拟结果、RRUFF-301 few-shot 与 CNRS-318 zero-shot 均已完成；当前在做论文图表与成果封装

## 1. 当前科学设计

当前已经完成的项目想回答一个问题：在线 PXRD 模拟器知道哪些谱图来自同一个母体结构，能不能把这种关系变成额外的监督信号，让七晶系分类器在测量条件变化时更稳。

最终确定的设计：

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency，一致性权重 `lambda_js=60`；
- 预处理：不做额外处理；
- 优化器：AdamW；
- 学习率：恒定；
- 划分：训练 9,842 / 验证 2,109 / 测试 2,109；
- 划分方式：按母体结构严格分开，训练/验证/测试不共享同一母体。

## 2. 已经做完的事

- 在验证集上跑完了五组配对实验；
- 在选好的模型上完成了模拟测试集评估；
- 固定了模型、数据、扰动、优化器和训练量；
- 把公开的结果和论文的说法统一了；
- 精简了公开文件，只留下训练、评估和核对结果需要的部分；
- 明确当前结果不再通过新增 loss、重新调参或重开训练改变。
- 完成 RRUFF-301 的 K=1/2/5 locked-test few-shot 评测并回溯核验结果；历史 prospective provenance 不完整，因此不将其表述为 provenance-complete confirmatory execution；
- 完成 CNRS-318 的 10-checkpoint zero-shot 外部域评测、原始输入复建和结果完整性审计；
- 完成模拟 Test 与 CNRS 的概率可靠性审计；
- 完成跨平台换行规范化哈希校验与全量回归测试（`122 passed`）。

## 3. 结果与当前评价口径

主科学判断采用 PXRD / Materials ML 社区常用的 performance-reporting 范式，并按三层证据组织：Macro-F1、balanced accuracy、accuracy、mean ± std、多 seed 一致性、few-shot learning curve、label efficiency 和 per-class F1 是主 performance layer；ECE/NLL/Brier 等是 reliability 增强证据；paired/class-stratified parent bootstrap、95% CI 与不确定性分解是 strict statistical audit。单个 CI 跨 0 不再自动把整体一致的结果判成失败。当前权威规范见 [`PXRD_RESULT_REPORTING_STANDARD.md`](PXRD_RESULT_REPORTING_STANDARD.md)，方法论转变的历史缘由见 [`PROJECT_HISTORY_NOTE_2026-08-27_REPORTING_STANDARD_RESET.md`](PROJECT_HISTORY_NOTE_2026-08-27_REPORTING_STANDARD_RESET.md)。

这项修正只改变证据层级，不改变实验或原始结果：不得删除不利统计结果、隐藏跨零 CI、看结果后换指标、修改 frozen test 数据、重选 checkpoint/seed、反复重跑到满意，或改写历史 raw outputs。

| 指标 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | Δ `+0.046569`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | Δ `+0.054600`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | Δ `+0.054454`；5/5 为正 |
| RRUFF-301 · K=1 few-shot locked-test Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | Δ `+0.0433`；21/25 为正 |
| RRUFF-301 · K=1 few-shot locked-test Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | Δ `+0.0384`；20/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | Δ `+0.0460`；23/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | Δ `+0.0488`；23/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | Δ `+0.0545`；24/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | Δ `+0.0568`；23/25 为正 |
| CNRS-318 · zero-shot seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | mean paired Δ `+0.01871 ± 0.00675`；5/5 为正 |
| CNRS-318 · zero-shot pooled Macro-F1（描述性） | 0.19118 | 0.20912 | `+0.01794` |
| CNRS-318 · zero-shot Balanced Accuracy | 0.21823 | 0.23878 | `+0.02055` |
| CNRS-318 · zero-shot Accuracy | 0.20000 | 0.21006 | `+0.01006` |
| CNRS-318 · zero-shot ECE ↓ | 0.68257 | 0.61242 | `−0.07015`（更低为好） |

表中 `±` 均为对应重复运行的 sample standard deviation；完整 mean±SD、paired consistency 与 provenance 边界见 [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)。

结果文件：

- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/reports/validation_results.json`](../xrd_robustness/reports/validation_results.json)
- [`../xrd_robustness/reports/simulated_test_results.json`](../xrd_robustness/reports/simulated_test_results.json)
- [`../xrd_robustness/reports/rruff301_fewshot_results.json`](../xrd_robustness/reports/rruff301_fewshot_results.json)
- [`../xrd_robustness/reports/CNRS_318_RESULTS.md`](../xrd_robustness/reports/CNRS_318_RESULTS.md)
- [`../xrd_robustness/reports/CALIBRATION_ANALYSIS.md`](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md)

## 4. 当前实现

主要实现：

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/scripts/train.py`](../xrd_robustness/scripts/train.py)

结果已经确定，不会再改。公开仓库里只留了当前实现、运行配置、结果和使用文档；`train.py` 是可复用的方法参考，分数看已有模型的评估结果文件。

这里说的"结果已经确定"包括模拟部分和两个角色不同的实验域。CNRS 的结果是
**zero-shot 外部域压力测试**，不是使用 CNRS 标签做域适配；冻结配置保持原样，执行完成状态由
结果报告和 run record 另行记录。

## 5. 实验进度

方法对比、验证集和模拟测试集的评估都做完了，模拟部分的结果已经确定、不会再改。

两个实验真实域互补，主任务不同：

- **RRUFF-301**：平衡、人工整理的实验真实域（balanced curated experimental domain），主任务是 K=1/2/5 few-shot adaptation。
- **CNRS-318**：自然不平衡、跨数据库的独立实验真实域（naturally imbalanced independent experimental domain），已正式定级为第二实验域，主分析是 frozen-model zero-shot external evaluation，保留自然类别分布 `21 / 87 / 77 / 41 / 33 / 12 / 47`。

两个真实域均已有结果，但不合并成一个分数：

- CNRS-318 的权威审计与父样本 manifest 已进入 git（见 [`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) 和 [`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv)）；
- 评测已按冻结协议执行完毕；pre-run 协议文件保持原样，完成状态与纠错记录见结果报告和 run record（[`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md)）；
- 人工标签质量复核**不计划执行**：标签由 deposited structure 稳定重建、未做人工物相核验，这一限制将如实注明；
- 真实数据不参与模型、checkpoint、seed 或 `lambda_js` 选择。
- CNRS-318 的五个 seed 均 favor JS，平均配对 ΔMacro-F1 为 `+0.018713`；pooled Macro-F1、balanced accuracy、accuracy、ECE、NLL 与 Brier 共同改善。修正后的 class-stratified paired-parent 95% CI 为 `[−0.009339, +0.046107]`，说明自然类别不平衡和低支持类别带来较大的统计不确定性；该区间作为严格审计如实保留，但不单独否决上述多 seed、多指标一致的科学结果。
- CNRS 的绝对 sim-to-real 表现仍弱、校准仍差；overall accuracy `0.200→0.210` 低于多数类基线 `0.274`，不能包装成已解决的真实域分类。

## 6. 当前卡点

现在主要是把已有数字转化为清楚、可复述的成果：

- 生成五种扰动图、同源双视图方法图和配对结果图；
- 完成仿照“组会1”视觉语言的阶段汇报；
- 完成方法、结果和讨论正文；
- 确保公开结果、图表和讲稿中的数字完全一致。

## 7. 当前项目下一步

1. 从 `reports/validation_results.json`、`reports/simulated_test_results.json` 和真实域结果文件生成论文与 PPT 图表。
2. 完成方法、结果和讨论章节。
3. 将组会 PPT、技术报告和一页项目摘要整理为申请可复用成果。
4. 把 RRUFF-301 few-shot 与 CNRS-318 zero-shot 分表写入正文，并补齐结果图；不重开模型选择或事后删改 CNRS 样本。

复现当前工程检查的命令：

```powershell
cd xrd_robustness
python -m pytest -q
```

## 8. 并行的下一项目规划（尚未启动）

在不改变当前分类项目的前提下，下一代项目已经正式收敛为：

> **已知相参考条件下的 PXRD 定量反演：从观测谱和名义参考谱中估计晶格与测量参数，并通过前向衍射和局部精修验证。**

第一版只计划做：

- 单相；
- 已知候选结构；
- 四方晶系；
- 晶胞尺度、四方畸变、零点偏移和峰宽；
- 同源双视图中的结构参数一致性；
- 分阶段加入前向物理一致性；
- 比较名义初始化与 ML 初始化后的相同局部精修。

相关文档：

- [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md)
- [`XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md`](XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md)
- [`PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md`](PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md)

该项目目前仅完成问题定义、边界收缩和执行规划。必须先完成四方结构数量审计与可辨识性 Gate，才创建 `xrd_inversion/` 代码目录并启动训练。
