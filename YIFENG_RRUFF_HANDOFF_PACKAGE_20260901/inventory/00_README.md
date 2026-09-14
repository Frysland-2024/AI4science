# Yifeng / cuifa01 — RRUFF real-domain personal handoff audit

## 结论先行

本目录是 **Stage 1 inventory**，不是交接包本体。审计已覆盖 `E:\AI4science` 当前工作树、ignored/untracked 文件、可达 Git 全历史、被删除/改名文件、`.workbuddy` 以及项目内明确相关的 DeepSeek 记录。**没有复制 RRUFF 资产、没有重跑实验、没有修改源文件、没有提交或 push。**

身份边界按本轮确认处理：**cuifa01 = 共同作者 Yifeng**。当前贡献归属的权威入口是 `docs/PXRD_RRUFF_COLLABORATOR_MODULE_PROVENANCE.md`；Git author 仅用于定位时间线，不用于推断实际贡献。

核心发现：

- Yifeng 负责的完整 RRUFF 研究线可恢复为 13 个阶段，见 `RRUFF_TIMELINE.md`。
- 当前最关键的本地原始层是 `rruff371` 的正确 v2 split、150 条运行级 metrics、34,650 条 prediction 记录，以及相关 runner/audit 脚本。
- 四个本地 RRUFF 数据包合计 **279,240,403 bytes（约 266.3 MiB）**，本身可以装进 1 GB；但 RRUFF 原始数据的合同明确没有声明再分发权，真正复制前需做私人协作者交接/许可复核。
- 10 个共享主线 pretrained checkpoints 合计 **1,561,824,960 bytes（约 1.455 GiB）**，单独就超过 1 GB；它们是共同项目依赖，不是 Yifeng 独立模块，Stage 1 仅登记。
- 未找到原始 DeepSeek 会话导出、session ID、逐轮 prompt/response 或 commit-to-session 映射；只找到当前 provenance、未完成模板和项目摘要型代理记录。
- 原始 preregistration 承诺的 `rruff301_episode_plan.csv` / 原始 support-ID 落盘记录未找到。Git 历史中的 retrospective replay plan 是 **事后重建**，不能冒充原始预注册 episode plan。

## 审计快照与并发变化

- 会话最初观察到的 HEAD：`db45664dc336c834453aac5d1dee9411f94509ef`
- 本 inventory 采用的最终仓库快照：`93da7d9f5cb3b2389439243d636bba6dcd5f68f9`；最后一次影响 RRUFF inventory 的 commit 是 `c977ba355989f96ac2da13d31950daa0bb48d715`。
- `origin/main` 在封版验收时同为 `93da7d9f5cb3b2389439243d636bba6dcd5f68f9`。`c977ba3..93da7d9` 只新增无关的 `xrd_inversion` factorization pilot，未改变本清单中的 RRUFF 资产。
- 任务期间有外部并发提交推进 HEAD；本审计没有制造这些提交。`PXRD_RRUFF_COLLABORATOR_MODULE_PROVENANCE.md` 是当前权威文件，但它形成于 2026-09-01，不能伪装成 7–8 月同时期原始记录。
- `docs/RRUFF真实域_科研叙事.md` 在审计期间由外部流程更新并于 commit `c977ba3` 纳入 main；CSV 固定的是最终观测工作树版：17,147 bytes，SHA-256 `B20130373C5F9A2254B8768F2FC7B4BD99B74F397A78289D4DAF888DC1566425`，mtime 2026-09-01 22:44:10。
- `docs/RRUFF_LINE_COAUTHOR_CONTRIBUTION.md` 与 `docs/RRUFF_COLLABORATOR_RECORD.txt` 曾以 untracked 文件被本审计读取和取证，随后由外部流程移除，且没有可达 Git blob；现归入 `MISSING_AND_UNKNOWN`，保留其当时大小/SHA 作为瞬时观察证据。

## 分类方法

CSV 使用两个正交维度，避免把“重要性”和“保存位置”混为一谈：

- `priority`：`MUST_TAKE`、`SHOULD_TAKE`、`REFERENCE_ONLY`。
- `category`：`ALREADY_ON_GITHUB`、`LOCAL_ONLY`、`MISSING_AND_UNKNOWN`。

所以一个文件可以同时是 `MUST_TAKE + ALREADY_ON_GITHUB`：它对 Yifeng 很重要，但已由 GitHub 当前 main 或可达历史完整保存，不必制造重复副本。

科学证据状态写在 `notes`：

- `CURRENT_AUTHORITATIVE`：当前可直接报告/复核。
- `HISTORICAL_VALID`：历史链条有效，但不是当前执行合同。
- `EXPLORATORY`：用于提出问题或假设，不能升级成 confirmatory 结论。
- `INVALIDATED`：明确作废，只能用于解释失败与纠错。
- `DRAFT` / `STALE_DRAFT`：叙事草稿；后者含已被当前权威边界推翻的表述。

目录行的 `TREE_SHA256` 定义为：相对路径统一用 `/`，按 ordinal 排序，单文件 SHA-256 写成小写十六进制，逐行以 UTF-8 编码 `relative_path|size|file_sha256\n`，再对完整字节串计算 SHA-256。CSV 同时列了目录集合和其中的关键文件，**不能把所有 CSV 行的 size 直接相加**。

`safe_to_copy` 口径：

- `YES`：从科研/权属角度可进入待审交接包；仍需在 Stage 2 复核目标路径。
- `PRIVATE_ONLY_AFTER_LICENSE_REVIEW`：只考虑共同作者私人科研归档，先核对 RRUFF 引用与再分发条件；不可据此公开发布。
- `NO_REFERENCE_ONLY`：只登记依赖，不放入个人模块包。
- `NO_UNTIL_REVIEW`：内容过时、存在归属或科学表述风险。

## 证据层级

1. 当前权威：provenance、当前公开结果 JSON、composition audit。
2. 当前本地原始层：ignored 的 split/manifest/raw runs/predictions、冻结数据包、runner/audit 脚本。
3. Git 历史层：决策、protocol、preregistration、RRUFF-70 exploratory、v1 invalidation、corrected v2、representation/fix-break、evidence freeze。
4. 叙事/代理记录：`PROJECT_HISTORY.md`、本地 `PROJECT_JOURNEY.md`、`.workbuddy`、申请材料草稿。
5. 缺失层：原始 DeepSeek sessions、原始 support-ID plan、完整命令/runtime 绑定、v1 raw outputs。

## 你最后要求的 8 个答案

### 1. Yifeng 最少必须带走哪些东西？

最小研究自证包应包含：当前 provenance；13 阶段时间线；当前公开结果与 composition audit；本地 `rruff371` 的 contract、master manifest、正确 split、split manifest、raw runs、predictions、fixed200 与 zero-shot；v1 错误 split；`run_rruff301_confirmatory.py`、`fix_rruff301_split.py`、`analyze_representation.py`；RRUFF-70 frozen exploratory 结果；关键历史 prereg/v1/v2/representation/evidence-freeze blobs；本地 `PROJECT_JOURNEY.md`、申请叙事交接稿和 RRUFF 相关 `.workbuddy` 摘要。精确清单见 `MUST_TAKE.md` 与 CSV。

### 2. 如果只能带 1 GB，优先带哪些？

先带所有文档、JSON/CSV、scripts、manifests/audits，再带 `rruff_pipeline_test`、`rruff70`、`rruff371`；如果许可复核通过，也可把 `rruff350` 一并纳入。四个数据包总计约 266.3 MiB，连同本地记录仍远低于 1 GB。不要带 1.455 GiB checkpoints；只带其 5.3 KiB metadata/hash 文件并记录共享存放位置。

### 3. 哪些资产 GitHub 已经有，不必重复？

当前 provenance、`RRUFF真实域_科研叙事.md`、当前结果 JSON、composition audit、`RESULTS.md`、`MANUSCRIPT.md`、`README.md`、`PROJECT_HISTORY.md` 已在 main。7–8 月的决策、protocol、RRUFF-70、prereg、v1/v2、representation 和 evidence-freeze 文件虽已从当前树删除，但其 blobs 仍位于 `origin/main` 可达历史。详见 `ALREADY_ON_GITHUB.md`。

### 4. 哪些是凡电脑上唯一的一份？

以“当前项目范围内、精确 SHA 未被任何可达 Git tree 保存”为准：四个 ignored RRUFF 数据包；RRUFF-301 raw runs/predictions/correct split；本地 runner/fix/analysis 脚本；ignored 的 `PROJECT_JOURNEY.md` 后续版、申请交接稿与 `.workbuddy` 摘要；当前 untracked 的 `分工陈述_申请材料.md`；两组 RRUFF PPT 临时 QA 束。这里只能证明“本项目 Git 未保存”，不能证明世界上不存在其他副本。审计中途消失的两份 untracked 草稿另列为缺失，不能再称为当前本地副本。

### 5. 哪些资产对“证明贡献”最重要？

第一是当前 provenance；第二是有时间戳的 decision/prereg/v1 invalidation/v2/representation/evidence-freeze 历史；第三是本地 raw runs、predictions、split、runner 和 audit 脚本形成的执行链；第四是 `.workbuddy` 项目摘要。Git identity 本身不能证明操作者。旧 `RRUFF_LINE_COAUTHOR_CONTRIBUTION.md` 的 attribution 段已经过时，不应用来举证。

### 6. 哪些资产对“写申请叙事”最重要？

依次是：从 broad zero-shot 转向 label efficiency 的 2026-07-24 决策；把 RRUFF-70 降级为 exploratory 的理由；RRUFF-301 prereg；主动发现 trigonal/hexagonal 标签 bug 并作废 v1；不改超参的 corrected v2；68/75 正配对、三档 K 均正的结果；monoclinic 负迁移未复现；fix/break 比随 K 增加；最后以“实验域标签效率提升而非消除 sim-to-real gap”收束。`RRUFF真实域_科研叙事.md` 已进入 main，可作主叙事候选；其中 ECE/NLL/Brier/confidence 应理解为当时提出的后续分析议程，不能写成已被当前 raw probability 证实的结果。

### 7. 哪些资产对“未来复现 RRUFF 实验”最重要？

数据 contract、master manifest、正确 split、原始 spectra/evidence、raw runs/predictions、candidate runner、split-fix 与 aggregation/representation scripts、pretrained checkpoint hashes/paths、`pyproject.toml` 和 prereg protocol。当前 runner 指向不存在的旧 checkpoint 路径，且原始 support-ID plan、命令日志和完整 runtime binding 缺失，因此现在只能做到“高可信重建”，不能声称 bit-for-bit 一键复现。

### 8. 是否存在任何关键缺失？

有：原始 DeepSeek 会话与 session index；原始 prereg episode/support-ID 文件；v1 原始 metrics/predictions；pipeline diagnostic 的独立 raw result；明确的 301 paired-comparison CSV；完整命令/环境锁定/运行日志；有效 checkpoint 路径绑定；RRUFF-specific scientific figures；原始数据私人交接/再分发许可结论。详见 `MISSING_AND_UNKNOWN.md`。

## 文件导航

- `MUST_TAKE.md`：必须进入后续待审交接包的资产。
- `SHOULD_TAKE.md`：建议保存的旁证、叙事和辅助材料。
- `REFERENCE_ONLY.md`：共享主线依赖，不属于个人模块。
- `LOCAL_ONLY.md`：当前 GitHub 未保存的本机资产。
- `ALREADY_ON_GITHUB.md`：当前 main 与可达历史中的资产。
- `MISSING_AND_UNKNOWN.md`：缺失、未知、复现断点。
- `RRUFF_TIMELINE.md`：13 阶段科研考古。
- `DEEPSEEK_RRUFF_SESSION_INDEX.md`：DeepSeek 搜索结论与代理记录索引。
- `YIFENG_RRUFF_HANDOFF_AUDIT.csv`：机器可读总清单。

**停止点：Stage 1 已完成。没有开始复制或打包。**
