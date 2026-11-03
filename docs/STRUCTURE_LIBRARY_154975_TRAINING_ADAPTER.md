# 154,975 structure library training adapter

**Status (2026-11-03):** The schema bridge, complete three-split PeakTable caches, file-integrity audit, and train/validation runner manifest are complete. No persistent spectra or model-training run was created.

## Schema bridge

The merged source shards are gzip-compressed JSONL. Each row stores the Pymatgen structure in `structure`, the cache fingerprint in `source_structure_fingerprint`, the crystal-system label in `crystal_system`, and its split and canonical parent ID.

`scripts/precompute_peak_tables.py` now accepts `--records-path` for external `.jsonl` or `.jsonl.gz` input. For the merged-library schema it maps:

| Source field | Precompute field | Purpose |
| --- | --- | --- |
| `structure` | `standardized_structure` | Pymatgen structure passed to ideal-reflection precomputation |
| `source_structure_fingerprint` | `structure_fingerprint` | Structure identity recorded in the cache manifest |

The original compressed shards are read-only inputs; no rewritten copy of the structure library is needed. Precompute outputs remain under a data root inside `xrd_robustness`, as required by the current project data-path policy. Use one output root per split so the train/validation/test roles stay explicit.

## Training manifest

After train and validation PeakTable caches are complete, `scripts/build_merged_library_training_manifest.py` joins the source shards to their cache manifests. It checks split labels, unique IDs, class names, parent-group split leakage across all three source shards, exact train/validation source-cache ID sets, fingerprints, cache completion counts, and file sizes. It writes `training_records.v1.jsonl` with the runner contract (`material_id`, `split`, `label`, `crystal_system`, and relative `peak_table_path`). The path is relative to the cache root so that the entire cache-root directory can move to a Tencent Cloud workspace as one unit.

The runner manifest contains **train and validation only**. The test shard remains excluded from model fitting and model selection. Its PeakTables may be generated separately for a frozen final evaluation.

## Full-run command sequence

Run these commands from the repository root in a compatible Python environment. `--data-root` is relative to `xrd_robustness`; `--records-path` may point to the raw shards on another drive. The explicit `--external-python` option is required when the batch helper uses a separate Pymatgen environment; its packages must be importable with Python's user site disabled. The default cache name is `peak_tables_v7_reflection`.

```powershell
$source = 'D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103'
$cacheRoot = 'data/merged_154975_v11'
$python = 'C:\path\to\compatible\python.exe'

foreach ($split in @('train', 'validation', 'test')) {
  & $python xrd_robustness/scripts/precompute_peak_tables.py `
    --data-root "$cacheRoot/$split" `
    --records-path "$source/${split}_structures.jsonl.gz" `
    --workers 6 --batch-size 100 `
    --external-python $python
}

python xrd_robustness/scripts/build_merged_library_training_manifest.py `
  --source-dir $source `
  --cache-root $cacheRoot
```

The precompute command writes the current cache builder's completion/skip summary and `.npz` PeakTable format. Do not build the training manifest from a limited smoke cache: its source and cache ID counts must match exactly. The builder loads and sorts one full shard in memory.

## Completed full-library run (2026-11-03)

All three original compressed shards were read without rewriting them. The adapter mapped `structure` to the precompute field `standardized_structure` and `source_structure_fingerprint` to `structure_fingerprint` on every row.

| Split | Rows completed | Skipped | PeakTable bytes | Precompute time |
| --- | ---: | ---: | ---: | ---: |
| Train | 108,483 | 0 | 1,213,929,797 | 1,777.38 s |
| Validation | 23,246 | 0 | 260,847,519 | 334.68 s |
| Test | 23,246 | 0 | 264,560,366 | 334.52 s |
| **Total** | **154,975** | **0** | **1,739,337,682** | **2,446.59 s** |

The precompute used six workers and batches of 100 on a local Windows workstation (32 logical processors, 31.7 GiB physical RAM) with Pymatgen 2026.5.4 / pymatgen-core 2026.10.31. Sampled process memory showed about 5.52 GiB for the main process and about 0.55 GiB per helper; system available memory reached a sampled low of 3.6 GiB while other Python workloads were active. This was not a Tencent Cloud run or a cloud sizing recommendation. The measurements cover ideal-reflection PeakTable creation, not rendered-spectrum export or a model-training epoch; future full-scale training and cloud resource planning continue to target the user's planned Tencent Cloud server.

The builder produced 131,729 runner records (108,483 train and 23,246 validation). The test shard is absent from that runner manifest. An independent exact-ID/fingerprint/size/per-file-SHA256 audit passed for all 154,975 cache files. The real-cache V11 smoke loaded one train and one validation PeakTable, rendered two distinct same-parent 3,501-point views for each, and replayed each pair exactly. The focused simulator and cache tests passed (10 passed).

PeakTables are ideal reflection intermediates; this run did **not** store 154,975 V11-rendered spectra and did **not** start model training. Machine-readable hashes, per-split timing, cache sizes, and smoke evidence are recorded in [the full-run evidence JSON](../xrd_robustness/reports/simulator_v11/merged_154975_precompute_20261103.json). The ignored cache directory can be copied as a unit to a Tencent Cloud workspace.

## Files

- [PeakTable precompute script](../xrd_robustness/scripts/precompute_peak_tables.py)
- [Training manifest builder](../xrd_robustness/scripts/build_merged_library_training_manifest.py)
- [V11 bounded readiness evidence](SIMULATOR_V11_READINESS_20261103.md)
