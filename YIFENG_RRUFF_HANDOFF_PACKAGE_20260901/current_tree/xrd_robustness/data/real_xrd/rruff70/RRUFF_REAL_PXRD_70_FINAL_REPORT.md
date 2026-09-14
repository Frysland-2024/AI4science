# RRUFF Real-PXRD-70 Final Freeze Report

**Dataset ID:** `rruff-real-pxrd-70-v1.0-final`  
**Freeze date:** 2026-07-24  
**Status:** `FROZEN_FINAL_DATASET`  
**Evaluation status:** locked; no model was loaded or run.

## Final population

- 70 unique measured powder profiles.
- Six pre-freeze candidates were replaced before any model access because they failed the final measured-vs-DIF weighted peak-coverage threshold of 0.80; the complete change log is in `audits/selection_changes.csv`.
- Seven crystal systems, exactly 10 samples per class.
- 70 unique RRUFF IDs, mineral names, and ideal-formula/space-group pairs.
- Maximum pairwise Pearson correlation: `0.513483`; pairs with `r >= 0.95`: `0`.

## Phase and label evidence

Every sample has an exact `Powder` diffraction description, XRD-confirmed identification, paired DIF space-group evidence, no explicit impurity warning in the diffraction sample description, and a physics-only measured-vs-DIF consistency pass. The frozen claim is **nominal single-mineral identity**. No quantitative Rietveld phase fraction or 100% purity claim is made.

## Overlap resolution

The benchmark is frozen as a **measurement-domain external test**, not an unseen-structure benchmark. Exact structure overlap is therefore not an exclusion gate. No known strict RRUFF–Materials Project mapping match occurs among the 70 samples. This scope choice was frozen before model access and cannot be changed after results are observed.

## Data use and release

The local package supports internal evaluation. Redistribution rights are not asserted; the public package is metadata-only and omits spectra/DIF contents. RRUFF citation is mandatory.

## Execution lock

The data manifest and preprocessing contract are final, but real-test execution remains disabled until the method, checkpoint hashes, and simulated-test results are frozen and the user gives a separate execution authorization.

## Frozen hashes

- Manifest SHA-256: `17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5`
- Preprocessing contract SHA-256: `90DCBDC89F641A876DA2E8A927499A3E7225934AE38E820D70AD26640113C9CC`
- Selection ID list SHA-256: `E497C65212EC36FFD6800B4806AF0B134B9CDBD9E270E073B1F3061409E7EE71`
