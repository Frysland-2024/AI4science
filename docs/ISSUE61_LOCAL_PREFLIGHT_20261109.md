# Issue #61 本机数据包与 CPU 预检记录

**日期：** 2026-11-09

**验收分支：** `codex/issue61-preflight-20261109`，基于当前 `main` `3df75f9b6a990c5789e27128dbcd6aaf57e08278`。

**结论：** 本机结构 schema、完整 PeakTable 缓存、训练/验证 manifest、私有包一致性与 CPU 路径通过。目标 Linux/CUDA GPU 验收未运行，已按负责人指示转到 Issue #55 Stage 0。

## 本机通过项

| 项目 | 证据 | 结果 |
|---|---|---|
| 私有源数据 | 六个源文件 SHA256 与 `delivery_validation.json` 一致；train/validation/test 行数为 108,483 / 23,246 / 23,246；154,975 records、154,968 parent groups，跨 split 无母结构泄漏 | PASS |
| PeakTable 缓存 | `verify_peak_cache.py` 对 154,975 个缓存逐文件 SHA256 全量核验；三个 split 的 summary、manifest 与 aggregate hash 一致 | PASS；缓存未重建或修改 |
| `--records-path` 与 schema adapter | 新增支持外部 `.jsonl` / `.jsonl.gz`；以全量 train shard 的行读取/字段适配、限一条真实结构执行 CPU PeakTable precompute；适配计数为 108,483 个 `structure → standardized_structure` 与 108,483 个 `source_structure_fingerprint → structure_fingerprint`，输出 1 项、跳过 0 项 | PASS |
| Train/Validation runner manifest | 对三个源 shard 和现有 train/validation 缓存完整重建 runner manifest；train 108,483 rows、validation 23,246 rows、Test 不写入；输出 131,729 rows，SHA256 `7f169d555de18b4dd811e18a67196acee317733864a1232fa719a861104333dd`，与冻结 manifest 一致 | PASS |
| 新私有 source snapshot | payload contract `v11-prefetch-validation-20261109.1`；136 个成员通过哈希/必需文件清单校验；四个 ZIP 与 launcher/verifier 的 SHA256 检查通过 | PASS |
| `start_server.sh --plan` | 在临时 HOME `E:\AI4science\_local\issue61_preflight_20261109\server_home` 完整解包；源分片逐行和 parent-isolation 校验通过；full PeakTable 清单快速校验通过；生成 PLAN_ONLY contract，Test/RRUFF 访问仍禁止 | PASS；没有创建 study/trial |
| ResNet/JS CPU smoke | `one_click_v11.py --mode smoke`：一条 Train 与一条 Validation 记录，V11 paired views → ResNet-18-GN A0 → CE+same-parent JS，13,008,839 参数，loss 有限 | PASS；一批 CPU，不是训练结果 |
| Prefetch parity smoke | 私有 Train 8 条记录、2 worker；串行与并行的两视图及标签逐元素 bitwise 相同 | PASS；启动耗时小样本，不作加速结论 |

新增 private migration kit 位于本机 `_local/issue61_package_20261109`；验证 Python 环境位于本机 `_local/issue61_preflight_20261109/venv`。源数据/缓存均通过只读路径消费，新的单结构 smoke 输出在验收分支忽略的临时数据目录；原始缓存未重算。

## 移交到 Issue #55 的云端门槛

以下内容不属于 #61 的本机完成范围，归入 #55 Stage 0，须在 HPO 前完成并留存记录：目标 Linux GPU/CUDA 兼容性与有限 smoke；吞吐、显存、RAM、磁盘测量；全量 Validation 在 GPU 路径上的可访问性；checkpoint/resume 与随机性复现。**本记录没有租云、启动 GPU、Optuna、正式训练或 RRUFF/Test 评分，也没有把本机 CPU 结果称作 GPU readiness。**

V10 A0_R1 权重在迁移 ZIP 中仍只作为历史参考，不是 V11/154,975 训练 checkpoint。即使 #55 的 GPU Stage 0 通过，HPO/最终训练仍需单独预算与负责人授权。
