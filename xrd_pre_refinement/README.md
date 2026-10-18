# XRD 智能预精修：W0 工程样例

本模块实现 metadata-first 材料家族路由、XRD observation 输入校验、JSON/Python 数据契约、单相模板排序、有限参数拟合和共享的 PXRD forward adapter。BaTiO₃ 部分是**模拟工程演示**，不是训练模型、校准预测器或科学结论；不修改冻结的 `xrd_robustness` 主线，也不重开已归档的 Stage-1 factorization。

## 运行

在仓库根目录、现有研究环境中：

```powershell
.\.venvs\xrd_test\Scripts\python.exe -m pytest -q xrd_pre_refinement\tests
.\.venvs\xrd_test\Scripts\python.exe xrd_pre_refinement\scripts\run_batio3_pilot.py
```

Demo 读取本目录 registry 与结构文件，调用 `xrd_robustness` 中的 pymatgen 峰表计算及 Gaussian measurement renderer。至少两个 BaTiO₃ 文献候选都会生成理论谱、与同一模拟 observation 比较，并通过 `scipy.optimize.least_squares` 做有界单相拟合；拟合参数是晶胞指标和全局 2theta 零点，固定原子分数坐标、峰宽和背景。脚本生成 JSON 预精修报告、模拟谱 CSV、运行 manifest、测试/运行日志和对比图，保存在 `reports/pilot_run/`。不训练神经网络。

新环境的依赖安装方式：

```powershell
python -m pip install -e ".\xrd_pre_refinement[science,figures,test]"
python -m pip install -e ".\xrd_robustness[science]"
```

## 输出边界

baseline 按 normalized RMSE 对候选排序。`single_phase_probability` 始终为 null，状态为 `NOT_CALIBRATED`。每个候选附带有限参数拟合的前后 normalized RMSE、参数值/搜索边界、forward 重构谱和残差；这些 ±0.5% 晶胞搜索范围及 ±0.05° 零点范围只是工程演示盒，不是验证先验、参数预测或区间。参数区间未估计。`coexistence_hypothesis.model_probability` 和 `phase_fraction` 分开定义且保持未估计。混相压力样例是任意系数叠加的 profile-intensity smoke test，不能解释成 wt%/vol%，也不能证明自动识别了混相。

未知/未配置家族、成分不匹配及所有未校准 demo 均要求人工复核。`family_id` 和名义成分由用户元数据提供；router 不从 XRD 推断化学家族。

## BaTiO₃ 来源说明

结构参考来自 Nakatani 等人 2016 年的单晶结构研究，原文报告该样品在 298 K 为 P4mm、413 K 为 Pm-3m，转变温度约 413 K。仓库 CIF 是按论文表格人工转录并补入完整空间群操作的文件，不是官方 supplementary CIF；官方补充文件 URL 记录在 family config 中，但此次没有取回原始文件。两份结构只用于生成理想化随机粉末模拟谱。波长、测量扰动和 profile-intensity mix 系数均是工程演示设定，不代表论文测量或真实实验仪器。

## 物理方法比较

[CrystalShift.jl 技术审计](reports/CRYSTALSHIFT_AUDIT.md)确认已有公开无训练的相组合搜索、对称性约束晶格 pseudo-refinement 和模型比较。W0 不复制它的树搜索/概率方法；其后若正式材料候选、数据处理与 Julia 运行环境匹配，可纳入同谱同预算基线。当前工作站没有 Julia，未完成安装或运行对照。该项目的问题是模拟训练 AI 能否给出更有用的候选结构和参数初值，并改善后续精修效率/可靠性；forward 是模型建议与实验谱、常规精修之间的物理接口，不主张发明新的物理相搜索框架。
