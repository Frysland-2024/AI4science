# 物理启发式初始化与 RRUFF 实测验证

**E1：COMPLETE；七种材料均未达到预注册的神经增量价值判据。** N+A 对 H1/P0 的主预算误差相当，但至少 20% 延迟降低只在少数 seed-材料比较中出现；E1 对 P3 全部通过不能替代对 H1/P0 的比较。

**E2：PHYSICS_NOT_READY；真实神经臂 NOT_RUN。** 三条精确 ID Rutile 实测谱均未通过多起点稳定性/边界门槛；R050417-1 还未通过预测强峰覆盖门槛。没有放宽门槛或用精修晶胞选初值。

记录的实验数值执行时间为 886.95 秒 / 10,800 秒上限；新训练 0 秒，新增 GPU 训练 0 秒。E1 使用 21 个既有模型，总历史训练成本 20.414 秒。

E1 原始 JSONL、每材料完成哈希、冻结协议及机器可读汇总均保留。E2 只公开来源与字节哈希、门槛结果和逐样品汇总；原始 RRUFF 谱、ZIP 成员和模型权重仍在本地私有目录。E2 的两个 base ID 与旧 RRUFF-301 locked-test 有重叠，因此这些病例不代表新的分类独立留出集。

结论仅适用于本次合成事后比较和三个描述性真实谱案例。优化器报告收敛或 RMSE 较低，不证明晶格参数正确；RRUFF 同 ID 精修晶胞仅用于事后一致性，不是独立真值。

详细记录：
- [E1 预注册](../E1_PREREGISTRATION.md) 与 [E1 结果](HEURISTIC_RESULTS.md)
- [E2 预注册](../E2_PREREGISTRATION.md)、[E2 结果](RRUFF_REAL_RESULTS.md) 与 [E2 manifest](e2_manifest.json)
- [机器状态](status.json)、[失败与预算记录](FAILURES.json)、[历史角色重叠](historical_id_overlap.json)
- [修正后的 E1 汇总（已移除不可用零占位）](e1/summary_without_unavailable_spread.json)
