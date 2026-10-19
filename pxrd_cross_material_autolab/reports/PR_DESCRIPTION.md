## PR43 delivery

The bounded synthetic pipeline completed seven supported CIF templates across three crystal systems: BaTiO3, MgO, CeO2, rutile, ZnO, Si and grossular. The manager provides immutable config/source/CIF hashes, gates before training, atomic state/events, conservative resume, resource limits, complete learning curves and fit attempts, metric recomputation and Chinese reports.

21 supervised MLP models (three seeds/material,24 epochs max);539 primary held-out parameter parents;112 NEW exploratory mismatch parents;5950 method/seed/sample records and8330 optimizer attempts retained. Primary991.29s wall;20.41s CUDA training/validation wall;1119.11s global through stress. Training/weights/generated spectra stay privately ignored; compact provenance/results are committed.

All primary cases meet the frozen runtime-Pareto rule **relative to full P3 cost**, with essentially equal final accuracy. P0 already achieves similar accuracy on five materials; MgO/ZnO primary P0 errors are larger despite solver success. The separate16-parent/material post-primary independent-renderer/peak-shape/background stress shows no extra neural accuracy/reliability gain over P0/P3. Do not interpret P3-relative timing as a universal neural win, zero-shot material transfer, real-XRD validation or resolution of previous real-Garnet failures.

Coverage is **PARTIAL; supported subset COMPLETED**:12 source IDs attempted,9 verified identities,7 supported trials. Preserve two wrong-ID sources, a forsterite fetch failure, and calcite/corundum unsupported trigonal skips. N+B and low-noise arm skipped/not run explicitly. No frozen gate, primary test, checkpoint, seed or decision threshold changed after opening. The independent stress was separately registered after primary opening and cannot replace primary results. A report-only UTF-8 decoding failure and one correction are preserved; no scientific trial repeated.

Validation:18 primary CPU tests plus3 stress engineering tests PASS; primary/stress hash and per-sample metric recomputation PASS; independent saved-JSON audit confirms counts, pairing, units and P3 accounting; git diff --check PASS. Main classification and old inversion results untouched; no merge.

Review `pxrd_cross_material_autolab/reports/OVERVIEW.md`, `COMPARISON.csv/json`, `MATERIAL_SUMMARY.csv/json`, `FAILURES.json`, `status.json`, `validation.json`, original immutable run manifests and stress report. Reproduction and conservative resume commands are in the module README. Current state and project history contain only the scoped separate-pilot update.
