# 代码仓库整理后的目录

## 核心区

`xrd_perturbation_core/`

保存 V6 直接相关的 XRD 源码、经过校验的候选源码、PySimXRD 软件包和按论文整理的代码位置说明。这里的代码只作为方法复核和独立重写的依据，不等于把第三方实现直接接入 V6。

## 相关方法区

`related_methods_and_tem/`

保存 PyWPEM、PRDNet、TIR 和 KBSS 等非 V6 核心方向的源码参考。它们只用于阅读、对照和提炼训练组织思想，不作为 V6 的运行依赖。

## 本次清理

- `paper_map` 已并入 `xrd_perturbation_core/paper_map`。
- `KBSS-main` 已移入 `related_methods_and_tem/04_KBSS_reference_source/KBSS-main`。
- `github_archives_extracted`、`root_archives_extracted` 已删除。
- KBSS 原始 ZIP 和 `WPEM-PyxploreUI-main` 界面/教程归档已删除。
- KBSS 原始 ZIP 的 SHA256：`186D1435EE40EB0AF38814FFB9B2960C2BF9D55D969ACC9DE61A31A2354602E2`。
