"""Build or verify a hash inventory for publishable Issue #44 artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDED_DIRS = {"private", "__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pt", ".pth", ".ckpt", ".npz", ".npy", ".pyc", ".pyo", ".onnx", ".safetensors"}
RUN = ROOT / "runs" / "benchmark_20261020"
OUTPUT = RUN / "artifact_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exclusion_reason(path: Path) -> str | None:
    if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
        return "private_or_cache_directory"
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return "weights_or_generated_arrays"
    return None


def build_manifest() -> dict:
    status = json.loads((RUN / "status.json").read_text(encoding="utf-8"))
    comparison = json.loads((RUN / "comparison.json").read_text(encoding="utf-8"))
    included = []
    excluded_files = Counter()
    excluded_bytes = Counter()
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        if path == OUTPUT:
            continue
        reason = exclusion_reason(path)
        if reason:
            excluded_files[reason] += 1
            excluded_bytes[reason] += path.stat().st_size
            continue
        included.append({
            "path": path.relative_to(ROOT.parent).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    audit = comparison["primary_record_audit"]
    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "publishable Issue #44 code, preregistration, machine-readable synthetic run records, and audit reports",
        "status": {
            "overall": status["status"],
            "synthetic_primary": status["synthetic_status"],
            "stress": status["stress_status"],
            "real_rruff": status["real_rruff"],
            "publication": status.get("publication", "PENDING"),
        },
        "primary_record_audit": audit,
        "train_validation_test_parents": {"train": 358, "validation": 77, "test": 77, "test_reused_from_pr43": True},
        "excluded_artifacts": {
            "directories": sorted(EXCLUDED_DIRS),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
            "file_counts_by_reason": dict(sorted(excluded_files.items())),
            "bytes_by_reason": dict(sorted(excluded_bytes.items())),
            "manifest_excludes_its_own_hash": True,
            "raw_rruff_data_or_locked_classification_test": "not present in this artifact root",
        },
        "included_file_count": len(included),
        "included_bytes": sum(entry["bytes"] for entry in included),
        "files": included,
    }


def verify_manifest(path: Path) -> None:
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = build_manifest()
    for field in ("scope", "status", "primary_record_audit", "train_validation_test_parents",
                  "excluded_artifacts", "included_file_count", "included_bytes", "files"):
        if expected.get(field) != actual.get(field):
            raise SystemExit(f"artifact manifest mismatch: {field}")
    print(json.dumps({"status": "PASS", "included_file_count": actual["included_file_count"],
                      "included_bytes": actual["included_bytes"], "manifest": str(path.relative_to(ROOT.parent))}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify every listed file hash and file-set membership")
    args = parser.parse_args()
    if args.verify:
        verify_manifest(OUTPUT)
    else:
        manifest = build_manifest()
        OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "WRITTEN", "included_file_count": manifest["included_file_count"],
                          "included_bytes": manifest["included_bytes"], "manifest": str(OUTPUT.relative_to(ROOT.parent))}))


if __name__ == "__main__":
    main()
