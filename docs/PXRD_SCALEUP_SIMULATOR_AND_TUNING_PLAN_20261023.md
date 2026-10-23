# 2026-10-23 — Large-data PXRD: simulation upgrade and hyperparameter re-selection

**Sole active research task:** machine-learning-based PXRD seven-crystal-system classification. Its only three core evaluation axes are RRUFF zero-shot Accuracy/Macro-F1, confidence calibration (ECE primary), and simulated-data efficiency by independent training-parent count. Parameter inversion, Forward Loss, DONUT-related, and refinement work are Archived / Inactive. All work below is planning only.

**Status:** USER-SELECTED NEXT-STAGE DESIGN / PLANNING. This is not an implemented simulator, hyperparameter search, new download, or improved RRUFF score. Treat the existing five-perturbation V7/V9 results as frozen historical evidence, not as a codebase to overwrite.

**Lead decision:** The next-stage project retains precisely three headline axes (RRUFF real-domain leaderboard; ECE confidence calibration; simulated independent-parent data efficiency), and adds two engineering/scientific prerequisites:
1. Study and selectively adopt a more comprehensive physically grounded **dynamic** PXRD measurement simulator (primary open reference: Cao et al. SimXRD / Pysimxrd).
2. After independent CIF training-data expansion and simulator changes, **re-select training and simulator distribution hyperparameters using development evidence**, instead of blindly keeping values calibrated for 9,842 training structures and an older measurement model.

## Existing repository implementation (read before modifying)
- `xrd_robustness/src/xrd_robustness/simulator.py` computes pymatgen ideal peaks and renders in-memory spectra with `SimulationGrid` (10–80°, step 0.02°, CuKa), Gaussian peak widths, global zero shift, March–Dollase reflection-aware orientation, background, and noise.
- `physics.py`, `measurement_models.py`, `preferred_orientation.py` hold deterministic configuration-driven perturbations; `online_views.py` uses two paired realization views sharing **one unchanged parent structure**.
- The frozen physical model already includes smooth polynomial/GP background and Poisson/electronic noise; do not call these features absent just because the new literature code has them.
- The frozen train ranges and their physical/literature justification are in `docs/PXRD_PERTURBATION_EVIDENCE.md` and `configs/simulation.method_transfer.frozen.json`.
- The earlier 984/2460/4921/9842 independent-parent efficiency protocol trained each ERM/JS method for 49,280 optimizer steps at parent batch=16: 788,480 sampled parent occurrences and 1,576,960 view realizations, with AdamW LR=1e-4, weight_decay=1e-4, no scheduler and JS λ=60. These are **historical choices, not automatically optimal for scale-up**.

## Reference code and cautions
- Cao et al., SimXRD-4M, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/b04843d76c9f090beca55f335c4ea6bf-Abstract-Conference.html
- Open source Pysimxrd: https://github.com/Bin-Cao/SimXRD/tree/main/src/Pysimxrd , MIT license at https://github.com/Bin-Cao/SimXRD/blob/main/LICENSE ; user manual: https://bincao.work/SimXRD/docs/manual_en.html
- Pysimxrd has default pymatgen-backed rendering and optional WPEM diffraction logic. Demonstrated options include grain-size-dependent line profiles, texture intensity variation, Debye–Waller-like thermal vibration, detector/slit geometry, background, and noise; it supports random lattice deformation and ASE-based bulk generation.
- **Do not copy blindly:** in the checked `generator.parser` at `src/Pysimxrd/generator.py`, the default (`sim_model=None`) call into `matgen_pxrdsim` **does not pass the `zero_shift` argument**: https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/generator.py . This is a code-path caution, NOT a claim about the WPEM branch.
- The source's default `MatgenKit.py` applies clipped independent per-peak orientation scaling; our existing March–Dollase preferred-orientation operator is more explicitly reflection-grounded for the same-parent objective. https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/utils/MatgenKit.py
- Random lattice shear/stretch can break the symmetry/space group and hence potentially change the **seven-system** label; do not turn on `deformation=True` as a generic class-preserving nuisance. Require a symmetry/label audit if introduced. Distinguish stable measurement nuisance from a genuine change in sample structure/phase.
- Compare against 2026 Kikkawa et al., *Experiment-informed data augmentation for machine-learning-based crystal system prediction for industrial XRD data*, DOI 10.1016/j.mtcomm.2026.115665: authors report on 1,298 industrial spectra that physics-informed augmentation alone is insufficient and experiment-informed nuisance augmentations improve experimental accuracy by >25% (the accessible abstract does not specify whether the increase is relative or percentage points) (best 77% on **their** data, not RRUFF). Abstract: https://www.sciencedirect.com/science/article/pii/S2352492826010548 . Investigate impurities/missing peaks/background and experimental coverage, **without inventing detailed formulas absent accessible methods**.
- Current pymatgen `XRDCalculator` supports named radiation wavelengths, `debye_waller_factors`, and structure/site input; check installed version and whether Debye–Waller sampling requires re-evaluating structure factors rather than merely rescaling cached peaks. https://pymatgen.org/pymatgen.analysis.diffraction.html

## Part A — Simulator upgrade (new *versioned* implementation; avoid reusing the historical ambiguous name "V8")
1. **Establish a compact source-to-feature map** with source code path, formula, units, random sampling, whether label-preserving, compute cost, and license. Verify on concrete structures rather than assuming any method is automatically superior because it has more switches.
2. **Keep**: existing parent identity, deterministic paired seeds, online rendering, cached ideal peak/reflection metadata, March–Dollase, Poisson/readout noise, smooth background, invariant known crystal-system label.
3. **First additions (cost-effective)**: angle-dependent peak broadening with Caglioti-type instrumental term and specimen grain-size/microstrain terms, and area-consistent pseudo-Voigt/Voigt-like line shapes as justified by references; preserve appropriate integrated intensity. Support optional Cu Kα1/Kα2 splitting as a radiation/instrument profile, with correct wavelength/relative strength assumptions and spectral-range handling.
4. **Second additions (only after first works)**: Debye–Waller/thermal scattering-factor attenuation, geometrical asymmetry/sample displacement, instrument/slit corrections, missing/weak peaks and limited impurity features **only where the seven-system label and single-phase interpretation remain defensible**. Thermal-factor change may require a new reflection cache or revisiting structure factors, not an arbitrary peak-wise multiplier.
5. Each operator is independently togglable, composable, seeded, logged with units and source, and compatible with frozen input grid/serialization where required. Keep old `v7` rendered evaluation reproducible.
6. Small acceptance suite: 7 crystal systems × several representative structures, finite/nonnegative outputs, peak locations vs theory, symmetry retention where claimed, monotonic width vs grain size, count/noise sanity, deterministic two-view replay, throughput and memory benchmark. Visual expert comparison is supportive, not a numerical claim of RRUFF accuracy.
7. Critically compare the old and new simulator in a matched **small-data** A/B on the **same structures, architecture, optimization and validation** before attributing improvements to the new physics. Only deploy bigger training if it is sufficiently fast and physically defensible.

## Part B — Re-select settings for larger data without overexpanding the search
Separate two classes of settings:
- **Physical augmentation-distribution settings**: operator ranges, application probabilities, composition/scheduling of perturbations, data normalization, Caglioti widths, specimen/geometry priors. Start from published/physically motivated ranges; develop on *training* and a held-out **synthetic validation** distribution, documenting decisions. Do not infer true instrument distributions from papers or tune on RRUFF-231 locked-test scores.
- **ML training settings**: number of train parents, class sampling, batch parents, optimizer LR/weight decay, scheduler and warmup, optimizer steps/parent exposure, validation cadence and early stopping, JS λ. λ=60 from earlier 9,842-parent V7 study is a reference, **not an eternal constant**.

Pragmatic staged tuning (suggested search candidates, NOT authorized frozen parameters):
1. At first feasible enlarged tier (~30k *training parents*, not guaranteed), run a short pipeline/throughput pilot and select a feasible parent batch such as 16 or 32 subject to GPU memory, with same shared online views for ERM/JS.
2. Calibrate optimizer settings first on training + **synthetic validation only**, using a *small* LR×schedule matrix, e.g. LR {1e-4,3e-4} × {constant, warmup+cosine}; assess convergence, not just one best score. AdamW remains the starting optimizer; do not simultaneously change architecture.
3. Diagnose CE and JS gradient scales on training batches under the new simulator, then test a few predeclared λ candidates around the historical 60 (e.g. 15,60,120 only if gradient diagnostics support them), using identical data/exposure. Keep λ=0 ERM as the baseline; no RRUFF model selection.
4. With online random views, **an epoch is not the same as one fixed spectrum per structure**; explicitly report independent parent exposures and optimizer steps. At fixed 49,280 steps and batch 16, training sees 788,480 parent occurrences; that corresponds to ~80 exposures/parent for 9,842 train parents but ~8 for 100k. The old step budget can significantly undertrain an expanded corpus. Pilot several training exposure horizons, with validation-based stop and an explicit resource cap; avoid blindly holding steps fixed or inflating epochs to historical values.
5. After the small pilot, freeze one reasonable recipe for the 30k/60k/100k scale curve (or report any predeclared per-tier tuning separately), and run ERM/JS with matched views, split, compute policy and seeds. Maintain negative runs and comparisons; label new evidence exploratory until fresh external test verification.

## Three headline readouts (remain unchanged)
1. **RRUFF primary**: seven-system **zero-shot Accuracy** + Macro-F1 on clearly identified real spectra; exact labels and RRUFF IDs, common input/split with replicable Lee/SimXRD/XQueryer-NoElem baselines wherever achievable. RRUFF-301 K=1/2/5 old results remain secondary historical few-shot evidence; never call zero-shot if RRUFF labeled data tunes the settings.
2. **ECE**: 15-bin reliability definition consistent with historical method, plus NLL/Brier supporting (on an explicitly named same prediction panel); ECE alone is insufficient without accuracy.
3. **Simulated-parent data efficiency**: unique **training CIF parents** vs Macro-F1 and Accuracy, ERM/JS matched budget, plus compute costs. The current frozen parent-budget report says `no_supported_parent_saving` even though JS beats ERM at every tested parent count; do not backfill a structure-savings claim.

CNRS stays **optional second real-domain evidence** and is not a required tuner or separate headline. Preserve already completed CNRS metrics and uncertainty transparently.

## Part C — Conditional model-architecture comparison (P2)

Keep ResNet-18-GN as the formal historical baseline. Only after the parent corpus and versioned simulator are stable, consider a controlled comparison with **SimXRD CNN11** and, optionally, a **multi-scale 1D CNN**. Preserve paired data/split/training controls and record the trigger for opening this comparison. Do not make a large Transformer or new architecture development a required milestone.

## Change management and completion
- Keep one local workspace at `E:\AI4science`; create versioned **subdirectories within it**, not sibling project folders. `formal_14060` and all existing frozen data/results/configs unchanged.
- Track provenance and citations to external code/physical formulas; comply with upstream MIT attribution if code is adapted.
- **Milestone 1:** source/feature audit + a versioned simulator with physics smoke and throughput numbers.
- **Milestone 2:** 14k data two-simulator controlled pilot, establish whether new simulation itself contributes.
- **Milestone 3:** at first feasible larger independent-parent tier, document optimizer/scheduler/batch/JS settings and training-compute scaling.
- **Milestone 4:** paired multi-size training and RRUFF zero-shot leaderboard + ECE, with a prospectively frozen independent external comparison when feasible.
- New results must be committed as reports/manifests only when actually executed; this document is a planning handoff, not experimental evidence.

**One-line rationale:** better simulated *measurement process* + correctly scaled *learning process* before expecting literature-competitive RRUFF results.
