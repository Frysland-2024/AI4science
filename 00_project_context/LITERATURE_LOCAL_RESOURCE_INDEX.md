# Local Literature and External Resource Index

**Inventory date:** 2026-07-26
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
