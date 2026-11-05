#!/usr/bin/env python
"""Create a version-pinned copy of the original V10 trainer with optional full-horizon cosine LR.
The historical V10 trainer is never edited.
"""
from pathlib import Path
import hashlib, json
ROOT=Path(r"E:\AI4science")
P=ROOT/"xrd_robustness"
LOCAL=ROOT/"_local"/"resnet_joint_20261103"
SOURCE=P/"scripts"/"run_simxrd_architecture_pilot.py"
OUTPUT=LOCAL/"joint_v10_runner.py"
LOCAL.mkdir(parents=True,exist_ok=True)
s=SOURCE.read_text(encoding="utf-8")

def replace_once(before,after):
    global s
    n=s.count(before)
    if n!=1:raise RuntimeError(f"Unexpected template count={n}: {before[:100]}")
    s=s.replace(before,after,1)

replace_once('PROJECT_ROOT = Path(__file__).resolve().parents[1]',
             'PROJECT_ROOT = Path(r"E:\\AI4science\\xrd_robustness")')
replace_once('''                fused=bool(runtime["fused_adamw"]),
            )
            sampler = PhysicsParameterSampler''',
             '''                fused=bool(runtime["fused_adamw"]),
            )
            schedule_name = str(expected.get("scheduler", "none"))
            if schedule_name == "cosine_5pct_floor":
                scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                    optimizer, T_max=planned_steps, eta_min=float(expected["learning_rate"]) * .05
                )
            elif schedule_name == "none":
                scheduler = None
            else:
                raise ValueError(f"Unsupported training scheduler: {schedule_name}")
            sampler = PhysicsParameterSampler''')
replace_once('''                "scheduler": "none",
                "objective":''',
             '''                "scheduler": schedule_name,
                "scheduler_t_max": planned_steps if scheduler is not None else None,
                "scheduler_eta_min": float(expected["learning_rate"]) * .05 if scheduler is not None else None,
                "objective":''')
replace_once('''                        optimizer.step()
                        _check_parameters_and_optimizer(model, optimizer, step=global_step)''',
             '''                        optimizer.step()
                        if scheduler is not None:
                            scheduler.step()
                        _check_parameters_and_optimizer(model, optimizer, step=global_step)''')
replace_once('''                            total_loss=float(result["total"].detach().float().cpu()),
                            gradient_l2_norm=gradient_l2_norm,''',
             '''                            total_loss=float(result["total"].detach().float().cpu()),
                            learning_rate=float(optimizer.param_groups[0]["lr"]),
                            gradient_l2_norm=gradient_l2_norm,''')
replace_once('''                                    "training_mode": "dynamic_js",
                                    "lambda_js": float(expected["lambda_js"]),''',
             '''                                    "training_mode": "dynamic_js",
                                    "scheduler_name": schedule_name,
                                    "scheduler_state": None if scheduler is None else scheduler.state_dict(),
                                    "lambda_js": float(expected["lambda_js"]),''')
if OUTPUT.exists():
    if OUTPUT.read_text(encoding="utf-8")!=s:raise FileExistsError(OUTPUT)
else:
    OUTPUT.write_text(s,encoding="utf-8")
import ast
ast.parse(s)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
print(json.dumps({"event":"joint_runner_built","runner":str(OUTPUT),
"sha256":sha(OUTPUT),"source_sha256":sha(SOURCE),"lines":len(s.splitlines())}))
