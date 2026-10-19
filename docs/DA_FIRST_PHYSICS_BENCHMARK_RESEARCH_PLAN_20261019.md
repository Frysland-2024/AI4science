# 2026-10-19 Method-first PXRD Sim-to-Real Adaptation Plan
# 从“能运行的软件”改为“少样本适配能否真正改善传统精修”

> **Decision made by the researcher on 2026-10-19: SCIENTIFIC PRIORITY = A.** The researcher explicitly requires **domain adaptation (DA)** to demonstrate **practical improvement against credible conventional physics-only refinement**, not just improve against a weak simulated ML model or make an end-to-end UI. **Status: hypothesis and research plan; NOT an approved frozen experiment, NOT demonstrated results.** This supersedes previous *future inversion task priority* discussions, not completed classification evidence, old failed inverse-model gates, or actual submitted experiments. Freeze a test protocol only after specified source/data gates. No training or GPU run authorized by this planning document.

## 0. Primary research question and claim boundary

> On a **known material family with verified candidate structure(s)**, does a **simulation-trained parameter-initialization model adapted with K independent target experimental spectra and reference refinements** improve the **quality-adjusted success or speed of the same classical PXRD physical refinement** compared with the best reasonable physics-only workflow given the same structure information, measurement metadata, compute budget and target calibration cases?

DA is **not a replacement** for nonlinear refinement. Its contribution is the incremental target-domain benefit of initialization/adaptation upstream of that solver. Success requires BOTH:
- **Incremental real-data adaptation:** M1 improves over M0 (same simulator, model, physics optimizer and budget, without target real-label adaptation).
- **Practical incremental benefit:** M1 improves over credible physics-only baselines (P0 and the equally target-calibrated P1) in an independently evaluated held-out experimental set **without clinically/scientifically meaningful loss of fit or parameter reliability**.

A synthetic-only advantage, software integration, a low training loss, or M1 only beating an artificially weak/no-calibration physics baseline does not establish the primary claim. Distinguish improved *initial estimates* from improved *final physical refinement*. Do not promise positive findings.

## 1. Prior evidence, risks and related work

- Completed seven-system classifier and RRUFF-301 few-shot **classification** study are separate frozen work; never borrow their evaluation scores as inversion evidence.
- Existing `xrd_inversion/` supports numerically tested **known-phase single-phase tetragonal** forward/optimization under limited assumptions; 288/288 clean P2-R recovery was a synthetic numeric diagnostic, not real-spectrum success.
- Existing draft PR #37 (`codex/phase-router-inversion-mvp-20261019`) is an engineering single-phase three-CIF router with synthetic self-consistency, not a validated real-domain DA method. Its CaF2/Rutile local test had **the wrong candidate chemistry and poor forward fits**. Do not infer AI failure or success from that test.
- PR #38 (RRUFF inversion feasibility audit, 2026-10-19): **Rutile structure type** has 11 exact-ID refined labels, 10 after excluding a known mixed-phase scan (9 high-compatible reference-template candidates before caveat screening); **Garnet** has 44 complete labels, 43 metadata-clean, seven mineral species, single cubic a degree of freedom, 44 high-compatible template candidates **as audit metadata**. Both values are provisional for independent evaluation; raw XY and same-ID cell outputs must be verified. Rutile is easiest for existing tetragonal code but too small for strong DA assessment; Garnet has more samples but needs validated cubic forward support.
- **Critical leakage mechanism in the audit script:** `rank_cif_candidates` uses `cell_metric_match(refined, cif)` to select the highest-scoring CIF. Audit compatibility is *retrospective triage*, not a test-time deployable structure prior. **Never select test CIFs, lattice parameter ranges or initial cells using held-out sample refinements.** Fix downstream selection logic; retain the original metadata audit as historical evidence.
- Published prior art: Mun, Nam and Choi, *J. Applied Crystallography* 2026, RAPID (DOI 10.1107/S1600576726001494; code DataForgeSci/RAPID) already performs simulated-diffraction CNN-based structural/profile parameter prediction and FullProf refinement; experimental DA / fine-tuning is explicitly future work. The research cannot claim generic originality of neural pre-refinement. Classical optimization and candidate-based refinement prior art must also be respected. The hypothesis is **target-data-efficient improvement over strong traditional and ML baselines**, if demonstrated.
- No RRUFF dataset here establishes **across-laboratory personal adaptation**, as instrument/lab identity is not separately established.

## 2. The precise four-way controlled comparison (same target domain/held-out samples)

| ID | Source of initial parameters / target-domain knowledge | Final solver |
|---|---|---|
| P0 | Material-appropriate independently sourced CIF, published/practice defaults, fair bounded multistart | Same validated physics solver |
| P1 | **Physics-only calibrated** with the same K target training cases as M1 (e.g. instrument zero shift/profile correction), plus reasonable multistart | Same validated physics solver |
| M0 | Same domain-specific simulator-trained supervised regressor; **no real-case adaptation** | Same validated physics solver |
| M1 | **The same M0 checkpoint** followed by predeclared **K-shot target experimental adaptation**, controlled updates/frozen blocks as appropriate | Same validated physics solver |

Everything except initialization/calibration procedure must match: candidate chemistry/CIF, wavelength, full observed profile, solver physics, parameter bounds, tolerances, fit objective, maximum iterations, wall-clock / function-evaluation budget and hardware. No oracle initialization. P1 prevents DA benefiting only from seeing target calibration data without comparison to a physics-only tool that also sees those cases.

K values: predeclare a modest grid such as 1/3/5 **distinct real training samples** if the audited group count permits. Only explore a small set of adaptation methods selected on development data (e.g. frozen backbone+small head, limited fine-tuning, or simulator-instrument calibration), not unrestricted hyperparameter search. Keep a minimal real-case calibration-only ablation separate from neural fine-tuning so the mechanism is identifiable. Same architecture and source training for M0/M1. No compulsory novel loss or phase-routing subtask.

## 3. Source and split contracts

1. Source `XY_RAW` experimentally described powder profiles, exact-ID refinement outputs, validated instrument metadata and independently sourced reference CIF/space groups. `XY_Processed` is not a real target profile. Sample-refined cells are **reference estimates** dependent on refinement assumptions, not ground truth in an absolute sense.
2. Obtain candidate CIF using **known chemistry and structural taxonomy / authorized external references** *without the held-out specimen's refinement cell*, wavelength or fitting residual. Pin structure hash, source, license. Preserve alternatives as hypotheses but do not cherry-pick after examining test labels.
3. Choose scientific scope only on audit/training-development material. For Rutile: use tiny clean 10-case cohort as **physics/forward compatibility smoke**, not a reliable held-out DA generalization result. For Garnet: **candidate primary real-domain DA cohort** after cubic forward verification; ~43 metadata-clean cases can support small sample-group held-out evaluation, but test and model generality are limited. Use small independent pool and reserve a fully untouched holdout before tuning; actual split sizes must follow duplicate and chemistry group checks. K-shot cases **never overlap** test by exact ID, base ID, near-duplicate numeric hash or associated specimen. Species-level cross-domain generalization needs a separate species-grouped design.
4. The old frozen RRUFF-301/371 classifier adaptation/test split **must not be changed**. For the new inversion study create its own **versioned** sample-level role assignment; never reuse previously accessed classification locked-test spectra to tune a new method. Explicitly state what new data has already been viewed or used for smoke tests; avoid calling it blind if previously inspected.
5. Predeclared train / development-validation / final holdout identities, reference CIF selection logic, allowed domain features and **stopping/decision rule**. Test identities/labels unseen during method, simulator and hyperparameter tuning. If no credible holdout remains, limit to exploratory feasibility and do not make a strong improvement claim.

## 4. Endpoint and statistics

**Primary practical endpoint:** on independently held-out *experimental* samples, physics-quality-constrained success at a **fixed per-sample evaluation budget**, defined before testing from domain-appropriate peak/fit quality and reference-cell agreement criteria; select exact numerical adequacy tolerances from existing physical standards and development samples, **never from the final test**. If success is saturated or nearly saturated for P1, prespecify **time-to-adequate-fit** or number of forward evaluations with a noninferior fit/parameter constraint as the primary actionable comparison. Record failures and timeouts (do not drop them to improve speed medians). Success flags alone are insufficient; inspect full residuals and peak alignment.

Secondary endpoints:
- paired lattice-parameter differences vs RRUFF same-ID reported refined cells, uncertainties and potential reference-model bias noted;
- final residual / Rwp when appropriate and weighting is physically comparable;
- solver iterations / forward evaluations, fixed-budget convergence and paired runtimes;
- training / adaptation wall time, target label and preparation cost, per-user amortized break-even and inference latency;
- **M1 minus M0**, **M1 minus P1** paired differences; paired per-sample tables and qualitative uncertainty when final n small.

Predeclare a **practically meaningful** effect (e.g. target >=20% lower *end-to-end median evaluation time* to the same fit adequacy with no extra failure, OR a development-justified success-rate gain at equal budget) before final test. Twenty percent is an initial engineering example, **not a verified domain threshold**. Small n means no promise of conventional statistical significance: repeated model seeds do not multiply the number of independent experimental specimens. Bootstrap or uncertainty analysis should resample *independent sample groups*.

Interpretation:
- M1 > P1 and M1 > M0 with credible practical gains: **supports main claim**, limited to scoped target domain.
- M1 > M0 but M1 <= P1: **DA measurable but not practically superior**; method-first scientific goal unmet.
- M1 > P1 but M1 ~= M0: **ML helps, DA contribution unproven**.
- Neither gain or saturated physics-only baseline: **NO-GO for DA-as-superior-initialization claim**. A standalone product might still be engineered but is not this research objective.

## 5. Minimum gated execution: 8–12 weeks as a *proposal*, no automatic training

### Gate 0 — first 1–2 weeks: data-independent forward, contamination repair, and conventional headroom
- Resolve PR #38 audit, recalculate **CIF selection without using same sample's refined cell**, add tests to catch reference leakage.
- Verify wavelength/profile and independent proper candidate CIF. Begin with one Rutile/TiO2 measured sample strictly for real-domain *development smoke*, not an external claim.
- Reconstruct peak positions/relative intensities with physically justifiable forward/instrument model; check convergence and identifiability, not just numerical optimizer termination.
- Benchmark best credible P0/P1 on **development-only** samples. If physically wrong or P1 always solves to acceptable fits cheaply, **do not train a regressor for this task**; consider a different predeclared material or more meaningful measured task rather than degrade the baseline.
- Output `PHYSICS_GATE.md` with independent template sources, leakage audit, credible baseline and explicit GO / CHANGE_TASK / NO_GO.

### Gate 1 — weeks 3–4: choose DA-worthy cohort, freeze evaluation and measure headroom
- Prefer Garnet if verified cubic forward compatibility, enough truly independent metadata-clean specimens and measurable physics-only failure/time headroom; Rutile 10-sample cohort may serve only limited pilot. If neither passes, **terminate DA-first hypothesis for this dataset** rather than push platform engineering.
- Freeze all 4 arms, target case IDs and K-shot roles, target primary metric / fit-acceptability, comparison budget and experiment stop condition **before final test**.

### Gate 2 — weeks 5–7: low-cost model and DA on development only
- Simulated data from chosen chemistry-specific independently sourced CIF, realistic lattice/instrument variability with recorded source.
- Small ResNet or equally modest regressor M0; M1 limited K-shot fine-tune; compare to P0/P1 on dev samples, including solver runtime and physics quality. Avoid piling on optional reconstruction losses or new models without diagnostic reason.
- If M1 does not improve over **both** M0 and P1 under development controls, stop or return to Gate 0 only for a *new, explicitly revised scientific question*, not to repeated post-hoc test tuning.

### Gate 3 — weeks 8–10: one-time held-out evaluation
- Run frozen protocol on **previously untouched independent real sample holdout**, report full paired sample table, failures, practical effects and confidence limitations. No test-selected checkpoint/normalization/CIF/threshold.
- Only after convincing M1/P1 and M1/M0 gains should software packaging or a minimal local Qwen read-only orchestration layer enter scope. UI operation is an implementation bonus, not science success.

## 6. Hard de-scoping and contingency

- **Frozen throughout:** old seven-system classifier evidence, JS lambda, CNRS/RRUFF evaluation, Stage-1 archived NO-GO, DONUT failure and other previous public negative results.
- Not on the critical path: Qwen, Material Project API automation, multi-user archive, all-material router, phase mixture fraction estimation, universal phase identification, novel neural loss, new foundation model, elaborate uncertainty packages.
- If no experimentally justified advantage remains over P1, **report a negative feasibility result and pivot the thesis scientific question**; do not advertise a DA breakthrough or silently reframe success as a working UI.
- If validated measurements/data cannot support independent DA/test even after audit, obtain a *new* dataset with explicit target instrument/parameter labels or narrow scope to a numerical methods evaluation; don't infer generalization from 10 small correlated profiles.

## 7. Immediate Codex work request — DO NOT train yet

Create an isolated `da_method_first` task branch/worktree based on actual auditable source, preserve PR #37 and PR #38 and local uncommitted audit work, implement:
1. leakage check comparing audit-selected CIF against alternative selection using only chemistry/species/independent provenance;
2. prospective candidate case-ID split preview (NO frozen split until human reviews);
3. meaningful P0/P1 known-structure physics baseline protocol and forward-model compatibility/identifiability diagnostic;
4. read-only evidence/decision report GO / CHANGE_TASK / NO_GO.
No GPU run, no target holdout probing, no RRUFF raw redistribution, no auto-merge. Subsequent training requires approved gate and frozen comparison protocol.

## Historical pivot

Decision 2026-10-19, author-originated in conversation: after envisioning a per-user materials archive, auto-fetch structure, simulator-driven on-demand expert models, K-shot adaptation, Qwen orchestration, the researcher explicitly chose **A: domain adaptation itself must prove a practical benefit over credible traditional physics refinement**, even if that causes a scientific NO-GO or makes platform work premature. The change is a **scientific priority narrowing**, not a validated adaptation result or a reversal of the completed classification project.
