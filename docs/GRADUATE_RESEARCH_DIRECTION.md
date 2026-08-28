# 研究方向、申请叙事与导师检索

本文件合并原先分散的申请叙事、研究方向框架、方向地图和日本导师检索关键词。内容保持原意，标题层级仅为适应合并文档而下调。

- [申请与面试叙事](#application-narrative)
- [研究生路线框架](#route-framework)
- [研究方向地图](#research-direction-map)
- [日本导师检索关键词](#japan-advisor-keywords)

<a id="application-narrative"></a>

## 原文件：`APPLICATION_RESEARCH_NARRATIVE.md`

## Application Research Narrative

**Updated:** 2026-08-28

### Research story

My project studies robust machine learning for powder X-ray diffraction (PXRD). Simulated spectra provide controlled access to realistic measurement variation, including peak shifts, broadening, preferred orientation, background and noise. The central idea is that a simulator provides useful relationships in addition to labeled samples: multiple perturbed spectra generated from one parent structure are measurements of the same latent physical object.

I converted this relationship into measurement-equivalence supervision. For each parent structure, the training system generates two online views and applies Jensen-Shannon prediction consistency while preserving the same structures, perturbation distribution, backbone, optimization and data exposure as a Dynamic ERM baseline.

The final comparison uses a ResNet-18-GN backbone for seven-crystal-system classification. Across five matched seeds, JS consistency improved simulated Validation mean single-factor OOD Macro-F1 by `+0.046569`. Evaluation of the already selected checkpoints on the simulated Test produced a `+0.054600` mean paired improvement. All five paired effects were positive on both the Validation and Test sets.

The same scientific conclusion is supported by two experimental domains with complementary roles. On RRUFF-301, JS-pretrained models improved locked-test Macro-F1 by `+0.0433`, `+0.0460` and `+0.0545` at K=1/2/5 labels per class, showing better label efficiency. On the independent, naturally imbalanced CNRS-318 source, all 5/5 frozen zero-shot seed comparisons favored JS (mean paired `+0.0187`); pooled Macro-F1, balanced accuracy, accuracy, ECE, NLL and Brier score also improved. CNRS remains a difficult sim-to-real setting with low absolute accuracy and larger uncertainty in low-support classes, so I present it as supporting independent-source evidence rather than claiming that real-domain classification is solved.

This work strengthened my interest in robust and data-efficient learning for scientific measurements. It also taught me how to convert information already available in a scientific data-generation process into a focused machine-learning hypothesis, a matched comparison and a reproducible result.

### Application version

My research focuses on robust machine learning for scientific measurements. In powder X-ray diffraction, simulated training patterns can vary with peak position, broadening, preferred orientation, background and noise. I recognized that an online simulator provides more than labeled spectra: it knows which perturbed views originate from the same parent crystal. I used this relationship as measurement-equivalence supervision by adding Jensen-Shannon prediction consistency to a matched Dynamic ERM design. The comparison kept the crystal structures, perturbation distribution, ResNet-18-GN backbone, optimization and two-view data exposure fixed. Across five matched seeds, consistency improved simulated Validation OOD Macro-F1 by `+0.046569`, and the already selected checkpoints achieved `+0.054600` on the simulated Test. JS also improved the full K=1/2/5 RRUFF few-shot learning curve and favored all 5/5 seeds on a second CNRS experimental source, with classification and probability-quality metrics moving together. The project demonstrates how scientific data-generation relationships can become structured supervision for robust and label-efficient classification while retaining honest limits on the remaining sim-to-real gap.

### Interview version

I worked on making simulated PXRD classifiers robust to realistic measurement variation. The key insight was that the simulator knows when two spectra are different measurements of the same parent crystal. I turned that relationship into a consistency objective and compared it with matched dynamic training. Five-seed simulated OOD evaluation showed a `+5.46` percentage-point Test gain; the same model family adapted more efficiently across the RRUFF few-shot learning curve and improved all five seed comparisons on an independent CNRS source. That cross-domain evidence made the project a concrete example of using scientific structure as supervision rather than treating simulation only as a source of more samples.

### Recommended claim language

- “I reframed simulator-retained parent identity as measurement-equivalence supervision.”
- “I compared Dynamic ERM and JS consistency under matched structures, perturbations, optimization and data exposure.”
- “Five matched seeds showed a `+0.046569` Validation gain and a `+0.054600` simulated Test gain.”
- “Under identical real-label budgets, JS improved Macro-F1 across the K=1/2/5 RRUFF few-shot learning curve.”
- “On CNRS-318, all 5/5 seeds and multiple classification and calibration metrics favored JS; uncertainty remains larger because the domain is naturally imbalanced.”
- “The evidence supports improved robustness and label efficiency, not a claim that zero-shot sim-to-real classification is solved.”

---

<a id="route-framework"></a>

## 原文件：`master_route_framework.md`

## Master Route Framework: Three Technical Trees for Graduate Study and Career Screening

### Purpose

This document replaces the earlier habit of treating several options as parallel "routes". The current framework is a three-level / three-tree structure built around a shared computational-and-physics foundation.

The three top-level branches are:

1. **A. Measurement -> Inference**
2. **B. AI-assisted Physical Modeling**
3. **C. EE / IC Design**

Branches A and B form the core **AI + physical systems** world. Branch C is an intentionally separate, high-quality EE / semiconductor-design path that does not require AI to justify itself.

---

## A. Measurement -> Inference

### Core question

> We already have a physical measurement. How can computation / machine learning extract reliable physical information from it?

Unified form:

```text
measured signal / image / spectrum / waveform
    -> computational analysis / inverse inference / ML
    -> structure / parameter / defect / state / anomaly
```

The emphasis is **not** on designing the instrument itself. New light sources, detectors, optical paths, sensor fabrication, higher spatial resolution, or instrumentation hardware should be treated as secondary unless the work clearly includes:

```text
measured data -> computational inference
```

### A-METRO — Semiconductor Metrology / Scientific Instrument Analysis

Typical data:

- SEM / TEM / STEM
- e-beam inspection
- X-ray measurements
- optical metrology
- scatterometry
- ellipsometry
- diffraction / spectroscopy

Typical outputs:

- CD
- overlay
- roughness
- defect class / defect geometry
- structure parameters
- process parameters

Representative pipeline:

```text
SEM / TEM / e-beam / optical / X-ray data
    -> algorithms / inverse problems / ML
    -> CD / defects / geometry / process state
```

This is the most direct industrial continuation of the current XRD project.

Possible industry exits include semiconductor inspection and metrology companies such as KLA, Nova, Applied Materials, Hitachi High-Tech, Onto Innovation, ASML, and related equipment / metrology firms.

### A-BME — Biomedical Measurement / Imaging Inference

Same computational structure, different physical object:

```text
CT projection / MRI k-space / ultrasound echo / physiological signal
    -> reconstruction / parameter estimation / inference / ML
    -> anatomy / tissue property / lesion / physiological state
```

Interest in BME should therefore be understood as interest in a mature application of **measurement -> inference**, not necessarily as a desire to move into medicine itself.

### A-IND — Industrial Measurement / NDT / Condition Monitoring

This branch should not be reduced to "industrial ultrasound". It includes:

- ultrasonic testing
- industrial CT
- acoustic emission
- guided waves
- thermal imaging
- vibration monitoring
- electromagnetic NDT
- structural health monitoring

Unified task:

```text
measured waveform / image / sensor signal
    -> inference
    -> crack / defect / geometry / material state / remaining life
```

---

## B. AI-assisted Physical Modeling

### Core question

The center of gravity is no longer simply "I have a measurement and want to interpret it." Instead:

> I have a physical system, equations, or simulator. How can data / AI make the model faster, more accurate, better calibrated, easier to identify, or easier to use for prediction and optimization?

Unified structure:

```text
physical equations / simulator
    + measurements / data
    + ML / optimization
    -> calibrated / accelerated / surrogate / predictive model
```

A and B can overlap, but the research subject is different:

- **A** starts from the measurement.
- **B** starts from the physical model / simulator / system representation.

### B-DEVICE — Semiconductor Device Modeling / TCAD

Physical basis may include:

- Poisson equation
- drift-diffusion
- carrier transport
- material / device physics
- TCAD
- compact models

AI / computational roles may include:

- surrogate modeling
- parameter calibration
- inverse parameter extraction
- compact modeling
- model-order reduction
- sensitivity analysis
- optimization
- uncertainty quantification
- TCAD acceleration

A typical A/B boundary case is:

```text
measured I-V
    -> infer mobility / trap density / interface parameters
    -> calibrate TCAD
```

This can legitimately receive both `A-METRO` and `B-DEVICE` labels.

### B-BATTERY — Battery Modeling / Digital Twin

The attractive version of battery research is not merely image classification. It is closer to:

```text
electrochemical / ageing model
    + voltage / current / EIS / temperature data
    + ML
    -> state / degradation / lifetime / model parameters
```

Typical topics:

- SOC estimation
- SOH estimation
- RUL prediction
- degradation modeling
- parameter identification
- surrogate electrochemical models
- physics-informed ML
- battery digital twins

The common kernel with semiconductor device modeling is:

> **physics model + real data + inference / ML**

---

## C. EE / IC Design

### Core principle

This branch is intentionally separated from A and B.

It does **not** need to satisfy an "AI + physics" narrative in order to be considered a valid or strong direction.

Representative areas:

- Analog IC
- Mixed-Signal IC
- RFIC
- Digital IC
- Physical Design
- Verification
- EDA / CAD

AI may participate through:

- AI-assisted analog design
- placement / routing optimization
- verification
- EDA automation
- design-space exploration

However, even a role that uses little or no AI, such as **Analog IC Designer**, can still be an excellent and acceptable career outcome.

Therefore the project / application should never be forced into an AI framing merely for narrative consistency.

---

## Standard Screening Labels

Use the following six labels for future graduate-program, advisor, laboratory, and career screening:

- `A-METRO` — Semiconductor metrology / scientific-instrument measurement inference
- `A-BME` — Biomedical measurement / imaging / physiological inference
- `A-IND` — Industrial measurement / NDT / condition monitoring
- `B-DEVICE` — Semiconductor device modeling / TCAD / device parameter inference
- `B-BATTERY` — Battery physical modeling / state estimation / digital twin
- `C-IC` — IC design / EDA / semiconductor electronic design

A program or laboratory may receive multiple labels.

Example scoring style:

```text
A-METRO  ★★★★★
B-DEVICE ★★★★☆
C-IC     ★★☆☆☆
```

This is preferable to a single vague score such as "Scientific ML fit = 8.3" because it preserves **which concrete exits the program actually supports**.

---

## How to Screen Graduate Programs

Do not ask only:

> Is this program Nano / AI4Science / Scientific ML / Materials Informatics?

Instead ask:

> Which of A-METRO, A-BME, A-IND, B-DEVICE, B-BATTERY, and C-IC can this program genuinely support?

For each program, evaluate separately:

1. courses
2. thesis groups / supervisors
3. available research projects
4. internship ecosystem
5. industry exits
6. whether the computational role matches the intended branch

This is especially important for broad programs such as Nano, Applied Physics, EE, BME, Engineering Physics, or Materials programs whose titles alone do not determine the real research and career exits.

---

## Position of the Current XRD Project

The current XRD project sits most directly in:

```text
A-METRO
```

because it starts from an experimentally meaningful physical measurement and asks how to infer latent structural information robustly.

Its transferable methodological components include:

- simulator-based training
- physically structured augmentation
- Sim2Real
- robustness under measurement shift
- few-shot adaptation
- uncertainty / calibration
- measurement-aware machine learning

These methods can transfer horizontally to `A-BME` or `A-IND`, and can also serve as a bridge toward `B-DEVICE` where forward models, simulators, and parameter inference become more central.

Thus the project should be treated as an **entry point into the A/B world**, not as a permanent commitment to XRD itself.

---

## Overall Structure

```text
                    Computational / Physics Foundation
                              |
            +-----------------+------------------+
            |                 |                  |
      A. Measurement      B. Physical        C. EE / IC
        -> Inference        Modeling            Design
            |                 |                  |
     AI interprets        AI assists         Circuit / chip
      measurements         models               design
            |                 |
      +-----+-----+       +---+---+
      |     |     |       |       |
   A-METRO A-BME A-IND B-DEVICE B-BATTERY
```

### Stable interpretation

- **A and B** are the core "AI + physical systems" research universe.
- **C** is an intentionally separate right turn into high-quality EE / semiconductor design.
- The shared foundation is computation + physics, not commitment to one measurement modality or one material system.
- Future program screening should focus on **real technical exits**, not program names.

---

<a id="research-direction-map"></a>

## 原文件：`research_direction_map.md`

## Research Direction Map: AI for Characterization and Measurement Systems

### Motivation

The XRD project is gradually positioned not only as a materials classification task, but as a study of machine learning for scientific measurement systems.

The core research identity is:

> Physics-aware machine learning for scientific measurements: understanding how measurement generation processes, domain shifts, and limited real data affect AI models.

The transferable capability is not restricted to XRD. The same framework can extend to other scientific sensing and imaging systems.

---

### Primary Direction

#### AI + Characterization

Main keywords:

- scientific machine learning
- AI for characterization
- computational microscopy
- physics-informed machine learning
- domain adaptation for scientific imaging
- measurement-aware representation learning

Representative problems:

- Sim2Real transfer
- domain shift between simulation and experiment
- few-shot adaptation
- uncertainty calibration
- physics-guided learning
- robust representation learning

---

### Potential Transfer Domain: Semiconductor Inspection

Keywords:

- semiconductor defect inspection
- SEM/e-beam inspection
- automated defect characterization
- computational microscopy for semiconductor defects
- defect inspection + ML
- wafer inspection + image analysis

Research connection:

XRD:

```
crystal structure
        |
measurement generation
        |
XRD spectrum
        |
AI prediction
```

Semiconductor inspection:

```
wafer structure / defect physics
        |
imaging process (SEM, e-beam, optical inspection)
        |
microscopy image
        |
AI detection and characterization
```

Shared machine learning challenges:

- limited labeled data
- instrument-dependent distribution shift
- simulation-to-experiment gap
- need for physics-aware representations
- robust defect/feature recognition

---

### Broader AI4Science Bridge

The long-term positioning is:

```
AI for Materials
        |
AI for Characterization
        |
AI for Scientific Measurement Systems
        |
AI for Imaging / Sensing / Inverse Problems
```

Possible future applications:

- X-ray diffraction
- SEM/e-beam microscopy
- semiconductor wafer inspection
- optical metrology
- CT/MRI reconstruction
- other computational imaging problems

---

### Research Narrative for Applications

The project development story should emphasize:

1. Starting from XRD as a scientific measurement problem.
2. Identifying that scientific data are generated by physical measurement processes rather than ordinary datasets.
3. Designing ML methods that exploit physical relationships and improve robustness under measurement shifts.
4. Extending this idea toward broader scientific imaging and industrial inspection systems.

The key identity is not "using AI for materials" but:

> Developing reliable AI methods for understanding and interpreting scientific measurements.

---

### Research Scope Clarification: Physical Measurement -> Inference

A crucial distinction is that the intended research direction is **not primarily about designing imaging or measurement hardware**, but about what happens **after a physical measurement has been obtained**.

The central problem is:

> Given a physical measurement, how can we reliably infer the latent structure, state, parameters, or defects that generated it?

For the current XRD project, the pipeline is:

```text
crystal
  -> XRD measurement
  -> diffraction pattern
  -> structural inference
```

The main research focus is the final mapping:

```text
measurement -> inference
```

rather than X-ray source design, detector design, optical path engineering, or diffractometer hardware.

A general physical measurement pipeline can be divided into four layers:

```text
measurement-system design
  -> signal acquisition
  -> reconstruction / preprocessing
  -> inference
```

The current research identity is clearly concentrated toward the right side of this chain.

Examples of the same research interface across different domains include:

```text
XRD pattern -> crystal system / structural state
SEM image -> defect / CD / roughness
Raman spectrum -> composition / physical state
scatterometry signal -> 3D geometry parameters
```

Although these measurements come from diffraction, microscopy, spectroscopy, or optical metrology, the underlying machine-learning task is the same:

> **Physical Measurement -> Latent Physical Information**

This gives a more precise long-term research identity than the broad label of "imaging".

#### Relation to inverse problems

Reconstruction itself is a form of generalized inference.

For example:

```text
ptychographic diffraction measurements -> object image
```

This is an inverse inference problem where the unknown is a high-dimensional spatial field.

The current XRD task:

```text
XRD pattern -> crystal system
```

infers a low-dimensional discrete variable.

Semiconductor metrology may instead involve:

```text
SEM / scatterometry -> (CD, height, sidewall angle, roughness)
```

which corresponds to a small set of continuous physical parameters.

Therefore, the possible future research space forms a continuum:

```text
classification
  -> parameter estimation
  -> property inversion
  -> structural recovery
  -> full image reconstruction
```

The current project lies toward the classification side, but its methodology can progressively move toward more difficult inverse problems.

#### Implication for graduate-advisor search

When screening future advisors, the most important question is not simply:

> Does this group work on XRD, SEM, or imaging?

A more useful criterion is:

> Does this group perform computational inference from real physical measurements?

Particularly relevant interfaces are:

```text
measurement signal -> structure / parameter / state / defect
```

with research involving:

- physical forward models
- simulated data
- noise and instrumental bias
- sim-to-real transfer
- robustness under measurement shift
- uncertainty and calibration
- low-data or few-shot adaptation

This means groups working on microscopy, semiconductor metrology, computational imaging, spectroscopy, diffraction, or related inverse problems can all be relevant, provided the intended entry point is **computational inference rather than measurement-system hardware design**.

This distinction should be preserved in future application narratives and advisor searches.

---

### Application Scope Clarification: Experimental Measurement Data -> Useful Information

The application scope should be kept broader than either **computer vision** or **strict mathematical inverse problems**.

The intended research object is any experimentally generated measurement data — curves, spectra, diffraction patterns, microscopy images, detector outputs, or sensor responses — from which machine learning can extract scientifically useful information.

A general pipeline is:

```text
sample
  -> measurement / imaging technique
  -> experimental data
  -> computational analysis and inference
  -> scientific or engineering conclusion
```

The intended position is primarily in the second computational box:

> **computational analysis and inference from experimental measurement data**

rather than in the design of the measurement or imaging hardware itself.

Representative tasks include:

```text
XRD spectrum -> crystal system / phase fraction / lattice or structural parameters
SEM image -> defect class / critical dimension / roughness / geometry
Raman / XPS / EELS -> composition / state / material properties
sensor response curve -> parameter / anomaly / physical state
scatterometry -> geometric parameters
```

This framing matters because not every relevant task is a strict inverse problem. Classification, anomaly detection, quality assessment, trend analysis, parameter estimation, and defect recognition may not all fit the same mathematical inverse-problem definition, but they share the same practical structure:

> **measurement data -> useful information**

Therefore the broader application identity is:

> **Machine learning for computational analysis and inference of experimental physical measurements.**

Within that broad application domain, the more specific methodological interest remains:

> **Machine learning and inference on physical measurement data, especially where physical models, simulated data, real measurement bias, sim-to-real transfer, robustness, low-data adaptation, and uncertainty matter.**

This also prevents the research direction from being narrowed to image recognition. The relevant data modalities can be images, spectra, one-dimensional curves, diffraction patterns, multidimensional detector data, or other scientific measurements.

#### Practical wording for applications and conversations

A natural concise description is:

> I am interested in machine learning for the analysis and inference of experimental physical measurement data, for example extracting structures, defects, or physical parameters from diffraction, microscopy, spectroscopy, or other instrument-generated data.

This wording intentionally does **not** imply a primary interest in lens design, optical paths, detectors, or imaging hardware. It also remains broad enough to include semiconductor metrology, microscopy, spectroscopy, XRD, computational imaging data, and other measurement-driven AI problems.

---

### Method vs Direction: Do Not Confuse the Two

A key correction from family discussion is:

> **"Image recognition, data judgment, analysis, and inference" describe how AI is used; they are methods or work interfaces, not by themselves a complete research direction.**

This distinction should remain explicit in future planning.

A useful three-level hierarchy is:

| Level | Current interpretation |
|---|---|
| Work paradigm / methodological interface | AI-assisted processing, judgment, analysis, and inference on experimental data |
| Machine-learning questions of interest | Sim2Real, robustness, low-data learning, physics-guided learning, uncertainty, inverse inference |
| Concrete application directions | semiconductor inspection/metrology, XRD, SEM/TEM analysis, spectroscopy, scientific-instrument data analysis |

Therefore, **measurement -> inference** should not be treated as a narrow field label or the only possible research direction. It is better understood as a recurring computational interface that can appear inside many concrete domains.

The broad positioning can be written as:

> **AI-assisted analysis of experimental measurement data.**

Within this broad scope, the preferred research problems are those where AI operates on the right-hand side of the experimental chain:

```text
experimental data
  -> judgment / analysis / parameter extraction / anomaly detection / structural inference
```

rather than primarily on instrument, detector, optical-path, or acquisition-system design.

This also explains why the research scope should not be reduced to computer vision. Relevant examples include:

- SEM defect image -> defect classification or geometry estimation
- scatterometry curve -> CD / sidewall angle
- ellipsometry spectrum -> thickness / optical constants
- e-beam measurements -> defect characterization
- electrical response curves -> process anomaly assessment
- Raman spectrum -> stress / composition
- XRD pattern -> lattice / phase / structural information

All of these fit the broader methodological paradigm, even though the data modality and scientific domain differ.

#### How to use this distinction when screening advisors

Do **not** filter advisors only by whether their data look like XRD, SEM, images, spectra, or curves.

Instead ask:

> **What experimental problem is this group solving, and what role does AI play in the experimental workflow?**

Groups are particularly relevant when AI is used to extract scientifically meaningful structure, state, defect, or parameter information from experimental measurements.

Within that broad set, the strongest personal fit is likely to involve:

```text
experimental measurement data
+ physical generation mechanism
+ machine-learning inference
+ simulation / forward models
+ real-world measurement discrepancy
+ sim-to-real / robustness / low-data adaptation
```

Thus the stable principle for future advisor search and application narratives is:

> **The method is AI-assisted experimental-data analysis; the research direction is determined by the scientific problem and application domain in which that method is used.**

---

<a id="japan-advisor-keywords"></a>

## 原文件：`japan_advisor_search_keywords.md`

## Japan Advisor Search Keywords: Measurement Informatics and AI-assisted Experimental Analysis

### Motivation

For Japanese graduate-advisor searches, keywords should not be limited to broad AI terms such as AI4Science or AI for Materials. Japanese groups often describe the research from the experimental measurement domain rather than from the machine-learning method.

The recommended search concept is:

> AI-assisted analysis and inference of experimental measurement data.

The focus is not imaging hardware design or measurement-system engineering, but applying computational methods after experimental data acquisition.

---

### Primary Japanese Keywords

#### 計測インフォマティクス

Most important umbrella keyword.

Related concepts:

- Measurement Informatics
- Experimental Informatics
- Data-driven measurement science

Potential coverage:

- XRD
- microscopy
- spectroscopy
- semiconductor metrology
- scientific instruments

---

#### 顕微鏡計測インフォマティクス

Related to:

- SEM
- TEM/STEM
- AFM
- optical microscopy
- computational microscopy

---

#### 半導体検査 × 数理解析

Related to:

- semiconductor defect inspection
- wafer inspection
- defect characterization
- mathematical analysis

---

#### 半導体計測 × データ科学

Related to:

- semiconductor metrology
- process monitoring
- scatterometry
- ellipsometry
- defect analysis

---

#### 電子顕微鏡 × 機械学習

Related to:

- electron microscopy image analysis
- automated microscopy
- defect recognition
- structure analysis

---

#### 放射光 × 機械学習

Related to:

- synchrotron measurement
- X-ray analysis
- X-ray imaging
- spectroscopy

---

#### X線解析 × 機械学習

Broader and more useful than only X-ray topography.

Related to:

- diffraction analysis
- X-ray spectroscopy
- structural inference

---

#### スペクトル解析 × 機械学習

Related to:

- Raman
- XPS
- EELS
- IR spectroscopy

---

### Semiconductor Device Inverse Problems / Property Estimation

This branch targets groups that infer latent device or material parameters from measured electrical, optical, or structural responses. It is particularly relevant when searching for semiconductor-oriented work that is closer to parameter inference than to defect-image classification.

Recommended Japanese search keywords:

- 半導体物性 逆推定
- 半導体デバイス 逆問題
- デバイスパラメータ抽出
- トランジスタ特性 物性推定
- デバイスシミュレーション 機械学習
- 半導体物性 機械学習

Useful adjacent combinations:

- 半導体デバイス パラメータ推定
- デバイス特性 逆推定
- 半導体計測 パラメータ抽出
- TCAD 機械学習
- TCAD 逆問題
- トランジスタ モデルパラメータ抽出
- I-V特性 機械学習
- 電気特性 パラメータ推定

Conceptually, this branch corresponds to:

```text
measured device response
        -> computational inference
        -> material / device / process parameters
```

Representative examples include:

```text
I-V / C-V characteristics -> mobility / threshold voltage / trap or interface parameters
optical / electrical response -> material-property estimation
measured transistor characteristics -> compact-model or physical parameters
device simulation + experimental data -> inverse parameter identification
```

This branch should be treated as a concrete **semiconductor application direction** under the broader methodological interface of AI-assisted experimental-data analysis.

---

### Search Tree

```text
計測インフォマティクス
        |
        +-- 顕微鏡計測インフォマティクス
        |
        +-- 半導体計測・検査
        |       |
        |       +-- 欠陥検査・画像解析
        |       +-- デバイス逆問題・物性推定
        |
        +-- 放射光・X線計測
        |
        +-- スペクトル解析
        |
        +-- 電子顕微鏡 × ML
```

Methods can be added as secondary keywords:

- 機械学習
- 深層学習
- データ科学
- 数理解析
- インフォマティクス
- 逆問題
- 逆推定
- パラメータ推定

---

### Search Principle

Do not search only by data modality:

- XRD
- SEM
- image
- spectrum

Instead evaluate:

> What experimental problem is the group solving, and what role does AI play in the workflow?

The preferred groups are those where:

```text
experimental measurement
        -> computational analysis
        -> structure / defect / parameter / state extraction
```

This keeps the research identity broad enough to include semiconductor inspection, semiconductor device parameter inference, microscopy, spectroscopy, diffraction, and other measurement-driven AI problems.

---

### Trajectory-based Advisor Screening: Find the Transition, Not the Keyword

For the Japanese semiconductor track, advisor search should operate at a higher level than checking whether a recent paper title contains "machine learning".

The preferred target is a **traditional semiconductor / measurement PI whose research trajectory is visibly turning toward computational analysis**.

A characteristic trajectory is:

```text
1980s / 1990s:
semiconductor materials / devices / crystal defects / XRD / XRT / synchrotron characterization
        |
        v
20-30 years of domain accumulation:
SiC / GaN / wafer / device problems
+ industrial collaboration
+ access to real measurement systems or large facilities
        |
        v
2018-2026 transition:
high-throughput measurement
whole-wafer data
large-scale experimental datasets
automatic analysis
quantitative analysis
informatics
machine learning
defect classification
        |
        v
new computational sub-line continues to grow
```

The goal is therefore **not to search from AI scholars toward semiconductor applications**, but to search in the opposite direction:

> Start from established Japanese semiconductor / metrology PIs, then trace their recent publication trajectory to determine whether a genuine algorithmic sub-line is emerging.

#### Three screening questions

##### 1. Is the old core field genuinely strong?

The PI should have a real, long-standing base in semiconductor industry-relevant problems rather than being a generic materials professor who happens to coauthor one semiconductor paper.

Strong signals include:

- SiC / GaN / power semiconductor
- wafer inspection or defect evaluation
- X-ray topography / diffraction / synchrotron characterization
- semiconductor metrology
- device or process evaluation
- long-term industrial collaboration
- use of SPring-8 or other major facilities

##### 2. Is the computational transition real and sustained?

The key evidence is not one isolated collaboration paper. Prefer groups where the last 5-8 years show repeated emergence of terms and activities such as:

- 自動解析
- 自動判定
- 欠陥自動分類
- 数理解析
- 機械学習
- インフォマティクス
- quantitative analysis
- automatic defect classification
- high-throughput
- whole-wafer analysis

A repeated sequence of such work is stronger evidence than a single paper with an ML coauthor.

##### 3. Can a student plausibly occupy the new computational sub-line?

The best fit is not merely a famous senior PI with an ML collaboration. The practical question is:

> Is there room for a student who can push the downstream algorithmic analysis of the group's existing measurement data?

Positive signs include:

- experimental data generation already mature
- data volume growing faster than manual analysis capacity
- a new automatic-analysis topic appearing in several recent projects
- few existing students fully dedicated to ML/informatics
- clear need for classification, parameter extraction, inverse inference, robustness, or high-throughput analysis

This is particularly attractive because the student can contribute through the **measurement-data -> inference** interface without needing to become the person who fabricates the device or designs the instrument.

#### Why this transition can be structurally inevitable

In some semiconductor metrology fields, the computational turn is not simply an AI trend.

A typical mechanism is:

```text
mature semiconductor measurement technique
        |
        v
whole-wafer / high-throughput acquisition becomes possible
        |
        v
experimental data volume increases sharply
        |
        v
manual interpretation becomes the bottleneck
        |
        v
automatic analysis / classification / quantitative inference becomes necessary
```

This creates exactly the kind of advisor environment sought here: deep domain expertise and industrial relevance already exist, while the computational layer is still expanding.

#### Practical search procedure

For finding the second or third advisor with this profile:

1. Build a candidate pool from established Japanese researchers in:
   - SiC / GaN / power semiconductor
   - wafer inspection
   - X-ray topography
   - synchrotron characterization
   - defect evaluation
   - semiconductor metrology

2. Trace each PI's publications backward and forward, especially **2018-2026**.

3. Mark the first appearance and subsequent continuity of:
   - automatic analysis
   - defect classification
   - high-throughput analysis
   - quantitative analysis
   - informatics / machine learning

4. Distinguish:
   - **one-off ML collaboration**
   - **real research trajectory transition**

5. Prioritize PIs where the new computational branch is growing but not yet fully saturated with dedicated algorithm students.

The ideal profile can be summarized as:

> **Old semiconductor / metrology PI + strong real data and industrial problems + recent sustained computational turn + room for a student to own the algorithmic sub-line.**

This trajectory-based rule should take priority over simplistic ratings such as "AI level: five stars" or whether the PI currently labels the lab as AI/ML.
