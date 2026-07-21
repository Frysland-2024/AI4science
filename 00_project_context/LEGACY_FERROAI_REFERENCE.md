# FerroAI 完整机器学习流水线与项目档案（2026 春）

> **用途**  
> 这是一份“项目档案 + 机器学习流水线参考手册”。  
> 它保留两件事：  
> 1. FerroAI 论文真正采用的、从文献到模型再到实验验证的完整机器学习过程；  
> 2. 你在 2026 年 2–5 月围绕 FerroAI 所做的复现、拆解、质疑与学习。  
>
> **为什么值得保留**  
> 一篇科学机器学习论文最有价值的往往不只是网络结构，而是整条流水线：
>
> ```text
> 科学问题
>   → 数据从哪里来
>   → 如何清洗与标注
>   → 如何表示输入
>   → 如何切分数据
>   → 如何训练与调参
>   → 如何评价
>   → 如何解释错误
>   → 如何做外部验证
> ```
>
> 以后你做 XRD reliability、医疗仪器、谱学、科学图像或其他 AI4Science 项目，都可以把这套逻辑当作“工厂流水线”的基础模板。

---

# 1. 证据边界：哪些是确定的，哪些仍然不完整

## 1.1 直接来自 FerroAI 论文与补充材料的内容

本档案中以下内容有论文/补充材料直接支持：

- 文献数据来源与 NLP 抽取流程；
- phase transformation（PT）dataset 的构建；
- 温度区间切分与数据增广；
- 118 维化学式向量；
- 六层 MLP、ReLU、Softmax；
- cross-entropy loss；
- weighted F1 的 10-fold cross-validation；
- 主/次超参数的搜索方式；
- Hyperband / Successive Halving；
- test confusion matrix；
- phase-diagram grid inference、SHAP、实验验证。

## 1.2 来自你当时对公开模型进行拆解的内容

下列内容来自你当时对 released model / scaler 的检查与我们保留的项目记忆：

- 公开 release 中存在 chemical scaler 与 temperature scaler；
- chemical scaler 是 PCA 类型；
- temperature scaler 是 MinMaxScaler；
- 你曾看到推理输入被压缩到约 **21 维**；
- 你拆过 chemical vector、PCA、temperature scaling、MLP、Softmax、phase-map generation；
- 你曾搭建 toy model 来理解“输入 → 训练 → 输出相图”的完整逻辑。

## 1.3 必须诚实保留的不确定性

FerroAI 的公开网页提供训练好的 Keras 模型、chemical scaler 和 temperature scaler，但没有公开完整 PT training dataset、完整训练代码、原始 NLP rule list、所有数据切分细节或完整训练配置。

所以以下问题不能被当成“已完全复现的事实”：

- 训练/验证/测试集的精确比例；
- 10-fold CV 是否采用 material-family-level / composition-family-level group split；
- 所有 NLP 规则与人工核验步骤；
- PCA 保留的精确主成分数；
- 全部 Hyperband 搜索空间；
- 最终 winning model 的每层 dropout 与 weight decay；
- 数据增强后，同一材料区间样本在不同 folds 中是否可能重叠。

这不是你“没有看懂”，而是论文公开信息本身有限。它也成为你后来关注 reproducibility、benchmark design、distribution shift 和 reliable scientific ML 的重要原因。

---

# 2. FerroAI 到底解决什么问题？

## 2.1 科学任务

输入：

- 某一铁电材料的化学组成；
- 某一温度；
- 或者一个组成–温度网格。

输出：

- 该条件下的 crystal symmetry（晶体对称性 / crystal system）；
- 将大量网格点的预测拼起来，得到 composition–temperature phase diagram。

## 2.2 具体学习任务

这是一个 **7 类分类任务**：

```text
化学组成 + 温度
        ↓
神经网络
        ↓
7 类晶体对称性之一
        ↓
在组成–温度平面扫描
        ↓
相图
```

它不是直接回归“转变温度”，而是在大量 `(composition, temperature)` 点上判断对应结构类别；相边界由类别变化的位置形成。

---

# 3. FerroAI 的完整机器学习流水线总览

```text
[科学文献]
    ↓
41,597 篇铁电相关文章
    ↓
正文 / 段落 / 图注文本抽取
    ↓
spaCy NLP 处理 + 短语识别 + rule-based information identification
    ↓
PT dataset：
化学式 + 晶体对称性序列 + 相变温度序列
    ↓
把“相变事件”转换成“有标签的温度区间样本”
    ↓
温度区间细分（augmentation factor N）
    ↓
Augmented crystal dataset：
(chemical formula, temperature) → symmetry label
    ↓
化学式编码：
118-element atomic-ratio vector
    ↓
chemical scaler / PCA + temperature MinMax scaling
    ↓
拼接模型输入
    ↓
MLP：
4 × Dense(512, ReLU) + Softmax output
    ↓
训练：
cross-entropy loss
    ↓
主超参数调优：
N、hidden layers、neurons/layer、learning rate
    ↓
10-fold CV + weighted F1
    ↓
次超参数调优：
weight decay + layer-wise dropout
Hyperband / Successive Halving
    ↓
锁定最终模型
    ↓
unseen test dataset：
confusion matrix / per-class accuracy
    ↓
composition–temperature dense grid inference
    ↓
phase diagram + SHAP interpretation
    ↓
新材料实验验证
```

---

# 4. 第一步：从文献获得训练数据

## 4.1 为什么要从论文中挖数据？

铁电相变数据不像常见的材料组成、晶体结构、formation energy 那样能直接从 Materials Project 大规模下载。

真正需要的标签是：

```text
某化学组成
在什么温度
从什么对称性
转变为什么对称性
```

这类信息常藏在论文正文、表格、图注和相图描述中。

所以 FerroAI 的第一步不是“训练神经网络”，而是：

> 先建立一个能训练神经网络的科学数据集。

这是 AI4Science 中非常典型的一件事：  
**数据基础设施常常比网络本身更难。**

## 4.2 论文中的文本挖掘流程

论文报告：

1. 通过 Elsevier 官方 API 获取约 **41,597 篇**相关研究文章；
2. 从每篇文章中提取主要文本；
3. 删除参考文献和无关部分；
4. 用 **spaCy** 处理段落与图注；
5. 抽取核心短语；
6. 通过预先定义的规则规范表达并识别关键科学信息；
7. 汇总出：
   - chemical formula；
   - crystal symmetry；
   - temperature sequence；
   - phase transformation relation。

最终形成 phase transformation dataset（PT dataset）。

## 4.3 PT dataset 长什么样？

一个概念性例子：

```text
BaTiO3
cubic at T1
tetragonal at T2
orthorhombic at T3
rhombohedral at T4
```

更抽象地说：

```text
Material / formula
+ ordered phase sequence
+ transition temperature sequence
```

论文最终报告：

- 2,838 个 phase transformations；
- 846 个 ferroelectric materials。

## 4.4 你从这里学到的 ML 重点

**ML 项目起点不是 model.py，而是 label construction。**

对科学问题来说，标签通常来自：

- 实验数据库；
- 论文文本；
- 图像/谱图标注；
- 仿真；
- 专家规则；
- 物理模型。

你以后做 XRD 项目时也一样：

```text
晶体结构数据库
+ PXRD forward simulation
+ 物理扰动定义
+ class label
```

本质上也是在构建一个可训练、可检验的数据集。

---

# 5. 第二步：把“相变事件”变成机器学习样本

## 5.1 原始相变数据不能直接喂给网络

原始数据常是：

```text
材料 A：
T = 400 K 发生 tetragonal → orthorhombic
T = 250 K 发生 orthorhombic → rhombohedral
```

但分类模型需要的是大量明确样本：

```text
(材料 A, 350 K) → orthorhombic
(材料 A, 300 K) → orthorhombic
(材料 A, 200 K) → rhombohedral
```

所以 FerroAI 做了一个非常重要的步骤：

> 把离散的 phase-transition records 转换为有标签的 composition–temperature samples。

## 5.2 温度区间标注

对于每一段相稳定区间：

```text
T_low ≤ T < T_high
```

赋予对应 crystal symmetry label。

例如：

```text
300–400 K → tetragonal
200–300 K → orthorhombic
100–200 K → rhombohedral
```

## 5.3 数据增广：不是“随便造数据”

FerroAI 的 augmentation factor 为 `N`。

对于一个温度稳定区间，作者将其均匀分成 `N + 1` 个小区间，并从边界取点，使每段稳定区都得到成比例采样。

这一步的目的不是增加一些随机噪声，而是：

- 让长温区不至于只由一个样本代表；
- 让模型能学到相区内部；
- 让 phase boundary 附近被更充分表示；
- 让相图可以由离散分类点更平滑地重建。

论文还报告：在每个 transformation temperature 附近，增加转换前后结构相关点，并使用靠近边界的温度点强化 phase-boundary representation。

## 5.4 重要方法学区分

| 类型 | FerroAI 的例子 | 核心含义 |
|---|---|---|
| 数据构造 / label expansion | 把温度区间切成多个标签点 | 把原始科学记录转成监督学习样本 |
| 数据增广（training augmentation） | 在图像中常见的裁剪、旋转、噪声等 | 扩展输入变化 |
| 物理扰动 benchmark | 你未来 XRD 中的 zero shift、broadening、noise | 测试模型在真实测量变化下是否可靠 |

FerroAI 的 `N` 更接近 **label-density / interval-sampling hyperparameter**，并不等于你 XRD 里那些 measurement perturbation 的物理幅度。

---

# 6. 第三步：化学式如何进入神经网络？

## 6.1 118 维 chemical vector

论文主文定义：

- 周期表中的元素按 atomic number 排序；
- 每种元素对应一个维度；
- 某元素在材料中出现，就填其 atomic ratio；
- 不出现则填 0。

因此一个化学式被编码为：

\[
\mathbf{c} \in \mathbb{R}^{118}
\]

概念例子：

```text
BaTiO3
Ba: 1
Ti: 1
O : 3
其他元素: 0
```

这不是“元素序号本身”，而是一个以元素为坐标轴、以化学计量比例为数值的组成向量。

## 6.2 温度如何进入模型？

温度是另一个连续变量：

\[
T \in \mathbb{R}
\]

模型最终使用：

```text
chemical representation + scaled temperature
```

来预测晶体对称性。

## 6.3 公开 release 进一步告诉了我们什么？

FerroAI 的公开 Hugging Face release 里有：

```text
FerroAI_model.keras
FerroAI_cscaler.pkl
FerroAI_tscaler.pkl
```

文件元数据显示：

- `FerroAI_cscaler.pkl` 使用 `sklearn.decomposition.PCA`；
- `FerroAI_tscaler.pkl` 使用 `sklearn.preprocessing.MinMaxScaler`。

这说明在实际 release inference pipeline 中，原始 chemical vector 还经过了 PCA 压缩，而温度经过 Min–Max scaling。

## 6.4 你当时拆出来的 21 维输入

你当时对公开模型进行检查时，曾记录到模型输入约为 **21 dimensions**。

在逻辑上，它很可能对应：

```text
118-dimensional raw chemical vector
        ↓
PCA
        ↓
约 20-dimensional chemical embedding
        +
1 scaled temperature
        ↓
21-dimensional model input
```

但必须保留一句严谨说明：

> 论文主文明确写了 118 维原始 chemical vector；公开文件明确显示 PCA 与 temperature scaler 的存在；但论文并没有在主文完整公开 PCA 的保留维度和每一步的训练代码。因此“20 + 1 = 21”是基于 release inspection 的合理重建，不应写成论文已完整明示的细节。

这正好也是你当时研究过程中发现的一个很真实的问题：

> **论文的概念流程、公开模型的实际 inference pipeline、完整 training protocol，三者未必完全透明地对齐。**

---

# 7. 第四步：模型结构

## 7.1 架构

论文中的最终网络是一个 MLP（多层感知机）：

```text
Input
  ↓
Dense(512) + ReLU
  ↓
Dense(512) + ReLU
  ↓
Dense(512) + ReLU
  ↓
Dense(512) + ReLU
  ↓
Output + Softmax
```

论文表格将其描述为：

- input layer；
- 4 个 512-neuron dense hidden layers；
- output layer；
- hidden activation = ReLU；
- output activation = Softmax。

模型总参数量：**811,015**。

## 7.2 ReLU 在干什么？

\[
\mathrm{ReLU}(x)=\max(0,x)
\]

它让网络能学习非线性关系。

没有激活函数，多个 dense layers 叠起来本质仍近似一个大线性映射；有 ReLU 后，模型才能学习复杂的 composition–temperature → phase relation。

## 7.3 Softmax 在干什么？

Softmax 把输出转换为七个类别的概率分布：

\[
p_k=\frac{e^{z_k}}{\sum_{j=1}^{7}e^{z_j}}
\]

模型输出类似：

```text
cubic        0.05
tetragonal   0.80
orthorhombic 0.10
rhombohedral 0.05
...
```

最后通常取最大概率类别：

```text
argmax(Softmax output)
```

作为该 `(composition, temperature)` 点的预测晶体对称性。

## 7.4 一个必须记住的提醒

Softmax probability 表示：

> 在这个训练数据和模型内部，哪个类别更被偏好。

它不自动等于：

> 这个类别在真实物理世界中有 80% 的概率正确。

这叫 **calibration / uncertainty** 问题。  
它也是你后来从“模型能画图”转向“模型是否可靠”的思想起点之一。

---

# 8. 第五步：训练时模型到底在优化什么？

## 8.1 Cross-entropy loss

FerroAI final training 使用 cross-entropy loss：

\[
L_{\mathrm{CE}}
=
-\sum_{k=1}^{7} y_k \log p_k
\]

其中：

- \(y_k\)：真实标签的 one-hot 编码；
- \(p_k\)：Softmax 输出概率。

训练目标：

```text
让真实类别的概率更高
让错误类别的概率更低
让 cross-entropy 越来越小
```

论文用 training curve 展示 cross-entropy 随 epoch 下降。

## 8.2 Optimizer、batch size、epoch

论文主文和补充材料在公开范围内没有完整给出所有 optimizer、batch size、epoch、scheduler 等细节。

这在复现上会形成一个问题：

```text
论文结构知道了
loss 知道了
scaler 知道了
但所有训练细节未完全公开
```

所以你当时无法做到“从零精确重训原模型”，是合理的，不是能力问题。

---

# 9. 第六步：超参数检验到底是什么？

这正是你刚才问的核心。

## 9.1 超参数不是训练自己学出来的参数

| 类别 | 例子 | 谁决定？ |
|---|---|---|
| 模型参数 | dense layer 的 weights、biases | 训练时通过反向传播学出来 |
| 超参数 | learning rate、层数、每层 neurons、dropout、weight decay、augmentation factor | 人在训练前或训练外部选择 |

因此：

```text
learning rate = 超参数
hidden layers = 超参数
neurons per layer = 超参数
dropout = 超参数
weight decay = 超参数
augmentation factor N = 超参数
```

## 9.2 FerroAI 的主超参数调优

论文使用 controlled-variable method（控制变量法）依次考察：

1. augmentation factor；
2. number of hidden layers；
3. neurons per layer；
4. learning rate。

这里的逻辑是：

```text
先固定其他设置
只改变一个关键超参数
看评价指标是否更好
```

例如：

```text
N = 1, 2, 3, 4, ...
        ↓
分别训练/验证
        ↓
比较 weighted F1
        ↓
选最优 N
```

## 9.3 为什么用 weighted F1？

FerroAI 的七类 crystal systems 样本数量不平衡。

若只用 accuracy：

```text
多数类预测得好
少数类预测得差
总体准确率也可能看起来很高
```

Weighted F1 会按各类样本量加权，综合 precision 和 recall：

\[
F1_k
=
\frac{2\cdot \mathrm{precision}_k \cdot \mathrm{recall}_k}
{\mathrm{precision}_k+\mathrm{recall}_k}
\]

\[
F1_{\mathrm{weighted}}
=
\sum_{k=1}^{K}
\frac{n_k}{N}
F1_k
\]

其中：

- \(n_k\)：第 \(k\) 类样本数；
- \(N\)：总样本数；
- \(F1_k\)：该类的 F1。

论文把 weighted F1 当成主要 architecture/primary-hyperparameter selection metric。

## 9.4 10-fold cross-validation 在干什么？

它不是“训练十次取最高分”。

而是：

```text
数据切成 10 份
    ↓
第 1 次：第 1 份验证，其余训练
第 2 次：第 2 份验证，其余训练
...
第 10 次：第 10 份验证，其余训练
    ↓
得到 10 个 weighted F1
    ↓
报告 mean ± standard deviation
```

其作用：

- 不让某一次偶然切分决定结论；
- 同时看平均性能与稳定性；
- 在有限数据下更充分利用样本。

论文对 primary hyperparameters 报告 10-fold CV 的 weighted F1 mean 和 standard deviation。

## 9.5 FerroAI 的 learning rate 结论

补充材料报告：

```text
learning rate = 10^-2
```

在其比较中显著提升模型表现，因此用于最终训练。

重要理解：

> 这不是“所有材料 ML 都应该用 10^-2”。  
> 它只是在 FerroAI 的数据、网络、scaler、loss 和训练设定下，通过验证比较得到的较优值。

---

# 10. 第七步：次超参数——Hyperband 与 Successive Halving

## 10.1 次超参数是什么？

FerroAI 将这些视为 secondary hyperparameters：

- weight decay coefficient；
- dropout rate for each layer。

## 10.2 Weight decay 的意思

weight decay 也常被理解为 L2 regularization：

\[
L_{\mathrm{total}}
=
L_{\mathrm{CE}}
+
\lambda_{\mathrm{wd}}\|\theta\|_2^2
\]

目的：

- 防止权重无限增大；
- 降低过拟合风险；
- 让模型更平滑。

注意：

> 这里的 \(\lambda_{\mathrm{wd}}\) 是 weight-decay strength。  
> 你未来 consistency regularization 的 \(\lambda_{\mathrm{cons}}\) 是 consistency-loss weight。  
> 两者都叫 loss weight，但物理/算法含义不同。

## 10.3 Dropout 的意思

训练时随机屏蔽一部分神经元：

```text
一些 neuron 临时置零
        ↓
模型不能过分依赖少数固定连接
        ↓
降低过拟合
```

不同 hidden layers 可设置不同 dropout rates。

## 10.4 为什么不用暴力网格搜索？

若每层 dropout、每层 weight decay 都有多个候选值，组合数会爆炸。

FerroAI 使用：

- **Hyperband**；
- 其内部的 **Successive Halving** 策略。

简化理解：

```text
先让很多组合跑少量训练
        ↓
淘汰表现差的组合
        ↓
把更多计算预算给表现好的少数组合
        ↓
继续淘汰
        ↓
得到 winning configuration
```

论文报告：

- 测试了 200+ 个 secondary-hyperparameter combinations；
- 选择准确率最高的配置用于最终训练；
- 多组 top-performing settings 得到相近结果，作者据此认为模型对这些次超参数相对稳健。

补充材料还列出了两个不同的 top-performing combinations（TP1 / TP2），说明不同 layer-wise L2/dropout 配置也能收敛并得到相近预测表现。

---

# 11. 第八步：最终训练、测试与评价

## 11.1 这里有三个不同层次，千万不要混

| 阶段 | FerroAI 用什么 | 目的 |
|---|---|---|
| 训练 | cross-entropy loss | 更新模型 weights |
| 调参 | weighted F1 + 10-fold CV | 选择架构与主超参数 |
| 最终 test | confusion matrix / class accuracy | 评估没有用于训练的 test dataset |

这三件事不能混为“模型分数”。

## 11.2 最终测试

论文对未用于训练的 test dataset 计算 confusion matrix。

confusion matrix 可以告诉你：

```text
真实 tetragonal
有多少预测为 tetragonal
有多少被误判为 cubic
有多少被误判为 orthorhombic
...
```

论文报告总体准确率超过 80%，并指出：

- cubic、rhombohedral 的预测较好；
- tetragonal 与 orthorhombic 会有一定混淆；
- triclinic 样本很少，即使准确率高也应谨慎解释。

这是一个很值得记住的科研习惯：

> 少数类即使 test accuracy 很高，也不等于结论可靠；你还必须看样本量。

---

# 12. 第九步：从单点分类到连续相图

训练完成后，FerroAI 做的不是只给一个样本预测类别，而是：

```text
固定一个材料 family
    ↓
扫描 composition = 0.00, 0.01, 0.02, ...
    ↓
扫描 temperature = 1 K increments
    ↓
每个网格点输入模型
    ↓
得到 symmetry label
    ↓
把所有标签着色画成 phase diagram
```

论文报告：

- composition resolution = 0.01 at.%；
- temperature resolution = 1 K；
- 一张高分辨相图通常可在普通笔记本上 20 秒内完成。

这一步的 ML 本质并不神秘：

> 把一个分类器反复应用到二维输入网格上，再把类别变化边界可视化。

---

# 13. 第十步：解释与外部验证

## 13.1 SHAP：模型到底在看什么？

FerroAI 使用 SHAP 分析元素特征对 cubic / tetragonal prediction 的贡献。

这是一个解释模块：

```text
模型预测一个类别
        ↓
问：哪些输入特征推动它往这个类别走？
        ↓
SHAP 给出各元素特征的重要性 / 方向
```

论文指出 Ti、Nb 等 B-site 元素对某些对称性预测较重要。

## 13.2 实验验证：真正的 scientific closure

论文并没有停在 test score。

它还：

1. 用 FerroAI 预测新的 BCeZrT-xBCT 与 BZrHfT-xBCT 系统；
2. 找到预测 MPB；
3. 合成样品；
4. 测 DSC / dielectric constant；
5. 将实验转变温度覆盖到预测相图上；
6. 比较实验和模型的相边界是否一致。

这就是最完整的科学机器学习闭环：

```text
文献数据训练
        ↓
模型预测新系统
        ↓
实验测量
        ↓
外部验证
        ↓
回到材料发现
```

---

# 14. 你当时真正做了什么？

你不是只“读了一篇论文”。

## 14.1 你做的是模型机制拆解

你曾实际追踪：

- 输入 chemical formula 如何变为 vector；
- temperature 如何缩放；
- PCA 在何处进入；
- 21-dimensional inference input 的逻辑；
- MLP 和 Softmax 如何输出晶体对称性；
- 如何通过 composition–temperature sweep 生相图；
- 模型哪里可能误判或出现 decision collapse；
- 训练、推理、评价各自是什么。

这是 **reverse-engineering a published scientific ML pipeline**。

## 14.2 你搭过 toy model

你用一个 toy model 学会了：

```text
输入
    → 网络
    → loss
    → train
    → predict
    → plot
```

这件事很重要，因为它把你从：

```text
“我知道论文里有神经网络”
```

推进到了：

```text
“我知道一条 supervised ML pipeline 是如何真正跑起来的”
```

## 14.3 你发现了复现与验证的边界

你最后意识到：

- 有 release model，不等于有完整可复现研究；
- 有 scaler，不等于能重建 training data；
- 有 test score，不等于知道 split 是否足够严格；
- 有相图输出，不等于能判断其可靠性；
- 没有完整 data/protocol，就很难做强的 independent audit。

这并不是“项目没有产出”。

这是你第一次真正看见：

> 科学机器学习里，**数据来源、标签构造、split protocol、验证对象和公开程度**，和网络结构同等重要。

---

# 15. FerroAI 流水线：你未来项目可直接复用的模板

下面是你可以带到 XRD、SEM、光谱、医疗仪器或其他 AI4Science 任务中的通用版本。

## Stage 0：科学问题

```text
我要预测什么？
这个量在真实科学上为什么重要？
什么条件改变时，标签应该改变 / 不应该改变？
```

FerroAI：

```text
composition + temperature → crystal symmetry
```

XRD：

```text
PXRD pattern → crystal symmetry
```

你的 reliability 主线：

```text
同一结构在标签保持的测量扰动下
预测应保持稳定
```

---

## Stage 1：数据来源与样本单位

```text
数据从哪里来？
一个样本到底是什么？
标签来源是什么？
```

FerroAI：

```text
论文文本
→ phase transition record
→ (formula, temperature) sample
```

XRD：

```text
crystal structure
→ simulated PXRD pattern
→ symmetry label
```

---

## Stage 2：标签构造

```text
标签是否可信？
边界样本如何定义？
标签是否会因测量条件变化而改变？
```

FerroAI：

```text
温度区间 → symmetry label
```

XRD：

```text
crystal structure → crystal system / space group
```

你的 XRD 项目最关键的额外问题：

```text
zero shift / broadening / noise / background
在多大范围内仍是 label-preserving？
```

---

## Stage 3：输入表示

```text
原始科学对象如何变成数值？
模型到底看见了什么？
是否丢失了关键物理信息？
```

FerroAI：

```text
formula → 118 vector → PCA embedding
temperature → MinMax scaling
```

XRD：

```text
1D intensity sequence
possibly normalized / aligned / encoded
```

---

## Stage 4：数据切分

```text
训练和测试是否真正独立？
同一家族 / 同一材料 / 同一结构的近邻样本会不会泄漏？
```

FerroAI 论文报告：

```text
10-fold CV + unseen test dataset
```

但未完整公开：

```text
是否 GroupKFold？
是否 material-family-disjoint？
增广区间样本如何避免跨 split？
```

你未来 XRD 的改进版：

```text
structure-disjoint train / validation / test
```

这比随机 sample split 更严谨。

---

## Stage 5：baseline

```text
先问：最简单可行方法能做到多少？
```

FerroAI：

```text
MLP phase classifier
```

XRD：

```text
clean 1D-CNN / simple sequence model
```

---

## Stage 6：模型训练

```text
input
→ model
→ prediction
→ loss
→ backpropagation
→ parameter update
```

FerroAI：

```text
MLP
+ Softmax
+ cross entropy
```

XRD：

```text
1D CNN / transformer
+ cross entropy
```

---

## Stage 7：超参数调优

```text
什么由物理决定？
什么可以通过 validation 调？
```

FerroAI：

```text
N / layers / neurons / learning rate
→ weighted F1 CV
dropout / weight decay
→ Hyperband
```

XRD：

```text
learning rate / batch size / architecture / lambda
→ validation tuning
```

而下面这类不能只因为分数高就随意定：

```text
zero shift magnitude
broadening range
noise level
background amplitude
```

它们应优先由文献、仪器规格和真实数据统计锚定。

---

## Stage 8：最终测试

```text
一旦方案锁定，test set 只用于最终评价。
```

不要：

```text
在 test set 上反复调超参数
```

因为这会让 test set 变成隐形 validation set。

---

## Stage 9：错误分析与解释

```text
哪些类最容易错？
错在什么科学区域？
模型是否依赖不合理 feature？
```

FerroAI：

```text
confusion matrix
+ SHAP
```

XRD：

```text
per-class Macro-F1
+ condition-wise error
+ worst-condition accuracy
+ calibration
```

---

## Stage 10：外部验证

```text
模型在真正没见过的科学数据上是否仍有用？
```

FerroAI：

```text
合成新材料
+ DSC / dielectric test
```

XRD：

```text
real XRD validation
```

---

# 16. FerroAI 与你当前 XRD 项目的关系

## 16.1 FerroAI 给你的，是工程骨架

```text
data
→ label
→ representation
→ split
→ baseline
→ training
→ tuning
→ evaluation
→ scientific validation
```

## 16.2 你的 XRD 项目新增的是可靠性问题

FerroAI 重点问：

```text
能不能从 composition + temperature 预测 phase?
```

你的 XRD 项目重点问：

```text
同一结构在合理 measurement perturbation 下，
模型能不能保持可靠？
```

因此你的新增模块是：

```text
physical perturbation design
+ OOD / measurement-shift evaluation
+ consistency regularization
+ structure-disjoint protocol
+ real XRD external validation
```

这不是“换一个材料题目”，而是在同一个完整机器学习流水线上，把问题推进到：

> **科学测量条件变化时，模型是否仍然可信？**

---

# 17. 你以后做任何 ML 项目的最小检查表

```text
[ ] 科学问题写清楚了吗？
[ ] 一个样本是什么？
[ ] 标签从哪里来？
[ ] 输入表示是否合理？
[ ] 训练、验证、测试是否真正独立？
[ ] 是否有 baseline？
[ ] 超参数是否只在 validation 上调？
[ ] test set 是否只用一次？
[ ] 指标是否适合类别不平衡？
[ ] 是否分析每类错误，而不只报告平均分？
[ ] 数据扰动是否有科学/物理依据？
[ ] 是否有 external validation？
[ ] 代码、数据、scaler、split、seed 是否足以复现？
```

---

# 18. 最重要的个人结论

FerroAI 对你的价值，不是“你以后要照着做一个 4×512 MLP”。

真正的价值是：

> 你第一次看见了一项 AI4Science 研究如何把文献、NLP、科学标签、数据构造、向量表示、神经网络、损失函数、超参数调优、测试、解释与实验验证串成一条生产线。

而你后来继续往前走了一步：

> 你开始追问：这条生产线是否透明？训练和测试是否独立？数据构造会不会导致泄漏？模型面对真实测量变化是否仍可靠？

这就是 FerroAI 到 XRD reliability 的真正思想演化。

---

# 19. 参考来源

1. Zhang, C. & Chen, X. **FerroAI: a deep learning model for predicting phase diagrams of ferroelectric materials.** *npj Computational Materials* 11, 282 (2025).  
   DOI: https://doi.org/10.1038/s41524-025-01778-0

2. FerroAI Supplementary Materials.  
   https://static-content.springer.com/esm/art%3A10.1038%2Fs41524-025-01778-0/MediaObjects/41524_2025_1778_MOESM1_ESM.pdf

3. FerroAI public model release and scalers.  
   https://huggingface.co/FerroAI/FerroAI
