# CIF provenance

| Candidate | Source and source structure | CIF SHA-256 |
|---|---|---|
| BaTiO₃ P4mm | [COD 9014273 CIF](https://www.crystallography.net/cod/9014273.cif); Shirane, Danner & Pepinsky, *Physical Review* 105 (1957) 856–860, doi:10.1103/PhysRev.105.856. COD header requests attribution to the source article. | `e880d6f9df10ad4a2bb347dbbeae2712817d95e2f16df9390784d916a0c02f9c` |
| MgO rocksalt Fm-3m | [COD 9000505 CIF](https://www.crystallography.net/cod/9000505.cif); Hazen, *American Mineralogist* 61 (1976) 266–271; 23 °C, 1 atm. COD header requests attribution to the source article. | `73e348f73ec4e2e41f2ea08cbe5f393366e7cfeb55285eebbb185ace7ec94923` |
| CeO₂ fluorite Fm-3m | [COD 9009008 CIF](https://www.crystallography.net/cod/9009008.cif); Wyckoff, *Crystal Structures*, vol. 1 (1963), 239–444. COD record identifies public domain/CC0 and requests attribution. | `cfb862ebff35ab342a254a267eff4d94a86a18ae284142289e7b56d8d7b8e099` |
| Grossular garnet Ia-3d | [COD 9001871 record](https://www.crystallography.net/cod/9001871.html); source AMCSD; Geiger & Armbruster, “Mn3Al2Si3O12 spessartine and Ca3Al2Si3O12 grossular garnet: Structural dynamics and thermodynamic properties,” *American Mineralogist* 82 (1997) 740–747, 293 K. | `EBDD9ABB0BB717A8154EE25B00E26E4AA69F9261EAAFA56B02FE77E30E3AFFD6` |

Each CIF is a pinned local snapshot. Registry metadata and hashes are checked in the demo/test workflow. CIF provenance supports the candidate structure definition; it is not evidence that a measured sample contains that phase.

The Grossular record is the ideal endmember formula Ca3Al2Si3O12 (pymatgen reduced formula `Ca3Al2(SiO4)3`), cubic Ia-3d (No. 230), with a=11.619 Å at 293 K. It was selected by mineral subgroup, composition, symmetry, and source publication—not by distance to any target RRUFF refined cell. COD records are distributed under CC0; the source publication remains attributed in the CIF header and pilot report.
