#!/usr/bin/env bash
# Explicit action ONLY. Train/validation reflection cache; no RRUFF or final training.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON=python3
WORKERS=3
BATCH_SIZE=100
LIB="$ROOT/structure_library/merged_154975_parent_split_20261103"
CACHE="$ROOT/xrd_robustness/data/merged_154975_v11"
"$PYTHON" server_migration/verify_payload.py --root "$ROOT"
for SPLIT in train validation; do
  TARGET="$CACHE/$SPLIT"
  SUMMARY="$TARGET/manifests/peak_cache_summary.v7.reflection.json"
  if [ -f "$SUMMARY" ]; then
    "$PYTHON" - "$SUMMARY" "$SPLIT" <<'PY'
import json,sys
j=json.load(open(sys.argv[1],encoding="utf-8"))
expected={"train":108483,"validation":23246}[sys.argv[2]]
if j.get("status")!="completed" or j.get("completed_count")!=expected or j.get("skipped_count")!=0:
    raise SystemExit("Existing cache is not valid: "+sys.argv[1])
print("VERIFIED COMPLETED CACHE",sys.argv[2],expected)
PY
    continue
  fi
  if [ -d "$TARGET/mp_processed/peak_tables_v7_reflection.tmp" ]; then
    "$PYTHON" xrd_robustness/scripts/precompute_peak_tables.py --data-root "data/merged_154975_v11/$SPLIT" --records-path "$LIB/$SPLIT""_structures.jsonl.gz" --workers "$WORKERS" --batch-size "$BATCH_SIZE" --force-local --resume-staging
  else
    "$PYTHON" xrd_robustness/scripts/precompute_peak_tables.py --data-root "data/merged_154975_v11/$SPLIT" --records-path "$LIB/$SPLIT""_structures.jsonl.gz" --workers "$WORKERS" --batch-size "$BATCH_SIZE" --force-local
  fi
done
"$PYTHON" xrd_robustness/scripts/build_merged_library_training_manifest.py --source-dir "$LIB" --cache-root "data/merged_154975_v11"
echo "Train+Validation cache built; TEST untouched. No final training was started."
