#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

OUTPUT_ROOT="${PROJECT_ROOT}/outputs/v9_resnet_js_ten_run_validation_v1"
SUMMARY="${PROJECT_ROOT}/reports/v9_resnet_js_ten_run_summary.json"
DEST="${PROJECT_ROOT}/reports/v9_resnet_js_ten_run_archive_20260802"

if [[ ! -d "${OUTPUT_ROOT}" ]]; then
  echo "ERROR: ten-run output root missing: ${OUTPUT_ROOT}" >&2
  exit 1
fi
if [[ ! -f "${SUMMARY}" ]]; then
  echo "ERROR: authoritative summary missing: ${SUMMARY}" >&2
  exit 1
fi

# Never mix this archival operation with tracked source changes.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: tracked working tree is dirty; stop before archiving." >&2
  git status --short >&2
  exit 1
fi

rm -rf "${DEST}"
mkdir -p "${DEST}/runs"

python - "${OUTPUT_ROOT}" "${SUMMARY}" "${DEST}" <<'PY'
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

output_root = Path(sys.argv[1]).resolve()
summary_path = Path(sys.argv[2]).resolve()
dest = Path(sys.argv[3]).resolve()
summary = json.loads(summary_path.read_text(encoding="utf-8"))

runs = summary.get("runs", [])
if len(runs) != 10:
    raise SystemExit(f"expected 10 registered runs, found {len(runs)}")

copied = []
verified = []
for run in runs:
    run_id = str(run["run_id"])
    run_dir = output_root / run_id
    results = run_dir / "results.json"
    if not results.is_file():
        raise SystemExit(f"missing results.json: {results}")
    actual = hashlib.sha256(results.read_bytes()).hexdigest().upper()
    expected = str(run["results_sha256"]).upper()
    if actual != expected:
        raise SystemExit(
            f"results hash mismatch for {run_id}: expected {expected}, observed {actual}"
        )
    target_dir = dest / "runs" / run_id
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(results, target_dir / "results.json")
    copied.append(str((target_dir / "results.json").relative_to(dest)))
    verified.append({
        "run_id": run_id,
        "results_sha256": actual,
        "best_epoch": run.get("best_epoch"),
        "best_global_step": run.get("best_global_step"),
    })

registry = output_root / "registry.json"
if registry.is_file():
    shutil.copy2(registry, dest / "registry.json")
    copied.append("registry.json")

# Copy additional Git-safe textual evidence. Binary checkpoints, arrays, spectra,
# caches and optimizer states are never copied. Large logs are represented by hash.
allowed_suffixes = {".json", ".csv", ".tsv", ".txt", ".md", ".log", ".yaml", ".yml"}
max_copy_bytes = 20 * 1024 * 1024
additional_root = dest / "additional_text_evidence"
manifest_rows = []
for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
    rel = path.relative_to(output_root)
    size = path.stat().st_size
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_rows.append((digest, size, rel.as_posix()))
    if path.name == "results.json" or path == registry:
        continue
    if path.suffix.lower() not in allowed_suffixes:
        continue
    if size > max_copy_bytes:
        continue
    target = additional_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    copied.append(str(target.relative_to(dest)))

manifest_path = dest / "local_output_file_manifest.tsv"
manifest_path.write_text(
    "sha256\tsize_bytes\trelative_path\n"
    + "".join(f"{digest}\t{size}\t{rel}\n" for digest, size, rel in manifest_rows),
    encoding="utf-8",
)

verification = {
    "schema_version": "v9-ten-run-git-safe-archive-v1",
    "status": "verified_complete_results_archive",
    "source_output_root": str(output_root),
    "run_count": 10,
    "verified_results": verified,
    "copied_files": sorted(copied),
    "binary_policy": (
        "Checkpoint binaries, optimizer states, generated spectra, caches and raw arrays "
        "remain local; every local file is represented in local_output_file_manifest.tsv."
    ),
    "simulated_test_accessed": False,
}
(dest / "archive_verification.json").write_text(
    json.dumps(verification, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

(dest / "README.md").write_text(
    "# V9 ten-run Git-safe evidence archive\n\n"
    "This directory archives the ten original per-run `results.json` files and all "
    "small textual evidence found under the completed Validation output root. Each "
    "`results.json` was verified against the SHA-256 registered in the authoritative "
    "ten-run summary before copying.\n\n"
    "`local_output_file_manifest.tsv` records SHA-256 and byte size for every local "
    "output file, including excluded binary artifacts. Checkpoint binaries, optimizer "
    "states, generated spectra, caches and raw arrays are intentionally not committed.\n\n"
    "This archive contains Validation evidence only and does not contain simulated-Test "
    "predictions or metrics.\n",
    encoding="utf-8",
)
PY

# Make the archive self-verifying.
(
  cd "${DEST}"
  find . -type f ! -name 'archive_files.sha256' -print0 \
    | sort -z \
    | xargs -0 sha256sum > archive_files.sha256
)

# Force-add only the explicitly created Git-safe archive, even if outputs are ignored.
git add -f "${DEST}"

if git diff --cached --quiet; then
  echo "Archive already matches Git; nothing to commit."
  exit 0
fi

git commit -m "Archive complete V9 ten-run Git-safe evidence"
git push origin HEAD:main

echo "TEN_RUN_ARCHIVE_PUSHED"
echo "Archive: ${DEST}"
