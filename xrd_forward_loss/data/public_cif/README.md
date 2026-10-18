# Public tetragonal BaTiO3 known-phase inversion feasibility (2026-10-18)

**Status:** single-CIF public-data engineering pilot; not a completed multi-material / real-data study. Code is isolated on `feat/public-batio3-forward-ab`, derived from Draft PR #11 and does not alter V9 or its frozen results.

## Source
- Crystallography Open Database **COD 9014273**, BaTiO3 P4mm (#99).
- Historical structure citation: G. Shirane, H. Danner, R. Pepinsky, *Physical Review* **105**, 856 (1957), DOI [10.1103/PhysRev.105.856](https://doi.org/10.1103/PhysRev.105.856). The CIF contains the original COD / AMCSD metadata and attribution. Source URL: https://www.crystallography.net/cod/9014273.cif
- Parsed reference structure: a=b=3.986 Å, c=4.026 Å, five atomic sites.

## Purpose and workflow
- Check existing GPU differentiable tetragonal forward physics on an independent, publicly cited ferroelectric structure (rather than the previous HfCd).
- Cross-check peak positions against Pymatgen's XRDCalculator, and check local `du,dv` Jacobian conditioning. This is a **screening gate**, not the full exhaustive CPU-GPU profile parity / diffraction physics audit.
- Generate Sobol-sampled lattice parameters, forward XRD, and independent count-noise + constant-background inputs. Model A is the existing supervised regressor; B adds observed-profile forward-reconstruction loss from Draft PR #11, with the **same** dataset and seed. The B weight of 1.0 is inherited as an engineering setting: **not validation-selected for BaTiO3**.
- Splits separate lattice parameter realizations of this single reference structure, **not** independent crystal structures. This is conditional same-structure regression, not transfer/generalization to new compositions or polymorphs.
- This script **does not yet include V9's full five-nuisance physics sampler**. It is intentionally isolated from an active independent Codex branch `codex/forward-loss-v9-reuse`, which is developing that adapter. Later the workflows may be joined only after scientific/engineering audit.

## Reproduction
From repository root in an environment containing Torch/CUDA, Pymatgen, SciPy and the three installed project packages:

```powershell
$env:PYTHONPATH = "xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src"
python xrd_forward_loss/scripts/run_public_batio3_smoke.py --gate-only --output xrd_forward_loss/reports/batio3_physics_check_new
python xrd_forward_loss/scripts/run_public_batio3_smoke.py --epochs 4 --sobol-power 7 --output xrd_forward_loss/reports/batio3_smoke_new
```

Do not reuse an existing output directory: results are deliberately not overwritten. Report numerical parameter MAE and physical-unit errors; avoid citing this exploratory test as proof of real-data precision, multi-seed reproducibility or a positive benefit of physics loss.

## Next gate
1. Review full Pymatgen–CUDA reference parity and symmetry/structure factors on this specific P4mm CIF before serious interpretation.
2. Use a new pilot configuration with a validation-only reconstruction-weight policy, adequate seeds, and physical nuisance modeling/clean-reference target choices explicitly locked.
3. Merge the V9 disturbance adapter only when tested; preserve `theta_true`, clean reference, observed profile and nuisance trace separately.
4. Hold out structurally distinct prototypes when moving to multiple CIFs; compare with physics-only fitting before claiming refinement-initialization value.
5. Evaluate real XRD only with independently documented instrument/sample data. The collaborator's final material is not yet chosen.
