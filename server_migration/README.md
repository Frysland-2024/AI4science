# V11 server migration — current execution status (2026-11-09)

> **STOP: #61 is BLOCKED and #55 is BLOCKED BY #61. Do not run `start_server.sh --run`, rent/start a GPU, launch HPO, or begin formal training.** The historical package and local laptop receipts have not been rebound to the current `main` source and private package hashes. GPU smoke is **BLOCKED / NOT_RUN** without separate authorization.

## Current authoritative gate

See [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61), [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55), and the [minimum preflight audit](../docs/ISSUE_61_V11_MINIMUM_PREFLIGHT_AUDIT_20261109.md).

PR #70 is merged and its CI passed. This verifies code integration/offline checks; it is not a private-payload or Linux-GPU acceptance. The latest #61 audit records two unresolved current-main gaps: the schema adapter/Train+Validation manifest-builder from unmerged PR #66 is absent, and current `precompute_peak_tables.py` lacks the documented `--records-path` interface. Historical local cache/package/CUDA receipts do not close these gaps.

## Evidence labels

- **Source split documented:** 154,975 MP-ID rows, 154,968 parent groups, with 108,478 Train / 23,245 Validation / 23,245 synthetic Test parent groups. This is source-split evidence, not server loader acceptance.
- **Historical private-package receipts:** prior local checks reported full PeakTable construction and hash/integrity checks. Their current bytes and code-version binding are not reverified.
- **Current-main CI:** passed for PR #70. It does not run against the user's private data bundle or a rented server.
- **Target GPU:** `BLOCKED / NOT_RUN`. No GPU smoke is claimed.
- **HPO/formal training/RRUFF score:** not run and not authorized by #61 or #55 documentation.

## Minimum CPU/data preflight before any GPU request

1. Record exact current `main` SHA and software versions.
2. Implement and regression-test the current-main private-schema adapter, Train+Validation manifest builder, and explicit source-record input interface. Port only the required pieces; do not transplant stale PR #66 wholesale.
3. Match private source snapshot, shard, PeakTable, optional Validation-panel, payload-contract and checksum versions to that SHA. Reuse verified caches; do not redownload or rebuild them without evidence of mismatch.
4. Verify row/group counts, fingerprints, split isolation, PeakTable schema/loader round trip, file counts/sizes/SHA values, skip count and exact Train+Validation membership. Keep all 23,245 Test parents out of training/selection manifests.
5. Run only the current-main `--plan` and bounded offline CPU smoke in a clean environment; preserve commands, environment, logs and input/output hashes.
6. Publish a receipt tied to source SHA and private package hashes. Keep GPU `BLOCKED / NOT_RUN` unless a separate authorization is given and a bounded GPU smoke is actually completed.

A CPU-only pass is necessary but not sufficient for #61 `READY`. The bounded target-GPU smoke is a separate authorization and evidence gate. Even after #61 is READY, GPU HPO and formal training remain separate work under #55, with its own explicit budget/protocol approval.

## Historical migration instructions

The remainder of this README and the linked one-click migration note preserve earlier #66/#67 implementation details, data/package descriptions and proposed commands for provenance. They are **not the present execution contract** and must not be used until the preflight audit's current-main code, data, package and authorization gates are closed.
