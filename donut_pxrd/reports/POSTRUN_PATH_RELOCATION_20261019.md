# Post-run local path relocation (2026-10-19)

**Administrative change only. Not a new experiment, rerun, validation result or alteration of scientific protocol.**

All related directories have been consolidated below `E:\AI4science\_local`. E: drive should contain only one AI4science top-level directory: `E:\AI4science`.

## New locations

| Historical original path | New private local path |
|---|---|
| `E:\AI4science_donut_pxrd` | `E:\AI4science\_local\worktrees\donut_pxrd` |
| `E:\AI4science_DONUT_runtime` | `E:\AI4science\_local\runtime\donut` |
| `E:\AI4science_DONUT_checkpoints` | `E:\AI4science\_local\checkpoints\donut` |
| `E:\AI4science_DONUT_reference_verified` | `E:\AI4science\_local\reference\donut_verified` |
| `E:\AI4science_DONUT_reference` | `E:\AI4science\_local\reference\donut_original` |

Existing experimental output JSON, pre-registered configs, reports and manifests **remain byte-for-byte unchanged**. Thus some recorded absolute paths in historical results still point to the original E: location. They are **historical provenance**, not current working file paths. When interpreting those records, replace only the old directory prefix as shown above. Do not claim that `Path(record["checkpoint"])` still directly resolves without relocation.

Five Python launcher / audit scripts have undergone only path-string replacement and lookup of existing saved checkpoints by `Path(name).name` under the relocated checkpoint directory. They remain on this post-run change commit. The original experiment source revision is preserved in the immediate parent commit and its hashes are still checked against `donut_pxrd/reports/EXECUTION_STATUS.json`. **Do not compare these post-migration script hashes to the immutable scientific run's original source hashes.**

## Evidence verification

- `donut_pxrd/results/study_v1/exp4/validation.json` lists **24 unique checkpoint records** (15 original DONUT checkpoints and 9 Experiment 4 A/B/C checkpoints).
- After moving, all **24** files were verified on disk against their recorded SHA-256 and byte counts.
- The three original scientific script SHA-256 entries from `EXECUTION_STATUS.json` were verified using `git show HEAD:<path>` **before** the path-only source commit.
- `study_v1.json` still has SHA-256 `0b0c5a3ec4c4a8ba8515c4bb6b32f4493f0ca64fe7abd0811dabf498c0996fb4`.
- `experiment4_preregistration.json` still has SHA-256 `e611ff0af68e20165f424bec4260d6fb90fdab8976d58e68cfa6ca9380e61c69`.
- No new training or model selection was performed during migration.

Running archived training scripts can still require explicit scientific approval and fresh run IDs; migrating their checkpoint location is NOT permission to overwrite any old checkpoint.

All migrated `_local` directories are excluded from the main repository's Git staging using `.git/info/exclude`; checkpoint weights are not uploaded to GitHub.
