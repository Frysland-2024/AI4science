# One-off split-sanity pilot: Dynamic ERM, 30 epochs, Validation every 10 epochs.
# Isolated from the registered 7-run tuning queue: separate output root and run ID.
# Authorized by the user on 2026-07-27 as a dataset/difficulty pilot only.
$ErrorActionPreference = 'Stop'
Set-Location 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
foreach ($name in 'OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS') {
    Set-Item -Path "Env:$name" -Value '2'
}
$env:CUDA_MODULE_LOADING = 'LAZY'

& $Python -s scripts/train_v7.py `
  --mode dynamic_erm `
  --simulation-config configs/simulation.v9.method_transfer.frozen.json `
  --train-profile train `
  --in-range-profile in_range `
  --ood-profiles ood_shift_negative,ood_shift_positive,ood_broadening,ood_noise,ood_background,ood_texture,ood_combo_shift_broadening,ood_combo_background_noise,ood_combo_texture_shift,ood_all `
  --variant b3 `
  --dataset-size 14060 `
  --data-root data/formal_14060 `
  --split-manifest data/formal_14060/manifests/split_manifest.json `
  --peak-cache-name peak_tables_v7_reflection `
  --epochs 30 `
  --max-optimizer-steps 18480 `
  --validation-interval-steps 6160 `
  --batch-size 16 `
  --evaluation-batch-size 256 `
  --dynamic-prefetch-workers 16 `
  --dynamic-prefetch-batches 16 `
  --dynamic-prefetch-worker-native-threads 1 `
  --dynamic-prefetch-start-method spawn `
  --pin-memory `
  --non-blocking-h2d `
  --main-process-intraop-threads 2 `
  --main-process-interop-threads 1 `
  --float32-matmul-precision high `
  --seed 20260710 `
  --evaluation-seed 20260720 `
  --development-subset-manifest data/formal_14060/manifests/v9_method_transfer_validation.csv `
  --study-contract configs/algorithm.v9.method_transfer.json `
  --evaluation-contract configs/evaluation.v9.method_transfer.json `
  --run-id split_pilot_dynamic_erm_30e__seed_20260710 `
  --device cuda `
  --output-dir outputs/v9_split_pilot_erm_30e/split_pilot_dynamic_erm_30e__seed_20260710 `
  --run-dir-exact `
  --development-only `
  --allow-tf32 `
  --cudnn-benchmark `
  --cudnn-deterministic `
  --fused-adamw `
  --amp `
  --amp-dtype bfloat16 `
  --amp-fallback-to-float32
exit $LASTEXITCODE
