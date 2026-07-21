# Codex Task — Data and Schema Audit

Read `AGENTS.md` and `context/00_CURRENT_STATE.md` through `context/05_DATA_AND_REAL_XRD_VALIDATION.md` first.

Task:

1. Inspect the available SimXRD-related files/dataset without modifying raw data.
2. Write `reports/data_audit.md` containing:
   - data location(s), file types, sizes, and checksums where practical;
   - pattern tensor shape and `2θ` grid conventions;
   - label vocabulary/order and class counts;
   - source/material/structure IDs usable for leakage-safe splitting;
   - existing preprocessing and normalization;
   - existing split files and whether they leak source structures;
   - explicit unknowns, including license/usage status.
3. Implement a read-only loader plus a visualization script for random patterns and label distribution.
4. Add tests that fail loudly if the label mapping or grid shape changes unexpectedly.

Do not create a train/validation/test split by random pattern index unless source-structure grouping has been verified.
