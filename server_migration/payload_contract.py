"""Versioned member contract for the private V11 Linux migration snapshot."""

PAYLOAD_CONTRACT_VERSION = "v11-focused-science-cpu-20261109.9"
PAYLOAD_MANIFEST_MEMBER = "AI4science/server_migration/source_snapshot_manifest.json"

PAYLOAD_REQUIRED_FILES = (
    "AI4science/server_migration/one_click_v11.py",
    "AI4science/server_migration/v11_prefetch.py",
    "AI4science/server_migration/smoke_prefetch.py",
    "AI4science/server_migration/start_server.sh",
    "AI4science/server_migration/start_windows.ps1",
    "AI4science/server_migration/windows_cuda_smoke.py",
    "AI4science/server_migration/hpo_handoff.py",
    "AI4science/server_migration/train_microbatch.py",
    "AI4science/server_migration/benchmark_windows_v11.py",
    "AI4science/server_migration/tests/test_epoch_microbatch.py",
    "AI4science/server_migration/verify_payload.py",
    "AI4science/server_migration/verify_peak_cache.py",
    "AI4science/server_migration/verify_source_snapshot.py",
    "AI4science/server_migration/payload_contract.py",
    "AI4science/server_migration/tests/test_full_validation_selection.py",
    "AI4science/server_migration/tests/test_v11_prefetch_pipeline.py",
    "AI4science/server_migration/tests/test_launcher_contract.py",
    "AI4science/server_migration/tests/test_source_snapshot.py",
    "AI4science/server_migration/tests/test_hpo_handoff.py",
    "AI4science/xrd_robustness/scripts/precompute_peak_tables.py",
    "AI4science/xrd_robustness/scripts/build_merged_library_training_manifest.py",
    "AI4science/xrd_robustness/tests/core/test_merged_library_preflight.py",
)
