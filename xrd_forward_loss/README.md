# PXRD Forward Reconstruction Loss Pilot

An isolated, reproducible A/B pilot for two continuous lattice coordinates on one known tetragonal parent. Method A uses supervised parameter MSE. Method B uses the same ResNet-18-GN and training protocol plus a differentiable transformed-profile reconstruction term.

The parent is read only from the original training fold. The train, validation, and test partitions then contain disjoint parameter draws and independently generated measurement perturbations for that one fixed known structure. This evaluates parameter inversion conditional on a known candidate structure; it does not evaluate unseen-structure generalization or establish evidence for ferroelectric ceramics.

## Run

Use the repository's CUDA-enabled environment and set the package paths:

```powershell
$env:PYTHONPATH = "xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src"
& .\.venvs\xrd_test\Scripts\python.exe xrd_forward_loss\scripts\run_pilot.py
```

The default run first checks the gradient and identifiability gate, runs one-epoch A/B smoke fits, selects `lambda` on validation data only, and trains three matched seeds. Results and plots are written to `xrd_forward_loss/reports/pilot_20261018/`.

Unit tests:

```powershell
$env:PYTHONPATH = "xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src"
& .\.venvs\xrd_test\Scripts\python.exe -m pytest xrd_forward_loss\tests
```

No frozen data, selected checkpoint, V9 JS study, archived NO-GO, or independent renderer holdout is edited or opened.
