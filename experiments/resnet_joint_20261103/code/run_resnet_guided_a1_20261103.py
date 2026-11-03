#!/usr/bin/env python
"""Direct, Codex-free, read-only-baseline V10 ResNet architecture A1 pilot."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import importlib.util
import json
import math
import shutil
import sys
import hashlib
import torch
from torch import nn

ROOT = Path(r"E:\AI4science")
PROJECT = ROOT / "xrd_robustness"
sys.path.insert(0, str(PROJECT / "src"))
RUNNER = PROJECT / "scripts" / "run_simxrd_architecture_pilot.py"
OLD = PROJECT / "outputs" / "simxrd_architecture_pilot_20261103"
OUT = PROJECT / "outputs" / "resnet_simxrd_guided_A1_20261103"
REPORT = PROJECT / "reports" / "resnet_simxrd_guided_A1_20261103"
PROTOCOL = ROOT / "_local" / "resnet_simxrd_guided_A1_protocol_20261103.json"
BASE_PROTOCOL = PROJECT / "configs" / "simxrd_cnn11_pilot.20261103.json"
BASE_SMOKE = PROJECT / "reports" / "simxrd_architecture_pilot_20261103" / "smoke.json"

from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D, ML4PXRDResNet1DConfig

@dataclass(frozen=True)
class A1Config(ML4PXRDResNet1DConfig):
    stage_strides: tuple[int, int, int] = (4, 2, 4)
    kernel_size: int = 9
    variant: str = "A1 selective reduced downsampling"

class A1ResNet(ML4PXRDResNet1D):
    def __init__(self, config: A1Config):
        super().__init__(config)
        assert config.square_kernel_size_and_stride and config.model_id == "18"
        # Only change the middle stage transition; keep original kernel=9 and stem.
        block = self.stages[2][0]
        for layer in (block.conv1, block.projection):
            assert layer is not None and layer.stride == 4
            layer.stride = 2
            layer.conv.stride = (2,)
        n = math.ceil(math.ceil(config.input_length / 2) / 2)
        for stride in config.stage_strides:
            n = math.ceil(n / stride)
        self.final_length = n
        self.embedding = nn.Linear(self.final_channels * self.final_length, config.dense_width)
        nn.init.xavier_uniform_(self.embedding.weight)
        nn.init.zeros_(self.embedding.bias)
        assert self.final_length > 0

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--max-steps", type=int, default=12320)
    args = ap.parse_args()
    assert args.max_steps in (6160, 12320), "This script only allows predeclared bounded screens."
    assert json.loads(BASE_SMOKE.read_text(encoding="utf-8"))["status"] == "passed"
    assert RUNNER.is_file() and BASE_PROTOCOL.is_file()
    spec = importlib.util.spec_from_file_location("existing_simxrd_pilot_A1", RUNNER)
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    model_config = A1Config()
    model = A1ResNet(model_config)
    with torch.inference_mode():
        logits = model(torch.zeros(2, 3501))["logits"]
    assert logits.shape == (2, 7) and torch.isfinite(logits).all()
    print(json.dumps({"event":"A1_shape_pass", "stage_strides":model_config.stage_strides, "kernel":9,
                      "final_length":model.final_length,"parameters":model.parameter_count,
                      "historical_resnet_parameters":13008839}), flush=True)
    if args.check:
        return
    if OUT.exists() or REPORT.exists() or PROTOCOL.exists():
        raise FileExistsError("Versioned A1 output/protocol already exists; refusing overwrite.")
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        if free < 3 * 1024**3:
            raise RuntimeError(f"GPU free memory only {free/1024**3:.2f}GiB; abort.")
    protocol = json.loads(BASE_PROTOCOL.read_text(encoding="utf-8"))
    protocol["direct_launch_note"] = {
        "experiment": "paper-guided ResNet architecture A1",
        "hypothesis": "weaker stage-3 downsampling preserves XRD peak information",
        "changes_from_baseline": "stage transitions 4/4/4 -> 4/2/4 ONLY; residual kernel stays 9",
        "selected_steps": args.max_steps,
        "validation_only": True,
        "source_runner_sha256": sha256(RUNNER),
        "source_resnet_sha256": sha256(PROJECT / "src/xrd_robustness/models/ml4pxrd_resnet1d.py"),
        "baseline_run": "resnet18gn_v10/seed_20260711, selected Val OOD F1 0.70899 at step 30800",
        "matched_early_baseline": "seed 20260711, Val OOD F1 0.57530 at 6160 and 0.67228 at 12320",
    }
    PROTOCOL.write_text(json.dumps(protocol,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    oldcache = OLD / "evaluation_cache" / "validation_v10_pseudo_voigt_caglioti_seed_20260721"
    newcache = OUT / "evaluation_cache" / oldcache.name
    if not (oldcache / "panel_index.json").is_file():
        raise FileNotFoundError(f"Missing prevalidated V10 panel cache: {oldcache}")
    newcache.parent.mkdir(parents=True,exist_ok=True)
    print(json.dumps({"event":"copying_prevalidated_validation_panels","source":str(oldcache)}),flush=True)
    shutil.copytree(oldcache,newcache)
    pilot.PROTOCOL_PATH = PROTOCOL
    pilot._make_model = lambda model_id: (A1ResNet(A1Config()), A1Config()) if model_id=="resnet18gn" else (_ for _ in ()).throw(ValueError(model_id))
    print(json.dumps({"event":"A1_training_launch","budget_steps":args.max_steps,"device":str(torch.device("cuda" if torch.cuda.is_available() else "cpu")),"report":str(REPORT)}),flush=True)
    _, _, sim = pilot._load_config()
    result = pilot.train_model(
        model_id="resnet18gn",
        config_id="resnet18gn_A1_stride424_kernel9",
        simulator_version=pilot.SIMULATOR_VERSIONS["v10"],
        sim_config=sim,
        sim_config_path=pilot.V10_SIM_PATH,
        line_profile=sim["line_profile"],
        data_root=pilot.DEFAULT_DATA_ROOT,
        output_root=OUT,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        report_root=REPORT,
        training_seeds=[20260711],
        max_steps=args.max_steps,
    )
    pilot._write_json(REPORT/"A1_training_results.json",result)
    print(json.dumps({"event":"A1_complete","result":str(REPORT/"A1_training_results.json")}),flush=True)

if __name__=="__main__":
    main()
