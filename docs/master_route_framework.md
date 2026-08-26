# Master Route Framework: Three Technical Trees for Graduate Study and Career Screening

## Purpose

This document replaces the earlier habit of treating several options as parallel "routes". The current framework is a three-level / three-tree structure built around a shared computational-and-physics foundation.

The three top-level branches are:

1. **A. Measurement -> Inference**
2. **B. AI-assisted Physical Modeling**
3. **C. EE / IC Design**

Branches A and B form the core **AI + physical systems** world. Branch C is an intentionally separate, high-quality EE / semiconductor-design path that does not require AI to justify itself.

---

# A. Measurement -> Inference

## Core question

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

## A-METRO — Semiconductor Metrology / Scientific Instrument Analysis

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

## A-BME — Biomedical Measurement / Imaging Inference

Same computational structure, different physical object:

```text
CT projection / MRI k-space / ultrasound echo / physiological signal
    -> reconstruction / parameter estimation / inference / ML
    -> anatomy / tissue property / lesion / physiological state
```

Interest in BME should therefore be understood as interest in a mature application of **measurement -> inference**, not necessarily as a desire to move into medicine itself.

## A-IND — Industrial Measurement / NDT / Condition Monitoring

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

# B. AI-assisted Physical Modeling

## Core question

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

## B-DEVICE — Semiconductor Device Modeling / TCAD

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

## B-BATTERY — Battery Modeling / Digital Twin

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

# C. EE / IC Design

## Core principle

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

# Standard Screening Labels

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

# How to Screen Graduate Programs

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

# Position of the Current XRD Project

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

# Overall Structure

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

## Stable interpretation

- **A and B** are the core "AI + physical systems" research universe.
- **C** is an intentionally separate right turn into high-quality EE / semiconductor design.
- The shared foundation is computation + physics, not commitment to one measurement modality or one material system.
- Future program screening should focus on **real technical exits**, not program names.
