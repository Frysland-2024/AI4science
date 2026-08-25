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
