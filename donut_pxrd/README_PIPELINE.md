# DONUT-PXRD serial pipeline

This stdlib controller coordinates the already specified DONUT-PXRD study. It does not define new science. The study remains one public BaTiO3 P4mm synthetic setting, with the same frozen 512 q-parent split (358/77/77) and seeds `20261061`, `20261062`, `20261063` throughout. A weak or negative model result is a scientific outcome; it is not, by itself, a software failure.

Run commands from the repository root and name the study tree explicitly. Python 3.10+ is required.

```powershell
# Inventory existing files only; report is written outside the selected study tree.
python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json `
  --repo-root E:\AI4science_donut_pxrd --mode inspect `
  --output-dir E:\AI4science_donut_serial\donut_pxrd\pipeline_status\active_inspect

# Small CPU-only subprocess smoke with an intentional failure and recovery.
python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json `
  --repo-root E:\AI4science_donut_serial --mode smoke `
  --output-dir donut_pxrd\pipeline_status\smoke

# Preview real commands; does not launch a stage.
python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json `
  --repo-root E:\AI4science_donut_pxrd --mode run `
  --output-dir E:\AI4science_donut_serial\donut_pxrd\pipeline_status\preview --dry-run

# Real training, only after the existing worker has stopped and the owner explicitly authorizes execution.
python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json `
  --repo-root E:\AI4science_donut_pxrd --mode run `
  --output-dir E:\AI4science_donut_serial\donut_pxrd\pipeline_status\production --execute

# Recover a prior run only after inspecting any BLOCKED partial outputs.
python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json `
  --repo-root E:\AI4science_donut_pxrd --mode resume `
  --output-dir E:\AI4science_donut_serial\donut_pxrd\pipeline_status\production
```

`inspect` does not write into or execute anything in the selected study tree. It records verified outputs and missing files in `inspect_report.json`; partial files are shown as not yet verified, not as scientific failure. `smoke` uses tiny subprocesses and never imports the GPU training stack. `run` requires `--execute`, holds an exclusive local lock, uses argument vectors without a shell, refuses existing training output directories, and checks the external worker process before Experiment 4. `resume` checks config and upstream hashes, raw NPZ manifest SHA, all three seed records, frozen test-parent identity lists, and checkpoint hashes. A damaged or partially written directory is marked `BLOCKED` for manual repair rather than overwritten.

The active script API runs exp3a, exp3b, and exp3c together for `--experiment 3`; the controller records exp3b and exp3c as artifact gates after the exp3a command. Texture OOD uses the existing separate `--texture-only` interface. Stage `COMPLETE` means required artifacts and integrity checks passed; the state also records subprocess exit status separately. Experiment 4 requires a terminal summary for A/B/C/D/E and all 77 frozen test parents. Only the terminal `report` stage can complete after every verifier succeeds. None of these software statuses alone means a result is scientifically favorable.

The pinned method reference is [official DONUT](https://github.com/AdvancedPhotonSource/DONUT) at `090c10bdf99333d3670dc26e617a93364f714bdc`; the study is a 1D powder-diffraction adaptation of its dual-branch training principle. The actual study protocol and numerical method evidence are in [`DONUT_PXRD_FOUR_STAGE_EXECUTION_20261019.md`](../docs/DONUT_PXRD_FOUR_STAGE_EXECUTION_20261019.md), and the current interface is read from `donut_pxrd/scripts/run_donut_stages.py` and `donut_pxrd/scripts/run_experiment4.py` in the explicitly selected study repository.
