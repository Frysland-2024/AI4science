#!/usr/bin/env python3
"""Check Materials Project API credentials and connectivity without writing data."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from mp_api.client import MPRester


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.mp_credentials import configured_api_key


def main() -> int:
    api_key = configured_api_key()
    if not api_key:
        raise SystemExit("MP_API_KEY or PMG_MAPI_KEY is not configured")
    with MPRester(api_key) as mpr:
        documents = mpr.materials.summary.search(
            material_ids=["mp-149"],
            fields=["material_id", "formula_pretty", "symmetry"],
            chunk_size=1,
            num_chunks=1,
        )
    if len(documents) != 1:
        raise RuntimeError("Materials Project did not return the mp-149 smoke record")
    document = documents[0]
    print(
        json.dumps(
            {
                "passed": True,
                "material_id": str(document.material_id),
                "formula": document.formula_pretty,
                "space_group": int(document.symmetry.number),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
