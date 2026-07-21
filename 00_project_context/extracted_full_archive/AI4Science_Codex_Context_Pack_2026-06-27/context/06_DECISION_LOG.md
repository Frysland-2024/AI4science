# 06 — Decision Log

This log captures decisions that should not be accidentally reversed by an implementation agent.

| Date / period | Decision | Status | Rationale |
|---|---|---|---|
| 2025-12 | FerroAI replication/audit became an early research task | legacy | Establishes initial AI-for-materials reliability motivation |
| 2026-05 | FerroAI work reframed from pure reproduction to public-artifact reliability audit | legacy | Outputs that resemble scientific knowledge require evidence and model-behavior audit |
| 2026-05-29 | SimXRD/XRD reliability project formulated | active | Move from auditing a model to constructing a controlled reliability benchmark |
| 2026-06-01 | Adopt `clean baseline + physical perturbation stress test + robustness enhancement` | active | Prevents an overly artificial shortcut/confounding benchmark from becoming the MVP |
| 2026-06 | Use measurement effects such as shift, broadening, noise, background as core perturbations | active | They have direct physical/instrumental interpretations |
| 2026-06 | Keep `preferred orientation/texture` separate and treat `unit-cell variation` as high risk | active | Not every plausible pattern change is safely label-preserving |
| 2026-06 | Do not make IRM the main 3-month method | active | IRM has higher assumption/implementation risk; consistency regularization is the safer MVP |
| 2026-06 | Default model objective is supervised learning plus paired-view consistency | active | Directly encodes the same-structure/same-label stability requirement |
| 2026-06 | Required ablations: ERM, augmentation-only, consistency-only, augmentation+consistency | superseded 2026-07-11 | The old naming incorrectly implied consistency could be isolated without a transformed view |
| 2026-07-11 | Required core conditions: ERM, augmentation-only, augmentation+consistency | active | The last two conditions use identical paired views and classification supervision; their difference isolates the added consistency penalty |
| 2026-07-11 | Residual measurement-disparity decorrelation is a phase-two candidate | active | Inspired by Hu et al.; reasonable measurement differences may remain, but should not carry crystal-class semantics |
| 2026-06 | Real XRD validation is a central closing-loop module | active | Simulated success alone lacks experimental relevance |
| 2026-06 | Perturbation numerical bounds must come from physical evidence, not LLM intuition | active | This is the project’s central scientific validity constraint |
| 2026-06 | Project target: bounded 12-week MVP, not an all-purpose XRD AI system | active | Ensures execution and a defensible research story |
| 2026-06-21 | Long-term advisor preference: strong probabilistic/generative/theory-oriented scientific ML | active personal research criterion | Helps maintain direction beyond this benchmark |

## Explicitly rejected or deprioritized approaches

- **Pure protocol-induced confounding as the main benchmark:** deprioritized because it risks looking like an artificial target chosen after the fact.
- **Hard IRM-first project:** deprioritized for MVP due to strong assumptions and implementation risk.
- **Only report clean classification accuracy:** rejected because it does not answer measurement reliability.
- **Only use synthetic data:** insufficient; external real-XRD relevance is required.
- **Treat all augmentations as label-preserving by default:** rejected on physical grounds.
