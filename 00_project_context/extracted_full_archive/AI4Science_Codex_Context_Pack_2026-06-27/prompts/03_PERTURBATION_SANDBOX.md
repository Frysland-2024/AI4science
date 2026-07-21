# Codex Task — Physics-Aware Perturbation Sandbox

Prerequisite: data audit completed; `2θ` grid/units are verified.

Read `AGENTS.md`, `context/02_SIMXRD_XRD_RELIABILITY_SPEC.md`, `context/04_PHYSICAL_VALIDITY.md`, and `context/10_KNOWN_UNCERTAINTIES.md`.

Task:

1. Create modular transforms for global shift, broadening, noise, and background.
2. Do not choose final numerical ranges. Implement parameterized functions and a config schema with `status: proposed` defaults.
3. Add tests for identity behavior, non-negativity, fixed-grid output, deterministic seeded behavior, and lack of wrap-around artifacts.
4. Build a report/gallery script that renders clean/transformed overlays plus parameter values.
5. Create an evidence-ledger CSV/YAML template and link each transform config to a ledger ID.
6. Explicitly flag any transform detail requiring a physical source or user decision.

Do not include unit-cell variation in the default transform pipeline.
