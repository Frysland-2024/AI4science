# 项目发展记录：pairing ablation 从 60 epoch pilot 延长到 100 epoch ceiling

**日期：** 2026-09-14  
**状态：** 已写执行脚本，等待本地运行。

## 为什么延长

单 seed quick pilot 中，same-parent JS 在 Validation mean six-single-OOD Macro-F1 上达到 `0.702199`，same-class different-parent JS 为 `0.627633`，差值约 `+7.46 pp`；六个单因素 OOD profile 全部为 same-parent 更高，其中 broadening 差值约 `+20.71 pp`。

这一结果强烈支持 parent-level provenance / measurement-equivalence relation 比 generic same-class consistency 更有价值，但 same-class arm 的最佳 checkpoint 恰好出现在原 60 epoch 上限，因此仍需排除“same-class 只是收敛更慢”的解释。

## 为什么不能直接从 60 epoch 继续

原 quick runner 只保存 `best.pt`，没有保存 epoch-60 的完整 model + AdamW optimizer state。

- same-parent `best_epoch = 40`；
- same-class `best_epoch = 60`。

如果分别从两个 `best.pt` 继续，会让两个 arm 从不同训练历史出发，破坏 controlled ablation 的公平性。因此本轮不做伪 resume，而做 deterministic replay：从 epoch 1 使用相同 seed / batches / views / optimizer / lambda / Validation panel 重放，并把最大 horizon 从 60 提高到 100。

## early stopping 保持不变

- Validation every 10 epochs；
- minimum epoch = 40；
- patience = 2 次 Validation check；
- min_delta = 0.002；
- stopping metric = Validation mean six-single-OOD Macro-F1。

因此“100 epoch”是 ceiling，不是强制跑满；若 early stopping 条件满足，可以在 100 之前停止。

## 执行脚本

`xrd_robustness/scripts/run_pairing_ablation_extend100.py`

默认输出：

`xrd_robustness/outputs/pairing_ablation_extend100/`

旧的 `pairing_ablation_quick` 只作为只读 reference，不被覆盖。

## 结果解释

- 若 same-class 到 80/100 epoch 后仍明显落后，parent-specific relational supervision 的机制解释得到进一步加强；
- 若差距显著缩小，说明此前的差异部分来自收敛速度，应收缩机制 claim；
- 无论结果如何，原 ERM-vs-JS 主结果不受影响，本实验只负责更窄的 parent-specific mechanism attribution。
