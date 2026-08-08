# AI4Science 本地工作区

本仓库是 `E:/AI4science` 的 GitHub 同步入口。当前成熟主线位于 `xrd_robustness/`，研究版本为 **V9-T / JS Consistency for robust PXRD learning**。

## 当前状态（2026-08-08）

项目已经从 **experiment-building** 切换到 **evidence freeze → manuscript building**。

当前论文级主问题已经关闭：

> 在线 PXRD 模拟器除了持续生成物理扰动样本，能否利用其保留的 parent-structure provenance，把“同一晶体的不同测量视图”转化为 measurement-equivalence supervision，并在相同数据暴露下比 Dynamic ERM 获得更好的鲁棒性与实验域少样本适配效率？

### 冻结方法

- backbone：ResNet-18-GN；
- baseline：Dynamic ERM；
- selected method：Dynamic JS Consistency；
- `lambda_js = 60`；
- parent-structure split：Train 9,842 / Validation 2,109 / Test 2,109；
- Residual-v1、V10、PAMPT 等均保留为历史/未来研究模块，不进入当前论文主线。

### 核心模拟证据

五组 paired seeds、十次 Validation replication：

- mean single-factor OOD Macro-F1 Δ = **+0.046569**；
- paired-bootstrap 95% interval = `[0.038145, 0.052834]`；
- 五组 paired seeds 的 OOD delta 全部为正；
- in-range Macro-F1 paired mean Δ = **+0.027991**。

冻结 simulated Test 独立确认：

- mean five-pair OOD Macro-F1 Δ = **+0.054600**；
- paired-bootstrap 95% interval = `[+0.048944, +0.060255]`；
- 五组 paired OOD delta 全部为正。

### 当前最强真实域确认性证据：RRUFF-301 v2

RRUFF-301 的 confirmatory v2 使用：

- 301 条实验 RRUFF PXRD；
- 70 条 adaptation pool（10/class）；
- 231 条 locked test（33/class）；
- K = 1 / 2 / 5；
- 5 个 pretraining seeds × 5 个 episode seeds；
- frozen convolutional backbone + trainable projection/head。

Macro-F1 paired mean Δ（JS − ERM）：

| K | ΔMacro-F1 | Positive pairs |
|---:|---:|---:|
| 1 | **+0.0433** | 21/25 |
| 2 | **+0.0460** | 23/25 |
| 5 | **+0.0545** | 24/25 |

合计 **68/75 paired comparisons 为正**。

RRUFF-70 现明确降级为 exploratory evidence；RRUFF-301 v2 是当前论文的真实域 confirmatory evidence。RRUFF-301 v1 因 trigonal/hexagonal 标签构建 bug 被作废用于确认性结论，bug、修复与完整重跑均保存在 audit trail 中。

## Evidence freeze

论文证据层级、允许主张、图表冻结和新增实验边界见：

- [`00_project_context/EVIDENCE_FREEZE_V1_20260808.md`](00_project_context/EVIDENCE_FREEZE_V1_20260808.md)

冻结的四张主图：

1. method / simulator provenance / ERM vs JS；
2. simulated Validation + locked Test paired effects；
3. RRUFF-301 K=1/2/5 paired few-shot；
4. per-class + fix/break/confidence diagnostic。

Calibration（ECE / NLL / Brier / confidence distributions）默认进入 Supplementary。

## 写作入口

- 论文初稿：[`xrd_robustness/MANUSCRIPT_DRAFT_V1_20260808.md`](xrd_robustness/MANUSCRIPT_DRAFT_V1_20260808.md)
- 申请用研究叙事：[`00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`](00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md)
- 项目历史：[`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md)

## RRUFF-301 权威结果

commit `24d8c8511bdea9df8b52cdf779b04420bebffafc`：

- [`xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md`](xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md)
- [`xrd_robustness/reports/rruff301_representation_analysis_20260807.md`](xrd_robustness/reports/rruff301_representation_analysis_20260807.md)
- [`xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md`](xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md)

Calibration commit `a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`：

- `outputs/calibration_metrics.json`
- `outputs/calibration_report.html`

## 权威入口

| 入口 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前科学状态、边界与下一步 |
| [`00_project_context/EVIDENCE_FREEZE_V1_20260808.md`](00_project_context/EVIDENCE_FREEZE_V1_20260808.md) | 当前论文证据层级、图表与 claim boundary |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 当前工程/写作交接 |
| [`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md) | 从 FerroAI 到当前 XRD 项目的完整研究演变 |
| [`AGENTS.md`](AGENTS.md) | Codex/GPT 仓库工作规范 |

## 当前默认动作

**不再默认启动训练。**

下一阶段是：

1. 从现有 artifacts 生成四张论文核心图；
2. 按冻结配置和审计报告写 Methods；
3. 用现有结果写 Results / Discussion / Limitations；
4. 整理 literature-backed Introduction；
5. 同步完善 application-ready research narrative。

只有当论文写作或外部 review 暴露出一个明确、 reviewer-critical、无法由现有证据回答的问题时，才允许提出新的、预先命名的补充实验。不得重新打开 `lambda_js`、排除 seed、重跑 frozen Test 或根据结果修改当前确认性结论。
