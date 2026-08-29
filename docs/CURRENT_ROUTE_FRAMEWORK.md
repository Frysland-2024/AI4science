# Current Graduate Route Framework

**Status:** Current authoritative route framework  
**Updated:** 2026-08-29  
**Precedence:** This file supersedes the route-framework section embedded in `docs/GRADUATE_RESEARCH_DIRECTION.md` when the two differ. The older labels `A-METRO / A-BME / A-IND / B-DEVICE / B-BATTERY / C-IC` remain useful as historical aliases, but future screening should use the A1/A2/A3/B1/B2/C system below.

---

## 1. Core Structure

The overall three-tree structure remains valid:

```text
                    Computational / Physics Foundation
                              |
            +-----------------+------------------+
            |                 |                  |
      A. Measurement      B. Physical        C. EE / IC
        -> Inference        Modeling            Design
            |                 |                  |
     interpret measured    model / simulator    circuit / chip
       physical data       + data / inference      design
            |                 |
       A1 / A2 / A3         B1 / B2
```

The important update is not the top-level structure, but the **sub-branch definitions and priorities**.

- **A**: start from a real physical measurement and infer hidden physical information.
- **B**: start from a physical system/model/simulator and use data, optimization or ML to identify, accelerate, calibrate or predict it.
- **C**: EE / IC design. This is now a non-core option rather than a parallel central identity.

A and B remain the main **AI + physical systems** research world.

---

## 2. Current Route Table

| Label | Current direction | Core task | Representative examples | Priority |
|---|---|---|---|---|
| **A1** | Semiconductor Metrology / Scientific Instrument Analysis | real semiconductor/scientific measurement -> hidden structure / parameter / defect inference | ellipsometry/OHE -> thickness, mobility, carrier concentration; SEM/X-ray -> CD, roughness, defects; diffraction/spectroscopy -> structural parameters | **Main line** |
| **B1** | Semiconductor Device Modeling | device measurements + device/material physics -> parameter / model / performance inference | I-V/C-V -> device parameters; transport/device modelling; TCAD + inverse modelling; compact-model extraction; surrogate / calibration | **Main line** |
| **A2** | Quantitative Biomedical Sensing & Physiological Inference | optical/spectral/wearable/multimodal physiological measurement -> latent physiological parameter or state | PPG/NIR/Raman/spectroscopy/wearables -> glucose, SpO2, blood flow, blood pressure, hydration, tissue composition, metabolic state | **Important secondary line** |
| **A3** | Industrial Measurement / NDT / Condition Monitoring | industrial sensing signal -> defect / damage / state inference | ultrasound, acoustic emission, photoacoustic, industrial CT, guided waves, thermal/vibration/EM sensing -> crack, damage, material state | Secondary line |
| **B2** | Battery Modeling / State & Degradation Inference | electrochemical time series + models -> state / parameter / degradation inference | V/I/T/EIS -> SOC, SOH, RUL, degradation parameters; electrochemical surrogate / digital twin | **Opportunistic secondary line; further downgraded** |
| **C** | IC / EDA / related EE design | design / optimization | analog/mixed-signal/RF/digital IC, EDA, physical design, verification, computational lithography when relevant | **Non-core** |

### Priority order

The current practical interpretation is:

```text
A1 + B1  = main routes
A2       = important secondary route
A3       = secondary route
B2       = opportunistic secondary route, lower priority than before
C        = non-core; consider mainly when there is a clear device-physics / measurement interface or when the industrial outcome itself is sufficiently attractive
```

---

## 3. A Tree: Measurement -> Latent Physical Information

The three A branches are now intentionally defined by the **measured object**, not by data modality.

Unified structure:

```text
physical system
    -> measurement
    -> measured signal / spectrum / image / waveform
    -> computational inference
    -> latent physical information
```

The central screening question is:

> **What hidden quantitative variable, physical state, defect or parameter is being inferred from the real measurement?**

This is more important than whether the input happens to be an image, spectrum, waveform or time series.

### A1 — Semiconductor Metrology / Scientific Instruments

Canonical form:

```text
semiconductor / wafer / device
    -> SEM / X-ray / optical / spectral / electrical measurement
    -> computation / ML / inverse inference
    -> CD / overlay / roughness / defect / structure / material or process parameter
```

High-fit examples include:

- ellipsometry / optical Hall effect -> thickness, mobility, carrier concentration
- scatterometry -> CD / sidewall angle / geometry
- SEM / e-beam -> defect type, CD, geometry, process state
- X-ray topography / diffraction / synchrotron measurements -> defect or structural parameters
- spectroscopy -> material / process properties

This remains the most direct industrial continuation of the current XRD work.

### A2 — Quantitative Biomedical Sensing & Physiological Inference

**New formal definition:**

> **Quantitative Biomedical Sensing & Physiological Inference**  
> **定量生物医学感知与生理参数推断**

Core sentence:

> **We estimate / recover / infer physiological parameters or states from measured optical, spectral, wearable, or multimodal signals.**

Canonical form:

```text
PPG / NIR / Raman / spectroscopy / wearable / multimodal signal
    -> computational inference / calibration / ML
    -> glucose / SpO2 / blood flow / blood pressure / hydration / tissue composition / metabolic state
```

The upper-level concept is **quantitative physiological sensing**. Non-invasive glucose sensing is one especially concrete application, not the only target.

Strong A2 signals include:

- real physiological measurements
- quantitative latent-variable inference
- parameter estimation / inversion
- calibration
- uncertainty quantification
- domain shift across subjects, devices or acquisition conditions
- robustness / personalization / low-data adaptation
- physical or physiological forward models

#### CT / MRI / ultrasound: new screening rule

These modalities are **not automatically high-fit because they are medical imaging**.

High-fit examples:

```text
CT / MRI / ultrasound measurement
    -> tissue property / blood flow / elasticity / perfusion / quantitative physiological parameter
```

Lower-priority examples when they are the main scientific objective:

```text
image -> denoising
image -> super-resolution
image -> prettier reconstruction
image -> segmentation
image -> generic classification
```

Pure image reconstruction can still be technically interesting, but it no longer receives high A2 priority merely because it is an inverse problem. The preferred endpoint is **quantitative physiological information**, not simply a better-looking image.

### A3 — Industrial Measurement / NDT / Condition Monitoring

Canonical form:

```text
industrial structure / material / machine
    -> measured waveform / image / sensor signal
    -> inference
    -> crack / defect / geometry / material state / remaining life
```

Relevant modalities include:

- ultrasonic testing
- acoustic emission
- guided waves
- industrial CT
- photoacoustic / optical sensing
- thermal imaging
- vibration monitoring
- electromagnetic NDT
- structural health monitoring

Industrial ultrasound is one important subtype, not the whole branch.

---

## 4. B Tree: AI-assisted Physical Modeling

B is related to A but has a different center of gravity.

```text
physical equations / simulator / system model
    + experimental data
    + optimization / ML
    -> calibrated / identified / accelerated / surrogate / predictive model
```

The distinction remains:

- **A starts from the measurement.**
- **B starts from the physical model or modeled system.**

A/B overlap is not a problem; many attractive projects should receive both labels.

### B1 — Semiconductor Device Modeling

This is now a **main line**, alongside A1.

Relevant physical bases include:

- Poisson equation
- drift-diffusion
- carrier transport
- semiconductor material physics
- TCAD
- compact models

Relevant computational roles include:

- device-parameter extraction
- inverse parameter identification
- model calibration
- transport / device modelling
- TCAD acceleration
- surrogate modelling
- model-order reduction
- compact-model extraction
- sensitivity analysis
- optimization
- uncertainty quantification

Canonical A1/B1 boundary example:

```text
measured I-V / C-V
    -> infer mobility / trap density / interface / transport parameters
    -> calibrate or improve device / TCAD model
```

This kind of project is especially attractive because it directly connects **measurement inference** with **semiconductor device physics**.

### B2 — Battery Modeling

B2 remains conceptually valid but is now explicitly **opportunistic and lower priority**.

Preferred form:

```text
voltage / current / temperature / EIS
    + electrochemical / ageing model
    + ML / optimization
    -> SOC / SOH / RUL / degradation or physical parameters
```

The attractive kernel remains:

> **physics model + real data + state / parameter inference**

However, battery research should not displace stronger A1/B1 opportunities merely because battery AI is fashionable.

---

## 5. C — IC / EDA and Other EE Design

C is now deliberately **non-core**.

It includes:

- Analog IC
- Mixed-Signal IC
- RFIC
- Digital IC
- EDA / CAD
- Physical Design
- Verification
- related computational design topics

C does not need an AI narrative to be legitimate. A strong IC/EDA route can still be a good career outcome.

However, under the current research-direction framework, C receives higher relevance mainly when it has an obvious bridge to:

- semiconductor device physics
- device modelling
- semiconductor measurement
- computational lithography / process modelling
- other A1/B1 interfaces

Do not force an `AI + xx` story onto C merely for narrative consistency.

---

## 6. Compatibility with the Old Labels

The previous merged framework in `docs/GRADUATE_RESEARCH_DIRECTION.md` used:

- `A-METRO`
- `A-BME`
- `A-IND`
- `B-DEVICE`
- `B-BATTERY`
- `C-IC`

Use the following mapping when reading historical notes:

| Old label | Current label | Change |
|---|---|---|
| `A-METRO` | **A1** | same core meaning; now explicitly a main line |
| `A-BME` | **A2** | **major redefinition**: from broad biomedical imaging/inference to quantitative biomedical sensing & physiological inference |
| `A-IND` | **A3** | same core meaning |
| `B-DEVICE` | **B1** | same core meaning; now explicitly a main line |
| `B-BATTERY` | **B2** | same core meaning but priority reduced |
| `C-IC` | **C** | moved from parallel technical tree to non-core option |

The old top-level A/B/C logic remains useful; the new A1/A2/A3/B1/B2/C labels are the preferred working vocabulary from 2026-08-29 onward.

---

## 7. Position of the Current XRD Project

The XRD project still sits most naturally in **A1-style measurement inference**, even though XRD itself is not semiconductor metrology.

Its methodological structure is:

```text
physical object / crystal
    -> simulated or experimental diffraction measurement
    -> measured spectrum
    -> latent structural information
```

Transferable components include:

- simulator-based data generation
- physically structured perturbation
- measurement-equivalence supervision
- Sim2Real
- robustness under measurement shift
- few-shot adaptation
- calibration / uncertainty
- measurement-aware machine learning

This makes the project a strong bridge into:

- **A1**: semiconductor / scientific-instrument measurement inference
- **A2**: physiological sensing under calibration/domain shift
- **A3**: industrial measurement robustness
- **B1**: simulator / forward-model / parameter-inference problems

The project is therefore an **entry point into quantitative measurement inference**, not a permanent commitment to XRD or materials classification.

---

## 8. Program and Advisor Screening Rules

### General program screening

Do not ask only:

> Is this program Nano / BME / AI4Science / Scientific ML / Materials Informatics?

Instead ask separately:

```text
A1 fit?
B1 fit?
A2 fit?
A3 fit?
B2 fit?
C fit?
```

For each branch, evaluate:

1. actual thesis groups / supervisors
2. research projects
3. courses supporting the technical transition
4. access to real measurement data / physical models
5. industrial or clinical collaboration
6. internship ecosystem
7. concrete career exits
8. whether the student's likely role is computational inference rather than wet-lab or instrumentation-heavy work

A useful scoring format is:

```text
A1  ★★★★★
B1  ★★★★☆
A2  ★★☆☆☆
A3  ★★☆☆☆
B2  ★☆☆☆☆
C   ★★☆☆☆
```

This is preferable to one vague total "Scientific ML fit" score.

### A2-specific screening question

Do not ask:

> Does the advisor do medical imaging?

Ask:

> **What latent physiological quantity is ultimately inferred from the real measurement?**

This single question should sharply separate high-fit quantitative sensing from generic image-processing work.

---

## 9. Japan-specific Screening Strategy

The existing trajectory-based Japanese advisor rule remains valid:

> **Find the research transition, not merely the ML keyword.**

Preferred profile:

```text
traditional semiconductor / device / defect / X-ray / synchrotron PI
    -> decades of real domain accumulation and industry / facility access
    -> data volume and measurement throughput increase
    -> manual interpretation becomes a bottleneck
    -> recent sustained automatic analysis / quantitative analysis / ML / informatics branch appears
    -> room exists for a student to own the downstream computational sub-line
```

For traditional former Imperial Universities and other large Japanese universities, do **not** begin by exhaustively scanning departments professor-by-professor.

Prefer scanning **special organizations and local ecosystems** first:

- semiconductor centers
- future-material / energy-system institutes
- measurement / characterization centers
- synchrotron / large-facility organizations
- corporate-sponsored chairs and joint laboratories
- industry consortia
- data-science centers
- joint graduate programs
- national semiconductor / device projects

The practical order is:

```text
local semiconductor / measurement ecosystem
    -> special organization / center / consortium / national project
    -> active project
    -> PI
    -> recent publication trajectory
```

This is especially important because the value of a university may come from a **local semiconductor ecosystem**, not from its university-wide ranking or a generic materials department.

For example, when screening Kyushu-related opportunities, the relevant question is not simply the university ranking, but whether the opportunity is embedded in the **New Silicon Island / Fukuoka semiconductor ecosystem**, university semiconductor organizations and corporate collaboration.

---

## 10. Stable Interpretation Going Forward

The current direction should be summarized as:

```text
Main world:
    AI / computation + physical systems

Main routes:
    A1 Semiconductor / scientific measurement -> physical inference
    B1 Semiconductor device physics / modelling -> parameter and model inference

Important secondary route:
    A2 Quantitative biomedical sensing -> physiological inference

Other secondary options:
    A3 Industrial measurement / NDT
    B2 Battery modelling (opportunistic, lower priority)

Non-core option:
    C IC / EDA / EE design
```

Across A1, A2 and A3, the common methodological identity is:

> **measurement -> latent physical information**

Across A1 and B1, the strongest semiconductor-facing identity is:

> **real measurement + physical model / simulator + quantitative parameter inference**

This framework should be used for future advisor searches, graduate-program comparisons, application planning and career-exit evaluation.