# Scientific Signal Tokenization and Backbone–Augmentation Compatibility

**Status:** `SEALED_FUTURE_MODULE`  
**Design date:** 2026-08-01  
**Active V9 affected:** no  
**Training authorized:** no  
**Simulated Test / real XRD access authorized:** no

> This document registers a future machine-learning research module. It must not
> modify, reopen, or reinterpret the frozen V9 Dynamic ERM versus JS Consistency
> experiment. The current V9 uses ResNet-18-GN because it passed the common
> learnability and robustness diagnostics. This module asks why the earlier
> peak-aware Transformer/PAMPT representation underperformed the convolutional
> backbone, and whether a representation that better matches the structure of
> scientific one-dimensional signals can close or reverse that gap.

## 1. Research identity

### Working title

**Scientific Signal Tokenization and Backbone–Augmentation Compatibility**

Alternative concise title:

**Structure-Aware Tokenization for PXRD Transformers**

### Core research question

> Why does a convolutional backbone learn robust PXRD classification more
> effectively than the current peak-aware Transformer/PAMPT design, and can the
> gap be explained and improved through scientifically meaningful tokenization,
> continuous-to-discrete representation design, and augmentation-compatible
> inductive bias?

### Broader machine-learning question

The module is not merely a comparison of CNN and Transformer accuracy. It asks:

> How should a scientific signal be converted into learning units when its
> physically meaningful objects are not raw sample points, but peaks, peak
> neighborhoods, spacings, absences, and multi-scale relationships?

This question can generalize from PXRD to Raman, FTIR, XPS, mass spectra, ECG,
chromatography, and other one-dimensional scientific signals.

## 2. Motivation from the project history

The project observed a strong architecture-dependent outcome under the same
PXRD task:

- the earlier PAMPT/Transformer-style backbone showed limited train
  learnability and weak validation performance;
- the ResNet backbone fitted the task substantially better and restored dynamic
  augmentation performance;
- therefore the failure cannot be described only as an OOD-generalization
  problem; it may begin at representation construction or optimization.

The current evidence supports the existence of a
**backbone–augmentation interaction**, but does not yet identify its mechanism.
This module is designed to separate the candidate explanations.

## 3. Main hypotheses

### H1. Raw-point tokens are semantically weak

A single PXRD intensity sample at one angular bin is not a stable physical
object. Its meaning depends on a local peak shape and on global reflection
relationships. Treating short fixed patches as language-like tokens may create
weak or unstable token semantics.

### H2. Peak-aware tokenization may be discontinuous under physical perturbation

Small physical changes in peak position, width, background, or noise can cause
large discrete changes in:

- detected peak count;
- peak ordering;
- peak prominence;
- selected token boundaries;
- merged or split peaks.

Thus a physically continuous signal transformation may become discontinuous in
model input space.

### H3. CNN inductive bias matches local diffraction structure

Convolution provides:

- local connectivity;
- translation-tolerant pattern recognition;
- weight sharing;
- hierarchical composition of peak shapes and peak groups.

These biases may be better matched to perturbed one-dimensional diffraction
signals than unconstrained global attention.

### H4. The current Transformer loses information before attention can help

Potential bottlenecks include:

- patch projection that compresses narrow peaks;
- derivative branches that amplify noise;
- mean pooling that dilutes sparse discriminative peaks;
- premature peak selection;
- inadequate positional encoding for angular geometry;
- insufficient data or training budget for a flexible attention model.

### H5. CNN and Transformer may be complementary rather than mutually exclusive

A convolutional stem may first produce stable local peak features, after which
attention can model long-range peak relations. A hybrid model may therefore be
more appropriate than either raw-point Transformer or pure peak-list
Transformer.

## 4. Scientific representations to compare

The module should compare representations before comparing large model families.

### R0. Continuous full-spectrum representation

Input: complete normalized intensity vector on the fixed 2-theta grid.

Purpose: preserve all available information and serve as the current ResNet
reference.

### R1. Fixed patch tokens

Input: fixed-width overlapping spectral patches.

Purpose: test the current generic Transformer tokenization assumption.

### R2. Peak-event tokens

Each detected peak token may contain:

- peak position;
- intensity;
- integrated area;
- FWHM;
- prominence;
- asymmetry;
- local background;
- local uncertainty or detection confidence.

Purpose: align tokens with physically meaningful signal events.

### R3. Peak-neighborhood tokens

Instead of reducing a peak to summary scalars, retain a short continuous window
centered on each candidate peak, with relative angular coordinates.

Purpose: preserve local shape while permitting event-level attention.

### R4. Multi-resolution tokens

Represent the spectrum simultaneously at:

- fine resolution for narrow peaks;
- medium resolution for peak clusters;
- coarse resolution for global intensity distribution.

Purpose: avoid forcing one token scale to represent all physical structures.

### R5. Hybrid CNN-to-attention tokens

Use a convolutional encoder to produce stable local features and then apply
attention to the resulting feature sequence or detected feature events.

Purpose: combine local inductive bias with long-range relation modeling.

### R6. Crystallography-informed relational encoding

Candidate relational features include:

- angular separations;
- d-spacing ratios;
- relative peak order;
- pairwise spacing embeddings;
- missing-reflection masks where defensible;
- wavelength-aware coordinate transformation.

These must be introduced carefully and must not assume unavailable indexing or
candidate structures.

## 5. Experimental decomposition

### Stage 0. Reproduce the architecture gap

Under one frozen data split, simulator, preprocessing, optimizer budget, and
checkpoint rule, reproduce:

- ResNet continuous-spectrum baseline;
- current PAMPT/Transformer baseline.

No mechanism claim is allowed until the gap is reproduced under controlled
conditions.

### Stage 1. Locate where information is lost

Hold the classifier family as constant as possible and compare:

1. continuous spectrum;
2. fixed patches;
3. detected peak scalars;
4. peak neighborhoods;
5. CNN feature tokens.

The objective is to determine whether degradation begins in tokenization or in
the attention encoder.

### Stage 2. Perturbation-stability audit

For each parent structure, generate paired clean and perturbed views and measure:

- detected peak-count change;
- peak matching rate;
- peak-order changes;
- token insertion/deletion rate;
- token embedding distance;
- representation Lipschitz-like sensitivity to small parameter changes;
- class-prediction stability.

This directly tests whether continuous physical changes become discontinuous in
model representation space.

### Stage 3. Capacity- and budget-matched backbone comparison

Compare models with approximately matched:

- parameter count;
- training steps;
- optimizer budget;
- effective receptive field;
- number of input views.

Candidate models:

- 1D ResNet;
- compact CNN;
- fixed-patch Transformer;
- peak-token Transformer;
- CNN-attention hybrid.

The purpose is to separate architecture bias from raw model capacity.

### Stage 4. Data-scale study

Use nested parent-structure subsets to test whether the Transformer gap narrows
with more independent structures.

This distinguishes:

- a representation-design failure;
- a data-hungry but ultimately competitive architecture;
- an optimization failure.

### Stage 5. Augmentation-compatibility study

Evaluate each representation under:

- level-0/minimal perturbation;
- single-factor perturbations;
- combined in-range perturbations;
- frozen OOD perturbations.

The primary question is whether a representation remains stable under the
specific physical transformations used in training.

### Stage 6. Generalization beyond PXRD

Only after the PXRD mechanism is supported, evaluate one external signal family
such as Raman or FTIR to test whether the conclusion concerns scientific signal
structure rather than PXRD alone.

## 6. Key metrics

### Task metrics

- Macro-F1;
- per-class F1;
- mean single-factor OOD Macro-F1;
- worst-class F1;
- calibration metrics where relevant.

### Learnability and optimization metrics

- train accuracy and loss;
- train–validation gap;
- convergence speed;
- gradient norms;
- representation collapse diagnostics;
- seed stability.

### Representation metrics

- token stability under small perturbations;
- peak matching consistency;
- embedding distance between paired views;
- sensitivity to peak shift, broadening, background, and noise;
- information retained after tokenization;
- robustness to missing or merged peaks.

### Efficiency metrics

- parameter count;
- FLOPs or approximate compute;
- memory;
- training time;
- inference latency.

## 7. Minimum viable study

The first executable version should remain small:

1. freeze one representative subset and simulator profile;
2. reproduce ResNet versus current fixed-patch/PAMPT gap;
3. implement only three representations:
   - continuous full spectrum;
   - fixed overlapping patches;
   - CNN feature tokens plus compact attention;
4. audit paired-view representation stability under zero shift, broadening, and
   background;
5. run at least three matched seeds;
6. stop before introducing peak detection, crystallographic pair encodings, or
   cross-domain datasets.

The MVP succeeds if it can identify whether the main bottleneck lies in:

- tokenization;
- Transformer optimization;
- data scale;
- augmentation incompatibility;
- or an interaction among them.

It does not require the Transformer to beat ResNet.

## 8. Stronger second version

If the MVP indicates tokenization is the bottleneck, the second version may add:

- differentiable soft peak proposals;
- uncertainty-aware peak tokens;
- peak-neighborhood tokens;
- relative d-spacing attention bias;
- multi-resolution token hierarchies;
- set/graph attention over peaks;
- masked signal modeling or contrastive pretraining.

Each addition must answer a diagnosed failure mode. The module must not become a
collection of fashionable components without causal experimental isolation.

## 9. Failure interpretations

### Outcome A. CNN remains superior across all tokenizations

Interpretation: local convolutional inductive bias is genuinely advantageous
for the available data and perturbations. This is still a useful scientific
result.

### Outcome B. CNN-attention hybrid closes the gap

Interpretation: attention is useful only after stable local feature extraction.
The original failure was primarily input representation mismatch.

### Outcome C. Peak tokens help clean data but fail under perturbation

Interpretation: event-level tokenization is physically meaningful but unstable
under measurement variation. Detection uncertainty or soft tokenization is
required.

### Outcome D. Transformer catches up only with more data or pretraining

Interpretation: the architecture is not structurally wrong but has weaker
sample efficiency under the current setting.

### Outcome E. No controlled comparison reproduces the original gap

Interpretation: the previous difference was caused by implementation,
optimization, or budget mismatch rather than a general architecture principle.

## 10. Guardrails

- Do not reopen or modify V9 method selection.
- Do not replace the frozen V9 ResNet before this module is activated and
  independently validated.
- Do not use simulated Test or real XRD during representation design.
- Do not claim Transformer inferiority from one implementation.
- Do not compare models with unequal data exposure or hidden tuning budgets.
- Do not call peak tokens physically superior without perturbation-stability
  evidence.
- Do not infer a universal CNN-versus-Transformer conclusion from PXRD alone.

## 11. Application narrative

This module records an important transition in the project:

> The failure of a more complex peak-aware Transformer was not treated merely as
> an engineering setback. It motivated a broader question about how scientific
> measurements should be tokenized and which inductive biases are compatible
> with their physical data structure.

The research identity is therefore not “trying another XRD model,” but:

> studying representation construction and architecture–augmentation
> compatibility for imperfect scientific signals.

## 12. Activation requirements

Before activation, freeze:

1. exact representation variants;
2. model-capacity matching rule;
3. parent-structure split and development-only evaluation panels;
4. optimizer and compute-budget policy;
5. perturbation-stability metrics;
6. minimum seed count;
7. success and failure interpretation rules;
8. prohibition on simulated-Test and real-XRD access;
9. code and configuration hashes.

Until activation, this file preserves the scientific hypothesis and project
journey only.