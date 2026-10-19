# PXRD 自动实验状态

status: BLOCKED

- batio3: PASS
- calcite: SKIPPED
- ceo2: PASS
- corundum: SKIPPED
- grossular: PASS
- mgo: PASS
- rutile: PASS
- silicon: PASS
- zno: PASS

结果与失败记录

- batio3: NEURAL_RUNTIME_PARETO; cuda; training_seconds=2.2429180000326596
- calcite: {"reason": "Unsupported crystal system: trigonal", "status": "FAIL", "traceback": "Traceback (most recent call last):\n  File \"E:\\AI4science\\_local\\worktrees\\pxrd_cross_material_autolab_20261019\\pxrd_cross_material_autolab\\manager.py\", line 146, in run\n    model=physics.PowderModel(material[\"cif_path\"],grid_size=config.get(\"grid_size\",1024))\n          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"E:\\AI4science\\_local\\worktrees\\pxrd_cross_material_autolab_20261019\\pxrd_cross_material_autolab\\physics.py\", line 27, in __init__\n    raise ValueError('Unsupported crystal system: '+self.system)\nValueError: Unsupported crystal system: trigonal\n"}
- ceo2: NEURAL_RUNTIME_PARETO; cuda; training_seconds=2.882030999986455
- corundum: {"reason": "Unsupported crystal system: trigonal", "status": "FAIL", "traceback": "Traceback (most recent call last):\n  File \"E:\\AI4science\\_local\\worktrees\\pxrd_cross_material_autolab_20261019\\pxrd_cross_material_autolab\\manager.py\", line 146, in run\n    model=physics.PowderModel(material[\"cif_path\"],grid_size=config.get(\"grid_size\",1024))\n          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"E:\\AI4science\\_local\\worktrees\\pxrd_cross_material_autolab_20261019\\pxrd_cross_material_autolab\\physics.py\", line 27, in __init__\n    raise ValueError('Unsupported crystal system: '+self.system)\nValueError: Unsupported crystal system: trigonal\n"}
- grossular: NEURAL_RUNTIME_PARETO; cuda; training_seconds=3.394477999943774
- mgo: NEURAL_RUNTIME_PARETO; cuda; training_seconds=2.673255700035952
- rutile: NEURAL_RUNTIME_PARETO; cuda; training_seconds=2.70759560004808
- silicon: NEURAL_RUNTIME_PARETO; cuda; training_seconds=3.3320183000178076
- zno: NEURAL_RUNTIME_PARETO; cuda; training_seconds=3.1817713000345975

比较表: [COMPARISON.csv](COMPARISON.csv) / [COMPARISON.json](COMPARISON.json)
归一化 q MAE 与晶格误差 (angstrom) 分开报告；不同自由度不混合汇总。
P3 时间包含全部三个起点；N+A 包含网络推理与物理精修，训练成本另列。
来源、配置、CIF 与代码 SHA256 见 ../manifest.json；失败历史见 ../events.jsonl 和各材料目录。

合成谱结果仅说明逐材料流程，不证明真实实验谱或零样本泛化。
