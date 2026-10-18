# CrystalShift.jl 技术可行性审计（W0）

**审计日期：** 2026-10-18
**核查版本：** `MingChiangChang/CrystalShift.jl` `main` at `d95bb2561a504258639fa18e0d25a06684c7c0d5`
**方式：** 检查 GitHub README、`Project.toml`、MIT LICENSE、CIF 转换器、`optimize.jl`、tree search 与概率计算源码；本机未找到 Julia 可执行文件，因此没有安装、运行或基准测试 CrystalShift。

## 做什么

CrystalShift 是无训练的 XRD 相标注与 pseudo-refinement 程序，不是模拟训练的神经网络。使用者先从 CIF 候选生成反射峰输入，再把观测谱与候选送入晶格参数优化。公开实现还提供候选相组合的 best-first tree search、背景/wildcard 模型以及根据近似边际似然计算组合概率；可选模式会给晶格参数不确定度，另有受先验约束的强峰高度调整。README 明示相组合概率的归一化常数需要按论文程序确定，故不能将任意默认配置的概率直接视为已校准结果。

入口和实现证据：

- [README：输入生成、优化、树搜索和概率](https://github.com/MingChiangChang/CrystalShift.jl/blob/d95bb2561a504258639fa18e0d25a06684c7c0d5/README.md)
- [CIF 到反射表的 Python 预处理](https://github.com/MingChiangChang/CrystalShift.jl/blob/d95bb2561a504258639fa18e0d25a06684c7c0d5/src/cif_to_input_file.py)
- [晶格/pseudo-refinement 优化实现](https://github.com/MingChiangChang/CrystalShift.jl/blob/d95bb2561a504258639fa18e0d25a06684c7c0d5/src/shift/optimize.jl)
- [候选相组合 tree search](https://github.com/MingChiangChang/CrystalShift.jl/blob/d95bb2561a504258639fa18e0d25a06684c7c0d5/src/tree/search.jl)
- [近似边际似然与组合概率](https://github.com/MingChiangChang/CrystalShift.jl/blob/d95bb2561a504258639fa18e0d25a06684c7c0d5/src/tree/probabilistic.jl)
- [软件仓库与 MIT license](https://github.com/MingChiangChang/CrystalShift.jl)
- [方法论文，npj Computational Materials (2025)](https://www.nature.com/articles/s41524-025-01627-0)

论文和实现显示它已覆盖“给定候选结构后，用对称性约束的晶格拟合与物理谱比较进行相标注/组合搜索”这条方法路线。论文同时限定其并非完整 Rietveld 结构因子模型：峰强没有按完整晶体结构因子一起精修；高度织构和对细弱峰敏感的区分仍有局限。它是本项目后续候选相选择与参数初值评估应考虑的先行软件/比较基线，不应把“首次提出物理相搜索、晶格精修或 forward-XRD”当作项目新颖性。

## 与本项目的接口匹配

| 项目 | CrystalShift | 本 W0 / 拟议工作 | 判断 |
|---|---|---|---|
| 输入结构 | CIF 文件夹经 Python（pymatgen + xrayutilities）转成峰表 CSV；Julia 端读取候选相 | family registry 中逐个 CIF，并调用仓库现有 pymatgen peak table / profile renderer | 数据对象不同，需做显式坐标、波长和归一化适配；不能直接假定输出可互换 |
| 目标 | 无训练的单相/多相相标注、候选组合搜索和晶格 pseudo-refinement | 研究问题是模拟训练 AI 是否能改善候选结构排序和参数初值，并在可靠性约束下提高后续 XRD 精修效率 | 互补：CrystalShift 可做强物理搜索/精修比较基线；它不能回答“模拟训练 AI 是否提供增益” |
| 参数 | 对称性约束的晶格参数；可选背景、wildcard、峰强修正及优化模式 | W0 只拟合 Pm-3m `a` 或 P4mm `a,c` 加一个全局 2theta 零点；原子坐标、峰宽和背景固定 | W0 数值拟合是很窄的工程 smoke，不复现 CrystalShift 的相组合搜索、噪声先验或概率方法 |
| 部署/复现 | Julia 1.10+；额外 Python 结构/衍射依赖；公开仓库 MIT | 当前工程为 Python，复用 `xrd_robustness` 的共享模拟渲染器 | 当前工作站缺少 Julia，不能声称已完成集成或运行对照 |
| 概率/可信度 | Bayesian/Laplace 近似模型比较；论文讨论以模拟谱校准概率 | 本 W0 的 normalized RMSE 和有界拟合均不输出概率、误差条或经过校准的不确定度 | 正式比较应匹配数据、候选集、预处理与预算，并单独验证校准/覆盖率 |

## 决策

1. W0 先用现有仓库物理 forward 实现两个候选的有限参数拟合，以满足“两个候选都确实经过 forward、谱比较和参数优化”的工程验收。这里没有实现树搜索、相组合模型或概率估计，也没有复制 CrystalShift 代码。
2. 正式研究问题表述为：**模拟训练 AI 能否在已知材料家族内，提供比物理模板/数值基线更有用的候选结构和精修参数初值，同时保留可验证的可靠性并减少后续精修时间或失败率？** Forward model 是 AI 建议与实验 XRD/传统数值精修之间的物理接口和验证环节，不作为“新物理反演框架”的独立新颖性主张。
3. 学长确认家族和实际候选后，将 CrystalShift 列为 time-boxed feasibility / comparator 选项：先核对 CIF 候选、实验波长与 q/2theta 区间、输入处理、Julia 环境、授权和数据可用性；若能一致运行，再用相同谱、相同候选和可比计算预算报告拟合/候选结果与时间。若环境或模型假设不匹配，记录原因并用合适的传统精修器作为比较，不把 CrystalShift 变成硬依赖。
4. 不把 CrystalShift 的相组合概率当作 wt%/vol%，也不把 W0 的 profile-intensity 混合压力样例当成其验证。

**状态：** 静态代码与论文审计完成；软件可运行性和本项目适配性能未验证。此次未从 CrystalShift 复制代码或依赖。
