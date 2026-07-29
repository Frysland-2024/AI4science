#!/usr/bin/env bash
set -Eeuo pipefail

PRECHECK_ONLY=0
if [[ "${1:-}" == "--preflight-only" ]]; then
  PRECHECK_ONLY=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--preflight-only]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python}"
CONTRACT="${PROJECT_ROOT}/configs/v9_resnet_js_ten_run.preregistered.json"
AUTHORIZATION="${PROJECT_ROOT}/configs/v9_resnet_js_ten_run.authorization.json"
OUTPUT_ROOT="${PROJECT_ROOT}/outputs/v9_resnet_js_ten_run_validation_v1"
SUMMARY_SCRIPT="${PROJECT_ROOT}/scripts/summarize_v9_resnet_js_ten_run.py"
REGISTRY="${OUTPUT_ROOT}/registry.json"
TARGET_STEPS=61600
SINGLE_FACTOR_PROFILES="ood_shift_negative,ood_shift_positive,ood_broadening,ood_noise,ood_background,ood_texture"
DYNAMIC_WORKERS="${DYNAMIC_WORKERS:-8}"
PREFETCH_BATCHES="${PREFETCH_BATCHES:-8}"

required_paths=(
  "${CONTRACT}"
  "${AUTHORIZATION}"
  "${SUMMARY_SCRIPT}"
  "${PROJECT_ROOT}/scripts/train_cnn_contract_diagnostic.py"
  "${PROJECT_ROOT}/configs/simulation.v9.method_transfer.frozen.json"
  "${PROJECT_ROOT}/configs/evaluation.v9.method_transfer.json"
  "${PROJECT_ROOT}/data/formal_14060/mp_processed/structure_records.jsonl"
  "${PROJECT_ROOT}/data/formal_14060/manifests/split_manifest.json"
  "${PROJECT_ROOT}/data/formal_14060/manifests/v9_method_transfer_validation.csv"
  "${PROJECT_ROOT}/data/formal_14060/mp_processed/peak_tables_v7_reflection"
)
for path in "${required_paths[@]}"; do
  if [[ ! -e "${path}" ]]; then
    echo "PRECHECK_FAIL missing required path: ${path}" >&2
    exit 1
  fi
done

"${PYTHON_BIN}" - "${CONTRACT}" "${AUTHORIZATION}" "${PROJECT_ROOT}" <<'PY'
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

contract_path = Path(sys.argv[1])
authorization_path = Path(sys.argv[2])
project_root = Path(sys.argv[3])
contract = json.loads(contract_path.read_text(encoding="utf-8"))
authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()

if authorization.get("status") != "authorized_for_serial_validation_replication":
    raise SystemExit("authorization status is not active")
if authorization["preregistered_contract"]["sha256"].upper() != contract_hash:
    raise SystemExit("authorization does not match the preregistered contract hash")
if contract.get("status") != "preregistered_locked_not_authorized":
    raise SystemExit("preregistration must remain immutable and fail-closed")
if contract["execution"].get("ten_run_enabled") is not False:
    raise SystemExit("preregistration must not self-authorize execution")
if len(contract.get("runs", [])) != 10:
    raise SystemExit("contract must contain exactly 10 runs")
if contract["data_boundaries"].get("simulated_test_allowed") is not False:
    raise SystemExit("simulated Test must remain locked")
if contract["data_boundaries"].get("real_xrd_allowed") is not False:
    raise SystemExit("real XRD must remain locked")
if contract["data_boundaries"].get("development_only_required") is not True:
    raise SystemExit("development-only boundary is required")

runs = contract["runs"]
erm = [r for r in runs if r["method"] == "ordinary_dynamic_augmentation"]
js = [r for r in runs if r["method"] == "js_consistency_transfer"]
if len(erm) != 5 or len(js) != 5:
    raise SystemExit("contract must contain five ERM and five JS runs")
if {r["training_seed"] for r in erm} != {r["training_seed"] for r in js}:
    raise SystemExit("paired training seeds do not match")
if any(float(r["lambda_js"]) != 0.0 for r in erm):
    raise SystemExit("ERM lambda must be zero")
if any(float(r["lambda_js"]) != 60.0 for r in js):
    raise SystemExit("JS lambda must remain frozen at 60")
if 20260710 in {r["training_seed"] for r in runs}:
    raise SystemExit("the tuning seed must be excluded from replication")

for item in contract.get("registered_inputs", {}).values():
    path = project_root / str(item["path"])
    if not path.is_file():
        raise SystemExit(f"registered input missing: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if actual != str(item["sha256"]).upper():
        raise SystemExit(f"registered input hash mismatch: {path}")

try:
    import numpy  # noqa: F401
    import torch
except Exception as error:
    raise SystemExit(f"Python dependency precheck failed: {error}") from error
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available")
print(f"TEN_RUN_PREFLIGHT_PASS contract_sha256={contract_hash}")
print(f"CUDA_DEVICE={torch.cuda.get_device_name(0)}")
PY

if pgrep -af 'train_(v7|cnn_contract_diagnostic)\.py' >/dev/null 2>&1; then
  echo "PRECHECK_FAIL another training process is active:" >&2
  pgrep -af 'train_(v7|cnn_contract_diagnostic)\.py' >&2 || true
  exit 1
fi

if [[ "${PRECHECK_ONLY}" -eq 1 ]]; then
  exit 0
fi

export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export VECLIB_MAXIMUM_THREADS=2
export BLIS_NUM_THREADS=2
export CUDA_MODULE_LOADING=LAZY
export PYTHONUNBUFFERED=1

mkdir -p "${OUTPUT_ROOT}"
if [[ ! -f "${REGISTRY}" ]]; then
  "${PYTHON_BIN}" - "${CONTRACT}" "${REGISTRY}" <<'PY'
import json
import sys
from pathlib import Path
contract = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload = {
    "schema_version": "v9-resnet-js-ten-run-registry-v1",
    "execution": "serial",
    "status": "running",
    "runs": [
        {
            "run_id": run["run_id"],
            "pair_id": run["pair_id"],
            "training_seed": run["training_seed"],
            "evaluation_seed": run["evaluation_seed"],
            "method": run["method"],
            "lambda_js": run["lambda_js"],
            "status": "pending",
        }
        for run in contract["runs"]
    ],
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
fi

mapfile -t RUN_ROWS < <(
  "${PYTHON_BIN}" - "${CONTRACT}" <<'PY'
import json
import sys
from pathlib import Path
contract = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for run in contract["runs"]:
    print("\t".join([
        str(run["run_id"]),
        str(run["method"]),
        str(run["lambda_js"]),
        str(run["training_seed"]),
        str(run["evaluation_seed"]),
    ]))
PY
)

update_registry() {
  local run_id="$1"
  local status="$2"
  local exit_code="${3:-}"
  "${PYTHON_BIN}" - "${REGISTRY}" "${run_id}" "${status}" "${exit_code}" <<'PY'
import datetime as dt
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
run_id, status, exit_code = sys.argv[2], sys.argv[3], sys.argv[4]
payload = json.loads(path.read_text(encoding="utf-8"))
matched = False
for row in payload["runs"]:
    if row["run_id"] == run_id:
        row["status"] = status
        matched = True
        if status == "running":
            row["started_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        if status in {"completed", "failed"}:
            row["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            row["exit_code"] = int(exit_code)
        break
if not matched:
    raise SystemExit(f"run not registered: {run_id}")
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

for row in "${RUN_ROWS[@]}"; do
  IFS=$'\t' read -r run_id method lambda_js training_seed evaluation_seed <<<"${row}"
  run_dir="${OUTPUT_ROOT}/${run_id}"
  results_path="${run_dir}/results.json"
  last_checkpoint="${run_dir}/last.ckpt"

  if [[ -f "${results_path}" ]]; then
    echo "=== Already completed; skipping ${run_id} ==="
    update_registry "${run_id}" "completed" "0"
    continue
  fi

  mode=""
  if [[ "${method}" == "ordinary_dynamic_augmentation" ]]; then
    mode="dynamic_erm"
  elif [[ "${method}" == "js_consistency_transfer" ]]; then
    mode="dynamic_js"
  else
    echo "Unsupported method in contract: ${method}" >&2
    exit 1
  fi

  resume_args=()
  if [[ -d "${run_dir}" ]]; then
    if [[ -f "${last_checkpoint}" ]]; then
      echo "=== Resuming ${run_id} from ${last_checkpoint} ==="
      resume_args=(--resume "${last_checkpoint}")
    else
      echo "Incomplete run directory lacks last.ckpt: ${run_dir}" >&2
      exit 1
    fi
  else
    mkdir -p "${run_dir}"
  fi

  update_registry "${run_id}" "running"
  echo "=== Starting ${run_id} (${mode}, seed=${training_seed}, lambda_js=${lambda_js}) ==="

  set +e
  "${PYTHON_BIN}" -s scripts/train_cnn_contract_diagnostic.py \
    --mode "${mode}" \
    --simulation-config configs/simulation.v9.method_transfer.frozen.json \
    --train-profile train \
    --in-range-profile in_range \
    --ood-profiles level0,ood_shift_negative,ood_shift_positive,ood_broadening,ood_noise,ood_background,ood_texture,ood_combo_shift_broadening,ood_combo_background_noise,ood_combo_texture_shift,ood_all \
    --variant b3 \
    --dataset-size 14060 \
    --data-root data/formal_14060 \
    --split-manifest data/formal_14060/manifests/split_manifest.json \
    --peak-cache-name peak_tables_v7_reflection \
    --epochs 100 \
    --max-optimizer-steps "${TARGET_STEPS}" \
    --validation-interval-steps 6160 \
    --early-stopping \
    --early-stopping-min-epochs 50 \
    --early-stopping-patience 3 \
    --early-stopping-min-delta 0.002 \
    --early-stopping-ood-profiles "${SINGLE_FACTOR_PROFILES}" \
    --batch-size 16 \
    --evaluation-batch-size 256 \
    --dynamic-prefetch-workers "${DYNAMIC_WORKERS}" \
    --dynamic-prefetch-batches "${PREFETCH_BATCHES}" \
    --dynamic-prefetch-worker-native-threads 1 \
    --dynamic-prefetch-start-method spawn \
    --pin-memory \
    --non-blocking-h2d \
    --main-process-intraop-threads 2 \
    --main-process-interop-threads 1 \
    --float32-matmul-precision high \
    --seed "${training_seed}" \
    --evaluation-seed "${evaluation_seed}" \
    --development-subset-manifest data/formal_14060/manifests/v9_method_transfer_validation.csv \
    --study-contract configs/v9_resnet_js_ten_run.preregistered.json \
    --evaluation-contract configs/evaluation.v9.method_transfer.json \
    --run-id "${run_id}" \
    --learning-rate 0.0001 \
    --weight-decay 0.0001 \
    --lambda-js "${lambda_js}" \
    --device cuda \
    --output-dir "${run_dir}" \
    --run-dir-exact \
    --development-only \
    --allow-tf32 \
    --cudnn-benchmark \
    --cudnn-deterministic \
    --fused-adamw \
    --amp \
    --amp-dtype bfloat16 \
    --amp-fallback-to-float32 \
    --cnn-preprocessing identity \
    --cnn-optimizer adamw \
    --cnn-lr-schedule constant \
    --cnn-lr-warmup-steps 0 \
    --cnn-total-steps "${TARGET_STEPS}" \
    --cnn-preregistration "${CONTRACT}" \
    "${resume_args[@]}" \
    2>&1 | tee -a "${run_dir}/launcher.log"
  exit_code=${PIPESTATUS[0]}
  set -e

  if [[ "${exit_code}" -ne 0 ]]; then
    update_registry "${run_id}" "failed" "${exit_code}"
    echo "Run ${run_id} failed with exit code ${exit_code}" >&2
    exit "${exit_code}"
  fi
  update_registry "${run_id}" "completed" "0"
done

"${PYTHON_BIN}" -s "${SUMMARY_SCRIPT}" --output-root "${OUTPUT_ROOT}"
summary_exit=$?
if [[ "${summary_exit}" -ne 0 ]]; then
  echo "Ten-run summarization failed with exit code ${summary_exit}" >&2
  exit "${summary_exit}"
fi

"${PYTHON_BIN}" - "${REGISTRY}" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["status"] = "completed"
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

echo "=== Ten-run Validation replication completed and summarized ==="
