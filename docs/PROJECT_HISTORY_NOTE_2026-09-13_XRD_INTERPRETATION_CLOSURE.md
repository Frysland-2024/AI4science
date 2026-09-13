# 项目发展记录：从“平均分数”转向 XRD-specific interpretation

**日期：** 2026-09-13  
**性质：** 现有冻结结果的重新组织与物理解读，不修改训练、数据划分、checkpoint 或 raw outputs。

## 背景

在将 PXRD 汇报标准从通用 AI 工程范式切换到 XRD-ML 社区范式后，进一步追问：相比成熟 XRD 机器学习论文，当前项目真正还缺什么？

结论发生了一个重要变化：

> 缺口已经不是更多 seed、bootstrap、loss、优化器或工程审计，而是把现有结果解释成“哪些 XRD 测量变化下更稳健、哪些晶系受益/受损、哪些真实谱被修正或破坏”。

因此，本轮不新增训练，而是重新挖掘已经冻结的预测与结果文件。

## 1. Profile-wise simulated Test 已从现有结果中闭环

从 `xrd_robustness/outputs/calibration_analysis/simulated_paired.csv` 重新整理六个 single-factor OOD。每个 profile 先在同一 training seed 内平均三个 evaluation seeds，再对五个 training seeds 汇总。

主要发现：

- negative shift：Macro-F1 `0.6926 -> 0.7290`，`+3.64 pp`；
- positive shift：`0.6871 -> 0.7307`，`+4.36 pp`；
- broadening：`0.5517 -> 0.6357`，`+8.40 pp`；
- noise：`0.6712 -> 0.7033`，`+3.22 pp`；
- background：`0.6827 -> 0.7332`，`+5.05 pp`；
- preferred orientation / texture：`0.6191 -> 0.7000`，`+8.09 pp`。

六种单因素条件下，五个 training seeds 的 seed-averaged Macro-F1 差值均为正。

新的 XRD-specific 认识是：

> broadening 与 texture 不仅是 ERM 最困难的两类扰动，也是 JS 增益最大的两类；background 次之，而纯 shift / noise 增益较小但仍为正。

这使原本单一的 `+5.46 pp mean OOD` 进一步获得了物理结构：收益主要集中在更明显改变峰宽和相对峰强关系的测量变化上。

## 2. RRUFF-301 已有成熟的 fix / break 与逐类证据

重新调出历史 `rruff301_representation_analysis_20260807.md` 后确认，当时其实已经完成了非常接近成熟 XRD-ML 论文的真实谱行为分析，只是后来没有进入当前技术报告。

主要结果：

- K=1：112 个 test samples 净改善、78 个净损伤，fix/break ratio 1.31；
- K=2：110 / 66，ratio 1.43；
- K=5：103 / 70，ratio 1.57。

K=5 的晶系级净正确次数变化：

- triclinic `+68`；
- monoclinic `+74`；
- orthorhombic `+116`；
- tetragonal `+30`；
- trigonal `-14`；
- hexagonal `+81`；
- cubic `-27`。

因此，真实域收益不能讲成“所有晶系都更好”，而应讲成：整体改善明确，但收益具有 class heterogeneity。

早期 RRUFF-70 中 monoclinic 的负迁移也在 RRUFF-301 中被否定：K=1/2/5 的 monoclinic F1 分别提升 `+3.60 / +6.81 / +6.91 pp`。

## 3. Representative real-XRD cases 已定位，但原始谱线仍需本地资产

K=5 下最强的 JS-improved candidates 包括：

- `R090034` orthorhombic；
- `R070562` triclinic；
- `R050008` orthorhombic；
- `R050027` hexagonal。

最强的 JS-damaged candidates 包括：

- `R050657` triclinic；
- `R040027` cubic；
- `R050609` cubic。

这些 sample IDs 与分类行为已经有 tracked historical evidence，但原始 RRUFF XRD traces 不在当前 Git tracked tree 中。因此正式报告只能记录“哪些样本被稳定修正/损伤”，不能凭 ID 推测峰缺失、背景、texture、杂相等物理原因。

下一步若做 spectrum-level failure figure，应从本地 RRUFF 原始资产读取这些谱线后再进行物理解释。

## 4. CNRS 的逐类失败模式被正式提升到 Discussion

CNRS pooled per-class F1 显示 JS 改善 5/7 类，但 monoclinic 与 tetragonal 下降；其中 tetragonal `0.2984 -> 0.2362`，已有 confusion 分析表明更多 tetragonal patterns 被路由到 trigonal。

因此 CNRS 的成熟写法不再只是“+1.79 pp Macro-F1”，而是同时说明：

- aggregate metrics 改善；
- orthorhombic 等类明显受益；
- tetragonal 存在明确退化模式；
- hexagonal 只有 12 parents，不能过度解释较大涨幅；
- overall Accuracy 仍约 0.21，sim-to-real gap 依旧显著。

## 5. 仍未闭环的唯一关键方法归因：same-parent vs same-class

仓库中没有发现以下直接消融：

`Dynamic ERM vs same-class different-parent JS vs same-parent JS`

所以当前严格能够证明的是：

> same-parent JS consistency 优于 matched Dynamic ERM。

但不能进一步声称：

> same-parent identity 已经被证明比一般的 same-class pairing 更有效。

如果未来真的以“simulator-retained parent identity”作为论文最强方法学 claim，这会是最值得新增的一项消融；当前阶段不把它伪装成已有证据。

## 项目发展意义

本轮进一步确认了项目从工程化 ML benchmark 向 XRD-specific scientific interpretation 的转变：

> 过去更关注“平均 OOD 分数提高多少”；现在开始追问“是哪些物理扰动提高、哪些晶系提高、哪些真实谱被修正、哪里仍然失败”。

这更接近成熟 XRD-ML 论文真正的科学组织方式，也更符合后续申请叙事中“从模拟增广到关系监督，再到科学测量机制解释”的发展轨迹。
