# V9 台式机硬件利用与加速配置

## 结论

目标机器固定为 AMD Ryzen 5 9600X（6 核 12 线程）、NVIDIA GeForce RTX 4070 Ti SUPER（16 GB）和至少 32 GB 系统内存。7-run lambda 调参只包含 Dynamic/Paired ERM、JS 和 Residual；科学合同继续固定 `batch_size=16`、`max_optimizer_steps=30650` 和每结构两视图，不能用扩大训练 batch 的方式改变方法暴露量。

机器可读的唯一配置源是 `configs/hardware.v9.desktop.9600x_4070tis.json`，其 SHA-256 冻结在 `configs/algorithm.v9.method_transfer.json`。计划、实现、硬件审计或迁移清单与当前合同不一致时必须拒绝放行。

## 已注册的硬件配置

- 单 run：`8 workers × 8-batch prefetch window`；每个 worker 限制 1 个原生线程。
- 双 run：同时运行 2 条 run，每条分配 4 个预取 worker；总 worker 预算仍为 8。第 7 条尾任务恢复 8 workers。
- Clean、Offline、Dynamic、JS、Residual 共用同一套确定性进程预取实现。
- 主进程：每条 run 使用 intra-op 2 线程、inter-op 1 线程，并固定 OMP/MKL/OpenBLAS/NumExpr 线程数。
- CPU→GPU：pinned memory 与 non-blocking H2D。
- GPU：`float32_matmul_precision=high`、TF32、cuDNN benchmark、deterministic cuDNN。
- 精度：BF16 自动混合精度；BF16 不使用 GradScaler，数值门失败时不放行。
- 编译：`torch.compile(backend="inductor", mode="default")`，允许记录 eager fallback，但只有检测到实际编译图才算编译门通过。
- 优化器：CUDA fused AdamW 与 `zero_grad(set_to_none=True)`。
- 评估：默认 batch 256；训练 batch 保持 16。

## 已修复的主要瓶颈

1. 动态参数流只为实际预取窗口生成，不再物化 606,267,200 行 manifest。
2. 每个 epoch 使用训练 seed 控制的确定性 shuffle，五种方法共享 sampler 和 pair schedule。
3. 每 step 的 `.item()` 同步已消除；GPU 标量在 epoch 末才汇总到 CPU。
4. 开启预取时主进程不再重复加载全部训练 peak table；worker 按稳定分片懒加载。
5. Clean/Offline 已接入与动态方法相同的确定性多进程预取。
6. 双 run 调度、BF16、Inductor 编译、fused AdamW 和批量评估均已接入启动参数与审计合同。

## 台式机首启门

首启门只做有界工程测试，不做 optimizer step，不保存 checkpoint，不访问 test split，也不启动 7-run：

1. 校验迁移文件逐文件 SHA-256。
2. 首启时即时重查 Python 3.11.9、PyTorch 2.5.1+cu124、CUDA 12.4、`pip check`、BF16、目标 GPU/显存、系统内存和 MSVC C++ 工具链；不复用可能过期的安装报告。
3. 重跑 `8×8` 与双 run 对应的 `4×8` 确定性等价审计。
4. 对 `4/6/8/10 workers × 6/8/10 windows` 做两次完整矩阵复测。只有全部数组、参数、质量门和 pair hash 等价才生成性能建议；脚本不会自动改合同。
5. 对评估 batch `128/256/512` 做真实 B3 合成输入前向、数值前缀、显存和吞吐检查，不访问任何验证/测试结构。
6. 检查 pinned/non-blocking H2D。
7. 对 Dynamic、JS、Residual 做 FP32/BF16/compiled BF16 的 B3 forward/backward 数值比较；要求检测到真实编译图。
8. 比较单进程与两个并发进程的 compiled BF16 吞吐和全局显存；峰值必须低于 15,360 MiB，聚合吞吐不得低于串行的 95%。
9. 汇总为 `ready_for_explicit_tuning_authorization` 或 `blocked`。即使 ready，也仍需用户另行明确授权后才能启动调参。

## 命令

迁移到台式机后，先创建冻结环境：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_v9_desktop_environment.ps1
```

先只查看首启步骤，不执行测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1 -PlanOnly
```

执行完整首启工程门：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1
```

最终证据写入 `reports/desktop_acceptance/desktop_readiness.json`。首启脚本不包含任何训练命令。

Windows 上的 Inductor 能力以目标机实测为准。配置中的 eager fallback 只用于保留可诊断性，不能替代 `torch_compile_graph_executed=true` 的证据。
