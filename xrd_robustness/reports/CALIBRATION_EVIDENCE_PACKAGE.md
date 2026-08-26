# Calibration / probabilistic reliability evidence package

**Date:** 2026-08-27  
**Purpose:** compact evidence map for group meeting, application materials, manuscript drafting, and internal scientific audit.

## One-sentence conclusion

> **Under the frozen PXRD evaluation protocol, same-parent JS consistency improves classification robustness together with probabilistic reliability: ECE and multiclass Brier improve in all 180 matched simulated-Test conditions, NLL improves in 176/180, and CNRS-318 shows the same ECE/NLL/Brier direction in all five matched training seeds.**

## What changed scientifically

The project originally noticed an unusually consistent ECE reduction in already frozen outputs. At that stage, ECE alone was insufficient because lower ECE could reflect generic confidence shrinkage.

The follow-up audit therefore tested two proper scoring rules, NLL and multiclass Brier, while also checking classification performance, mean confidence, entropy, and reliability diagrams.

The result passed the intended qualitative gate:

- ECE improves broadly;
- NLL improves broadly;
- Brier improves broadly;
- Macro-F1 and accuracy are not sacrificed;
- CNRS shows the same probability-level direction.

This upgrades the finding from **“lower ECE”** to **“improved probabilistic reliability under the evaluated shifts.”**

It does not upgrade JS into a dedicated calibration algorithm and does not prove the underlying mechanism.

## Canonical numerical evidence

### Simulated Test — 180 matched evaluation conditions

| Quantity | Dynamic ERM | JS Consistency | Δ JS−ERM | Direction count |
|---|---:|---:|---:|---:|
| Macro-F1 | 0.618282 | **0.671078** | **+0.052796** | 176 / 180 better |
| Accuracy | 0.618242 | **0.672075** | **+0.053833** | 179 / 180 better |
| ECE ↓ | 0.289934 | **0.204461** | **−0.085473** | **180 / 180 better** |
| NLL ↓ | 2.667772 | **1.632070** | **−1.035702** | 176 / 180 better |
| Brier ↓ | 0.648412 | **0.518434** | **−0.129978** | **180 / 180 better** |
| Mean confidence | 0.907905 | 0.876093 | −0.031811 | lower in 151 / 180 |
| Mean entropy | 0.235102 | 0.319464 | +0.084363 | higher in 152 / 180 |

Approximate relative changes in the condition-averaged metrics:

- ECE: **−29.5%**;
- NLL: **−38.8%**;
- Brier: **−20.0%**;
- Macro-F1: **+8.5%**;
- Accuracy: **+8.7%**.

The strongest consistency facts are:

- ECE: `180/180` matched conditions favor JS;
- Brier: `180/180` favor JS;
- NLL: `176/180` favor JS;
- accuracy: `179/180` favor JS;
- Macro-F1: `176/180` favor JS.

The worst-direction ECE and Brier differences are still favorable to JS:

- maximum ΔECE = `−0.0128818`;
- maximum ΔBrier = `−0.0148692`.

NLL has four opposite-direction conditions, so the evidence is strong but heterogeneous rather than literally unanimous across every probability metric.

### CNRS-318 zero-shot — five matched training seeds

| Quantity | Dynamic ERM pooled | JS pooled | Δ JS−ERM | Seed direction |
|---|---:|---:|---:|---:|
| Macro-F1 | 0.191176 | **0.209119** | **+0.017943** | **5 / 5 better** |
| Accuracy | 0.200000 | 0.210063 | +0.010063 | 4 / 5 better |
| ECE ↓ | 0.682570 | **0.612420** | **−0.070150** | **5 / 5 better** |
| NLL ↓ | 8.319988 | **6.118566** | **−2.201422** | **5 / 5 better** |
| Brier ↓ | 1.433841 | **1.315606** | **−0.118235** | **5 / 5 better** |
| Mean confidence | 0.882570 | 0.822483 | −0.060087 | 5 / 5 lower |
| Mean entropy | 0.289702 | 0.441971 | +0.152269 | 5 / 5 higher |

CNRS is therefore a useful external-domain directional replication of the probability-level effect.

The absolute values remain poor: JS still has pooled confidence around `0.822` against accuracy around `0.210`, with ECE `0.612`. This evidence supports **relative improvement**, not successful absolute calibration of the experimental domain.

## Evidence-file map

| Claim / check | Canonical file |
|---|---|
| Overall status, means, paired sign counts | `outputs/calibration_analysis/summary.json` |
| Compact result table and reading rule | `outputs/calibration_analysis/REPORT.md` |
| Every simulated method-level evaluation | `outputs/calibration_analysis/simulated_metrics.csv` |
| Every one of the 180 matched simulated ERM-JS comparisons | `outputs/calibration_analysis/simulated_paired.csv` |
| CNRS per-seed method metrics | `outputs/calibration_analysis/cnrs_metrics.csv` |
| Five matched CNRS seed comparisons | `outputs/calibration_analysis/cnrs_paired.csv` |
| Simulated descriptive reliability plot | `outputs/calibration_analysis/simulated_single_factor_ood_reliability.png` |
| CNRS descriptive reliability plot | `outputs/calibration_analysis/cnrs318_reliability.png` |
| Metric computation and frozen forward-inference audit code | `scripts/analyze_calibration.py` |
| Full scientific interpretation and limits | `reports/CALIBRATION_ANALYSIS.md` |

## Provenance and protocol safeguards

1. Main models, checkpoints, `lambda_js`, training seeds, and evaluation profiles were frozen before this secondary analysis.
2. Calibration/reliability metrics were not used to select a model or checkpoint.
3. Simulated per-sample probabilities were regenerated only by forward inference from the frozen checkpoints on the frozen simulated-Test panel/cache when needed.
4. CNRS probability predictions were read from the already generated zero-shot prediction file; CNRS labels were not used for adaptation or calibration fitting.
5. No temperature scaling or target-domain calibration was fit.
6. The 180 simulated rows are matched repeated evaluation conditions, not 180 independent experiments.
7. The five CNRS pairs arise from five matched training seeds on one external dataset, not five independent datasets.
8. The original local `raw_results.json` was not present for direct per-condition legacy-ECE cross-check; `summary.json` records zero such comparisons. The committed completed audit is therefore the canonical evidence set.

## Claim ladder

### Safe strong claim

> **Consistency regularization improves both robustness and probabilistic reliability under the evaluated PXRD measurement shifts.**

Why this is supported:

- classification metrics increase on average;
- ECE and Brier improve in 180/180 simulated matched conditions;
- NLL improves in 176/180;
- CNRS shows ECE/NLL/Brier improvement in 5/5 matched training seeds.

### Safe mechanistic hypothesis

> Same-parent consistency may smooth probability responses along legal measurement-variation directions and reduce view-specific over-confidence.

This is plausible from the objective and observed behavior, but remains a hypothesis because the present study does not causally isolate the mechanism.

### Claims to avoid

- “JS is a calibration algorithm.”
- “JS proves an implicit calibration regularizer.”
- “All 180 independent experiments succeeded.”
- “CNRS is now calibrated.”
- “Consistency solves Sim-to-Real.”
- “Lower confidence itself proves better calibration.”

## Presentation-ready evidence

### Minimum group-meeting slide

Use one table or grouped graphic containing:

- Simulated: Macro-F1 `+0.0528`, ECE `−0.0855`, NLL `−1.0357`, Brier `−0.1300`;
- sign counts: ECE `180/180`, Brier `180/180`, NLL `176/180`;
- CNRS: ECE `0.6826 -> 0.6124`, NLL `8.3200 -> 6.1186`, Brier `1.4338 -> 1.3156`, all `5/5` seeds in the better direction;
- one reliability diagram as visual support.

Suggested slide title:

> **同源一致性不仅提高鲁棒性，也改善预测概率可靠性**

Suggested one-line takeaway:

> **在冻结测试协议下，JS 同时提高分类表现并降低 ECE/NLL/Brier；该概率层面的改善在 CNRS 外部实验域也保持一致方向。**

### Application / interview version

> 在主实验完成后，我重新检查冻结预测结果，发现一致性训练的模型不仅在 OOD 分类上更稳，而且 ECE 在 180 个匹配测试条件中全部下降。为了排除“只是把置信度整体压低”的解释，我进一步计算了 NLL 和多分类 Brier：Brier 在 180/180 条件中改善，NLL 在 176/180 中改善，同时 Macro-F1 和 Accuracy 继续提高；CNRS 实验域上的五个训练种子也全部呈现 ECE/NLL/Brier 同向改善。这个过程把项目从单纯追求准确率推进到了对科学测量模型“预测是否可信”的讨论。

## Current evidence hierarchy in the XRD project

1. **Primary strong evidence:** stable simulated Validation/Test robustness gain from JS.
2. **Primary real-domain transfer evidence:** RRUFF-301 few-shot adaptation gain.
3. **Secondary but strong reliability evidence:** simulated ECE/NLL/Brier improvement with high matched-condition consistency.
4. **External stress-test evidence:** CNRS-318 zero-shot shows positive classification trend plus 5/5 probability-level directional replication, while exposing the remaining broad Sim-to-Real gap.

This hierarchy should be preserved in presentations: the reliability result strengthens the central same-parent consistency story, but does not replace the primary robustness contribution.
