# 2026-10-19 — Candidate undergraduate-thesis fallback after Garnet physics pilots

> **Status: RECOMMENDATION FOR SUPERVISOR DISCUSSION ONLY; NOT A RESEARCHER DECISION; NOT AN APPROVED THESIS TITLE.** This records the request "那如果是这样的话，那我的毕设做什么呢" following unfavorable Garnet physics-fit findings. Preserve it alongside the earlier 2026-10-19 researcher-chosen A hypothesis, not as a retroactive reversal.

## Trigger and evidence

Related *Draft* PRs #40 and #41 implemented two different single-family Garnet development-only physics checks:
- PR #40: three independent-source-CIF Grossular dev samples, lattice errors +0.086–0.108% vs posthoc RRUFF references; five-start lattice spread ~0.546–0.846 Å fails predeclared stability gate. Result PHYSICS_MODEL_NOT_READY.
- PR #41: 12 Grossular dev spectra, different pinned CIF and fixed instrument/parameter setup, physics-only multistart improves profile RMSE 12/12 and reference cell error 6/12; approximate mean absolute lattice-reference difference 0.01985 Å, 1.86 s/sample. Result LIMITED_GO only. These cannot be compared head-to-head because their CIFs, instrument wavelength and nuisance freedom differ.
- Neither PR trained a DA model or proved M1 > robust traditional P1; current data splits and specimen reference provenance remain limiting. The student's scientific standard A (DA must yield **useful incremental value** vs strong physics-only refinements) remains valid; there is no justification for claiming it already succeeds.

## Candidate safe degree thesis

**Proposed title (if permitted by supervisor / school's project-credit rules):** 利用模拟器母结构同源关系监督的 PXRD 七晶系分类及真实域少样本迁移 / Measurement-Equivalence Supervision from Simulator Provenance for PXRD Classification.

This is the **already completed** main `xrd_robustness` scientific research, distinct from the unproven inversion/DA line. Its core method reuses same-parent provenance to create measurement-equivalent XRD views and add JS prediction consistency to supervised ResNet18-GN. Reported *frozen* comparisons:
- synthetic test OOD Macro-F1 0.65074 → 0.70534 (paired +0.05460, 5/5 seeds);
- RRUFF-301 K=5 Macro-F1 0.3555 → 0.4099 (paired +0.0545); K=1/2 also improve;
- CNRS-318 independent zero-shot seed-level Macro-F1 0.18837 → 0.20708 (small absolute scores, do not oversell);
- four parent-budget supplementary experiments have same-budget advantages but do **not** establish measurable parent-data savings, and were post-main.
Do not label JS itself as an invented algorithm, don't call the entire classification research "domain adaptation"; the target-domain DA result is the RRUFF subset. Keep data provenance, locked tests and collaborators' executed work appropriately acknowledged; research-design leadership belongs principally to the project lead as documented, but thesis/authorship requirements require supervisor confirmation.

## Conditional graduation alternatives

1. **Preferred if school permits use of prior work:** focus thesis on already completed classification method, rigorous material-characterization framing, analysis, model limitations and reproducibility; reserve future inversion as optional outlook, not as a results chapter.
2. **If an independent new Advanced Project increment is mandatory:** get supervisor to specify non-overlap and credit requirements *before* scheduling experiments. Choose one bounded new scientific question rooted in the proven classification/real-domain adaptation framework (e.g., a genuinely independent new target domain or an independently evaluated lab-shift experiment), with fresh data or properly frozen holdout. Do not re-score the frozen RRUFF/CNRS test and present that as new confirmatory evidence. A software demonstration can complement but cannot constitute an ML-method gain.
3. **Keep inversion only as gated parallel exploratory line:** revisit if verified wavelength/structure, robust physics headroom, independent specimen holdout and fair M1>P1 and M1>M0 tests become possible. If not, report NO-GO and stop rather than manufacture an easy traditional baseline.
4. Optional minimal local XRD demonstration may show application but must be labeled engineering, not DA scientific validation.

## Next discussion with supervisor

Ask: Can previously completed PXRD JS relationship-supervision research, including RRUFF/CNRS and independent budget supplements, be submitted as the bachelor's thesis or Advanced Project under the institution's dates, supervision, contribution and originality requirements? If not, what *specific new independent work* must be demonstrated? Until answered, don't claim a final degree-thesis choice.

## Historical significance

The researcher did not abandon AI4Science or the desire for scientifically meaningful gains. The question emerged because experimentally grounded physics comparisons narrowed the plausible value of an ambitious inverse-parameter/few-shot DA claim, while a completed supervised PXRD research project already provides a stronger evidence base. The proposed decision is to **separate scientific risk-taking from graduation delivery** instead of letting one speculative DA hypothesis jeopardize the thesis.
