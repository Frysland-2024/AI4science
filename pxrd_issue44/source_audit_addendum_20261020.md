# Issue #44 source and license audit addendum

**Audit date:** 2026-10-20
**Purpose:** append verified facts without changing the preregistered and hashed `literature_matrix.md`.

## Issue body verification

The complete live [Issue #44](https://github.com/Frysland-2024/AI4science/issues/44) body was fetched through the connected GitHub repository tool on 2026-10-20. It confirms the task requires a source-fidelity audit, the physical and data gates, the seven already-supported materials, paired architecture/seed comparisons against immutable PR43 MLP and P0/P3/P5, a bounded serial manager, failure preservation, and a Draft PR. Its acceptance condition permits actual run evidence with explicit remaining blockers. The earlier final bullet in `literature_matrix.md` saying the issue body was unavailable is superseded by this addendum; the frozen matrix itself is unchanged.

## Code snapshot and license provenance

The three Bin Cao repositories named in the matrix declare MIT in `LICENSE` at their audited commit snapshots below. The license files were fetched at the exact commit refs on 2026-10-20. Their license blob SHA-1 is `e08fc2f95598146186e7f87c6a601f505d85851c` in each repository.

| Repository | Audited commit | License evidence |
|---|---|---|
| [Bin-Cao/XQueryer](https://github.com/Bin-Cao/XQueryer/tree/35ea79f496ff740861fce10597fbad796e290ced) | `35ea79f496ff740861fce10597fbad796e290ced` | [MIT LICENSE at audited commit](https://github.com/Bin-Cao/XQueryer/blob/35ea79f496ff740861fce10597fbad796e290ced/LICENSE) |
| [Bin-Cao/SimXRD](https://github.com/Bin-Cao/SimXRD/tree/821f145ac3f04a1dfe91cc813a31216c14cd74a5) | `821f145ac3f04a1dfe91cc813a31216c14cd74a5` | [MIT LICENSE at audited commit](https://github.com/Bin-Cao/SimXRD/blob/821f145ac3f04a1dfe91cc813a31216c14cd74a5/LICENSE) |
| [Bin-Cao/PyWPEM](https://github.com/Bin-Cao/PyWPEM/tree/6b4e5542af3896040a0f445e5a72487d7023c1aa) | `6b4e5542af3896040a0f445e5a72487d7023c1aa` | [MIT LICENSE at audited commit](https://github.com/Bin-Cao/PyWPEM/blob/6b4e5542af3896040a0f445e5a72487d7023c1aa/LICENSE) |

For [WPEM/CPICANN](https://github.com/WPEM/CPICANN), the matrix records commit `5c3c929fa5073a3fe7d97b95b836fc5b4475b1ca`, but the connected GitHub API returned “No commit found” for that ref on this audit. The repository's current [`main` LICENSE](https://github.com/WPEM/CPICANN/blob/main/LICENSE) declares MIT with copyright notice `2022 daweedkob`; this does **not** verify the license at the matrix's recorded snapshot. No CPICANN source is used by this benchmark.

No code, weights, or data were copied or imported from these repositories. The ResNet and patch Transformer in `models.py`, bounded manager, and evaluation code are local implementations inspired by the broad model families and task distinctions described in the cited sources. The upstream papers' metrics are not used as numerical baselines. The work does not reproduce XQueryer or SimXRD classification, CPICANN phase identification, or PyWPEM/FullProf/TOPAS refinement.

## Provenance and data boundary

- Exact paper records, repository commit snapshots, tasks, and claim limits remain in the frozen `literature_matrix.md`.
- The benchmark's CIF/config/PR43 source identities and hashes are recorded in `runs/benchmark_20261020/manifest.json`; result and recovery artifacts retain their own hashes.
- The 77 primary parents per material were already opened for PR43. Issue #44's new architecture comparison is exploratory and not an independent test.
- No raw licensed RRUFF spectra, RRUFF metadata, local checkpoint, generated profile array, or secret is in the publishable audit package. RRUFF remains `BLOCKED`; the locked classification test was not opened.
