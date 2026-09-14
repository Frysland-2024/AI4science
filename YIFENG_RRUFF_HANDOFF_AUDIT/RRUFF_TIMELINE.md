# RRUFF real-domain 13-stage timeline

## Stage 1 — broad RRUFF zero-shot / pipeline diagnostic

- 日期/锚点：2026-08-06，commit `2cb656c0`；历史报告 `xrd_robustness/reports/rruff_pipeline_smoke_test_20260806.md`。
- 本地输入：`xrd_robustness/data/real_xrd/rruff_pipeline_test/`，35 个独立样本。
- 历史记录：JS accuracy 约 0.2343，ERM 约 0.1886；cubic 为 0、hexagonal 约 0.04。
- 解释：这是 pipeline/domain diagnostic，不是稳定的 real-domain 效果估计；当前没有独立 raw result 文件，数字只能作为历史记录。

## Stage 2 — RRUFF-70 exploratory few-shot

- 日期/锚点：2026-08-06/07，commit `385cbbc9`；本地 frozen bundle `rruff70/`。
- 设计：7 类 × 10 样本，K=1/2/5，5 pretrained seeds × 5 episode seeds，配对比较。
- 当前本地 exploratory JSON 的 accuracy：K1 0.19746→0.24000，K2 0.19929→0.24786，K5 0.20914→0.28000；paired delta +0.04254/+0.04857/+0.07086；60/75 正配对。
- 边界：JSON 没有 Macro-F1 字段，`per_class` 是类级正确率/recall；旧文案若称其为 ΔF1 不可复用。

## Stage 3 — zero-shot → label-efficient adaptation

- 日期/锚点：2026-07-24，commits `5e624f0b`、`5af5358e`。
- 核心决策：真实域单纯 zero-shot 暴露 domain gap，但难回答“少量实验标签是否能高效利用模拟预训练表征”；研究问题转为 label-efficient few-shot adaptation。
- 证据：历史 decision、method-transfer config、few-shot protocol。

## Stage 4 — 为什么 RRUFF-70 不够

- RRUFF-70 每类仅 10 个样本，K 改变时 query 数也变化，类级信号高度不稳定。
- monoclinic 在 K1/K2/K5 出现约 −0.0356/−0.0150/−0.0880 的 exploratory 负迁移，但不能据此得出 confirmatory 类别结论。
- 因此将 RRUFF-70 明确降级为探索性证据，扩展到均衡的 RRUFF-301。

## Stage 5 — RRUFF-301 preregistration

- 日期/锚点：commit `385cbbc9`。
- 设计：301 个谱图，7 类各 43；70 adaptation pool + 231 locked test；K=1/2/5；train seeds 20260711–20260715；episode seeds 42/123/456/789/1024；25 配对/K；paired Macro-F1 为 primary；K1/K5 fixed-200 sensitivity；monoclinic 是预先提出的 follow-up。
- 关键限制：prereg 中承诺的原始 `rruff301_episode_plan.csv` 没有找到。

## Stage 6 — RRUFF-301 v1

- 日期：2026-08-07 早期运行。
- v1 曾生成约 +0.063/+0.081/+0.078 的正增益摘要，但 split 实际是 60 adaptation + 241 test，不符合预注册的 70+231。
- 本地遗留：`rruff301_split.csv`，SHA-256 `15B7E2...D72E1D`。它只能保存为失败证据。

## Stage 7 — trigonal/hexagonal label bug discovery

- 审计发现 RRUFF `CELL PARAMETERS` 中的 trigonal/rhombohedral 条目按 hexagonal setting 被解析到 hexagonal；结果为 hexagonal=86、trigonal=0。
- 证据：`rruff301_v1_audit_trail_20260807.md`、本地 `check_rruff_pool.py`、`fix_rruff301_split.py`，以及错误 v1 split。
- 科研价值：主动审计标签语义，而不是只接受看似更好的指标。

## Stage 8 — v1 invalidation

- v1 因标签映射与样本计数违反 prereg 而整体作废；不是简单改标签后保留原结果。
- 决策：不改模型、超参、K、seed 或 primary metric，只修复 DIF + pymatgen 的 crystal-system 判定并完整重跑。
- 历史权威：`rruff301_v1_audit_trail_20260807.md`。

## Stage 9 — corrected RRUFF-301 v2

- 日期/锚点：commit `24d8c851`；当前本地正确 split `rruff301_adaptation_test_split.csv`。
- v2 恢复 7 类各 43，70 adaptation + 231 locked test。
- 当前 composition audit：301 unique IDs；split ID overlap=0；exact spectrum SHA overlap=0；16,170 个跨 split 谱对最大 Pearson=0.947785，无 ≥0.95 近重复。

## Stage 10 — K=1/2/5 + 5×5 paired results

当前权威 raw：`rruff301_fewshot_runs.json`；公开摘要：`xrd_robustness/reports/rruff301_fewshot_results.json`。

| K | Macro-F1 ERM → JS | paired Δ ± sample SD | positive pairs | Accuracy ERM → JS | paired Δ |
|---:|---|---|---:|---|---|
| 1 | 0.284719 → 0.328040 | +0.043321 ± 0.044623 | 21/25 | 0.299048 → 0.337489 | +0.038442 |
| 2 | 0.302615 → 0.348641 | +0.046026 ± 0.035264 | 23/25 | 0.312035 → 0.360866 | +0.048831 |
| 5 | 0.355464 → 0.409931 | +0.054467 ± 0.031175 | 24/25 | 0.358095 → 0.414892 | +0.056797 |

总计 68/75 正配对；先对 episode 求均值后，每个 K 都是 5/5 pretrained seeds 正向。SD 为 25 个 paired deltas 的 sample SD（ddof=1）。

## Stage 11 — per-class / negative transfer

- monoclinic v2 paired F1 delta：K1 +0.03604、K2 +0.06807、K5 +0.06910；RRUFF-70 的负迁移信号未复现。
- trigonal：K1 −0.02305、K2 −0.03444、K5 +0.02794；cubic：K1 +0.07750、K2 −0.01666、K5 −0.01501。
- 结论：aggregate label-efficiency 改善稳定，但类别响应异质；不能声称所有类别、所有 K 都获益。

## Stage 12 — representation / fix-break analysis

- 历史报告：`rruff301_representation_analysis_20260807.md`。
- 当前 prediction 只读核对：K1 fix=934、break=712、ratio=1.312；K2 936/654/1.431；K5 902/574/1.571。
- 解释：K 增大时净纠错相对破坏更强，与 label-efficient representation transfer 一致。
- 边界：prediction 文件没有 logits/probabilities；所谓 confidence proxy 是跨运行 correctness rate，不是 calibrated confidence，不能直接支持 ECE/NLL/Brier。

## Stage 13 — final label-efficiency conclusion

最稳健的科学结论是：**在均衡、锁定、成对的 RRUFF-301 实验域任务中，simulation-pretrained JS representations 相对 Dynamic ERM 在 K=1/2/5 均提高 Macro-F1 和 accuracy，且 68/75 配对为正；收益随类别变化，并不等于消除了 sim-to-real gap。**

RRUFF-70、broad zero-shot 与 monoclinic 信号用于形成问题和假设；corrected RRUFF-301 v2 才是 confirmatory 主证据。
