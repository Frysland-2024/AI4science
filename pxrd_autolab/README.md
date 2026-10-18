# PXRD AutoLab P0

P0 is a report-only, fail-closed workflow for locking a JSON protocol, recording a run, verifying existing PXRD evidence, and creating review drafts. It does not invoke a trainer or produce new scientific results. The existing `xrd_forward_loss/` package and its recorded results remain the experiment implementation and source of truth.

## Install

From the repository root in PowerShell:

```powershell
python -m pip install -e ".\pxrd_autolab[test]"
```

## CPU fixture smoke

```powershell
python -m pxrd_autolab.run `
  --config .\pxrd_autolab\configs\fixture_smoke.json `
  --repo-root . `
  --runs-root .\runs\pxrd_autolab
```

The fixture is explicitly synthetic. It only proves that config locking, unique run creation, logs, state transitions, charts, and draft reports work. Each run is stored in a fresh `run_id` directory; generated run directories are ignored by Git.

## Report the existing Forward Loss pilot

Run this after the `xrd_forward_loss/` pilot files are present in the repository checkout:

```powershell
python -m pxrd_autolab.run `
  --config .\pxrd_autolab\configs\forward_loss_recorded.json `
  --repo-root . `
  --input-root . `
  --runs-root .\runs\pxrd_autolab
```

The runner checks the recorded forward gate, recomputes means and sample standard deviations from the seed-level test metrics, verifies the validation-only lambda choice, and checks the source hashes recorded by the pilot manifest. It then writes `metrics.json`, `figures/` (A/B metrics, training parameter/reconstruction losses, and validation error), `report.md`, and `biweekly_brief.md`. A successful run ends in `AWAITING_REVIEW`; it does not approve a scientific interpretation or send the brief.

If AutoLab is checked out separately from the Forward Loss branch, set `--input-root` to that checkout and use `--repo-root` for the code checkout whose provenance should be recorded.

## Stop conditions and records

- `--dry-run` validates and freezes the config without reading evidence files.
- `--max-steps` adds a stricter command-line budget cap. P0 configurations must declare `planned_steps: 0`; requests for training are blocked.
- A missing input produces a `FAILED` state and traceback. A failed forward gate or exhausted budget produces `BLOCKED`; report generation does not proceed.
- `config.raw.json`, canonical frozen config, `manifest.json`, `state.json`, `events.jsonl`, and `run.log` are preserved with each run. Artifacts and inputs are SHA-256 recorded.
- No resume, scheduler, GPU training, automatic approval, or message delivery is implemented in P0.

## Tests

```powershell
python -m pip install -e ".\pxrd_autolab[test]"
python -m pytest .\pxrd_autolab\tests -q
```
