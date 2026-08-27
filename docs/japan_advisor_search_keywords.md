# Japan Advisor Search Keywords: Measurement Informatics and AI-assisted Experimental Analysis

## Motivation

For Japanese graduate-advisor searches, keywords should not be limited to broad AI terms such as AI4Science or AI for Materials. Japanese groups often describe the research from the experimental measurement domain rather than from the machine-learning method.

The recommended search concept is:

> AI-assisted analysis and inference of experimental measurement data.

The focus is not imaging hardware design or measurement-system engineering, but applying computational methods after experimental data acquisition.

---

## Primary Japanese Keywords

### 計測インフォマティクス

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

### 顕微鏡計測インフォマティクス

Related to:

- SEM
- TEM/STEM
- AFM
- optical microscopy
- computational microscopy

---

### 半導体検査 × 数理解析

Related to:

- semiconductor defect inspection
- wafer inspection
- defect characterization
- mathematical analysis

---

### 半導体計測 × データ科学

Related to:

- semiconductor metrology
- process monitoring
- scatterometry
- ellipsometry
- defect analysis

---

### 電子顕微鏡 × 機械学習

Related to:

- electron microscopy image analysis
- automated microscopy
- defect recognition
- structure analysis

---

### 放射光 × 機械学習

Related to:

- synchrotron measurement
- X-ray analysis
- X-ray imaging
- spectroscopy

---

### X線解析 × 機械学習

Broader and more useful than only X-ray topography.

Related to:

- diffraction analysis
- X-ray spectroscopy
- structural inference

---

### スペクトル解析 × 機械学習

Related to:

- Raman
- XPS
- EELS
- IR spectroscopy

---

## Semiconductor Device Inverse Problems / Property Estimation

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

## Search Tree

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

## Search Principle

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

## Trajectory-based Advisor Screening: Find the Transition, Not the Keyword

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

### Three screening questions

#### 1. Is the old core field genuinely strong?

The PI should have a real, long-standing base in semiconductor industry-relevant problems rather than being a generic materials professor who happens to coauthor one semiconductor paper.

Strong signals include:

- SiC / GaN / power semiconductor
- wafer inspection or defect evaluation
- X-ray topography / diffraction / synchrotron characterization
- semiconductor metrology
- device or process evaluation
- long-term industrial collaboration
- use of SPring-8 or other major facilities

#### 2. Is the computational transition real and sustained?

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

#### 3. Can a student plausibly occupy the new computational sub-line?

The best fit is not merely a famous senior PI with an ML collaboration. The practical question is:

> Is there room for a student who can push the downstream algorithmic analysis of the group's existing measurement data?

Positive signs include:

- experimental data generation already mature
- data volume growing faster than manual analysis capacity
- a new automatic-analysis topic appearing in several recent projects
- few existing students fully dedicated to ML/informatics
- clear need for classification, parameter extraction, inverse inference, robustness, or high-throughput analysis

This is particularly attractive because the student can contribute through the **measurement-data -> inference** interface without needing to become the person who fabricates the device or designs the instrument.

### Why this transition can be structurally inevitable

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

### Practical search procedure

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