# XRD Robustness V9-T：当前工程交接

**交接状态日期：2026-08-01**  
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

## 十轮实验状态

五组 paired seeds、每组 Dynamic ERM 与 JS lambda=60，共十次运行，已全部
完成。训练 seeds 为 `20260711` 至 `20260715`，evaluation seed 固定为
`20260720`。

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

## 必须保留的诊断风险

seed `20260714` 的 worst-class F1 delta 为 `-0.061139`，其余四组为正。
因此不能写成“JS 对每个 seed、每个类别都一致改善”。下一阶段需要定位：

1. 哪个 crystal system 形成 worst class；
2. 该下降来自哪个 in-range condition；
3. 是否与 epoch 30 的 selected checkpoint 有关；
4. 在不重新选模型、不重新调 lambda 的前提下如何呈现该限制。

该异常不改变预注册 primary OOD conclusion，但必须进入论文 limitation 和
secondary diagnostic。

## 当前进程与产物

- ten-run 已结束；
- 当前没有需要继续恢复的 ten-run；
- 不应重复启动相同十轮矩阵；
- 不应重新选择 seed；
- 不应继续搜索 lambda；
- checkpoint、outputs、generated spectra 和 caches 不进入 Git。

仓库中的 summary 只记录结果与哈希，不替代本地完整训练产物。

## 访问边界

以下资源仍锁定：

- simulated Test；
- real XRD；
- real-domain adaptation；
- V10；
- 任何新的 Validation-guided method selection。

本次 summary 明确记录：

- `simulated_test_used = false`；
- `real_xrd_used = false`；
- `lambda_retuned = false`；
- `seed_excluded_posthoc = false`。

任何后续 Codex/GPT 会话不得把本次结果描述为 Test、sim-to-real 或真实实验
验证。

## 下一阶段的正确顺序

1. 先编写 simulated-Test preregistration / authorization 文件；
2. 冻结 evaluation checkpoint rule、指标、随机性与输出目录；
3. 做 read-only preflight，确认 Test 尚未被访问；
4. 用户明确授权后，进行一次性 simulated-Test evaluation；
5. 生成审计与结果报告后停止；
6. 再单独设计 real-XRD external validation。

在新的 Test 合同完成并获得明确授权前，不得执行 Test 命令。

## 新会话读取顺序

1. `AGENTS.md`
2. `00_project_context/CURRENT_STATE.md`
3. 本文件
4. `reports/v9_resnet_js_ten_run_results_20260801.md`
5. `reports/v9_resnet_js_ten_run_summary.json`
6. `configs/v9_resnet_js_ten_run.preregistered.json`
7. `configs/v9_resnet_js_ten_run.authorization.json`

## 当前明确下一动作

当前不是继续训练。当前动作是：

> 起草并审查 one-shot simulated-Test evaluation contract；在获得新的明确
> 授权前保持 Test 和 real XRD 锁定。
