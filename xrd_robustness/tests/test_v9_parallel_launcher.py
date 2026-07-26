from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.run_v9_method_transfer import _scheduled_argv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class V9ParallelLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        contract = json.loads(
            (PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json")
            .read_text(encoding="utf-8")
        )
        profile = json.loads(
            (PROJECT_ROOT / contract["hardware_profile"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.applied = profile["applied"]
        self.scheduler = self.applied["parallel_run_scheduler"]
        self.argv = [
            "scripts/train_v7.py",
            "--dynamic-prefetch-workers",
            "8",
            "--dynamic-prefetch-batches",
            "8",
        ]

    def test_registered_laptop_concurrency_uses_all_workers_for_one_run(self) -> None:
        self.assertEqual(self.applied["run_concurrency"], 1)
        effective, workers = _scheduled_argv(self.argv, self.scheduler, group_size=1)
        self.assertEqual(workers, 8)
        self.assertEqual(
            effective[effective.index("--dynamic-prefetch-workers") + 1], "8"
        )
        self.assertEqual(self.scheduler["strategy"], "serial-v1")

    def test_unpaired_tail_run_restores_all_eight_workers(self) -> None:
        effective, workers = _scheduled_argv(self.argv, self.scheduler, group_size=1)
        self.assertEqual(workers, 8)
        self.assertEqual(
            effective[effective.index("--dynamic-prefetch-workers") + 1], "8"
        )


if __name__ == "__main__":
    unittest.main()
