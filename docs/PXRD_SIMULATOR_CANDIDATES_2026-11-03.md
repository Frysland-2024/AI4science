# PXRD simulator reuse candidates — 2026-11-03

**Status: ACTIVE THESIS RESEARCH — SOURCE INVESTIGATION FIRST.** The project lead confirmed on 2026-11-03 that the undergraduate thesis has restarted. This document is a **candidate and implementation-decision record**, not evidence that external simulators have already been integrated or that new models have been trained.

## Why this direction was selected

After the 2026-10-22 supervisor discussion, the lead prioritized **absolute seven-crystal-system Accuracy on real RRUFF patterns**, with paper-specific RRUFF train/test protocols (not a blanket zero-shot requirement). Their next experiment keeps **same-parent Dynamic JS consistency**, borrows mature simulator implementations, then compares established CNN backbones against the previous ResNet-18-GN + JS system.

Key choices from the 2026-11-03 discussion:
- **First understand the upstream simulators** and select working components; do not implement or scale training prematurely.
- Favor **reuse/adaptation**, not full reproduction of published models. Correct simple code-path bugs/units when justified; reject components incompatible with our seven-system label or online same-parent training.
- The key synthetic-data scale is **unique valid CIF parent structures**, not the number of regenerated online patterns. Record view exposures and compute separately.
- Do not force a training CIF count to equal every paper's reported database size. Paper-specific **real RRUFF data protocol** matters for interpreting literature score comparisons.
- **JS-only is sufficient for the immediate exploratory architecture/simulator pilot.** Historical ERM/JS evidence is preserved; new performance gains must not automatically be attributed uniquely to JS.
- For an initial low-cost comparison, retain the original simulator/ResNet-18-GN + JS as historical reference, then compare improved simulator with ResNet-18-GN + JS and SimXRD CNN11 + JS, using compatible CIF splits and recorded optimization budgets. Large-scale CIF acquisition, extra architectures and publication-style benchmarks come later.

## Simulator candidate shortlist

| Candidate | Source / documentation | Why examine it | Priority | Proposed role / caveat |
| --- | --- | --- | --- | --- |
| SimXRD / Pysimxrd | https://github.com/Bin-Cao/SimXRD | Data generation and measurement variation; source includes MatgenKit/pymatgen and optional WPEM paths | **P0** | Trace actual calls, formulae, parameter distributions, units, random sampling and licenses; do not assume paper text and public script always coincide |
| GSAS-II | https://github.com/AdvancedPhotonSource/GSAS-II ; https://gsas-ii.readthedocs.io/en/latest/GSASIIscriptable.html | Mature instrument/sample diffraction profile models | **P0** | Reference implementation / validation oracle for peak shapes and geometric effects; assess Python automation cost, correctness and licensing before adopting |
| ML4pXRDs | https://github.com/aimat-lab/ML4pXRDs | Potentially reusable fast PXRD generation, Numba-oriented pipelines and structure sampling approaches | **P0** | Measure throughput and assess fit with online same-parent peak caching; a source archive was previously provided in project materials |
| PhaseSmith | https://github.com/CPrescher/PhaseSmith | Candidate lightweight powder-diffraction profile implementation | **P1** | Inspect maturity, instrument broadening/asymmetry API, numerical behavior and license before use |
| DebyeCalculator | https://github.com/FrederikLizakJohansen/DebyeCalculator | Debye-scattering modeling for finite-size/nanoparticle cases | **P2** | More specialized than ordinary periodic-crystal PXRD and potentially compute-heavy; not a default renderer replacement |
| PowderLine | https://github.com/NSLS2/PowderLine | Possible batch workflow around other powder diffraction engines | **P2 / optional** | Orchestration reference, not presumed independent physical simulator |
| xrd_simulator | https://github.com/FABLE-3DXRD/xrd_simulator | Spatial polycrystal / detector geometry simulation | **P2 / optional** | 2D geometry differs from our present 1D PXRD classification goal |

**Verification status:** All rows above are **candidates**; the inventory does not certify compatibility, an exact published experiment code path, performance superiority, legal reusability, or availability of installed dependencies. Check upstream source/version and license before importing code; record commit hashes.

## Existing capabilities to retain

Current implementation in `xrd_robustness/src/xrd_robustness/` includes:
- `simulator.py`: pymatgen ideal peak table, Gaussian rendering, global shift;
- `preferred_orientation.py`: reflection-aware March–Dollase orientation;
- `measurement_models.py` and `physics.py`: background/noise and physically motivated sampling;
- `online_views.py`: deterministic, cached, same-parent paired views for JS training.

The new library should not be assumed superior merely because it contains more options. Preserve existing frozen versioned configurations and results.

## Mandatory phase gate — simulator before backbone (owner decision)

**Phase S1: source understanding.** Trace SimXRD/Pysimxrd, GSAS-II, ML4pXRDs (PhaseSmith optional), including concrete code paths, formulas and units, parameter distributions, seed control, labels, licensing and runtime. Record exactly what is implemented vs assumed; choose modules to reuse, adapt or reject.

**Phase S2: simulator construction and standalone acceptance.** Integrate only selected components into a new, versioned simulator while preserving cached ideal peaks, same-parent paired views and frozen old code. Validate physics, label preservation, deterministic replay, peak area/shape, noise and throughput on a small fixed CIF set. Compare generated profiles against original and reference implementations. Produce a runnable simulator and evidence-backed acceptance report.

**Gate:** Architecture comparison remains **BLOCKED** until Phase S1/S2 are complete and the simulator is demonstrated to work, with documented exceptions/limitations. Passing this gate authorizes planning a controlled **JS-only ResNet-18-GN vs CNN11** pilot on shared CIF and evaluation conditions, not automatic large-scale GPU jobs. Keep RRUFF locked test out of tuning.

## First audit questions, before any code adaptation

1. **Exact path from CIF to 1D intensity:** underlying structural data, space-group/symmetry treatment, ideal structure factors and `hkl`, peak positions and normalization.
2. **Profile model:** Gaussian / pseudo-Voigt / Voigt, instrumental Caglioti U/V/W, size/strain broadening, doublet, asymmetry, slit/detector geometry; compare formulas, units and peak-area consistency.
3. **Nuisance sampling:** distributions, probabilities, correlations, zero shift, background, Poisson/readout noise, texture and thermal effects; distinguish measured code behavior from paper prose.
4. **Label preservation:** arbitrary lattice deformation or sample phase/impurity changes may invalidate seven-system same-parent pair labels; do not turn them on without symmetry audit.
5. **Engineering fit:** CPU/GPU overhead, cached ideal reflections, deterministic seeded replay, on-the-fly two-view output, reproducibility and compatibility with existing grid.
6. **Licensing and provenance:** external project versions, compatible licenses, file paths, attribution and third-party dependencies.

Specific previously recorded caution for Pysimxrd: its default `generator.parser` route may omit forwarding `zero_shift` to `matgen_pxrdsim`; verify against the checked version instead of assuming the optional WPEM path behaves the same. Do not automatically replace our March–Dollase texture with independent peak intensity scaling.

## Requested next deliverable

Produce a **source-to-feature comparison** for SimXRD/Pysimxrd, GSAS-II, ML4pXRDs, with PhaseSmith as optional lightweight candidate. Mark each module `KEEP_EXISTING`, `REUSE`, `ADAPT`, `REJECT` or `UNKNOWN`; include code reference, formula/units, seven-system label compatibility, runtime, reproducibility and license. Make a shortlist of *physical effects worth integrating*. Then prepare a small, versioned JS-only simulator/backbone pilot; **do not interpret the pilot as already executed**.

**Integrity constraints:** old splits, checkpoints, test sets and frozen results stay unchanged. Do not select model hyperparameters against the old RRUFF locked test. The 2026-10-26 thesis closure remains a valid historical decision, but the **new 2026-11-03 restart supersedes its "no new research" execution status**.

Related: [current state](CURRENT_STATE.md), [project history](PROJECT_HISTORY.md), [October 23 plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).
