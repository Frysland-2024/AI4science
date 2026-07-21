# AI4Science / XRD Reliability — Repository Instructions

## Mission
Build a reproducible, physics-grounded benchmark and training workflow for robust **1D powder XRD crystal-system / symmetry classification** under label-preserving measurement perturbations.

The project asks whether predictions for the **same underlying structure** remain stable under physically plausible measurement changes:

\[
f(x_{\mathrm{clean}}) \approx f(T_{\mathrm{phys}}(x_{\mathrm{clean}})).
\]

## Mandatory read order

Before editing code, read:

1. `context/00_CURRENT_STATE.md`
2. `context/02_SIMXRD_XRD_RELIABILITY_SPEC.md`
3. `context/03_EXPERIMENT_PROTOCOL.md`
4. `context/04_PHYSICAL_VALIDITY.md`
5. `context/10_KNOWN_UNCERTAINTIES.md`

Read `legacy/` only when a task needs the historical FerroAI audit context.

## Non-negotiable rules

- Treat **physical validity** as a research requirement, not a cosmetic augmentation choice.
- Never invent numerical perturbation ranges. Put every proposed value into an evidence ledger and mark it `unverified` until a source or a user decision confirms it.
- Preserve the three core conditions: `ERM`, `augmentation-only`, and `augmentation + consistency`. Do not define a no-augmentation `consistency-only` condition because the consistency term itself requires a transformed paired view.
- Prevent leakage: split by underlying structure/material identity before generating multiple perturbations or views.
- Keep labels and class mappings versioned. Do not silently remap, merge, or drop classes.
- Do not overwrite raw data, source PDFs, labels, or prior experiment outputs.
- Every run must record: git commit/version, config, data split ID, seed, model checkpoint, metrics, and environment information.
- Use fixed seeds for comparisons and report variation across multiple seeds for main claims.
- Keep clean IID evaluation separate from perturbation robustness and real-XRD external validation.
- Treat `unit-cell variation` and strong texture as high-risk transformations: they are **not automatically label-preserving**.
- Do not market a high IID score as a reliability result.
- Do not claim a scientific conclusion from a single plot or a single random seed.

## Coding standards

- Prefer small composable modules and config-driven experiments.
- Add type hints, docstrings, and explicit validation for public functions.
- Add at least a smoke test for each new data transform and metric.
- Make transformations deterministic under a passed random generator/seed.
- Keep plots generated from saved result tables, never from manually edited arrays.
- Preserve provenance in filenames and `run_manifest.json`.

## Required response style from Codex

Before a nontrivial implementation, state:

1. which assumptions are already grounded by this context;
2. which assumptions are unresolved;
3. the minimal safe implementation plan;
4. how leakage, physical invalidity, and confounding will be checked.

When blocked by missing metadata, labels, data access, or evidence for perturbation bounds, ask a concise question or build only the schema/tests that do not assume an answer.
