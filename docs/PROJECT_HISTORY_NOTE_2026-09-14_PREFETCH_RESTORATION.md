# 项目发展记录：机制消融前恢复历史在线生成优化

**日期：** 2026-09-14  
**性质：** 工程加速恢复，不改变科学对照。

## 背景

在准备执行 `same-parent JS` 与 `same-class different-parent JS` 的机制消融时，最初的新脚本直接调用当前精简版 `training/runner.py` 中的同步在线渲染路径。随后回顾项目历史发现：正式主线训练在 2026-07-28 已经专门优化过在线 PXRD 生成瓶颈。

当时的优化包括：

- persistent multiprocessing prefetch；
- 16 个渲染 worker；
- 每个 worker 固定 1 个 native NumPy/BLAS thread；
- 6 个 batch 的 bounded prefetch window；
- worker 内按 material-id stable shard 懒加载并缓存 ideal peak tables；
- `PeakTable` 在加载时缓存 preferred-orientation 所需的结构不变量（canonical hkl、hkl→indices、candidate ranking）；
- quality-reference profile 在 worker 内缓存；
- pinned host memory + non-blocking host-to-device copy。

历史 benchmark 记录表明，该优化在 matched 64-batch / 2,048-view Gate 上使 16-worker prefetch throughput 提升约 `27.67%`，同时 sequential path 因结构不变量缓存提升约 `47.49%`；谱数组、物理参数、material order、hash 与 quality-Gate 计数保持一致。

这些模块后来在 2026-08-23 的公开仓库清理中被删除，因为当时五 seed 主结果已经冻结，公开 reproduction surface 被压缩到简化的 `train.py / training/runner.py`。删除优化模块不代表优化方案无效，只是当时不再需要继续训练。

## 本轮决定

为避免新的 pairing ablation 无谓退回到慢速同步渲染，恢复动态 prefetch 核心，并接入：

`xrd_robustness/scripts/run_pairing_ablation.py`

恢复后的默认执行参数：

- `prefetch_workers = 16`
- `prefetch_batches = 6`
- `worker_native_threads = 1`
- `pin_memory = true`
- `non_blocking_h2d = true`
- `quality_gate = true`
- multiprocessing start method = `spawn`

同时只在主训练进程加载 Validation peak tables；Train peak tables 由 worker 按 shard 懒加载，避免主进程重复持有全部训练 peak cache。

## 科学一致性

本次恢复只改变“谁提前把已经确定的 view 渲染出来”，不改变 pairing ablation 的科学变量。

两个 arm 仍严格共享：

- 同一批 parent；
- 同一两张 online views；
- 同一 CE；
- 同一 ResNet-18-GN；
- 同一初始化 seed；
- 同一 optimizer / learning rate / weight decay；
- 同一 `lambda_js=60`；
- 同一 Validation panels；
- 同一 quality gate。

唯一科学差异仍然是：

- same-parent：`view1(A) ↔ view2(A)`；
- same-class：`view1(A) ↔ view2(B)`，其中 `A != B` 且晶系相同。

same-class arm 仍然只是交换 batch 内已经渲染好的 second-view logits，不增加任何额外谱或 forward。

## 与历史主实验的进一步对齐

恢复 prefetch 时同步恢复了正式训练中的 view-coordinate 语义：

- `epoch` 与 epoch-local `step` 共同决定在线扰动；
- `step` 每个 epoch 从 0 重新开始；
- optimizer 的全局 step 只用于执行记录，不再作为物理扰动采样坐标。

因此，新机制消融比最初的临时脚本更接近历史正式主实验的在线数据生成协议。

## 结果角色

这项恢复属于本地工程实现层，不进入正式 XRD-ML Results。正式汇报仍只讨论 pairing ablation 的 Accuracy / Macro-F1 与 profile-wise 行为；prefetch worker 数、等待时间和 runtime 只保留在本地 JSON / history 中。
