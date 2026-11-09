# Issue #61 本机数据包与 CPU 预检记录

**日期：** 2026-11-09

**代码基线：** GitHub `main` commit `158c98902033b56de746c349c12d7db953a35f36`（含 schema adapter、manifest builder、缓存逐文件 SHA 检查和回归测试）

**payload contract：** `v11-prefetch-validation-20261109.3`
**结论：** 本机 package/schema/manifest/CPU preflight 通过。目标 Linux/CUDA GPU 验收未运行，已按负责人指示转到 Issue #55 Stage 0。

## 本机验收

| 项目 | 证据 | 结果 |
|---|---|---|
| 源数据和划分 | 6 个冻结文件 SHA 与 `delivery_validation.json` 一致；Train/Validation/Test 行数为 108,483 / 23,246 / 23,246；共 154,975 records、154,968 parent groups；跨 split 无 parent 泄漏 | PASS |
| 私有迁移包 | 基于当前 `main` 重建 source snapshot，contract `.3`、137 个 source 文件；ZIP/launcher SHA 核验通过。结构分片、PeakTable cache、V10 A0_R1 参考 checkpoint 沿用字节不变的既有 ZIP，SHA 分别为 `e1f1b2486cee1eb371b7bce10ba5d94feb2441664125a81ea317ffafd5f77a23`、`5ee89e04d66af9bcf318d6586d0c819c60e6f2c894c92f5e4f3a67b8181092f2`、`e7eb09ca2d4b9567504db6013b9a2f1dc4403d70bdc91d65c0b9722c7015f895`；完整清单在私有包 `bundle_manifest.json` | PASS |
| PeakTable cache | 本机既有缓存曾对 154,975 项逐文件 SHA256 全量核验通过；当前代码的 merged manifest builder 又对全部 Train/Validation cache 文件执行 bytes 与 SHA256 检查；当前包 `--plan` 核对 split 数量和缓存 aggregate | PASS；没有重算或改写既有 cache |
| `--records-path` / schema adapter | 从冻结 `.jsonl.gz` train shard 读取一条真实结构，`precompute_peak_tables.py` 输出 1 项、跳过 0 项，写入隔离临时目录 | PASS |
| Train/Validation runner manifest | 当前 main builder 从三个冻结 shard 与 Train/Validation cache 完整重建；Train 108,483 rows、Validation 23,246 rows，Test 未纳入；合计 131,729 rows，SHA256 `7f169d555de18b4dd811e18a67196acee317733864a1232fa719a861104333dd`，与冻结值一致 | PASS |
| `start_server.sh --plan` | payload `.3`、source snapshot 137 文件 hash、源分片行数/parent isolation、cache readiness 和 PLAN_ONLY contract 均通过；Train 108,478 parent、Validation 23,245 parent、held-out Test 23,245 parent；Test/RRUFF 访问禁止 | PASS；没有创建 study/trial |
| ResNet/JS CPU smoke | `one_click_v11.py --mode smoke`：1 条 Train 与 1 条 Validation 记录，V11 → ResNet-18-GN A0 → CE + same-parent JS，13,008,839 参数，loss 有限 | PASS；单批 CPU smoke，不是训练结果 |
| Prefetch parity | 私有 Train 8 条记录、2 workers；串行与多进程两视图及标签逐元素 bitwise 相同 | PASS；启动占主导的小样本，不构成加速结论 |

XRD CI [#42554396816](https://github.com/Frysland-2024/AI4science/actions/runs/42554396816) 与 V11 migration CI [#42554691047](https://github.com/Frysland-2024/AI4science/actions/runs/42554691047) 均通过。私有包和隔离验收日志位于本机 `_local/issue61_preflight_20261109/`；结构分片、cache 与 checkpoint 未被改写。

## 移交到 Issue #55 Stage 0 的云端门槛

以下项目不属于 #61 的本机范围，均标记 `BLOCKED / NOT_RUN` 并由 #55 Stage 0 负责：目标 Linux/CUDA 有界 smoke；Train batch 吞吐及 GPU 显存、主机 RAM、磁盘测量；全部 23,245 Validation parents 在 GPU 路径上的可访问性；checkpoint/resume、数据游标和 RNG 复现。它们需负责人单独批准 GPU 预算和有限验收方案。**本记录没有租云、启动 CUDA/GPU、Optuna、正式训练或 Test/RRUFF 评分。**

Stage 0 通过也不自动授权 HPO 或正式训练；这些仍需单独预算、协议和负责人批准。V10 A0_R1 checkpoint 在迁移包中仅作历史参考，不是 V11/154,975 训练结果。
