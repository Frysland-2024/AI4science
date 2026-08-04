# XRD Robustness V9-T：当前工程交接

## 2026-08-03 RRUFF-371 data handoff

- Current local dataset: `data/real_xrd/rruff371/` (Git-ignored, not
  publishable data).
- Frozen identity: `rruff-real-pxrd-371-v2`.
- Composition: 371 unique RRUFF sample IDs; 53 per crystal system; 70 frozen
  legacy spectra plus a 301-sample model-blind extension (43 per class).
- Preservation: `rruff-real-pxrd-350-v1` remains intact. All 350 IDs and their
  canonical-spectrum, RAW, and DIF hashes are preserved in v2; the 21 additions
  are balanced at three per class.
- Rebuild: parameterized `scripts/build_rruff350.py` using the five official
  archives retained in `data/real_xrd/rruff350/source_archives/`, with
  `--target-per-class 53 --dataset-version 2`.
- Audits: `reports/rruff371_build_audit.json` and
  `reports/rruff371_expansion_audit.json`.
- Intended roles: legacy RRUFF-70 is development/few-shot data; the extension
  is the 301-sample external evaluation cohort. The replacement role/episode
  manifests are not yet frozen and real-XRD execution remains disabled.
- Design recommendation: replace the obsolete 21/14/35 split with 35 support
  and 35 adaptation-validation samples (five per class each), supporting a
  nested 0/1/2/3/5-shot curve.
- Scope caveat: 34 extension samples share 23 normalized mineral names with the
  legacy 70. Primary claims are measurement-domain transfer; unseen-mineral
  claims require a separately frozen group-disjoint sensitivity cohort.

**交接状态日期：2026-08-03**
**仓库：** `Frysland-2024/AI4science`  
**分支：** `main`

> 本文件只保留当前可执行状态。旧阶段的完整细节仍保存在 Git 历史、
> `00_project_context/PROJECT_JOURNEY.md` 和日期化报告中。

## 当前结论

V9 的正式方法比较已经收敛为：

- baseline：Dynamic ERM；
- selected method：JS Consistency；
- fixed weight：`lambda_js = 60`；
- backbone：ResNet-18-GN；
- preprocessing：identity；
- optimizer：AdamW；
- learning-rate schedule：constant；
- split：parent-structure 70/15/15；
- evaluation role：Validation-only replication completed。

Residual-v1 已经因预注册稳定性 Gate 失败而归档，不得重新开放其 lambda
范围。JS lambda 也不得因本次结果继续调参。

one-shot simulated-Test 合同现已冻结：

`configs/v9_resnet_js_simulated_test.preregistered.json`

人类可读说明：

`reports/v9_resnet_js_simulated_test_contract_20260801.md`

合同文件继续保留 `preregistered_locked_not_authorized`，以固定执行前科学
选择；独立执行授权已于 2026-08-02 记录。2026-08-03 的第一次本地启动因
runner 对每个 checkpoint 重复生成相同冻结谱图而形成 CPU 瓶颈，用户在任何
checkpoint 结果或 summary 写出前将其停止。没有观察到 Test 指标，但必须如实
记录已经发生过部分 Test 访问。

用户随后明确指令“重搞”，授权一次完全相同的工程重试。新增 retry
authorization 只允许 render-once 哈希缓存、原子状态和同一 attempt 的断点续跑；
checkpoint、manifest、profile、evaluation seed、metric 和选择规则均不得改变。

## 十轮实验状态

五组 paired seeds、每组 Dynamic ERM 与 JS lambda=60，共十次运行，已全部
完成。训练 seeds 为 `20260711` 至 `20260715`，Validation evaluation seed 固定
为 `20260720`。

权威机器结果：

`reports/v9_resnet_js_ten_run_summary.json`

人类可读报告：

`reports/v9_resnet_js_ten_run_results_20260801.md`

结果文件最初提交于：

`868b079c1b410e6afe877330b7defc4262d82969`

## 核心结果

| Metric | Dynamic ERM | JS lambda=60 | Paired mean delta |
|---|---:|---:|---:|
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

Primary OOD paired-bootstrap 95% interval：
`[0.038145, 0.052834]`。

In-range paired-bootstrap 95% interval：
`[0.014028, 0.041954]`。

五组 paired seeds 的 OOD delta 全部为正，in-range delta 也全部为正；
预注册 in-range guardrail 通过。

## 已冻结的 simulated-Test 执行规则

Test 阶段保留全部五组 paired training seeds，并独立评估十个已经由
Validation 选出的 checkpoint。不得重新训练、替换、平均、集成或根据 Test
结果选择 checkpoint。

冻结 checkpoint：

| seed | Dynamic ERM | JS lambda=60 |
|---:|---|---|
| 20260711 | epoch 80 / step 49280 | epoch 40 / step 24640 |
| 20260712 | epoch 90 / step 55440 | epoch 80 / step 49280 |
| 20260713 | epoch 100 / step 61600 | epoch 80 / step 49280 |
| 20260714 | epoch 90 / step 55440 | epoch 30 / step 18480 |
| 20260715 | epoch 80 / step 49280 | epoch 60 / step 36960 |

Test split 固定为 2,109 个 held-out parent structures。deterministic evaluation
seeds 为：

- `20260721`；
- `20260722`；
- `20260723`。

Primary endpoint 为：先在每个 checkpoint 内平均 6 个 single-factor OOD
profiles × 3 个 evaluation seeds，再计算五组 JS-minus-ERM paired deltas。
评测 seed、profile 和谱图不得被当成额外训练 replicate；主要置信区间在五组
matched training-seed pairs 上进行 paired bootstrap。

旧 `evaluation.v9.method_transfer.json` 中的“三个 checkpoint hashes”是早期
占位条目，历史文件不改写。新 Test 合同明确取代该占位规则，要求十个
Validation-selected checkpoints。

## 必须保留的诊断风险

seed `20260714` 的 Validation worst-class F1 delta 为 `-0.061139`，其余四组
为正。因此不能写成“JS 对每个 seed、每个类别都一致改善”。Test 合同要求定位：

1. 哪个 crystal system 形成 worst class；
2. 该下降来自哪个 condition/profile；
3. Test 上是否出现相同模式；
4. 如何在不重新选模型、不重新调 lambda 的前提下呈现该限制。

该异常不改变预注册 primary Validation-OOD conclusion，但必须进入论文
limitation 和 secondary diagnostic。

## simulated-Test 已完成结果

完全相同的 authorized retry 已于 2026-08-03 完成，10/10 checkpoints 均已
写入带哈希的原子 run state。主要结果为五组 paired single-factor OOD
Macro-F1 delta 均为正，平均 `+0.054600`，sample SD `0.007271`，paired-bootstrap
95% 区间 `[+0.048944, +0.060255]`。五组 in-range delta 也全部为正。

推理阶段连续 12 秒 GPU 样本平均 94.25%（范围 91-97%）；CPU-bound 缓存
阶段不纳入该利用率口径。完整清点与 secondary diagnosis 见
`reports/v9_resnet_js_simulated_test_results_20260803.md`。

seed `20260714` 的 Test worst-class paired delta 为 `+0.005531`，未复现
Validation 上的 aggregate decline；但 monoclinic 仍是主要瓶颈，positive/
negative shift 和 texture 条件仍出现 worst-class 下降。因此只能主张 aggregate
robustness improvement，不能主张每个类别和扰动条件都一致改善。

## 当前进程与产物

- ten-run 已结束；
- simulated-Test 合同已冻结；
- simulated-Test 首次本地启动因工程瓶颈中止，未产生任何 run result；
- 完全相同的 retry 已授权并完成 10/10 checkpoints；
- 本地十个 checkpoint 与三份 frozen manifest 已通过 preflight；
- 优化 runner、retry authorization 与性能审计已完成；
- 当前没有需要继续恢复的训练；
- 不应重复启动相同十轮矩阵；
- 不应重新选择 seed；
- 不应继续搜索 lambda；
- checkpoint、outputs、generated spectra 和 caches 不进入 Git。

仓库中的 summary 只记录结果与哈希，不替代本地完整训练产物。

## 访问边界

以下资源仍锁定：

- 任何 simulated-Test 重跑、Test-guided selection 或 retuning；
- real XRD；
- real-domain adaptation；
- V10；
- 任何新的 Validation-guided method selection。

当前状态明确为：

- `simulated_test_accessed = true`；
- `simulated_test_result_available = true`；
- `identical_retry_started = true`；
- `identical_retry_completed = true`；
- `simulated_test_contract_frozen = true`；
- `identical_retry_authorized = true`；
- `real_xrd_used = false`；
- `lambda_retuned = false`；
- `seed_excluded_posthoc = false`。

任何后续 Codex/GPT 会话不得把 Validation 结果描述为 Test、sim-to-real 或
真实实验验证，也不得把合同冻结解释为 Test 执行授权。

## 下一阶段的正确顺序

1. 冻结并保留 Test summary、audit、结果报告与本地 hashed raw evidence；
2. 不得重跑 Test、重新选择 checkpoint、排除 seed 或重新调 lambda；
3. 把 monoclinic shift/texture limitation 纳入论文限制；
4. 另行设计和授权 real-XRD external validation，保持 V9 方法选择关闭。

## 新会话读取顺序

1. `AGENTS.md`
2. `00_project_context/CURRENT_STATE.md`
3. 本文件
4. `reports/v9_resnet_js_ten_run_results_20260801.md`
5. `reports/v9_resnet_js_ten_run_summary.json`
6. `configs/v9_resnet_js_simulated_test.preregistered.json`
7. `reports/v9_resnet_js_simulated_test_contract_20260801.md`
8. `reports/v9_resnet_js_simulated_test_results_20260803.md`
9. `reports/v9_resnet_js_simulated_test_summary.json`
10. `configs/v9_resnet_js_ten_run.preregistered.json`
11. `configs/v9_resnet_js_ten_run.authorization.json`

## 当前明确下一动作

当前动作是：

> simulated Test 已完成并冻结；不得重跑或 Test-guided retuning。下一步是
> 单独设计和授权 real-XRD external validation。real XRD 目前仍未使用。

## 2026-08-04 opXRD 铁电可行性审计（NO_GO）

opXRD 铁电相关陶瓷 PXRD 数据可行性审计已完成。结论为 **NO_GO**：

- opXRD（92,552 条实验谱）中 **不存在** 铁电氧化物陶瓷材料
- 唯一有结构标签的贡献者 EMPA（770 条）研究的是卤化物钙钛矿和金属氮化物
- 两大贡献者 LBNL（70,012 条）和 INT（19,796 条）的 phases 数组均为空，无结构标签
- 零候选记录通过所有筛选条件

新增审计资产：

- `configs/opxrd_ferroelectric_family_rules_v1.yaml`：19 个铁电材料家族匹配规则
- `configs/opxrd_feasibility_filters_v1.yaml`：晶系映射、质量筛选、Gate 配置
- `scripts/download_opxrd_metadata.py` 等 5 个审计脚本
- `tests/test_opxrd_*.py`：53 个测试全部通过
- `reports/opxrd_ferroelectric_feasibility_v1.md`：完整审计报告
- `reports/opxrd_ferroelectric_feasibility_v1_summary.json`：机器可读摘要

审计约束全部遵守：未加载模型、未执行真实谱推理、未修改 RRUFF-371、
未重新打开 JS/V9/simulated-Test 合约。

建议：按原设计继续推进 RRUFF-371 真实域适配路径。opXRD 保留为未来
更广泛 PXRD ML 研究的资源，但不适用于铁电陶瓷域。

