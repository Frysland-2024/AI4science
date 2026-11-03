# RRUFF zero-shot model comparison library — 2026-11-03

> **Role:** User-approved, source-attributed, presentation-ready *comparison library*. One paper may contribute multiple distinct model variants. This file is a **literature reference**, not a head-to-head test on common RRUFF IDs. It does not change the owner's five-paper 60/80/full acceptance hierarchy or the three research outcomes (RRUFF Accuracy, independent-CIF data-efficiency curve, ECE).

## Reference presentation style (user selection)

![Dark-table recreation based on AlphaDiffract Table 1](assets/alpha_diffract_2026_table1_style_reference.svg)

The figure is a **readable SVG recreation of the user's screenshot**, not the source paper's native artwork or a direct export of the screenshot. **Figure source:** Andrejevic et al., *AlphaDiffract* (2026), Table 1, [arXiv 2603.23367v1](https://arxiv.org/html/2603.23367v1). Dark charcoal background, white concise text, light horizontal rules, clear model/variant columns, bold only the notable numerical entries. For future supervisor slides, *replace dataset columns with RRUFF-focused columns unless multiple domains are actually evaluated*. Preserve citations and paper/model variant/source protocol footnotes. Never combine simulated and real Accuracies without indicating the dataset.

**2026-11-03 owner correction:** The library's inclusion criterion is **other researchers' published RRUFF-classification-relevant work**, including a model with extra chemical-formula input, if reported transparently. **DiffractGPT DGPT-formula (28.75%, AlphaDiffract 2026 Table 1 re-evaluation) is INCLUDED in the main literature comparison as a below-pass reference**, not excluded just because it is not a PXRD-only model. Original Choudhary training used JARVIS-DFT simulated data and reports no labeled RRUFF training. This broadens the comparison set; the pass tier includes Vecsei 2019 Dense at 70%, Lee 2023 at 74.24%, and Salgado synthetic-only at approximately 74% or alter full/80 targets. [Original DiffractGPT 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874033/).

**Owner 2026-11-03 correction:** Vecsei et al. 2019 **Dense/MLP at 70.0% is PASS/60**, not a below-pass reference. Its 56.0% CNN variant remains in the broader comparison. The pass tier is a set of literature anchors, not a demand that all different RRUFF cohorts were identical.

## A. Owner-approved grading — presentation-ready five-column table

**Approved slide format:** Grade | Paper / model | **Simulated training source structures (CIF parents / curated records)** | **Real RRUFF evaluation spectra** | **RRUFF seven-system top-1 Accuracy**. Values are grounded in original-paper statistics; estimates and unknowns are explicitly marked, not substituted with archive catalog size.

| Grade | Paper / model | Simulated training structures | Real RRUFF test spectra | RRUFF Accuracy |
| --- | --- | ---: | ---: | ---: |
| **Pass / 60** | **Vecsei et al. 2019 — Dense/MLP** | **114,404 actual training** (128,404 deduplicated total) | **~800** | **70.0%** |
| **Pass / 60** | **Salgado et al. 2023 — synthetic-only Large NPCNN** | **171,006 curated ICSD parents*** | **~908 source entries** (precise zero-shot evaluated N unverified) | **~74%** |
| **Pass / 60** | **Lee et al. 2023 — Large FCN** | **197,131 curated ICSD parents*** | **~960 inferred** (about 1,600 source spectra, highest-background 40% removed; precise evaluated N unverified) | **74.24%** |
| **80 / PRIMARY** | **AlphaDiffract 2026 — 10-model ensemble** | **312,267 curated ICSD + MP records*** | **734** | **81.74 ± 0.78%** |
| **Full / 100** | **SimXRD-4M 2025 — CNN11** | **119,569 unique MP parents** | **Unknown** (**3,002 is archive/catalog count, NOT confirmed score denominator**) | **89.3%** |
| **Full / 100** | **XQueryer-NoElem 2025** | **100,315 MP structures*** | **1,003** | **91.5 ± 1.5%** |

* **Training-structure interpretation:** An asterisk denotes **curated structure corpus/structure records**, which should not silently be labeled the exact **post-split training** parent count. For Vecsei, the **original paper explicitly states 128,404 deduplicated input patterns, divided into 7,000 simulated test, 7,000 simulated validation and 114,404 training**. For Salgado, Lee, XQueryer, the listed figures are paper corpus sizes and actual training subsets may be smaller. For AlphaDiffract, 312,267 retained ICSD/MP records are not formally proven independent-parent deduplicated across databases. SimXRD's 119,569 structures participate in all environment-view splits of the in-library training scenario; its out-of-library scenario uses different nonoverlapping parents. All source-versus-training distinctions matter for a future data-efficiency comparison.
* **RRUFF test N interpretation:** Vecsei's source evaluates about **800** real RRUFF records. Salgado's **~74% synthetic-only** result is on its reported **908-record RRUFF dataset**, but its exact evaluated count/IDs for that condition are not independently recovered. Lee's **~960 is arithmetic only** (0.6 × approximately 1,600); the exact postfilter number is unpublished. SimXRD's **3,002 is a catalog reference**, NOT a confirmed 89.3% evaluation size. AlphaDiffract's **734 classification** count includes 59 calculated powder profiles derived from single-crystal measurements. XQueryer's **1,003 classification** count is distinct from 849 MP-matched structure identification records.
* **Zero-shot comparison rule:** **All six owner-assigned grading entries use 0 labeled RRUFF training/fine-tuning samples**, not 0 potential use of unlabeled target-domain information. AlphaDiffract is RRUFF-informed in its augmentation/noise and some hyperparameter decisions. Salgado's **86% using ~452 real RRUFF training spectra** is separate and **not eligible** for grading. Different published RRUFF curation choices mean this is a literature TARGET scoreboard, not matched-sample head-to-head benchmarking. Keep the RRUFF locked test outside model selection.
* **Primary sources:** [Vecsei 2019 original PDF, Section IV, Table I](https://arxiv.org/pdf/1812.05625) (114,404 training; ~800 RRUFF); [Salgado 2023](https://www.nature.com/articles/s41524-023-01164-8); [Lee 2023](https://doi.org/10.1002/aisy.202300140); [AlphaDiffract 2026](https://arxiv.org/html/2603.23367v1); [SimXRD-4M 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/b04843d76c9f090beca55f335c4ea6bf-Paper-Conference.pdf); [XQueryer-NoElem 2025](https://academic.oup.com/nsr/article/12/12/nwaf421/8268901). Detailed row-specific cohort sourcing: [five-paper cohort audit](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md).

## B. Additional published model variants INCLUDED in the RRUFF comparison (without creating new 60/80/full thresholds)

| Paper / model variant | RRUFF crystal-system Accuracy | Original source of the number | Input and comparison status |
| --- | ---: | --- | --- |
| **Vecsei et al. (2019) — Convolutional / CNN** | **56.0%** | AlphaDiffract 2026 Table 1, citing Vecsei et al. 2019 | Same historical paper, different architecture. The 85% in the ICSD column is **synthetic ICSD**, not real RRUFF |
| **Choudhary (2025) — DiffractGPT DGPT-formula** | **28.75%** (source also shows **26.57%** in parentheses) | **AlphaDiffract 2026 Table 1 re-evaluated the Choudhary model on its own RRUFF cohort** | **USER-INCLUDED ZERO-SHOT COMPETITOR / below-pass reference**. Original DiffractGPT trains on JARVIS-DFT simulated XRD/structures with no reported labeled RRUFF adaptation; DGPT-formula also uses chemical formula input. Include in the same main RRUFF Accuracy comparison and presentation, explicitly footnote extra chemistry input and third-party reevaluation. Do not claim that 28.75% was in the original Choudhary paper or a PXRD-only matched setting. Exact parenthetical protocol remains source-as-written |

**References:** Vecsei et al., *Neural network based classification of crystal symmetries from x-ray diffraction patterns*, Phys. Rev. B **99**, 245120 (2019), https://doi.org/10.1103/PhysRevB.99.245120 . Choudhary, *DiffractGPT*, J. Phys. Chem. Lett. **16**, 2110–2119 (2025), https://doi.org/10.1021/acs.jpclett.4c03137 . AlphaDiffract Table 1 https://arxiv.org/html/2603.23367v1 (this is specifically the secondary source of all three of the above numbers).

## C. Additional **same-paper, same-RRUFF-protocol** model variants worth retaining

Cao et al., **SimXRD-4M**, ICLR 2025 **Table 5**, trained/validated on SimXRD and evaluated on the same stated RRUFF panel:

| Model variant | RRUFF seven-system top-1 Accuracy |
| --- | ---: |
| CNN11 | **89.3%** |
| CNN7 | 86.8% |
| CNN10 | 85.9% |
| Bidirectional-GRU | 80.4% |
| CNN9 | 79.2% |
| Bidirectional-LSTM | 78.8% |
| GRU | 77.4% |
| LSTM | 72.3% |
| PatchTST | 72.3% |
| MLP | 32.5% |
| Transformer | 35.4% |

**Source:** https://proceedings.iclr.cc/paper_files/paper/2025/file/b04843d76c9f090beca55f335c4ea6bf-Paper-Conference.pdf (Table 5). All entries above are **model variations in ONE research paper**, **not 11 independent new papers**, and not newly designated grading targets. This within-paper architecture table is a useful reference for our own CNN11-vs-ResNet development; its absolute accuracy still should not be conflated with the differently filtered AlphaDiffract or XQueryer cohorts.

### Same-paper model variants from Salgado et al. 2023

The paper's **large synthetic dataset** experiment (before adding real RRUFF labels) also reports **SCNN 40%**, **MLP 67%**, and **NPCNN 74%** seven-way Accuracy on its RRUFF cohort. This is particularly useful evidence of architecture/pooling effects at a fixed source paper and dataset; their later 86% after 'souping' is NOT included in the zero-shot rows. Source: https://www.nature.com/articles/s41524-023-01164-8 (Results, "Using mix and large datasets for training"). These are **additional model variants, not new independent papers or grading tiers**.

## D. Other contextual comparisons, excluded from the strict zero-labeled-RRUFF/PXRD-only list

| Model / paper | Reported RRUFF Accuracy | Why separate |
| --- | ---: | --- |
| Salgado 2023 — *Large Souping* | 86% | ~452 labeled real RRUFF samples included in training; **not zero-shot** |
| Cao et al., 2025 — XQueryer with elemental composition | 93.3% | Element metadata is supplied; **not PXRD-only** (NoElem = 91.5%) |
| Park et al., 2017 — CNN | 94.99% **ICSD**, *not RRUFF* | Do not insert 94.99% into an RRUFF Accuracy ranking |
| Lee et al., FCN (different paper/model) | 82.17% **Materials Project**, *not RRUFF* | Do not insert as RRUFF |

## E. Five-column deliverable rule and presentation usage

When adding a **new paper**, collect **(1) original paper and model variant, (2) unique training CIF parents or curated structure records, (3) *actual* evaluated RRUFF spectrum count, (4) RRUFF crystal-system top-1 Accuracy, (5) labeled RRUFF training/fine-tuning count**. Flag Unknown, distinguish a reported paper number from a third-party re-evaluation, and note non-PXRD inputs.

For **weekly/supervisor slides**, show a short AlphaDiffract-style table with `Paper / Model | Training CIFs | RRUFF Test N | RRUFF Accuracy`; use bold face for the owner's model, the key threshold, or top verified result. Put RRUFF real-label adaptation count / domain use in a concise footnote if needed. The owner's fixed grade targets now include **Pass Vecsei Dense 70% + Lee 74.24% + Salgado synthetic-only ~74%**; 80 AlphaDiffract; Full SimXRD CNN11+XQueryer-NoElem. **Include DiffractGPT DGPT-formula 28.75% as an actual reference model in the same RRUFF leaderboard, below the pass threshold, with a succinct note on formula input and third-party reevaluation; do not omit it on those grounds.** The other two project headlines are the **data-efficiency curve and ECE**; neither changes the Accuracy scorecard.

**Image provenance:** The user supplied a screenshot of AlphaDiffract Table 1 (929×514 px) in the 2026-11-03 conversation and specifically approved its black-background minimalist layout. This repository includes the above vector re-creation for durable display. The exact original screenshot is preserved in the conversation attachment / separately exported local artifact, rather than being misrepresented as this SVG.
