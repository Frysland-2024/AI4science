# W0 交接记录

**日期：** 2026-10-18
**状态：** 通用工程接口、BaTiO₃ 两候选 forward/有限参数拟合 smoke 与 CrystalShift.jl 静态技术审计完成；正式 12 周研究仍为 `PROPOSED / NOT_STARTED`，没有模型训练或真实谱结论。

## 验收范围与结果

W0 不止输出 Top-K 排序。两个有同行评审结构表来源的候选都经过结构校验、PXRD forward 重构、同一观测谱比较和有限参数优化：

- P4mm 拟合 `a`, `c` 与全局零点；normalized RMSE 从 **0.286485** 降到 **0.109186**。
- Pm-3m 拟合 `a` 与全局零点；normalized RMSE 从 **0.677231** 降到 **0.652587**。
- 拟合曲线、逐点残差、参数值/边界、optimizer 状态和前后目标值已写入主报告与 manifest。这里的拟合目标与 Top-K 模板 ranking score 不同，不能把二者混为一个概率或精修质量指标。

以上是同一条合成 P4mm observation 上的确定性有界数值 smoke，既不证明相识别/参数恢复准确，也不证明真实粉末谱可辨识或精修时间缩短。范围仅为结构晶格指标（P4mm `a,c`；Pm-3m `a`）与一个全谱零点；原子分数坐标、峰宽和背景固定。晶胞 ±0.5% 和零点 ±0.05° 是工程搜索盒，不是有证据的物理先验；没有参数区间、可辨识性、覆盖率或实验验证。

## 已完成的工程内容

- 对 ResNet、模拟/测量扰动、概率校准、`xrd_inversion` 数值 forward 与数据近重复风险形成复用矩阵，见 [CODE_AUDIT.md](CODE_AUDIT.md)；模块接口见 [ARCHITECTURE.md](ARCHITECTURE.md)。
- 建立 metadata-first family registry、空家族模板、未知/未配置/成分不匹配路由、观测输入与预精修输出 JSON Schema、Top-K normalized-RMSE baseline、有限参数 fitter 和共享模拟 adapter。
- 提供 BaTiO₃ Pm-3m / P4mm 两个文献候选模板。来源为 Nakatani 等人 2016 年单晶结构论文表格；官方 supplementary CIF 地址记入配置，但此次通过 DOI 的直接读取返回 HTTP 403，因此仓库结构仍是人工表格转录件，不应称为官方 CIF。原文报告该样品 298 K 为 P4mm、413 K 为 Pm-3m，转变约 413 K。
- 由参考单晶晶胞生成理想化随机粉末谱。Cu Kα1 (1.5406 Å)、10–80°、0.02° 步长与零点/展宽/背景/噪声值均为工程模拟设定，不是论文实验条件、仪器测量或已验证先验。
- 模板 Top-K 的 tetragonal observation 为 Top-1：P4mm normalized-RMSE ranking score = **0.580935**，Pm-3m = **0.844145**。这是依赖当前谱预处理、模拟设置和随机种子的未校准距离，非概率、accuracy 或真实外部性能。
- 另输出任意 50/50 profile-intensity 合成压力样例，报告要求复核；该接口烟雾测试没有实现混相 detector，合成权重不是质量/体积分数。
- CrystalShift.jl 已按公开仓库固定版本进行静态源码、依赖、license 和论文审计，结果见 [CRYSTALSHIFT_AUDIT.md](CRYSTALSHIFT_AUDIT.md)。该方法已实现 training-free 候选相组合搜索和晶格 pseudo-refinement；本项目不主张新发明物理相搜索。当前工作站没有 Julia，未安装或运行 CrystalShift；是否把它作为正式 benchmark，待材料候选/谱输入/仪器和运行环境兼容性审查。

## 实际验证与产物

在 `.venvs\xrd_test` 环境安装 `xrd_pre_refinement[test]` 后执行：

```powershell
.\.venvs\xrd_test\Scripts\python.exe -m pytest -q xrd_pre_refinement\tests
.\.venvs\xrd_test\Scripts\python.exe xrd_pre_refinement\scripts\run_batio3_pilot.py
```

最新测试：**13 passed，2 个 spglib deprecation warnings**。两候选均有专门的 bounded forward-fit 测试；输出结构及 schema 测试通过。registry index、两份 family config、两份 JSON report、observation schema/parser、参数边界和拟合前后残差均有校验。模拟网格 3,501 点；manifest 记录配置、代码和 CIF 哈希、环境、种子与模拟边界。初轮 W0 有两个已修复的测试夹具问题（profile 长度为 1、哈希字符串大小写比较），最终测试通过；本轮 fitter 首次调试也修复了 pymatgen 无 `Structure.modify_lattice` 的 API 假设，现改用保持分数坐标的重建路径并已测试。

输出目录：[pilot_run/](pilot_run/)

- `pre_refinement_report.json`：模板 Top-K、每候选初始模板 forward check，以及两个候选的有限参数 forward fit / 重构曲线 / 残差；概率和参数区间为空，`REVIEW_REQUIRED`。
- `synthetic_mix_stress_report.json`：合成 profile-intensity mix 报告。
- `simulated_example.csv`：3,501 行双列模拟 observation。
- `run_manifest.json`：结构/代码哈希、运行环境、参数范围、拟合分数和模拟限定。
- `batio3_template_comparison.png`：observation、未拟合模板与两个有界拟合曲线。
- `test_log.txt`、`demo_run_log.txt`：本轮最后执行的测试和 pilot stdout。

## 方法定位与后续边界

Forward model 是模拟训练 AI 给出的候选/参数初值与真实 XRD、传统数值精修之间的物理接口和可检查环节，不是独立的“新物理反演框架”新颖性主张。正式问题应问：在已知家族和同一评估预算下，模拟训练 AI 能否比物理模板及适用的数值方法给出更有用的候选结构/参数初值，同时保持可审计的可靠性并减少精修时间或失败率？计划沿用 [12 周候选方案](../../docs/FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md) 的冻结/验证边界。

## 尚未具备的输入与能力

- 学长尚未确认真实材料家族、名义成分、候选相、仪器元数据、参考精修与谱量；BaTiO₃ 只是工程 fixture。正式继续时，先获取家族和成分，再核验 2–4 个真实候选相 CIF、条件与 split。
- 没有模拟训练模型、候选概率校准、参数回归器、区间估计、合格拒判阈值、定量 Rietveld 精修、自动混相检测或相分数估计。
- 没有跨成分/相边界泛化、独立 renderer 对照、实验峰形/织构/缺陷建模或精修收敛收益证据。当前结构及两份模拟粉末谱不能代表学长的真实样品。
- CrystalShift 目前只完成静态审计；未来若纳入基线，需核对同候选、波长/角度轴转换、标准化、候选域、版本、依赖及相同预算。它的组合模型概率不等于 wt%/vol%。

## 学长回复后的第一步

先取得**材料家族和名义成分清单**，再为 2–4 个实际候选相建立候选表：候选/物相 ID、组成窗口、reference CIF 及来源、空间群、温度/压力/测量条件、结构/参数范围。用样品组成和仪器元数据核验这张表，再拟定母结构/原型隔离 split。通过这些检查前，不启动大规模模拟库或训练；若 CrystalShift 的依赖和输入匹配，则把它加入限时适配试验和公平物理基线。
