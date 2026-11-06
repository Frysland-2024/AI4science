# V11 validation record (2026-11-03)

Base: `origin/main` at `bc96731` (`docs(history): record ResNet hyperparameter retuning as intermediate phase before CNN11`).

## Automated tests

Command:

```powershell
& E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest xrd_robustness\tests\simulation xrd_robustness\tests\training\test_training_objectives.py xrd_robustness\tests\training\test_train_cli.py --no-header -q
```

Result: **50 passed in 6.48s**. Console output is preserved in `pytest_20261103.txt`.

## Actual CIF to V9 reference + V11 dynamic pair

Command:

```powershell
& E:\AI4science\.venvs\xrd_test\Scripts\python.exe xrd_robustness\scripts\generate_dynamic_pair.py --cif E:\AI4science\milly_ceramics_xrd_20261023\reference-CIF\Na0.5Eu0.5TiO3_R-3c_start.cif --simulation-config xrd_robustness\configs\simulation.v11_tch_pseudo_voigt.json --material-id Na0.5Eu0.5TiO3_R-3c --seed 20261103 --epoch 2 --global-step 19
```

Result: trigonal label retained by both views; shape `[3501]`; views are distinct and fixed-seed replay is exact. Output is preserved in `cif_pair_example_20261103.json`.

## Seven-system physical acceptance and timing

`accept_simulator_v11.py` passed for seven CIF-round-tripped structures, preserving all seven crystal-system labels. Checks passed for fixed-seed pairs, V9 regression, angle/size/strain broadening trends, and discrete integrated peak area (`2.4999999984` for a requested area of `2.5`). Full results are in `acceptance_20261103.json`.

Mean cached two-view generation time over seven PeakTables: V9 `2.029 ms/pair`; V11 `5.147 ms/pair`; V11/V9 `2.537x`. This is a local timing observation, not a hardware-independent benchmark.

No model training was run.