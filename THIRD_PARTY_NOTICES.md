# Third-Party Notices

This repository contains or adapts components from third-party open-source projects.

## ML4pXRDs

The file xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py is a PyTorch port of the 1D ResNet family implemented in ML4pXRDs, including architecture logic described in the upstream training/utils/resnet_keras_1D.py and training/models.py::build_model_resnet_i.

Upstream repository: https://github.com/aimat-lab/ML4pXRDs

Upstream license: **MIT**.

The upstream MIT permission and warranty disclaimer apply to the adapted portions. The upstream license is compatible with this repository's MIT license.

Third-party scientific datasets are **not** relicensed by this repository. Their original terms continue to apply.

## K-Dense Scientific Agent Skills (repo-scoped)

The complete upstream `paper-lookup`, `database-lookup`, and `pymatgen` Skills under `.agents/skills/` are vendored without intended modification from https://github.com/K-Dense-AI/scientific-agent-skills at pinned commit `ec59a29a03d5c40f73ab40878df04860bc00e876`, under the **MIT License** (copyright 2025 K-Dense Inc.). A copy of upstream's complete permission text and warranty disclaimer is included in `.agents/skills/K_DENSE_LICENSE.md`.

The project-local `materials-investigation` coordinating Skill is not from K-Dense. Python libraries, Materials Project, COD and third-party scientific datasets retain their own licenses and usage terms. No personal-device Python environment, remote API credentials, or GPU jobs are automatically provisioned by this Git commit.
