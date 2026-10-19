# DONUT source fidelity audit

**Audit date:** 2026-10-19
**Paper:** Aileen Luo et al., “DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis,” *npj Computational Materials* 11, 380 (2025), DOI [10.1038/s41524-025-01860-7](https://www.nature.com/articles/s41524-025-01860-7).
**Official code:** [AdvancedPhotonSource/DONUT](https://github.com/AdvancedPhotonSource/DONUT), pinned commit `090c10bdf99333d3670dc26e617a93364f714bdc`.

The official repository files were fetched at the pinned commit into the read-only local mirror `E:\AI4science_DONUT_reference_verified`. Git blob object IDs were checked against the GitHub tree API for all five files:

| File | Git blob |
|---|---|
| `README.md` | `388985b6441caae337d74d0c8ff556a8ad169f1e` |
| `training.py` | `97ecd6bd5b2f59cce4a9e14271439b983557d504` |
| `train_with_thickness.py` | `ec619f61555075b3ce86597a1f1c15228230ca0b` |
| `sim_SIO_gpu.py` | `68a669b67a2fa51d6e6cadea68b14b152d9d2ffd` |
| `LICENSE` | `ef30eba6a4a6965de369d024760b4f56fca2d3e2` |

## Mechanism from paper and code

The paper describes a CNN encoder whose low-dimensional latent corresponds to physical parameters. That same constrained latent feeds (1) a symmetric decoder that reconstructs a denoised diffraction pattern and (2) a fixed differentiable physics model. The outputs are compared with the measured input using weighted SmoothL1 loss. The model is trained without labeled parameter targets. The paper's formulation and architecture discussion is in “Model approach” and “Neural network architecture and training.”

Pinned `train_with_thickness.py` implements a six-block `Encoder` (`Encoder.__init__`, lines 204–218) and a decoder started only from the four-coordinate bottleneck (`Decoder.__init__` and `Decoder.forward`, lines 221–236). `DonutNN2.forward` applies `1.7159 * tanh((2/3) * x)` at lines 310–311, sends the result to the decoder and the fixed scattering calculation, then returns reconstruction, physics simulation and physical latent at lines 314–370. There are no encoder feature skip connections into the decoder. The decoder and physics branches are optimized jointly.

Pinned `training.py` `Trainer.train` (lines 152–168) applies `criterion` separately to decoder reconstruction and simulator output, weights them and backpropagates the sum. `Trainer.validate` (lines 185–201) uses the same weighted sum. `train_with_thickness.py` uses `nn.SmoothL1Loss()` and weights `(1, 5)` at lines 373–408; AdamW has encoder/global learning rate `1e-4` and decoder learning rate `3e-5` at lines 373–375.

## Paper/code configuration differences

The paper reports decoder learning rate `1e-5`, batch size 16, 30 epochs and describes dropout 0.1. At this pinned code revision, the selected `train_with_thickness.py` script sets batch size 256 and 60 epochs, the `DonutNN2` instantiation uses its default dropout `0.0`, and the decoder AdamW group sets `3e-5`. `training.py` confirms loss weights `(1, 5)`. We preserve the source discrepancy rather than presenting one as the other. This PXRD run follows the pinned model/loss mechanism, uses the paper's batch size and the preregistered 30-epoch ceiling, and uses the observed code's `3e-5` decoder learning rate and zero-dropout default.

## PXRD adaptation boundary

The source paper predicts strain and two tilt angles from a 2D single-Bragg-peak nanodiffraction image. This task adapts the **dual-branch unsupervised training principle**, not the original geometry or reported performance: 1D powder patterns are encoded into normalized lattice coordinates and, in later stages, selected scalar measurement parameters. The physics branch reuses `CachedTetragonalGPUForward` and the repository's `expected_profile`; it is fixed and differentiable. Lattice and nuisance truth are stored only for synthetic generation and post-hoc scoring, never used in DONUT train or checkpoint-selection losses. The decoder receives only the physical latent, not an input skip path.

Experiment 3 texture uses the existing reflection-level March–Dollase simulator from `xrd_robustness` for a held-out OOD stress case. The CUDA forward model has no validated differentiable texture term; texture results are not represented as a texture inverse.
