# Codex Cloud 任务：BaTiO3 × V9 测量扰动 × Clean-Reference Forward Loss

**状态：QUEUED / NOT EXECUTED。** 2026-10-18。适用于在用户本地 RTX 4060 电脑离线时，通过 GitHub 连接的 **Codex Cloud 环境**实施。此文件是任务指令，不代表该实验已经成功，亦不代表 Codex Cloud 实际有 GPU。

## 科学目标（仅一项）

将 PR #17 已通过小规模工程 Gate 的 **HfCd V9 四类扰动适配器**迁移到 PR #16 使用的 **公开 BaTiO3 P4mm CIF**，比较已知四方结构条件下：
- A：同一 ResNet-18-GN 的连续晶格参数监督回归；
- B：相同 backbone / data / split / train budget + **simulator-supervised clean-reference Forward Loss**。

不做未知物相识别、多相精修或大模型，不预设 B 必须优于 A。March–Dollase 本次关闭。无需学长真实数据，可独立完成代码、物理检查、CPU smoke；正式 GPU 训练根据云端可用算力执行或留待笔记本/其他授权 GPU。

## 基础证据和分支

从 `AGENTS.md`、`docs/CURRENT_STATE.md` 和 `docs/PROJECT_HISTORY.md` 开始。**不可修改原有冻结 V9** 或下面任意先前 Pilot 的已存结果。

- PR #11 `feat/physics-guided-pxrd-inversion-pilot`：最初 HfCd differentiable Forward + A/B，实验原件保留。
- PR #17 `codex/forward-loss-v9-reuse`：`xrd_forward_loss/V9_PERTURBATION_ADAPTER.md`、`perturbation_data.py`、`scripts/run_v9_perturbation_pilot.py`、`losses.py`、`training.py`。四类扰动：全谱零点偏移、峰展宽、平滑背景、Poisson–Gaussian 噪声；保留 `theta_true`、`clean_profile`、`observed_profile` 与 provenance。原 HfCd 工程 Pilot 128 样本、三个 seed 已完成，不可冒充 BaTiO3 结果。
- PR #16 `feat/public-batio3-forward-ab`：`xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif`、`scripts/run_public_batio3_smoke.py`、`BATIO3_PUBLIC_PILOT_REPORT.md`。BaTiO3 公开 CIF COD 9014273，P4mm，a≈3.986 Å、c≈4.026 Å。512 张模拟谱、单 seed Pilot 已运行，但**使用旧版 noisy-observed Forward Loss 和简单扰动**，不可与新干净谱约束混为同一 protocol。

## 操作顺序

1. **独立开发分支 / Draft PR**：以 PR #17 最新 head 创建新分支；受控引入 PR #16 的公开 BaTiO3 CIF 和相关来源说明，避免重复覆盖同名报告、扰动代码和旧结果。必要时 cherry-pick 仅需文件，不盲目合并整个 PR；记录源提交 SHA。生成新的 `batio3_v9_...` 配置与脚本/结果目录。不得直接改主分支或合并上述 Draft PR。
2. **先核对来源与物理**：检查 CIF 组分、P4mm、原子分数坐标、晶格 convention、占位；独立 Pymatgen XRD reference vs differentiable GPU/CPU Forward 的峰位**及强度、整体谱图**数值对照，不能只凭 PR #16 的 peak coverage=100% 宣称完整 parity。对允许参数边界进行小规模 Jacobian rank/conditioning 检查。异常即停止并报告。
3. **结构参数真值与测量扰动分开**：参数 `theta_true` 采样后，生成同一 q 的干净谱 `clean_profile` 与多种带 nuisance 的 `observed_profile`；保持 seed/provenance，核对零点偏移不会改动 q 真值。V9 NumPy renderer 不可切断新 Forward 的 autograd 路径。固定两套输入条件（simple 与 v9）；同一条件下 A/B 使用严格配对的数据与预算。
4. **训练目标**：B 必须采用 PR #17 的 `L_param + lambda*D(F(theta_pred), clean_profile)`；不是 PR #16 原先的 `D(F(theta_pred), observed)`。报告为 *simulator-supervised clean-reference*，不得宣传为真实谱无监督约束。Lambda 在**验证集**选择，并将预选列表写进新配置；不要使用过去 BaTiO3 的测试结果来定超参。之前的 Pilot 仍作为探索性背景，不当作全新未见测试。
5. **执行级别**：优先完成兼容性 gate + minimal CPU/GPU smoke。若云端无合适 GPU，可只做实现与测试、给出需在本地 RTX 4060 上执行的复制命令；不得伪造训练完成。如果 GPU 可用，先 128 张样本的限定试跑，经测试通过再运行上限 512 张参数样本、三 paired seeds、合理固定训练预算。若显著资源/时间差异，需要在日志说明，不能无限试不同 λ 直到 B 优于 A。
6. **评价**：保存 test 两参数 normalized MAE、a/c Å MAE、clean/observed transformed-profile RMSE、各 seed 配对差异与失败样本、运行时间、配置/版本/hash、train/validation/test counts 与所有物理 gate；严格标注同一 CIF 只是参数插值测试，不是跨原型泛化、真实 XRD 或精修初始化的直接证据。
7. **测试与交付**：针对重构 target、nuisance 元数据、q 真值不变、重建梯度/finite difference、测试集数据隔离写可执行回归测试。将真实执行过的命令及 exit code、机器环境保存；生成 `TECHNICAL_REPORT.md`、指标 JSON 和至少一个输出图（仅在真的跑出结果时）。在独立 Draft PR 提交，给出有意义的科学结论或清楚的 BLOCKED 原因。

## 停止条件

**停止于“BaTiO3 单家族方法工程 + 如可执行则受控小规模 A/B”的交付。** 不要继续扩展 PZT/KNN、同时训练通用多家族模型、重启 V9 或做大规模自动超参搜索。本轮不改变已批准/未批准的科研定位，研究者后续审查后再做新决策。

## 安全/运行原则

- **在 Codex Cloud 执行**，不依赖用户离线电脑。若选不到仓库或缺少已创建的环境，应明确报告 `CLOUD_ENVIRONMENT_NOT_READY`，不能声称任务已启动。
- 不配置独立 API Key，不上传设备密钥/私有原始实验谱。PR、公开 Issues 和仓库仅可包含可公开的材料与结果。
- GitHub 的 `research_bridge/worker.py` 是只读本地工作流，本任务**不能**靠添加 `bridge-ready` 或 `bridge-readonly-approved` 标签来运行 GPU 代码；也不应以 `[Bridge]` 开头创建任务。
