# Issue #19 nuisance diagnostic 摘要（2026-10-18）

在固定的 77 个测试 q、两个合成测量条件和三个配对 seed 上，A/B 各自的 q 预测保持冻结；随后用同一套零初始化、受界 L-BFGS-B eta profile solver 对两者做相同预算的事后谱拟合。equal-budget observed expected-profile RMSE：simple 为 A `0.009456 ± 0.000016`、B `0.009415 ± 0.000491`，V9 为 A `0.016034 ± 0.000795`、B `0.015621 ± 0.000655`（三 seed 均值 ± sample SD）。配对的 B−A 差分别为 `−0.000041 ± 0.000477` 和 `−0.000413 ± 0.001268`，每个条件的逐 seed 方向不一致，因此不构成稳定优势证据。

此前“B 原生 eta 残差高于 A profile-fit 残差”的比较确有推理路径不对等。固定 B 的 q 后，其 native eta residual 在 simple/V9 为 `0.015885 ± 0.001492` / `0.027332 ± 0.001431`；同一 q 做 shared eta fit 后降低 `0.006470 ± 0.001435` / `0.011711 ± 0.001283`。V9 B native zero-shift RMSE 为 `0.032117 ± 0.004448°`，均值偏差 `+0.005290 ± 0.007080°`，仍显示 nuisance head 的偏差问题。全量 924 次 shared fit 中 923 次成功；唯一非收敛为 V9/B/seed 20261046、全局测试 index 435，仍保留在汇总中。

这是同一 BaTiO₃ 模板上的 post-hoc、合成数据诊断；profile solver 是额外的测试时优化器，不是 B 学到的 eta head。结果不证明 nuisance loss 对冻结 q 网络权重有因果效果，不支持真实实验谱、未见结构或 Rietveld 结论。详见 [技术报告](../../TECHNICAL_REPORT.md)、[metrics.json](metrics.json) 和 [run_manifest.json](run_manifest.json)。
