# 现有模块审计与复用结论（W0）

**范围：** 只读审计 `xrd_robustness/`、`xrd_inversion/` 当前代码/文档，并静态审计公开 CrystalShift.jl 源码；未运行旧训练、未访问独立 renderer holdout，未改冻结配置/结果。结论针对 W0 预精修需求，不代表已证明其科学有效性。

| 模块 | 现有能力 | 可复用部分 | 必须改造部分 | 风险 |
|---|---|---|---|---|
| ResNet-18-GN | 单通道 PXRD 七晶系分类，flatten + dense head 输出 7 类 logits；ERM/JS 训练目标 | 可参考一维卷积骨干、输入张量和规范化工程 | 相候选分类器需重训并换类目头；连续晶格/仪器参数回归、条件不确定度和拒判头均需新实现；旧 V9 权重/softmax 不得迁移为铁电相概率 | 七晶系标签与候选相不等价，旧权重概率未对新域校准 |
| 在线模拟与视图生成 | `ideal_peak_table` 从结构算 Bragg 峰；高斯峰形、采样视图、种子/配置 provenance；train 动态、validation/test 固定 | 可直接调用底层 `ideal_peak_table`、`simulate_from_peak_table` 作为工程 forward/测量算子；可借 deterministic seed / metadata 习惯 | 新材料候选、温度/成分有效域、仪器响应、结构参数化、陶瓷 microstructure 和独立 renderer 需逐项验证；不能把旧扰动幅度当作新体系范围 | 理想单相峰表 + Gaussian 轮廓不覆盖所有仪器/织构/缺陷效应 |
| 五类测量扰动 | 全谱零点偏移、Gaussian FWHM、March–Dollase 织构、flat/polynomial/GP 背景、Gaussian/Poisson 噪声 | 可借用算子实现及确定性实现；本 W0 小样本使用受限零点、展宽、背景、噪声 | 真实幅度、相关性、Kα 线型、陶瓷纹理和监督标签范围须按实际仪器/材料重定；不能把受预测的参数当成任意 nuisance | `PhysicsParameters` 默认范围服务于 V9，不等同新课题的测量先验 |
| 概率校准 | 分类 top-label ECE；现有脚本审计 ECE/NLL/Brier/entropy | 未来单相候选概率可复用分类 ECE/NLL/Brier 思路与可靠性图 | 新相模型需 validation-only 温度缩放及覆盖域定义；连续参数区间覆盖/宽度需新方法；W0 仅保留显式 NOT_FITTED | ECE 是一组预测统计量，不是单谱置信度、参数误差条或校准器 |
| `xrd_inversion` forward / numerical gates | pymatgen/结构峰表的四方已知单相数值 forward、float64 parity、Jacobian/recoverability 门；Week-1 P2-R 288/288 通过，P2-L 为诊断未全过 | 仅作为独立数值验证参考和函数行为参考；W0 调用 robustness 的现有谱渲染入口，不复制反演结论 | 多候选相、铁电结构、两个相叠加、实际仪器与新参数范围均需新验证；旧 Stage-1 factorization NO-GO 不恢复 | formal ML 仍有匿名原型跨 split 重叠警示；不得用 Week-1 结果证明新体系/网络已成立 |
| Data split / 近重复风险 | exact CIF fingerprint、材料 ID/母结构分组 split 与泄漏检查 | 可复用 identity/provenance-first 的流程和 exact fingerprint 基线 | 需添加对称等价/变胞/超胞/同原型/微扰结构及谱近重复审计；按结构原型、成分/晶格状态和测量批次明确独立单位 | 精确 fingerprint 不会发现等价晶胞或近似原型；两 CIF pilot 不能作为泛化数据量 |

## 代码证据入口

- `xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`: `ML4PXRDResNet1D`, `ML4PXRDResNet1DConfig`。
- `xrd_robustness/src/xrd_robustness/simulator.py`: `ideal_peak_table`, `render_gaussian_peaks`, `simulate_from_peak_table`, `simulate_structure`。
- `xrd_robustness/src/xrd_robustness/physics.py`: `PhysicsParameters`；`measurement_models.py`: `generate_background_profile`, `apply_noise_model`。
- `xrd_robustness/src/xrd_robustness/evaluation/metrics.py`: `expected_calibration_error`; `scripts/analyze_calibration.py`: frozen-classification calibration audit。
- `xrd_robustness/src/xrd_robustness/structure_data.py`, `structure_split.py`: exact fingerprint and parent split interfaces.
- `xrd_inversion/src/xrd_inversion/gpu_forward.py`, `xrd_inversion/reports/WEEK1_FORMAL_REPORT.md`: existing numerical infrastructure and scope limits.
- `reports/CRYSTALSHIFT_AUDIT.md`: CrystalShift.jl static source/license/paper audit, feasibility matrix, and baseline decision.

**结论：** 可复用的只有经过明确输入限制的 pymatgen PXRD peak calculation / Gaussian measurement operators。W0 另新增两个参考候选上的有界数值 forward fit smoke，但没有新网络训练、概率校准、连续参数学习、不确定度或实验参数反演证据。CrystalShift 已具备更完整的训练无关相搜索/晶格 pseudo-refinement 路线；它应作为正式研究候选 baseline 接受兼容性评估，不作为本项目原创算法声称。未在当前工作站运行 CrystalShift，因为没有 Julia 可执行文件。
