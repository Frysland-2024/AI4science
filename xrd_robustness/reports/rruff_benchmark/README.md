# JS-only RRUFF benchmark interface

The single runner is `xrd_robustness/src/xrd_robustness/rruff_benchmark.py`. It uses the project's ResNet-18-GN and `dynamic_js` loss, can render transient same-parent pairs through the existing `OnlineViewFactory`, optionally fine-tunes on labeled RRUFF training rows with cross-entropy, evaluates the test split once, and writes JSON/CSV/JSONL outputs plus hashed-ID predictions. Configs choose either validation-Accuracy checkpoint selection or a fixed final schedule. The latter supports external-test-only protocols with zero RRUFF training and no RRUFF validation; its epoch schedule must be declared before the one-time test evaluation.

## Data contracts

- A real source manifest contains `samples[]` with `rruff_id` or `sample_id`, `crystal_system`, and a relative `spectrum_path` to finite, non-pickle `.npy` arrays. The manifest's `preprocessing.points` must match the array length. `make-split` uses the fixed seven-system class order and stores sample/spectrum hashes. When audited real `parent_id` values exist, validation rejects parents shared across train/validation/test. For an exact paper split, use a verified ID-aligned author manifest rather than regenerating membership; newly generated stratified splits are approximate protocols.
- A precomputed synthetic-pair manifest contains `samples[]` rows with `parent_id`, integer `label`, `view1_path` and `view2_path`. The manifest producer must ensure both views came from that one parent; the runner requires the parent ID and both files, records exposures, and reports zero online-generated views for this mode.
- For online JS, provide a JSONL with one row per independent parent: `material_id` (use the deduplicated parent fingerprint), `label`, `split: "train"`, and `peak_table_path` to an existing `.npz` peak table. Provide a frozen simulation JSON and profile name. The existing `OnlineViewFactory` creates two views inside every batch; the result records unique parent count, online-generated view count, steps, simulation/config/manifest hashes and elapsed time.
- Real RRUFF rows without an audited parent mapping enter only the CE fine-tuning stage. The runner never pairs those rows for JS.

## Commands (PowerShell)

From `E:\AI4science\xrd_robustness` with the project's `xrd_test` environment:

```powershell
$env:PYTHONPATH = 'src'
python -m xrd_robustness.rruff_benchmark make-split `
  --source-manifest data\real_xrd\rruff_pipeline_test\manifest.json `
  --root data\real_xrd\rruff_pipeline_test `
  --output outputs\rruff_js_benchmark\splits\SMK-20261103-02.json `
  --seed 20261104 --train-per-class 3 --validation-per-class 1 --test-per-class 1
python -m xrd_robustness.rruff_benchmark run `
  --config configs\rruff_benchmark\smoke_js_online_finetune.json `
  --split-manifest outputs\rruff_js_benchmark\splits\SMK-20261103-02.json `
  --output-dir outputs\rruff_js_benchmark\SMK-20261103-02_run --device cuda
```

The four paper JSON files are protocol specifications and carry `PARTIAL` status. They are not permission to claim strict reproduction or to run without their missing paper-aligned manifests, preprocessing adapter, split, and compute plan. For external-test-only protocols, make a test-only split manifest and set `checkpoint_selection` to `fixed_final_state` and `training.real_epochs` to `0`; supply either a JS-trained initialization checkpoint or a synthetic JS manifest/online-parent manifest. Do not consult the RRUFF test metrics to choose the fixed schedule. For labeled RRUFF training protocols, freeze separate train/validation/test rows before fitting and use validation-only checkpoint selection. The separate smoke configurations are deliberately marked non-comparable.

## Metric contract

Accuracy is top-1 correct/test count; Macro-F1 is the unweighted mean across the fixed seven classes; ECE uses 15 equal-width confidence bins. Test predictions are written once after validation-only checkpoint selection. Result outputs include the config and runner SHA-256, split-manifest hash, model hashes, optimizer steps, training exposures, online-generated views, elapsed time, peak allocated GPU bytes, metric CSV, per-step JSONL and a CSV with sample IDs hashed.

The source manifest, real arrays, author-restricted datasets, and derived model checkpoint stay local. Public experiment evidence contains no raw measured vectors or unhashed RRUFF identifiers.
