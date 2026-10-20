# 已知 CIF 初值与 RRUFF 实测验证

本模块将两个独立协议分开冻结：E1 为旧七材料测试的固定一次事后探索比较；E2 为精确 RRUFF 样品的描述性案例系列。不得将它们称为新的确认性测试或总体泛化证据。

从仓库根目录，使用已安装 numpy/scipy/pymatgen/torch/pytest 的 Python 环境：

```powershell
$py = 'C:/Users/Lenovo/.codex/venvs/issue19-measurement-closure/Scripts/python.exe'
& $py -m pxrd_heuristic_rruff_validation audit
& $py -m pxrd_heuristic_rruff_validation preflight
& $py -m pxrd_heuristic_rruff_validation run --arm e1
& $py -m pxrd_heuristic_rruff_validation run --arm e2
& $py -m pxrd_heuristic_rruff_validation verify
& $py -m pxrd_heuristic_rruff_validation report
& $py -m pxrd_heuristic_rruff_validation status
& $py -m pytest pxrd_heuristic_rruff_validation -q -p no:cacheprovider
```

先看两份预注册及其冻结 manifest，再看 reports/HEURISTIC_RESULTS.md 与 reports/RRUFF_REAL_RESULTS.md。run 只恢复尚未完成的固定单位，不以已打开结果调整方法、门槛或样品。真实谱门槛失败时停止神经臂；波长未知时阻断定量拟合。

原始 RRUFF ZIP 位于 E:/AI4science/RRUFF，仅只读使用。原权重与归一化位于原七材料 worktree，仅只读使用。生成数组、原谱及权重不能上传；private/ 已忽略。公开证据只保留代码、协议、来源/字节哈希和紧凑逐样品记录。E1 不再训练，E2 未经物理门槛不能训练。总授权上限为3小时墙钟、90分钟GPU训练、5GB新增输出。

status 是执行与科学结论的分别记录；优化器报告成功不代表晶格正确，参考 RRUFF 晶胞只用于事后一致性比较。

交付后可单独执行不写文件、不重新拟合的检查：

```powershell
& $py -m pxrd_heuristic_rruff_validation.e1_verify
& $py -m pxrd_heuristic_rruff_validation.verify_delivery
```

完整 `report` 命令只从已有数值记录重建中文报告，不重开数值测试。`verify` 会重算汇总；最后的 `verify_delivery` 是纯只读工件哈希检查。历史RRUFF角色另见 reports/historical_id_overlap.json；两条病例与旧分类锁定测试有base ID重叠，本次没有任何真实训练或阈值调优。
