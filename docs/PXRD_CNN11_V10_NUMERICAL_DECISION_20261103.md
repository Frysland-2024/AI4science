# CNN11 V10 数值诊断与架构取舍（2026-11-03）

**工程结论：RETAIN_RESNET / STOP_CNN11_EXTRA_TRAINING。** 保留 ResNet-18-GN + same-parent Dynamic JS；不再为 CNN11 追加完整三 seed GPU 训练。这个判定只适用于当前项目的训练和验证预算，不证明 CNN11 架构普遍劣于 ResNet。

## 证据与结果

原始 V10 CNN11 在 seed 20260711、约 20,000 step 首次记录 CE / JS / total loss 均为 NaN，并在 step 24,640 的 Validation OOD Macro-F1 跌至 0.035581；原始 step 18,480 选中 checkpoint 的 SHA256 为 E415DBFD042EADC8595F4B5FD7F78AC1F7160517324308AD71B74AA187CDB08F。所有历史日志和权重保留原样。

- **未经修复 BF16 回放：**从原始 checkpoint 恢复 AdamW、CPU/CUDA RNG 与 parent sampler，18,480→27,000 step 全程有限，未再次出现 NaN。回放与原始训练路径不完全一致，故不能认定当初故障已被准确重现或排除。
- **数值风险的可重复证据：**旧 JS 实现直接以极小/零概率作为 KL target，对极端 BF16 logits 的回归测试出现 loss 有限而梯度非有限；单纯 FP32 上转仍未解决。换成 FP32 CE/JS 与等价的 logaddexp-JS 算法后，梯度有限，相关 6 项测试通过，拓展的仿真与训练回归测试合计 **21/21 通过**。
- **修复后实际 GPU 回放：**RTX 4060 Laptop GPU 8 GB，BF16 网络前向不变，FP32 损失/稳定 JS，18,480→24,640 step 全程有限。仅访问已冻结的七个 Validation profiles，不运行 RRUFF 或锁定 Test。回放输出纯推理 snapshot 本地 SHA256 72BFDCE2ABFAB1C620D7D6A1A549419CA5F2424AEA3C1D35E70E81F8DDFE8E92（权重文件不提交 Git）。
- **验证协议复核：**把旧 step 18,480 checkpoint 按相同代码重新打分，六单因素平均 OOD Macro-F1 = 0.681748，与冻结日志 0.681741 相差约 0.000007，说明当前 Validation 读取/计算方法与原协议一致。

| Validation 指标 | ResNet (seed 20260711, step 24640) | 修复 CNN11 (seed 20260711, step 24640) |
|---|---:|---:|
| 6-profile OOD Macro-F1 | **0.696204** | 0.629091 |
| In-range Macro-F1 | **0.726802** | 0.668341 |

ResNet 三个已完成训练 seed 各自选择的最佳 Validation OOD Macro-F1 为 **0.708988 / 0.713894 / 0.706045**；均值 **0.709642**。修复 CNN11 在相同 seed 和 step 的 OOD Macro-F1 比 ResNet 低 **6.71 个百分点**。继续为 CNN11 完整跑满剩余训练及两次种子复现的预计信息收益不足。

## 科学边界与后续决定

1. 极端 logits 回归证明 JS 实现存在数值梯度漏洞，但**不能反推**它就是历史 NaN 的唯一根因；原始训练未被逐位重现。
2. CNN11 是一轮 partial single-seed 恢复，不属于完整等预算三 seed 架构对比。不得据此撰写 CNN11 本质较差或达到统计显著劣势的声明。
3. 损失改动在实数数学上保留 CE + same-parent JS 目标，只改变有限精度实现；冻结的旧 ResNet、RRUFF、模拟 Test 和 checkpoint 不修改。
4. **架构工程筛选完成：保留 ResNet。** Stage 2 中的 ResNet 结构/训练超参数有限优化仍未完成，见 GitHub Issue #55。随后依次进行独立 CIF 数据扩容（#61）与 RRUFF 文献对标。

## 可检查工件

- xrd_robustness/src/xrd_robustness/training/objectives.py：FP32 CE/JS + logaddexp-JS。
- xrd_robustness/tests/training/test_cnn11_bf16_objectives.py：极端梯度/BF16/数学等价性。
- xrd_robustness/scripts/diagnose_cnn11_nan_resume.py：原始 checkpoint 恢复，逐步有限检查，冻结 Validation 评分，本地 snapshot 可选。
- xrd_robustness/reports/cnn11_direct_20261103/：原始 BF16 与修复后 GPU 回放 JSONL/summary、冻结原 checkpoint 评分复核、decision.json。
- xrd_robustness/reports/simxrd_architecture_pilot_20261103/：选择性保留旧失败日志与已冻结基线摘要，供交叉审计。
- 本分支单独位于 E:\AI4science\_local\worktrees\cnn11_direct_20261103；主工作区 E:\AI4science 未被清理或覆盖。
