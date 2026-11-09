# Issue #61 — V11 minimum preflight audit (2026-11-09)

## Decision

**#61 = BLOCKED; #55 = BLOCKED BY #61.** This audit is limited to GitHub-visible source and historical receipts. It does not access the offline private D:/E: artifacts or a rented server. No GPU smoke, HPO, formal training, or RRUFF scoring was run or authorized here.

The 2026-11-09 #61 audit comment is the current blocker record: the schema adapter and training-manifest builder described on the closed, unmerged #66 branch are absent from current `main`; current `precompute_peak_tables.py` does not expose the documented `--records-path` input; the laptop/private artifacts could not be reopened for current hash verification. Thus the local receipts below remain dated evidence, not current-main or server acceptance.

## Evidence already present (historical or scoped)

- `docs/STRUCTURE_LIBRARY_154975_SPLIT_EVIDENCE.md` records 154,975 MP-ID rows, 154,968 canonical parent groups, and parent-disjoint 70/15/15 splits: 108,478 Train / 23,245 Validation / 23,245 synthetic Test parents. It records source-shard hashes and a passed source delivery validation. This proves the documented source split only.
- Issue #61's earlier local migration comments record private archive/hash checks, schema/cache construction, full PeakTable inventory, and laptop CPU/CUDA engineering smokes. They are historical laptop receipts tied to earlier code/package snapshots, not current-server acceptance.
- PR #70 is merged and its CI passed. It establishes integration and offline code checks for the current migration runner; it does not establish that private payloads match current `main`, nor that the runner has passed on the target Linux GPU.
- The 131,729-row Train+Validation manifest and laptop throughput/resume receipts are useful engineering evidence. They are not trained-model performance results and do not unlock #55.

## Required recheck on current `main`

1. **Freeze source identity:** record current `main` commit SHA, Python/dependency versions, and the exact migration code revision used to generate/consume the kit.
2. **Close the adapter/CLI gap:** selectively port or implement the structure-schema adapter and Train+Validation manifest builder on current `main`; provide an explicit records-path interface for PeakTable precompute. Add CPU regression coverage for the actual private schema and fail-closed input/schema errors. Do not use the stale #66 branch wholesale.
3. **Bind package to source:** using the existing private package, verify `source_snapshot`, structure shards, PeakTable bundle, optional Validation panel bundle, `SHA256SUMS`, payload contract/version and member hashes against that exact source SHA. Regenerate only source/package metadata that is genuinely stale; do not redownload structures or rebuild caches already proven byte-identical.
4. **Validate data contract:** verify source IDs and fingerprints, split membership and parent isolation, row/group counts, PeakTable schema and loader round trip, per-file SHA/size/count, skipped-record count, and exact Train+Validation manifest membership. Confirm Test is excluded from every training/selection manifest.
5. **Run current-main CPU-only checks:** execute the Linux `--plan` and bounded offline CPU smoke in a clean environment after steps 2–4; capture commands, environment, logs and input/output hashes. This must exercise V11 rendering → paired views → ResNet-A0 → CE + same-parent JS, not just imports or generic fixtures.
6. **Publish the receipt:** include main SHA, package hashes, schema/loader result, split/isolation result, CPU logs and a pass/fail/not-run table. Until separately authorized target-GPU smoke is actually run, record GPU smoke exactly as **`BLOCKED / NOT_RUN`**.

## Explicitly not complete / must not be claimed

- No current-main ↔ private-package version/hash match has been demonstrated.
- No current-main execution of the missing adapter/manifest path or `--records-path` precompute has been demonstrated.
- Historical “154,975/154,975 PeakTables” and local CUDA/throughput/resume receipts do not prove the server can read or reproduce those artifacts today.
- No target Linux server environment, CUDA compatibility, full-size I/O, GPU smoke, memory/throughput, resume, or full Validation accessibility acceptance is evidenced.
- GPU smoke is **`BLOCKED / NOT_RUN`** without separate authorization. Do not say “GPU preflight passed.”
- Do not mark #61 `READY`, close it, unblock #55, rent/launch a GPU, start HPO or formal training, or score RRUFF-Cu1011 on the basis of this documentation/PR.

## Shortest path to a defensible `READY`

Complete steps 1–5 above on current `main`, resolve all CPU/data/package failures, and publish the reproducible receipt. Then obtain separate authorization for the bounded GPU smoke described by #61 and execute only that scope. #61 can become `READY` only after that GPU evidence and every blocking item is closed; #55 remains blocked until then. GPU smoke authorization is not HPO or formal-training authorization.

## Source records

- [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61), including the 2026-11-09 readiness audit comment.
- [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).
- [PR #70](https://github.com/Frysland-2024/AI4science/pull/70) and [PR #66](https://github.com/Frysland-2024/AI4science/pull/66).
- [Current state](CURRENT_STATE.md), [migration README](../server_migration/README.md), and [source split evidence](STRUCTURE_LIBRARY_154975_SPLIT_EVIDENCE.md).
