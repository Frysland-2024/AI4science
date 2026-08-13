# Local Literature and External Resource Index

**Inventory date:** 2026-08-13
**Scope:** Git-safe metadata for local, Git-ignored literature, datasets, source
archives, and extracted third-party reference code.

This file records identities, hashes, extraction proof, scientific roles, and
execution boundaries. It does not make any local PDF, dataset, ZIP archive, or
third-party source tree eligible for Git commit.

## Acquisition

Local acquisition record:

```text
E:\AI4science\01_literature\source_acquisitions\2026-07-23_opxrd_simpod\
```

### Papers

| Work | DOI | Local curated role | SHA-256 |
| --- | --- | --- | --- |
| Hollarek et al., opXRD, *Advanced Intelligent Discovery* 2 (2026), e202500044 | `10.1002/aidi.202500044` | core XRD perturbation / experimental-pattern resource | `BA8A6BC981DC47981DC03B1E7E910FEEB3DC33AE808621B7FBBE7D159A7D5ADC` |
| opXRD supporting information | `10.1002/aidi.202500044` | core XRD perturbation / dataset schema support | `0D3D9B3F3C25813DEF2A326D8B6DF7499909988A7C5E1BC63F393DF590338FB2` |
| Rincon et al., SIMPOD, *Scientific Data* 12 (2025), 1186 | `10.1038/s41597-025-05534-3` | XRD AI / crystal-structure benchmark context | `6306B64823C36013646F5EAB390C2F2468A5AF44E97B8A936DD253714B06140D` |

Journal indexing was not requested or assessed. The available journal
identifiers were checksum-validated only:

- *Advanced Intelligent Discovery*: eISSN `2943-9981`, checksum valid;
- *Scientific Data*: eISSN `2052-4463`, checksum valid.

No SCIE, EI Compendex, or CSCD conclusion is made here.

## Archives and extraction verification

| Archive | SHA-256 | Payload files | Payload bytes | Verified extracted role |
| --- | --- | ---: | ---: | --- |
| `opxrd_zenodo_14254270.zip` | `38B62BCDDF976DEBB3E41D2597D3F14AC6C1F1C8A33565A84A98EF38BA3B6044` | 92,552 | 3,612,139,779 | local external experimental-pattern resource |
| `opXRD_source_9a6050ea8b62c9d67f72a126a33bf18f70cebefb.zip` | `AEF42DD1491A27665F251F21DF60CD1CAE7C276998A961B2B009B9994E7C6449` | 30 | 1,628,828 | third-party loader, wrapper, analysis, and figure-source reference |
| `SIMPOD_source_main.zip` | `04E7D66FDF6AF8DD692F3A593A44DAB4365DC2A3C43585FC91B8C80798A3B962` | 22 | 23,092,051 | third-party generation and benchmark reference |

For every archive, extracted file count and total uncompressed bytes exactly
match the ZIP payload. Original archives remain in the acquisition directory as
provenance and recovery copies.

The opXRD data are organized locally under:

```text
E:\AI4science\01_literature\data_resources\opxrd_zenodo_14254270\
```

Its seven contributor directories are `CNRS`, `EMPA`, `HKUST`, `IKFT`, `INT`,
`LBNL`, and `USC`. All 92,552 payload files are JSON. A sample from every
contributor directory parsed successfully and exposed
`two_theta_values`, `intensities`, `label`, and `metadata`.

The extracted third-party reference sources are organized under:

```text
E:\AI4science\02_code_repositories\xrd_perturbation_core\extracted_verified\
```

## Execution boundary

- opXRD is not silently merged with RRUFF-70, GTIIT, Simulation Validation,
  simulated Test, or final real test.
- opXRD and SIMPOD source trees are references, not active V9 runtime
  dependencies.
- These resources authorize no training, tuning, model loading, validation, or
  test evaluation.
- Any future opXRD use requires a duplicate/grouping audit, label mapping,
  immutable role assignment, provenance review, and explicit authorization.

## Real-domain predecessor archive (2026-08-13)

The seven predecessor works reviewed for real-domain validation are recorded in
the following Git-ignored local acquisition bundle:

```text
E:\AI4science\01_literature\source_acquisitions\2026-08-13_real_domain_predecessors\
```

Each per-work directory contains a local `README.md` with source URLs, license
boundaries, checksums, existing-repository references, and explicit negative
findings. The bundle-level `README.md` is the navigation entry point.

### Newly acquired and verified files

| Work | File | SHA-256 | Verification |
| --- | --- | --- | --- |
| Vecsei et al. (2019) | arXiv source archive | `E5400CAC72FC0E790174F88FD66ED93A6A2F13FEA582BBBDAE2B0C3F288E7D9F` | archive listing passed |
| Salgado et al. (2023) | official supplementary PDF | `EEA3F8A340BB3BC0A737B55BE9D843E6A9594E3E0E221AEA6EDCA499C5C3872C` | 2 pages rendered and inspected |
| ML4pXRDs (2023) | KITopen version-of-record PDF | `40F320E362BDC0B5997364B17576C6A41BADD66330B8A6E579E81FFA3A461885` | 11 pages; first and last rendered and inspected |
| CrystalMELA (2023) | Europe PMC article PDF | `884AB7CA7B9A2B643AB3B9640291E896071EF0AAFE82842DFF97058AB4A6BB24` | 11 pages; first and last rendered and inspected |
| CrystalMELA (2023) | Europe PMC full-text XML | `24A568E35B196D4D337FE5D3B546899F93F9AA366A2EAD93193E6C02A6539245` | XML acquired from the official API |
| CrystalMELA (2023) | CNR official-page snapshot | `8C96340B875406A64B1B7ED0A8268E88D25F65D6B79098693BB4E75F91A07097` | HTML snapshot retained for provenance |
| CrystalMELA dependency | cited Suzuki 2020 ExRT upstream ZIP | `1E5C5B305E1837839C31E74B427CFCE1B7BB4DEC2794A51539BA2CE57242F970` | archive checked; explicitly not CrystalMELA source |
| CPICANN (2024) | official supplementary PDF | `7EF1DBC42ACB359E13140BAC240F6D2A99856BBA914FE98D1745DD94819740CD` | 14 pages; first and last rendered and inspected |

Existing local PDFs and source snapshots for Vecsei, Salgado/XRDs,
ML4pXRDs, CPICANN, and SimXRD were retained rather than duplicated. The complete
SimXRD-4M data, licensed ICSD inputs, model checkpoints, and other large generated
artifacts were not downloaded.

### Explicit availability limits

- Vecsei has no verified paper-specific public code repository or independent
  supplementary file; the paper appendix is part of the article.
- The ML4pXRDs supplementary-information URL is recorded, but the current RSC
  endpoint did not return the PDF; the article and official code remain local.
- CrystalMELA has no independent supplementary record, public platform source,
  public weights, or public copy of its 110 private experimental patterns. The
  retained ExRT ZIP is only the cited upstream implementation.
- Toyota (2026) is represented by an acquisition record because automated PDF
  access was blocked by the publisher challenge, no public code or independent
  supplementary archive was found, and the 1,298-pattern WAVEBASE data require
  approval by the data owner. No access control was bypassed and no data request
  was sent on the user's behalf.

This acquisition improves literature reproducibility only. It does not create a
second experimental domain, change the frozen V9 evidence, or authorize a new
evaluation.
