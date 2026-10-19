# DONUT source fidelity audit

**Audit date:** 2026-10-19
**Upstream:** AdvancedPhotonSource/DONUT commit `090c10bdf99333d3670dc26e617a93364f714bdc`
**Local mirror:** `E:\AI4science_DONUT_reference_verified` (small, read-only source mirror; not a full upstream checkout)
**Paper:** Luo et al., *npj Computational Materials* 11, 380 (2025), DOI [10.1038/s41524-025-01860-7](https://doi.org/10.1038/s41524-025-01860-7).

## Source identity and integrity

The mirror's `SOURCE_COMMIT.txt` records the pinned commit. A separate temporary bare Git fetch of the official `main` ref resolved to the same commit. The following local files were hashed as Git blobs and compared to the official commit tree; every object ID matched:

| File | Official Git blob | Local match |
|---|---|---|
| `README.md` | `388985b6441caae337d74d0c8ff556a8ad169f1e` | yes |
| `training.py` | `97ecd6bd5b2f59cce4a9e14271439b983557d504` | yes |
| `train_with_thickness.py` | `ec619f61555075b3ce86597a1f1c15228230ca0b` | yes |
| `sim_SIO_gpu.py` | `68a669b67a2fa51d6e6cadea68b14b152d9d2ffd` | yes |
| `LICENSE` | `ef30eba6a4a6965de369d024760b4f56fca2d3e2` | yes |

The GitHub REST API request was unavailable from this Windows environment (the HTTPS client failed certificate credential acquisition). Content identity was therefore verified against the official Git commit tree fetched from GitHub, which supplies the same Git blob object IDs. This is not represented as a full checkout or a GitHub API response.

## Original method and code mapping

The paper describes a 2D SXDM physics-aware autoencoder. An image is encoded to a low-dimensional physical latent; the latent feeds both a symmetric image decoder and a differentiable geometric diffraction simulator. Training compares **both** generated outputs to the measured input using a weighted SmoothL1/MAE-like composite. The modified tanh activation is `1.7159 * tanh((2/3) z)`. In the pinned implementation:

| Paper mechanism | Pinned implementation evidence | DONUT-PXRD mapping |
|---|---|---|
| Convolutional encoder | `train_with_thickness.py`, `DoubleConv`, `DownSample`, `Encoder`; `DonutNN2.forward` calls `self.encoder(x)` | Replace 2D convolutions/pooling and image geometry with 1D convolutions/pooling over a powder profile. |
| Physically scaled latent | `DonutNN2.forward`, `constrained_params` then `scales`; physical conversion precedes simulator | Use a two-coordinate `du,dv` latent for stage 1, and `[du,dv,delta_2theta]` in stage 2. Preserve bounded modified-tanh outputs and explicit physical scaling. |
| Parallel decoder and physics branches | `DonutNN2.forward`: `recon = self.decoder(constrained_params)` and `sim_norm` from the same scaled latent | Decoder starts from the latent alone; no raw-input skip or bypass. Both branch losses backpropagate through the encoder. |
| Fixed differentiable physical forward | `DonutNN2.forward` computes the nanodiffraction model; it is not a learned simulator | Reuse fixed `CachedTetragonalGPUForward` plus `expected_profile` for powder PXRD; simulator/model parameters are not optimized. |
| Weighted SmoothL1 objective | `training.py`, `Trainer.train` (lines 152–172): decoder loss and simulation loss each use the same criterion; sum is `weights[0] * decoder + weights[1] * sim`. Validation follows the same rule (lines 185–208). | Keep both losses on the same transformed observed spectrum. Freeze weights before scored training. |
| Encoder/decoder rate split | `train_with_thickness.py`, lines 117–121 and 371–376: encoder LR `1e-4`, decoder LR `3e-5`, batch size `256`, 60 epochs in this script, SmoothL1, AdamW defaults, and weights `(1,5)` | Use 30 epochs and batch size 16 as bounded study settings from the approved brief; use encoder LR `1e-4`, decoder LR `1e-5`, and weight decay `0.01` as approved paper-guided settings. Record these as PXRD protocol choices, not exact values copied from the pinned script. |

Paper Methods specify the weighted SmoothL1 form and modified tanh; the pinned `training.py` proves the actual two-branch weighted objective. These are separate source facts and are not conflated. The inspected training script uses `(1,5)` weights; batch size 256 and 60 epochs. The approved PXRD study uses 30 epochs, batch size 16 and encoder/decoder rates `1e-4/1e-5`; these are recorded as adaptations. Weight decay uses the AdamW default `0.01`. The paper's different reported weighting/configuration values remain a paper/code divergence, not silently attributed to the pinned script.

## Fidelity boundary

This experiment reproduces DONUT's **core training mechanism** after adapting the input/decoder geometry from 2D images to 1D powder profiles and replacing the SXDM forward physics with the fixed tetragonal powder-XRD forward model. It does not reproduce DONUT's 2D SXDM geometry, experimental dataset, latent quantities, or numerical figures. No true lattice or nuisance labels are supplied to DONUT training losses, selection, or model inputs. Ground truth is reserved for synthetic data generation and post-hoc scoring. March–Dollase texture is evaluated as nondifferentiable generator-side shift stress unless a differentiable hkl-aware model separately passes its physics gates.

## Primary paper source notes

The publisher's article and Methods identify DONUT as unsupervised training of a CNN physical bottleneck with a decoder and an embedded differentiable scattering model. The paper's results describe the physics branch as more heavily weighted than the decoder branch for the reported applications. The official GitHub README identifies the project and points to its training/simulation implementation. The publisher page was discoverable through search but redirected direct fetches to an inaccessible identity-provider URL; the source audit therefore uses its indexed article text and the directly inspected, hash-verified official code mirror.
