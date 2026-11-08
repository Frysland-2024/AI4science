#!/usr/bin/env bash
# Read-only Linux preflight: never triggers GPU training or precompute.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON=python3
"$PYTHON" --version
"$PYTHON" server_migration/verify_payload.py --root "$ROOT" --check-records
if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; else echo "WARNING nvidia-smi unavailable"; fi
"$PYTHON" - <<'PY'
import importlib,sys
print("PYTHON",sys.version.split()[0])
for name in ("numpy","scipy","pymatgen","spglib","pytest","torch"):
    try:
        mod=importlib.import_module(name)
        print("PACKAGE",name,getattr(mod,"__version__","installed"))
        if name=="torch":print("TORCH_CUDA",mod.cuda.is_available(),"BUILD",mod.version.cuda)
    except Exception as exc:print("BLOCKED_PACKAGE",name,type(exc).__name__,str(exc)[:160])
PY
echo "Preflight finished: inspect BLOCKED warnings before starting full precompute."
