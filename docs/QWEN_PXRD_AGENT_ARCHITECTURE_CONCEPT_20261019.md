# Qwen orchestration layer for personalized PXRD adaptation (concept note, 2026-10-19)

> **Status: PROPOSAL ONLY / NOT IMPLEMENTED / NO SCIENTIFIC RESULTS.**
> Historical supplement to [PERSONALIZED_PXRD_ADAPTATION_WORKFLOW_IDEA_20261019.md](PERSONALIZED_PXRD_ADAPTATION_WORKFLOW_IDEA_20261019.md). This proposal was explicitly initiated by the researcher. Do not claim the Qwen agent, RRUFF inversion dataset, or domain adaptation is operational.

## New researcher's question

Can an **open-weight Qwen** model be integrated into the previously proposed, per-user materials archive and simulation-to-real PXRD model-production workflow, so that a person can describe a material family and supply a few already-refined experimental cases, while an agent orchestrates structure retrieval, physics simulation, model preparation, optional domain adaptation, classical refinement, and results archiving?

**Answer at architecture level:** yes, as a **tool-calling / orchestration layer**, not as a replacement for the domain-specialist numerical models or as a claim that Qwen itself predicts accurate lattice parameters from powder XRD.

## Clear division of labor

- **Research user:** provides known chemistry, family, phase candidates/CIF, diffraction metadata, refinement references and approvals.
- **Qwen Agent:** natural language intent → bounded typed tool calls, workflow state summary, failure explanation, audit report. Does not invent physical values or trust its free-form outputs as labels.
- **Validated program modules:** Materials Project official API / curated licensed CIF lookup, provenance registry, physical PXRD generator, narrow ResNet regression, simulation-to-real adaptation, numerical/GSAS-II or other refinement interface, report exporter.
- **Deterministic controller:** validates input schemas, allows only authorized steps, enforces resource limits and state transitions, records exact versions/seeds/hashes, asks approval before training, deletes or exports nothing without authorization.
- **User project archive:** versioned family/CIF, instrument settings, source records and licenses, real experimental references, splits, trained model hashes, metrics and outcome/failure reports. Separate different users, honor upload privacy, retention/deletion controls.

## Proposed first tool surface (smallest meaningful Qwen demo)

1. `get_project_summary(project_id)`: read-only user/domain/experiment state.
2. `search_structures(project_id, constraints)`: MP `mp-api` query or approved indexed structures; returns records and provenance; does not claim these are ready-made experimental XRD spectra.
3. `propose_pipeline(project_id, stage)`: validates readiness and emits reproducible plan/config; optionally runs inexpensive read-only preview of spectrum simulation. **Training requires explicit approval and gate passage.**
4. `get_run_report(project_id, run_id)`: read-only structured metrics and physical fit diagnostics; can explain unsupported or failed claims.

Later separately add `run_simulation`, `train_regressor`, `adapt_to_lab`, `initialize_refinement`, `run_refinement`, but only after corresponding deterministic modules exist and independent scientific gates pass.

## Proposed RRUFF demonstration (not yet a successful experiment)

RRUFF acts as a **virtual user/domain case study**, not automatically a multi-laboratory transfer benchmark:
1. Audit for one family with enough sample-ID matched raw experimental PXRD, trusted refinement cell parameters and appropriate CIF. Preserve old RRUFF-301/371 frozen classification splits/results.
2. Create a YAML/JSON project archive (no user accounts necessary).
3. Human supplies a family/structural range; Qwen requests a schema-validated MP/AMCSD structure list. Verified simulator generates spectra and parameters.
4. Train a simple domain-specific network or reuse a pretrained one; test `sim-only` first.
5. Only if enough independent real reference cases exist, allocate disjoint adaptation/held-out test and compare with and without limited target adaptation.
6. Compare (a) reference CIF initialization (b) pure physics multistart (c) synthetic-only NN initialization (d) adapted NN initialization, all followed by the **same physics refinement**; report wall clock, convergence, credible parameter difference, fit residual, and failures.
7. Qwen summarizes machine-recorded evidence and writes archives; never substitutes a textual assertion for a run artifact.

## Important guardrails

- Open-weight Qwen model selection, hardware fit, license and tool parser support must be verified at implementation time. Official **Qwen-Agent** has custom tools, function calling and MCP. Run via local vLLM/Ollama/other compatible server as appropriate; don't overfit the research around one transient checkpoint.
- Treat external database text, user file names, and model-generated tool arguments as untrusted. Whitelist tool names, validate arguments and enforce filesystem boundaries. No arbitrary shell execution or unrestricted code-interpreter access through model output.
- MP structures are computational or curated structure inputs; **not a source of verified sample-specific refinement labels**. Diffraction patterns require a simulator.
- Few real refined examples may be insufficient for robust neural adaptation; fallback to instrument calibration / frozen backbone or label-free approaches only after methodological verification.
- Separate orchestration/product engineering from scientific claims: adding a Qwen chat interface does not itself improve inversion or prove domain adaptation.
- Record project-specific data/license provenance and protect collaborator uploads.
- Follow repository AGENTS.md, scientific state and approval system. New work in isolated branch; no changes to frozen JS-only results and no revival of archived factorization NO-GO.

## Thesis boundary

**Do not implement an entire commercial-style multi-tenant SaaS or fully autonomous GPU system now.** Initial MVP can be CLI/Gradio with one local project, a selected RRUFF family and 4 safe tool calls, plus deterministic pipeline. Finish the RRUFF inversion data feasibility audit before doing expensive training.

## Value for the historical research narrative

The researcher's idea has progressed from an isolated XRD classification model → exploring numerical inversion → re-evaluating conventional human refinement workflow → domain-specific simulation/training/adaptation → per-user archived model production → **an open-weight LLM orchestration front end**. This is an architectural proposal and a record of the researcher's thinking, not a claim of implementation or original foundation-model invention.
