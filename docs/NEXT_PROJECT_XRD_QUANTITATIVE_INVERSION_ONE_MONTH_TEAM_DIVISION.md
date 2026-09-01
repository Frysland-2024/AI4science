# PXRD 定量反演：一个月双人分工与工程执行方案

**日期：** 2026-09-01  
**性质：** 当前一个月版本的团队分工补充协议。  
**适用范围：** `xrd_inversion/` known-phase / single-phase / tetragonal V0。  
**与旧协议关系：** 不推翻 Week-1 已完成的 P0/P1/P2 数值 Gate；本文件只规定从现在开始的双人分工、代码边界、交接接口与四周节奏。

---

## 1. 总体分工原则

项目只保留两个核心模块：

```text
主模块（约 75–80%）
Structure–Measurement Factorized Inversion
        ↓
回答：模型能否区分“材料结构变化”和“测量/仪器变化”？

辅助模块（约 20–25%）
Forward-Physics Verification
        ↓
回答：拆出的参数是否能重新生成、交换并组合成物理上正确的 PXRD？
```

主创新属于 **structure–measurement factorization / paired physics supervision**；forward physics 不作为独立主 novelty，而作为完整、独立但次级的物理验证模块。

最简单的贡献边界：

> **主负责人负责“拆对”；协作者负责“验证拆出来以后能不能拼回物理世界”。**

---

## 2. 主负责人：Factorization 主线（约 75–80%）

### 2.1 研究问题

普通监督回归只告诉模型：

```text
(a, c, zero shift, FWHM) 应该是多少
```

主线进一步利用 simulator-known 的 2×2 intervention relation：

```text
同结构 + 不同测量
同测量 + 不同结构
```

检验 paired supervision 是否能减少 cross-talk。

### 2.2 数据设计

继续使用冻结的最小 2×2 factorial block：

\[
x_{11}=F(s_1,m_1),\quad x_{12}=F(s_1,m_2),
\]

\[
x_{21}=F(s_2,m_1),\quad x_{22}=F(s_2,m_2).
\]

其中：

- `s=(u,v)`：structure state；
- `m=(delta,w)`：measurement state。

当前有限 Pilot 继续限制在 Train split 的 32 个 conventional tetragonal parents，不扩大数据规模，直到机制 Gate 通过。

### 2.3 主比较

第一版只保留最关键的两组：

1. **Two-head supervised regression**
   - structure head: `(u,v)`
   - measurement head: `(delta,w)`
   - 只有参数监督

2. **Two-head + paired factorization supervision**
   - 架构、数据、优化器、训练预算完全相同
   - 仅增加：

\[
L_{s-inv}=\|\hat s(x_{i1})-\hat s(x_{i2})\|^2
\]

\[
L_{m-inv}=\|\hat m(x_{1j})-\hat m(x_{2j})\|^2
\]

总损失：

\[
L=L_{param}+\lambda_{pair}(L_{s-inv}+L_{m-inv}).
\]

### 2.4 主指标

主负责人负责：

- 四参数 MAE；
- `measurement -> structure` cross-talk：`E_{s<-m}`；
- `structure -> measurement` cross-talk：`E_{m<-s}`；
- own-factor response fidelity；
- 2×2 intervention response matrix；
- 三个固定 seeds；
- `GO / PARTIAL / NO-GO` 结论。

当前有限 Pilot 的核心 GO 条件仍保持：paired model 相对 two-head baseline，两种 cross-talk 均平均降低约 20%，同时参数精度与 own-factor response 不明显恶化。

---

## 3. 协作者：Forward-Physics Verification 模块（约 20–25%）

### 3.1 模块定位

协作者不重新设计 factorization 数据集、不负责 paired loss、不做 backbone 搜索，也不重新训练主 baseline。

其完整故事线为：

> **神经网络反演得到的物理参数不能只靠参数 MAE 判断可信度；因此建立 forward-diffraction verification 模块，在观测空间检查预测参数是否能够重新解释原谱，并进一步验证 factorized structure / measurement parameters 是否具有跨视图可组合性。**

### 3.2 Task A — Self reconstruction

读取主模型输出：

\[
\hat s=(\hat u,\hat v),\qquad
\hat m=(\hat\delta,\hat w)
\]

通过已有、已经通过 P0/P1/P2 审计的 forward renderer：

\[
\hat x=F(\hat s,\hat m).
\]

比较：

\[
D(\hat x,x_{target}).
\]

第一版只实现一种简单、固定、可审计的 profile mismatch，不展开复杂距离函数搜索。

### 3.3 Task B — Swap reconstruction【该模块核心】

对 2×2 factorial block：

\[
x_{11}=F(s_1,m_1),\qquad x_{22}=F(s_2,m_2).
\]

从不同视图分别取出预测因素：

\[
\hat s_{11}=\hat s(x_{11}),\qquad
\hat m_{22}=\hat m(x_{22}).
\]

重新组合：

\[
\hat x_{12}^{swap}=F(\hat s_{11},\hat m_{22}).
\]

理论目标：

\[
\hat x_{12}^{swap}\approx x_{12}=F(s_1,m_2).
\]

同理可构造：

\[
F(\hat s_{22},\hat m_{11})\approx x_{21}.
\]

该实验的意义是：

> 参数空间中的“解耦”如果是真实的，那么从不同样本提取出的 structure factor 与 measurement factor 应当能够重新组合，并在观测空间生成正确的第三种 PXRD。

因此：

- 主负责人提供 **parameter-space factorization evidence**；
- 协作者提供 **measurement-space physics evidence**。

### 3.4 Task C — Forward-loss 小消融【仅在主线 GO 后执行】

仅在 factorization Pilot 先通过 GO 后，才允许比较：

\[
L_{base}=L_{param}+L_{pair}
\]

与：

\[
L_{physics}=L_{param}+L_{pair}+\lambda_fL_{forward}.
\]

限制：

- `lambda_f` 第一版只固定一个保守值；
- 不做大规模超参数搜索；
- 不同时比较 Soft-DTW / Wasserstein / 多种复杂 profile loss；
- 不因此启动 refinement、真实谱或独立 renderer 正式 benchmark。

Task C 是可选增强，不得阻塞主项目。

---

## 4. 四周并行执行节奏

| 周次 | 主负责人（Factorization） | 协作者（Forward Physics） | 必须冻结的交接点 |
|---|---|---|---|
| **Week 1** | 构建 2×2 factorial dataset；two-head model；tiny-overfit；固定训练接口 | 将现有 `gpu_forward.py` 封装成 verification API；写 oracle / shape / decode 单测 | 冻结数据字段、参数顺序、decode 方式 |
| **Week 2** | 跑 two-head baseline vs paired factorization，3 seeds | 完成 self-reconstruction evaluator；准备 profile mismatch 与批量报告 | 主负责人交付首批 checkpoint + prediction dump |
| **Week 3** | 计算 cross-talk、own-factor response、2×2 response matrix；做 GO/NO-GO | 完成 swap reconstruction；比较 baseline 与 factorized model 的 swap error | 合并 parameter-space + measurement-space 机制证据 |
| **Week 4** | 冻结主结论、图表、报告 | 仅在主线 GO 时做 `+forward loss` 一个小消融；否则停止扩张 | 形成两个独立报告 + 一个总 summary |

---

## 5. 代码边界

不要继续向当前大型 `week1_pilot.py` 塞入 Week-2/3/4 ML 代码。

建议新增：

```text
xrd_inversion/src/xrd_inversion/

factorial_dataset.py          # 主负责人
parameterization.py           # 主负责人
models.py                     # 主负责人
factorization_losses.py       # 主负责人
factorization_metrics.py      # 主负责人

forward_verification.py       # 协作者
forward_losses.py             # 协作者；Week4 可选
```

公共 physics primitive：

```text
gpu_forward.py                # 两边调用；除非修 bug，否则不随意改
```

`independent_renderer.py` 在本一个月主线中继续保持 unopened / 不作为调参工具。

---

## 6. 必须冻结的公共接口

建议新增：

```text
xrd_inversion/contracts/factorization_interface_v1.md
```

接口至少固定：

```text
输入：
  x_obs
  x_ref
  x_diff

标签：
  theta_s = [u, v]
  theta_m = [delta, w]

标识：
  parent_id
  block_id
  structure_state_id
  measurement_state_id

模型输出：
  pred_s, pred_m = model(x)

统一 decode：
  [u,v] -> [a,c]
  w -> FWHM
```

所有参数顺序、标准化方式与单位必须在 Week 1 后冻结。

---

## 7. 主负责人向协作者的交接物

协作者不直接进入主训练脚本改逻辑；主负责人通过固定 artefact 交接：

```text
checkpoint.pt
factorial_eval_manifest.json
prediction_dump.npz
```

`prediction_dump.npz` 至少包含：

```text
x11_pred_s, x11_pred_m
x12_pred_s, x12_pred_m
x21_pred_s, x21_pred_m
x22_pred_s, x22_pred_m

ground-truth theta_s / theta_m
block_id / parent_id
```

这样 forward module 可以独立评估，不需要耦合主训练代码。

---

## 8. 最终交付物

### 主负责人

```text
xrd_inversion/reports/FACTORIZATION_PILOT_REPORT.md
```

至少包含：

- parameter MAE；
- `E_{s<-m}`；
- `E_{m<-s}`；
- own-factor response；
- 2×2 intervention response matrix；
- 三 seeds；
- GO / PARTIAL / NO-GO。

### 协作者

```text
xrd_inversion/reports/FORWARD_VERIFICATION_REPORT.md
```

至少包含：

- self reconstruction error；
- swap reconstruction error；
- baseline vs factorized model 对比；
- 若执行 Week4：`+forward loss` 小消融。

### 总结

最终故事线必须能够压缩成：

```text
Factorized inversion
        ↓
parameter-space evidence：减少 structure / measurement cross-talk
        ↓
Forward physics verification
        ↓
measurement-space evidence：拆出的因素可以重新生成与跨视图重组
```

---

## 9. 一个月内明确不做

为保证工作量不失控，本版本不做：

- 七晶系统一反演；
- unknown phase / indexing；
- 多相；
- 真实实验谱正式 benchmark；
- full Rietveld replacement；
- Transformer / PAMPT；
- backbone 大搜索；
- 大规模 `lambda_pair` / `lambda_forward` 搜索；
- Soft-DTW / Wasserstein 等多套 forward loss 比较；
- independent renderer 的结果访问与调参；
- 根据最终结果反复修改任务定义。

若 factorization Pilot 未通过 GO，则停止把 factorization 扩展为主创新；forward module 仍可作为普通 quantitative inversion 的 physics verification 工具保留。

---

## 10. 当前贡献比例的内部定位

建议内部按以下比例理解，不用于替代最终作者贡献声明：

```text
约 75–80%：
  task definition
  2×2 intervention design
  factorized inversion
  paired supervision
  training / cross-talk / mechanism analysis

约 20–25%：
  forward-physics verification
  self reconstruction
  swap reconstruction
  optional forward-loss ablation
```

这样能够同时满足：

1. 主创新和主工程链条保持集中；
2. 协作者拥有一个边界清晰、工作量受控、但可以独立讲述的完整物理验证模块。
