# 项目文档

这个目录放项目当前状态、下一阶段规划、对外讲法和完整历史档案。

| 文件 | 用途 |
|---|---|
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | 当前科学设计、做完的事、实验进度、卡点和下一步 |
| [`PXRD_RESULT_REPORTING_STANDARD.md`](PXRD_RESULT_REPORTING_STANDARD.md) | 当前有效的三层评价体系：performance 主结果、reliability 增强证据、strict statistical audit |
| [`master_route_framework.md`](master_route_framework.md) | 研究生方向与职业筛选的三棵技术树：测量到推断、AI辅助物理建模、EE/IC设计 |
| [`research_direction_map.md`](research_direction_map.md) | AI＋表征、科学量测和半导体检测等方向地图 |
| [`japan_advisor_search_keywords.md`](japan_advisor_search_keywords.md) | 日本导师检索的方向关键词与检索组合 |
| [`APPLICATION_RESEARCH_NARRATIVE.md`](APPLICATION_RESEARCH_NARRATIVE.md) | 申请材料、面试和项目介绍的统一说法 |
| [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md) | 下一代项目的正式执行计划：已知相参考条件下的 PXRD 定量参数反演、同源结构一致性、前向物理验证和 refinement 初始化 |
| [`XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md`](XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md) | 定量反演项目的论文、代码、数据和补充材料资源清单 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md`](PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md) | 2026-08-27 思路节点：从分类中的晶格物理约束构想，收敛为独立的已知相定量反演项目 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md`](PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md) | 2026-08-27 认知修正节点：CNRS-318 重新定级为正式第二实验域（balanced-equivalent=NO / naturally-imbalanced=YES），记录旧 Gate、问题重构、RRUFF few-shot 与 CNRS zero-shot 分工 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_REPORTING_STANDARD_RESET.md`](PROJECT_HISTORY_NOTE_2026-08-27_REPORTING_STANDARD_RESET.md) | 评价层级从 confirmatory Gate 纠正为 community-standard reporting + strict audit 的历史原因 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_REAL_DOMAIN_HEADLINE_METRICS.md`](PROJECT_HISTORY_NOTE_2026-08-27_REAL_DOMAIN_HEADLINE_METRICS.md) | RRUFF few-shot 与 CNRS zero-shot 的 headline 指标和域分工决策记录 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_CALIBRATION_RELIABILITY_UPGRADE.md`](PROJECT_HISTORY_NOTE_2026-08-27_CALIBRATION_RELIABILITY_UPGRADE.md) | 2026-08-27 概率可靠性分析从 ECE 观察扩展到 NLL、Brier 与跨域一致性的历史节点 |
| [`PROJECT_HISTORY_NOTE_2026-08-24_INVERSE_PROBLEM_DIFFICULTY.md`](PROJECT_HISTORY_NOTE_2026-08-24_INVERSE_PROBLEM_DIFFICULTY.md) | 2026-08-24 方向认知节点：区分高维不完备重建与强先验、有限解空间的识别/参数反演，并记录其对未来 AI+科学量测方向选择的影响 |
| [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md) | 完整研究演化档案：保留失败、版本变化、思路转向与历史决策；用于追溯项目如何发展，不代表当前方法或论文主张 |
| [`../xrd_robustness/MANUSCRIPT.md`](../xrd_robustness/MANUSCRIPT.md) | 当前 JS 分类项目的论文正文框架 |
| [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md) | 当前 JS 分类项目的跨域主结果与证据层级汇总 |
| [`../xrd_robustness/reports/rruff301_fewshot_results.json`](../xrd_robustness/reports/rruff301_fewshot_results.json) | RRUFF-301 K=1/2/5 Macro-F1 与 Accuracy 的可跟踪汇总及 provenance 边界 |
| [`../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) | CNRS-318 数据集审计（git 可跟踪的权威摘要，含 v2 manifest SHA 与七类计数） |
| [`../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md) | CNRS-318 原样保留的 pre-run 冻结评测协议；完成状态与统计纠错另见结果报告/run record |
| [`../xrd_robustness/reports/CNRS_318_RESULTS.md`](../xrd_robustness/reports/CNRS_318_RESULTS.md) | CNRS-318 zero-shot 结果、完整性审计、修正后的 paired bootstrap 与限制 |
| [`../xrd_robustness/reports/README.md`](../xrd_robustness/reports/README.md) | 报告索引：区分当前权威结果、冻结协议、历史快照和本地大文件 |
| [`../xrd_robustness/configs/real.cnrs318.zero_shot.frozen.json`](../xrd_robustness/configs/real.cnrs318.zero_shot.frozen.json) | CNRS-318 冻结评测配置（zero-shot，含类序/类计数与 10 个 checkpoint 哈希） |
| [`../xrd_robustness/manifests/cnrs318_eval_manifest.csv`](../xrd_robustness/manifests/cnrs318_eval_manifest.csv) | CNRS-318 冻结评测清单（318 父样本；标签由结构派生、未人工物相核验） |
| [`../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv) | CNRS-318 轻量父样本 manifest（318 个独立父样本，不含原始谱） |

## 建议阅读顺序

1. 第一次阅读从 [`CURRENT_STATE.md`](CURRENT_STATE.md) 开始；
2. 想理解长期方向，再看 [`master_route_framework.md`](master_route_framework.md)；
3. 想了解下一代 XRD 项目，再看 [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md)；
4. 只有需要追溯某个决定、失败实验或思路变化时，再查 `PROJECT_HISTORY.md` 与日期化历史节点文档。

## 当前结论与未来规划的边界

对外的当前科学说法以 `CURRENT_STATE.md` 和结果文件为准。已经完成的项目是七晶系 PXRD 分类、在线物理扰动，以及 Dynamic ERM 和 Dynamic JS 的配对比较。

两个实验真实域角色互补：RRUFF-301（平衡、人工整理的实验真实域）主讲 K=1/2/5 few-shot adaptation 与 label efficiency；CNRS-318（自然不平衡、跨数据库的独立实验真实域）主讲 frozen-model zero-shot external evaluation，5/5 seed 的 Macro-F1 以及 pooled Macro-F1、balanced accuracy、accuracy 均 favor JS。CNRS 的宽 bootstrap CI 保留在第三层严格审计中，用于说明低支持类别带来的不确定性，而不再定义该域是否“成功”；它也不是 CNRS 域适配。

定量反演文档属于**下一项目规划**：它已经完成问题定义和执行路线设计，但尚未启动训练，不能被写成当前已完成成果，也不会反向修改已经冻结的 JS 分类实验。
