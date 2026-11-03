#!/usr/bin/env python
"""A2: A1 geometry with 5-bin residual kernels; standalone direct GPU launcher."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import json
import math
import shutil
import sys
import torch
from torch import nn

ROOT=Path(r"E:\AI4science")
PROJ=ROOT/"xrd_robustness"
sys.path.insert(0,str(ROOT/"_local"))
sys.path.insert(0,str(PROJ/"src"))
from run_resnet_guided_a1_20261103 import A1Config,A1ResNet,sha256
from xrd_robustness.models.ml4pxrd_resnet1d import ML4PXRDResNet1D,_SamePadConv1d

OUT=PROJ/"outputs"/"resnet_simxrd_guided_A2_20261103"
REPORT=PROJ/"reports"/"resnet_simxrd_guided_A2_20261103"
PROTOCOL=ROOT/"_local"/"resnet_simxrd_guided_A2_protocol_20261103.json"
BASE_PROTOCOL=PROJ/"configs"/"simxrd_cnn11_pilot.20261103.json"
BASE_SMOKE=PROJ/"reports"/"simxrd_architecture_pilot_20261103"/"smoke.json"
RUNNER=PROJ/"scripts"/"run_simxrd_architecture_pilot.py"
OLD=PROJ/"outputs"/"simxrd_architecture_pilot_20261103"

@dataclass(frozen=True)
class A2Config(A1Config):
    kernel_size:int=5
    variant:str="A2 selective reduced downsampling plus residual kernel 5"

class A2ResNet(A1ResNet):
    def __init__(self,config:A2Config):
        super().__init__(config)
        for stage in self.stages:
            for block in stage:
                for attr in ("conv1","conv2"):
                    old=getattr(block,attr)
                    assert old.kernel_size==9 and old.stride in (1,2,4)
                    replacement=_SamePadConv1d(
                        old.conv.in_channels,old.conv.out_channels,
                        kernel_size=config.kernel_size,stride=old.stride,bias=False,
                    )
                    ML4PXRDResNet1D._keras_variance_scaling_(replacement.conv.weight)
                    setattr(block,attr,replacement)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--check",action="store_true")
    ap.add_argument("--max-steps",type=int,default=12320)
    opt=ap.parse_args()
    assert opt.max_steps==12320,"Predeclared A2 matched budget must remain 12320"
    model=A2ResNet(A2Config())
    with torch.no_grad():
        pred=model(torch.zeros(2,3501))["logits"]
    assert tuple(pred.shape)==(2,7) and torch.isfinite(pred).all()
    for stage in model.stages:
        for block in stage:
            assert block.conv1.kernel_size==5 and block.conv2.kernel_size==5
    assert model.stages[2][0].conv1.stride==2
    print(json.dumps({"event":"A2_architecture_pass","kernel_size":5,
          "stage_strides":[4,2,4],"parameter_count":model.parameter_count,
          "final_feature_length":model.final_length}),flush=True)
    if opt.check:return
    if OUT.exists() or REPORT.exists() or PROTOCOL.exists():
        raise FileExistsError("A2 archive already exists; refusing overwrite/second run")
    assert json.loads(BASE_SMOKE.read_text(encoding="utf-8"))["status"]=="passed"
    if not torch.cuda.is_available():raise RuntimeError("GPU unavailable; refuse CPU training")
    free,total=torch.cuda.mem_get_info()
    if free<3*1024**3:
        raise RuntimeError(f"Insufficient free GPU VRAM: {free/1024**3:.1f} GiB")
    base=json.loads(BASE_PROTOCOL.read_text(encoding="utf-8"))
    base["direct_launch_note"]={
        "experiment":"SimXRD-guided ResNet A2 kernel-size ablation",
        "hypothesis":"With stage transitions 4/2/4 fixed, kernel 5 vs 9 alters XRD peak receptive field",
        "changes_from_A1":"Only residual kernels 9 to 5; preserve stride 4/2/4",
        "training_seed":20260711,"selected_steps":opt.max_steps,
        "evaluation":"Validation OOD only; NEVER RRUFF/Test selection",
        "source_runner_sha256":sha256(RUNNER),
        "source_a1_sha256":sha256(ROOT/"_local"/"run_resnet_guided_a1_20261103.py"),
        "source_a2_sha256":sha256(Path(__file__)),
        "source_resnet_sha256":sha256(PROJ/"src"/"xrd_robustness"/"models"/"ml4pxrd_resnet1d.py"),
    }
    PROTOCOL.write_text(json.dumps(base,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    source=OLD/"evaluation_cache"/"validation_v10_pseudo_voigt_caglioti_seed_20260721"
    target=OUT/"evaluation_cache"/source.name
    if not (source/"panel_index.json").exists():raise FileNotFoundError(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,target)
    spec=importlib.util.spec_from_file_location("simxrd_architecture_pilot_A2",RUNNER)
    pilot=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    pilot.PROTOCOL_PATH=PROTOCOL
    pilot._make_model=lambda model_id: (
        A2ResNet(A2Config()), A2Config()
    ) if model_id=="resnet18gn" else (_ for _ in ()).throw(ValueError(model_id))
    _,_,sim=pilot._load_config()
    print(json.dumps({"event":"A2_training_launch","requested_steps":opt.max_steps,
        "report_root":str(REPORT)}),flush=True)
    result=pilot.train_model(
        model_id="resnet18gn",config_id="resnet18gn_A2_stride424_kernel5",
        simulator_version=pilot.SIMULATOR_VERSIONS["v10"],
        sim_config=sim,sim_config_path=pilot.V10_SIM_PATH,
        line_profile=sim["line_profile"],
        data_root=pilot.DEFAULT_DATA_ROOT,output_root=OUT,
        device=torch.device("cuda"),report_root=REPORT,
        training_seeds=[20260711],max_steps=opt.max_steps,
    )
    pilot._write_json(REPORT/"A2_training_results.json",result)
    print(json.dumps({"event":"A2_complete","result":str(REPORT/"A2_training_results.json")}),flush=True)

if __name__=="__main__":main()
