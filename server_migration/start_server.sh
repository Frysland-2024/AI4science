#!/usr/bin/env bash
# One command on a rented Linux GPU server after 4 private ZIPs have been copied into KIT.
# Usage: bash start_server.sh --plan | --run [extra one_click_v11.py options]
set -euo pipefail
MODE="plan"
if [ "$#" -gt 0 ]; then MODE="$1"; shift; fi
if [ "$MODE" != "--plan" ] && [ "$MODE" != "--run" ]; then echo "Usage: bash start_server.sh --plan | --run [--trials N ...]"; exit 2; fi
KIT="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/research"
mkdir -p "$DEST"
cd "$KIT"
for f in source_snapshot.zip structure_shards.zip peak_cache_bundle.zip a0_reference_checkpoint.zip; do
  test -s "$f" || { echo "BLOCKED: missing $f"; exit 3; }
done
sha256sum -c SHA256SUMS.txt
test -f "$DEST/AI4science/server_migration/one_click_v11.py" || unzip -q source_snapshot.zip -d "$DEST"
test -f "$DEST/AI4science/structure_library/merged_154975_parent_split_20261103/delivery_validation.json" || unzip -q structure_shards.zip -d "$DEST"
test -f "$DEST/AI4science/xrd_robustness/data/merged_154975_v11/training_records.v1.jsonl" || unzip -q peak_cache_bundle.zip -d "$DEST"
test -f "$DEST/AI4science/reference_a0_r1_v10/best.ckpt" || unzip -q a0_reference_checkpoint.zip -d "$DEST"
cd "$DEST/AI4science"
PYTHON=python3
"$PYTHON" server_migration/verify_payload.py --root . --check-records
"$PYTHON" server_migration/verify_peak_cache.py --root . --fast
if [ "$MODE" = "--plan" ]; then
  "$PYTHON" server_migration/one_click_v11.py --mode plan "$@"
  echo "PLAN PASS: run 'bash start_server.sh --run' on the configured GPU server after reviewing resource budget."
  exit 0
fi
bash server_migration/setup_linux.sh
"$PYTHON" server_migration/one_click_v11.py --mode smoke
"$PYTHON" server_migration/one_click_v11.py --mode run "$@"
echo "ONE-CLICK V11 PIPELINE COMPLETE; results under AI4science/server_runs/v11_a0_js_optuna/"
