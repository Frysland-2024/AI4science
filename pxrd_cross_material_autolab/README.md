# Cross-material PXRD AutoLab

This isolated synthetic known-CIF pilot compares one supervised neural start plus bounded physical refinement with single-start and three-start physics-only inversion. Per-material training is workflow portability, not zero-shot transfer. See [preregistration](PREREGISTRATION.md), [source audit](source_audit.json), [materials](materials.json), and the final [overview](reports/OVERVIEW.md).

Run from repository root with Python containing numpy, scipy, torch, pymatgen, matplotlib and pytest. The executed environment was `C:/Users/Lenovo/.codex/venvs/issue19-measurement-closure/Scripts/python.exe`. No installation or changes to that shared environment were necessary.

```powershell
$autolabPython = 'C:/Users/Lenovo/.codex/venvs/issue19-measurement-closure/Scripts/python.exe'
& $autolabPython -m pytest pxrd_cross_material_autolab -q -p no:cacheprovider
& $autolabPython -m pxrd_cross_material_autolab inventory
& $autolabPython -m pxrd_cross_material_autolab preflight
& $autolabPython -m pxrd_cross_material_autolab dry-run --resume
& $autolabPython -m pxrd_cross_material_autolab run --resume
& $autolabPython -m pxrd_cross_material_autolab status
& $autolabPython -m pxrd_cross_material_autolab verify
& $autolabPython -m pxrd_cross_material_autolab report
```

For a fresh reproduction use `--root pxrd_cross_material_autolab/runs/replication_<date>` consistently. Do not change or reuse the original held-out run as a tuning loop. Its immutable manifest is bound to the original absolute source location, config and CIF byte hashes. A relocated checkout uses a fresh run root; the original report remains historical evidence. Check Git line-ending conversion against recorded raw CIF hashes; `materials.json` documents BaTiO3 LF/CRLF equivalence, but the runner deliberately rejects unexpected raw-byte differences.

Completed materials are idempotently skipped on resume. Failed historical attempts are retained and never automatically retried. An interrupted experiment is BLOCKED from automatic test reopening, even if it ended before the test marker; inspect its state before any separately registered attempt. A stale `manager.lock` requires verifying its PID is dead before manual removal. This conservative control favors preservation over automatic recovery of ambiguous stages.

The manager checks all physical gates before entering research training and aborts on independent renderer parity failure. Every successful attempt includes split/selection hashes, train/validation curves, full fit attempts in JSONL, compact CSV, metrics, timing, final weights/data hashes, a plot and artifact checksums. `verify` recomputes summary metrics from saved predictions and checks hashes. Generated spectra/weights under `private/` are ignored; only compact evidence is committed.

`PASS` for an experiment means the registered procedure completed, not a neural scientific win. A skipped unsupported candidate remains visible; the root manager conservatively returns `BLOCKED` when any requested candidate was skipped. Delivery reports distinguish this machine state from a completed supported subset (`PARTIAL`). No hidden gate relaxation or test-driven rescue is permitted.

The primary P3 budget is three optimizations versus one for P0/N+A. The equal-evaluation sensitivity uses a total ceiling of600 (200 for each P3 start) and reports actual counts, including SciPy finite-difference overshoot. This does not claim matched wall time. Training is reported separately and cannot be hidden in inference-only Pareto conclusions.
