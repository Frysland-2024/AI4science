#!/usr/bin/env python3
"""Verify every file in a prepared V9 desktop migration manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "reports" / "v9_desktop_migration_manifest.json"),
    )
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_desktop_migration_verification.json"),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _stream_hash(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            f"{row['path']}\0{row['size_bytes']}\0{row['sha256']}\n".encode("utf-8")
        )
    return digest.hexdigest().upper()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    csv_path = root / str(manifest["file_manifest"]["path"])
    csv_hash_matches = csv_path.is_file() and _sha256(csv_path) == str(
        manifest["file_manifest"]["sha256"]
    )
    rows: list[dict[str, Any]] = []
    if csv_path.is_file():
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "path": str(row["path"]),
                        "size_bytes": int(row["size_bytes"]),
                        "sha256": str(row["sha256"]),
                    }
                )

    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[dict[str, str]] = []
    for row in rows:
        path = root / row["path"]
        if not path.is_file():
            missing.append(row["path"])
            continue
        observed_size = path.stat().st_size
        if observed_size != row["size_bytes"]:
            size_mismatches.append(
                {
                    "path": row["path"],
                    "expected": row["size_bytes"],
                    "observed": observed_size,
                }
            )
            continue
        observed_hash = _sha256(path)
        if observed_hash != row["sha256"]:
            hash_mismatches.append(
                {"path": row["path"], "expected": row["sha256"], "observed": observed_hash}
            )

    gates = {
        "file_manifest_csv_hash_matches": csv_hash_matches,
        "file_manifest_row_count_matches": len(rows)
        == int(manifest["file_manifest"]["row_count"]),
        "payload_stream_hash_matches": _stream_hash(rows)
        == str(manifest["file_manifest"]["payload_stream_sha256"]),
        "no_missing_files": not missing,
        "no_size_mismatches": not size_mismatches,
        "no_hash_mismatches": not hash_mismatches,
    }
    status = "pass" if all(gates.values()) else "fail"
    report = {
        "schema_version": "v9-desktop-migration-verification-v1",
        "status": status,
        "manifest": str(manifest_path),
        "source_hostname": manifest["source"]["hostname"],
        "verification_hostname": platform.node(),
        "verification_is_on_source_host": (
            str(manifest["source"]["hostname"]).casefold() == platform.node().casefold()
        ),
        "verified_root": str(root),
        "verified_file_count": len(rows),
        "verified_payload_size_bytes": sum(row["size_bytes"] for row in rows),
        "gates": gates,
        "missing_files": missing[:100],
        "size_mismatches": size_mismatches[:100],
        "hash_mismatches": hash_mismatches[:100],
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "verified_files": len(rows),
                "missing": len(missing),
                "size_mismatches": len(size_mismatches),
                "hash_mismatches": len(hash_mismatches),
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
