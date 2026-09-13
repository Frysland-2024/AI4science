# Same-parent vs same-class JS：今晚可执行的机制消融

**日期：** 2026-09-13  
**目标：** 回答一个非常窄的问题：JS 的收益是否特异地依赖“同一母结构”关系，而不是只要两个样本属于同一晶系就可以。

## 1. 为什么这样设计

现有主实验已经证明：

`Dynamic ERM < same-parent JS consistency`

但它还没有区分两个解释：

1. **parent-specific hypothesis**：同一母结构的两个测量视图提供了额外关系监督；
2. **generic same-class hypothesis**：只要两个样本属于同一晶系，做 prediction consistency 就足够。

因此最直接的消融是比较：

`same-parent JS` vs `same-class different-parent JS`

这项实验不替换现有 ERM-vs-JS 主结果，只负责机制归因。

## 2. 公平性控制

脚本：`scripts/run_pairing_ablation.py`

两个 arm 使用：

- 相同 ResNet-18-GN；
- 相同初始化 seed；
- 相同 14,060 数据资产中的 Train / Validation；
- 相同 online perturbation；
- 相同每个 parent 的两张 view；
- 相同 CE；
- 相同 AdamW / learning rate / weight decay；
- 相同 `lambda_js=60`；
- 相同 Validation spectra；
- 相同 checkpoint-selection 指标：Validation six-single-OOD mean Macro-F1。

唯一改变的是 JS 配对：

- `same_parent_js`：`view1(A) <-> view2(A)`；
- `same_class_js`：`view1(A) <-> view2(B)`，其中 `A != B` 且两者 crystal-system label 相同。

实现上，batch 先构造同晶系的不同 parent 对；两个 parent 各自仍生成两张 view。分类 CE 完全不变。`same_class_js` 只把 second-view logits 在 pair 内交换，因此不会多看数据、不会多做 forward。

由于七晶系 Train 数量中有少数类别为奇数，每个 epoch 最多轮换省略 1 个该类 parent；这只影响不到 0.1% 的 Train parent，而且两个 arm 完全相同，因此不构成 arm 间差异。

## 3. 今晚先跑什么

在仓库根目录更新后：

```powershell
cd E:\AI4science
git pull
cd xrd_robustness
```

先只检查数据和配对，不训练：

```powershell
python scripts/run_pairing_ablation.py --dry-run --device cuda --output-root outputs/pairing_ablation_quick
```

看到 `pairing_check` 中每一对都满足：

- `different_parent: true`
- 两个 ID 的 `class` 相同

就可以启动今晚的单 seed pilot：

```powershell
python scripts/run_pairing_ablation.py --quick --device cuda --output-root outputs/pairing_ablation_quick
```

`--quick` 的定义：

- training seed = `20260711`；
- 两个 arm，各自最多 60 epochs；
- 40 epoch 后允许 early stopping；
- 每 10 epoch 在 Validation 的 in-range + 六个 single-factor OOD 上评估；
- 不访问 simulated Test。

本质上就是**两次 ResNet 训练**。墙钟时间约等于你本机“单个 60-epoch 在线 ResNet run”的两倍，再加 Validation 评估；脚本无法提前知道你当前 GPU/CPU 渲染速度，所以不虚构小时数。

## 4. 跑完看哪里

主文件：

`outputs/pairing_ablation_quick/summary.json`

最关键字段：

`parent_minus_same_class_mean_ood_macro_f1`

定义为：

`same-parent JS mean OOD Macro-F1 - same-class JS mean OOD Macro-F1`

解释：

- **明显 > 0**：支持 parent identity 提供了比一般 same-class consistency 更有价值的关系信息；
- **接近 0**：当前结果只能支持“consistency 有效”，不能证明 parent specificity；
- **< 0**：不支持 parent-specific 解释，甚至提示一般 same-class pairing 可能更有效。

同时看 `profile_delta_macro_f1`，判断差异是否主要集中在 broadening / texture 等 XRD 扰动，而不是只来自一个 profile。

## 5. 单 seed 结果能说到什么程度

今晚的 `--quick` 是**机制 pilot**，不是新的五 seed 正式主实验。

如果差异很清楚，可以说：

> 单 seed controlled ablation gives preliminary support that same-parent pairing is more effective than generic same-class pairing.

不能立刻说：

> parent identity has been definitively proven as the causal mechanism.

如果今晚看到明显差异，再决定是否跑完整五 seed：

```powershell
python scripts/run_pairing_ablation.py --full-seeds --device cuda --output-root outputs/pairing_ablation_full
```

完整版本是 **5 seeds × 2 arms = 10 次训练**，因此不建议在不知道单 seed 结果前直接全开。

## 6. 为什么不用旧 ERM 再跑第三个 arm

这个消融的因果问题不是“JS 是否优于 ERM”——那已经由主实验回答。

这里真正要隔离的是：

`same-parent pairing` vs `same-class different-parent pairing`

脚本让这两个 arm 连输入 spectra 都完全相同，只改变 JS 内的 pair identity；这比重新加一个 ERM arm 更直接，也更省今晚的计算量。

如果未来论文审稿明确要求三臂展示，再增加 matched ERM 即可。

## 7. 结果在项目中的角色

这项实验属于**机制归因补强**，不是主结果 replacement：

- 主结果仍然是 simulated OOD、RRUFF few-shot、CNRS external domain；
- pairing ablation 只回答“为什么 same-parent design 值得保留”；
- 无论结果正负都必须保留，因为两种结果都会修正项目的机制叙事。
