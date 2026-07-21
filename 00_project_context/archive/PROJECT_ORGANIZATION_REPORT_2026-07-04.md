# XRD Consistency 项目报告书

重写日期：2026-07-04

## 1. 项目定位

本项目不是单纯的 XRD 分类准确率项目，而是一个面向科学测量数据的鲁棒性研究：

> 构建一个可复现、物理可信的 1D powder XRD 测量可靠性 benchmark，评估同一晶体结构在合理测量扰动下，模型预测是否保持稳定，并用 consistency regularization 尝试提升这种稳定性。

核心判断不是“模型能不能在干净数据上分类”，而是：

- 在物理上 label-preserving 的测量扰动下，模型会不会预测翻转。
- 哪类扰动、哪个 severity、哪些类别或样本最脆弱。
- consistency training 是否比普通 augmentation 更能降低这种不稳定。
- simulated stress test 的结论是否能在 real-XRD 数据上得到外部支持。

形式化表达：

```text
x' = T_phys(x)
y(x') = y(x)
f(x') should be close to f(x)
```

这个项目的长期价值不局限于材料学。它可以被包装成“科学测量 AI 的鲁棒性与可靠性”项目，对医学 AI 方向也有迁移意义：医学影像同样面对设备差异、扫描协议、噪声、伪影、重建参数和域偏移问题。

## 2. 当前 MVP 范围

输入：

- 统一网格上的一维 powder XRD intensity pattern。

初始任务：

- 晶系 / 对称性分类。
- 具体 taxonomy、class order 和 label mapping 需要从 SimXRD 实际数据中确认。

数据主线：

- SimXRD 风格模拟数据作为可控 benchmark 基础。
- real-XRD 数据作为后续 external validation，不作为装饰性附录。

方法主线：

- clean baseline。
- 物理扰动 stress test。
- augmentation-only。
- augmentation + consistency。

核心扰动：

- 2theta / zero shift。
- peak broadening。
- noise。
- background。

暂缓或高风险扰动：

- preferred orientation / texture：可作为次级扰动。
- unit-cell variation：不应默认视作 label-preserving。

核心指标：

- CleanAcc。
- PerturbedAcc。
- Accuracy drop。
- FlipRate。
- pairwise consistency。
- JS / KL disagreement。
- calibration。
- sample-level churn。

## 3. 核心实验设计

当前必须先完成三组基础对照：

```text
Clean -> Aug-only -> Aug + Consistency
```

| 组别 | 含义 | 作用 |
| --- | --- | --- |
| Clean | 无增广、无一致性约束 | 建立干净数据上的基础脆弱性基线 |
| Aug-only | 训练时加入物理扰动，仍只用监督分类损失 | 检验“看过扰动数据”是否足够 |
| Aug + Consistency | 与 Aug-only 使用完全相同的增强与分类监督，再增加一致性损失 | 检验一致性在普通增强之外的额外价值 |

必须公平比较 `Aug-only` 和 `Aug + Consistency`：两组使用相同扰动、双视图分类损失和训练预算，只允许一致性项不同。不存在无 augmentation 的 consistency-only，因为一致性本身需要 `T_phys(x)`。

建议第一阶段只做 supervised paired consistency，不急着上 unlabeled SSL：

```text
D(p(x_clean), p(T_phys(x_clean)))
```

其中 `D` 可先从 JS divergence、KL divergence 或 logit MSE 中选择一个，并且只在 validation set 上调参。

## 4. 暑假执行策略

暑假的目标不是把所有算法想法都做完，而是把主线打穿，形成可信、可复现、能展示研究判断力的结果。

### 7 月：先搭研究地基

7 月由你主导，优先完成：

- 审清数据来源、schema、坐标网格、intensity normalization。
- 确认 label 字段、class mapping、source structure ID。
- 建立 structure-level split manifest，避免同一结构的不同扰动视图跨 split 泄漏。
- 实现 deterministic loader、基础可视化脚本、简单 1D-CNN clean baseline。
- 搭出 perturbation sandbox，至少实现 identity transform 和 1-2 个扰动范例。
- 确定 augmentation transform 的接口规范：输入输出、severity、随机种子、参数记录、是否 label-preserving。
- 建立 metrics skeleton：accuracy drop、FlipRate、JS / KL disagreement、pairwise consistency。

7 月不建议追求复杂算法模块。这个阶段最重要的是让实验骨架可信。

### 8 月：同伴接入 data augmentation 执行层

8 月让同伴边学边做，负责 data augmentation 的执行层是合理安排。这个入口明确、产出具体，也能让他自然理解 XRD 的物理扰动。

建议给他的责任边界：

- 实现四类 augmentation transform：shift、broadening、noise、background。
- 实现 severity sweep 配置。
- 生成 clean vs perturbed overlay gallery。
- 编写 transform smoke tests：
  - identity test。
  - zero-severity test。
  - shape preservation。
  - non-negativity 或合理 intensity range check。
  - deterministic seed test。
- 维护 augmentation 参数表和 evidence ledger 草稿。
- 负责跑或协助跑 `Aug-only` 实验线。

不建议他一开始负责：

- consistency loss 设计。
- perturbation-aware weighting。
- 最终科学叙事。
- label-preservation 决策。

这些仍应由你主导，因为它们决定项目是否从普通工程训练变成研究问题。

### 8 月后半段：主线结果闭环

如果 7 月和 8 月前半段顺利，可以推进：

- Clean baseline 完整训练。
- Aug-only 训练。
- Aug + Consistency 训练。
- 多 severity stress test。
- 多 seed 或至少关键设置重复实验。
- 失败样本、失败类别和扰动敏感性分析。

只有在主线结果稳定后，再加一个最贴合项目叙事的算法模块。

## 5. 算法模块优先级

这些算法模块是储备池，不是暑假任务清单。

| 优先级 | 方法 | 当前建议 |
| --- | --- | --- |
| 必做 | Clean / Aug-only / Aug + Consistency | 暑假主线 |
| 第一候选 | Measurement-disparity decorrelation | 胡浩天论文启发的第二阶段方法 |
| 第二候选 | Perturbation-aware consistency weighting | 主线顺利后再测试 |
| 第三候选 | Curriculum consistency | 可作为简单训练策略 ablation |
| 第四候选 | Mean Teacher / EMA | 仅当普通 consistency 不稳定时再上 |
| 第五候选 | Confidence-gated consistency | 后续可和扰动权重结合 |
| 远期 | Adaptive augmentation policy | 可作为同伴 augmentation 支线后续升级 |
| 远期 | Cross-view FFT consistency | 模型型创新，成本较高 |
| 远期 | Perturbation-specific experts | 更大项目或未来论文方向 |

最推荐的演化路径：

```text
Stage 1:
Clean -> Aug-only -> Aug + Consistency

Stage 2:
Aug + Consistency -> Aug + Consistency + Measurement-Disparity Decorrelation

Stage 3:
Measurement-Disparity Decorrelation
+ Perturbation-aware weighting
+ Curriculum
or
+ EMA Teacher
or
+ Confidence Gating

Stage 4:
Cross-view spectral consistency
/ perturbation-specific experts
```

一句话原则：

> 第一阶段先证明 consistency 是否有价值；第二阶段再研究“什么样的 consistency 才符合 XRD 的物理扰动结构”。

## 6. 医学 AI 申请叙事

如果以后申请医学 AI 方向，这个项目的竞争力取决于表述方式。

较弱表述：

> 我做了一个 XRD 晶体分类项目。

更强表述：

> 我研究了科学测量数据中模型预测在物理扰动、仪器误差、噪声和背景漂移下的稳定性，并设计 consistency regularization 框架提升测量鲁棒性。

与医学 AI 的连接：

- XRD 的 zero shift、broadening、noise、background 类似医学影像中的 scanner shift、protocol shift、noise、artifact、reconstruction variation。
- 项目关注 reliability、calibration、domain shift 和 external validation，而不是只看 IID accuracy。
- label-preserving perturbation 的审查意识，可以迁移到医学影像中的 clinically label-preserving augmentation。
- Clean / Aug-only / Aug + Consistency 的公平对照，体现研究可解释性和工程可复现性。

申请材料中可以使用的定位句：

> I studied consistency regularization for measurement-robust classification under physically meaningful perturbations in 1D scientific signals, with methodological relevance to robust medical imaging AI under acquisition shift.

如果后续能补一个小型医学影像迁移验证，例如 chest X-ray 或 MRI 的 acquisition perturbation toy study，项目对医学 AI 的相关性会进一步增强。但暑假阶段不建议为了这个额外验证牺牲 XRD 主线。

## 7. 硬约束与质量控制

不可妥协的规则：

- 不可臆造扰动数值范围；每个数值都要进入 evidence ledger。
- split unit 必须是 underlying structure/material identity，不是单个 pattern。
- raw data、source PDFs、labels、历史实验输出不能覆盖。
- clean IID performance 与 measurement reliability 必须分开报告。
- Aug-only 与 Aug + Consistency 必须使用相同增强和分类监督，只让一致性项不同。
- real-XRD 是 closing-loop 目标，不是装饰性附录。
- unit-cell variation 和强 texture 不应默认视作 label-preserving。
- 不从单个 plot 或单个 random seed 得出科学结论。

每个 transform 至少需要：

- 参数定义。
- 单位。
- severity 范围。
- 物理解释。
- label-preserving 审查。
- zero-severity 行为。
- deterministic seed 行为。
- 可视化 overlay。
- evidence ledger 记录。

每个实验 run 至少需要记录：

- 代码版本或脚本版本。
- config。
- data split ID。
- seed。
- model checkpoint。
- metrics。
- environment 信息。
- 输出文件路径。

## 8. 当前资料结构

```text
E:\AI4science
├── 00_project_context
│   ├── extracted_light_pack
│   ├── extracted_full_archive
│   ├── manifests
│   ├── pdf_reading_extracts
│   ├── XRD_consistency_methodology_reserve_pool.md
│   ├── file_inventory.csv
│   ├── pdf_inventory.csv
│   └── pdf_reading_summary.csv
├── 01_literature
│   ├── core_xrd_crystal_ai
│   └── related_methods_and_tem
├── 02_code_repositories
│   ├── root_archives_extracted
│   └── github_archives_extracted
├── 03_tools_and_packages
│   ├── logs
│   └── pypi_packages
├── 90_retrieval_tmp
├── PROJECT_ORGANIZATION_REPORT.md
└── READING_SYNTHESIS_REPORT.md
```

关键文档：

- `00_project_context/extracted_light_pack/.../AGENTS.md`：项目执行规则。
- `00_project_context/extracted_light_pack/.../context/00_CURRENT_STATE.md`：当前权威状态。
- `00_project_context/extracted_light_pack/.../context/02_SIMXRD_XRD_RELIABILITY_SPEC.md`：任务和方法规格。
- `00_project_context/extracted_light_pack/.../context/03_EXPERIMENT_PROTOCOL.md`：实验和 ablation 规范。
- `00_project_context/extracted_light_pack/.../context/04_PHYSICAL_VALIDITY.md`：物理合法性与 label-preservation 审查。
- `00_project_context/extracted_light_pack/.../context/07_12_WEEK_ROADMAP.md`：12 周路线图。
- `00_project_context/XRD_consistency_methodology_reserve_pool.md`：算法升级储备池。

## 9. 资料与源码资产

核心论文与资料：

- SimXRD-4M：主模拟数据 / benchmark 参考。
- XQueryer：PXRD 智能晶体结构识别框架，面向实验 PXRD。
- AI-Driven Structure Refinement / PyWPEM：物理约束精修、峰形、背景、Bragg consistency 参考。
- Unified preprocessing framework：diffraction preprocessing 与 reproducibility 参考。
- PRDNet：倒易空间 / diffraction physics 与 crystal property prediction 方法参考。
- KBSS / Mean Teacher / FixMatch / VAT / UDA：consistency regularization 与 semi-supervised learning 方法参考。

源码与工具：

- `SimXRD-main`：主 benchmark / 数据读取 / simulation 参考。实际大数据未完整包含，当前目录中主要有 demo/test db。
- `XQueryer-main`：包含大量匹配/检索数据、demo databases、训练/推理脚本、RRUFF-MP matching，可作为 real-XRD connection 参考。
- `PyWPEM-main` / PyXplore：XRD simulation、whole-pattern decomposition、Bragg EM optimization、background、refinement 等物理参考。
- `PRDNet-main`：diffraction-informed representation 参考，不作为当前 1D XRD reliability MVP 主模型。
- `XRDMatch-main`：基于 SemiLearn 的 XRD 半监督脚本，可作为 consistency / SSL baseline 参考，但不能直接作为主线工程。

临时检索材料：

- `90_retrieval_tmp/tmp` 包含网络检索中间文件、HTML、JSON、cookies、临时脚本和 PDF 副本。
- 这些材料可用于追溯检索过程，但不应作为实验输入。

## 10. 风险与应对

| 风险 | 后果 | 应对 |
| --- | --- | --- |
| 数据 schema 未审清就训练 | label 或 split 错误，结果不可用 | 先做 data audit 和 data card |
| 按 pattern split 而不是 structure split | 泄漏，鲁棒性结果虚高 | 建 structure-level split manifest |
| 扰动范围无证据 | 物理叙事站不住 | 建 evidence ledger，未确认值标记为 unverified |
| 七个算法模块同时推进 | 主线被拖垮 | 暑假只做主线，最多加 perturbation-aware weighting |
| 同伴过早接触方法创新层 | 学习成本过高，责任边界模糊 | 让他先负责 augmentation 执行层 |
| 只报告 clean accuracy | 项目变成普通分类任务 | 分开报告 clean IID 与 perturbation reliability |
| real-XRD 只做口头展望 | 外部验证不足 | 至少写 real-XRD data card 或记录访问 blocker |

## 11. 近期可交付物

7 月可交付：

- `data_card.md`。
- data audit 脚本和字段报告。
- structure-level split manifest。
- clean baseline 训练脚本。
- transform interface 草案。
- identity / zero-severity plotting smoke test。
- 初版 metrics table schema。

8 月可交付：

- 四类 augmentation transform。
- severity sweep 配置。
- overlay gallery。
- transform smoke tests。
- Aug-only 实验结果。
- Clean / Aug-only / Aug + Consistency 主线对照。
- 失败样本和扰动敏感性分析。

若主线顺利，可追加：

- Measurement-disparity decorrelation。
- 与 Aug + Consistency 的 ablation 对比。
- 方法论小节草稿。

## 12. 最终输出形态

项目完成后应形成三类输出：

研究输出：

- 一个完整的 XRD measurement reliability benchmark。
- 一套 Clean / Aug-only / Aug + Consistency ablation。
- 一套扰动严重度与模型不稳定性的分析图。
- 一个可选的 measurement-disparity decorrelation 改进模块。

工程输出：

- 可复现实验代码。
- transform 测试。
- run manifests。
- metrics tables。
- plots from saved results。
- data card 和 evidence ledger。

申请材料输出：

- 项目摘要。
- 研究问题陈述。
- 方法图。
- ablation 表。
- robustness / calibration 图。
- 医学 AI 迁移叙事段落。

## 13. 下一步

最小安全下一步：

1. 读取 `AGENTS.md` 与核心 context 文档，确认项目规则。
2. 写 SimXRD data audit 脚本，只读字段、shape、label distribution、source IDs。
3. 生成 data card 初稿。
4. 建 structure-level split manifest 草案。
5. 实现 identity transform 和 clean / perturbed overlay smoke test。
6. 确认这些基础可信后，再进入 clean baseline 训练。

当前最重要的一句话：

> 不要急着堆算法。先把“物理扰动下模型是否可靠”这个问题证明清楚，再做一个最贴合 XRD 物理结构的 consistency 升级。
