from __future__ import annotations

import os
from pathlib import Path
import sys


os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "xrd_inversion" / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "xrd_robustness" / "src"))

from xrd_inversion.factorization_pilot import main  # noqa: E402


if __name__ == "__main__":
    main()
