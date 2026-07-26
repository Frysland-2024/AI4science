# XRD Robustness V9-T：跨 Codex 账号与台式机完整交接

> **2026-07-26 parent-structure split override (latest and authoritative):**
> The chemistry-anonymous Wyckoff-family-disjoint split is retired. The active
> split unit is one parent structure, randomly assigned 70/15/15 with
> crystal-system stratification and seed `20260726`. Every derived clean,
> weak, strong, ID, and OOD pattern inherits its parent's split. The current
> manifest SHA-256 is
> `B9D3B72E42EA0FD549DAE34425FF61D2D650D5DD7FE6F337D747CB952CF43293`.
> Old-split results and checkpoints are invalid. The remaining six old-split
> runs are cancelled; new-split tuning is `0/7` and restarts at experiment 1
> from step zero. The restart is authorized; the authoritative Python 3.11.9
> runtime is available and the Train-only candidate-grid Gate passed on this
> exact split without Validation/Test access. The change was committed and
> pushed as `9eeb972d45574c9b6d49a34d0914879bc8133288`; the registered serial queue
> was then launched from
> `reports/v9_method_transfer_tuning_plan_parent_structure_split_v1.json`.
> Experiment 1, `ordinary_dynamic_augmentation__tuning_seed_20260710`, is
> active from optimizer step zero and is writing its run contracts and
> Validation-only manifests under
> `outputs/v9_method_transfer_tuning_parent_structure_split_v1/`. Registry
> completion remains `0/7` until this run finishes. Test, formal 15-run,
> real-XRD, real adaptation, and V10 remain locked.

> **2026-07-26 paused-after-first state (superseded by split reset):**
> The first run, `ordinary_dynamic_augmentation__tuning_seed_20260710`,
> completed via early stopping at epoch 80 / step 49,280. The selected best
> checkpoint is epoch 70 / step 43,120 with mean single-factor Validation-OOD
> Macro-F1 `0.3300474407481531` and Validation-ID Macro-F1
> `0.3875303685641823`. Results SHA-256 is
> `80C48FF483CA08E4AA567281F1C76F38153E4369DC53889651B4775CD277D7DB`.
> The suspended launchers were terminated; no trainer or candidate-2 output
> exists. The scheduler registry remains `0/7` until a later explicitly
> authorized serial relaunch ingests the completed first result. Keep the
> remaining six candidates unstarted and do not run `tune-select`.

> **2026-07-26 10-epoch Validation override (latest and authoritative):**
> The user replaced the initial 5-epoch / patience-4 schedule with Validation
> every 10 epochs / 6,160 optimizer steps and patience 2. The effective
> no-improvement window remains 20 epochs. The first superseded run was stopped
> at epoch 14 / step 8,624. Its isolated output directory was moved to the
> Windows Recycle Bin on the user's explicit authorization on 2026-07-26; the
> source path is absent and the run is neither resumable nor countable. Restart
> all seven candidates from optimizer step 0 in
> `outputs/v9_method_transfer_tuning_100e_10epoch_patience2`.
> Maximum epochs/steps, minimum epoch 50, monitor, min_delta, best+last
> checkpoints, tie-breakers, hardware profile and all data/Test boundaries are
> unchanged.

> **2026-07-26 100-epoch early-stopping retuning override (authoritative):**
> The user has authorized a fresh optimizer-step-0 rerun of the complete frozen
> seven-candidate Validation-only grid. The new fixed maximum is 100 epochs /
> 61,600 optimizer steps; Validation runs every 5 epochs / 3,080 steps;
> `min_epochs=50`; the monitor is mean single-factor Validation-OOD Macro-F1
> with `mode=max`, `min_delta=0.001`, and patience 4 Validation checks.
> Save both `best.ckpt` and `last.ckpt`. Primary-score ties within `min_delta`
> are resolved by higher Validation-ID Macro-F1 and then the earlier epoch.
> The complete grid restarts from step 0 in
> `outputs/v9_method_transfer_tuning_100e_early_stopping`; do not resume or
> overwrite the historical 50-epoch tuning outputs. The registered laptop
> profile remains one run at a time with 16 workers / 16 prefetched batches,
> eager BF16, TF32, fused AdamW, pinned memory, and non-blocking H2D. The prior
> 50-epoch selection is historical fixed-endpoint evidence only. After 7/7,
> run the new selection audit and stop. Do not start the 15-run formal stage,
> simulated Test, real XRD, real adaptation, or V10.

> **2026-07-26 convergence-audit override:** The seven completed tuning runs
> are an internally fair fixed-budget comparison at 30,650 optimizer steps, but
> they do not prove convergence by epoch 50. Each canonical history contains
> only one Validation evaluation at epoch 50 because
> `validation_interval_steps=30650`, and each run retains only `last.ckpt`;
> therefore best epoch, late Validation slope, epoch-50-versus-best, and
> overfitting are not recoverable. This was operationally intentional rather
> than a hidden logging failure: `fairness.same_checkpoint_rule` is explicitly
> `last_fixed_budget_checkpoint`, and the trainer does not evaluate before the
> final interval. No hidden TensorBoard/event log, metrics CSV, earlier
> Validation row, or historical epoch checkpoint exists. The final checkpoints
> do contain optimizer and RNG state for a separately authorized, validated
> future continuation, but they cannot reconstruct past epoch models. The
> contract is nevertheless semantically inconsistent:
> `evaluation.validation_role` still advertises early stopping and checkpoint
> selection, neither of which these runs implemented. Resolve this conflict
> before freezing any formal 15-run protocol. All seven late classification-objective
> slopes remain negative, with selected JS 3.0 at `-0.01438355` and selected
> Residual 2.0 at `-0.00700665` per 616 optimizer steps. Learning rate remains
> the original `1e-4` because no scheduler is configured. Treat
> `lambda_JS=3.0` and `lambda_res=2.0` as selected only at the frozen
> 30,650-step budget. Do not start or lengthen the 15-run formal comparison
> without a separate scientific decision; any new common budget requires
> revalidation of the complete candidate grid. The authoritative audit is
> `reports/v9_tuning_convergence_audit.json`.

> **2026-07-26 tuning-complete override:** The seven-run laptop
> Validation-only tuning stage is complete and audited. All seven registered
> runs finished 30,650 optimizer steps with 490,400 structure and 980,800
> spectrum exposures, 23,199 prediction rows, matching artifact hashes, common
> sampler/pair/parameter hashes, and locked Test boundaries. The repaired
> Residual lambda=0.2 prediction replay preserved checkpoint SHA-256
> `91e227dd1e7224c9551e065de681036e714b05584549c94544f3522232f20084`
> and matched its completed history metrics exactly. `tune-select` passed and
> selected `lambda_JS=3.0` and `lambda_res=2.0`; the authoritative report is
> `reports/v9_method_transfer_tuning_selection.json`. The queue is stopped and
> no training process remains. Do not start the 15-run comparison, simulated
> Test, real XRD, real adaptation, or V10 without separate explicit
> authorization.

> **2026-07-26 seven-run final-audit override:** All seven registered laptop
> Validation-only tuning runs completed their frozen 50-epoch, 30,650-step
> budgets and the queue exited with code 0. Final `tune-select` correctly
> stopped on two engineering-only recovery issues: tuning prediction rows use
> the producer's mode identity while the auditor expected the contract method
> ID, and the full-step recovery for Residual lambda=0.2 overwrote its
> prediction rows with an empty file after skipping the already-complete
> training loop. Evidence is preserved at
> `outputs/v9_method_transfer_tuning/failed_final_tuning_audit_evidence_20260726_1554`.
> The checkpoint, history metrics, Validation manifests, posthoc manifest,
> exposure counts, and sampler/pair/parameter hashes remain valid. The repair
> aligns the audit identity with the producer and requires deterministic
> prediction replay from the verified full-step checkpoint with exact metric
> agreement. Test, commit, and push the repair; regenerate only the lambda=0.2
> prediction artifact from that checkpoint; then rerun `tune-select`. Do not
> start the 15-run comparison, simulated Test, real XRD, real adaptation, or V10.

> **2026-07-26 run-5 second-recovery override:** The registered queue remains at 4/7. Residual lambda=0.2 completed all 50 epochs and 30,650 optimizer steps, but its first recovery exposed a second posthoc-only engineering defect after the invalid split-label repair: the regenerated Train probe persisted initial sampler rows without the deterministic training quality-gate retry policy, so replay rejected `mp-1147626` with `window_intensity_below_threshold`. The second traceback and regenerated manifest are preserved under `outputs/v9_method_transfer_tuning/failed_posthoc_recovery_evidence_20260726_143311`; no later run started. The follow-up repair builds the posthoc Train manifest with the same deterministic accepted-row renderer used by training, while preserving the frozen model/grid/seed/budget/completed exposure and all training hashes. Resume is authorized only from the same verified epoch-50 checkpoint after tests plus commit/push; finish this same run before runs 6-7. Formal 15-run, simulated Test, real XRD, real adaptation, and V10 remain locked.

> **2026-07-26 最新执行覆盖（优先于下文旧台式机迁移说明）：** 用户已明确授权在当前 LENOVO 82WM 笔记本上执行且仅执行 V9-T 的 7-run Validation tuning。当前注册目标为 Ryzen 9 7945HX、RTX 4060 Laptop GPU、32 GB RAM；新硬件合同是 `configs/hardware.v9.laptop.7945hx_4060.json`。新鲜运行时和有界 BF16 审计已通过，单负载峰值约 1822 MB；双进程负载虽无 OOM，但聚合吞吐仅为串行的 0.838，因此注册调度为严格单 run。首轮实时采样确认原 8-worker 动态谱图预取会周期性饿住 GPU；严格等价扫描覆盖 8/8、12/12、16/16、20/20、24/24，最终冻结最快的 16-worker/16-batch 窗口。新鲜 128-batch 审计达到约 32.4 batch/s，且 manifest、材料顺序、参数、谱图、哈希和质量门计数逐项完全相同。由于本机缺少可工作的 Triton，`torch.compile` 探针产生 0 个 compiled graph，故笔记本合同显式关闭编译，保留 BF16、TF32、fused AdamW、pinned memory 和 non-blocking H2D。7-run 必须由注册启动器从 optimizer step 0 开始；15-run、simulated Test、real XRD、真实适配和 V10 均未获授权。下文“笔记本不训练/等待台式机授权”的旧说明仅作为历史迁移记录，不再代表当前 7-run 权限。

> **启动完整性补充：** 2026-07-26 首次启动在发现 `git_commit.txt` 错报“无 Git 仓库”后被主动终止且不计入 7-run。根因是训练器硬编码 unavailable，而真正的 Git 根位于父目录 `E:\AI4science`。部分目录已完整隔离为 `outputs/v9_method_transfer_tuning/aborted_provenance_probe_20260726_1147`，不得恢复或计数。训练器现通过 `git -C <project-root> rev-parse HEAD` 记录提交，并有父仓库回归测试；正式队列必须重新从 optimizer step 0 开始。

> **新账号必须从这里开始。** 本文件是接管入口，不是训练授权。先核验机器可读证据，再进行任何操作。

## 给下一个 Codex 的第一条指令（可直接复制）

```text
请先完整阅读 E:\AI4science\xrd_robustness\CODEX_HANDOFF.md，并把它作为接管入口。
随后只运行不含训练的交接核验、迁移核验、环境核验和台式机工程验收。
任何一步失败都必须停止并报告具体失败项；不得猜测、跳过或自动修改科学合同。
即使 desktop_readiness.json 显示 ready_for_explicit_tuning_authorization，也必须停下，等待我在台式机上重新明确授权，才能运行 tune-run。
不得恢复、复制或使用笔记本 checkpoint；完整 lambda 7-run 必须从 optimizer step 0 开始。
不得访问 simulated test 或 real test，也不得启动 15-run 正式实验，除非我分别重新明确授权。
```

## 0. 一页结论：现在究竟到哪一步

截至 2026-07-26，本项目的当前主线是 **V9-T：Algorithm Transfer for PXRD Robustness**。科学合同、数据划分、物理模拟范围、PAMPT-B3 主干、三种核心动态方法、公平性流审计、台式机硬件配置、迁移脚本和 7-run 计划均已建立。方法参数语义 Gate 与六候选 Train-only 梯度尺度 Gate 均已通过；JS `[0.3,3,30]`、Residual `[0.2,2,20]` 已在唯一一次人工修订后冻结。真实适配合同和确定性计划已经完成严格本地审计，但训练器仍未实现且执行锁关闭。V10 Train-only 诊断已形成负结果并冻结归档。7-run 尚未获得执行授权。

当前执行状态必须表述为：

- lambda 调参完成度：**0/7**；七条 run 全部是 `planned_not_started`。
- 7-run 只能生成计划供检查；`development_tuning.execution_enabled=false` 且 `development_tuning_execution_enabled=false`，不得执行。
- 活动训练进程：0。
- 活动 run registry：0 条记录。
- 活动 checkpoint：0。
- 活动 `results.json`：0。
- 活动 run 目录：0。
- 笔记本旧训练产物已经物理删除，不迁移、不恢复。
- 台式机采用冷启动：七条 run 全部从 **optimizer step 0** 开始。
- 笔记本允许单元测试、哈希审计、CUDA smoke test 和有界吞吐测试；不允许正式训练。
- 台式机首次启动脚本也只做工程验收，不包含训练命令。
- `ready_for_explicit_tuning_authorization` 仅表示工程门通过，不表示已获训练授权。
- 之前聊天中出现过“启动 7 次调参”，但用户随后明确暂停，并决定迁移到台式机重新开始。**最新意图优先：当前没有训练授权。**
- 15-run 正式实验、simulated test 和 real test 分别需要后续独立授权；lambda 调参授权不能外推到这些阶段。

机器可读零状态见：

- `outputs/v9_method_transfer_tuning/run_registry.json`
- `outputs/v9_method_transfer_tuning/desktop_restart_state.json`
- `reports/codex_account_handoff_manifest.json`
- `reports/codex_account_handoff_verification.json`

## 1. 证据优先级与失效规则

新账号不能依赖旧账号聊天记忆，也不能把本文件中的数字当作永不过期。判断当前状态时按以下顺序建立信任：

1. `configs/*.json` 中冻结的机器可读合同。
2. 当前源代码实现及其 SHA-256。
3. 与当前合同/代码哈希匹配的 JSON/CSV 审计报告。
4. 本文件和 `docs/*.md` 中的解释性文字。
5. 历史聊天、旧输出和 `archive/` 只可作为背景，不得覆盖当前合同。

若配置、代码、报告、迁移清单或本文互相冲突，必须：

1. 停止训练和测试集访问；
2. 指出冲突文件、字段和哈希；
3. 重新生成只读审计；
4. 修复冲突后重新验证；
5. 不得用“看起来应该没问题”替代证据。

本项目目录 `E:\AI4science\xrd_robustness` **没有独立 Git 元数据**，但它属于上级 Git 仓库 `E:\AI4science`。所有 `git status`、暂存、提交和推送都必须从该仓库根目录执行；只有在根目录实际运行 `git status --short --branch` 后才能报告 worktree 状态。根目录 `AGENTS.md` 规定：实际修改代码、配置或项目文档后，先运行相关测试或审计，只显式暂存本次任务文件，检查 staged diff 与秘密信息，再使用准确的英文提交说明并推送 `origin/main`。不得使用 `git reset --hard`、force push 或其他历史改写操作。当前科学可信性仍依赖配置、源文件、数据、缓存、计划、检查点和报告的 SHA-256 链。

便携版 `docs/CODEX_ACCOUNT_HANDOFF.docx` 是本文的派生阅读副本；根目录 Markdown 始终是文字权威源。当前 DOCX 已通过 ZIP/XML 结构、必备章节、表格和分页元素校验，也已由 Microsoft Word 成功打开并统计为 23 页；本笔记本缺少 LibreOffice，且 Word 的无界面 PDF 导出接口超时，因此未宣称逐页视觉渲染通过。该限制不影响 Markdown、JSON、CSV 和源文件的哈希迁移验证。

## 2. 新账号接管时的最短安全路径

在源笔记本上，或台式机已经完成 13.2 冻结环境创建后，在项目根目录执行：

```powershell
$ProjectRoot = 'E:\AI4science\xrd_robustness'
Set-Location $ProjectRoot
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'

& $Python -s scripts\verify_codex_account_handoff.py
& $Python -s scripts\verify_v9_desktop_migration.py --root $ProjectRoot
```

两个命令都必须返回 `pass`。它们不训练模型。如果交接核验失败，新账号必须停下，不得继续 bootstrap、首启或训练。

如果台式机尚未创建 `xrd_tools`，不得用普通 Python 强行运行完整交接核验；此时只按 13.1 执行纯文件迁移校验，然后创建冻结环境。

迁移到台式机后，桌面端还必须重新执行迁移 SHA-256 验证；源笔记本上的 `pass` 只能证明源文件内部一致，不能证明复制过程正确。

## 3. 研究问题与论文边界

核心研究问题是：

> 在母晶体结构、物理增广视图、模型架构、优化预算和评估面板严格匹配的条件下，显式建模同一晶体不同扰动视图之间的关系，能否比单纯增广监督更好地泛化到未见扰动和真实 PXRD 图谱？

当前论文只做 **跨领域算法迁移与 XRD 特定验证**，不声称发明新的通用机器学习理论。

论文方法递进是：

1. augmentation-only supervised learning；
2. cross-view prediction consistency；
3. difference-aware residual class decorrelation。

Dynamic/Paired ERM 是最强、最公平的动态增广基线和成对视图基础设施。动态增广本身不作为创新点。

Residual Class Decorrelation 是重点假设，但在获得直接、匹配的 Dynamic 和 JS 对照结果之前，不得预先宣称 Residual 更优。

结构化扰动不属于当前 V9-T：

- `structured_perturbation_in_scope = false`
- `structured_perturbation_status = archived`
- 未来 V10 的 simulator-supervised residual 研究已经延期，不得混入当前 7-run 或 15-run。

权威合同：`configs/algorithm.v9.method_transfer.json`。

## 4. 数据、划分与泄漏边界

权威数据根：`data/formal_14060`。

已退役的 family-aware 划分仅保留为历史记录；当前使用 parent-structure 随机分层划分：

| Split | 结构数 | 当前用途 |
|---|---:|---|
| Train | 9,842 | 训练和动态视图生成 |
| Validation | 2,109 | 已完成调参中的固定预算终点 lambda/开发 OOD 比较；没有中间 early stopping 证据 |
| Test | 2,109 | 当前锁定；不能用于调参或方法选择 |
| 合计 | 14,060 | 七晶系，结构 ID 唯一 |

关键文件：

- `configs/data.v9.method_transfer.structure_split.json`
- `data/formal_14060/manifests/split_manifest.json`
- `data/formal_14060/manifests/v9_method_transfer_validation.csv`
- `reports/v9_method_transfer_split_audit.json`

冻结审计确认：跨 split 的结构家族交叉数为 0，Train/Validation/Test ID 互斥。动态训练只允许读取 Train ID；Validation 和 Test 不得进入训练动态视图流。

`formal_14060` 反射峰缓存完整：14,060/14,060，失败数 0。峰缓存包含峰位、积分强度、hkl、多重性和倒易矢量等反射元数据。

### 4.1 本地 GTIIT 候选真实数据（未冻结、未授权）

2026-07-22 将一份 GTIIT 实验室资料归档到
`E:\AI4science\04_external_lab_data\GTIIT`。该顶层目录被 `.gitignore`
整体排除，不属于仓库执行依赖，也不得提交原始数据或含隐私的实验文档。

本地审计确认：XRD 相关内容共 543 个文件，其中有 237 个 RAW、228 个
TXT；224 个 TXT 可直接解析为严格递增二维光谱，218 组 RAW/TXT 具有相同
目录和文件名主干。原始导出记录有一个远端 XRD 文件夹未下载，且实验委托
文档普遍包含联系方式、地址、开票或账户类信息。完整本地说明、逐文件哈希和
文本谱审计见该目录的 `README.md`、`file_manifest.csv` 和
`xrd_text_profile.csv`。

这些文件当前只能视为候选真实仪器数据池，不能视为七晶系正式训练集、
Validation 或 real test。若以后获得单独授权，必须先去标识化并建立样品级
标签证据、批次隔离和 provenance manifest；本次归档不改变 simulated/real
test 锁定状态，也不授权用真实谱选择扰动范围、lambda、方法或 checkpoint。

## 5. 物理模拟器与输入谱图

每个母结构从同一份理想反射峰表在线生成两个独立扰动视图 `x1` 和 `x2`，两者标签相同。

模型输入网格：

- `2theta_min = 10.0°`
- `2theta_max = 80.0°`
- `step = 0.02°`
- 输入长度 = 3,501

当前五类物理扰动：

1. 全局 `2theta` 峰位偏移；
2. FWHM 峰宽展宽；
3. 平滑非负背景；
4. 泊松光子计数与可选电子读出噪声；
5. March-Dollase 择优取向。

背景和噪声必须始终作为两个物理效应描述：

```text
I_observed = I_peak + I_background + noise
```

择优取向先改变反射积分强度；背景添加到期望强度；随后采样计数噪声和电子噪声；最后裁剪并进行输入归一化。

真实仪器标定不是训练前置条件。扰动来源优先级必须保持可见：`literature_source`、`code_source`、`physics_basis`；真实仪器数据只有在用户明确批准时才能成为参数来源。

冻结模拟配置：`configs/simulation.v9.method_transfer.frozen.json`。

## 6. 当前模型架构：PAMPT-B3

完整名称可表述为：

> 物理模拟成对视图驱动的峰先验双分支 Transformer，加可插拔跨视图关系目标。

模型不是两个独立网络。`x1` 和 `x2` 两次调用同一套共享 PAMPT-B3 编码器与七分类头。

PAMPT-B3 内部：

1. 主信号支路使用 5、11、21 三种卷积核提取多尺度局部峰形；
2. 峰先验支路从原始谱图的一阶和二阶导数提取峰位、峰肩和峰形变化；
3. 两条支路都用重叠 Patch：patch size 16、stride 8；
4. 输入产生 437 个 Token；
5. embedding dimension 128；
6. 四个、四头注意力块，顺序为 `self -> guided -> self -> guided`；
7. 对编码 Token 做 mean pooling；
8. 线性分类头输出七晶系。

实测模型参数量为 1,419,660。实现入口：`src/xrd_robustness/models/xrd_pampt.py`。

## 7. 五种方法与七次 lambda 调参

完整方法族有五种：

| 合同 mode | 论文名称 | 角色 |
|---|---|---|
| `clean_erm` | Near-clean ERM | 参考方法；`clean_erm` 只是兼容名称 |
| `offline_erm` | Offline Physical Augmentation ERM | 参考方法 |
| `dynamic_erm` | Dynamic/Paired ERM | 最强匹配基线 |
| `dynamic_js` | JS Consistency | 候选方法 |
| `dynamic_residual` | Residual Class Decorrelation | 重点候选方法 |

当前 **7-run lambda tuning** 只包含 Dynamic、JS 和 Residual：

以下 run ID 是已冻结候选网格的计划模板，但 7-run 仍未获得执行授权；任何接管 agent 都不得据此启动训练。

1. `ordinary_dynamic_augmentation__tuning_seed_20260710`
2. `js_consistency_transfer__lambda_js_0p3__tuning_seed_20260710`
3. `js_consistency_transfer__lambda_js_3p0__tuning_seed_20260710`
4. `js_consistency_transfer__lambda_js_30p0__tuning_seed_20260710`
5. `residual_decorrelation_transfer__lambda_res_0p2__tuning_seed_20260710`
6. `residual_decorrelation_transfer__lambda_res_2p0__tuning_seed_20260710`
7. `residual_decorrelation_transfer__lambda_res_20p0__tuning_seed_20260710`

lambda 网格：

- `lambda_js = [0.3, 3.0, 30.0]`
- `lambda_res = [0.2, 2.0, 20.0]`
- Residual head depth = 1
- Residual warmup = 2 epochs
- Residual ramp = 3 epochs

共同训练预算：

- tuning seed = 20260710
- evaluation seed = 20260720
- epochs = 50
- steps per epoch = 616
- maximum optimizer steps = 30,650
- batch size = 16 个母结构
- 每结构两个视图，即每 step 32 张训练谱图
- evaluation batch size = 256

### 7.1 Dynamic/Paired ERM

```text
L = 0.5 * [CE(p1, y) + CE(p2, y)]
```

输入成对，但不显式约束两视图关系。

### 7.2 JS Consistency

```text
L = L_classification + lambda_js * JS(p1, p2)
```

约束同一晶体两个扰动视图的预测分布一致。

### 7.3 Residual Class Decorrelation

```text
r = abs(L2Norm(z1) - L2Norm(z2))
```

残差对视图顺序不变。每个 step 只做两次主干 forward：

1. Step A：对 `z1/z2` detach，训练残差分类头从 `r` 预测晶系；
2. Step B：冻结残差头参数但保留对输入的梯度，训练 PAMPT 最小化分类损失，并使残差头输出趋近七类均匀分布。

```text
L = L_classification + lambda_res * KL(q(class | r) || Uniform(7))
```

残差头只参与训练；正式推理只需 PAMPT 编码器和七分类头。

## 8. 公平性与可重放性合同

五种方法共享：

- 同一 Train 结构集合；
- 同一固定预算 sampler；
- 同一 deterministic epoch shuffle；
- 同一 batch 结构顺序；
- 同一 pair ID 顺序；
- 同一 optimizer-step 数；
- 同一结构暴露量和谱图暴露量；
- 同一验证面板；
- 同一最后固定预算 checkpoint 规则。

三个核心动态方法 `dynamic_erm`、`dynamic_js`、`dynamic_residual` 还共享完全相同的动态参数 pair hash。它们看到相同的 `x1/x2`，只改变学习目标。

当前流审计证据：

- optimizer steps：30,650
- structure exposures：490,400
- spectrum exposures：980,800
- unique train structures：9,842
- 每结构暴露次数：49 至 52
- batch 内动态参数行上限：32
- `8` 个预取 batch 下最大 live 动态参数行：256
- sampler hash：`6e1a4e6e46f59e913fc0165c41d8a584a1669514d70ec0814985a34c4ee6430c`
- pair schedule hash：`99c033bddbdfd3bd442388201c11863047e83f2012eebfd0781aac94a4d932a0`
- 核心动态 parameter pair hash：`46149a5170c51f67ec9a05b04978520eece0221d741f4478f402eb5eb1e07e07`

权威报告：`reports/v9_training_stream_preflight_audit.json`。

## 9. 已经修复的工程问题

以下问题不再是待办：

1. **606,267,200 行动态 manifest 膨胀**：旧设计等价于 `9842 * 50 * 616 * 2` 行；当前只为实际 batch/预取窗口生成参数，最大 live 行为 256。
2. **训练 batch 没有 shuffle**：当前每个 epoch 使用训练 seed 控制的 SHA-256 key sort；所有方法共享 sampler/pair schedule hash。
3. **每 step CUDA scalar 同步**：高频 `.item()` 已移除，GPU 标量在 epoch 级汇总后才同步到 CPU。
4. **peak table 重复加载**：启用预取时主进程不再加载全部训练 peak table；worker 按稳定分片惰性加载静态 shard。
5. **Clean/Offline 串行渲染**：Near-clean、Offline 和三个动态方法均已接入确定性多进程预取。
6. **CPU/GPU 传输阻塞**：启用 pinned memory 和 non-blocking H2D。
7. **低精度和编译未利用**：已接入 BF16 AMP、TF32、`torch.compile/Inductor`、fused AdamW，并保留显式 fallback 与运行来源记录。
8. **评估逐样本前向**：注册评估 batch 256；台式机需在 128/256/512 中重新验收。
9. **单 run 调度**：注册两个并发 run 的有界调度器，但必须先通过台式机双进程显存和聚合吞吐门。

这些修复通过代码合同和轻量审计证明；真正台式机吞吐仍必须在目标机器重新测量，不能用笔记本数值替代。

## 10. 台式机目标硬件与注册配置

用户报告的目标：

- CPU：AMD Ryzen 5 9600X，6 核 12 线程
- GPU：用户称“4070 Ti S，16 GB”；当前合理解释为 NVIDIA GeForce RTX 4070 Ti SUPER
- VRAM：16 GB
- 系统内存：用户尚未在本交接中提供实测值；配置要求至少 32 GB
- 项目和 peak cache 推荐放 NVMe SSD

GPU 精确型号、可用显存、系统内存和逻辑线程必须由台式机上的 `nvidia-smi`、PyTorch 和系统探针确认，不得只按用户口头型号自动放行。

当前注册配置：

### 单 run

- 8 个预取 worker
- 每 worker 1 个原生线程
- 8 个 batch 预取窗口
- 主进程 intra-op 2，inter-op 1
- training batch 16
- evaluation batch 256

### 两个并发 run

- 注册 `run_concurrency = 2`
- 每条并发 run 分配 4 个预取 worker
- 两条合计仍为 8 个 worker
- 第七条尾任务恢复 8 个 worker
- 若台式机双进程门失败，安全 fallback 是 `--max-parallel-runs 1`

### GPU

- `float32_matmul_precision = high`
- TF32 matmul/cudnn 开启
- cuDNN benchmark 开启
- cuDNN deterministic 开启
- BF16 AMP 开启，无 GradScaler，允许明确记录的 FP32 fallback
- `torch.compile(backend='inductor', mode='default')`
- fused AdamW
- `zero_grad(set_to_none=True)`

两个并发 run 必须满足：

- 聚合峰值显存低于 15,360 MiB；
- 聚合吞吐不低于串行的 95%；
- 数值、梯度和损失等价门通过；
- 检测到真实编译图执行；仅发生 eager fallback 不算编译门通过。

权威配置：`configs/hardware.v9.desktop.9600x_4070tis.json`。

## 11. 笔记本与 XRD-clean 环境的准确角色

笔记本 GPU 是 NVIDIA GeForce RTX 4060 Laptop GPU，约 8 GB VRAM。它不是目标台式机，因此笔记本预取、BF16、显存和吞吐结果只能作为工程证据，不能冻结台式机运行配置。

环境边界：

- `E:\AI4science\.venvs\xrd_tools\Scripts\python.exe`：当前 CUDA 训练/审计解释器，Python 3.11.9，PyTorch 2.5.1+cu124。
- `.conda\envs\xrd-clean`：CPU PyTorch 测试环境；可用于轻量 CPU 单元测试，但不是正式训练环境，也不迁移到台式机。
- 不复制任何 `.venv`/`.conda` 目录；台式机重新创建环境。
- `reports/v9_laptop_environment_reference.txt` 只是包参考，不是要求原样复制整个笔记本环境。

## 12. 迁移清单与复制边界

源笔记本先运行：

```powershell
Set-Location E:\AI4science\xrd_robustness
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'

& $Python -s scripts\prepare_codex_account_handoff.py
& $Python -s scripts\prepare_v9_desktop_migration.py
& $Python -s scripts\verify_codex_account_handoff.py
& $Python -s scripts\verify_v9_desktop_migration.py --root E:\AI4science\xrd_robustness
```

必须满足：

- handoff = `handoff_ready_for_copy`
- handoff verification = `pass`
- migration = `ready_for_copy`
- migration verification = `pass`
- active training process / registry / checkpoint / result / run directory 都为 0

复制前先 dry run：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\copy_v9_desktop_payload.ps1 `
  -DestinationRoot 'E:\AI4science\xrd_robustness' -WhatIf
```

确认目标路径后再去掉 `-WhatIf`。复制器不会删除目标文件，只复制 CSV 清单中的文件和迁移控制文件，并拒绝 `..` 越界路径。

迁移排除：

- Python/Conda 虚拟环境；
- `__pycache__`、`.pytest_cache`、`*.pyc`、`*.pyo`、`*.tmp`；
- 活动范围外的旧输出；
- 旧 checkpoint 和 optimizer state；
- `archive/` 不是当前执行依赖。

## 13. 台式机第一次接管：按顺序执行

### 13.1 复制后立即核验

如果台式机上的 `xrd_tools` 环境还没有创建，先使用任意可用的 Python 3.11，只执行不依赖 PyTorch 的迁移文件校验：

```powershell
Set-Location E:\AI4science\xrd_robustness
python -s scripts\verify_v9_desktop_migration.py --root E:\AI4science\xrd_robustness
```

完成 13.2 的冻结环境创建后，再用 `xrd_tools` 执行完整的跨账号语义校验：

```powershell
Set-Location E:\AI4science\xrd_robustness
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'

& $Python -s scripts\verify_v9_desktop_migration.py --root E:\AI4science\xrd_robustness
& $Python -s scripts\verify_codex_account_handoff.py
```

### 13.2 创建台式机环境

先安装：

- 与 CUDA PyTorch 兼容的 NVIDIA 驱动；
- Python 3.11.9；
- Visual Studio 2022 C++ Build Tools，x64 C++ workload。

然后：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\bootstrap_v9_desktop_environment.ps1
```

要求：Python 3.11.9、PyTorch 2.5.1+cu124、CUDA runtime 12.4、CUDA available、BF16 supported、`pip check`、MSVC 工具链和目标 GPU/显存全部通过。

### 13.3 运行完整单元测试

```powershell
$env:PYTHONPATH = 'E:\AI4science\xrd_robustness\src'
& $Python -s -m unittest discover -s tests -p 'test_*.py' -v
```

任何失败都必须先修复，再继续首启工程门。

### 13.4 只查看首启计划

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1 -PlanOnly
```

必须看到 `formal_training_commands=0`。`PlanOnly` 不应写报告或执行测试。

### 13.5 执行无训练首启验收

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\desktop_first_boot_v9.ps1
```

它依次执行：

1. 迁移逐文件验证；
2. runtime/environment 现场验证；
3. V9-T contract preflight；
4. 目标硬件识别；
5. 8x8 单 run 预取等价审计；
6. 4x8 并发单元预取等价审计；
7. 完整 worker/window 候选矩阵；
8. pinned/non-blocking H2D 审计；
9. 评估 batch 128/256/512 审计；
10. Dynamic/JS/Residual 的 FP32、BF16、compiled BF16 数值与吞吐门；
11. 两进程显存与聚合吞吐门；
12. 生成 `reports/desktop_acceptance/desktop_readiness.json`。

这个脚本没有 `tune-run`，不会创建训练 checkpoint。

### 13.6 强制停止点

如果 readiness 状态不是 `ready_for_explicit_tuning_authorization`：修复失败门并重跑，不能训练。

如果状态是 `ready_for_explicit_tuning_authorization`：**仍然停止。** 向用户报告门禁证据，等待用户在台式机上重新明确授权完整 lambda 7-run。

## 14. 训练授权矩阵

| 操作 | 当前是否授权 | 说明 |
|---|---|---|
| 阅读代码/合同/报告 | 是 | 只读 |
| 单元测试 | 是 | 不创建训练 checkpoint |
| 数据、哈希、流、公平性审计 | 是 | 不访问 Test 内容 |
| CUDA smoke/吞吐工程测试 | 是 | 有界、非正式训练 |
| 台式机环境 bootstrap | 是，迁移接管阶段 | 不训练 |
| 台式机 first boot acceptance | 是，迁移接管阶段 | 不训练 |
| 7-run `tune-run` | **否** | 必须在台式机上获得新的明确授权 |
| 15-run 正式实验 | **否** | 需要 lambda 冻结后再单独授权 |
| simulated test | **否** | 需要方法冻结后单独授权 |
| real test | **否** | 需要真实数据 manifest 冻结和单独授权 |

任何“请继续”“按计划做”都只能在当前已授权阶段内解释，不能自动跨越到下一个训练或测试阶段。

## 15. 用户未来明确授权 7-run 后的唯一启动方式

在收到台式机上的新授权之后，先重新生成当前计划：

```powershell
& $Python -s scripts\run_v9_method_transfer.py preflight
& $Python -s scripts\run_v9_method_transfer.py tune-plan
& $Python -s scripts\run_v9_method_transfer.py final-preflight
& $Python -s scripts\verify_codex_account_handoff.py
```

再次确认：

- preflight scientific status passed；
- desktop runtime ready；
- 七条 run 仍为 `planned_not_started`；
- registry/checkpoint/result/run directory 全为 0；
- simulated/real test 仍锁定；
- plan、contract、trainer、launcher 和缓存哈希当前一致。

然后只能使用注册 launcher，不要手工拼七条训练命令：

```powershell
& $Python -s scripts\run_v9_method_transfer.py tune-run --confirm-development-tuning
```

默认使用通过台式机门禁的注册双 run 调度器。若双 run 门失败或用户选择保守串行：

```powershell
& $Python -s scripts\run_v9_method_transfer.py tune-run `
  --confirm-development-tuning --max-parallel-runs 1
```

`--confirm-development-tuning` 只是命令级防误触参数，不能替代用户授权。

## 16. 7-run 完成后的阶段边界

七次调参完成后：

1. 验证七条结果、checkpoint、sampler/pair/parameter hash 和失败状态；
2. 运行 `tune-select`，按冻结 Validation 规则选择 lambda；
3. 主要指标：mean single-factor OOD macro-F1；
4. 相对 Dynamic baseline 的 ID drop 最大允许 0.01；
5. 并列时选择较小 lambda；
6. 写入并冻结 tuning selection artifact；
7. 到此停止。

不得自动开始 15-run。15-run 是五方法乘三个 seed 的正式 development experiment，必须单独授权。

15-run 完成并冻结方法之后仍不得自动访问 simulated test。simulated test 完成后也不得自动访问 real test。真实 XRD 只用于最终外部验证，不用于扰动范围、lambda、方法或 checkpoint 选择。

## 17. 故障与恢复规则

### 17.1 首启工程门失败

- 保留失败 JSON 和控制台日志；
- 报告准确的 failed check；
- 只修复该工程问题；
- 不放宽科学公平性合同；
- 重新运行对应审计和最终 readiness；
- 不训练。

### 17.2 某条 tuning run 失败

- launcher 的策略是让当前并发 pair 收尾后停止调度新任务；
- 不覆盖已有结果；
- 检查 run registry 和该 run 的 runtime provenance；
- 只在相同合同、相同 run ID、相同 sampler/pair schedule 下恢复；
- 当前交接初始状态不允许使用任何笔记本 checkpoint；
- 训练开始后的 checkpoint 恢复策略必须验证 `global_step`、sampler contract hash、pair schedule 和源文件哈希。

### 17.3 `torch.compile` 失败

- 可以记录 eager fallback 以便诊断；
- 但台式机 acceptance 要求检测到真实 compiled graph；
- 若长期无法执行 compiled graph，不得把 fallback 伪报为编译门通过；
- 可以退回串行或 FP32 进行诊断，但正式配置变化必须重新审计并记录。

### 17.4 显存不足

- 不得随意改变训练 batch 16，因为它属于暴露量和公平性合同；
- 优先把 run concurrency 从 2 降为 1；
- 再检查评估 batch、编译缓存和预取设置；
- 任何影响训练视图、optimizer steps 或 pair schedule 的变化都必须拒绝。

## 18. 胡皓天架构只作为对照背景

此前阅读过胡皓天的海报和 KBS 论文：

命名消歧：用户在聊天里曾写“胡浩天”，但本地海报/论文文件和已核读资料使用“胡皓天”；新账号检索本地资产时应使用“胡皓天”，不得把两种写法误当成两套架构。

- 海报：`E:\AI4science\01_literature\4f936fcce3e6bcd362ddb656afaac913.png`
- 论文：`E:\AI4science\01_literature\literature_zones\03_consistency_ssl_physical_regularization\胡皓天KBS.pdf`
- 论文主题：Hyperspectral single-source domain generalization via structured data simulation and domain-disparity decorrelation。

其 SD3Net 使用 SDSG（SALS + MSVS）生成域、MRCE 编码器和残差类别去相关。与本项目的共同思想是“同样本跨扰动视图 + 差异中的类别去相关”。关键区别：

- 胡皓天：学习型/结构化数据模拟 + MRCE CNN；
- 本项目：非学习型物理 PXRD 模拟器 + 峰先验 PAMPT Transformer；
- 本项目残差是归一化表征绝对差，对视图顺序不变；
- 本项目还独立比较 JS Consistency；
- 当前 V9-T 不包含结构化动态生成器。

参数溯源已经按论文原文更正：式 (16)–(17) 定义 `L_cls=lambda_1 L_sd+lambda_2 L_sim` 和 `L_total=L_cls+lambda_3 L_decorr`；Table 5 在三个数据集上都列 `lambda_3=1`，并在 `[0.1,1]` 内联合检查 `lambda_1/lambda_2`。Fig. 12 又单列一个约在 `1e-4` 最优的 regularization parameter `lambda`，但正文没有明确解释它与 `lambda_3=1` 的关系。新账号不得把 `1e-4` 误称为该论文的 `lambda_3`，更不得把它作为 V9-T `lambda_res` 的数值依据。该论文对本项目只提供机制存在性、相对损失比例、敏感性分析和模块消融的先例。

这些外部文献文件不属于 `xrd_robustness` 执行依赖。即使没有迁移原图和 PDF，本节也足以避免新账号误以为当前模型就是 SD3Net。

## 19. 已归档、已删除或不得复活的内容

- 旧笔记本 V9 调参输出已经删除并验证不存在。
- 不存在可迁移的旧 optimizer state 或 checkpoint。
- `archive/v9_pre_unified_validation_20260716` 中的旧二分 Validation 清单、中止输出和旧脚本已于 2026-07-19 物理删除；平台可能保留空目录骨架，但其中不得重新放入历史内容。
- 旧的两个 Validation 子集已经废止；当前只使用统一 Validation。
- V8 StructuredDynamicStrategy 已归档，不得偷偷重新放入 V9-T。
- V10 simulator-supervised representation learning 延期，不得混入本论文。
- `xrd-clean` 不是台式机训练环境，不需要迁移。
- 全工作区清理分类、已删除项目和平台阻止项见 `reports/ai4science_cleanup_inventory_20260719.json`。

## 20. 关键文件地图

### 第一次必须读

1. `CODEX_HANDOFF.md`
2. `reports/codex_account_handoff_manifest.json`
3. `configs/algorithm.v9.method_transfer.json`
4. `docs/V9_METHOD_TRANSFER_ENGINEERING.md`
5. `docs/V9_DESKTOP_MIGRATION_HANDOFF.md`
6. `configs/hardware.v9.desktop.9600x_4070tis.json`
7. `reports/v9_training_stream_preflight_audit.json`
8. `reports/v9_method_transfer_tuning_plan.json`
9. `reports/v9_method_transfer_final_lock_audit.json`

### 架构与训练实现

- `src/xrd_robustness/models/xrd_pampt.py`
- `src/xrd_robustness/training/objectives.py`
- `src/xrd_robustness/training_stream.py`
- `src/xrd_robustness/training_prefetch.py`
- `src/xrd_robustness/view_manifest.py`
- `scripts/train_v7.py`
- `scripts/run_v9_method_transfer.py`

### 迁移与台式机门禁

- `scripts/prepare_v9_desktop_migration.py`
- `scripts/copy_v9_desktop_payload.ps1`
- `scripts/verify_v9_desktop_migration.py`
- `scripts/bootstrap_v9_desktop_environment.ps1`
- `scripts/desktop_first_boot_v9.ps1`
- `scripts/audit_v9_desktop_readiness.py`

### 交接本身

- `scripts/prepare_codex_account_handoff.py`
- `scripts/verify_codex_account_handoff.py`
- `docs/CODEX_ACCOUNT_HANDOFF.docx`
- `reports/codex_account_handoff_manifest.json`
- `reports/codex_account_handoff_verification.json`

## 21. 接管完成的定义

只有同时满足以下条件，才能说“新账号已经正确接管”，但仍不能说“训练已授权”：

1. 新账号完整阅读本文件；
2. 交接 artifact ledger 的大小和 SHA-256 全部匹配；
3. 迁移 payload 在台式机逐文件验证通过；
4. 台式机环境和硬件现场探针通过；
5. 全量单元测试通过；
6. 预取、H2D、评估 batch、BF16、compile、双 run 门通过；
7. `desktop_readiness.json` 为 `ready_for_explicit_tuning_authorization`；
8. registry/checkpoint/result/run directory 仍为 0；
9. simulated test 和 real test 仍锁定；
10. 新账号向用户报告证据并停下等待训练授权。

这十条是跨账号、跨机器交接的最终验收边界。

## 16. 2026-07-22 笔记本阶段新增闭环证据

以下内容优先于本文件中仍把 resume integration test 写成“未完成”的旧段落；旧段落保留作为历史上下文。

### 已关闭的工程 Gate

- `reports/v9_resume_determinism_audit.json`：真实 reflection cache、冻结 Train renderer、CUDA 小模型；连续运行与 epoch 0 后中断/恢复在后续 material ID、parameter pair、next loss、global step、stream hash/snapshot 和最终模型 SHA256 上全部一致，12/12 PASS。
- checkpoint 现在直接保存 `training_stream_audit` 与 `training_sampler_contract_hash`；修复了 `map_location=cuda` 后 CPU RNG state 被放到 CUDA 的恢复错误。
- `reports/v9_method_semantics_audit.json`：22/22 PASS；覆盖零权重退化、JS 对称/非负/batch mean、Residual 熵方向与数值稳定性、head/backbone 梯度流及 2-epoch warmup/3-epoch ramp。
- `reports/v9_loss_gradient_scale_audit.json`：正式 PAMPT-B3、14 个七类平衡 Train 结构、128 optimizer steps（前 64 burn-in）；该历史数值审计通过但处于 chance state，不能决定网格。
- `reports/v9_candidate_grid_gate.json`：从 epoch 0 重建 learned state 并直接测量六个冻结候选，当前范围 Gate 通过；未使用 Validation/Test/real data，未选择最终 λ。
- `configs/v9_method_parameter_governance.json`：绑定语义、chance-state、learned-state 与 candidate-grid Gate 哈希，冻结 head/warmup/ramp、一次性范围修订及 tuning Gate。

### 新的统计执行契约

- 每个正式 run 结束时必须生成并在 `results.json` 中哈希绑定 `prediction_rows.jsonl`。
- 每行至少包含 seed、method ID、profile、material ID、family ID、label、prediction、probabilities。
- 正式比较必须在 seed 内对母结构/family cluster 做配对 bootstrap，再跨全部注册 seed 汇总。
- 禁止恢复旧的“只对三个 seed 数值反复 bootstrap”实现。
- 声称 Residual 优于 JS 时，必须直接报告 `Residual - JS` 与 parent-structure-level 95% CI。

### 预先准备的非训练资产

- `scripts/analyze_v9_results.py`：验证逐谱 schema，输出分类/ECE/worst-group/confusion 和 family bootstrap 对比表。
- `scripts/analyze_v9_mechanisms.py`：只消费冻结 feature arrays，输出 Residual/feature norm、variance、effective rank、class separation 等；不得把 Residual 直接命名为物理测量变量。
- `scripts/audit_v9_real_test_preprocessing.py`：只审计锁定 contract/未来 manifest；当前报告明确 `model_loaded=false`、`spectra_loaded=false`、`real_test_used=false`。
- 论文骨架、结果/绘图模板和审稿人攻击清单已经建立，不能提前填入正向结论。

### 当前新增阻塞项

正式 B3 审计显示：当前六个候选的中位“加权辅助 backbone 梯度/分类 backbone 梯度”全部低于 1%；`lambda_js=1.0` 为 `7.489e-5`，`lambda_res=1.0` 为 `7.610e-4`。诊断平衡中心约为 JS `9.745e4`、Residual `2.950e4`，跨度过大，不能由接管 agent 自动写成正式网格。必须先复核短 Train-only 轨迹和 influence bands 的代表性，再在接触 Validation 前进行最多一次整体对数平移，重跑两份审计并冻结哈希。不得用 Validation、Test 或真实谱驱动这次修订。

### 状态锁保持不变

- tuning：**0/7**；formal development：**0/15**；
- active process/checkpoint/result/run directory：0；
- simulated Test、real test：未访问且锁定；
- 笔记本 checkpoint：不具权威性，不复制、不恢复；
- 台式机 first boot 即使工程检查通过，也必须同时看到 `candidate_range_frozen_for_validation=true` 和用户明确授权才可执行 7-run；当前前者已满足，后者仍不满足。

### 迁移演练证据

- `reports/v9_desktop_migration_manifest.json` 已在所有本轮代码、配置、文档和审计产物完成后重新生成，状态为 `ready_for_copy`。
- payload 的权威文件数、字节数与 stream SHA-256 只读取 `reports/v9_desktop_migration_manifest.json`，避免在 payload 自身文件中抄录会随源码变化失效的聚合值。
- `reports/v9_desktop_migration_verification.json` 在源机器逐文件验证全部清单项：missing=0、size mismatch=0、hash mismatch=0；具体数量只以该报告为准。
- `copy_v9_desktop_payload.ps1 -WhatIf` 只完成复制演练，没有写入目标目录；`desktop_first_boot_v9.ps1 -PlanOnly` 验证了 11 个验收步骤，并确认 formal training commands=0。
- 这些证据只证明源端 payload 自洽和脚本可规划，不替代台式机现场验收，也不构成 7-run 授权。

## 22. 跨项目边界：Raman 不替代当前 XRD 主线

- 本地 Raman mapping 只有两个独立样品文件，虽然每个文件包含 26 x 26 x 829 的空间—光谱立方体，但 1,352 条像素谱不是 1,352 个独立样本。
- 禁止按像素随机切分 Train/Test 后把结果解释为掺杂泛化；样品、批次、日期、仪器和空间背景会共同泄漏。
- 当前 MATLAB 原型仅覆盖读取、选峰/区间积分和空间绘图，没有 ML 假设、样品级划分、baseline 或外部验证。
- Raman 只作为未来第二项目的数据种子；补齐多个独立样品/批次、标签证据和样品级外部验证后，才考虑 spatial-spectral self-supervision、unmixing/segmentation 或 anomaly detection。
- 当前唯一主研究仍为 XRD V9-T。本节不授权 Raman 开发，不改变 XRD 方法矩阵、λ 候选、0/7、0/15 或 Test 锁。

## 23. 方法权重诊断更新：不得把梯度倒数写成正式 λ

本节是 chance-state 诊断的历史记录；候选范围的当前权威状态以第 25 节为准。

`reports/v9_loss_gradient_scale_audit.json` 已升级为 schema v3 并在 CUDA
上重跑。新 agent 必须优先采用本节，旧章节中“下一步直接整体平移网格”
的表述已经被本轮证据取代。

### 新审计实际测量了什么

- 正式 PAMPT-B3、14 个七类平衡 Train 结构、128 optimizer steps；
- 128 个不重复的确定性配对 batch，不再循环旧报告中的 8 个 batch；
- early=0–41、middle=42–84、late=85–127，仅是审计轨迹三等分，
  不是正式 50-epoch 训练的早中晚；
- raw `L_cls/L_JS/L_res`、三项未加权 encoder/backbone gradient norm、
  prediction JS、normalized feature residual norm、residual-head entropy；
- residual probe 每次 Step A 更新前后的 loss/accuracy/entropy；
- PAMPT `head.*` 已从 encoder/backbone gradient norm 中排除，同时在 trace
  中保留 full-model/task-head norm；
- Validation、simulated Test、real data、候选专属训练和 λ 选择全部为 0/false。

### 决定性的 late-stage 结果

- 分类准确率 `11.96%`，低于七分类随机 `14.29%`；
- `L_cls=1.9499`，与均匀交叉熵 `ln(7)=1.94591` 一致；
- 两视图 top-1 agreement `99.34%`，prediction JS 约 `2.97e-7`；
- residual probe pre-update accuracy `14.62%`，CE `1.94613`；
- residual-head entropy 约 `1.94566`，几乎是最大熵；
- classification learning signal 与 residual probe competence 均为
  `not_demonstrated`。

所以 JS 小首先是两个未学会任务的预测本来就相同；Residual 小首先与
probe 尚未学会类别同时发生。倒数得到的 JS `2.874e5`、Residual
`2.556e4` 只叫 diagnostic gradient compensation factors，不是理论权重、
网格提案或可自动采用的值。

### 当前 Gate 与接管规则

- JS `{0.1,0.3,1.0}`、Residual `{0.01,0.1,1.0}` 原样保留且未冻结；
- 不得执行一次性范围平移，不得启动 7-run；
- 下一项科学工作是设计 Train-only milestone audit：分类主干先明显优于
  随机，再测 JS；Residual 还必须先证明 pre-update probe 高于描述性随机
  阈值，再解释 confusion gradient；
- 这项更长诊断尚未授权执行，也不能使用 Validation/Test/real XRD；
- tuning `0/7`、formal development `0/15`、candidate-range Gate blocked、
  gradient-compensation interpretation Gate blocked；
- 台式机 first boot 与方法参数 Gate 仍是两个独立阻塞项。

复现当前短诊断的命令（只复现现有证据，不解决里程碑阻塞）：

```powershell
$env:PYTHONPATH='E:/AI4science/xrd_robustness/src'
E:/AI4science/.venvs/xrd_tools/Scripts/python.exe scripts/audit_v9_loss_and_gradient_scale.py --device cuda --steps 128 --burn-in-steps 64 --output reports/v9_loss_gradient_scale_audit.json
```

## 24. 2026-07-22 learned-state Train-only audit（取代“尚未授权”的旧阻塞描述）

本节记录人工修订前的 learned-state 证据；修订后的当前权威状态以第 25 节为准。

用户已明确授权并完成更长的 Train-only 诊断，但**没有授权任何候选训练、
Validation tuning 或 7-run**。权威报告为：

- `reports/v9_learned_state_scale_audit.json`
- schema：`v9-learned-state-scale-audit-v1`
- SHA-256：`384982FE0C3D0E125F4D8AD96637FBFFCBBD9D76823CEEF3C01C296AA8BE62CE`
- 脚本：`scripts/audit_v9_learned_state_scale.py`
- 脚本 SHA-256：`C500C4F2516B214B757981EC2911A448BAAD07E715A58B19F19E821D849FC81A`

### 诊断合同与数据边界

- 一个 PAMPT-B3、classification-only Dynamic/Paired ERM 轨迹；
- 完整 9,842 Train 结构，5 epochs，batch size 16；
- 主干 AdamW：`lr=1e-4`、`weight_decay=1e-4`，两个动态 Train 视图；
- milestone 固定为 epoch 1、3、5；
- probe calibration、probe audit、scale audit 各为 700 个七类平衡 Train
  结构，三者严格互斥；
- probe 是一层 `ResidualClassifier`，使用 detached residual，固定 50
  epochs、AdamW `lr=1e-3`、`weight_decay=0`；该独立诊断学习率用于避免
  underfit-probe 假阴性，不会改变 backbone；
- `validation_used=false`、`simulated_test_used=false`、`real_xrd_used=false`；
- `checkpoint_written=false`、`formal_training_runs_started=0`、
  `candidate_specific_training_performed=false`；
- 实际设备是 RTX 4060 Laptop GPU；报告不作目标台式机性能声明。

### 结果

| Epoch | Backbone learning Gate | Probe Gate | Probe audit accuracy | Probe Macro-F1 | Raw JS median | JS/cls grad median | Residual/cls grad median |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | not demonstrated | not demonstrated | 14.86% | 8.33% | `5.95e-7` | `1.00e-5` | `1.70e-4` |
| 3 | pass | pass | 22.43% | 16.55% | `0.00593` | `0.02945` | `0.07034` |
| 5 | pass | pass | 32.57% | 28.92% | `0.01862` | `0.05898` | `0.09738` |

Epoch 5 的主干训练 CE 为 1.62189、两视图准确率为 31.02%；probe audit
CE 为 1.85059。结论是：主干学习后，JS 不再接近零；当前 symmetric
normalized residual 确实含有可被独立 Train probe 读取的晶系信息。因此
JS 与 Residual 都有实际信号，旧 128-step 几万级倒数仍然作废。

主机意外重启后，本报告使用相同固定 seed 从 epoch 0 完整重跑；此前仅
存在于内存的模型、优化器和缓存状态均未恢复，也没有断点恢复声明。

### 当前 Gate 与接管规则

- 旧 `reports/v9_loss_gradient_scale_audit.json` 继续保留，只能称为
  initialization/chance-state evidence；
- 新报告只让 learned-state 梯度进入 `eligible_for_human_review`，不产生
  自动 grid proposal；
- JS `[0.1,0.3,1.0]`、Residual `[0.01,0.1,1.0]` 原样保留为待审候选；
- 在该历史 checkpoint，`candidate_range_frozen_for_validation=false`；两个
  tuning execution switches 继续关闭；
- tuning 仍为 0/7，formal development 仍为 0/15；Test 与 real test 锁定；
- 下一项科学动作是用户/研究者人工判断是否根据 learned-state 比率使用
  唯一一次 pre-Validation 整体对数范围修订；任何 agent 不得自动作出该
  决定，也不得直接启动训练。

复现 learned-state 诊断（约 4 分钟，RTX 4060 Laptop GPU；不得误当正式
训练命令）：

```powershell
E:/AI4science/.venvs/xrd_tools/Scripts/python.exe scripts/audit_v9_learned_state_scale.py --device cuda --prefetch-workers 8 --prefetch-batches 8 --output reports/v9_learned_state_scale_audit.json
```

当前无授权训练命令。下一条安全验证命令：

```powershell
E:/AI4science/.venvs/xrd_tools/Scripts/python.exe -m unittest tests.test_v9_learned_state_scale_audit -v
```

## 25. 2026-07-22 唯一一次候选网格修订与 Train-only 冻结 Gate

用户已明确批准并消耗唯一一次 pre-Validation 网格修订：

- JS：`[0.3, 3.0, 30.0]`；
- Residual：`[0.2, 2.0, 20.0]`。

机器治理阈值为 negligible `<0.01`、weak `[0.01,0.1)`、material
non-dominant `[0.1,1)`、dominant `>=1`。Dynamic/Paired ERM 继续作为
`lambda=0` 锚点，因此计划仍为 1 ERM + 3 JS + 3 Residual，共 7 run。

权威 Gate 报告：

- `reports/v9_candidate_grid_gate.json`
- schema：`v9-candidate-grid-gate-v1`
- SHA-256：`E59EE2A56906757C82238CB47D520B1D74D690455EA907540AFFF59EA2E8A947`
- 脚本：`scripts/audit_v9_candidate_grid_gate.py`
- 脚本 SHA-256：`60D71F8E4B27F8ECFBD6C7067D16275B197059C2F9C5A749D38D9DE6E3290069`

该 Gate 没有磁盘 checkpoint 可恢复，因此从相同固定 seed、epoch 0 重建
五 epoch、完整 9,842 Train 结构的 classification-only Dynamic/Paired ERM
PAMPT-B3。probe-train、probe-audit、scale-audit 仍为三个互斥的 700
结构 Train 子集；probe 为一层头、`lr=1e-3`、50 epochs。六个候选分别
对加权辅助目标和合并目标执行真实 autograd，不是仅用 `lambda=1` 线性外推。

| 方法 | λ | 中位辅助/分类 backbone 梯度比 | 实测 band |
|---|---:|---:|---|
| JS | 0.3 | 0.02283 | weak |
| JS | 3.0 | 0.22842 | material non-dominant |
| JS | 30.0 | 2.28533 | dominant |
| Residual | 0.2 | 0.02581 | weak |
| Residual | 2.0 | 0.25854 | material non-dominant |
| Residual | 20.0 | 2.58715 | dominant |

主干 learned-state Gate 和互斥 residual-probe Gate 再次通过；六候选的有限性、
分类与辅助梯度存在性、band 匹配、中位分类下降方向、BF16 梯度和一致性与
单 batch 50 倍失控保护全部通过。审计工具在冻结前透明修正了 BF16 容差和
一个与 dominant 开区间冲突的内部 p90 上限；网格、Train 数据和四段影响
阈值均未改变，完整理由写入治理 JSON、报告和 PROJECT_JOURNEY。

当前接管规则：

- `candidate_range_frozen_for_validation=true`；
- `completed_range_revisions=1`，不得再次修改候选范围；
- `development_tuning.execution_enabled=false`；
- `execution_policy.development_tuning_execution_enabled=false`；
- 7-run 仍为 `0/7`，Validation tuning 未授权；
- simulated Test 与 real XRD 继续锁定；
- 迁移与预检证据已经刷新；下一动作仅是等待用户单独授权 7-run。

重跑 Gate 会重新训练约 4 分钟且不写 checkpoint：

```powershell
E:/AI4science/.venvs/xrd_tools/Scripts/python.exe scripts/audit_v9_candidate_grid_gate.py --device cuda --prefetch-workers 8 --prefetch-batches 8 --output reports/v9_candidate_grid_gate.json
```

当前安全验证命令（不会启动训练）：

```powershell
$env:PYTHONPATH='src'; E:/AI4science/.venvs/xrd_tools/Scripts/python.exe -m unittest tests.test_v9_candidate_grid_gate tests.test_method_transfer -v
```

## 26. 2026-07-25 V10 Train-only 诊断闭环与归档

V10 已完成受限的 Train-only 诊断链并冻结归档，当前 V9-T 主线不变。

权威归档入口：

```text
docs/V10_MODULE_ARCHIVE_AND_FUTURE_DIRECTIONS.md
```

证据链：

- `reports/v10_p0_measurement_information_gate.json`
  - P0 premise Gate：`PASS`;
  - SHA-256：`22EF5EFCFD63ABEA3AFE1848B0F7E1B12C3849B006B1FE091FE5918AD5AC2CAB`;
- `reports/v10_train_only_pilot.json`
  - Pilot v1：`HOLD`;
  - SHA-256：`C3F1B64A8022B011F0997085A7D4F42A56CD28C95EAFBAF2B62263F7D326B1DB`;
- `reports/v10_train_only_pilot_v2.json`
  - Pilot v2：`PARTIAL`;
  - SHA-256：`86762B1B0AD74C32AB8E7BA8A8E1A6BC366F2F0C8F6A245AE4856CE1B47B4228`.

Pilot v2 的 learned-state Gate 通过：Train-only controlled-panel accuracy
为 `31.43%`、CE 为 `1.7016`，高于七分类随机基线。V10 保留了测量家族、
背景、展宽和噪声强度信息，且相对匹配 ERM 的分类 CE 代价仅
`+0.00394`；但 signed residual 与 symmetric residual 的独立晶系泄漏
分别比匹配 V9 高 `+0.01429` 和 `+0.03714` accuracy。

当前结论不是“测量监督无效”，而是无条件 simulator supervision 增加了
residual 的总信息量，没有完成测量信息与晶体语义的解耦。该问题按架构级
失败处理，不能通过继续 epoch 或标量权重搜索自动推进。

V10 只有在 V9 validation 完成、新 Train-only 协议预注册且用户重新明确
批准科学方向后才能重启。7-run 仍为 `0/7`，15-run 仍为 `0/15`，
Validation、simulated Test 和 real test 的锁均未改变。

## 27. 2026-07-26 本地文献与外部资源清点

opXRD/SIMPOD 新增归档已经在本地完成解压、哈希核验和科学角色分类。
Git-safe 权威索引为：

```text
00_project_context/LITERATURE_LOCAL_RESOURCE_INDEX.md
```

本地资源边界：

- opXRD 论文与补充材料归入核心 XRD 扰动/相识别文献区；
- SIMPOD 论文归入 XRD AI/晶体结构 benchmark 文献区；
- opXRD Zenodo 数据解压为 92,552 个 JSON、3,612,139,779 bytes，和 ZIP
  payload 完全一致；
- opXRD 与 SIMPOD 源码解压为第三方参考树，不是 V9 runtime dependency；
- 原 ZIP 保留为 provenance/recovery 副本；
- PDF、数据、ZIP 和第三方源码树均保持 Git ignored；
- 所有新资源当前 V9 role 为 `none`，不授权训练、调参、validation 或 test。

## 28. 真实适配审计产物同步

两个不加载模型或谱图、也不执行 final real test 的机器可读产物已纳入交接：

- `reports/v9_real_adaptation_contract_audit.json`
  - status：`locked_contract_and_manifests_pass`;
  - SHA-256：`B598B3E843C429B34F27DF3B2AB5143093ED3FA14298AFD736DEAC3C3611F84E`;
- `reports/v9_real_adaptation_plan.json`
  - status：`planned_not_started_execution_disabled`;
  - SHA-256：`C97C02395CE8BA7C44245159F10B0A22A370DEEE9782FBCF3EC17FA38A4FCE4E`.

合同审计确认 70 个样品、`21/14/35` 角色、七类各 `3/2/5`、七个 episode
平衡且 final-test 隔离。计划仍只是 189 个 primary candidate run、63 个
selection group 和 9 个 zero-shot evaluation 的确定性描述；执行器继续
拒绝运行。
