# AI4science — Provenance-Aware Supervision for PXRD Classification

[![XRD tests](https://github.com/Frysland-2024/AI4science/actions/workflows/xrd-tests.yml/badge.svg)](https://github.com/Frysland-2024/AI4science/actions/workflows/xrd-tests.yml)

Research code, frozen configurations, result summaries, and audit material for **provenance-aware supervised learning on powder X-ray diffraction (PXRD)**.

The central question is simple: an online PXRD simulator knows not only the crystal-system label, but also **which perturbed spectra came from the same parent crystal**. This repository studies whether that parent identity can be turned into additional supervision.

> **Status:** research code and evidence package; manuscript preparation is ongoing.

## Core idea

For one parent structure s, the simulator generates two measurement realizations:

x1 = g(s, m1), x2 = g(s, m2).

Both Dynamic ERM and Dynamic JS see the same parent structures, perturbation distribution, and two-view data exposure. The key difference is that Dynamic JS explicitly uses the known same-parent relation through prediction consistency:

L = 0.5 CE(p1, y) + 0.5 CE(p2, y) + lambda_JS JS(p1, p2).

~~~text
parent crystal
   ├─ measurement realization 1 ─► PXRD view x1 ─┐
   └─ measurement realization 2 ─► PXRD view x2 ─┤
                                                  ├─ shared parent identity
                                                  └─ measurement-equivalence supervision
~~~

The contribution is therefore **not** a new JS-divergence algorithm. It is the use of **simulator-retained provenance as relationship supervision**.

## Headline results

The main comparison uses a ResNet-18-GN backbone and lambda_js = 60.

| Evaluation | Dynamic ERM | Dynamic JS | Paired change |
|---|---:|---:|---:|
| Simulated single-factor OOD Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | **+0.05460**; 5/5 seeds positive |
| Simulated single-factor OOD Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | **+0.05445**; 5/5 seeds positive |
| RRUFF-301 K=1 Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | **+0.0433** |
| RRUFF-301 K=2 Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | **+0.0460** |
| RRUFF-301 K=5 Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | **+0.0545** |
| CNRS-318 zero-shot seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | **+0.01871 ± 0.00675**; 5/5 seeds positive |

Full result definitions, uncertainty treatment, and dataset-role boundaries are documented in [xrd_robustness/reports/RESULTS.md](xrd_robustness/reports/RESULTS.md) and [docs/PXRD_RESULT_REPORTING_STANDARD.md](docs/PXRD_RESULT_REPORTING_STANDARD.md).

Machine-readable headline summaries:

- [validation_results.json](xrd_robustness/reports/validation_results.json)
- [simulated_test_results.json](xrd_robustness/reports/simulated_test_results.json)
- [rruff301_fewshot_results.json](xrd_robustness/reports/rruff301_fewshot_results.json)

The manuscript draft is tracked in [xrd_robustness/MANUSCRIPT.md](xrd_robustness/MANUSCRIPT.md).

## Repository structure

~~~text
AI4science/
├── xrd_robustness/   # main PXRD classification / relationship-supervision study
│   ├── src/          # reusable Python package
│   ├── configs/      # frozen experiment configs
│   ├── manifests/    # run and provenance manifests
│   ├── reports/      # compact result and audit artifacts
│   ├── scripts/      # training, evaluation, audit, and figure scripts
│   └── tests/        # implementation and evidence-contract tests
├── xrd_inversion/    # secondary numerical PXRD inversion work
├── docs/             # scientific framing, evidence, reporting, and project history
└── .github/workflows # CI
~~~

## Quick start

Main package documentation: [xrd_robustness/README.md](xrd_robustness/README.md).

### Main PXRD classification package

~~~bash
git clone https://github.com/Frysland-2024/AI4science.git
cd AI4science/xrd_robustness

python -m pip install -e ".[test]"
python -m pytest -q -m "not data_bound"
~~~

The public test suite validates code, interfaces, configs, and tracked evidence artifacts. It does **not** retrain all models.

Optional scientific and plotting dependencies:

~~~bash
python -m pip install -e ".[science,figures,test]"
~~~

## Data and reproducibility

Raw external datasets, model checkpoints, generated spectra, and large intermediate arrays are intentionally not committed. The repository keeps compact configs, manifests, scripts, hashes, summary results, and audits needed to understand and verify the reported evidence chain.

See [docs/DATA_AND_REPRODUCIBILITY.md](docs/DATA_AND_REPRODUCIBILITY.md) for data requirements and reproducibility levels.

## Scientific scope and limitations

- The primary task is **seven-crystal-system PXRD classification**.
- RRUFF-301 is an **in-domain few-shot adaptation / label-efficiency** evaluation, not an unseen-mineral benchmark.
- CNRS-318 is an independent **zero-shot external-domain** evaluation. Its labels are reconstructed from deposited structures and were not independently verified by manual spectrum-level phase analysis.
- CNRS absolute sim-to-real performance remains low; the result is evidence about the *relative* ERM–JS comparison, not a claim that experimental PXRD classification is solved.
- The project uses JS consistency as a controlled implementation of provenance-aware supervision; it does not claim JS divergence itself is novel.

## Documentation

Start here:

- [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) — current scientific state
- [docs/PXRD_SUPERVISION_FRAMING.md](docs/PXRD_SUPERVISION_FRAMING.md) — task and method framing
- [docs/PXRD_EVIDENCE_CLOSURE.md](docs/PXRD_EVIDENCE_CLOSURE.md) — evidence closure and claim boundaries
- [docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md](docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md) — implementation and fairness audit
- [docs/PXRD_NOVELTY_LITERATURE_LINEAGE.md](docs/PXRD_NOVELTY_LITERATURE_LINEAGE.md) — related-work lineage
- [docs/PROJECT_HISTORY.md](docs/PROJECT_HISTORY.md) — concise public research-evolution timeline

## Citation

A manuscript citation will be added once the author list and persistent identifier are frozen. Until then, cite the repository URL together with the commit hash used. See [CITATION.md](CITATION.md).

## License and third-party code

This repository is released under the [MIT License](LICENSE). The ResNet implementation in xrd_robustness is a PyTorch port based on the MIT-licensed ML4pXRDs implementation by aimat-lab. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
