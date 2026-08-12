# Application-Ready Research Narrative V1 — 2026-08-08

> **Supersession notice (2026-08-11):** This application draft is retained as a
> historical narrative, not as the current evidence contract. Before reuse,
> reconcile it with `CURRENT_STATE.md`: the implemented task is robust seven-class
> PXRD classification rather than physical-parameter inversion, the split is only
> exact-parent-disjoint, and RRUFF-301 is retrospective rather than confirmatory.

## Short positioning

I began the project as a materials-science student trying to make simulated PXRD classifiers robust to experimental perturbations. Over time, the project changed from a conventional “generate more realistic synthetic data and train a model” workflow into a machine-learning question: **what additional supervision is hidden in the scientific data-generation process, and can that structure improve robustness and data efficiency?**

The most important outcome was not a particular architecture. It was learning to translate a physical measurement process into a controlled ML hypothesis, reject attractive but unsupported ideas, and build a confirmatory evidence chain rather than optimizing toward a single favorable score.

## Full narrative

### 1. Starting point: FerroAI and the search for a more method-oriented project

My earlier FerroAI work taught me the value of a complete research pipeline: literature review, dataset construction, feature generation, model training, validation, error analysis, and physical interpretation had to form one reproducible chain. At the same time, I became increasingly interested in research where machine learning was not merely a faster surrogate for an existing materials calculation.

When choosing a new project, I compared characterization modalities such as XRD, TEM, and Raman. Powder XRD was attractive because its signal has a clear physical origin, simulated structures are accessible at scale, measurement perturbations can be controlled, and the label can remain fixed while acquisition conditions change. This made it possible to ask not only whether a model could classify a pattern, but whether it could remain reliable when the measurement process changed.

### 2. First formulation: robustness under physical perturbations

The initial question was straightforward: if peak position, peak width, preferred orientation, background, or noise changes while the underlying crystal system remains the same, should a classifier make the same decision?

My first instinct was close to standard materials-ML practice: create more perturbed spectra, broaden the synthetic distribution, and compare augmentation schemes. This stage was useful because it forced me to define parent-structure splits, avoid leakage between multiple spectra generated from the same crystal, and create explicit OOD panels instead of relying only on a random Train/Test split.

### 3. A period of over-expansion: PAMPT, structured perturbations, residual learning, sample efficiency

The project then became too broad. I explored a peak-aware Transformer-like backbone, sample-efficiency studies, structured dynamic perturbation systems, residual decorrelation, and simulator-parameter supervision. Many of these ideas were individually interesting, but together they made the paper difficult to falsify and diluted the main question.

This was an important lesson: a project does not become stronger simply because it contains more mechanisms. I gradually learned to separate “future research modules” from the one question that could be answered rigorously with the available data and compute.

### 4. Backbone failure changed the way I diagnosed ML systems

A major turning point came when the peak-aware PAMPT backbone failed to learn the task adequately. Initially I worried that the physical augmentation itself was too destructive. Instead of immediately changing the simulator, I built a sequence of diagnostic Gates: clean-pattern learnability, longer training, matched backbone comparison, and input-quality checks.

The result was decisive. A ResNet-style 1D convolutional backbone fit the training task far more effectively than PAMPT and restored strong performance under dynamic physical augmentation. This taught me to distinguish **method failure from foundation failure**. If the shared backbone cannot learn the base task, comparing sophisticated regularizers is scientifically meaningless.

That diagnosis also produced a future ML question of its own: why do different inductive biases interact so differently with physically perturbed one-dimensional scientific signals?

### 5. Residual decorrelation: an attractive idea that did not survive the evidence

Inspired by domain-generalization work, I explored residual decorrelation: allow two measurements of the same object to differ, but try to make their feature residual independent of the crystal-system label. This was appealing because it seemed more flexible than forcing strict invariance.

The experiments were valuable precisely because the method did not cleanly work. Independent probes showed that residual features could still carry crystal information, and a later measurement-supervised residual variant increased measurement decodability while also increasing crystal leakage. This suggested that PXRD measurement factors and structural semantics are not trivially separable: peak shift, broadening, and intensity changes act directly on the same physically meaningful peaks used for classification.

Instead of repeatedly tuning the method until it looked successful, I archived it. That decision became a methodological milestone for me: a negative mechanism result should narrow the hypothesis space rather than be hidden by post-hoc optimization.

### 6. The key reframing: the simulator provides relationships, not only samples

The main conceptual step came from reconsidering what the online simulator actually knows.

For a parent crystal structure `s`, two physically perturbed PXRD observations can be written as

`x1 = g(s, m1)` and `x2 = g(s, m2)`.

Ordinary dynamic ERM uses the fact that both have the same crystal-system label. But the simulator knows something stronger: **they are two observations of the same physical parent structure**.

This changed the research question. Instead of asking only how to generate more training data, I asked whether the simulator’s provenance information could become an additional supervision signal.

I implemented a matched two-view comparison:

- Dynamic ERM sees two online perturbed views and applies only cross-entropy;
- Dynamic JS sees exactly the same two views, but also minimizes Jensen–Shannon divergence between their predictive distributions.

The important point is not that JS divergence is new. The contribution is the problem formulation: using physically paired simulator provenance as **measurement-equivalence supervision** while controlling data exposure, backbone, perturbation distribution, split, and optimization.

### 7. From a promising run to a controlled evidence chain

I became increasingly strict about experimental governance. Before comparing methods, I froze the candidate JS weights using Train-only gradient-scale Gates. Validation selected `lambda_js = 60`; after selection, the weight was closed. I then ran five matched ERM–JS seed pairs rather than relying on one favorable seed.

On simulated Validation data, JS improved mean single-factor OOD Macro-F1 by about `+0.0466`, with all five paired seeds positive. A separately frozen simulated Test independently confirmed the direction with a mean paired improvement of about `+0.0546`.

The value of this stage was not only the score. It taught me to separate:

- Train-only numerical legality;
- Validation-based model selection;
- multi-seed replication;
- locked confirmatory Test;
- external experimental-domain evidence.

Each stage answered a different question and had a different access boundary.

### 8. Real-domain validation: exploratory evidence was not enough

The next challenge was experimental PXRD. My first RRUFF-70 few-shot pilot showed a promising JS advantage, but I did not want to treat a small exploratory set that had already influenced hypothesis formation as final evidence.

I therefore designed a larger RRUFF-301 confirmatory experiment prospectively. The protocol used 301 experimental mineral PXRD spectra, a 70-spectrum adaptation pool, a locked 231-spectrum test set, frozen K=1/2/5 budgets, five pretraining seeds, five episode seeds, and a paired Macro-F1 comparison.

The first execution revealed an important label-construction bug: RRUFF CELL PARAMETERS metadata represented trigonal entries under a hexagonal convention, collapsing the two classes. I invalidated the v1 result, documented the bug in an audit trail, rebuilt the labels using DIF space-group evidence and crystallographic mapping, and reran the complete experiment from the corrected split.

The corrected v2 result showed JS improvements of approximately `+0.043`, `+0.046`, and `+0.055` Macro-F1 at K=1,2,5, with 68 of 75 paired comparisons positive.

This episode is one of the parts of the project I value most. It changed my definition of a good research result from “a number that supports the idea” to “a result whose provenance, failure modes, and corrections can survive scrutiny.”

### 9. What the project became

The project started as a materials-characterization classification task. It eventually became a study of how a scientific simulator can provide **structured supervision** for robust representation learning.

The final paper-level question is:

> Can simulator-retained parent-structure provenance be used as measurement-equivalence supervision to improve robustness and reduce the amount of experimental PXRD data needed for adaptation?

This framing is specific enough to be scientifically testable in XRD, but general enough to connect to broader AI-for-science problems involving multiple measurements of the same latent physical object.

### 10. What I learned about my future direction

The project made me more interested in the interface between machine learning and scientific measurement than in using ML merely as a property-prediction tool. The problems I now find most compelling include:

- simulation-to-experiment transfer;
- structured and weak supervision from scientific simulators;
- robust representation learning under measurement shift;
- label-efficient adaptation to experimental data;
- inductive bias for one-dimensional scientific signals;
- physics-guided learning objectives and evaluation protocols.

My materials background remains useful because it helps me understand what a data point physically represents, which transformations preserve the target, and which apparent “augmentations” are scientifically invalid. But the research questions I want to pursue increasingly concern the learning principle itself.

## 150-word application version

My undergraduate research began with a practical PXRD problem: models trained on simulated diffraction patterns often fail when experimental peak shifts, broadening, texture, background, and noise change the measurement distribution. I initially approached this as a data-augmentation problem, but repeated failures changed the project. A peak-aware backbone proved to be a learnability bottleneck; a residual-disentanglement approach failed to remove crystal information from measurement differences. These negative results led me to a simpler question: an online simulator knows that two perturbed spectra come from the same parent crystal, so can this provenance become supervision? I compared matched Dynamic ERM and Jensen–Shannon consistency training under identical data exposure. Across five paired seeds, JS improved simulated OOD robustness, and a preregistered RRUFF-301 experiment showed 68/75 positive few-shot adaptation comparisons. The project taught me to turn physical data-generation mechanisms into ML hypotheses and to value auditable confirmation over post-hoc performance tuning.

## Interview version — 30 seconds

I started by trying to make simulated XRD classifiers robust to experimental perturbations. The key shift was realizing that the simulator gives more than augmented samples: it knows which spectra are different measurements of the same parent crystal. I converted that provenance into a consistency-supervision problem, compared it fairly against matched dynamic ERM, and then validated the effect with multi-seed simulated experiments and a preregistered RRUFF-301 few-shot study. Along the way I also had to archive failed residual and backbone ideas and invalidate an experiment after finding a label bug. That process is why I now want to work on robust and data-efficient ML for scientific measurements rather than only applying standard models to materials datasets.

## Claim discipline for applications

Use:

- “I reframed the simulator as a source of structured supervision.”
- “I designed paired, preregistered comparisons and separated exploratory from confirmatory evidence.”
- “A label bug was discovered, disclosed, and the confirmatory experiment was rerun from a corrected split.”
- “The project moved me from materials-ML application toward robust learning for scientific measurements.”

Avoid:

- “I invented consistency regularization.”
- “I solved XRD Sim2Real.”
- “The residual method is impossible for XRD.”
- “The method universally improves every crystal system.”
- “RRUFF represents all experimental PXRD.”
