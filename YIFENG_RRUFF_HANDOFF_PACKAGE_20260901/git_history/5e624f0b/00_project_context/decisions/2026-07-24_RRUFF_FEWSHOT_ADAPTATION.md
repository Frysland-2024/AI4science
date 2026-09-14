# 2026-07-24：将真实谱从纯 zero-shot 验收扩展为少样本适配轴

## 决定

V9-T 保留 Dynamic/Paired ERM、JS Consistency、Residual Class Decorrelation 的模拟预训练受控比较，同时增加真实域少样本适配：

- 0-shot：不使用真实标签；
- 1-shot：每晶系 1 条真实训练谱；
- 2-shot：每晶系 2 条；
- 3-shot：每晶系 3 条。

来源语料为已经冻结组成的 RRUFF-70。模型访问前，使用确定性 SHA-256 规则将其冻结为：

- adaptation train：21 条，3/class；
- adaptation validation：14 条，2/class；
- final real test：35 条，5/class。

GTIIT 不进入主适配指标，只保留为本地仪器 supplementary case study。

## 为什么改变

此前协议把真实谱限定为一次性 zero-shot final test，目的是避免真实数据参与模拟参数、lambda、方法和 checkpoint 选择。这条红线对于模拟开发仍然正确，但它不意味着科学上不能研究少量真实标签适配。

用户重新明确了真正关心的比较：

> 在三种模拟预训练模型都使用同一批少量真实数据、同一适配目标和同一预算时，JS 或 Residual 是否仍能相对 Dynamic ERM 提供增益？

在这个问题下，真实数据提高所有方法的绝对准确率是合理目标；公平性来自三方法完全共享支持样本和适配程序，而不是要求所有模型永久保持 zero-shot。

## 方法学含义

新增问题把论文从单层的模拟到真实零样本泛化，扩展为：

```text
controlled simulated pretraining
→ zero-shot real robustness
→ label-efficient real-domain adaptation
```

这更接近标准 transfer learning 范式，也更能检验预训练表示是否具有可适配性。

## 防止事后改题的措施

本次修订发生在：

- lambda tuning 仍为 0/7；
- formal simulation runs 仍为 0/15；
- 没有正式 checkpoint；
- 没有模型访问 RRUFF-70；
- final real test 没有执行。

因此角色划分、support episodes 和统计规则可以在结果前冻结。

## 公平性冻结

1. 三个核心方法使用相同 RRUFF support episode；
2. 主适配只使用 cross-entropy，冻结 encoder、更新 classifier head；
3. 真实域不继续使用 JS/Residual 辅助损失；
4. adaptation validation 只选择适配学习率、epoch 和 checkpoint；
5. final real test 不参与任何选择；
6. 0/1/2/3-shot 全部报告，不能只保留最有利预算；
7. 所有预训练 seed 和支持 episode 全部报告。

## 未改变的边界

- 真实谱仍不能定义模拟扰动参数；
- 真实适配结果不能修改模拟 lambda 或模拟 checkpoint；
- simulated Test 必须先完成并冻结；
- final real test 仍需单独授权；
- RRUFF 谱图与数据 manifest 不提交 GitHub，只登记哈希；
- GTIIT 数据仍需标签、批次和隐私审计。

## 对项目发展叙事的意义

这是项目从“把真实数据当作最终验收”进一步走向“研究表示的可迁移性和标签效率”的转折。核心没有变成单纯追求真实准确率，而是把三种学习原则放进更完整的迁移学习流水线中比较。这个变化使 XRD 项目更接近用户希望的 AI+science：领域数据用于构造可检验的迁移问题，而不是只作为模型展示场景。
