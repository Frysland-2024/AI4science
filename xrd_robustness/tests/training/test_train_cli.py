from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from xrd_robustness.training import runner


def _fixed(value: float) -> dict[str, float | str]:
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


class TinyResNetContract(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.head = nn.Linear(8, 7)

    def forward(self, values: torch.Tensor) -> dict[str, torch.Tensor | None]:
        embedding = torch.nn.functional.adaptive_avg_pool1d(
            values.unsqueeze(1), 8
        ).squeeze(1)
        return {
            "logits": self.head(embedding),
            "pooled_embedding": embedding,
            "main_tokens": embedding.unsqueeze(1),
            "prior_tokens": None,
        }


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    rows = []
    for index, split in enumerate(("train", "train", "validation")):
        peak_path = tmp_path / f"material-{index}.npz"
        np.savez(
            peak_path,
            positions=np.asarray([20.0 + index, 35.0 + index, 50.0 + index]),
            intensities=np.asarray([100.0, 60.0, 25.0]),
        )
        rows.append(
            {
                "material_id": f"material-{index}",
                "split": split,
                "crystal_system": ("cubic", "hexagonal", "monoclinic")[index],
                "peak_table_path": peak_path.name,
            }
        )
    records = tmp_path / "records.jsonl"
    records.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    simulation = tmp_path / "simulation.json"
    simulation.write_text(
        json.dumps(
            {
                "run_seed": 7,
                "profiles": {
                    "train": {
                        "severity_level": 1,
                        "background_type": "flat",
                        "delta_2theta_deg": _fixed(0.0),
                        "fwhm_deg": _fixed(0.08),
                        "background_to_peak_ratio": _fixed(0.0),
                        "noise_std_ratio": _fixed(0.0),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return records, simulation


def test_peak_record_contract_rejects_duplicate_materials(tmp_path: Path) -> None:
    records, _ = _fixture(tmp_path)
    first = records.read_text(encoding="utf-8").splitlines()[0]
    records.write_text(first + "\n" + first + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate material_id"):
        runner.load_peak_records(records)


def test_public_parser_exposes_only_dynamic_erm_and_js() -> None:
    action = next(
        action for action in runner.build_parser()._actions if action.dest == "mode"
    )
    assert set(action.choices) == {"dynamic_erm", "dynamic_js"}


def test_one_step_training_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records, simulation = _fixture(tmp_path)
    monkeypatch.setattr(runner, "build_model", lambda _config: TinyResNetContract())
    output = tmp_path / "run"
    args = runner.build_parser().parse_args(
        [
            "--records",
            str(records),
            "--simulation-config",
            str(simulation),
            "--output-dir",
            str(output),
            "--mode",
            "dynamic_js",
            "--lambda-js",
            "0.5",
            "--epochs",
            "1",
            "--batch-size",
            "2",
            "--max-steps",
            "1",
            "--device",
            "cpu",
        ]
    )
    result = runner.run(args)
    assert result["status"] == "completed"
    assert result["global_step"] == 1
    for name in (
        "resolved_config.json",
        "history.json",
        "best.ckpt",
        "last.ckpt",
        "result.json",
    ):
        assert (output / name).is_file()
