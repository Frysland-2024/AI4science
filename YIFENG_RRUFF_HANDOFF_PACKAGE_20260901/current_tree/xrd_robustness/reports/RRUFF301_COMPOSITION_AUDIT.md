# RRUFF-301 Composition Audit

> 这是对现有本地 RRUFF-301 数据库的**只读描述性检查**，不是新的实验 Gate。
> 不改变 adaptation/test split，不删除样本，不读取模型预测，也不改变已经报告的 few-shot 结果。

## 1. Split integrity

- adaptation pool: **70**
- locked test: **231**
- unique RRUFF IDs: **301**
- exact RRUFF-ID overlap: **0**
- exact spectrum-SHA overlap: **0**

## 2. Metadata overlap

| 字段 | 共享唯一值 | adaptation 中涉及样本 | locked test 中涉及样本 | 跨 split 配对数 |
|---|---:|---:|---:|---:|
| `mineral_name` | 23 | 26 | 36 | 40 |
| `ideal_chemistry` | 23 | 27 | 38 | 44 |
| `measured_chemistry` | 4 | 4 | 4 | 4 |
| `space_group` | 27 | 57 | 139 | 419 |

### 共享 mineral name

- **Bastnasite-(Ce)** — adaptation: R050409, R060359; locked test: R060550, R060737
- **Axinite-(Fe)** — adaptation: R050061; locked test: R050026, R060558
- **Calcite** — adaptation: R040070; locked test: R050009, R050127
- **Chalcanthite** — adaptation: R060102; locked test: R050293, R050354
- **Chalcopyrite** — adaptation: R050208; locked test: R050222, R050559
- **Dolomite** — adaptation: R050357; locked test: R040030, R050370
- **Fluorite** — adaptation: R050045; locked test: R040099, R050046
- **Marialite** — adaptation: R040113; locked test: R060458, R060526
- **Microcline** — adaptation: R050193; locked test: R050054, R050150
- **Natrolite** — adaptation: R040102; locked test: R040112, R060561
- **Rutile** — adaptation: R060745; locked test: R050031, R050417
- **Sphalerite** — adaptation: R060005, R060636; locked test: R050005
- **Strontianite** — adaptation: R050564; locked test: R040037, R050476
- **Wulfenite** — adaptation: R050024, R050501; locked test: R050149
- **Zircon** — adaptation: R050488; locked test: R050034, R050203
- **Corundum** — adaptation: R060020; locked test: R040096
- **Dioptase** — adaptation: R050010; locked test: R040028
- **Grossular** — adaptation: R060453; locked test: R060452
- **Kurnakovite** — adaptation: R050105; locked test: R050393
- **Leucite** — adaptation: R060300; locked test: R040107
- **Mimetite** — adaptation: R040123; locked test: R050007
- **Scheelite** — adaptation: R060417; locked test: R040172
- **Topaz** — adaptation: R050200; locked test: R050405

## 3. Stored-spectrum similarity

- cross-split pairs: **16170**
- maximum Pearson correlation: **0.947785**
- maximum same-crystal-system Pearson: **0.947785**

| 阈值 | 全部跨 split pairs | 同晶系 pairs | adaptation 样本有匹配 | test 样本有匹配 |
|---|---:|---:|---:|---:|
| ≥ 0.95 | 0 | 0 | 0 | 0 |
| ≥ 0.98 | 0 | 0 | 0 | 0 |
| ≥ 0.995 | 0 | 0 | 0 | 0 |

### 最高相关的跨 split 谱图对

| Pearson | 同晶系 | adaptation | mineral | locked test | mineral |
|---:|:---:|---|---|---|---|
| 0.947785 | yes | R050564 | Strontianite | R050476 | Strontianite |
| 0.947225 | yes | R060102 | Chalcanthite | R050354 | Chalcanthite |
| 0.937991 | yes | R050045 | Fluorite | R040099 | Fluorite |
| 0.934461 | yes | R050045 | Fluorite | R050046 | Fluorite |
| 0.931048 | yes | R040102 | Natrolite | R060561 | Natrolite |
| 0.931017 | yes | R060636 | Sphalerite | R050005 | Sphalerite |
| 0.929974 | no | R060300 | Leucite | R040107 | Leucite |
| 0.928720 | yes | R040102 | Natrolite | R040112 | Natrolite |
| 0.927214 | yes | R050357 | Dolomite | R050370 | Dolomite |
| 0.920842 | yes | R040070 | Calcite | R050009 | Calcite |
| 0.918809 | yes | R050501 | Wulfenite | R050149 | Wulfenite |
| 0.910036 | yes | R050208 | Chalcopyrite | R050559 | Chalcopyrite |
| 0.908368 | yes | R050010 | Dioptase | R040028 | Dioptase |
| 0.904089 | yes | R060417 | Scheelite | R040172 | Scheelite |
| 0.903703 | yes | R040113 | Marialite | R060458 | Marialite |
| 0.884588 | yes | R050024 | Wulfenite | R050149 | Wulfenite |
| 0.877617 | yes | R050564 | Strontianite | R040037 | Strontianite |
| 0.875271 | yes | R060020 | Corundum | R040096 | Corundum |
| 0.872409 | yes | R050409 | Bastnasite-(Ce) | R060550 | Bastnasite-(Ce) |
| 0.864084 | yes | R050409 | Bastnasite-(Ce) | R060737 | Bastnasite-(Ce) |

## 4. Interpretation boundary

- 相同 mineral name / chemistry string 的存在**不等于数据泄漏**；RRUFF-301 的任务是同一实验域内的 few-shot adaptation，而不是 unseen-mineral benchmark。
- `ideal_chemistry` / `measured_chemistry` 这里只做规范化后的**精确字符串比较**，不是化学式约简、原型识别或结构等价判定。
- Pearson correlation 只检查已经存储的一维规范化谱图是否近似重复，不是结构同构性证明。
- 本报告的用途是把数据组成讲清楚；无论结果如何，都不事后修改 frozen split 或重跑模型。
