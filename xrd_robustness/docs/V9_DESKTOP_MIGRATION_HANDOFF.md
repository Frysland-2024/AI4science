# V9 台式机迁移交接

> 新 Codex 账号的完整研究、工程、授权与恢复上下文以仓库根目录 `CODEX_HANDOFF.md` 为接管入口；本文件只负责迁移步骤。迁移和首启验收均不构成训练授权。

## 当前边界

- 笔记本只做代码、哈希和轻量工程测试，不启动正式训练。
- 不迁移旧训练进程、optimizer 状态或 checkpoint；台式机未来从 optimizer step 0 开始完整 7-run。
- 迁移和首启均不构成训练授权。

## 1. 在笔记本生成并确认迁移清单

```powershell
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\prepare_v9_desktop_migration.py
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\verify_v9_desktop_migration.py --root E:\AI4science\xrd_robustness
```

必须满足：manifest 为 `ready_for_copy`、逐文件验证为 `pass`、活动训练进程/registry/checkpoint/results 均为 0。

## 2. 复制清单内文件

把目标磁盘挂载为合适盘符后运行；先用 `-WhatIf` 查看范围：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\copy_v9_desktop_payload.ps1 -DestinationRoot "E:\AI4science\xrd_robustness" -WhatIf
powershell -ExecutionPolicy Bypass -File scripts\copy_v9_desktop_payload.ps1 -DestinationRoot "E:\AI4science\xrd_robustness"
```

复制器只复制 CSV 清单中的文件和两个迁移控制文件，拒绝 `..` 越界路径。

## 3. 台式机环境

安装 NVIDIA 驱动、Python 3.11.9 和 Visual Studio 2022 C++ Build Tools（x64 workload），然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_v9_desktop_environment.ps1
```

脚本创建 `E:\AI4science\.venvs\xrd_tools`，安装冻结的 NumPy/PyTorch CUDA 版本，执行 `pip check`，并输出 `reports/desktop_environment_bootstrap.json`。

## 4. 台式机首启工程门

```powershell
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1 -PlanOnly
powershell -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1
```

首启会即时重查冻结 runtime 与 `pip check`，再运行迁移、配置、预取矩阵、评估 batch、H2D、BF16、真实编译图和双进程显存/吞吐门。最终只生成 readiness 报告，不启动训练。

## 5. 停止点

看到 `ready_for_explicit_tuning_authorization` 后仍然停止。只有用户在台式机上重新明确授权完整 lambda 7-run，才可以调用 `tune-run`；不得根据本交接文档自动启动。
