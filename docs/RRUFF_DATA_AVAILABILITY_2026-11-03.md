# RRUFF data availability and local inventory — 2026-11-03

This is an inventory of data sources and local archives. It does not grant redistribution rights. No raw RRUFF spectra, CIFs or author-provided arrays are copied into this report or uploaded to GitHub.

## Public source

The primary source is the [official RRUFF data download page](https://www.rruff.net/about/download-data/) and its [archive format help](https://www.rruff.net/help/zip-download/). The website describes diffraction archives and mineral data; exact archive revisions may change. The local ZIP counts and SHA-256 values below are a snapshot of the already-present files in `E:\AI4science\RRUFF` on 2026-11-03 and are not claimed to be current upstream totals.

| Local archive | File entries | Entry types | SHA-256 |
|---|---:|---|---|
| `cif.zip` | 21,720 | 21,720 `.cif` | `f84e8aa19042182dd1c01c25f4d4aa171356bf709c5b888fac706295999687bc` |
| `DIF.zip` | 3,013 | 2,978 `.txt`, 35 `.rtf` | `3b540db61664cacdd22268ffbac6ab586ca6bce389b7399cc3e9baaeb6607b03` |
| `XY_RAW.zip` | 3,019 | 3,019 `.txt` | `948a133482bb3c99da80194cc2848933aee668129beb209150f7f850cd4b0587` |
| `XY_Processed.zip` | 1,484 | 1,484 `.txt` | `c0b079535ab3e6077212b7a8f6ced28129cbe538fc03b1479061430f219ff9cb` |
| `Refinement_Data.zip` | 1,175 | 1,175 `.txt` | `7e075457ebac5ad8c5841e699857e7666e6feae1f8e8dd00945dc6818d60d5f6` |
| `Refinement_Output_Data.zip` | 1,176 | 1,176 `.txt` | `a51e4f7399051889a3d699dadbb99c2139476d3d17ea47baf85e3ebf3df4f5c12` |

Archive entry counts are not unique mineral counts, matched XY_RAW–DIF pair counts or a seven-system benchmark denominator. Matching and label coverage must be computed and recorded from IDs and source metadata before a paper protocol can be claimed.

## Existing local RRUFF-derived assets

| Asset | Local size / role | Use in this stage |
|---|---|---|
| `xrd_robustness/data/real_xrd/rruff_pipeline_test/` | 35 spectra, five per class, 10–80°/0.02°/3,501 points, max normalized; manifest role `pipeline_smoke_test_only__no_paper_numbers` | Used only for the documented SMK pipeline checks; never reported as a paper-protocol cohort |
| `xrd_robustness/data/real_xrd/rruff70/` | 70-sample frozen final external measurement test; manifest hash `17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5` | Not used; preserve historical test role |
| `xrd_robustness/data/real_xrd/rruff350/` | 350-sample frozen model-blind set; `real_test_execution_authorized=false`; hash `6CAFA5EA0917AD6A1163DE7738AF94C713F811292FDC89E214F50795C08170B5` | Not used or modified |
| `xrd_robustness/data/real_xrd/rruff371/` | 371-sample frozen balanced panel, 53/class; `real_test_execution_authorized=false`; hash `EBF6B35ABAF78C716498D327CDD02EF3FFC3E53662AFC56A5CB009A10B96B142` | Not used or modified |
| Other local real-XRD folders (`opxrd`, `opxrd_cnrs7cs`, `GTIIT_real_XRD`) | Separate source/data contexts; not audited as RRUFF benchmark cohorts here | Not used |

The RRUFF-derived frozen assets are local research data. Public artifacts retain metadata and provenance only. Their IDs, raw arrays, and original measurements are not redistributed by this change.

## Published RRUFF cohorts and public author releases

| Source | What is publicly documented | What remains unavailable or unverified for this audit |
|---|---|---|
| Lee et al. (2023) | Paper says about 1,600 RRUFF patterns were extracted and describes a 40% background-based exclusion; [official repository](https://github.com/socoolblue/Advanced_XRD_Analysis) | Exact retained row count and split IDs; the visible repository tree did not verify the full Ex_dataset_2 cohort |
| Salgado et al. (2023) | Paper reports 908 entries; authors' [repo](https://github.com/AGI-init/XRDs) contains preprocessed arrays and a loader | Public loader does not return sample IDs or an ID-aligned split file; binary metadata not independently decoded |
| SimXRD-4M | Paper reports a 3,002-pattern RRUFF catalogue; [HF dataset](https://huggingface.co/datasets/AI4Spectro/rruff) provides parsed XY_RAW/DIF records | The parsed collection does not identify the exact Table 5 filter, labels, split or denominator |
| XQueryer | Main paper reports 1,003 crystal-system samples; [official repo](https://github.com/Bin-Cao/XQueryer) publishes match artifacts and links to external data | Full verified 1,003-sample classification manifest and its preprocessing chain were not accessible |

These published dataset counts are not interchangeable. A new exact protocol requires a row-level sample manifest, class labels, exclusion reasons, preprocessing hashes and split membership. When any is unavailable, experiments must be named approximate and report the actual recovered denominator.

## Candidate synthetic-parent CIF sources and scale feasibility

| Source | Publicly documented scope/access | Independence and licensing notes | Current feasibility status |
|---|---|---|---|
| [CrystDB](https://huggingface.co/datasets/caobin/CrystDB), the SimXRD/XQueryer structure release | Dataset card describes thermodynamically stable Materials Project structures through MP-2024.1 (released through Jan 2024); reports 132 MB total file size. Exact structure count in this card is **Unknown**. File access requires accepting the Hub access conditions and sharing account information. | MP-derived and therefore not an independent structure family from the SimXRD/XQueryer parent sources. The card says **commercial use is prohibited**; do not mirror or redistribute it. | A likely route to the cited MP-era structure distribution if access conditions fit. Not present locally and not counted as newly independent parents. Exact overlap/count must be verified before use. |
| Materials Project API / [AWS Open Data](https://docs.materialsproject.org/downloading-data/aws-opendata) | Structures and CIF fields are available through the [API](https://docs.materialsproject.org/downloading-data/using-the-api/getting-started), which requires an individual key. Official docs describe bulk data and advise minimizing fields, batching and local caching for large queries. | Same underlying family as CrystDB and the two Cao papers; newer snapshots may change parent count. Terms and attribution apply. A new retrieval must record database release, query and retrieval date. | Potentially available at scale, but no current parent count, API entitlement, dedup result or local retrieval is verified here. Do not count as independent scale expansion until deduplicated against the frozen MP parents. |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | COD reports more than 500,000 entries in its 2023 public materials and provides individual CIFs plus bulk access through [rsync/SVN/archive instructions](https://wiki.crystallography.net/howtoobtaincod/). The exact current entry count and usable seven-system count are **Unknown**. | An independent archive from MP, publicly licensed **CC0** according to [COD policy](https://www.crystallography.net/cod/documents/topic/privacy/COD-privacy-GDPR.pdf). Entries include organic, inorganic, organometallic and mineral structures; raw record count is not the usable PXRD parent count. | Best independent candidate identified, but requires CIF validity, duplicate/near-duplicate, occupancy/disorder, formula, crystal-system and source-overlap audits. Not downloaded locally in this stage. |

The first scale-curve point remains 30,000 audited unique training parents, followed by 60,000 and then 100,315 to approach the cited Cao scales. Counts mean deduplicated structures that pass the seven-system and simulation-readiness filters, not source-database row totals. Parent acquisition and formal training remain gated on a frozen inventory, label audit, simulator checks and an explicit GPU/time budget. No 30k+ run has started.

## Data handling

- Keep the official RRUFF archives and all existing frozen panels unchanged.
- Use public source links and archive hashes for provenance; do not upload raw spectra/CIFs or third-party full arrays to this repository.
- Public reports may include cohort counts and hashes when this does not reveal restricted source payloads; do not include raw measured vectors.
- For a future benchmark release, confirm source terms and include only the metadata necessary to reproduce the selection unless redistribution permission is explicit.
