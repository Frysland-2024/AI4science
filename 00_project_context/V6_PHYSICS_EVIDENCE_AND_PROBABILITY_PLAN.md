# V6 物理证据与扰动概率方案

## 1. 总原则

7 篇核心文献已经足够第一版证据链。理论公式决定变化方式，文献决定合理数量级，代码核验决定具体生成方式，V6 映射决定能否进入训练。不能把工程候选值写成已经被实验完全验证的物理真值。

核心文献：Szymanski 2021、SimXRD-4M、XQueryer、Salgado 2023、CPICANN、Lee 2023、Schopmans 2023。只有在某个参数仍然 `blocked` 时才继续补文献。

## 2. 证据等级

每条证据分别评估机制可信度和数值可迁移性：

| 等级 | 含义 |
|---|---|
| A | 粉末 PXRD、单位和公式明确，正文/补充材料/代码可核验 |
| B | 粉末 PXRD，但任务、仪器、归一化或实现方式不同 |
| C | 薄膜、不同任务，或只能支持扰动机制 |
| D | 内部系数、数组索引或归一化不明，不能定义物理参数 |

## 3. V6 参数映射边界

| V6 字段 | 合法含义 | 当前状态 |
|---|---|---|
| `delta_2theta_deg` | 整体仪器零点/样品高度造成的全谱偏移 | 保守 candidate |
| `effective_fwhm_deg` | 固定标量峰宽的工程代理，不等于 Scherrer 或 Caglioti | 保守 candidate |
| `noise_std_ratio` | 明确定义归一化顺序后的噪声尺度 | 保守 candidate |
| `background_to_peak_ratio` | `background_amplitude / clean_signal_peak` | 保守 candidate |

必须区分：整体零点偏移、晶格变化和应变峰移；固定 FWHM、晶粒尺寸展宽和 Caglioti 仪器展宽；背景幅度比例和信号/背景混合比例。`0.08--0.20` 度、`0--0.02` 噪声、`0--0.02` 背景目前是候选工程范围，不是无条件物理真值。

Schopmans 的 20--100 nm 晶粒尺寸、Scherrer 展宽、Caglioti 参数、伪 Voigt 和标准化谱加性噪声应作为 V6.1 对齐的优先依据。V6.1 至少要接入角度相关展宽或明确记录固定 FWHM 仍是代理。

原始证据表至少记录：来源、参数、物理机制、原始数值和单位、采样分布、归一化定义、公式、任务、粉末/薄膜、训练/测试用途、正文/补充材料/代码位置、证据等级、V6 映射和备注。

## 4. 启用概率的定义

`apply_probability` 是训练数据生成策略超参数，不是仪器现象真实发生概率。四种扰动必须分别拥有并记录概率和 active flag，不能暗中共享一个概率：

```json
{
  "zero_shift": {"apply_probability": 0.5},
  "broadening": {"apply_probability": 0.5},
  "background": {"apply_probability": 0.5},
  "noise": {"apply_probability": 0.5}
}
```

关闭定义固定为：零点偏移为 `0`，展宽回到基线 `0.08` 度，背景比例为 `0`，噪声标准差为 `0`。每条谱记录 `zero_shift_active`、`broadening_active`、`background_active`、`noise_active` 和 `active_perturbation_count`。

四个概率都取 `0.5` 时，独立采样下平均启用 2 个扰动，至少启用一种的概率为 93.75%，完全无额外扰动的概率为 6.25%，因此不能未经敏感性实验直接冻结为正式规则。

## 5. 概率敏感性实验

固定 `dev_3500`、Dynamic ERM、backbone、优化器、训练步数、数据划分和随机种子协议。先做单扰动实验，每次只开启一种扰动，测试 `p ∈ {0, 0.25, 0.50, 0.75}`；`p=1` 只作为压力条件。再比较三类联合方案：四个 `0.5`、各自单因子候选最优值、保守联合值。

选择指标至少包括 clean Macro-F1、in-range Macro-F1、开发集鲁棒性 AUC、最差严重度、clean 到扰动性能下降和训练稳定性。概率选择不能使用最终 test 或 real-XRD 数据；选定后四种正式方法必须共同冻结。

实验输出：

```text
configs/simulation.v6.probability_search.json
configs/simulation.v6.candidate_probability_selected.json
reports/perturbation_probability_single_factor.csv
reports/perturbation_probability_joint_search.csv
reports/perturbation_activation_statistics.json
docs/perturbation_probability_selection_report.md
```

## 6. 当前结论与下一步

- 对称峰移 OOD 已完成，旧的负向 `-0.28` 是窗口质量门槛残留，不是物理方向性证据。
- 物理参数证据链和代码映射已足够支持第一版开发，但固定 FWHM、噪声归一化和背景算子仍需 V6.1 对齐。
- 14,000 和 3,500 数据层已经具备；概率敏感性尚未运行，不能生成 selected 配置。
- 当前决定：V7 样本效率模块暂停；先用 `configs/simulation.v6.formal.json` 的同一哈希和同一概率配置完成四种 V6 方法的公平验证。对应锁定记录为 `reports/v6_method_verification_parameter_lock.json`。
- 下一步顺序：先完成四种方法的 GPU 开发验证，再单独进行 V6.1 算子对齐、单扰动概率敏感性和联合策略敏感性；在此之前不修改四方法比较所用参数。
