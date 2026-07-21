# 08 — Literature and Resource Index

The original PDFs are listed in `references/REFERENCE_CATALOG.md` and, in the full archive, copied under `references/original/`.

## Core XRD / reliability references

1. **SimXRD-4M: Big Simulated X-Ray Diffraction Data and Crystal Symmetry Classification Benchmark** (ICLR 2025)
   - Role: primary simulated benchmark reference; inspect exact labels, preprocessing, data format, and split protocol before coding.

2. **A Unified Preprocessing Framework for High-Throughput Diffraction Pattern Analysis** (npj Computational Materials, 2026)
   - Role: diffraction preprocessing, reproducibility, and measurement-analysis context.

3. **AI-Driven Structure Refinement of X-Ray Diffraction** (arXiv 2026)
   - Role: emphasizes diffraction-consistent constraints and the physical meaning of peak positions, profiles, overlap, background, and instrument/sample factors.

## Conceptual scientific-ML references

4. **Kalinin et al., From atomically resolved imaging to generative and causal models** (Nature Physics, 2022)
   - Role: model/data/physics framing; probabilistic, generative, and causal vocabulary should be used with care.

5. **Ziatdinov et al., Causal analysis of competing atomistic mechanisms in ferroelectric materials...** (npj Computational Materials, 2020)
   - Role: caution that correlative ML can be susceptible to confounders and observational bias; supports reliability motivation, not a direct method recipe for XRD.

6. **AtomAI Framework for Deep Learning Analysis of Image and Spectroscopy Data...**
   - Role: examples of scientific-data workflows, uncertainty, invariance-aware representations, and simulation/measurement integration.

7. **Deep Learning of Atomically Resolved STEM Images: Chemical Identification and Tracking Local Transformations**
   - Role: useful analogue for simulated-to-experimental data, physically varied acquisition conditions, and weakly supervised scientific interpretation.

## Materials / dielectric context

8. **Probing Atomic-Scale Structure of Dielectric Ceramics with STEM**
   - Role: dielectric materials and experimental characterization context.

9. **AI-Assisted Discovery of High-Temperature Dielectrics for Energy Storage**
   - Role: examples of materials-AI positioning; do not assume its methodology transfers directly.

10. **Machine-Learning-Designed BCZT–SBT Heterointerface Unlocks Fatigue-Resistant Energy Storage**
    - Role: user’s group/domain context for dielectric materials.

11. **Machine Learning-Driven Ultra-High Energy Storage Performance in Ferro-Superparaelectric Capacitors**
    - Role: user’s group/domain context for dielectric materials.

12. **Designing Polymer Nanocomposites with High Energy Density Using Machine Learning**
    - Role: adjacent ML-for-dielectrics example.

13. **A Review of Machine Learning with Small and Limited Data**
    - Role: small-data caution and methodology review; not the central project reference.

## Internal/reference materials

14. **组会1.pdf**
    - Role: an example of an engineering-first molecular-ML project pipeline. Use as a process reference, not a topic template.

15. **chatgpt_project_memory.md**
    - Role: older May 2026 project-memory export centered on FerroAI; archived verbatim in `legacy/`.

## Citation rule

When a claim in code documentation, a report, or a paper depends on a particular source, cite the original paper rather than this context pack. This pack is only an index and decision record.
