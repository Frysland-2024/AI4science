# 模块化预精修架构（W0 工程接口）

系统默认由实验人员提供材料家族与名义成分。Family Router 不从 XRD 谱推测化学组成。Registry 为每一相候选保留 CIF 来源、结构身份、空间群、有效条件、参数化/范围和仪器配置。

```mermaid
flowchart LR
    A[2theta-intensity + metadata] --> B{family_id / composition}
    B -->|unknown or mismatch| R[REVIEW_REQUIRED]
    B -->|known family| C[Family Registry]
    C --> D[Family-specific CIF candidates]
    D --> E[Single-phase template ranking]
    E --> F[Reference parameter initialization]
    F --> G[Bounded candidate-wise forward fit]
    G --> H[Pre-refinement JSON / plot]
    G -->|insufficient or uncalibrated| R
    H --> I[Human review / conventional refinement]
    J[Optional H(i+j) synthetic stress case] -. separate hypothesis .-> G
    J -. never a wt% estimate .-> H
```

## Data contracts

- Family: `family_id`, nominal composition/window, instrument wavelength/range/grid, model/calibration status, and candidates.
- Candidate: `candidate_id`, phase identity, formula/composition range, reference CIF and provenance/hash, space group, stability/measurement conditions, reference parameters, allowed/provisional parameter ranges.
- Observation: common 2theta axis plus intensity and experiment metadata; mismatched axis/configuration must stop or require explicit regridding.
- Single-phase result: rank + uncalibrated distance or calibrated single-phase probability, reference initialization, candidate-wise forward fit where enabled, parameter/interval status, saved reconstructed spectrum and pointwise residual.
- Coexistence is a separate `H_(i+j)` object. Candidate-model probability, coexistence-model probability, and phase fraction occupy separate schema fields. The W0 baseline fills none of these probabilities or phase fractions.
- Unsupported family, composition mismatch, missing metadata, or lack of validated single-phase adequacy produces `REVIEW_REQUIRED`.

## Current implementation boundary

Implemented: JSON family registry loader, metadata-first router, normalized-RMSE template ranker, report serializer with reconstructed profiles and residual arrays, shared pymatgen/robustness simulation adapter, and the BaTiO3 engineering pilot. The pilot runs a bounded `scipy.optimize.least_squares` fit for both Pm-3m and P4mm reference candidates, varying only their symmetry-allowed lattice metrics and a global zero shift.

Not implemented: trained neural network, temperature scaling, calibrated phase probabilities, continuous parameter regressor, fitted parameter uncertainty/intervals, evidence-backed search ranges, validated reject threshold, quantitative Rietveld refinement, automatic coexistence detection, or phase fractions. The W0 numerical fit is one synthetic engineering smoke, not validated parameter recovery. The mixture remains only a synthetic profile-intensity stress case. CrystalShift's separate public implementation and the conditions for a future baseline are documented in [CRYSTALSHIFT_AUDIT.md](CRYSTALSHIFT_AUDIT.md).
