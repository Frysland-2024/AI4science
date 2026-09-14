# PXRD RRUFF 真实域模块：协作者实际贡献与执行溯源

**日期：** 2026-09-01  
**性质：** 对 `PXRD_ROBUSTNESS_TEAM_DIVISION_80_20.md` 的事实归属补充。  
**状态：** 正式记录；不修改既有实验结果，不重写历史 Git commit。

## 1. 核心事实修正

RRUFF 真实域相关工作的实际执行并不是在 2026-09-01 才“重新切给协作者”。

实际项目历史是：

> **RRUFF zero-shot、早期 RRUFF-70，以及后续 RRUFF-301 few-shot / label-efficiency 这一整条真实域实验线，本来就是由协作者借助 DeepSeek 完成实验执行、整理和分析；其中相当一部分结果也是协作者本人在同一台共享工作电脑上完成 Git 提交 / 上传。**

但该电脑当时使用的是项目主仓库 `Frysland-2024/AI4science` 的既有 Git / GitHub 身份配置，因此历史 commit 的 author / committer 元数据可能仍显示为 `Frysland-2024`。例如 RRUFF-301 confirmatory v2 的历史 commit `24d8c851...` 在 GitHub API 中记录的 author / committer 均为 `Frysland-2024`，这反映的是该工作站上的 Git 身份与仓库认证配置，不能据此推出实际坐在电脑前执行实验、整理文件和发起上传的人是谁。

因此：

- GitHub commit / push 身份不能直接等同于科研贡献归属；
- 同一工作站、同一 Git 配置下产生的提交，不能作为区分两位实际操作者的可靠证据；
- 不应为了制造新的 GitHub 署名痕迹而重新跑一次已完成实验；
- 不应重写既有 Git 历史来伪造原始提交者；
- 后续 authorship / CRediT / 申请叙事应按实际完成的工作归属，而不是按 commit 上显示的账号归属。

## 2. 协作者真正拥有的是一条连续的真实域研究轨迹

协作者的模块不应仅被描述成“后来接手 RRUFF-301”。更准确的是：

```text
早期 RRUFF zero-shot
        ↓
暴露广域 sim-to-real 直接迁移的困难
        ↓
RRUFF-70：探索少量真实标签 / 真实域适配
        ↓
RRUFF-301：形成更完整的 K=1/2/5 few-shot benchmark
        ↓
比较 ERM-pretrained vs JS-pretrained representations
        ↓
形成 experimental label-efficiency / low-label transfer 结论
```

因此协作者的独立科学故事可以表述为：

> **从广域 zero-shot 压力测试出发，逐步将真实域问题收敛为低标签实验适配，并系统评估模拟预训练表示在 RRUFF experimental domain 上的 label efficiency。**

这比单独说“负责 RRUFF-301”更符合真实项目历史，也更完整。

### 2.1 已确认属于协作者的智力设计与研究决策

项目负责人在 2026-09-01 进一步明确：下面这些并不是“共同、待核实”或“只能从产物反推”的内容，而是**协作者本人实际提出 / 主导完成的 RRUFF 线研究设计决策**：

- 从 broad zero-shot real-domain evaluation 转向 few-shot adaptation / label-efficiency 的问题重构；
- 将 RRUFF-70 明确降级为 exploratory study，而不是继续把小样本结果包装成最终真实域结论；
- 设计 RRUFF-301 作为 preregistered confirmatory benchmark；
- 确定 K=1 / 2 / 5 的真实标签预算与对应 few-shot 评测结构；
- 采用 paired comparison 作为 ERM-pretrained 与 JS-pretrained representation 的主要比较方式；
- 设计并执行 5 pretrained seeds × 5 episode seeds 的 matched few-shot protocol；
- 将 RRUFF-301 的 primary performance 重点放在 Macro-F1、paired delta 与 label-efficiency learning curve，而不是只看单次 accuracy；
- 在发现 trigonal / hexagonal 标签问题后，作废 v1 并完成修正后的 v2 confirmatory rerun；
- 将 RRUFF-70 中出现的 monoclinic negative-transfer 现象带入 RRUFF-301 作为需复核的假设，并根据 confirmatory result 判定该现象未复现、属于小样本不稳定现象。

因此，这些内容在未来的贡献声明、申请叙事与项目回顾中，应当归入协作者的 **Conceptualization / Methodology / Investigation / Formal analysis** 范围，而不是仅仅归入“工程执行”。

同时需要维持边界：这些 RRUFF 真实域设计贡献并不自动等同于主方法 `parent provenance -> measurement equivalence -> relationship supervision` 的原创归属；主方法与 RRUFF downstream adaptation 是两条相连但不同的问题线。

## 3. 与主负责人 80% 主线的边界

主负责人仍负责：

- simulator / physical perturbation system；
- parent-level synthetic dataset governance；
- Dynamic ERM / Dynamic JS 主方法；
- `lambda_js=60` 选择与 matched simulated training；
- 5-seed simulated OOD 主结果；
- CNRS-318 zero-shot second-domain validation；
- `parent provenance -> measurement equivalence -> relationship supervision` novelty framing；
- manuscript 的核心方法学整合。

协作者真实域模块负责：

- RRUFF zero-shot 早期探索；
- 从 broad zero-shot 向 few-shot / label-efficiency 的研究问题转向；
- RRUFF-70 阶段的真实域实验与 exploratory 定位；
- RRUFF-301 preregistration 与 confirmatory design；
- RRUFF-301 adaptation / locked-test few-shot evaluation；
- K=1/2/5 label-budget experiments；
- paired-comparison protocol 与 5×5 matched execution；
- ERM-pretrained vs JS-pretrained downstream adaptation comparison；
- RRUFF-specific result aggregation / learning-curve / label-efficiency interpretation；
- v1 label issue audit、v2 rerun 与 per-class / negative-transfer follow-up analysis。

这使 80/20 切分不是事后“制造一个 20%”，而是对已有真实工作边界的正式识别。

## 4. 关于 DeepSeek 的记录原则

“使用 DeepSeek 跑实验”本身不改变人的科研贡献归属。应区分：

- AI 工具负责生成/修改代码、给出命令或辅助分析；
- 人负责提出任务、决定协议、选择和检查输入、执行实验、判断输出、修复错误、解释结果并承担科学责任。

正式贡献描述应写协作者实际完成的科研与工程工作，不把 DeepSeek 列为作者，也不把“谁敲下代码”机械等同于“谁提出或完成研究”。若未来需要更细的 CRediT 归属，应按 Conceptualization / Software / Investigation / Validation / Formal analysis / Visualization 等实际贡献逐项确认。

## 5. GitHub 记录应怎么处理

现有 RRUFF 结果文件继续保留原路径和原 Git 历史，不需要重新上传或重跑：

- `xrd_robustness/reports/rruff301_fewshot_results.json`
- `xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`
- 与 RRUFF-70 / RRUFF zero-shot 相关的历史记录与结果资产

如果希望让协作者今后在 GitHub 上也留下更容易辨认、且真实的个人维护痕迹，可以从现在开始让其使用自己的 Git identity / GitHub account 提交：

- RRUFF-specific figure scripts；
- RRUFF 模块说明 / reproduction notes；
- downstream analysis / per-class analysis；
- 论文 RRUFF subsection 的修改。

这些属于今后的真实维护记录，而不是对旧历史的补造。

## 6. 最终一句话

> **RRUFF 真实域线从 zero-shot、RRUFF-70 到 RRUFF-301，本来就是协作者实际提出问题、设计协议、借助 DeepSeek 执行实验、分析结果并逐步发展出来的工作；其中部分历史提交也是协作者本人在共享工作站上完成上传，只是由于该工作站沿用了 `Frysland-2024` 的 Git / GitHub 身份配置，commit 元数据无法区分实际操作者。项目现在做的不是“把 20% 切给他”，而是把这条已经存在的真实贡献线正式识别、命名并与主方法线分开记录。**
