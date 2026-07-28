# V9 P0 follow-up diagnostics

Date: 2026-07-24

## Protected first result

The first completed P0 report is immutable and must be retained:

- `xrd_robustness/reports/v9_p0_local_benefit.json`
- user-observed SHA-256: `8A89A90B42352331AB926A3169EB35EC27BF05B8F2C8374849CD1FAC273CEBEA`

No follow-up script may overwrite or delete this file. Every runner verifies its hash before and after execution and fails closed if the hash changes.

## Added follow-ups

### 1. Statistical robustness re-analysis

`xrd_robustness/scripts/analyze_v9_p0_statistical_robustness.py`

- reads the original P0 JSON only;
- computes repeat-clustered bootstrap intervals;
- computes leave-one-profile-out sensitivity;
- reports per-profile contributions;
- performs no model training and writes a separate file:
  `reports/v9_p0_statistical_robustness.json`.

### 2. Independent-seed replication

`xrd_robustness/scripts/audit_v9_p0_independent_replication.py`

- rebuilds the five-epoch Train-only ERM state with an independent seed;
- changes initialization, Train order, local batches, and perturbation stream;
- preserves the original report;
- writes `reports/v9_p0_local_benefit_replication_seed1.json`;
- remains a P0 diagnostic and cannot establish formal performance gain.

### 3. Matched short trajectory

`xrd_robustness/scripts/audit_v9_p0_short_trajectory.py`

- starts ERM, JS, and Residual branches from the same in-memory learned state and optimizer state;
- gives all branches the same fixed Train-only update batches;
- evaluates the same fixed Train-only in-range and six single-factor-OOD panels after each of five default steps;
- uses the middle registered lambda values without selection;
- writes `reports/v9_p0_short_trajectory.json`;
- writes no checkpoint and accesses no Validation, simulated Test, or real XRD.

## One-command runner

`xrd_robustness/scripts/run_v9_p0_followups.ps1`

The runner executes focused tests, CPU-only statistical analysis, independent-seed replication, and the short trajectory. It verifies that the original P0 SHA-256 is unchanged after all steps.

## Scientific boundary

These follow-ups reduce uncertainty about local optimization direction, seed sensitivity, profile dependence, and short-horizon behavior. They do not replace:

- seven-run Validation tuning;
- fifteen-run multi-seed formal comparison;
- simulated Test;
- zero-shot real-XRD evaluation;
- few-shot real adaptation.

No follow-up result may be used to select a non-registered lambda or unlock formal execution automatically.
