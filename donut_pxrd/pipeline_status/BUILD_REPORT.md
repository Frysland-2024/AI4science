# DONUT-PXRD serial runner build report

**Build scope:** engineering orchestration only, on `codex/donut-pxrd-serial-pipeline-20261019`. No scientific training or GPU process was launched by this work.

## Implementation

- Added the Python standard-library controller, declarative pipeline config, unittest suite, and manual.
- The controller has ordered preflight, exp1, exp2, exp3a/b/c, texture OOD, exp4, and report gates. The inspected active API executes exp3a/b/c together for `--experiment 3`; exp3b/c are explicit artifact gates after that invocation.
- Run and resume state is atomic and SHA-256 based. State records the run ID, immutable per-attempt log paths, argument vector, exit code, elapsed time, stage status, input/upstream fingerprints, and verified artifact hashes.
- Existing output folders and expected checkpoint files prevent a fresh run from overwriting artifacts. Resume requires output verification; partial or stale outputs are blocked for manual repair. Checkpoint references are constrained to the configured checkpoint root and compared to the hashes in the stage records.
- `run` requires `--execute`; `--dry-run` prints inputs and argv without creating a lock or launching stages. A per-study-tree lock blocks concurrent controller instances. Experiment 4 also checks for an active process running either study script.

## Verification commands and results

| Command/check | Exit | Result |
|---|---:|---|
| `python -m unittest donut_pxrd.tests.test_serial_pipeline -v` | 0 | 10 CPU-only tests passed, including output refusal, stale hash, checkpoint hash mismatch, concurrent lock, atomic state, stop-on-failure, and resume skips. |
| `python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json --repo-root E:\AI4science_donut_serial --mode smoke --output-dir donut_pxrd\pipeline_status\smoke` | 0 | Four subprocess stages; first pass returned 2 after intentional child exit 23; resume returned 0 and skipped three verified stages. No GPU or study script was invoked. See `smoke/smoke_report.json`. |
| `python donut_pxrd/pipeline.py --config donut_pxrd/configs/serial_pipeline_v1.json --repo-root E:\AI4science_donut_pxrd --mode run --output-dir donut_pxrd\pipeline_status\preview --dry-run` | 0 | Printed command vectors and SHA-256 input inventory; no training command was launched. |
| Read-only `inspect` against `E:\AI4science_donut_pxrd` | 0 | Snapshot at **2026-10-19 04:17:13 UTC**. See `active_inspect/inspect_report.json` and `active_inspect/inspect.log`. |
| `git diff --check` | 0 | No whitespace errors. |
| `python -m pytest donut_pxrd/tests/test_serial_pipeline.py -q` | 1 | Pytest is not installed in the selected Python environment (`No module named pytest`). The same suite passed with stdlib unittest above. |

## Active-study snapshot

At the inspect timestamp, the frozen config and pre-registration matched; exp1, exp2, exp3a, exp3b, exp3c, and texture OOD outputs passed the runner's file, split/seed, data-archive SHA, and checkpoint SHA checks. Experiment 4's `raw_paired_results.json` and `summary.json` were absent, so exp4 and the terminal report gate are recorded `NOT_RUN`. This is a point-in-time inventory of a live study tree; missing files are not classified as experiment failure, and the study may have progressed since the snapshot.

## Limits and science status

The controller validates NPZ file SHA against its data manifest and checks all three per-seed records, shared 77-parent lists, and recorded checkpoint SHA values. It uses only Python's standard library and does not deserialize PyTorch checkpoints or recompute NumPy array-internal hashes. The existing training script reloads its checkpoints during execution; a separate PyTorch audit remains outside this CPU-only engineering run.

No claim is made here that the DONUT experiments or Experiment 4 are scientifically complete. A passing pipeline smoke verifies orchestration and recovery behavior only.
