# 项目文档

这个目录放项目当前状态、下一阶段规划、对外讲法和完整历史档案。

| 文件 | 用途 |
|---|---|
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | 当前科学设计、做完的事、实验进度、卡点和下一步 |
| [`master_route_framework.md`](master_route_framework.md) | 研究生方向与职业筛选的三棵技术树：测量到推断、AI辅助物理建模、EE/IC设计 |
| [`research_direction_map.md`](research_direction_map.md) | AI＋表征、科学量测和半导体检测等方向地图 |
| [`APPLICATION_RESEARCH_NARRATIVE.md`](APPLICATION_RESEARCH_NARRATIVE.md) | 申请材料、面试和项目介绍的统一说法 |
| [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md) | 下一代项目的正式执行计划：已知相参考条件下的 PXRD 定量参数反演、同源结构一致性、前向物理验证和 refinement 初始化 |
| [`XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md`](XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md) | 定量反演项目的论文、代码、数据和补充材料资源清单 |
| [`PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md`](PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md) | 2026-08-27 思路节点：从分类中的晶格物理约束构想，收敛为独立的已知相定量反演项目 |
| [`PROJECT_HISTORY_NOTE_2026-08-24_INVERSE_PROBLEM_DIFFICULTY.md`](PROJECT_HISTORY_NOTE_2026-08-24_INVERSE_PROBLEM_DIFFICULTY.md) | 2026-08-24 方向认知节点：区分高维不完备重建与强先验、有限解空间的识别/参数反演，并记录其对未来 AI+科学量测方向选择的影响 |
| [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md) | 完整研究演化档案：保留失败、版本变化、思路转向与历史决策；用于追溯项目如何发展，不代表当前方法或论文主张 |
| [`../xrd_robustness/MANUSCRIPT.md`](../xrd_robustness/MANUSCRIPT.md) | 当前 JS 分类项目的论文正文框架 |
| [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md) | 当前 JS 分类项目的模拟结果汇总 |

## 建议阅读顺序

1. 第一次阅读从 [`CURRENT_STATE.md`](CURRENT_STATE.md) 开始；
2. 想理解长期方向，再看 [`master_route_framework.md`](master_route_framework.md)；
3. 想了解下一代 XRD 项目，再看 [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md)；
4. 只有需要追溯某个决定、失败实验或思路变化时，再查 `PROJECT_HISTORY.md` 与日期化历史节点文档。

## 当前结论与未来规划的边界

对外的当前科学说法以 `CURRENT_STATE.md` 和结果文件为准。已经完成的项目是七晶系 PXRD 分类、在线物理扰动，以及 Dynamic ERM 和 Dynamic JS 的配对比较。

定量反演文档属于**下一项目规划**：它已经完成问题定义和执行路线设计，但尚未启动训练，不能被写成当前已完成成果，也不会反向修改已经冻结的 JS 分类实验。
