# 154,975 条结构库：晶系分类与划分证据

**决定日期：** 2026-11-03
**状态：** 当前结构库采用 70/15/15；项目负责人在查看逐晶系父结构数后确认保留该比例。
**用途：** 为后续 PXRD 晶系分类模型准备结构库划分；本文记录拆分依据，不代表模拟谱已生成或模型训练已启动。

## 决定与理由

沿用项目已有的 `sha256_seeded_crystal_system_stratified_random_v1` 方法，按 `crystal_system` 分层、按规范化父结构分组，随机种子为 `20260726`，比例为训练/验证/测试 `70/15/15`。

当前划分有 108,478 个训练父结构组、23,245 个验证组和 23,245 个测试组。七个晶系都覆盖在三个分区中；验证集和测试集每个晶系至少有 1,605 个父结构组。按同一代码与种子估算的 80/10/10 情景会把训练记录增加 15,496 条，但仍有 15,497 个验证组和 15,497 个测试组；目前没有 154,975 条规模的学习曲线证据证明增加训练比例会提高模型效果。因此本版本继续保持与既有方案一致的 70/15/15，后续是否调整应由预先规划的学习曲线证据决定。

## 数据粒度与总量

| 项目 | 数量 |
| --- | ---: |
| MP ID 记录 | 154,975 |
| 规范化父结构组 | 154,968 |
| 保留的历史 `formal_14060` 记录 | 14,060 |
| 新增的 MP-only ID | 140,915 |
| 历史与筛选源共有的 MP ID（在合并库中只计一次） | 13,844 |
| 筛选源中未出现、仍保留的历史 ID | 216 |

有 7 对不同 MP ID 具有相同规范化父结构指纹；每对都放在同一分区。分类计数表以下按**父结构组**统计，以匹配实际拆分单位；它不是 MP ID 行数表。

## 逐晶系父结构组数

| 晶系 | 总组数 | 训练 | 验证 | 测试 |
| --- | ---: | ---: | ---: | ---: |
| cubic | 20,411 | 14,288 | 3,062 | 3,061 |
| hexagonal | 10,704 | 7,493 | 1,605 | 1,606 |
| tetragonal | 17,352 | 12,147 | 2,603 | 2,602 |
| trigonal | 13,026 | 9,118 | 1,954 | 1,954 |
| monoclinic | 36,562 | 25,593 | 5,484 | 5,485 |
| orthorhombic | 32,591 | 22,814 | 4,889 | 4,888 |
| triclinic | 24,322 | 17,025 | 3,648 | 3,649 |
| **合计** | **154,968** | **108,478** | **23,245** | **23,245** |

## 完整性与可复核性

交付校验状态为 `passed`：全部历史 ID 与新增 MP-only ID 均在库中；154,975 个 MP ID 各出现一次；没有父结构跨分区；没有空结构或格式错误结构。历史行保留 `legacy_split` 作为原划分来源信息，原有冻结清单与结果未被改写。

本次分库文件位于外部数据目录：

`D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103`

| 文件 | SHA-256 |
| --- | --- |
| `train_structures.jsonl.gz` | `e6b8b841d7973f83ef73068ed5755ff810a35737e0a54a931207a4e6c6f2ebb6` |
| `validation_structures.jsonl.gz` | `0ccd53e1cc00ac18df816e70ca2e91385ad1017d207775893370b8e9762f5008` |
| `test_structures.jsonl.gz` | `e730a111f5b72032ca217eaf85dbc1004df37e960eecd74fe182954401dab8ef` |
| `parent_split_manifest.csv` | `1b9e62d5c4adce625e5a9ea707ed4d41067987d698179fc8f6c3da061910e340` |

Git tracks this evidence record and its checksums; the large compressed structure shards remain in the external data directory. The source is a screened Materials Project structure snapshot, not the exact SimXRD/CrystDB release. The library contains structures only, with no precomputed PXRD spectra. Simulation readiness, an independent RRUFF evaluation panel, and a compute budget remain prerequisites for formal scale training.

## Implementation and related project records

- Split implementation: [`structure_split.py`](../xrd_robustness/src/xrd_robustness/structure_split.py)
- Current project status: [`CURRENT_STATE.md`](CURRENT_STATE.md)
- Decision history: [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md)
- External delivery readme: `D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103\README.md`
- External machine-readable integrity record: `D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103\delivery_validation.json`


## 2026-11-09 execution-boundary addendum

This document establishes the source-library split only. It does **not** establish that the current `main` schema adapter can consume these JSONL shards, that the server migration loader can read their PeakTables, or that a private package matches current source code. The latest Issue #61 audit reports the current-main adapter/manifest-builder and `--records-path` gaps; the private artifacts could not be re-opened for current hash verification. Keep this source-split evidence as historical input evidence and use [the current preflight audit](ISSUE_61_V11_MINIMUM_PREFLIGHT_AUDIT_20261109.md) for readiness. #61 remains BLOCKED and #55 remains blocked; GPU smoke is **BLOCKED / NOT_RUN** until separately authorized and executed.
