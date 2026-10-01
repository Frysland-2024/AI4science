# PXRD relationship-supervision study

This directory contains the main research package for **seven-crystal-system PXRD classification with simulator-provenance supervision**.

## Experiment

Two training objectives are compared under matched data exposure:

- **Dynamic ERM:** two independently perturbed views from the same parent, trained with label supervision only.
- **Dynamic JS:** the same two views and labels, plus Jensen–Shannon consistency between their predictive distributions.

The backbone is ResNet-18-GN. The selected consistency weight is lambda_js = 60.

~~~text
simulator-retained parent identity
            ↓
measurement-equivalent views
            ↓
relationship supervision
            ↓
prediction consistency
~~~

## Results

| Evaluation | Dynamic ERM | Dynamic JS | Change |
|---|---:|---:|---:|
| Simulated Test OOD Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | +0.05460 |
| Simulated Test OOD Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | +0.05445 |
| RRUFF-301 K=1 Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | +0.0433 |
| RRUFF-301 K=2 Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | +0.0460 |
| RRUFF-301 K=5 Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | +0.0545 |
| CNRS-318 zero-shot seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | +0.01871 ± 0.00675 |

See [reports/RESULTS.md](reports/RESULTS.md) for definitions, uncertainty, and additional metrics.

Public result artifacts:

- [reports/validation_results.json](reports/validation_results.json)
- [reports/simulated_test_results.json](reports/simulated_test_results.json)
- [reports/rruff301_fewshot_results.json](reports/rruff301_fewshot_results.json)
- [MANUSCRIPT.md](MANUSCRIPT.md)

## Install

~~~bash
python -m pip install -e ".[test]"
python -m pytest -q -m "not data_bound"
~~~

Optional scientific and plotting dependencies:

~~~bash
python -m pip install -e ".[science,figures,test]"
~~~

## Main code

| Path | Purpose |
|---|---|
| src/xrd_robustness/models/ml4pxrd_resnet1d.py | ResNet-18-GN backbone |
| src/xrd_robustness/training/objectives.py | ERM and JS objectives |
| src/xrd_robustness/simulator.py | PXRD measurement perturbations |
| src/xrd_robustness/online_views.py | paired views from one parent |
| src/xrd_robustness/training/runner.py | training entry point |
| scripts/run_simulated_test.py | simulated final evaluation |
| scripts/run_cnrs318_zero_shot.py | CNRS zero-shot evaluation |
| scripts/audit_rruff301_composition.py | RRUFF split/composition audit |

CLI entry point after installation:

~~~bash
xrd-train --help
~~~

## Evidence and reproducibility

- [../docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md)
- [../docs/PXRD_SUPERVISION_FRAMING.md](../docs/PXRD_SUPERVISION_FRAMING.md)
- [../docs/PXRD_EVIDENCE_CLOSURE.md](../docs/PXRD_EVIDENCE_CLOSURE.md)
- [../docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md](../docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md)
- [../docs/PXRD_PERTURBATION_EVIDENCE.md](../docs/PXRD_PERTURBATION_EVIDENCE.md)
- [../docs/DATA_AND_REPRODUCIBILITY.md](../docs/DATA_AND_REPRODUCIBILITY.md)

Raw datasets, checkpoints, generated spectra, and bulky intermediate outputs are intentionally not tracked.
