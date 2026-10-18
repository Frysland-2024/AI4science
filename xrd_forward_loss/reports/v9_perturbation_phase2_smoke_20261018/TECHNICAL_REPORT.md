# V9 扰动与 clean-reference Forward Loss 工程 Pilot

> 这是单一已知 HfCd 母结构上的模拟器工程 Pilot，不代表铁电陶瓷或真实实验谱验证。B 使用模拟器生成的 clean reference；不得解释为真实实验谱上的无监督物理重建。

## 数据与接口

- 材料：HfCd（mp-1007758），来源 split=train；共 128 个晶格参数样本，train/validation/test=90/19/19。
- CIF：未提供；从本地冻结 structure_records.jsonl 的 standardized_structure JSON 重建结构，指纹 `3372b44a22899c7f335410eb74d2f7e8f50270ef242a7fddc21af142f05cd46f`。
- 配置 SHA-256：`2801ab28d547fddd63eab21c801ec0195c2aaf6e8de69496fdb0b1a8d741a144`；数据阵列 SHA-256：`d65a946d545f0c50645c89caa380ea551bb2233836bd22fac504fc1a1ceeca3e`。逐样本 q、lattice truth、扰动参数/类型/采样 seed、结构来源与配置哈希在 `sample_records.jsonl`；profile 阵列按同一 sample_index 存于 `pilot_samples.npz`。
- 谱顺序：干净相对强度（峰值归一化）→ V9 平滑背景 → Poisson 计数和计数域 Gaussian 读出 → clip → 每谱单次 max 归一化 → log1p 变换。背景与噪声前不做归一化。原始绝对计数未建模，因此是相对计数工程模拟。
- Forward/V9 clean renderer 兼容 Gate：通过，max abs=1.04e-07，RMSE=2.12e-09。

## V9 接入范围与物理检查

- 操作 Gate 总体：通过。noise=True，smooth background=True，area-stable broadening=True，whole-pattern zero shift=True。
- Forward lattice Jacobian rank/condition：full-rank=True，condition=3.36；有限差分与 autograd Gate=通过。Loss 名称为 `simulator-supervised clean-reference forward loss`。
- March–Dollase 保持关闭：当前 pilot 不需要择优取向，且没有将随机逐峰缩放伪装成晶面择优取向。
- 扰动范围是工程压力测试范围，不是任何仪器标定范围。零点偏移和峰宽只改变输入谱，不改变 q 标签。

## 运行结果

- 本报告阶段：`phase2_add_broadening_and_zero_shift`。四格单 seed smoke 的有限损失检查：通过。Smoke 只跑 1 epoch，最多 16 个训练样本，不作为效果结论。
- 当前目录仅保存 smoke 与 Gate 记录；未执行三 seed 主 Pilot。

## 后续材料迁移条件

迁移到铁电陶瓷前，至少需要：经授权且可追溯的陶瓷结构/CIF 与相组成、反射/晶面族元数据和可信空间群、实验仪器波长/几何/标准样品零点及峰宽标定、背景和噪声统计、样品择优取向证据、适用于陶瓷的结构扰动边界、独立于参数抽样的样本级 train/validation/test 划分，以及预注册的优化预算和失败判据。需先验证 forward renderer 对真实标准谱的误差，再决定是否训练；本 HfCd 结果不能替代这些验证。
