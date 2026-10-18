# PXRD AutoLab：自动化科研执行与可审计证据流水线（2026-10-18）

**状态：PROPOSED / ARCHITECTURE & DELIVERY CONTRACT / NOT_IMPLEMENTED / NO_AUTOMATED_RUNS。** 本文记录拟建工程，不宣称已完成自动调度、无人值守实验、图表或双周报告；不修改已冻结的 V9 研究。本文的自动化范围必须服从 [AGENTS.md](../AGENTS.md) 的证据优先级与科研诚信要求。

**发起背景与科学目标：** 用户在确定“尽量前置完成科研，双周真实汇报，同时推进课程、硕士申请与 GRE”的时间策略后，提出能否建立自动科研流。要自动化的是**执行与证据整理**，不是让 AI 自由重定义科研问题。首个实际用例是 [铁电陶瓷前向重构 Loss 候选计划](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)：借鉴 PQ-Net 参数回归、DRNets 物理重构思想，比较 **A = supervised PXRD parameter inversion** 和 **B = 相同 NN + differentiable forward reconstruction loss**。在有据可查的已知单相候选与可靠 forward 上做小 pilot；材料家族待合作学长确认。

## 1. 首先区分「实验自动化」与「自主科研」

- **V1 / 本期核心：可复现自动执行**：人工签署任务配置 → 自动检查 → 生成模拟数据 → 运行公平 A/B → 分析 → 产出图表与证据报告 → 提交供人审查。固定协议内可以无人值守运行，外部状态仍需实际配置。
- **V2 / 后续：受控复盘建议**：读取结果提出*候选*下一步实验，**不得未经授权自行修改科学问题、测试集、预算、损失函数或搜索空间并继续无限训练**。用户决定是否批准新增版本。
- **明确非目标**：全自主发论文、自动做出正面科研结论、自动模拟学长真实样品、跨所有材料体系自动学习、全套多相 Rietveld 工作站、没有已连接 GPU/调度器仍保证后台运行。

## 2. 系统分工（解耦，最简先行）

```text
User / Researcher
  └── reviewed protocol.yaml + approval (Gate A)
        │
        ▼
Work / Codex [build, audit, prepare PR, review summaries; not an always-on runner]
        │
        ▼
GitHub repository [source + protocol + CI checks; no bulky training data]
        │
        ▼
Runner on authorized GPU machine [local CLI, queue/scheduler if actually available]
  validate schema ─> audit split/CIF ─> forward numerical gate (Gate B)
        │
        ▼
  synthesize/resolve dataset ─> paired A/B train ─> evaluate ─> figures
        │
        ▼
  immutable run manifest + raw metrics/logs/checkpoint locations
        │
        ▼
  report generator ─> Markdown + 4-page biweekly outline + draft PPT figures
        │
        ▼
User reviews outcome and scientific interpretation (Gate C)
        │
        ▼
Optional next experiment: new reviewed config + new run_id
```

**运行现实边界：** GitHub Actions 负责 lint/tests/schema/small CPU smoke，不假定 Actions 免费 GPU，也不把训练 checkpoint 推到 Git。Work 的浏览器/云电脑与实验 GPU 主机是否连接须事先核实；**Work 一次性做工程与报告编制**和**持续在线训练调度**不是同一服务。可先本机/台式机显式运行一条命令，工作站确有 scheduler 时再实现定时、队列和断点恢复。远程访问、重试与通知只有连接/凭据/权限到位才能真实启用。

## 3. 最小可维护代码形态（名称仅建议，实际以仓库约束为准）

```text
pxrd_autolab/                            # 新隔离模块，绝不侵入冻结 V9
  configs/
    forward_ab_smoke.yaml               # 只能运行少量模拟数据
    forward_ab_pilot.yaml               # 需要 Gate 通过后签署
  src/pxrd_autolab/
    config.py                           # schema / immutable protocol hash
    dataset.py                          # cached simulator + split manifest
    gates.py                            # CIF/physics/gradient/split/budget
    run.py                              # DAG / finite state machine
    trainer.py                          # paired A/B runner; reuse code
    evaluate.py                         # separate validation/test
    summarize.py                        # metrics, figures, report
  tests/                                 # smoke, failure injection, reproducibility
  README.md
docs/
  PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md
runs/                                    # generated local/object-store only, gitignored
  <run_id>/
    manifest.json
    config_frozen.yaml
    environment.json
    audit.json
    train/{A,B}/...                     # seeds, logs, checkpoint *paths*
    metrics/{validation,test}.json
    figures/
    report.md
    biweekly_brief.md
```

**技术栈：** Python + PyTorch + 现有模拟/forward + `pytest` + 机器可读 YAML/JSON + `matplotlib`；先用本地 CSV/JSON 管理实验（最低依赖），规模上来再考虑 MLflow。无需首版就装 W&B、多智能体平台、消息队列、复杂数据库或 K8s。

**单命令目标（设计示例，当前尚不存在）：**

```bash
python -m pxrd_autolab.run --config pxrd_autolab/configs/forward_ab_smoke.yaml
```

任务必须具有 `--dry-run`、`--resume`、`--max-steps` 或相当预算闸门；实际 CLI 由实现与测试决定，不能把本段命令误认为已成功运行。

## 4. 数据合同、状态机与自动关卡

**每次 run 的身份：** `run_id`, UTC start/end, Git commit, code dirty status, config hash, dataset/split manifest hashes, CIF provenance, generator version & physical settings, environment/pip/driver/torch/CUDA, deterministic seeds, compute budget, A/B model init pairing, optimizer schedule, resource use, artifact checksums, evaluation role, exception trace。

**状态机（建议）：**
`CREATED -> CONFIG_VALIDATED -> PHYSICS_PASS -> SPLIT_PASS -> READY -> RUNNING -> EVALUATED -> REPORTED -> AWAITING_REVIEW -> APPROVED/ARCHIVED`；
任意步骤可去 `BLOCKED`/`FAILED`，不得掩盖失败继续下一步。
- **Gate A · 人工锁协议**：问题、A/B 唯一变量、可调 `lambda_recon` 的验证集规则、单相有效域、成本上限、数据角色、测试集锁定；必要时把学长材料待确认标记 `UNKNOWN`。
- **Gate B · 自动 fail-closed 检查**：CIF/相候选有来源；forward 的 Bragg 位置/单位与结构因子适用性正确；autograd vs finite differences；物理参数可辨识性；split 的母结构/原型重复与近重复审计；GPU/cost/timeout 上限；固定 test 不参与训练、模型选择或阈值设计。旧 `xrd_inversion` 四方单相数值 PASS **不能**替新铁电相或混相承诺 Gate PASS。独立 renderer holdout 的冻结边界照旧。
- **Gate C · 人审 scientific claim**：A/B 的独立物理参数 MAE、重构误差、耗时和收敛/初始化效益；失败/差结果与残差并列，不能由 AI 选择性隐藏；实验域非常少时明确 `CASE_STUDY_ONLY`。只有审核后可将结果标为适合论文主张的 evidence。

**失败恢复：** 保留失败状态和日志；同一 `run_id` 仅可恢复中断且不改变 config/split/代码签名，任何科学配置变化产生**新** `run_id`；测试集结果不能作为触发新自动超参搜索的反馈。训练时间、磁盘和最大实验数均设硬预算。

## 5. 工程拆解：按价值顺序交给 Work/Codex

### P0（首个 PR，预计 2–4 个集中开发日；估计非承诺）
1. **先审计而非造新框架**：复用 `xrd_inversion` numerics、`xrd_robustness` ResNet/data generation/训练逻辑，标注冻结边界；检查目前是否已有实际可调用 A/B 模块和已有运行脚本。
2. **配置 + run manifest + 状态机**：一个 smoke 配置，可靠 fail-closed 处理；检查参数变化时必须创建新 run ID；保存原始日志和失败记录。
3. **以 mock/stub 回归数据跑通 execution DAG 的本地 CPU smoke**：只证明管线执行/审计/报告可复现，不得包装成科学发现。
4. **最小报告器**：消费真实 metrics.json，绘制 A/B 指标表和损失曲线（不存在指标就显示 UNKNOWN/NOT_RUN），生成 `report.md` 与 `biweekly_brief.md`；任何图注明 run_id 与数据角色。
5. **GitHub Actions**：只跑 config schema、unit tests、短 CPU smoke；PR 审查后合并。

**P0 验收：** 用单条命令真实执行配置校验、受控 smoke、产出报告；故意注入梯度 Gate 不通过/缺文件/超预算时**确实停止**；重复运行不会静默覆盖先前结果；生成物可由 run_id 对应到 Git commit、配置 hash；运行文档与失败记录可以复现。

### P1（第二个 PR；满足物理 Gate 才进入）
- 替换 mock 为**有可靠 CIF/forward 的限定单相模拟任务**；复现普通监督参数回归 A；接入可微 forward reconstruction B。
- 使用**相同 backbone、同一数据拆分、相同计算预算、可追溯 seeds**，只比较 `lambda_recon=0` 与事先选择的非零候选；少量 pilot，拒绝借由自动大搜索“刷”有利结论。
- 自动计算参数 MAE、谱图重构误差、训练/推理时间、失败数量，生成叠加谱和残差图；确保真实 scientific values 来自文件，而不是语言模型生成。
- 若学长材料未定，本阶段仅称 `METHOD_PILOT` 或 `ENGINEERING_SMOKE`，不能称“真实铁电陶瓷效果已证明”。

**P1 验收：** 至少一次实际 paired A/B smoke/pilot 完整重跑，报告数字可由 `metrics.json` 逐项重建；故意失败场景不被吞掉；资源消耗有界。

### P2（第三个 PR；必要时才做）
- 对接真正可用的桌面 GPU scheduler/队列，若条件允许设置断点续跑、显式重试和运行结束通知；必须核实 Worker 是否持续在线及数据权限。
- 双周汇报器从**已完成有证据的 runs**制作 4 页草稿：目标与协议、A/B 数据、失败/诊断、下一步待确认事项。**不把汇报自动发给学长**，需本人审稿发送。
- 可提供 `proposed_next_experiments.md` 作为建议，但不授权 agent 自己执行。
- 存储管理：检查 run 所需原始产物本地留存、必要数据保留期和备份/校验；Git 只追踪小型 manifest/报告/源代码。

## 6. 协作安全与资源策略

- **GitHub**：独立分支 `feat/pxrd-autolab-v1` + PR，禁止自动直推受保护科研结果；保留冻结 V9 配置、结果、checkpoint 和已归档 NO-GO，更新 `CURRENT_STATE`、`PROJECT_HISTORY`（如科学决策变化）以及相应实验协议。
- **代码执行**：研究仓库内容可读取，但不得对外泄露私有 CIF、样品元数据、凭据或实验谱；GitHub Actions secrets / GPU access token 均需最小权限，绝不存进配置或报告。Work 与外部算力的连接必须单独验证。
- **评价真实性**：报告生成器不能给缺失指标补数字、不能依靠样例图声称 A/B 显著提升；不把模拟内同一 Forward 的重构改善冒充真实域性能。
- **协作**：用户保持科研假设和最终发表口径控制；学长确认材料、仪器和精修适配；Work/Codex 实现和复盘代码，自动系统执行记录但不能代替科学判断。
- **与申请节奏兼容**：一次 smoke/pilot 完成后可提早进行科学分析与写作，双周如实汇报真实完成状态；不为了“每次有新结果”增跑不必要实验。

## 7. 首先做什么（今天即可启动的唯一工程工单）

让 Work/Codex 在新分支**只完成 P0**，不要它“一口气全自动训练发论文”：
- 读 `AGENTS.md`、最新 commits、`CURRENT_STATE`、该计划、Forward 报告和当前模拟器，做 1 页现状/复用矩阵；
- 用本地可执行的 config/manifest/run_id/state machine 构建小型真实 smoke，不要要求 GPU；
- 验证假数据、失败状态、复跑、报告都正确；
- 提交 PR 并交付可执行命令、真实测试日志与缺口清单。

**P0 完成后先审核，才进入 P1 的科学 A/B。** 这条线是科研服务工程，不能与“新研究已完成”混淆。

## 8. 思路变迁记录

2026-10-18 初步想做全面 AI 预精修平台（多家族、相概率、两相共存） → 回到参照 PQ-Net/DRNets 的**一项 Forward Loss 干预** → 主动把科研前置、双周诚实沟通以腾出申请 GRE 时间 → 再提出把执行链条自动化。此次自动科研流并非新的研究方向，也不恢复此前因数据或物理风险而搁置的复杂功能；它服务于确定的单项研究对照。**记录此处为 proposal，不得伪装已运行的自动科研系统。**
