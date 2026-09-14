# REFERENCE_ONLY — 共同项目依赖

这些资产支撑 RRUFF，但当前 provenance 明确不把它们归为 Yifeng 独立模块。Stage 2 不应复制整个共同项目；只需保留路径、commit/hash 与依赖说明。

| 路径 | 当前状态 | RRUFF 为什么依赖 | 处理 |
|---|---|---|---|
| `xrd_robustness/src/xrd_robustness/formal_14060.py` | tracked | 共享 simulated PXRD/measurement 基础 | 仅记录 Git path |
| `xrd_robustness/src/xrd_robustness/dynamic_pair_dataset.py` | tracked | Dynamic paired training data plumbing | 仅记录 Git path |
| `xrd_robustness/src/xrd_robustness/training/objectives.py` | tracked | Dynamic ERM / JS objective 实现 | 仅记录 Git path |
| `xrd_robustness/src/xrd_robustness/training/runner.py` | tracked | 共享训练执行框架 | 仅记录 Git path |
| `xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py` | tracked | RRUFF adaptation 使用的 pretrained backbone 结构 | 仅记录 Git path |
| `xrd_robustness/scripts/run_simulated_test.py` | tracked | 提供 pretrained seeds / shared simulated-OOD 主线 | 仅记录 Git path |
| `xrd_robustness/reports/simulated_test_results.json` | tracked | 解释 checkpoint/model selection 的共享背景 | 仅记录 Git path |
| `xrd_robustness/configs/real.cnrs318.zero_shot.frozen.json` | tracked | CNRS 是独立 real-domain zero-shot 证据，不属于 RRUFF 个人模块 | 仅记录 Git path |
| `xrd_robustness/scripts/run_cnrs318_zero_shot.py` | tracked | CNRS 执行链 | 仅记录 Git path |
| `xrd_robustness/reports/CNRS_318_RESULTS.md` | tracked | 外部 real-domain 背景/证据三角验证 | 仅记录 Git path |
| `xrd_robustness/outputs/simulated_test_checkpoints/checkpoints/` | ignored；10 files / 1,561,824,960 B | RRUFF few-shot 的共同 pretrained weights | 不纳入 1 GB；记录 hashes/共享位置 |

## checkpoint 依赖断点

候选 runner `tmp/run_rruff301_confirmatory.py` 指向当前不存在的：

`xrd_robustness/outputs/v9_resnet_js_simulated_test_checkpoints/checkpoints`

现存 weights 位于：

`xrd_robustness/outputs/simulated_test_checkpoints/checkpoints`

10 个 checkpoint 的 SHA 与本地 `metadata/checkpoints.sha256` 一致，因此权重仍在，但当前 runner 的路径绑定不完整。Stage 2 如果要做可复现包，只应保存 metadata/hash 和一个经人工确认的依赖说明；不得静默改脚本或复制全部 weights。

## 共享主线边界

Yifeng 的归属覆盖 RRUFF 问题重构、设计、执行、bug audit、v2、per-class/representation 与 label-efficiency 解释；不延伸到 simulator core、Dynamic JS 方法本身、lambda=60 的主线选择、synthetic mainline 或 CNRS 独立模块。
