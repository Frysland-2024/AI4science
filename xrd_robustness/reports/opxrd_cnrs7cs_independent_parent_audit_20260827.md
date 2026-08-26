# opXRD/CNRS-7CS independent-parent follow-up audit

> **Superseded calculation snapshot.** This note used the pre-v2 manifest,
> whose global duplicate representative incorrectly discarded the eligible
> `pattern_57` because its exact-spectrum twin `pattern_472` had no stable
> structural label.  The corrected eligibility-stratum logic gives strict
> `476 spectra -> 323 structural parents -> 318 after formal exclusion`, with
> final counts `triclinic 21 / monoclinic 87 / orthorhombic 77 / tetragonal 41 /
> trigonal 33 / hexagonal 12 / cubic 47`.  Use
> `data/real_xrd/opxrd_cnrs7cs/CNRS_7CS_FEASIBILITY_REPORT.md` and the v2
> manifest (SHA-256 `FAF089375C10C18D0A4AB3568E85FA78EAA56DE45F507FAACD39672AD88BE424`)
> as the authoritative result.  This file is retained only for its independent
> methodology and endpoint-sensitivity notes.
>
> **Decision reversal (2026-08-27):** the HOLD/NO-GO recommendation below was later
> reversed.  CNRS-318 is now registered as the formal second real domain
> (naturally imbalanced independent experimental domain); see
> `data/real_xrd/opxrd_cnrs7cs/SECOND_REAL_DOMAIN_DECISION.md`.  The retained,
> still-valid point is that CNRS is *not* equivalent in statistical strength to
> RRUFF-301 and must not be presented as such.

Audit date: 2026-08-27 (Asia/Shanghai)

## Scope and pinned inputs

This is a read-only follow-up to the main CNRS feasibility audit. It does not
load a model or checkpoint, run inference, train a model, or change the main
audit script. Its purpose is to distinguish unique spectra from independent
crystallographic parents and to explain the different formal-14060 overlap
counts.

- CNRS source: `01_literature/data_resources/opxrd_zenodo_14254270/CNRS`
- opXRD v11 archive SHA-256:
  `38B62BCDDF976DEBB3E41D2597D3F14AC6C1F1C8A33565A84A98EF38BA3B6044`
- Main audit manifest:
  `xrd_robustness/data/real_xrd/opxrd_cnrs7cs/cnrs_7cs_audit_manifest.csv`
- Main audit manifest SHA-256:
  `D01C2EC4476FC52E6DDB914D4791E6DCE07F703B63C3E8D7A4E3164977211F4C`
- Main audit script snapshot SHA-256 at calculation time:
  `4B8867DA5F39EF489AC0FF19171870D833FF7D12E7AA4160FCA5934D00FFE79A`
- Formal structure records:
  `xrd_robustness/data/formal_14060/mp_processed/structure_records.jsonl`
- Runtime: `.venvs/xrd_test/Scripts/python.exe`
- Packages: pymatgen 2026.5.4, spglib 2.7.0, NumPy 2.4.6,
  SciPy 1.17.1.

## Candidate definitions

The deposited CNRS JSONs contain no direct space-group numbers. A label is
therefore considered structurally recoverable only when the deposited lattice
and atomic basis can be parsed and `SpacegroupAnalyzer` returns the same space
group and crystal system at all four `symprec` values:

```text
symprec = 0.001, 0.01, 0.05, 0.1
angle_tolerance = 5 degrees
```

The source axis is mapped to the Cu K-alpha target wavelength
`lambda_target = 1.5406 Angstrom` using Bragg's law:

```text
2theta_target = 2 asin[(lambda_target / lambda_source) sin(theta_source)]
```

For actual resampling, source points for which the arcsine argument exceeds one
must be discarded, not clipped to 180 degrees. The canonical target grid is
10--80 degrees at a 0.02-degree step (3,501 points), with linear interpolation
and max normalization.

Two coverage policies are reported:

1. `strict`: the main audit's exact mapped coverage, mapped minimum `<= 10.0`
   and mapped maximum `>= 80.0`.
2. `half-step sensitivity`: mapped minimum `<= 10.01` and mapped maximum
   `>= 79.99`. The 0.01-degree tolerance is half one target-grid step and is a
   sensitivity analysis, not permission to relax the frozen contract.

`broad` means every structurally recoverable crystal regardless of chemistry.
`not-C-and-H` is the main audit's risk proxy (`strict_nonorganic_proxy`): it
excludes structures that contain both carbon and hydrogen. It is not a proven
inorganic label. `no-C` is a stricter sensitivity stratum and likewise is not a
complete chemical taxonomy.

Spectrum uniqueness comes from the main manifest: one representative per exact
numeric spectrum hash, with spectrum-label-conflict groups excluded. It is not
treated as physical or structural independence.

## Structural-parent grouping

The exploratory parent grouping used these exact parameters:

```python
StructureMatcher(
    ltol=0.2,
    stol=0.3,
    angle_tol=5,
    primitive_cell=True,
    scale=True,
    attempt_supercell=False,
    comparator=ElementComparator(),
)
```

Comparisons were blocked by `(reduced_formula, recomputed_crystal_system)`.
Every positive pairwise match became an undirected edge, and union-find
connected components were counted as conservative structural parents. There
were 899 positive edges in the half-step superset and no matcher errors. This
is deliberately more conservative than exact standardized-structure hashes:
small experimental/DFT cell differences should not create false independence.

If any member of a CNRS parent component matched formal-14060, the entire
component was excluded.

## Counts

The main manifest contains 1,052 source scans, 891 parseable structures, 886
stable reconstructed space groups/crystal systems, and 878 stable records with
valid arrays. The table below applies exact-spectrum deduplication followed by
the fuzzy structural-parent grouping described above.

| Stratum | Spectrum representatives | Structural parents before formal exclusion | Formal-overlap parent components | Parents after exclusion | Cubic | Hexagonal | Monoclinic | Orthorhombic | Tetragonal | Triclinic | Trigonal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Strict broad | 475 | 322 | 5 | 317 | 46 | 12 | 87 | 77 | 41 | 21 | 33 |
| Strict not-C-and-H | 324 | 202 | 5 | 197 | 32 | 11 | 40 | 53 | 38 | 4 | 19 |
| Half-step broad | 507 | 349 | 6 | 343 | 47 | 13 | 96 | 82 | 47 | 21 | 37 |
| Half-step not-C-and-H | 349 | 222 | 6 | 216 | 33 | 12 | 45 | 55 | 44 | 4 | 23 |
| Half-step no-C | 250 | 185 | 6 | 179 | 29 | 9 | 35 | 43 | 41 | 4 | 18 |

The maximum CNRS component contained 23 spectrum representatives. Therefore,
the main manifest's 475 broad unique spectra or 470 exact-fingerprint-independent
records cannot be interpreted as 475 or 470 independent physical/structural
samples.

The predeclared `>=20 independent parents per crystal system` gate fails:

- strict broad is limited by hexagonal = 12;
- half-step broad is limited by hexagonal = 13;
- both chemistry-restricted sensitivity strata are limited by triclinic = 4.

This supports `HOLD/NO_GO` for a balanced formal second domain. The data can
still support an explicitly unbalanced exploratory domain, or at most a small
balanced parent-level panel, but it should not be represented as equivalent in
strength to RRUFF-301.

## Why formal overlap is 10, 5, or 6 depending on the denominator

These values answer different questions and all should be retained with
explicit names:

- `10`: all 891 structure-resolvable CNRS records were screened against the
  formal-14060 structures, before wavelength/window eligibility. Ten CNRS
  records have a fuzzy `StructureMatcher` match (8 train, 2 test).
- `5`: of those ten, five pass the main audit's strict Cu-K-alpha mapped 10--80
  coverage and unique-spectrum candidate rules.
- `6`: the half-grid-step sensitivity additionally admits `pattern_245`, whose
  mapped lower bound is 10.00065079 degrees. This is why the exploratory count
  was six. It must not replace the strict count of five in the main audit.

| CNRS scan | Formal ID | Formal split | Cu-K-alpha mapped range | Strict candidate | Half-step candidate | Reason if excluded |
| --- | --- | --- | --- | --- | --- | --- |
| pattern_1035 | mp-19504 | train | 5.00012991--119.98515153 | yes | yes | -- |
| pattern_169 | mp-14708 | train | 5.00012991--119.98515153 | yes | yes | -- |
| pattern_245 | mp-1194160 | train | 10.00065079--119.73181260 | no | yes | lower edge is 0.00065079 degrees above 10 |
| pattern_346 | mp-1194023 | test | 5.00012991--119.98515153 | yes | yes | -- |
| pattern_465 | mp-20311 | train | 11.19277785--179.46543270 | no | no | missing mapped low-angle coverage |
| pattern_651 | mp-1223443 | test | 6.74655996--121.13859238 | yes | yes | -- |
| pattern_701 | mp-20311 | train | 11.16835824--179.64133377 | no | no | missing mapped low-angle coverage |
| pattern_715 | mp-22216 | train | 9.73694666--89.76872279 | yes | yes | -- |
| pattern_824 | mp-20311 | train | 11.18128114--179.25624130 | no | no | missing mapped low-angle coverage |
| pattern_981 | mp-1190858 | train | 9.99926028--69.99408305 | no | no | missing mapped high-angle coverage |

Recommended machine-readable fields are therefore:

```text
formal_14060_structure_match_all
strict_candidate_formal_14060_structure_match
halfstep_candidate_formal_14060_structure_match
formal_14060_match_ids
formal_14060_match_splits
parent_component_has_formal_14060_match
```

## Reproduction command and core code path

The calculation was run from `E:/AI4science` with:

```powershell
$env:PYTHONPATH = (Resolve-Path 'xrd_robustness\scripts').Path
$code | & '.venvs\xrd_test\Scripts\python.exe' -
```

The core grouping operation was:

```python
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
import audit_opxrd_cnrs_7cs as audit

source = Path('01_literature/data_resources/opxrd_zenodo_14254270/CNRS')
manifest = Path(
    'xrd_robustness/data/real_xrd/opxrd_cnrs7cs/'
    'cnrs_7cs_audit_manifest.csv'
)

def as_bool(value):
    return str(value).lower() == 'true'

def halfstep_candidate(row):
    return (
        as_bool(row['derived_structural_eligible'])
        and as_bool(row['spectrum_unique_representative'])
        and not as_bool(row['spectrum_label_conflict'])
        and float(row['cu_ka_mapped_two_theta_min']) <= 10.01
        and float(row['cu_ka_mapped_two_theta_max']) >= 79.99
    )

rows = {
    row['scan_id']: row
    for row in csv.DictReader(manifest.open(encoding='utf-8-sig'))
}
items = {}
for scan_id, row in rows.items():
    if not halfstep_candidate(row):
        continue
    payload = json.loads((source / f'{scan_id}.json').read_text())
    label = audit.parse_json_like(payload['label'])
    phase = audit.parse_phase(label['phases'][0])
    structure, _ = audit.build_structure(phase)
    items[scan_id] = (row, structure)

blocked = defaultdict(list)
for scan_id, (row, _) in items.items():
    blocked[(row['recomputed_crystal_system'], row['formula_reduced'])].append(scan_id)

matcher = StructureMatcher(
    ltol=0.2,
    stol=0.3,
    angle_tol=5,
    primitive_cell=True,
    scale=True,
    attempt_supercell=False,
    comparator=ElementComparator(),
)

edges = []
for scan_ids in blocked.values():
    for index, left in enumerate(scan_ids):
        for right in scan_ids[index + 1:]:
            if matcher.fit(items[left][1], items[right][1]):
                edges.append((left, right))

# For each requested stratum, initialize one union-find node per selected scan,
# union every positive edge whose endpoints are selected, count connected
# components by recomputed_crystal_system, then remove every component for
# which any member has formal_14060_structure_match == True.
```

## Production implementation recommendation

The exact standardized fingerprint already in the main audit is a useful fast
screen, but it is not a sufficient parent identifier for experimental versus
DFT structures. The production audit should add the conservative fuzzy
component identifier after exact-spectrum deduplication and before the
per-class sample-count gate. A deterministic identifier can be formed from the
SHA-256 of the sorted member scan IDs. The output should include a component
manifest, every positive matcher edge, matcher parameters, formula/system
blocking keys, formal-match IDs/splits, and exclusion reasons.

The final gate should require all of the following before the domain is frozen:

1. pinned source/archive and manifest hashes;
2. single phase, experimental record, valid arrays;
3. stable reconstructed crystal system at all registered symmetry tolerances;
4. known wavelength and full Bragg-mapped 10--80 coverage;
5. exact-spectrum conflict/duplicate handling;
6. fuzzy structural-parent grouping;
7. exclusion of every parent component overlapping any formal-14060 split;
8. at least 20 remaining parent components in every crystal system;
9. manual label validation on a registered sample from every class.

On the pinned inputs above, gate 8 fails even for the broad chemistry stratum,
and manual label validation has not yet been run.
