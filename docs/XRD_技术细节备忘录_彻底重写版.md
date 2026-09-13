# PXRD 七晶系鲁棒分类：技术细节备忘录（彻底重写版）

**用途：** 导师汇报、Methods 复现与物理追问。  
**日期：** 2026-09-13  
**范围：** 只记录已经完成并冻结的七晶系鲁棒分类实验；后续参数反演/因子解耦属于另一研究模块。

## 一页结论

研究问题：在完全相同的母结构、在线扰动分布、ResNet backbone、优化器和双视图数据暴露下，显式利用“同一母结构的两次测量属于同一个物理对象”这一关系，是否能比普通 Dynamic ERM 获得更好的 PXRD 扰动鲁棒性？

`same parent → measurement-equivalent views → CE + JS prediction consistency`

| 证据层 | Dynamic ERM | JS consistency | 差值 / 结论 |
|---|---:|---:|---|
| 模拟 Test · in-range Macro-F1 | 0.6953 | 0.7349 | +3.96 pp |
| 模拟 Test · 单因素 OOD Macro-F1 | 0.6507 ± 0.0072 | 0.7053 ± 0.0098 | +5.46 pp；5/5 seed 为正 |
| 模拟 Test · worst-class F1 | 0.5111 | 0.5586 | +4.75 pp |
| RRUFF-301 · 1-shot/class | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | +4.33 pp |
| RRUFF-301 · 2-shot/class | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | +4.60 pp |
| RRUFF-301 · 5-shot/class | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | +5.45 pp |
| CNRS-318 · zero-shot Macro-F1 | 0.1884 ± 0.0263 | 0.2071 ± 0.0213 | +1.87 pp；5/5 seed 为正 |

**核心结论：** 同母结构关系监督在本任务中提高模拟 OOD 鲁棒性，并改善 RRUFF 少样本适配与 CNRS 独立来源 zero-shot 的方向性表现；但它没有解决广义 Sim-to-Real，CNRS 绝对性能与校准仍然较差。

**证据边界：** 主分类代码使用 `pymatgen.XRDCalculator(wavelength="CuKa")`，不擅自改成硬编码数值；五类扰动是文献锚定、物理合理、冻结的模拟空间，不是某台真实仪器的经验误差分布；parent split 防止精确母结构泄漏，但不保证 family/prototype-disjoint。

## 1. 任务、数据与标签

- 输入：10°–80°，步长 0.02°，3,501 点一维 PXRD。
- 输出：七晶系概率，顺序为 triclinic / monoclinic / orthorhombic / tetragonal / trigonal / hexagonal / cubic。
- formal_14060：14,000 formal tier + 140 gate tier − 80 overlap = 14,060 独立晶体结构。
- 当前权威 split：9,842 / 2,109 / 2,109；70/15/15；seed=20260726；以 `structure_fingerprint` 为 parent identity；按 crystal system 分层。
- `family_fields_used_for_assignment=false`：不是 chemical-family/prototype-disjoint benchmark。

## 2. PXRD forward model

主链：

`Materials Project structure → pymatgen XRDCalculator → ideal reflection table → March–Dollase（可选）→ 全谱 2θ shift → Gaussian broadening → background → Poisson/readout noise → clip → max normalization`

### 2.1 理想峰表

- `XRDCalculator(wavelength="CuKa")`
- `two_theta_range=(10,80)`，`scaled=True`
- 保存 positions、relative intensities、hkl、multiplicity、reciprocal vectors 和 reflection→peak 映射。

### 2.2 Gaussian 渲染

`σ = FWHM / [2√(2 ln2)]`

`I(2θ) = Σ (A_i/σ) exp[-0.5((2θ−2θ_i)/σ)^2]`

- 每个峰截断到 ±5σ。
- `A_i/σ` 使不同 FWHM 下积分峰强近似稳定。
- level0 FWHM=0.08°，网格 0.02°，约 4 bin/FWHM。
- 这是标量有效峰宽，不是完整 Caglioti/Scherrer 仪器模型。

## 3. 五类测量扰动

| 扰动 | Train / in-range | Single-factor OOD | 含义 |
|---|---|---|---|
| 全谱峰位偏移 | Δ2θ~U(-0.2,0.2)°, p=0.5 | [-0.5,-0.2]° / [0.2,0.5]°, p=1 | 零点/样品高度/标定型偏移，不是应变 |
| 统一峰展宽 | FWHM~U(0.08,0.20)°, p=1 | U(0.20,0.35)° | 标量峰宽代理 |
| 择优取向 | March–Dollase r~U(0.8,1.0), p=0.7 | r~U(0.5,0.8), p=1 | 方向相关的系统峰强变化 |
| 平滑背景 | 3阶 polynomial，ratio 0–0.02，p=0.5 | GP，ratio 0.02–0.05 | 平滑非负背景 |
| 计数+读出噪声 | C~LogU(2500,40000)，σe 0–2 counts | C~LogU(100,2500)，σe 0–5 counts | Poisson counting + readout noise |

March–Dollase：

`P(α;r) = [r² cos²α + (1/r)(1−cos²α)]^(-3/2)`

背景训练路径以归一化角度轴为自变量；GP OOD 使用 33 anchors、平方指数 covariance、长度尺度 0.12（无量纲 normalized-axis scale）。

Poisson–Gaussian：

`E[counts_j]=I_j*C; counts_j~Poisson(E[counts_j]); I'_j=(counts_j+ε_j)/C`

`ε_j~Normal(0,σe²)`，最后 clip negative → max normalize。

主评估面板：level0、in-range、6 个 single-factor OOD、3 个 combined OOD、ood_all；论文主 OOD 指标是 6 个 single-factor 的等权平均。

## 4. 学习设计

同一个 parent：`x1=g(s,m1)`、`x2=g(s,m2)`。

`L_cls = 0.5[CE(f(x1),y)+CE(f(x2),y)]`

`JS(p1,p2)=0.5 KL(p1||m)+0.5 KL(p2||m)`，`m=0.5(p1+p2)`

`L_JS = L_cls + λ_JS JS(p1,p2)`，正式 `λ_JS=60`。

ERM 和 JS 看完全相同的两张 view；唯一差别是 JS 使用 same-parent relation。

### λ 选择

| 候选 | Validation in-range | Validation mean OOD |
|---|---:|---:|
| ERM | 0.7140 | 0.6665 |
| λ=3 | 0.7184 | 0.6761 |
| λ=30 | 0.7164 | 0.6762 |
| λ=60 | 0.7298 | 0.6997 |

λ 候选先经 Train-only 梯度尺度审计固定，再只用 Validation 选 60；Test/RRUFF/CNRS 未参与选参。

## 5. Backbone 与训练配置

- ML4pXRDs 风格 1D ResNet-18 PyTorch port，GroupNorm，约 13M 参数。
- Stem：Conv1d k=7,s=2, 64ch → GN/ReLU → MaxPool k=3,s=2。
- 4 stages：64/128/256/512ch，各 2 blocks，kernel=9，阶段 stride=1/4/4/4。
- Flatten 7168 → Linear 256 → Linear 7；无 dropout/GAP。
- 16 parents/step × 2 views = 32 patterns。
- AdamW，lr=1e-4，weight decay=1e-4，constant LR。
- 100 epoch max；每 10 epoch 验证；至少训练 50 epoch；连续 3 次验证无 >0.002 mean-OOD 改善则停止。

## 6. 模拟域正式结果

### Validation

| 指标 | ERM | JS | Δ |
|---|---:|---:|---:|
| level0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| in-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| mean single-factor OOD Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | +0.046569 |
| worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

### Frozen simulated Test

| 指标 | ERM | JS | Δ |
|---|---:|---:|---:|
| level0 Macro-F1 | 0.697280 | 0.737159 | +0.039880 |
| in-range Macro-F1 | 0.695267 | 0.734854 | +0.039587 |
| mean single-factor OOD Macro-F1 | 0.650737 ± 0.007208 | 0.705336 ± 0.009767 | +0.054600 ± 0.007271 |
| mean single-factor OOD Accuracy | 0.650782 ± 0.007804 | 0.705237 ± 0.008560 | +0.054454 ± 0.004149 |
| worst-class F1 | 0.511064 | 0.558558 | +0.047495 |

主 OOD paired-bootstrap 95% CI = `[+0.048944,+0.060255]`，5/5 matched training seeds 为正。

## 7. RRUFF-301 few-shot

- 301 条；七晶系各 43 条。
- 10/class adaptation pool（70）+ 33/class locked test（231）。
- K=1/2/5 → 7/14/35 support。
- 冻结卷积与 residual blocks，只更新 7168→256 embedding + 256→7 head；微调只用 CE。
- 5 pretraining seeds × 5 support seeds = 每档 25 组比较。

| K | ERM Macro-F1 | JS Macro-F1 | paired Δ |
|---:|---:|---:|---:|
| 1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | +0.0433 |
| 2 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | +0.0460 |
| 5 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | +0.0545 |

这是同域标签效率证据，不是 unseen-mineral benchmark。

## 8. CNRS-318 zero-shot

- 318 独立 structural parents；类别 21/87/77/41/33/12/47。
- 不参与 adaptation / λ / checkpoint selection。
- 原始谱按 Bragg relation 映射到 `λ_target=1.5406 Å`，线性插值到 10–80° / 0.02°，max-normalize；范围外用端点延拓。

Macro-F1：`0.188372±0.026336 → 0.207085±0.021336`，paired `+0.018713±0.006754`，5/5 seed 为正。

严格 class-stratified paired-parent bootstrap 95% CI：`[-0.009339,+0.046107]`。自然不平衡尤其 hexagonal n=12 使不确定性较大；绝对 accuracy=0.210 仍低于 majority-class baseline≈0.274。

## 9. 声明边界

可以说：
- matched JS improves aggregate simulated OOD robustness；
- same-parent provenance is used as measurement-equivalence supervision；
- RRUFF supports few-shot label efficiency；
- CNRS gives supporting independent-source zero-shot evidence。

不能说：
- JS/consistency/online simulation 是本项目首创；
- 扰动分布精确拟合某台仪器；
- family/prototype leakage 被完全排除；
- 已解决广义 Sim-to-Real。

## 10. 权威项目文件

- `xrd_robustness/configs/data.method_transfer.structure_split.json`
- `xrd_robustness/src/xrd_robustness/simulator.py`
- `xrd_robustness/src/xrd_robustness/measurement_models.py`
- `xrd_robustness/src/xrd_robustness/preferred_orientation.py`
- `xrd_robustness/configs/simulation.method_transfer.frozen.json`
- `xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`
- `xrd_robustness/configs/experiment.public.json`
- `xrd_robustness/reports/RESULTS.md`
- `xrd_robustness/MANUSCRIPT.md`
- `docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`
- `docs/PXRD_PERTURBATION_EVIDENCE.md`
- `docs/RRUFF真实域_科研叙事.md`
- `xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`

## 外部参考

1. Lee BD et al. *Advanced Intelligent Systems* 2023, 5, 2300140. DOI: 10.1002/aisy.202300140.
2. Schopmans H, Reiser P, Friederich P. *Digital Discovery* 2023, 2, 1414–1424. DOI: 10.1039/d3dd00071k.
3. Oviedo F et al. *npj Computational Materials* 2019, 5, 60. DOI: 10.1038/s41524-019-0196-x.

### 波长不要混用

- 主分类模拟器：`XRDCalculator(wavelength="CuKa")`。
- CNRS 统一化：`λ_target=1.5406 Å`。
- 后续 inversion 模块部分配置：`1.54184 Å`，属于另一个研究模块，不能回填到本分类实验。
