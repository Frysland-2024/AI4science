# Issue #19：测量一致的 PXRD Forward 闭环结果

**状态：** P0–P2 物理、梯度和未知 nuisance Gate 全部通过；P3 smoke 与预算内 A/B exploratory pilot 完成。结果保存在独立分支并通过 Draft PR 供评审，不自动合并。

## 结论

本次实现并验证了 `mu(q,eta)=M(F_crystal(q),eta)` 的可微 expected-profile 闭环。Gate 证明当前 BaTiO₃ 模板和限定 nuisance 范围下的全谱一致性、梯度正确性及局部可辨识性；它们不证明真实仪器或材料上的可辨识性。

A/B 结果混合：simple 条件两维 q MAE 为 A `0.013533 ± 0.000849`、B `0.013676 ± 0.001923`；V9 条件为 A `0.032235 ± 0.001255`、B `0.030554 ± 0.002580`。B 在 simple 略差、V9 略好；V9 B 的预测 nuisance 尤其 zero-shift 仍有较大失配，且 observed-profile RMSE 高于 A。当前证据不支持“reconstruction loss 普遍提高参数反演”的结论。

## Gate 与执行

- BaTiO₃ COD 9014273 / P4mm：Torch 与独立 Pymatgen/V9 的全谱 max abs `1.19×10⁻⁷`，7 个 q 探针全部通过。
- P1/P2：最差 V9 测量谱 parity `2.03×10⁻⁸`；autograd/有限差分最大相对误差 `2.21×10⁻⁴`；q+eta Jacobian condition `23.40`、最大列相关 `0.924`；non-oracle 恢复及 64 次噪声期望检查通过。23 项测试通过。
- P1 v1 曾因两个自由背景形状系数不可辨识而失败。依据 V9 冻结的 variation=0 配置固定形状后只估计幅度，Gate 阈值保持不变。
- Smoke：128 q、1 seed、4 epochs；loss 和 q/eta 梯度有限，eta_true 未进入训练路径。
- Formal：512 q，358/77/77 split、3 paired seeds、最多 24 epochs；simple λ=`0.1`、V9 λ=`1.0`，均只由 validation 选出。test 未参与选择。
- smoke、第一次失败尝试保守计入 630 秒、正式重跑与 λ 选择累计 `1386.05 s / 7200 s`。正式重跑的 checkpoint RNG 类型错误已修复；失败轮次完整保留。

**解释限制：** 单一已知 CIF 的合成 conditional interpolation；test 不是未看过的 confirmatory benchmark。A 的 q/a/c 指标直接来自网络预测，A 的观测谱残差则额外做了固定 q 的受界 eta profile fit；B 用网络预测 eta，因此两者 residual 计算成本不相同。完整数值、逐 seed 原值、运行记录和物理边界见 [技术报告](../xrd_forward_loss/measurement_closure/TECHNICAL_REPORT.md)。

机器结果和 provenance：[`gate_report.json`](../xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/gate_report.json)、[`ab_results.json`](../xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal/ab_results.json)、[`command_log.json`](../xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/command_log.json)、[`checkpoint_manifest.json`](../xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/checkpoint_manifest.json)。本工作不更改冻结分类结果、旧 PR 结果或 factorization NO-GO；不据此作真实 XRD、未见材料或精修结论。
