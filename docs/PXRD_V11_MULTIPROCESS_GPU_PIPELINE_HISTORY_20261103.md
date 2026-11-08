# PXRD V11: 从串行训练到统一 CPU/GPU 流水线（2026-11-03）

## 研究过程与问题来源
此前 V9/V10 训练使用过多进程 DynamicBatchPrefetcher，具有 SHA256 material-ID
稳定 worker 分片、有界预取、固定线程数与批次原顺序恢复的成熟机制。迁移到
154,975 个 MP-ID 的 V11 HPO 原型时，为优先实现科研工作流，暂时使用了串行
`render_pair_batch`，全验证集缓存也采用串行 CPU 谱图渲染。这带来两个问题：

1. GPU 训练需要等待 CPU 对下一个 parent 的双视图模拟，GPU 空转；
2. 23,245 个 Validation parent × 六种扰动 × 两个视图会产生大量 CPU 模拟，
   再把同一套谱重复用于 Optuna，因此一次性冻结是正确的，但需要并行制备。

项目负责人进一步明确：**旧的工程加速不仅用于 Validation，也必须用于接下来的
GPU HPO、独立 seed 验证与最终三 seed 训练**。这不是修改研究主线，而是
复用原来已积累的科研工程资产。

## 本轮代码实现（PR #67，基于 #66）
- `server_migration/v11_prefetch.py`：重用旧
  `training_prefetch.deterministic_worker_shard` 与
  `PREFETCH_NATIVE_THREAD_ENV_VARS`；V11 用同一个
  `build_online_view_factory`，保留 same-parent 动态物理扰动与两视图身份；
  4 个默认 `spawn` worker，三批有限缓冲，1 native thread/worker，
  单 worker 最多 512 个 PeakTable LRU 条目，按 material-ID 确定性汇总。
- 训练 CPU/GPU 重叠：主进程生成后续 batch 的 parent 索引，CPU workers
  在线模拟，GPU 对当前 batch 做 pinned non-blocking H2D、BF16 前向与 FP32 CE/JS
  梯度；不将有限的模型输入谱保存为训练数据库。
- checkpoint 正确性：预取可能提前消费 NumPy 的 parent RNG，因此
  **checkpoint 保存已提交 optimizer step 的 RNG，而非预取窗口末端的 RNG**。
  恢复后可重建尚未训练的 batch，防止 silently skip 样本。
- Validation：按全部 23,245 独立 parent 生成六种 OOD paired spectra，
  使用同一 CPU worker 渲染；数据一次写成 SHA256 索引的 float32 memmap，
  后续全部 HPO/seed 复用，GPU 分批推理使用 pinned H2D；为保留科研排序，
  默认 FP32 Validation（BF16 仅显式选用并先核验分数差异）。
- HPO 与终训：`--mode run` 为六组 Optuna 搜索及两 seed 复验；
  新的显式 `--mode final` 用冻结的最优配置在相同优化引擎里执行
  三 seed（缺省每 seed 49,280 step），并归档独立 checkpoints 与汇总。
- 安全：旧 ZIP 若缺少新增预取模块，一键脚本拒绝执行；完整迁移包须重新构建。
  锁定 Test 与真实 RRUFF 不参与超参数/验证选择。

## 可核验结果与未完成工作
- GitHub Actions 已通过一轮 Python 编译、parent 校验、预取窗口/随机数恢复的
  CPU-only 测试；更多 CI 持续复验中。
- 新增 `smoke_prefetch.py`：在真实数据上比对原串行 V11 与预取 V11
  的 paired XRD 数组，逐元素一致才允许启动正式云端训练。
- **由于本地电脑暂时离线，尚未执行这份新版代码的本地性能测试，也没有重打
  E:\AI4science\_local\server_migration_20261103 的私有 ZIP。**
  不应据此宣称已测得加速比例、云端运行成本、完整验证吞吐或断点恢复实测。
- 电脑重新在线后：更新主项目工作树和私有 ZIP，确认 SHA256；
  执行串行/并行 V11 谱一致性测试、GPU batch / full Validation 与
  完整中断恢复测试，对比 steps/s 与内存峰值；才允许把 PR #67 合入运行基线。

**科学边界：** 本轮属于训练系统优化；没有重新筛选结构、改变七晶系标签、
修改同 parent JS 定义、重选 Test/RRUFF，也没有产生新的正式科研成绩。
