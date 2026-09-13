# Pairing ablation：恢复优化管线后的启动说明

默认脚本已经重新接入历史动态在线生成优化，不需要额外传 prefetch 参数。

默认值：

- 16 persistent render workers；
- 6 batches ahead；
- 1 native thread / worker；
- pinned host memory；
- non-blocking H2D；
- training quality gate enabled；
- Validation-only mechanism pilot；
- simulated Test 不访问。

在 `E:\AI4science\xrd_robustness` 下：

```powershell
& "E:\AI4science\.venvs\xrd_test\Scripts\python.exe" scripts/run_pairing_ablation.py --dry-run --device cuda --output-root outputs/pairing_ablation_quick
```

确认配对后启动单 seed pilot：

```powershell
& "E:\AI4science\.venvs\xrd_test\Scripts\python.exe" scripts/run_pairing_ablation.py --quick --device cuda --output-root outputs/pairing_ablation_quick
```

脚本每个 epoch 都会打印训练墙钟时间与 prefetch wait；每 10 epoch 打印 Validation in-range Macro-F1 与 six-single-OOD mean Macro-F1。

最终结果：

`outputs/pairing_ablation_quick/summary.json`

关键字段：

`parent_minus_same_class_mean_ood_macro_f1`

工程 runtime / prefetch 统计只留在本地 JSON，不进入正式 XRD-ML Results。
