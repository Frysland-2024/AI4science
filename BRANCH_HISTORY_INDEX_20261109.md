# Branch history preservation — 2026-11-09

This branch archives **commit reachability**, not current code. Its archival commits use the exact Git tree of `main` at snapshot `6bb8efb71d177828fb19ed1c2194f225fb996127`, so experimental/inversion/old Codex source was **not** merged into `main`.

**Snapshot**: 38 remote branches (37 non-main); archive commits preserved 37 branch tips, by making each a Git ancestor of this archive branch. `main` and active branches were not changed by the archival commits. Do not merge this branch into `main`.

GitHub PR status at review: 0 open PRs. An open PR is not required for a branch to contain unique work. Before deleting a branch, compare its latest head with the SHA in this table; if it has moved, archive the newer tip first.

## Branch heads at audit

| Branch | Snapshot tip SHA |
|---|---|
| `docs/da-must-beat-physics-20261019` | `b56b445c5d77dd083c63a88122b7abda02d6beb0` |
| `docs/donut-source-workflow-audit-20261019` | `e174e8ad23f9b9ef9514fc822d33e829a95d9c61` |
| `docs/final-inversion-evidence-boundary-20261027` | `9ca139cf21da8b5d468eafe64f2e3e4c136428a6` |
| `docs/fix-showcase-evidence-20261030` | `6e4dd70a7134427fc9c8a04b686dce5e20ea6727` |
| `docs/history-date-label-20261030` | `eee753dd41d5b6151b21e14acf20699940c65763` |
| `docs/personalized-pxrd-adaptation-concept-20261019` | `759fa61bba2585c872870f0a91e2b3d1a0b59801` |
| `docs/pxrd-two-day-decision-record-20261019` | `f05cc366a1c48cee2c784bb36c6fef9a7bc5770f` |
| `docs/record-pr50-boundary-sync-20261031` | `8ff2dad1a61844a1c9b4e508a6deb86841c8b478` |
| `docs/research-supervisor-mvp-20261018` | `ba47e402991482c9c3c5c3ee34fae40f651a7efe` |
| `docs/rruff-cohort-expansion-20261104` | `7dad3ad40bd7f8422d9c10840f076104e03f0b49` |
| `docs/streamline-public-repository-20261109` | `b2e7902974fb17822bba70b5899a079c90887b2d` |
| `docs/supervisor-showcase-20261020` | `dc1013c9804debb728ad89065adad2b763785c86` |
| `experiments/resnet-a1-a2-20261103` | `5641d5d82ac8009400db848ee5b22814960a2552` |
| `experiments/resnet-joint-a0-a1-a2-20261103` | `e5594ac2f112dd60d20b1dc9bf09f4c8baddaae6` |
| `feat/bridge-fresh-source-code-approval` | `e49f0becd8d5da422a6598ffb6c65052cb53ee1a` |
| `feat/codex-chatgpt-task-bridge-20261018` | `fe44ac996d0d5da84d7b26a7237247aadc2dbda8` |
| `feat/ferroelectric-pre-refinement-w0` | `3fbb64f16e0f53164ce607afa071dca199aeb0c3` |
| `feat/gpu-bridge-unbounded-auto-results-20261018` | `4a8e662cf7ac13e2956a412e7b03ac008e8ac33d` |
| `feat/issue-53-simulator-v11` | `5fd54fc25e929a853c8ae57f3e843c204f77fc65` |
| `feat/physics-guided-pxrd-inversion-pilot` | `f88bb5e0340bd5f47f80149c0a9464ae92711943` |
| `feat/public-batio3-forward-ab` | `66cba0202fc232080ef42c31952cc66c8a4d75fc` |
| `feat/pxrd-autolab-v1` | `e92066b2dab61b39aa8838674af789ccf4d8c52c` |
| `feat/research-supervisor-mvp-20261018` | `b075c79ec5f4a6eeedb4d6c229689a1c8b2e719d` |
| `feat/v11-prefetch-train-validation-20261103` | `890fc9f3c2b47af9627b6eeb0b2e7ce2a079f0a0` |
| `feat/v11-server-oneclick-optuna-20261103` | `314ab5ccf4f346faa2a1d84f751da057b8d83d79` |
| `feature/v10-p0-measurement-information-gate` | `d699bc6745927899046930fdf08fdd8432b87c06` |
| `feature/v10-pilot-v2-learned-state` | `39ce72b6b8bc836536958c6f0713b91667a96584` |
| `feature/v10-train-only-pilot` | `e0f5d5c840434203c6865fee45f342cdd77ce1f1` |
| `fix/cnn11-v10-numerics-direct-20261103` | `ff547d03493b89d16b120d2ee4f8041d2b5ae0e3` |
| `fix/research-bridge-remote-snapshot-and-logs-20261018` | `64794cadb25e57726c198c2cab02b972707154e4` |
| `integrate/parent-budget-results-roles-20261018` | `1ce212ec01a6caa505d2db55a82c7f87c5ba94f3` |
| `integrate/v11-server-pipeline-20261109` | `a34f94b5da6581416315922ea35b78bff4864b83` |
| `issue53-simulator-v11` | `6c162635ca34bc170e3b2c3488e9fd38aa995363` |
| `issue55-resnet-js-search` | `14873c44ab8e7bfc12744495b99721210b95ac56` |
| `main` | `6bb8efb71d177828fb19ed1c2194f225fb996127` |
| `maintenance/archive-branches-20261109` | `6bb8efb71d177828fb19ed1c2194f225fb996127` |
| `public-cleanup-20261002` | `5f5a34e18763962dde52722d60764ac8349bbf81` |
| `tools/local-training-monitor` | `5802060702f1a7f48e17c790c8573ebf01f8a8a4` |

## Clean-up policy

- Keep `main`, this archive reference, and only genuinely ongoing/unmerged research implementation lanes until their integration decisions are closed.
- For old Codex, diagnostics, experiments, DONUT, inversion, historical docs and PR-related branches: verify against the snapshot; then remove branch **refs**, not scientific documentation or source artefacts from main.
- Do **not** bulk merge stale research code into `main`; archived branches may include obsolete instructions, failed experiments, and security-sensitive bridge utilities.
- Do **not** delete any branch with a changed SHA or with currently active work until separately audited.
- The archive contains historical commits, **not** copies of ignored local datasets, GPU checkpoints, private files or live machine state.
