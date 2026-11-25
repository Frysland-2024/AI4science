# Project History — Public Research Timeline

This file is the **public, concise history** of how the PXRD project evolved. It preserves major corrections, negative results, and changes in problem definition without reproducing internal handoff notes or application material.

For current scientific claims, use [CURRENT_STATE.md](CURRENT_STATE.md) and the tracked result reports. History explains *how the project changed*; it does not override the current state.

## 2026-11-19: Anthropic 的光谱研究与通用科研 Agent——“手与脑子”以及野牛问题的延续

**记录类型：研究者对 AI4Science 科学方法、工具分工和人机理解边界的阶段性反思；不是新实验结果、已证实的产业趋势或对当前 PXRD 主线的修改。** 本次讨论延续 [2026-11-10 的 Vibe Research / 野牛反思](#2026-11-10-vibe-research-的双刃剑自己不知道不理解的能力思考时间与野牛)，外部研究与研究者观点严格分开记录。

### 一、触发案例：Anthropic《Making Claude a chemist》与 Claude Science

- **原始来源：** Anthropic, [*Making Claude a chemist*](https://www.anthropic.com/research/making-claude-a-chemist)，2026-06-05。文章关注通用 Claude 对化学结构与光谱表示的理解，特别是核磁共振 **¹H/¹³C NMR**，而**不是氢原子发射谱线，也不是直接验证 XRD/Raman 物相识别**。
- **论文所报告的具体证据：** 20 个来自训练截止后 ChemRxiv 预印本的化合物，覆盖四类骨架；将 Claude（每个化合物重复三次）与 ChemDraw、MestReNova 比较正向 NMR 化学位移预测。Anthropic 报告 Opus 4.7 在 ¹H 任务中平均误差 **0.079 ppm**、在所比较方法中表现最好；¹³C 任务约 **1.37 ppm**，与 MestReNova 的 **1.48 ppm** 接近。另有 15 个由分子式及 1D NMR 反推结构的测试：8 个较简单目标无起始物提示，7 个复杂目标额外提供了反应起始物信息。
- **证据边界：** 以上是 Anthropic 公布的、规模有限的特定基准，未覆盖复杂天然产物、多数溶剂、2D NMR 与立体化学；复杂逆向任务并非“仅凭谱图”完成。它支持“通用模型在某些专业光谱任务上已具竞争力”，**不能推出通用模型普遍优于专有模型、已具备经验证的科学理解，或能够直接代替真实测量验证**。
- **更广的同日讨论背景：** [Claude Science（2026-06-30）](https://www.anthropic.com/news/claude-science-ai-workbench)将通用模型与科研数据库、工具、可审计产物和计算环境连接；[Anthropic 药物研发进展（2026-10-27）](https://www.anthropic.com/research/early-progress-drug-development)描述了药企合作与早期实验反馈。**公司公布的合作与早期结果并不等于新药临床成功，也不证明 Anthropic 是唯一的 AI4Science 落地参与者。** 这些案例吸引研究者的不是“所有专有模型消失”，而是通用模型参与跨工具、跨表示的真实科研工作流。

### 二、研究者当天的核心思辨：“专有模型是手，通用模型可能是脑”

研究者批评部分领域论文将“为固定数据集训练一个预测器、展示漂亮指标”视为主要科研贡献，却缺乏独立实验、真实域评价、传统方法对照及可解释的失败分析；尤其反感将 **Sim-to-Real Gap** 作为验证失败的笼统托辞。**这是对一类研究实践的批评，不是“所有神经网络论文毫无价值”的证实结论。** Sim-to-Real Gap 本身可以成为严肃的研究对象，关键在于是否被测量、解释和验证。

研究者用自己的话将系统分工概括为 **“通用模型会用专有模型就行了”** 与 **“手和脑子的区别”**：专有网络、数值求解器、数据库等可以成为高效、可检验的专业计算模块；通用科研 Agent 则负责理解研究目标、阅读文献、组合工具、提出及比较假设，并组织验证。研究者反对把仅完成局部预测任务的“手”包装成整体科研判断能力，也担忧把通用“脑”的开放能力过早缩窄为单一任务预测器。

**需要保留的反论点：** 这个比喻是有启发性的功能分层，**不是已证实的智能层级或可靠性排序**。专有模型仍可能在计算效率、时延、受约束精度和大规模吞吐上不可替代；通用 Agent 同样会误读文献、错误调用程序或给出貌似可信的解释。GanJiang 本身也是结合专业工具的领域 Agent，不应在无相同数据、同等工具预算和盲测的条件下，以个人使用体验宣称通用系统客观“碾压”领域系统。

### 三、进一步的问题：怎样证明 AI 真正“理解科学”？

讨论从“通用模型能否调用专业模型”转向一个**对通用 Agent 同样严格**的问题：模型能检索、写代码和解释结果，不等于它理解了物理机制。更可信的检验应观察：在陌生测量条件下能否提出可证伪的备选解释；能否区分不可辨识问题与可测量问题；能否设计具有区分力的下一次实验；能否随着真实反馈修正结论；能否保留来源、计算步骤、失败和不确定性。**“会说得通”不能替代“能够被证据纠正”。**

研究者也提出未来希望 AI 能理解人类研究者正在做什么：不仅阅读论文，还应理解数据来源、实验意图、仪器条件、历史失败、限制和拒绝下结论的理由。这是值得探索的人机科研协作问题，不是已实现的能力声明。

### 四、与 11 月 10 日“脱缰野牛”的双向联系

- **11 月 10 日的问题：** AI 获得了超越人类即时知识边界的执行能力；研究者形容 Vibe Research 让人具有“自己不知道、不理解的能力”，速度过快会挤压人的科研思考时间。
- **11 月 19 日的问题：** 通用 AI 能否理解人类正在进行的科学研究，而不仅是运行一个已定义任务？反过来，人能否理解并审计 AI 的解释、工具选择和下一步建议？
- **当天对助手的直接批评：** GPT 经常提出过多 A/B/C 方案，制造人类难以消化的分叉，继而把筛选、学习和解释的负担转嫁给研究者。**能生成更多方案，不等于对研究者更有帮助。**

因此，野牛的缰绳并非让 AI 更慢，而是**把执行速度与人的理解、决策速度解耦**：明确科学问题和停止条件 → 受限的工具执行与证据交付 → 人理解关键物理假设、反例、风险及结论 → 再决定是否推进。保持 [RESEARCH_WORKFLOW.md](RESEARCH_WORKFLOW.md) 中的人类决策门槛；AI 默认给出一个可解释的最小下一步，而不是无端扩展 ABC 研究树。

### 五、与 PXRD、潜在 Raman/SRS 研究的关系（仅候选思路）

研究者当天讨论过：未来是否可以让通用 Agent 检索晶体/光谱文献、查询数据库、调用物理模拟与拟合工具，在真实 PXRD 或 Raman/SRS 测量中完成候选解释、误差审计和证据核查；尤其考虑到其与东京大学小关泰之教授研究的潜在联系。更有说服力的研究形式是**在任务与信息预算明确的独立样本上**比较通用工具 Agent、领域 Agent/专有网络和传统物理分析，记录正确性、拒答/不确定性、可复现性、成本及人工核查负担，允许否证原始直觉。

**状态与决策（2026-11-19）：** 这是科研理念及未来研究兴趣的记录，**非当前项目研究方向的正式变更、非新实验协议、非新任务授权**。现行主线仍是 **PXRD 七晶系分类与同母结构关系监督**，V11 的既有冻结数据、门槛、RRUFF 评估合同及尚未授权的 GPU/HPO 保持不变；不据此启动新的 LLM-vs-CNN 比较、创建 PR/Issue 或修改 CURRENT_STATE。今后若要真正转向 Agent 研究，需要先界定科学问题、资源与可证伪实验，再由研究者明确决定。

**外部依据与归属：** Anthropic 官方文章及产品/药物研究公告是其自身报告；“手与脑”、对领域模型论文的批评、野牛反思及未来 Agent 方向属于研究者的观点；对方法边界和验证要求是本轮共同讨论的归纳，均不冒充已完成的研究成果。

---

## 2026-11-10: Vibe Research 的双刃剑——“自己不知道、不理解的能力”、思考时间与“野牛”

**记录类型：研究者的方法论与工作方式转折（不是新的模型结果）。** 本条记录 2026-11-10 前后关于 AI 辅助科研的连续反思，保留尚未解决的矛盾，供将来回溯项目发展和撰写申请材料。它不改变 V11 科学协议；执行真相始终以 CURRENT_STATE 和原始证据为准。

### 一、首先意识到的矛盾：AI 执行能力扩张，而人的思考时间反而被挤占

研究者直接提出过：**“我觉得，在 vibe research 时代，能做的事情很多，但是留给人去思考的时间很少。”** 这不是反对 AI，也不是否认其显著提高了编码、调研、实验计划和证据整理的速度；恰恰相反，问题是可做的事情膨胀得太快。生成新方向、新试验、新修复建议的速度，开始超过一个人判断它们是否值得做、为什么要做、应当何时停止的速度。**执行吞吐量增加，不等于科研判断质量按同样比例增加。**

### 核心命题：一种既是“最好的事情”也是“最坏的事情”的能力

**研究者本人在 2026-11-10 的直接补充：**“vibe research 让人第一次有了自己不知道，不理解的能力，是最好的事情，也是最坏的事情”。这里的“第一次”是个人对新科研范式的强烈体验和价值判断，并非要证明历史上从未存在借助他人或工具超越自身知识的情况。

**最好的一面：** 人不必先学会所有实现细节，就能借助 AI 进入陌生方法、跨学科尝试、快速搭建原型、执行原先因技能和时间门槛过高而不可行的研究。科研的**行动边界突破个人知识边界**，确实扩展了普通研究者的探索空间。

**最坏的一面：** 研究者也可能尚未弄清方法为什么合理、结果说明了什么，就被连续的新实验和新结果推动进入下一个任务。模型、代码和试验的可执行性，不等于假设的正确性、解释的可信性或路径的研究价值；“能做”与“理解”“应该做”脱钩，甚至让人失去对自己科研方向的控制。

研究者随后复贴并认可过一个对这一思想的解释，认为**“差不多就是这种感觉”**：过去的个人知识边界大体约束行动边界（“我知道什么 → 我能做什么”）；现在可以出现“我能让 AI 做什么 ≫ 我真正理解什么”的落差。**Vibe Research 缓解了“我不会做”，却放大了“我不知道该做什么”**。此处为研究者认可的解释性重建，不冒充消失聊天的逐字原文。

### 两种速度的倒挂：廉价试错，昂贵反思

研究者特别强调，**AI 大幅提高科研执行速度，却没有同比提高人类理解、反思和判断的速度**。过去一个想法从形成到落实可能需要数日，人有间隙阅读、怀疑和琢磨原理；如今 GPT 能很快提出多条路线、Codex 修改代码、GPU 开始运行，下一轮建议可能先于对上一轮的理解到来。

这种模式会产生反常现象：**科研工具越强，人反而越没有时间真正思考科研。** 当提出和执行候选工作的速度超过人消化结果的速度，每次试错虽然更便宜，**每个结果引入的新解释负担**却会累积。研究者可能必须继续追问：为什么指标变好？是否回答了原问题？有没有更简单的解释？方向是否仍值得继续？倘若回答之前就启动下一轮，便可能不断**积累实验结果，却没有积累相应的理解**。

这一张力也有助于理解研究者此前报告的反复查看 GPT / Codex 进度的经历：人在等待下一次快速交付并不断迎来新的待办时，注意力可能受机器执行节奏牵引。这是对研究工作方式的反思，**不是已经得到因果证明的心理学结论**。

### 机器时间要快，人类时间要慢

- **机器时间：** 文献检索、代码实现、参数搜索、实验执行、重复性核验、整理结果。对边界清楚且已获批准的任务，尽量自动化并减少人的消息搬运。
- **人类时间：** 阅读、怀疑、理解原理、重新建立假设、解释失败、决定研究方向、必要时停下来。它不是机器时间的空闲补丁，更不能单纯用完成多少实验衡量价值。
- **关键设计目标：** 不是逼人跟上机器，而是**让机器不再打断人的思考**。将一组有边界的 AI 任务与一次有质量的研究者证据审阅分开，避免“人 → GPT → Codex → 人 → GPU → GPT → 人”的高频往返。
- **研究者可主动安排“不向 AI 下任务的科研思考时间”**：这段时间不是普通休息，而是科研本身；不必规定僵硬的时长，应保护其不被新提案和提醒占用。

由此得到的更深层研究能力不是“把多少想法变成实验”，而是**面对近乎无限的可执行想法，知道什么问题值得研究、什么结果值得相信、何时应该停止执行并开始思考**。

### 野牛只是这种矛盾的形象表达，不是理论本身

研究者认可“像野牛一样，在广阔的科研草原上横冲直撞：哪里都能跑、什么都能尝试，却可能不知道为什么向那里跑”的重建性解释。**野牛比喻表达的是执行能力扩张而思考与方向感跟不上；根本矛盾则是“拥有自己尚不知道、不理解的能力”带来的赋能与失控的双重可能。** 项目地图的任务不是让野牛跑得更快，而是让研究者能看到路径、证据与未决问题，并保留转向、暂停和不执行的权力。原来消失的完整对话未被找回；上述部分区分研究者直接补充的原话、研究者认可的解释和整理性概括。

### 二、从研究方法上的“不成体系”，到认知资源上的“被任务淹没”

更早的自我对照是：一些同伴的课题似乎有现成范式、模板和流水线，而自己的 PXRD/AI4science 路线更依靠直觉选择研究问题、拼接实验设计、反复试错；研究者曾将其比作**“经过考级训练的钢琴手”与“纯靠直觉演奏音符的钢琴手”**。这种处境有两个面向：直觉允许跨材料表征、测量系统与机器学习做探索，但也意味着每次转向都可能重新消耗方法设计与优先级判断的精力。记录这一点不是要否认已完成的研究或把探索描述成失败，而是承认**当外部范式不足时，内部的项目地图、检验标准和停止条件就更重要**。

与此直接相关的要求是建立**“项目地图路径”**：不仅知道今天做什么，还要看到各阶段的研究假设、证据、依赖条件、失败分支、可暂停环节，以及为何从 ferroAI、早期 XRD 任务走向同源谱一致性、真实域评估、大规模 V11 和后续计测方向。地图要帮助人做选择，而不是成为又一个需要不断维护的文档工程。

### 三、注意到 Vibe Research 引发的心理循环：期待（A）＋急迫（C）

研究者主动询问过，为何用 GPT 开展 Vibe Research 时会焦虑、忍不住反复拿起手机看进展。对更具体的自我观察，他选择了 **A（期待看到新成果）与 C（总觉得科研还没做完、需要继续推进）**，而不是简单归因于“害怕 AI 出错”。

本轮归纳出的待验证解释是：AI 可能随时交付一个新结果；结果令人兴奋，却几乎总能引出下一项任务，于是“检查进展—收到新结果—发现待办—再次检查”不断循环。这里描述的是研究者报告的感受及对话中的工作假设，**不是临床判断，也不等于证明了某种心理机制**。重要的是：这种兴奋是真实的科研动力，但不应令研究者丧失主动离开工作状态的能力。

由此形成一个核心区分：**“整个项目还没有完成”不等于“今天我应该继续工作”。** 机器仍在训练、待办仍然存在，都不能自动成为继续盯着手机的理由。每天需要一个真实的个人完成条件。

### 四、意识到角色错配：不应永远当 GPT／Codex／GitHub／GPU 之间的“人力转接器”

研究者随后明确说：**“我觉得我需要建立一个健康的 vibe research 工作流，而不是一直当人力转接器。”** 这句话标志着问题定义的变化。先前主要思考**如何让 AI 能做更多科研任务**，此时转向思考**应该把哪些权力交给 AI，以及如何让 AI 执行任务时不持续占用人的注意力**。

不希望继续重复“GPT 提建议 → 人复制给 Codex → Codex 出错 → 人转发给 GPT → 再复制指令”的链条。理想职责分工是：**人选择科学问题、优先级和重大资源决策；AI 拆解和审查已定义的任务；受控调度器负责在权限内运行、记录、失败即停；GitHub／原始产物提供可追溯证据；人只在约定的验收窗口或真正需要批准时介入。** 这一方向不是要把科学判断外包，而是把低价值的消息搬运从研究者身上移走。

### 五、健康的自动化必须有“停止的能力”

这次讨论形成的工作原则，不是“让 AI 24 小时源源不断地产生下一件事”，而是以下几条边界：

1. **预先冻结范围**：每个任务必须明确输入、可执行动作、预算、验收证据、失败处理与停止条件。小修复和已批准的试验可自动执行；更改 loss、数据集、冻结 Test、GPU 预算或下一研究阶段，需要研究者重新批准。
2. **任务完成不自动扩大任务**：V11 HPO 的结束点是可供审查的模型选择证据，不是自动进入 final、Test 或 RRUFF。负面结果也应可结案，而非自动触发无限改法。
3. **允许离线**：研究者不在线不妨碍已经授权的执行；但自动化不得因为缺少回复就推定拥有新权限。机器的状态不明时，报告 UNKNOWN／NEEDS_DECISION，不能假装“仍在运行”。
4. **减少信息刺激**：以定时、简短的结果摘要代替高频通知和反复刷新；优先呈现新证据、阻塞、唯一需要本人处理的决策，不用普通进展催促马上开始新任务。
5. **文件与历史要够用而非越多越好**：保留真实科学转向及有意义的负面证据，但避免每次想法、每个 PR 都产生新报告；项目历史不是自动生成的科研流水账。

### 六、具体行动与尚未闭环之处

讨论随后从抽象反思转为工程动作：在现有仓库采用任务状态、分层审批、只读验收、受控 Codex 审查及 V11 执行器的可恢复能力；笔记本已有受控任务调度和定时摘要，旧 research_bridge 不应复活；截至本次记录，**cuifa 目标机器的真实 Stage 0、正式 HPO 和后续评测均未因工作流建设而获得许可或被证明已运行**。这些属于执行边界，不应写成训练成绩。

真正的下一阶段不是无休止扩建代理网络，而是检验这个体系能否减少研究者的时间碎片化：**即便一天只集中查看两次，能否仍然掌握足够的科研事实并作出必要决策？** 如果系统增加了新的报告维护、审批搬运和无意义通知，就说明虽有技术自动化，却没有实现最初要解决的人机协作问题。

### 七、为未来申请材料保留的真实转折

这段经历不宜被追溯性包装成“一开始就有完备路线图”。更真实的脉络是：

**依靠直觉探索材料表征 AI → 借助 GPT/Codex 显著加速研究，第一次强烈体验到“自己不知道如何做也能行动” → 像野牛一样探索过多分叉 → 面对不断出现的新任务，思考、理解与决策时间被挤占 → 注意到期待与急迫交织的频繁检查行为 → 发现自己成了 AI 之间的人力转接器 → 要求建立项目地图、权限边界及可结案的执行系统 → 让人重新保有足够时间去理解证据、选择方向和决定停止。**

这一变化的意义，不在于证明模型更好，而在于研究者逐渐理解：**科研能力不仅是“能尝试多少个实验”，也是“知道哪些问题值得问、哪些实验应该做、什么时候已有足够证据、什么时候应当停下来思考”。** 未来若再次改变对自动化程度、项目组织或人机分工的看法，应保留本次判断及修改原因，而不是悄悄改写成一条从未犹豫的直线路径。

**研究决策（Research decision，2026-11-10）：** 项目地图应呈现“科学问题 → 证据与未决假设 → 研究分支与失败原因 → 当前门槛 → 下一项需要本人作出的决策”，而不只是展示任务吞吐量。每轮已授权执行结束后，默认提交证据、停止扩大范围，并给研究者保留独立的理解与决策环节；只有本人确认科学意义与下一步范围后才进入新的科研阶段。具体操作规则见 [RESEARCH_WORKFLOW.md](RESEARCH_WORKFLOW.md)。本决定**不授权**任何新的 Codex/GPU/HPO/final/Test/RRUFF 工作，也不改变现有 V11 冻结协议。

**取材范围与可信度：** 本条依据可见的 2026-11-09 至 11-10 项目内对话、研究者后来补充的未完成原话片段和明确确认的“野牛”含义，以及当前工作流代码/规范。未找到完整原话的比喻已说明边界；这里记录的是经本人确认的含义，而非被系统找回的原始对话。非逐字的心理机制与价值判断均为整理性归纳，日后可校正。


**2026-11-10 Research decision — restore the V9 lambda-selection logic in V11.** Source-level archaeology uncovered an important distinction: V9 originally used PAMPT-B3 probes (λ=0.3/3/30), observed a FAIL when those gradient bands transferred poorly to ResNet-18-GN, then shifted to ResNet probes (λ=3/30/60) and separately selected λ=60 on frozen Validation. The old V11 design instead transformed a Train gradient-norm heuristic (R≤2) into a hard Optuna exclusion rule, ruling out λ60 before any Validation training. We corrected the methodological overreach: **the gradient gate may admit a cross-decade candidate span after combined-gradient safety checks, but cannot select the best λ**. See V9 primary reports at Git commits `09185c8`, `0697cb2`, `e7965db` and `34fe205`.

**New direct evidence:** the existing 108,478-parent/6,780-batch V11 learned-state Train gradient audit was preserved verbatim; a separate real RTX4060 Train-only learned A0 FP32 trunk check covered 704 independent Train parents in 44 batches at λ0.3/3/30/60. All passed the original V9-style checks (median cosine between CE and combined CE+λJS gradients positive; maximum combined/CE norm ratio ≤50). At λ60 the **median cosine is 0.2232**, its P10 is **0.0193**, and the worst combined/CE gradient norm ratio is **10.08**; this passes the limited safety gate but has smaller direction margin than λ30, and cannot predict Validation advantage. The new HPO proposal covers **λ∈[0.3,60]**, alongside middle stride and residual kernel, selected entirely on frozen Validation **on cuifa after Stage0 and budget authorization**. The six pre-enqueued comparisons include four λ30 A0–A3 architecture controls and A0 λ0.3/60 endpoints, followed by multivariate TPE. Nothing has been trained/tuned on cuifa; Test and RRUFF remain locked. This decision repairs an overly strict assumption, not a demonstrated new model improvement.


**2026-11-10 Research correction — use transferable gradient strength R, not V9's numerical lambda.** After the additional safety probe, revisiting both immutable V11 reports showed the FIRST full-Train gate was the more informative **HPO interval-design evidence**: A0 r=0.0681726422 and the original R target [0.05,2] yield lambda[3,29.3373]. Crucially, V9's selected lambda60 was R=1.754115, so the corresponding V11 A0 reference is lambda≈25.73, not 60. The later lambda[0.3,60] proposal simply copied historical lambda magnitudes; despite passing 704-parent Train-only combined-gradient safety, it explored R up to ~4.09 without matching V9's relative-gradient rationale. We therefore restored the first window as the primary HPO focus, **reinterpreted R=2 as a search-budget boundary (not a physical safety theorem)**, and retained the second report unchanged as supplementary safety evidence and a documented methodological correction. Four architecture controls now share the A0-based R reference with an explicit caveat that A1–A3 need not have equal actual R. No further laptop GPU study is warranted; frozen Validation on cuifa will make the final model/weight choice after separately approved Stage0. The completed local Train-only stage is closed; cuifa HPO, confirmation and final evaluation remain NOT_RUN.

## 核对后的完整时间线（2026-11-09 阶段节点）

**这张表是项目发展的主时间线**：记录不同科研阶段实际解决了什么问题，不把 Git 代码版本号当作严格顺序的独立论文，也不覆盖已有结果和失败记录。

| 阶段 | 实际发生的事情 | 科研性质 |
|---|---|---|
| **FerroAI** | 从材料性质预测起步，逐渐建立对数据、模型和证据链的认识 | 前置研究经历 |
| **PXRD 早期—V8** | 物理扰动模拟、PAMPT、Residual、结构化模拟等多次尝试与纠偏 | 研究问题与方法探索 |
| **V9（2026 年 7–8 月）** | 转向 ResNet-18-GN，确定 JS λ=60，完成多种子 ERM–JS 对照及模拟 Test | **完整主研究成果** |
| **早期 V10（7 月）** | 尝试测量信息监督的 Residual 解耦，得到负结果并归档 | 与 V9 后期交叠的探索支线 |
| **2026 年 8–10 月** | RRUFF、CNRS、校准、数据效率补充实验；另探索参数反演，随后归档 | 已完成研究的补充与新方向尝试 |
| **11 月的 V10** | 更新模拟环境，探索 CNN11、ResNet 的 Stride/Kernel，以及 LR/Scheduler | **下一阶段的初步架构与训练优化** |
| **V11（当前）** | V11 物理模拟器、15.5 万结构数据库、完整训练和 RRUFF-Cu1011 竞争性测试规划 | 新阶段的基础设施基本就绪，正式性能实验待运行 |

**主要阶段分界：** 回顾性地把 **V1–V9 视作已经完成的一轮 PXRD 科研**（研究问题→方法形成→V9 的冻结对照与 Test 验证）；**11 月的 V10 只是下一阶段的初步调参/架构筛选**；**V11 则负责更大数据集上的后续训练与真实域性能检验**。V9 不是被 V10/V11 “补做完”的项目。

**历史精确性：** V1–V5 暂无逐版本完整可核验证据，因此“V1–V9”是科研阶段概括，不是九次独立验证；**7 月的 V10 Residual 分支**确实早于 V9 最终收束，与 V9 工作交叠，且和 **11 月的 V10 架构比较**不是同一试验。8–10 月对 V9 的真实域、可靠性和样本效率研究可视为第一轮成果的后续完善，不等于重新开启其超参数选择。11 月的 V10 单种子 A0_R1 优胜（Validation OOD Macro-F1 0.731830）来自 **LR=2e-4 与 Cosine 捆绑改变**；不能据此宣称 LR 单变量最优，更不能当成 V11 或 RRUFF 成绩。

**可追溯依据：** [2026-08-23 历史全档](https://github.com/Frysland-2024/AI4science/blob/d70d84da6535a0a04e7cd5fba3faa794c64656cd/00_project_context/PROJECT_HISTORY.md)（FerroAI→V9、7 月 V10 负结果）、[V9 科研结果](../xrd_robustness/reports/RESULTS.md)、[JS 权重选择证据](PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md)、[11 月 V10→V11 迁移说明](PXRD_SERVER_MIGRATION_V11_ONECLICK_20261103.md)。以下保留各节点的详细经历与负结果。**本表只整理历史，不修改研究合同、训练参数、Test 或 RRUFF 冻结规则。**

---



## 2026-11-10 · V11 从固定候选转向梯度约束的全自动 HPO

**思路转折（负责人明确纠正）：** 最初过于复杂的全维度 HPO 逐步收缩为两个科学问题——（1）同母结构 JS 正则强度 λ；（2）参考 Bin Cao/SimXRD 产生的 PXRD 峰信息保留假设，即 ResNet 下采样 Stride 与卷积 Kernel。Weight decay=1e-4、LR=2e-4+Cosine 继承 V9/V10 合理训练配方；Batch size=16 优先视为工程预算，不与科研参数混淆。随后早期 V11 .9 曾把这两个问题实现为四组固定架构加两个固定 λ=30/90，负责人进一步强调：**保留 Optuna 的真正全自动优化能力，但给优化限定有依据的方向与范围**，不能反过来把少量预定组合误称“自动调参”。

**新的科学设计：** 以 V9 Train-only learned-state 梯度尺度 Gate 为先例，在新 V11 全部 108,478 个独立 Train 母结构上实施已学习状态的 CE/JS 全模型梯度检查（其中 ResNet trunk 比率用于 λ 作用范围的校准）；在 Validation 之前冻结 λ 的有界搜索范围。将中间 stage stride {2,4} 与 residual kernel {5,9} 分开作为 Optuna 两个变量，在 λ 锚点下先形成 A0/A1/A2/A3 的 2×2 可解释对照，再由多变量 TPE 自由建议后三维组合，决策仍取自冻结 synthetic Validation。为避免上一轮**暴露次数和训练步数过短**，每个 HPO Trial 至少 50 个完整 Train 母结构 Epoch（Batch16 为 339,000 optimizer updates），确认/正式训练最多 100 Epoch，早停不得先于 Epoch50，所有阶段统一 100 Epoch Cosine 时间尺度；没有凭 5/10 Epoch 的临时 F1 选赢家。测试集/RRUFF 严禁参与优化。

**证据状态：** 本次已把 .10 自动方案提交到 main，隔离本机核验 **47 项 server_migration 回归测试 + 2 subtests PASS**，并包含真实 Optuna 4.9 的三维 TPE 候选模拟。它目前是**代码与方案交付，而不是 GPU 科学结果**：5–10 Epoch Train-only learned-state 训练、108,478 Train-parent 完整梯度审计、目标 GPU 的实际 HPO、确认种子和真实 RRUFF-Cu1011 得分均 NOT_RUN。相比 .9，这是一次**为保留科研问题与降低无效搜索，而不是为增加超参数数量**做出的流程纠偏。操作合同与限制以 [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) 为准。

**V11 未训练梯度先验摸底（2026-11-09；仅作设计参考）：** 为把 V9 的梯度尺度判断迁移到新的 154,975 条来源结构和 TCH pseudo-Voigt V11 模拟器，额外完成一个 **Train-only、A0 随机初始化**的数值实验：从冻结的 **108,478 个 Train parent** 中，每个种子按七晶系分层抽取 **112 个不同 parent**（每类 16），使用种子 `20260711` / `20261109`；batch=16，共 **14 个 batch 观测**，分别计算全模型可训练参数的 FP32 CE 与未加权 JS 梯度。仅使用 Validation 分割元数据作隔离校验，**未加载 Validation 谱图，也未读取 synthetic Test、RRUFF 或 CNRS**。

| 未训练模型梯度诊断量 | 观测值 |
|---|---:|
| 未加权梯度范数比中位数 `||∇JS|| / ||∇CE||` | **0.048486** |
| 比率 P10 / P90 | 0.025746 / 0.076274 |
| 当 λ=60 时加权梯度范数比中位数 | **2.90914** |
| CE/JS 梯度余弦相似度中位数 | **−0.349669** |
| 余弦相似度 P10 / P90 | −0.479127 / −0.002932 |

以**初始化态梯度范数比的中位数**换算的 JS 相对梯度强度目标 `0.05 / 0.2 / 0.5 / 1 / 2`，对应 λ 原始值约为 `1.03 / 4.12 / 10.31 / 20.62 / 41.25`；按 V11 安全范围 `[3,120]` 裁剪后约为 **`3 / 4.12 / 10.31 / 20.62 / 41.25`**。这只提示后续可以**优先调查 λ=60 以下的梯度尺度**，绝不代表正式 HPO 搜索边界或性能最优 λ。负余弦表示这组初始梯度在方向上有冲突，不能据此断言 JS 对训练有害。

**与正式设计的本质区别：** 这里测量的是**随机初始化下、逐 batch、全模型参数梯度范数比**；当前 V11 正式 Gate 需经过至少 5、最多 20 个完整 Train epoch，并满足 Train Accuracy ≥0.30、CE ≤1.85 及近期 Train-only CE 下降幅度趋稳等门槛，再使用全部 108,478 个 Train parents，并以**卷积主干（排除 embedding/head）的梯度尺度**决定弱/中/强 λ 范围。不能把本次 Pilot 伪装为已通过 Gate 的结果，更不能据此提前批准正式 HPO。执行当时源码为 `4749806`（历史版本，而非现行训练合同）；源 manifest SHA256 为 `7f169d555de18b4dd811e18a67196acee317733864a1232fa719a861104333dd`，模拟器配置 SHA256 为 `367aeb8a28c88106ab6df13b4d6b10cf088534318b9d78dd94b6d2f41bc79860`。完整 **14 个 batch 原始数值**及双种子的抽样指纹已按原文件保存在 [V11 Train-only 初始化梯度记录](../xrd_robustness/reports/v11_train_only_init_gradients_20261109.json)，状态为 **`UNTRAINED_DIAGNOSTIC_NOT_VALID_LAMBDA_GATE`**。


---
## 2026-11-10 · V11 Train-only 梯度 Gate 实测成功：λ 新范围与两次执行纠偏

**历史节点（实际运行和负结果均已核验）：** 继 2026-11-10 确定“V9 式 Train-only 梯度先验 + cuifa 全自动三参数 Optuna HPO”后，在笔记本 RTX 4060 上进行了真实校准。因 CPU/GPU 预算，将参考模型学习阶段限定为 **20,480 条七晶系覆盖的确定性 Train 母结构**，而非误称已训练全 108,478；A0 Dynamic ERM 在 **20 Epoch** 后，采样 Train 诊断 accuracy **99.387%**、CE **0.083568**（注意这是训练期间少量 Batch 的指标，非全 Train、更非 Validation）。旧的 CE 5% 平台期标准因持续改善而错误拦截模型，于是根据“已经学得晶系特征而不等于完全收敛”的研究要求，**采用精确 SHA256 绑定的 checkpoint 受控恢复**，不重新训练 20 Epoch。

**第二次纠偏：** 第一次复跑梯度扫描后，覆盖门禁拒绝出具结果：Warmup 的 1,280 个 Batch 被意外复用于全量扫描，实际只遍历了 20,480 条。保留失败证据，修复为全 Train **6,780 个 Batch / 108,478 个独立母结构** 的严格覆盖与验证，并补充回归测试。之后真实重跑全量谱图双视图 CE/JS 梯度扫描成功，**没有打开 Validation/Test/RRUFF**；获得 JS/CE（未乘 λ）的 ResNet-trunk 梯度量级比中位数 **0.0681726422**，累计整模型梯度比 **0.0341939561**。在预先约定的 JS 梯度影响区间下冻结后续自动调参 **λ∈[3,29.3373]**：弱 **[3,4.4006]**、中 **[4.4006,14.6686]**、强 **[14.6686,29.3373]**。λ60 已不属于当前梯度先验范围，但不代表实验已经证明它表现更差。方向证据显示 per-batch trunk 余弦中位数 **-0.02044**（q10 -0.25997、q90 +0.19696），Train 全量 trunk 累计余弦 **+0.15016**；梯度模长与主导优化方向不是一回事。

**成果与下一阶段证据交接：** 完整可核验 JSON 已上传 [gradient_gate_v11_train_108478.json](../server_migration/gradient_gate_v11_train_108478.json)，SHA256 `7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020`，证据提交 `8d7c7a6b4834d5369f9190cdc418f1e449ac5686`。cuifa 上的下一阶段采用锁定证据范围的**全自动** Optuna TPE，搜索 JS λ、中间层 Stride≤4（{2,4}）及 Kernel≤9（{5,9}），不重新进行梯度审计。**实际 HPO / 多种子确认 / RRUFF-Cu1011 仍未运行**。这次经历说明，记录科研历程时应保留“最初判据过严→复用可信检查点→误扫子集被审计拦截→全量重跑与冻结搜索范围”这一完整纠偏链；它是方法论与工程证据质量的重要发展，而不是实验跑分成果。

---
> **新增沟通记录（整理于 2026-09-20）：** [与学长沟通纪要：XRD 项目当前进展与后续计划](PROJECT_HISTORY_NOTE_2026-09-20_SENIOR_MEETING_SUMMARY.md)。依据用户提供的会议摘要截图，记录当前方法与验证进展、定量反演及初步晶体结构预测方向、云算力与协作安排；会议日期未注明。

> **2026-10-22 导师汇报复盘（2026-10-23 整理）：** [方法设计、真实域验证与物理/应用可信度的视角错位](PROJECT_HISTORY_NOTE_2026-10-22_SUPERVISOR_PRESENTATION_REFLECTION.md)。系统记录当晚交流与后续对话纠偏：温度/成分扰动的物理边界、cubic 示例被误认为只做单一晶系、RRUFF 的 K-shot 微调被误听为总训练样本数、CNRS 无目标域适配的 zero-shot 相对增益与低绝对性能的不同评价、原方法/原模型比较及 bias、数据可获得性、扩容和发表文献跑分对标，以及实验室铁电陶瓷 R/T 相真实谱检验建议。保留负责人因方法设计贡献未得到充分理解而受挫及「横向方法研究 vs 纵向材料任务」的认识变化。此为历史反思，不更改冻结实验，也不宣称导师建议已获批或完成。

> **2026-10-23 暂定研究兴趣认识（PROVISIONAL）：** 在复盘导师汇报、准备与东京大学小关泰之老师交流时，项目负责人提出一个新的自我观察：与以材料合成、制备及湿实验为核心的工作相比，自己可能更适合围绕**科学测量系统与测量数据**开展研究，尤其是从物理测量过程、模拟与正向模型、信号处理、监督设计、逆问题到真实域验证的研究链条。过去从 FerroAI 到 PXRD 的选择与反复尝试，为这一兴趣判断提供了经历依据；但当前的已完成研究主要是**基于现有 PXRD 数据/模拟的 ML 方法与评估**，不能据此声称已经具备激光/光学仪器搭建、测控硬件或完整测量系统开发经验。**有待进一步分辨的三个方向是：仪器与光路硬件、测量方法与采集策略、计算测量/信号分析。** 这是一种探索中的自我定位，不是项目主线或毕业课题已经正式变更，也不意味着排斥所有物理实验。未来选择研究组需确认具体课题是否主要涉及光学搭建、信号与算法，还是材料/生物样品制备。

---

## 2026-11-09 · Cuifa CPU provisional sync, not assumed identical hardware

The user reported that the Windows RTX 4070 Ti SUPER / 32GB desktop used for the intended HPO has a CPU stronger than the local Ryzen 9 7945HX, without supplying the exact model. The previous unrecognized-host 2-worker default would underuse that machine. Therefore, the user's tested **12-worker / 4-queue / 64-cache** profile is the **conservative Windows default** on all Windows hosts, including Cuifa's 32GB desktop, regardless of CPU model or RAM size. The previous 2-worker low-memory fallback was deliberately removed at the owner's request; free-RAM warnings remain. A **16-worker resource profile** is deliberately opt-in for a bounded Train-only benchmark and full GPU/Validation headroom check, not automatically assumed faster or approved for HPO. This decision carries forward the same-parent paired-physics determinism and preserves the existing scientific experiment plans. The owner subsequently extended the **same 12/4/64/1 prefetch baseline to Linux/cloud and direct Python entrypoints**, rejecting an automatic cloud-specific 4-worker fallback. This is a uniform starting configuration, not evidence that 12 workers are optimal on an untested rental host; per-machine explicit runtime overrides and hardware preflight remain valid.

## 2026-11-09 · V11 CPU bottleneck measured and Windows prefetch tuned

Once the complete six-profile Validation and a bounded real RTX 4060 training run had passed, the limiting engineering problem was **CPU-bound online TCH pseudo-Voigt spectrum generation**, not GPU memory. Rather than replacing the physics model, the project compared deterministic multiprocessing worker counts, bounded prefetch and reflection caches. With identical paired-spectrum SHA fingerprints, short CPU+GPU A0/JS comparisons improved from approximately **82 parents/s at 4 workers/2 queues** to **168 parents/s at 12 workers/4 queues** on the user's Ryzen 9 7945HX laptop. A follow-up 12-worker **512-step plus complete six-profile Validation** acceptance passed in 129.88s for the train+scoring phase (versus ~183.17s in the earlier 4-worker acceptance), with cached-panel and checkpoint hashes intact; the lowest observed free system memory was 5.80GiB, so further concurrency increases were not justified. This is a compute pipeline gain, not a trained-model accuracy result.

The Windows launcher gained a machine-specific, reproducible CPU resource profile: auto-enabled only on the known 16-core 7945HX/32GiB host, conservative by default elsewhere. cuifa's Windows 4070 Ti SUPER CPU is still unknown and must be benchmarked separately. The V11 research protocol, frozen Validation and RRUFF holdout are unchanged. The executable .8 CLI still has 5/10/10-epoch defaults, but the active performance-first v2 research plan has moved to 50-epoch matched JS/ERM convergence pilots and a prospective larger HPO; that plan is NOT YET IMPLEMENTED. No formal HPO/final or real-domain inference was performed.

## 2026-11-09 · HPO full-data claim corrected to independently shuffled parent epochs

**Research decision (implementation default, formal HPO not yet authorized):** While adapting V11 to cuifa's Windows 4070 Ti SUPER, a code audit exposed that the old 6,160 × 16 HPO recipe made only 98,560 parent draws from 108,478 independent Train structures, and the prior per-step random selection could repeat a parent across batches. The former phrasing "HPO uses the whole Train library" therefore described the *sampling pool*, not actual coverage. Rather than implying exposure to every structure, V11 now defaults to deterministic **epoch-wise shuffled, without-replacement** sampling, one complete 108,478-parent epoch per HPO candidate (6,780 steps at effective batch 16), two epochs for confirmation (13,560), with a shorter last batch and reproducible resume. The previous random-batch sampler remains selectable for provenance; no old results are reinterpreted as new full-coverage scores.

At the same time, separate GPU microbatches accumulate parent-weighted CE + same-parent JS before one optimizer update (effective batch unchanged), and HPO vs final-training platforms may vary CPU prefetch resources without changing the scientific contract. The motivation was **experimental exposure validity and practical hardware portability**, not a new model, changed RRUFF selection, or an observed accuracy improvement. Bounded local RTX 4060 smokes and microbatch/coverage tests provide only engineering evidence; cuifa Stage 0, large-data HPO and RRUFF evaluation remain unrun. See [current state](CURRENT_STATE.md) and [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

## 2026-11-04 · AlphaDiffract original-paper check and owner freezes RRUFF-Cu1011

After the user explicitly asked whether AlphaDiffract (Andrejevic et al. 2026) used a compatible RRUFF filtering protocol, the team checked the original paper's Methods §5.1 rather than inferring its sample policy from the abstract. Its evaluation uses **1362 curator-background-corrected XY + 2901 DIF**, progressive metadata/structure/cell and radiation conversion screening, **745** PXRD/DIF source label and lattice matches, then **734** after converting wavelengths without missing angular data. Importantly, **59 of the final 734 are calculated powder patterns**, and the authors used **20-keV/8192-bin/5–20°** input (10-model ensemble 81.74 ± 0.78%), not our original RAW/Cu Kα/V11 10–80° 3501-bin source. Thus their rigorous filtering provides a methodological precedent without forcing an identical sample count or author-mismatched test set.

The owner-requested additional full RAW–DIF six-cell-parameter cross-check found **758** close source pairs (≤0.1% lengths and ≤0.1° angles), **219** moderate source-pair differences (≤1% lengths and ≤1° angles) and **34** larger source-lattice discrepancies, including cell-setting-like differences. Those 34 cannot honestly be called AlphaDiffract-certified, but none had previously failed the project's **seven-crystal-system family** source label tests, and the project is not fitting full lattice parameters. Rather than optimizing the held-out sample list with future accuracy, owner-approved decision is to **KEEP and transparently flag the 34**, freeze primary RRUFF-Cu1011 membership and processing before model inference, and optionally report sensitivity on the non-flagged 977 as secondary analysis, never choosing the headline ex post. **134** main-set nonstandard symmetry symbol spellings are separately flag-labeled. Published comparisons to Bin Cao 1003, Lee, Salgado 908 and AlphaDiffract 734 must be cross-paper context or require same-1011 reruns for direct leaderboards.

**Immutable private freeze:** source ordered manifest SHA256 75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37; V11 1011x3501 inputs SHA256 19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179; freeze decision JSON SHA256 d258e3f85506e91867e2d9aebd73b77e2f777636bc6a8b722ebe28bf52129455. Source and code histories retained. See [final selection and AlphaDiffract rationale](RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md).

## 2026-11-04 · Whole-cohort physical audit: 1034 candidates become 1011 Cu-domain primary + 23 separately characterized records

After the owner considered an RRUFF-1034 main set and asked for **final verification of sources, labels, and preprocessing**, every original RAW and DIF file was audited against its SHA, RRUFF ID, sample label, diffraction sampling axis and radiation. The first audit appeared to find 21 broken x axes and 22 incomplete model windows; drilling into the raw bytes showed that scientific-notation intensities were being silently lost and a spurious -2009,10 source row was being treated as a measurement. These were parser defects, not scientifically justified reasons to discard good specimens. The pipeline was repaired, 19 isolated native theta typos corrected deterministically in derived arrays, one duplicate angle averaged, one impossible negative angle excluded, with untouched raw source archives and replayable logs.

The decisive scientific problem was **measurement-condition mismatch** rather than software strictness: **19 specimens explicitly said Mo radiation**, including 11 with paired calculated DIF files in Cu radiation. A Mo raw XRD spectrum cannot be treated as a Cu source merely because its DIF reference uses Cu. Three Cu-compatible spectra stopped at 60°/70° and could not supply complete measured 10°–80° model inputs. One Harmotome RAW comprised 232 irregular peak-like observations rather than a dense profile. The owner-preferred **1034 original records** therefore led to **1011 Cu-compatible, densely sampled, fully measured 10–80° primary spectra**, plus 19 Mo separate-domain candidates, three partial-window challenge spectra, and one quarantined sparse profile. The 1011 has a reproducible 3501-point source-only fixed input array, all seven labels, and cryptographic source/array prelock; no model accuracy was inspected or used for data selection.

This is a central research-methodology lesson: reject arbitrary source filters (such as failure to parse 24 valid nonstandard space-group symbols), **but keep physically meaningful measurement/wavelength and missing-observation distinctions**. The resulting 1011 has roughly the same sample count as the Bin Cao 1003 benchmark, yet the two sample cohorts and source vintages are NOT identical; no same-sample paper leaderboard should be claimed. Original RAW instrument wavelength is not always independently documented, and 134 noncanonical SG family labels in the Cu-primary carry explicit evidence tiers; scientific final certification is distinguished from engineering source prelock. Full record [RRUFF source QA and Cu1011 prelock](RRUFF_1034_FULL_SOURCE_AUDIT_CU1011_PRELOCK_20261104.md).

## 2026-11-04 · Exhaustive source-only reconsideration of remaining 13 mixed RRUFF specimens

After selectively reinstating two mild-impurity specimens into the proposed 1032 sample real-domain benchmark, the project owner asked to examine **all remaining 13** just as seriously rather than stop at the apparently clear examples. The method expanded from single named reference peak checks to all locally available reference variants, baseline/smoothing sensitivity, explicit overlapping-reflection analysis and separate exploratory two-phase NNLS fits, all run on the original RRUFF source spectra without any model inference. The audit produced **7** strong source-supported >10% impurity marker cases, **2** probable large extra-phase cases not formally certified because secondary identity/peak overlap remain unresolved, and **4** genuinely ambiguous cases. In particular, Rutile/hematite independent markers were weak despite 13% sample composition (mass fraction is not the Lee peak-height ratio); chlorite/Actinolite hovered near 10% depending on assumed chlorite family and signal processing; both garnets were structurally near-degenerate; Natrojarosite lacked a named secondary phase. The 13 source cases and all numerical uncertainties were documented and **none was inserted into the proposed 1032 primary Test**. Research lesson: correct application of a benchmark preprocessing rule requires preserving unresolved cases as unresolved, not arbitrarily inflating the sample count or treating ambiguous approximate two-phase fits as experimental proof. See [13-case audit](RRUFF_13_MIXED_SOURCE_AUDIT_20261104.md).

## 2026-11-04 · Historical proposal (superseded): 1030 to proposed 1032 after source-only revalidation

Having first proposed to remove all 15 explicitly mixed RAW profiles, the project owner reconsidered whether two weakly contaminated samples (Dickite/quartz R090054-1 and Polylithionite/corundum R060215-1) could legitimately meet an adapted Lee 2023 10% strongest impurity-peak criterion. Rather than reselect on machine-learning performance, a **blind source-data-only** validation was performed: 6 quartz and 13 corundum DIF reference variants, three background/smoothing settings and four quartz peak-position tolerances. The Dickite specimen passed an observed-total intensity **upper-bound** at 7.60–7.66%, giving high-confidence evidence. The Polylithionite specimen involved an impurity/main 35.17/35.15-degree overlapped reflection; a source-template-constrained estimate over 39 reference/preprocessing combinations was 7.08–9.33%, just under 10% but **dependent on reference-relative-intensity assumptions**. At that point in the decision history, the project prepared a transparent **proposed RRUFF-1032 candidate** retaining the two with different explicit confidence flags, leaving 13 mixed and 4 short-angular-range cases outside the main pool. That proposal was later superseded by the final RRUFF-Cu1011 source freeze; it is not a current cohort or scoring protocol. This decision demonstrates an important research lesson: neither automatic rejection of all minor impurities nor treating model-dependent deconvolution as direct quantitative proof is justified. See [the two-case source audit](RRUFF_TWO_LEE_BORDERLINE_FINAL_SOURCE_AUDIT_20261104.md).

## 2026-11-04 · Empirical Lee impurity peak screen of 15 RRUFF mixed specimens

After adopting Lee's >10% impurity/main peak-height criterion (borrowed from Lee's 52 self-measured powders, not Lee's RRUFF preparation), the project actually read and compared original RRUFF XY_RAW experimental profiles to main-phase DIF and independently named impurity-phase DIF reflections. Three background/smoothing settings and diagnostic peak SNR checks gave **7 strong source-supported impurity exclusions** (where an independently attributed impurity peak alone was >10% of the entire experimental spectrum's largest peak), **2 low observed ratios** of 7.0%/7.6% (still only provisional Lee passes because overlaps can hide impurity peaks), and **6 Unknown** due to unspecified impurities or unresolved phase overlap. Direct Rietveld phase decomposition was not performed. These are source-only evaluations; no model predictions or selection leakage. At that proposal stage, the RRUFF-1030 candidate was unchanged and fifteen source-annotated patterns were retained as proposed challenges; the later Cu1011 freeze superseded these roles. Auditable source file IDs, ratios, sensitivity estimates, and 15 figures saved privately. See [measured-source Lee audit](RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md).

## 2026-11-04 · Mixed-phase challenge screening rule updated to Lee 2023

Owner chose to screen the 15 known multi-phase/contamination RRUFF spectra by **Lee's 10% relative impurity diffraction peak-height threshold**, instead of automatic removal upon seeing a second phase in sample descriptions. Crucial method distinction: Lee applied that rule to its self-measured 52-powder Ex_dataset_1, **not** to its RRUFF Ex_dataset_2 (which used a separate low-angle background standard-deviation cutoff). Transferring the rule to our RRUFF case study is explicitly an **adaptation**. A source-only 15-case peak-identity/phase-reference worksheet was created privately; the 15 cases are currently **Unknown** for quantitative Lee eligibility until observed peaks can be attributed, and wt% cannot stand in for the intensity ratio. At that historical stage, the proposed 1030 primary set was unchanged pending the pre-inference audit; the final Cu1011 freeze later superseded it. Never reselect samples using trained model errors. This supersedes any earlier impression that all 15 must be deleted or automatically qualify as Lee-rejected impurities.

## 2026-11-04 · Superseded RRUFF-1030 proposal: 1030 headline / 19 hard cases

This proposal-time sequence retired RRUFF-70/301/350/371 for future use, then moved from 910 to 1049 after correcting software-only parsing exclusions, to 1045 after the angular-range screen, and to a proposed **1030 primary plus 19 challenge cases** after role assignment. Those counts and roles were later superseded by the owner’s final RRUFF-Cu1011 source-membership freeze. The 19-case list remains historical case-study material; it is separate from the 19 explicit-Mo sources and does not define current primary metrics. At the time of this proposal, source/label provenance and preprocessing review still blocked the then-planned Test freeze. See [RRUFF-1030/19 protocol](RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md).

## 1. From FerroAI to a measurement-centered problem

The project grew out of earlier materials-ML work that emphasized an end-to-end evidence chain: literature and data curation, model training, metric checks, failure analysis, and materials interpretation.

When choosing a new characterization problem, PXRD became attractive because it combines:

- public crystal structures;
- controllable forward simulation;
- physically interpretable peak-position / peak-shape / intensity changes;
- a stable crystal-system label;
- and a natural distinction between latent structure and measurement realization.

The initial question was not simply "can a network classify clean simulated patterns?" but whether a classifier remains reliable when the same structure is observed under plausible measurement variation.

### 2026-05-20—06-29：早期研究构想、文献吸收与一致性方法形成（2026-11-26 回溯补记）

**来源与性质：** 本节应研究者本人要求，依据 2026-05-20 至 06-29 的可检索历史对话摘录回溯整理；日期按检索记录的日期，区分研究者明确提出/确认的决定与助手曾提出的建议。不是原始聊天全文、穷尽式文献综述或实验运行记录；文献名及链接仅在摘录或仓库已有依据时列出，不把当时讨论等同于读完、复现或采用。2026-11-26 本人另确认 AugMix 为 JS 一致性直接灵感来源，见 [方法谱系](PXRD_NOVELTY_LITERATURE_LINEAGE.md)。本节保留早期设想及后来的收敛，不用后见之明把所有早期想法改写成现行方案。

#### 五月：从材料 ML、因果推断走向科学测量

| 日期 | 可追溯的讨论与决定 |
|---|---|
| 05-20 | 研究者提出暑期材料 ML 毕设：优先公开/模拟数据丰富、可呼应本校实验方向的任务，训练模型，可能加入因果推断限制层，初步希望 12 月前完成。助手推荐 XRD/PXRD/SimXRD，讨论 WPEM 的 diffraction consistency / Bragg-law constraint，并建议因果分析作为可靠性与偏差分析而非 MVP 核心；也比较 Raman、FTIR、UV-Vis、XPS、NMR、EIS、显微图像、晶体结构、工艺性能数据。 |
| 05-23 | 研究者认可工业测量与 ML 的落脚点，认为信号/图像处理可以落在 XRD/SEM，期望形成测量数据理解、信号/图像处理、ML、工程实现、可靠性分析等能力。助手补充 inverse problems、instrument-aware ML、uncertainty/OOD 等差异化方向。 |
| 05-25 | 研究者认为单纯分子预测方向偏窄；助手提出 XRD perturbation robustness benchmark，利用 SimXRD-4M，而非低配复刻其分类任务，关注 realistic measurement perturbations、failure mode、raw profile/peak-list、峰位与强度、sim-to-real、混相及置信度。同期 Raman/FTIR/NIR 的噪声、基线漂移、峰位偏移鲁棒性也被讨论，但未检索到特定 Raman 论文题名。 |
| 05-29 | 在对比可控数据任务后，XRD 被认为便于以 CIF/SimXRD 自行生成数据，实现 clean → corrupted → prediction → reliability audit。助手提出 SimXRD-based causal stress-test benchmark：XRD → crystal symmetry，以 noise、broadening、texture、zero shift 构建 unbiased/biased/intervention 数据，检查 shortcut learning。 |
| 05-30 | 研究者明确要求后续优先检索别人如何处理类似技术问题以及论文/benchmark 先例，避免“先射箭后画靶子”。助手建议将 confounding 定义为 protocol/source-induced 而非简单制造 label→nuisance 相关；预设扰动、强度和划分，并用 counterfactual pairs 检验同结构换扰动应保持预测、不同结构同扰动仍应有区分力。 |

#### 六月上旬：从 measurement intervention 到 consistency regularization

| 日期 | 可追溯的讨论与决定 |
|---|---|
| 06-01 | 助手提出 clean baseline → physical perturbation stress test → intervention-aware/consistency training，扰动包含 peak shift、broadening、noise、background。研究者明确回复“很好很好，记住”，确认该暑期 SimXRD/XRD scientific ML MVP 主线及边界。备选题目为 *Physically Motivated Measurement Interventions for Robust XRD Symmetry Classification* 与 *Intervention-Aware Robust Learning for XRD-Based Crystal Symmetry Classification under Measurement Perturbations*。 |
| 06-05 | 研究者要求先建立学姐式 data → preprocessing → model → metric → error analysis → figures 的完整基础 pipeline，再加入 physical measurement perturbation、robustness、consistency/invariance；坚持保留 invariance。助手提出 *Physically Motivated Invariance Learning for Robust XRD Symmetry Classification under Measurement Perturbations*，用 f(x_clean) ≈ f(x_perturbed) 表达目标；zero shift/noise/background 是候选 nuisance，broadening 需要限制范围，strain/phase transition 不应一概视为 invariant。 |
| 06-06 | 仍以 SimXRD/XRD physical perturbation/invariance robustness 定位，并讨论 scientific measurement ML、materials informatics、inverse problems。 |
| 06-07 | 项目工程闭环被描述为 clean baseline → 物理扰动 → FlipRate/robustness audit → augmentation vs consistency/invariance → real XRD validation。助手根据当时讨论的学校真实 XRD 数据条件将 real validation 纳入规划（非数据已取得或实验已完成）。当时英文表述：*Controlled SimXRD robustness benchmark + real XRD validation for AI-assisted phase/symmetry identification under measurement perturbations.* |
| 06-11 | 研究者认可从其他领域迁移 consistency regularization，明确将其作为项目主方法、因果推断降为背景。助手提出 XRD-specific robustness benchmark + physics-informed perturbation operators + consistency-based invariant learning，并讨论 accuracy drop、flip rate、prediction consistency、calibration；另建议 *Physics-guided Weak-to-Strong Consistency Regularization for Robust XRD Classification*。当时 weak-to-strong、KL/MSE 等为候选，并非已经冻结的 Dynamic JS 实现。 |

#### 六月中下旬：四组消融、物理边界与方法来源

- **06-16（目前检索到的最早明确四组记录）：** 助手列出 ERM baseline、Aug-only、Consistency-only、Aug+consistency，要求扰动具有物理依据且 label-preserving，并评估 accuracy、FlipRate、calibration/OOD。另建议先检查约 20 条谱及标签，建立 1D-CNN baseline，曾写出 CE + lambda·KL/MSE 的候选损失。
- **06-27：** 研究者独立提出并要求评价 measurement-invariance 下的 consistency regularization 研究方案。讨论将贡献定位为 XRD-specific label-preserving measurement interventions、paired reliability benchmark 与检验普通 augmentation 是否足够，而非发明新正则项。助手再次明确四组消融、已见/未见/复合扰动和真实 XRD，以及 FlipRate、prediction consistency、ECE/calibration；若 Aug-only 已足够应如实报告。术语上更倾向 physically motivated consistency regularization，而非将其夸大为严格物理约束求解。
- **06-28：** 讨论 SimXRD、paired intervention、physics-bounded consistency、FlipRate/JSD/ECE 与 WPEM/Bin Cao 等背景；zero shift、背景/噪声、轻微仪器展宽通常作为候选标签保持扰动，强应变、相混合、严重 texture 暂不直接用于一致性约束。此为当时的适用边界讨论，不替代后续冻结的 texture 等具体实现。
- **06-29：** 继续对比 XRD-ML 文献、EELS calibration-invariance 及跨领域一致性方法；AugMix 被讨论为多视图 JS 一致性的参考，拟改为物理扰动；还讨论 GroupDRO、feature consistency、预处理校正后分类等替代路线。研究重点仍是普通 ERM/增强/预测一致性对照及 FlipRate、worst-condition accuracy。

当时的四组概念设计是一个 augmentation × consistency 的 2×2 消融：

| 历史实验组 | 物理扰动谱的标签监督（augmentation） | 显式预测一致性 |
|---|---|---|
| Clean ERM | 否 | 否 |
| Augmentation-only | 是 | 否 |
| Consistency-only | 否 | 是 |
| Augmentation + Consistency / Full | 是 | 是 |

这里的 “consistency-only” 并非无标签或无扰动输入，而是指不额外以扰动谱的类别 CE 作为增强监督、仍利用扰动视图计算一致性。此表是概念层面的复原；各早期版本的确切 loss 权重、视图采样方式及是否实际运行需另查代码和 run records。后续收敛为 Dynamic ERM vs Dynamic JS，匹配两张扰动谱、标签、backbone、训练预算及扰动分布，唯一额外目标为 same-parent JS。四组历史方案不是当前重新运行的任务。

#### 当时讨论的文献与方法（按历史讨论用途，而非重要性排名）

| 文献、方法或线索 | 可追溯讨论 | 当时用途/边界 |
|---|---|---|
| Karniadakis 等，*Physics-informed machine learning* | 05-20 | 物理信息学习背景；不是本项目具体损失的来源。 |
| Ziatdinov 的 STEM 因果分析（06-11 摘录提及 2020 npj Computational Materials）；Kalinin 相关科学成像方向、AtomAI | 05-20、06-11 等（具体论文尚待核） | 观测偏差、confounding、科学成像与因果启发；未确认完整书目，不凭记忆补题名。 |
| WPEM / XRD refinement | 05-20、05-25、06-07、06-28 | diffraction consistency、Bragg-law constraint、PXRD 峰重叠与物理约束背景；当时不是分类一致性损失的直接来源，完整书目待核。 |
| [SimXRD-4M](https://arxiv.org/abs/2406.15469) | 05-25、06-11、06-28 | 大规模模拟 XRD 与晶体对称性分类基准；提供数据/任务基础，避免仅复刻分类。 |
| Bin Cao, *Physics-Constrained Learning of Crystal Structures and Properties from Powder Diffraction*, thesis (May 2026) | 06-07、06-28 | 物理约束 PXRD 的相关研究线索；当时可见 thesis/摘要信息，未确认完整阅读。 |
| Chatzidakis & Botton, *[Towards calibration-invariant spectroscopy using deep learning](https://doi.org/10.1038/s41598-019-38482-1)* (2019) | 06-07、06-29 | EELS 的校准不变性、光谱测量条件变化与泛化的类比；非 Raman，非 JS consistency loss 来源。 |
| Lee et al., *A Deep Learning Approach to Powder X-Ray Diffraction Pattern Analysis: Addressing Generalizability and Perturbation Issues Simultaneously* (2023) | 06-11 | PXRD 物理扰动、增强及泛化领域先例。 |
| Szymanski/Bartel/Ceder 多相衍射 probabilistic deep learning；XQueryer | 06-11 | PXRD 相关先例与其他任务比较；历史摘录没有提供具体完整书目。 |
| [Mean Teacher](https://arxiv.org/abs/1703.01780)、FixMatch、UDA、[VAT](https://arxiv.org/abs/1704.03976)、Cross-Consistency Training | 06-11、06-29 | 半监督/跨领域 consistency 思想参考：不同视图/模型预测稳定、弱强视图等；未意味着采用其伪标签或训练机制。 |
| [ImageNet-C/P](https://arxiv.org/abs/1903.12261) | 06-11 | 系统化 corruption/perturbation 测试与预测稳定性指标的参考。 |
| 医学影像 domain adaptation / scanner-protocol shift | 06-11、06-27 | 仪器和测量域变化下稳定识别的类比；未确认具体医学论文。 |
| XRDMatch | 06-29 | XRD 半监督弱强视图一致性领域先例；历史讨论中的完整论文题名及 DOI 需单独核对。 |
| KBSS | 06-29；后续 07-13 历史笔记 | 知识引导增强与同对象视图预测一致性的思想参考，不移植其代码。详见 [原笔记](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/KBSS_PROJECT_RELEVANCE.md)。 |
| Hendrycks et al., [AugMix](https://arxiv.org/abs/1912.02781) (ICLR 2020) | 06-29；11-26 本人回溯确认 | JS prediction consistency 的直接灵感来源；将图像增强视图思想重新解释为物理测量视图。 |
| *[Machine learning in X-ray diffraction for materials discovery and characterization](https://www.sciencedirect.com/science/article/abs/pii/S2590238525003157)*, Matter (2025) | 06-29 | 当时讨论 physics-agnostic XRD-ML、experimental artifacts、transferability 和 responsible reporting。 |
| XRPD 测量扰动/物相识别论文（题名未检索到） | 06-29 | 当时讨论 noise、baseline、constant theta shift、peak-width irregularity 与更困难的 preferred orientation/poor particle statistics，以及峰位/强度的相对作用。 |
| FlexMatch、GroupDRO、feature consistency、预处理校正后分类 | 06-29 | 候选算法与替代路径，不代表最终采用。 |

**EELS／Raman 回忆纠正（2026-11-26 本人确认）：** 此前记成 Raman 的光谱测量不变性论文实际为 Chatzidakis & Botton (2019), *[Towards calibration-invariant spectroscopy using deep learning](https://doi.org/10.1038/s41598-019-38482-1)*（EELS）；AugMix 为 JS 一致性直接灵感来源。五月的 Raman 讨论仍保留，原独立 Raman 论文待考线索关闭。见 [方法谱系](PXRD_NOVELTY_LITERATURE_LINEAGE.md)。

**历史意义：** 五月最初的因果/物理限制探索，经过测量干预、预测不变性、跨领域一致性方法和四组消融，逐步收敛为同母结构的测量等价关系监督。研究者在 06-01 确认主线、06-05 坚持 invariance、06-11 选定一致性正则化、06-27 明确研究问题；这些是可追溯的科学方向与设计决策。助手提供的备选算法、文献提示及具体实验建议分别保留，不追认成研究者独立提出的全部细节或已完成成果。当前方法、结果冻结和执行边界仍由 [CURRENT_STATE.md](CURRENT_STATE.md) 及冻结证据决定。

## 2. Physical perturbation and dynamic augmentation

Early versions built a simulator around label-preserving PXRD variation: peak-position shift, peak broadening, preferred orientation, background, and noise.

A key methodological lesson was that **data generation itself had to be treated as part of the scientific design**. Perturbation families were progressively tied to literature, physical mechanisms, and frozen numerical ranges rather than used as arbitrary image-style augmentation.

Parent structures were split before generating measurement views so that different spectra of the same parent could not leak across train / validation / test.

## 3. Over-expansion and the Residual branch

One stage explored richer objectives, including a Residual-style idea intended to separate structure-related and measurement-related information.

This branch was not forced into the final method. Analysis showed that, in PXRD, measurement effects such as peak shift, broadening, and texture are coupled to the underlying peak arrangement. A residual between two spectra therefore need not represent measurement state independently of crystal structure.

The Residual route was archived rather than rescued by adding more auxiliary losses.

**Lesson:** a physically appealing decomposition is not automatically a valid inductive bias.

## 4. Backbone diagnosis: PAMPT to ResNet

A major turning point came from diagnosing model learnability rather than immediately blaming the data pipeline.

The earlier PAMPT configuration did not sufficiently fit the training task, while a mature 1D ResNet could. Replacing the backbone restored strong learning and made dynamic perturbation training beneficial instead of unstable.

This changed the interpretation of earlier failures: the dynamic data scheme itself was not necessarily the bottleneck; there was a substantial **backbone–augmentation interaction**.

ResNet-18-GN was therefore adopted as the public common backbone for the controlled ERM–JS comparison.

## 5. Convergence to a JS-only controlled comparison

After the backbone diagnosis, the main line was deliberately simplified.

Dynamic ERM and Dynamic JS were matched on:

- parent structures;
- two-view exposure;
- perturbation distribution;
- backbone;
- optimizer and training budget;
- checkpoint and evaluation rules.

The intended scientific difference became narrow and testable:

> Does explicitly using the known same-parent relation add value beyond ordinary label supervision when data exposure is otherwise matched?

JS consistency was retained as a simple implementation of that question. The project stopped treating "more algorithms" as progress.

## 6. From "robustness" to provenance-aware relationship supervision

The framing then changed again.

Calling the whole project "robustness research" described an important outcome but not the most distinctive method idea. The simulator does more than generate perturbed spectra: it retains **parent identity**.

For one parent crystal, multiple generated spectra are not merely samples with the same class. They are different measurements of the **same latent physical object**.

This led to the current chain:

~~~text
shared parent identity
      ↓
measurement equivalence
      ↓
relationship supervision
      ↓
prediction consistency
~~~

The simulator is therefore used as:

> **data generator + relationship supervisor**

This is the current method-level interpretation.

### 2026-07—08 中旬：研究思想与实验决策的同期证据（2026-11-26 考古补记）

**Research decision:** 回补 V6→V9/V10、真实域与反演分岔的研究思想史，尤其保留被放弃的方案、实验如何改变判断，以及当时尚未回答的问题。依据以下同期或接近同期文档，而非将后来的成熟叙事倒灌为早期原话：

- [旧版 PROJECT_JOURNEY.md](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/PROJECT_JOURNEY.md)（含逐日决策与 08-11 时效说明、08-13 反演设想，约 4.8 万字符）。
- [KBSS 思想吸收笔记，07-13](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/KBSS_PROJECT_RELEVANCE.md)。
- 07-25 的十页技术简报 `PXRD_robust_learning_project_architecture_for_Haotian_Hu_v4_architecture_page_replaced.pdf`（研究者文档库原件，日期化快照；用于与 Hu et al. 方法进行技术讨论，不证明实际会谈或对方答复）。
- 08-07 的交接文件 `AI4Science_Project_Handoff_for_Admissions_AI_2026-08-07.docx`（研究者文档库原件，含当时结果与申请叙事；其中较强证据表述由 08-11 审计覆盖）。
- [08-08 的 Application Research Narrative V1](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md)（保留历史 supersession notice）。

完整的六月中下旬至八月中旬原始聊天目前未恢复；以下是上述文档中的决策、记录及历史技术讨论的归纳，不冒充逐字对话。数值仅用于解释当时的决定，不是重新定义现行结果。

#### 1. V6/V7：从测量不变性走向复杂学习方案

- 六月已有 augmentation × consistency 四组概念消融；V6 进一步将 PAMPT 峰形感知骨干、Offline/Dynamic ERM、Dynamic JS、Dynamic Residual、物理扰动和 OOD 评价组织成可运行流程。
- V7 补上 reflection-level March–Dollase 择优取向，使五类扰动涵盖峰位、峰形、相对强度、背景和噪声；又引入 25/50/100% 独立训练结构预算。后者回答的是另一项科学问题，不能与测量域泛化自动合并。
- 07-13 的 KBSS 代码审计已区分弱/强视图、伪标签筛选、论文与实现是否一致、初始化缓存与训练时动态生成；决定仅吸收高层预测稳定性思想，不移植其代码。AugMix 是研究者后来明确确认的 JS 直接灵感来源。

#### 2. 07-15—16：一度放弃 JS，尝试结构化模拟与测量表征

V8 将独立算子随机化视为尚可改进的模拟范式：先采样虚拟 sample/instrument/acquisition state，再采样条件相关的五扰动参数；不强制所有扰动相互相关，强调同一物理机制内部一致、参数有文献/代码/公式依据以及合理生成顺序。拟比较 Independent Dynamic ERM、Structured Dynamic ERM、Structured Dynamic + Residual。

- 07-15 删除 Structured Dynamic + JS 正文组，并移除独立结构样本效率轴，避免把多个科学问题塞入同一主实验；取消无依据的“最多两个强扰动”规则。Independent Dynamic ERM 借用 XRDMatch 的算子级独立在线随机化思想，不复制其半监督训练或具体算子；完成软件 smoke，而非科学结果。
- 当时也讨论扰动差参数监督（AugSelf 式思路）：令两视图特征差预测模拟器已知的测量参数差，同时降低晶系信息；复杂连续/离散/结构化标签及可辨识性问题使其成为独立未来支线。
- 07-16 V9.2 将结构化联合模拟归档为未来模块（状态变量与联合分布缺少足够证据冻结）；形成测量参数监督与 matched ERM/JS/Residual 比较的双轨计划。真实仪器被定位为 external validation，而非某台仪器专属模拟器的必要前提。

#### 3. 07-22：一致性假象、权重治理与 Raman 第二项目

- 复核 Hu et al. SD3Net：论文 Table 5 的去相关权重 lambda_3=1 与 Fig.12 中约 1e-4 的 regularization parameter 不应混为一谈。外部论文是机制及敏感性实验先例，不是 PXRD 权重的来源。
- 初始 Train-only 128-step 审计 late 段分类准确率 11.96%、CE 1.9499（近 ln(7)），两个视图 top-1 一致率却 99.34%、JS 约 2.97e-7；residual probe 也接近随机。**尚未学会的模型可以表现出虚假的一致性。** 不把巨大梯度比倒数当权重提案，不把随机 probe 当作已成功去相关。
- 后续 learned-state audit 以 Train-only ERM 学习里程碑取样；三个互斥 700-parent 子集分别用于 detached probe 训练、probe 审计、loss/gradient audit。到 epoch 5，主任务和 probe 已有学习信号，probe accuracy 32.57%、raw JS 中位 0.01862、top-1 disagreement 35.42%。由此才能解释辅助梯度尺度。最终以 Train-only 证据冻结旧 PAMPT 候选 JS [0.3,3,30]、Residual [0.2,2,20]，不接触 Validation/Test/real。相应 BF16 容差与未授权阈值修订见同期 PROJECT_JOURNEY；不把 gate 当科学性能结论。
- 复现性也从“保存模型”升级为 checkpoint/resume 同一随机流、后续 loss 与模型哈希的等价性；同期记录 12/12 检查通过。
- 同日另有 **Raman mapping 第二项目**：两份 undoped/doped 文件，每份 26×26×829，虽共有 1,352 条像素谱，却只有两个独立样品。随机像素划分可能泄漏样品与批次；MATLAB 原型只完成读取、积分、绘图与空间显示。决定不替代 XRD 主线，不用 3D CNN/Transformer 强行做两样品分类，优先描述性 PCA/NMF；未来在更多独立样品、批次和可靠标签下研究空间-光谱自监督、解混/分割、异常检测。这是后续科学光谱研究兴趣的同期线索，不是已完成 Raman ML 项目，也与此前误记为 Raman 的 EELS 论文是两件不同的事。

#### 4. 07-25：三种学习原则与失败机制的讨论

7 月 25 日技术简报中的正式设想是同一母结构、同一动态 pair stream 和计算预算下，比较普通增强、JS 和 residual 类别去相关。PAMPT-B3 尚为公共骨干，正式调参 0/7、多种子 0/15，RRUFF-70 当时仅完成规划；P0 的 JS 为 promising but seed-sensitive，Residual 独立 probe 约 29–31% 对 14.3% chance，收益区间跨零。V10 无条件测量监督提升背景/展宽/噪声可解码性，却同时提高 signed/symmetric residual 晶系泄漏（相对 matched V9 分别 +0.01429/+0.03714 accuracy），因而归档。

简报列出的五个待讨论问题值得完整保留其含义：① SD3Net 的跨域残差思想迁移到同晶体双视图时，symmetric absolute residual + adversarial class entropy 是否合适；② 不稳定来自优化/交替训练还是结构性的目标冲突；③ 如何区分内部 discriminator 被欺骗和独立 probe 真正无法读出类别；④ 是否可用 stop-gradient semantic context 条件化 measurement decoder；⑤ 哪些 OOD/real 指标之外的机制证据（probe、effective rank、class separation、residual norm、flip、profile sensitivity、representation visualization）才足以支持论文。它们是当时开放的技术问题，不声称已得到 Hu 的反馈或最终解决。

参考文献按 07-25 简报保留：Hu et al., *Hyperspectral single-source domain generalization via structured data simulation and domain-disparity decorrelation*, Knowledge-Based Systems 348 (2026) 116429；Lee et al., *A Deep Learning Approach to Powder X-Ray Diffraction Pattern Analysis: Addressing Generalizability and Perturbation Issues Simultaneously*, Advanced Intelligent Systems 5 (2023) 2300140；Schopmans, Reiser & Friederich, *Neural networks trained on synthetically generated crystals can extract structural information from ICSD powder X-ray diffractograms*, Digital Discovery 2 (2023) 1414–1424；Oviedo et al., *Fast and interpretable classification of small X-ray diffraction datasets using data augmentation and deep neural networks*, npj Computational Materials 5 (2019) 60；Yu et al., *A Knowledge-Based Semi-Supervised Crystal Property Prediction Framework with Consistency Regularization*, IEEE TKDE (2026)。这些为同期简报书目，不代表本轮重新核验每篇原文。

#### 5. 07-26—28：先验证地基，再决定算法

- 07-26：旧 PAMPT 七条 Validation-only run 在 30,650-step 固定终点协议完成，曾选择 JS=3 / Residual=2；发现仅终点评估不能证明收敛，故重订最长 100 epochs 与预注册 early stopping。之后更换 family-disjoint 为按晶系分层的 exact-parent-disjoint split，旧选择及 run 作废，不外推。另有 Git provenance 缺口导致首轮停止并重启等工程审计。
- 07-27：新 split pilot ID Macro-F1 约 0.42、OOD 约 0.36，排除旧 family split 为主要瓶颈；Foundation Gate 3 的 matched Clean 诊断将 PAMPT-B3 与 ML4pXRDs ResNet-18-GN 比较：Train accuracy 0.638494→1.0、level-0 Macro-F1 0.532749→0.652168、OOD 0.289676→0.403163。决定先更换骨干，不把训练失败归因于物理增强。
- 07-28：sqrt preprocessing、Adam、warm-up+cosine 三项 Clean 诊断未改善原 ResNet 主指标；matched Dynamic ERM 诊断将 OOD 从约 0.4032 提升到 0.6563，表明旧动态训练崩溃主要是 backbone interaction。Residual 独立 probe 三 seed 稳定性 gate 在 epoch 3/5/10 为 2/3、1/3、2/3，未通过预注册要求，因此不改阈值救方法；正式主线收敛至 Dynamic ERM vs JS。重新冻结 JS [3,30,60] 的 Train-only 梯度网格，并预注册四条 Validation-only 比较；此前七组合同关闭。此处的四条是超参数比较，与六月四组消融不同。

#### 6. 08-03—13：关系监督、真实域证据与可辨识性

- 08-03：云端十个 checkpoint 的哈希恢复证明产物完整，但归档不含性能摘要；随后与权威 Git 同步取得五 seed 的 Validation OOD 证据，全部 favor JS lambda=60。冻结 simulated Test 平均 paired gain +0.054600；monoclinic、shift/texture 部分 profile 仍有下降，不能宣称处处有效。
- 同日 RRUFF 先扩至 350，再至 371（70 legacy + 301 extension）的历史设计；角色后来重新划分。矿物名重叠提醒外部测量域 transfer 不等于 unseen-mineral generalization。
- 08-04：opXRD 铁电氧化物/陶瓷真实谱可行性模型盲审计 NO_GO。原因是数据采集对象与标签可用性不匹配，不靠放宽阈值虚构有效样本；未以模型结果筛数据。
- 08-06：尝试将真实域任务定义为谭启组功能陶瓷相态识别（single phase / polymorphic coexistence / secondary phase），而非强凑七晶系；保留通用预训练、Scratch/ERM/JS 适配比较和独立物理样品/配方批次分组原则。属于 prospective 下游研究设想，非已完成 benchmark。
- 08-07—08：交接与研究叙事明确区分 Materials Science enabled by ML 与 ML motivated by a scientific problem；从更多真实模拟谱转向同样数据暴露下的 learning principle；将 x1=g(s,m1)、x2=g(s,m2) 的同一潜在物体关系变成额外监督。保留 Backbone–Augmentation Compatibility、simulator provenance、label-efficient transfer、科学数据语义等思想。RRUFF-70 的 monoclinic 负迁移现象在 RRUFF-301 历史结果中未复现，提示小样本机制叙事风险；trigonal/hexagonal 标签错误被发现并纠正。校准分析属补充，非主贡献。
- 08-11：从代码、confusion matrix、逐条预测与哈希反校叙事。确认实际完成的是分类，不是参数反演；360/360 profile 的旧命名 per_crystal_system_f1 字段需纠正，主 Macro-F1 等不受影响；正式 split 只有 exact-parent-disjoint，不是 formula/family-disjoint；RRUFF-301 原 runner、support IDs、授权及 runtime binding 缺失，虽指标可重算，证据降为 retrospective，不能称 confirmatory。上述 08-07/08 的较强历史表述以本条及当前权威证据为准。
- 08-13：另立 known-template identifiability-aware sample/instrument inversion 候选，以 isotropic lattice strain 和 instrument zero shift 两变量为最小问题；前者角度相关、后者为常量，但需 Jacobian/Fisher、参数碰撞搜索和 classical multistart fit 证明可辨识性，不能以网络分数代替。扩维分级、forward discrepancy 辅助目标及 operator-mismatch panel 为计划，不是训练结果。该时期开始将科学测量主线延伸到 inverse problems，分类证据不因此改变。

#### 7. 新找回的同期研究储备原稿（同日继续考古）

- [07-15 研究支线原始快照](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/XRD_future_research_branches_2026-07-15.md) 与 [FUTURE_RESEARCH_DIRECTIONS 扩展稿](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/FUTURE_RESEARCH_DIRECTIONS.md)：前者是日期化且被扩展稿标为用户确认的快照，明确列出 AugSelf、AET、DDG 与 weakly supervised nuisance disentanglement 的联系（原稿仅列方法名，不补造完整文献引用）。一条分支从两视图差 r=h2-h1 预测已知扰动差并减少晶系泄漏，建议先研究峰移与展宽；另一条分支以独立晶体结构而非增强谱数量为数据单位，原始候选预算 10/25/50/75/100%，扩展稿举例 10/25/50/100%，讨论在线视图收益饱和、结构与视图多样性的替代关系、计算预算和代表性/主动采样。这些是计划，而非已运行实验。两份原稿已明确将研究区分为数据生成机制、表征学习机制、独立样本利用效率三个层次。
- [08-01 Measurement Parameter Inversion and Calibration 原设计](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/future_modules/PXRD_MEASUREMENT_PARAMETER_INVERSION.md)：早于 08-13 的样品—仪器联合反演。其问题不是完整结构重建，而是能否从谱估计 nuisance 参数、何时可辨识、显式校准是否改善分类。候选参数为零偏、有效展宽、背景幅值、计数噪声尺度，讨论不同参数的可辨识性、信息损失、混杂、选择性校准与不确定性。原设计还提出 classical/statistic baseline、parameter collision search、SNR/峰数/重叠分层、identifiability map、heteroscedastic regression/ensemble/conformal、uncertainty-gated calibration，以及反对无物理依据的锐化和补造峰信息。其对 V9 的互补性为学习不变性 vs 显式估计与校正；原稿为 SEALED_FUTURE_MODULE，不是已实现反演。
- [08-13 Identifiability-Aware Joint Sample–Instrument Inversion 原设计](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/00_project_context/future_modules/PXRD_IDENTIFIABILITY_AWARE_SAMPLE_INSTRUMENT_INVERSION.md)：作为 08-01 的 sibling module，由六参数直接回归收缩至 known-template 两自由度；正号 forward discrepancy 与监督回归作唯一学习目标差异，并要求 Jacobian/Fisher、碰撞、经典多起点拟合、可微 renderer 的有限差分核验及 operator mismatch。特别保留“合成参数标签本来存在，低标签只是人为 mask 的受控消融，不等于标签昂贵”和“谱残差下降不等于参数恢复正确”的方法学边界。原稿没有授权训练；历史设想的后续状态以当前权威记录为准。

**思想史价值（本轮回顾）：** 这不是从一开始就知道终点的成功故事。七月曾主动移除 JS、探索复杂表征；随机一致性假象、probe 失败、数据划分及 backbone 诊断迫使问题重构；八月将物理观测的同源关系识别为监督信息，又对已获得结果进行证据降级和纠错。应保留这一过程及未解决的问题，而非仅保存最后分数。七月至八月完整原始聊天仍是待恢复材料；本节不改变冻结结果、研究任务、执行授权或当前 scientific framing。

## 7. Frozen simulated evaluation

With the method and hyperparameter selection frozen through the validation protocol, the final simulated single-factor OOD comparison showed a consistent gain across five matched seeds.

Headline Test Macro-F1:

- Dynamic ERM: 0.65074 ± 0.00721
- Dynamic JS: 0.70534 ± 0.00977
- paired gain: +0.05460
- positive direction: 5/5 seeds

The largest perturbation-specific gains were observed for peak broadening and preferred orientation, motivating the interpretation that same-parent supervision is especially informative when the measurement change is strongly coupled to the concrete diffraction structure.

## 8. Experimental-domain evidence: RRUFF and CNRS

Two experimental domains were kept separate because they answer different questions.

### RRUFF-301: few-shot adaptation

RRUFF-301 tests whether the simulated pretraining is more label-efficient when a small number of real spectra are available.

At K=1/2/5 labels per class, the JS-pretrained model produced higher locked-test learning curves than the ERM-pretrained model. This is treated as **few-shot adaptation / label-efficiency evidence**, not unseen-mineral generalization.

### CNRS-318: zero-shot external-domain evaluation

CNRS-318 is a separate, naturally imbalanced zero-shot external-domain stress test. No CNRS label is used for adaptation.

Across five matched seeds, the relative Macro-F1 comparison favored JS in all five runs. Absolute scores remain low, and the structure-derived labels were not manually verified spectrum by spectrum, so this result is deliberately framed as supporting relative evidence rather than proof that the sim-to-real problem is solved.

## 9. Reporting-policy correction

Another important correction concerned evaluation standards.

The project initially treated strict statistical auditing too much like a binary gate. The reporting policy was later reorganized into three layers:

1. community-standard performance reporting;
2. probability-quality / reliability evidence;
3. strict paired and bootstrap uncertainty auditing.

Negative or uncertain statistics are retained, but a single cross-zero confidence interval no longer automatically erases an otherwise transparent multi-metric, multi-seed result.

## 10. Secondary inversion work

A separate xrd_inversion line studies numerical quantitative inversion. Its first structure–measurement factorization proposal received a preregistered **NO-GO** and was archived.

The surviving inversion module focuses on auditable forward-model and numerical-recoverability infrastructure. It is intentionally separate from the completed classification evidence.

## 11. 2026-10-08: prospective undergraduate thesis plan (not active research)

For future graduate applications, a possible undergraduate thesis direction was formulated: predict a limited set of structural and measurement parameters from PXRD; reconstruct a theoretical pattern with a forward physical model; then test whether a reconstruction-based **auxiliary** training constraint improves parameter accuracy, data/label efficiency, or training behavior under specific conditions.

This is not a claim of new work completed and not a return to the failed factorization Stage 1. In September 2026, the earlier 2×2 structure–measurement factorization intervention received an explicit preregistered **NO-GO**; the original prediction–forward-reconstruction idea also lost stand-alone novelty weight after related-work review. The new plan therefore explicitly studies **when physics helps and when it fails**, rather than promising improvement or silently reopening that archived experiment.

The conceptual path is now recorded as: provenance-aware PXRD classification (completed main line) → constrained physical parameter inversion (possible undergraduate thesis) → broader AI for scientific measurement, reconstruction and inverse problems (longer-term direction).

**Status:** FUTURE / CANDIDATE; see [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md).

## 12. 2026-10-13: revisit simulated parent-structure efficiency (planned, not run)

An earlier design for `10/25/50/100%` stratified nested training-parent subsets was restored to test the supervision-efficiency consequence of parent provenance. The unit of information is the **independent parent structure**, not synthetic spectrum count. Two-view Dynamic ERM and Dynamic JS (`lambda=60`) will be compared at identical parent, generated-view and optimizer-step budgets.

This design was previously deferred while the JS-only method was still being stabilized; revisiting it **after freezing the main method** now makes it a precise supplementary test. It does not change the original study, does not rerun RRUFF few-shot adaptation, and does not claim that equivalent performance has already been achieved with fewer parents.

The first task is code/data audit and matched fixed-step implementation, because the public epoch-based runner has partial-batch and per-epoch validation behavior that must not confound different parent budgets. The old simulated Test has already been evaluated; this new analysis will be explicitly post-main supplementary work.

**Status:** PROPOSED / NOT_RUN; protocol: [PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md](PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md).

## 13. 2026-10-18: pivot to calibrated pre-refinement assistance; coexistence as a safety boundary (proposed)

**Date / status:** 2026-10-18 / PROPOSED, NOT_STARTED. No new experiments, thesis approval or guaranteed real-data volume.

**Question / prior assumption:** The October 8 candidate framed undergraduate inversion primarily as direct continuous-parameter prediction aided by differentiable PXRD reconstruction. In subsequent discussions the prospective real spectra from a collaborator appeared likely to be scarce, so treating experimental data as the main training set was unrealistic. The candidate also oscillated between very narrow single-phase tetragonal regression and a much larger universal/multiphase ferroelectric project.

**New reasoning:** Retain simulation-trained modeling but focus on what a diffraction expert can actually use *before* conventional refinement: Top-K candidate single-phase structures, simulation-domain-calibrated candidate probabilities, phase-conditional lattice-parameter initializations and estimated intervals, plus forward-pattern checks. Limit the main 12-week scope to one selected ferroelectric ceramic family (family choice pending the collaborator's sample list). ECE concerns probability calibration over datasets; candidate probabilities do **not** represent constituent phase fractions.

**Decision / what changes:** A new [12-week pre-refinement plan](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md) specifies six biweekly milestones. Two-phase coexistence must be represented as a **risk to the single-phase assumption**, evaluated with plausible synthetic mixtures and a possible reject/review output. Explicit two-phase hypothesis testing is optional; quantitative phase fractions and broad multiclass/multimaterial models are future directions. Differentiable reconstruction loss is optional rather than obligatory; physics verification and refinement initialization are the central workflow.

**What does not change:** Completed `xrd_robustness/` frozen JS-only results, the older inverse numerical gates, the archived preregistered factorization NO-GO, and the historical October 8 plan. The new proposal is not an experimentally supported result.

## 14. 2026-10-18: candidate multi-family routing architecture (discussion, not adopted)

**Previous issue:** The latest 12-week project deliberately selects one known ferroelectric ceramic family to keep a simulation-trained, calibrated phase-hypothesis and parameter-initialization study executable; the user then suggested building separate simulation databases/experts for popular families (e.g., PZT, BaTiO3, KNN), with an upstream material-family decision.

**Reasoning/correction:** This is a plausible *modular extension*, but XRD-only inference of a sample's chemical family is not reliable in general for related perovskite ceramics; refinement workflows frequently have nominal sample composition available. Prefer a metadata-guided family router with an explicit unknown/mismatch/review option. Family-specific phase prototypes, simulators/parameter supports and calibration could use a shared interface; auto family recognition is a distinct optional inference problem.

**Decision status:** ARCHITECTURE CANDIDATE / NOT ADOPTED AS 12-WEEK MUST-DO / NO DATA OR MODEL RESULTS. Preserve one-family scientific MVP, allow a second-family configuration smoke only after core milestones. See [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md#9-新的前置构想多材料家族路由--分家族专家discussion--not-yet-adopted). The main frozen JS-only results and archived inversion NO-GO remain unchanged.

## 15. 2026-10-18: CrystalShift changes the forward-model framing (literature audit)

A literature check found a close, public physics-only precedent: Chang et al. (2025) CrystalShift already combines symmetry-constrained XRD lattice refinement, Bayesian probabilities for single- and multi-phase combinations, and forward-pattern model comparison **without a trained neural network**. Related work includes Lee et al. (2020) on simulation-trained multiphase CNNs and Dong et al. (2021) PQ-Net on physical parameter regression. Differentiable forward reconstruction itself also has related precedents in other diffraction modalities.

**Correction:** a pure Top-K classifier would marginalize the user's original forward-model insight; the project should keep forward modeling as a core inference-time physical validity/limited refinement step, with simulation generation as a second role. Training-time forward reconstruction loss remains an independent optional scientific test, not a mandatory contribution. The properly framed research opportunity is the *incremental value and limits* of learned candidate/parameter initialization on top of physics-based optimization, with physics-only, NN-only and hybrid comparisons.

**Status:** evidence-backed research framing correction / future candidate; no new experiments, no revision to frozen V9, no revival of archived factorization Stage-1. Detailed references: [PRE_REFINEMENT_FORWARD_MODEL_RELATED_WORK_20261018.md](PRE_REFINEMENT_FORWARD_MODEL_RELATED_WORK_20261018.md).

## 16. 2026-10-18: user re-prioritizes direct forward-reconstruction-loss training (proposal)

**Question / reasoning:** After reading CrystalShift as a physics-only strong baseline, the user challenged the conservative choice of leaving NN training-time Forward Reconstruction Loss as optional. The user originally wanted physics-model output to send meaningful learning gradients back to the neural network; post-hoc forward checking alone risks collapsing the next research task back into ordinary phase classification. This objection is scientifically sound.

**Candidate correction (not executed or finally approved):** Consider supervised phase/conditional-parameter inversion **with differentiable forward reconstruction loss as the primary candidate method**. Design a small-scope single-phase start; handle discrete class choices explicitly instead of assuming `argmax` differentiability; advance to physically plausible single/dual-phase hypotheses with carefully controlled scale factors and nuisance parameters only if forward correctness and identifiability hold. Compare supervised-only vs supervised-plus-reconstruction and physics-only. Prior work includes Chen et al. (2021) DRNets using reconstruction plus scientific constraint reasoning and CrystalShift (2025) probabilistic physics-only refinement; do not claim differentiable reconstruction itself is original.

**Why previous gating existed:** The current `xrd_inversion` report validates restricted known-tetragonal forward physics, not full mixed-phase differentiable models; previous local-capture and split-policy risks remain. The old archived paired factorization NO-GO **did not experimentally disprove** reconstruction loss in this new task. Train-only reconstruction can reduce spectrum residual yet fail to recover unique physical parameters.

**Status:** FUTURE / DESIGN CANDIDATE, NO NEW EXPERIMENTS. Appended for the user's application-purpose decision history without overriding the main 12-week planning document or frozen V9. See section added before W0 in [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 17. 2026-10-18: converge on a reference-workflow-led, single-intervention thesis direction

After successive expansions to multi-family routing, calibrated single/mixed-phase models, inference-time physical fitting, and train-time differentiable reconstruction, the user intentionally simplified the project: **follow a mature PXRD regression workflow (PQ-Net as practical reference), add and test a forward-reconstruction training constraint (DRNets as related physics-reconstruction reference), then demonstrate whether it helps on one ferroelectric ceramic material family**. The desired result is a bounded, reproducible scientific comparison rather than a universal autonomous Rietveld platform.

**Primary experimental contrast:** matched supervised parameter-regression NN vs the same NN with differentiable forward reconstruction loss; quantitative outcomes should include physical parameter MAE, spectral error, and refinement-initialization utility. Physics-only refinement (CrystalShift-type) is an external strong baseline where practicable. One family, initially known-phase/single-phase and valid CIFs, before considering physically supported coexistence cases. Small amounts of real collaborator data are reserved for independent cases, not relied upon for the main training set. Novelty must be tied to the tested result and task adaptation, not simply to using forward loss, which has prior art.

**Explicit de-scoping:** no mandatory 3-family routing model, broad phase-probability product, universal multiphase fractions, or feature-complete pre-refinement software in the 12-week core. Earlier discussions and competing approaches remain in their original dated entries for provenance; they are no longer equally weighted present implementation priorities.

**Status:** USER-SELECTED FUTURE RESEARCH PRIORITY, NOT_STARTED / NOT APPROVED / NO RESULTS. Do not overwrite existing V9 results or revive archived NO-GO. See the priority note in [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 18. 2026-10-18: PXRD AutoLab automation proposal

The user proposed automating repetitive experimental work after choosing a small, literature-based Forward Reconstruction Loss A/B study and a transparent biweekly reporting schedule. The new idea is an auditable engineering workflow: locked config, physics/split/budget gates, paired training, machine-derived metrics and figures, immutable manifests, and draft reports.

The first engineering step should be a minimal P0 (manifest, state machine, safe CPU smoke, reporting and tests), then a P1 scientific pilot, followed by optional GPU scheduling if an authorized worker is accessible. Scientific decisions and claims stay with researchers. No changes to frozen V9 evidence or archived Stage-1 NO-GO.

**Status:** PROPOSED / NOT IMPLEMENTED / NO NEW SCIENTIFIC RESULTS. See [PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md).

## 19. 2026-10-18: reconcile tiny one-parent pilot with possible multi-material horizontal extension

**Question:** The user chose option A (known-material/known-candidate PXRD continuous parameter inversion), but asked whether the mature PQ-Net-inspired workflow could be replicated horizontally across several materials, and whether the first Forward Reconstruction Loss pilot means reconstruction is useless or simply inaccurate.

**Evidence:** Draft PR #11 on `feat/physics-guided-pxrd-inversion-pilot` used a *single* known tetragonal HfCd structure and 512 simulated parameter realizations (358/77/77). Matched three-seed synthetic results: normalized two-coordinate parameter MAE A=`0.01495 ± 0.00327`, B=`0.01509 ± 0.00120`; clean transformed-profile RMSE A=`0.009008 ± 0.001868`, B=`0.008497 ± 0.000602`. Physical a/c MAEs were approximately 0.0003 Å/0.0015–0.0016 Å for this narrow simulator-matched task. Forward/gradient gate passed. Mean parameter benefit was **not demonstrated**; small mean reconstructed-spectrum improvement and mixed per-seed/parameter effects do **not** prove general failure of forward reconstruction, nor experimental accuracy.

**Possible scope adjustment (DISCUSSION / NOT ADOPTED):** Keep a single clear scientific question and one A/B protocol; once the collaborator's family is known, run separate matched experiments on that family, and *if capacity and reference CIF/physical validity allow*, replicate the **same** workflow on a second family (and optionally third) for cross-material evidence. Distinguish (i) independent family-specific expert models sharing a pipeline, (ii) a jointly trained family-conditioned model, and (iii) genuine unseen-family transfer: these are different claims with different splits; do not accidentally call independent per-family success zero-shot transfer. For any family/phase-specific forward, verify lattice symmetry, occupancies, structure factors, instrument metadata, gradients, identifiability, prototype-grouped splits and real-domain applicability. Avoid arbitrarily adding 14,060 heterogeneous CIFs: that was appropriate to the previous crystal-system classification question, not automatically to known-candidate parameter inversion.

**Current decision:** User explicitly prefers **A: known-family parameter inversion**. Multiple materials are a candidate way to broaden application breadth, *not yet a commitment to three fully trained material experts or a universal model*. Await family information and a bounded protocol; preserve PR #11 as method engineering evidence and frozen V9 untouched.

**Status:** SCIENTIFIC INTERPRETATION + FUTURE SCOPE DISCUSSION; NO NEW EXPERIMENTS. Reference: [PR #11](https://github.com/Frysland-2024/AI4science/pull/11), `xrd_forward_loss/FORWARD_LOSS_PILOT_REPORT.md` on its draft branch, and [12-week proposal](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 20. 2026-10-18: user proposes reusing V9 physical measurement perturbations in forward-guided inversion

The user proposed incorporating the previous V9 PXRD simulator's five physical measurement perturbations into the new known-material continuous-parameter inverse-model pipeline. This follows the narrow HfCd method pilot, in which only count noise plus linear background was added, reconstruction RMSE improved slightly but average parameter MAE did not.

**Scientific reason:** train the same A/B parameter-regression models on varied measurement realizations of the same physically labeled structure/parameter state, examining whether Forward reconstruction constraints help under credible instrument/texture/background/noise mismatch. Reuse source-grounded zero shift, width, March-Dollase preferred orientation, background and Poisson–Gaussian noise **without reviving old V9 scientific experiments or changing archived results**.

**Crucial correction:** in a lattice-parameter-only forward model, zero-shifted input peaks and other nuisance effects are not necessarily reconstructible by changing lattice parameters. Blindly minimizing `D(F(theta_pred), observed_noisy)` can *bias the structural parameters* to imitate nuisance. A valid next experiment must separate `theta_true`, `clean_profile` and `observed_profile`, then explicitly decide whether the new reconstruction target is clean simulation truth or an observed profile with modeled nuisances; it cannot just swap old NumPy functions into a differentiable path.

**Status:** DISCUSSION / FUTURE DESIGN CANDIDATE / NOT IMPLEMENTED / NO NEW RESULTS. The detailed engineering/science proposal is [FORWARD_LOSS_V9_PERTURBATION_REUSE_DISCUSSION_20261018.md](FORWARD_LOSS_V9_PERTURBATION_REUSE_DISCUSSION_20261018.md). The user has not yet approved a new formal experimental protocol; PR #11 remains an unchanged preliminary pilot.

## Current perspective

The project is no longer summarized as "a JS loss for XRD" or "an XRD robustness benchmark."

The current research statement is:

> **Use relationships known by scientific data-generation systems — here, simulator-retained parent provenance — as additional supervision for learning from scientific measurements.**

PXRD is the concrete test bed. The broader transferable idea is to identify supervision that already exists in a scientific measurement process but is normally discarded when observations are reduced to independent (x, y) pairs.


## 2026-10-18: parent-budget archival and explicit design/implementation distinction

The 2026-10-14 parent-budget experiment had completed in Cuifa01's implementation/execution branch but remained outside main due to branch divergence. The results and implementation were integrated without overwriting newer independent developments. The research lead clarified the historical division of labor: Frysland-2024 originated and led the study's scientific framing, simulated OOD and RRUFF/CNRS real-domain experiment design, and the parent-budget learning-curve design; Cuifa01 participated as an engineering implementation/execution collaborator, including desktop GPU training and artifact preparation. This clarification is a statement of research roles, not a rewrite of commit metadata or a final publication authorship ruling. The experimental outcome shows higher JS Macro-F1 at all four matched parent budgets but no demonstrated parent-count reduction. See the preserved full [supplement report](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).


## 2026-10-18: further correction to the attribution of scientific design and supporting work

The project lead clarified that the prior research-role descriptions were still too narrow and insufficiently explicit: **the scientific approaches and project-level plans were principally designed and directed by Frysland-2024 throughout the project's evolution**, not merely for isolated later experiments. This includes framing and redirecting the research, choosing and planning evaluation protocols, designing the simulated OOD, RRUFF, CNRS and Data Efficiency/parent-budget studies, and interpreting the results. Cuifa01's primary role was **participation in carrying out those plans**, alongside **auxiliary idea suggestions, feedback, data gathering/organization, code implementation, computing and experiment operations**, including the desktop GPU work.

The distinction is between **principal research design and planning** versus **supporting intellectual input and execution**. It does not erase the collaborator's execution or suggestions, change the historical Git record, or prejudge formal manuscript authorship. The earlier 2026-10-18 entry remains as a historical record of the first attribution clarification; this entry records the later, more complete correction explicitly rather than silently rewriting history.

## 2026-10-23: Converge on three headline metrics for the crystal-system extension

**Previous assumption / question:** After exploratory quantitative PXRD inversion did not mature into a stable real-domain result, the lead prioritized returning to seven-crystal-system classification. The October 22 supervisor discussion underscored the need for credible *absolute* measured-RRUFF performance against published systems, not only internally matched JS-versus-ERM gains. A scale-up task was opened for independent simulated parent structures.

**Decision (explicit, 2026-10-23):** Exactly three next-stage headline evaluation axes:
1. **RRUFF real-domain leaderboard** — primary zero-shot crystal-system Accuracy, with Macro-F1 and same-test-set published model comparisons.
2. **Confidence calibration** — ECE and reliability, with NLL/Brier as complementary probability scores.
3. **Simulated parent-structure data efficiency** — classification performance versus number of distinct simulated training structures, with matched ERM/JS training budget.

**Why these three:** They respectively answer whether a model *performs*, whether its expressed uncertainty is *trustworthy*, and whether parent-relationship supervision improves the *use of structure data*. This response targets both measurement-facing practical value and the lead's original simulator-provenance method idea.

**What changes:** The next-stage presentation, scaling work and external evaluation prioritize these three axes. RRUFF published benchmark numbers are only reference lines unless protocols/sample IDs are matched. The RRUFF zero-shot and prior K=1/2/5 few-shot tracks must never be conflated; probabilistic calibration requires a declared evaluation domain.

**What does not change:** All frozen historical V9, CNRS and RRUFF experiments and negative/uncertain results stay untouched. A completed 984/2460/4921/9842 parent-budget study demonstrated positive same-budget JS gains but explicitly did **not** establish a statistically supported count of saved parent structures. Residual and parameter-inversion branches remain part of the honest chronology, not newly reactivated.

**Status:** ACTIVE RESEARCH PRIORITY / PLANNING, NO NEW GPU OR LITERATURE-ALIGNED RUN CLAIMED. See [current scientific state](CURRENT_STATE.md) and [scaling task](https://github.com/Frysland-2024/AI4science/issues/49).

## 2026-10-23: CNRS becomes an optional secondary real-domain result

**Previous assumption:** The 2026-10-23 three-pillar evaluation design already made RRUFF the primary real-domain benchmark, but CNRS remained a possible secondary external-domain figure.

**User decision:** Explicitly deprioritize CNRS. Focus the new scale-up and published-paper comparison on RRUFF; CNRS is optional for the headline slides and is not a required fourth research objective. The user expressed a preference to show CNRS when it looks good and omit it otherwise.

**Research-integrity correction:** A result-dependent decision to hide already-run unfavorable tests could bias the scientific record. The appropriate distinction is between *narrative priority* (RRUFF headlined, CNRS optional or supplementary) and *evidence transparency* (retaining and accurately citing all completed material evaluations, including negative/weak results where relevant to generalization claims).

**Existing evidence:** CNRS-318 zero-shot five-seed paired Macro-F1 improves about +0.0187; pooled Macro-F1 0.1912→0.2091, Accuracy 0.2000→0.2101, ECE 0.6826→0.6124. Absolute task performance remains low, and the paired-parent strict CI spans zero. Preserve that distinction.

**What changes:** New training/acquisition/benchmarking work is not required to include CNRS unless justified. Core evaluation themes remain RRUFF running score, ECE, and simulated parent-data efficiency.

**What does not change:** CNRS artifacts, frozen predictions, original result reports, historical analyses and source disclosures must remain unmodified; future papers must not claim comprehensive real-domain generalization by omitting material counterevidence.

**Status:** ACTIVE SCOPE CHANGE / NO NEW EXPERIMENT. See [current state](CURRENT_STATE.md), [CNRS report](../xrd_robustness/reports/CNRS_318_RESULTS.md).

## 2026-10-23: Upgrade measurement simulation before reselecting large-data hyperparameters

**Previous assumption:** After prioritizing seven-crystal-system classification, three headline evidence pillars were fixed (RRUFF real-domain scores, ECE, independent-parent simulated-data efficiency). The initial expansion plan concentrated on acquiring many more CIFs and applying the established V7 online perturbation pipeline.

**New reasoning and user decision:** The project lead identified two prerequisites: borrow from a more comprehensive **dynamic physical simulation** framework, then revisit optimizer/training settings once far more independent structures become available. The rationale is that simulator fidelity and data scale both change the learning task; old parameters, especially the chosen JS λ and fixed optimizer-step budget, may no longer be appropriate.

**Source and implementation observation:** Existing V7 already has global 2θ shift, reflection-aware March–Dollase, Gaussian broadening, smooth/GP background and Poisson/electronic noise. SimXRD/Pysimxrd offers additional size-dependent line profiles, thermal and geometry effects; however code/source inspection shows that its default pymatgen path does not pass the public `zero_shift` argument and unconstrained random lattice shear can threaten seven-system label preservation. Thus the plan is **selective, verified reuse**, not wholesale copying. The 2026 Kikkawa et al. industrial-XRD augmentation study supplies a complementary real-measurement perspective.

**What changes now:** Implement a versioned simulation extension, validate it cheaply against the old simulator on equal structure/compute budgets, and choose a limited validation-only search for LR/scheduler/batch/training exposure/λ before the large-scale matrix.

**What does not change:** The old frozen V7/V9 scientific evidence, RRUFF-301 70/231 protocol, and the three core evaluation axes remain untouched. This is a design decision, not evidence that implementation or new training has been completed.

**Status:** ACTIVE NEXT-STAGE DESIGN / NOT IMPLEMENTED. [Implementation plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md) and [Issue #49](https://github.com/Frysland-2024/AI4science/issues/49).


## 2026-10-23: formal return to seven-crystal-system classification

**Project path:** FerroAI and earlier materials-ML work led into PXRD as a scientific measurement problem; the PXRD study then developed into a controlled method investigation of simulator-retained same-parent identity and relationship supervision. A subsequent exploration tested whether PXRD spectra could support quantitative lattice/measurement-parameter prediction through supervised inversion, Forward Reconstruction Loss, DONUT-inspired reasoning, and automated/refinement-assisted workflows. Those proposals and numerical feasibility results did not establish a stable, validated real-domain parameter-inversion study. On 2026-10-23 the project lead formally returned the sole active scientific task to **machine-learning-based PXRD seven-crystal-system classification**.

**Current plan:** Only three evaluation axes are active for planning: (1) RRUFF real-domain zero-shot Accuracy and Macro-F1 with matched-condition comparisons to Lee (2023), SimXRD-4M (2025), and XQueryer-NoElem (2025); (2) confidence calibration, led by ECE with NLL/Brier/reliability diagrams supporting; and (3) simulated-data efficiency by unique training-parent count under matched Dynamic ERM/JS budgets. CNRS remains optional secondary-domain evidence. See [CURRENT_STATE.md](CURRENT_STATE.md) and the [2026-10-23 scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).

**Technical order:** First audit independent structure availability and develop a versioned online simulator with physically defensible, label-preserving paired views. Then retune training settings against synthetic development evidence. Only after data and simulation stabilize may ResNet-18-GN be compared conditionally with SimXRD CNN11 or an optional multi-scale 1D CNN. These are future plans, not implemented work.

**Archived / Inactive:** Quantitative parameter prediction, lattice-parameter recovery, Forward Reconstruction Loss, DONUT-inspired workflows, automatic refinement, and the ferroelectric pre-refinement candidate. Their code, completed numerical checks, failures, reports, citations, and prior authorizations remain in the repository as historical evidence. No historical issue or detailed proposal can reactivate them.

## 2026-10-26: narrow the undergraduate thesis; archive parameter inversion

**Date:** 2026-10-26

**Question / previous assumption:** The 2026-10-23 decision treated classification scale-up through a new RRUFF zero-shot comparison, calibration, and parent-data efficiency as the active next stage. In parallel, PR #46 recorded a partial multi-architecture synthetic lattice-parameter inversion benchmark.

**Evidence and reasoning:** PR #46 completed primary synthetic scoring for 42 models and 8,085 records, but the q-accuracy gate passed 0/42; the per-DOF cell-MAE constraint passed 41/42. The parent test set had already been opened in PR #43, so the benchmark is exploratory rather than independent confirmation. New-architecture stress was not run, and real RRUFF validation was blocked/not run. The benchmark did not establish consistent neural accuracy gain, real-domain validity, or an exact reproduction of the cited methods. The existing classification study has a bounded, reportable research question and frozen comparative evidence.

**Decision:** The sole current undergraduate thesis line is to write up and defend the completed PXRD seven-crystal-system classification study: test whether same-parent measurement-equivalence supervision improves classification over matched Dynamic ERM. No new experiments are in current thesis scope. Parameter inversion, including PR #46 and its associated routes, is **ARCHIVED / INACTIVE**. The 2026-10-23 classification scale-up plan is **DEFERRED**, not an active task or thesis acceptance gate.

**What changes now:** README, current state, supervisor brief, agent contract, and the scale-up plan status are aligned to the 2026-10-26 thesis scope. PR #46 is closed unmerged; Issue #44 is closed as not planned; Issue #49 is closed as deferred/not planned. Their original text and the PR artifacts remain available as historical records.

**What does not change:** Frozen classification splits, configurations, scores, reports, code, and the negative/uncertain evidence remain unchanged. PR #46's completed metrics remain descriptive exploratory evidence; its incomplete gates are not being rerun, and no new experiment is started.

**Status:** CURRENT THESIS SCOPE / PARAMETER INVERSION ARCHIVED / SCALE-UP DEFERRED.

**Relevant records:** [current state](CURRENT_STATE.md), [README](../README.md), [supervisor brief](START_HERE_FOR_SUPERVISORS.md), [deferred scale-up proposal](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md), [PR #46](https://github.com/Frysland-2024/AI4science/pull/46), [Issue #44](https://github.com/Frysland-2024/AI4science/issues/44), [Issue #49](https://github.com/Frysland-2024/AI4science/issues/49).

## 2026-10-27: final parameter-inversion evidence boundary

This note reconciles the current GitHub state of PRs #36, #42, #43, #45, and #48 with the 2026-10-26 thesis decision. The sole current undergraduate thesis remains the frozen seven-crystal-system classification study; this update does not reopen inversion work or authorize experiments.

**PR #36 — completed conditional synthetic evidence.** The four-stage study is marked COMPLETE in its final technical report, but the PR is currently closed and unmerged. It used one known COD 9014273 tetragonal BaTiO3 CIF, 512 parameter parents split before perturbations into 358/77/77, three model seeds, and 77 held-out parents per seed. In Exp 4, direct normalized-q MAE was 0.033607/0.033578/0.034282 for A/B/C and 0.228037 for DONUT-PXRD. The same bounded joint q+instrument L-BFGS-B refinement yielded 0.000343/0.000350/0.000341 for A/B/C and 0.080026 for DONUT-PXRD. Thus the roughly 0.00034 values are post-refinement results, not neural outputs; A/B/C are effectively tied after the same optimizer. Exp 1/2 and the four Exp 3 conditions are separately reported in the final report and must not be collapsed into the Exp 4 headline. Retain PR #36 as feasibility evidence conditional on this exact known-CIF synthetic setup only. It does not establish real-measurement accuracy, unseen-CIF/composition transfer, multiphase capability, general PXRD inversion, or broad method superiority. The adaptation of a 2D SXDM method to 1D PXRD also does not test or invalidate the original DONUT method. The report includes metric provenance, but model checkpoints and generated arrays are local-only.

**Related branches and source precedence.** Current GitHub state shows PRs #42, #43, and #45 as closed and unmerged; their branches are historical, not current execution queues.

- **PR #42:** decision/journey documentation, not an additional experiment. Its compact DONUT summary lists values (including Exp 1 ≈0.3162 and Exp 2 ≈0.3313) that conflict with PR #36's final report (0.344228 and 0.398342). Use PR #36's final technical report as the numerical source for that study; do not merge the conflicting digest into canonical claims.
- **PR #43:** completed a bounded supported subset of a synthetic cross-CIF pilot (seven templates across three crystal systems; not seven systems). In the primary study, N+A q-MAE was essentially tied with three-start P3; P0 was comparably accurate on five materials but had larger errors on MgO and ZnO. Its separately registered post-primary renderer/peak-shape/background stress test used 16 new parents per material and found no added accuracy or reliability over P0/P3. Neither result establishes unseen-material transfer or real-measurement performance.
- **PR #45:** E1 is complete but no material met the preregistered incremental-value criterion against H1/P0. E2 is **PHYSICS_NOT_READY / NN_NOT_RUN** for three RRUFF rutile profiles; it contributes no neural real-domain validation. The PR body says “open,” but the current GitHub state is closed/unmerged.
- **PR #48:** merged to main on 2026-10-20; it established supervisor-facing classification materials, not parameter-inversion evidence.

**Claim disposition.** Keep PR #36's direct and refined metrics only with the single-CIF synthetic condition attached. Do not present the post-refinement score as direct neural accuracy; do not claim broad robustness, real-XRD validity, cross-material generalization, multiphase solving, neural superiority over strong physical methods, or reproduction of the cited literature systems. Retain PR #43/#45 E1 as completed exploratory comparisons with their negative/limited result, PR #45 E2 as a failed readiness gate with no NN run, PR #42 as historical documentation with a stale numeric summary, and PR #46 as a separate partial benchmark whose q-accuracy gate passed 0/42. The 2026-10-26 classification-only thesis decision remains in force.

**Primary source:** [PR #36 final technical report](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-experiment-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md); related records: [PR #36](https://github.com/Frysland-2024/AI4science/pull/36), [PR #42](https://github.com/Frysland-2024/AI4science/pull/42), [PR #43](https://github.com/Frysland-2024/AI4science/pull/43), [PR #45](https://github.com/Frysland-2024/AI4science/pull/45), [PR #48](https://github.com/Frysland-2024/AI4science/pull/48).

## 2026-10-29: PR #50 documentation sync

PR #50 was merged into `main` on 2026-10-29 (merge commit [`6e4dd70`](https://github.com/Frysland-2024/AI4science/commit/6e4dd70a7134427fc9c8a04b686dce5e20ea6727)). It synchronized `README.md`, `docs/CURRENT_STATE.md`, this history, and `docs/START_HERE_FOR_SUPERVISORS.md` around the existing evidence boundary: PR #36 remains feasibility evidence for one known BaTiO3 CIF under one frozen synthetic setup; its approximately 0.00034 normalized-q MAE values are post-refinement scores, not direct neural outputs; and the 1D DONUT-PXRD adaptation does not test or invalidate the original 2D DONUT method. This was a documentation-only reconciliation: no experiment or result was added, and the 2026-10-26 classification-only undergraduate-thesis scope did not change. See [PR #50](https://github.com/Frysland-2024/AI4science/pull/50).

## 2026-11-03: explicit thesis restart and simulator-first JS performance route

**Question / previous assumption:** On 2026-10-26 the undergraduate-thesis work had been frozen for writing/defense only. The prior October 23 proposal for bigger CIF datasets, more realistic simulators and RRUFF literature benchmarking had been deferred. Recent discussion revisited the supervisor's expressed interest in published-model performance and absolute RRUFF experimental accuracy.

**Evolution of the lead's reasoning (2026-11-03 discussion):**
1. Reject a blanket **zero-shot** target when a target paper used real RRUFF examples for training or fine-tuning: compare each paper under its own disclosed real-data protocol instead. Full replication of the published network is not required for literature-referenced scoring.
2. Prefer **Dynamic JS only for the new exploratory performance run**; older ResNet-18-GN ERM vs JS evidence already exists and is preserved.
3. Ask whether synthetic-data scale should be matched. Clarify that **unique CIF parent count**, not arbitrarily numerous re-rendered spectra, is the meaningful structural dataset axis. Do not pick 30k/60k/100k out of habit or match every paper's total database count mechanically; first audit real training CIF count and availability.
4. Observe that papers with apparently larger structural datasets do not necessarily report higher RRUFF Accuracy, but note **dataset and evaluation protocols differ**. Thus data size alone is a poor selection rule; examine **both simulator implementation and CNN backbone**.
5. State the priority explicitly: **a clear improvement in absolute experimental-data Accuracy** is the immediate engineering success criterion, not a large factorial ablation study.
6. Narrow the immediate action again: **first understand and selectively borrow existing simulators**; after that, run a small same-CIF JS backbone comparison against the old ResNet-18-GN+JS, and only then consider large-scale training.
7. Request a broader shortlist: GSAS-II, ML4pXRDs, PhaseSmith, DebyeCalculator, PowderLine and xrd_simulator alongside SimXRD/Pysimxrd; prefer modules that can be reused, repair simple verified problems, and reject components that violate seven-system label preservation.

**NEW DECISION:** The lead expressly confirmed that **the undergraduate thesis has restarted**. Simulator source investigation, careful module selection and the subsequent bounded JS-only comparison are therefore an **active forward research direction**. The earlier 2026-10-26 *no new experiments* operational pause is superseded, while old results remain frozen as historical evidence.

**What changes now:** [CURRENT_STATE.md](CURRENT_STATE.md) is updated; [simulator candidate inventory](PXRD_SIMULATOR_CANDIDATES_2026-11-03.md) records priorities, evidence status, and next-source-audit deliverable. Initial effort is research/source review, not a claim of newly executed training or scientific validation.

**What does not change:** Existing ERM/JS comparisons, fixed splits, uncertainty caveats, project contribution history and archived parameter-inversion work. Published RRUFF percentages from unmatched sample selections are literature references rather than fair matched head-to-head results.

**Status:** ACTIVE THESIS / SIMULATOR INVESTIGATION FIRST / NO NEW TRAINING RESULT YET.


**2026-11-03 execution-order clarification (project lead):** "先抄明白模拟器，再比较架构" — first understand the external simulator code thoroughly, select and validate useful components as a working, versioned simulator; only **afterwards** compare architectures with the same JS objective. Architectural experiments are not to be launched concurrently with the simulator audit. This sharpens, without replacing, the restart decision above.

**2026-11-03 execution-deliverable correction:** The lead rejected a Phase-1 deliverable consisting only of a simulator audit/report: **“我不要什么报告，我要成品”**. The Phase-1 contract is now working code (versioned PXRD simulator, compatible JS paired-view pipeline, runnable CIF→paired-spectra CLI, tests and example outputs). Upstream source understanding is required to build it, not an independent endpoint. Issue [#54](https://github.com/Frysland-2024/AI4science/issues/54) is the specific Codex-ready implementation specification. At this conversation, the laptop Desktop Commander connection was offline, and the old bridge coding lane explicitly blocked `xrd_robustness/` edits, so creating Issue #54 is **not evidence that Codex executed or that the simulator exists**. No new model architecture trial is authorized until simulator acceptance.

**2026-11-03 implementation-deliverable clarification:** The project lead rejected a research report as Phase 1 output and explicitly requested a *finished, runnable simulator*, built by selecting useful upstream components and validating their integration with current same-parent JS. Implementation task [Issue #53](https://github.com/Frysland-2024/AI4science/issues/53) specifies acceptance tests. No execution is claimed while local Codex machine is disconnected and the legacy bridge code lane forbids core simulator writes.

**2026-11-03 ResNet hyperparameter clarification (owner):** The lead explicitly noted that because the existing ResNet-18-GN was itself borrowed from ML4pXRDs, its *architecture hyperparameters* should not be treated as fixed or optimal for the updated simulator. New sequence: **finish simulator → retune existing ResNet+Dynamic JS architecture (especially heavy downsampling/kernel size) and optimization (LR/scheduler, JS lambda, exposure budget, regularization) → compare fairly with CNN11+JS → consider larger CIF scale and real RRUFF benchmarks**. The old backbone and its frozen experiments remain valid historical references; the new comparison has not been run. Models should receive comparable bounded tuning opportunities, with held-out RRUFF tests reserved for evaluation rather than hyperparameter selection.

**2026-11-03 decision refinement — purpose of V10 and what follows (project lead):** The lead rejected describing V10 mainly as a simulator-vs-simulator test. V10 is the **fixed shared simulation environment** for a simple question: *is replacing the existing ResNet with CNN11 worthwhile?* The lead believes the V10 three-condition outcome is sufficient for this initial decision, and does not want another full backbone sweep. Once V10 results and the planned terminal evaluations are complete, prioritize **Codex's automatic retuning of the existing ML4pXRDs-derived ResNet + Dynamic JS** instead of spending compute on more architecture comparisons. The priority is practical RRUFF absolute performance through an improved, validated simulator and bounded hyperparameter tuning. Code/experiment instructions are queued in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). At this point the three ResNet V10 runs are complete locally and CNN11 V10 training is still in progress; no final verdict or ResNet-retuning result is claimed. This changes an earlier assumption about experimental ordering and should be preserved for future project-development statements.

## 2026-11-03: final clarification — hyperparameter tuning belongs within architecture optimization

**Owner correction and reasoning (chronological):** The lead objected to the assistant's repeated reordering of the project into simulator → immediate ResNet tuning → data and to the later mistaken correction that *deferred* hyperparameter tuning until after dataset expansion. The lead emphasized **“现在要保证做的每一步都是有意义的”** and **“调参本身就是架构优化的一部分”**. These statements refine the scientific logic, not merely a task list.

**Authoritative progression:** (1) Simulator development: engineering task completed, with V11 acceptance evidence (separate PR merge housekeeping); (2) **model architecture optimization as a single stage**: ongoing V10 ResNet-vs-CNN11 screening decides whether to replace the backbone, **followed by autonomous bounded architecture/training hyperparameter tuning of the selected model**, with same-parent Dynamic JS, validation selection and no blind second architecture sweep; (3) build more **unique, valid CIF parent structures**, with class coverage, provenance and deduplicated parent-disjoint splits; (4) run final model training and **RRUFF real-domain literature benchmarking** under comparable disclosed evaluation/real-label-access protocols. Do not confuse V10's screening purpose with a competition between simulator versions.

**Evidence / risks at correction time:** all three existing V10 ResNet seeds completed locally. The CNN11 V10 seed-1 training log showed CE and JS become NaN from ~20,000 steps, invalidating any premature architecture ranking until diagnosed and repaired. No stage-2 tuned checkpoint, larger-CIF dataset or final RRUFF result is claimed. [#60 architecture screening](https://github.com/Frysland-2024/AI4science/issues/60) → [#55 automatic tuning within the same stage](https://github.com/Frysland-2024/AI4science/issues/55) → [#61 expanded CIF data build](https://github.com/Frysland-2024/AI4science/issues/61) → final RRUFF benchmarking. Earlier chronological proposals remain historical and **do not supersede this latest owner clarification**.

## 2026-11-03: SimXRD ML methodology inspires focused ResNet tuning

**Project-lead proposal:** Instead of treating SimXRD solely as a source of simulator physics or replacing ResNet wholesale with CNN11, study **the machine-learning benchmark part of Cao et al.'s SimXRD-4M (ICLR 2025)** as a principled source of *ideas for optimizing the retained ResNet*. This is a methodologically meaningful refinement of Stage 2 (architecture choice plus hyperparameter optimization), not a new phase and not license for blind parameter sweeping.

**Source-based specifics:** SimXRD benchmarked 21 sequence models, used shared batch=128, LR=2.5e-4, up to 50 epochs with early stopping (patience 3), investigated pooling/downsampling, and compared class weighting, label smoothing and focal loss for long-tail symmetry data. Source: https://openreview.net/pdf?id=mkuB677eMM Sections 4.2–4.3. These hyperparameters are **not defaults to copy** into our 8GB GPU online paired-view JS training. Real application requires data-protocol and loss-composition adaptation. Our local ML4pXRDs-derived ResNet presently couples stage stride 4 + kernel 9 in a single Boolean; separate these for targeted, interpretable development experiments. Targeted order: stride/kernel design -> LR/schedule/validation early stopping -> optional smoothing/focal if seven-class imbalance indicates -> targeted JS lambda gradient balance -> selected checkpoint replication. Paper did not use same-parent JS; that part is our own adaptation. Details in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). V10 CNN11 NaN repair and valid architecture verdict remain prerequisites; no new training started by this literature-inspired decision.

## 2026-11-03: direct, non-Codex launch of paper-guided ResNet A1

**Problem:** Codex quota was exhausted while the next architecture-optimization stage remained actionable. The project lead explicitly asked whether ChatGPT could start the experiment directly. **Execution decision:** use authorized Desktop Commander to launch an independent, versioned Python training script with the existing V10 simulator and ResNet+Dynamic JS trainer; do not require Codex or overwrite the dirty root. **Actual proof of start:** local PowerShell session PID 10936 on RTX 4060, source `E:\AI4science\_local\run_resnet_guided_a1_20261103.py`, model shape test passed, training-start event and first finite step recorded. **Hypothesis:** in light of SimXRD's emphasis on peak-information retention, isolate less aggressive residual-stage downsampling (stride transitions 4/4/4 to 4/2/4, residual kernel 9 unchanged), holding existing 14,060 CIF split, V10 simulated spectra distribution, online same-parent JS λ60, LR 1e-4 and batch 16. Changes to head dimension increase model count from ~13.01M to ~14.84M and must be accounted for. **Bounded pilot:** one seed 20260711 for 12,320 steps, validation at fixed 6,160 and 12,320 steps, selecting on Validation OOD Macro-F1 only; prior ResNet V10 same-seed checkpoints provide the direct comparison. Reports and outputs are in new `xrd_robustness/reports/resnet_simxrd_guided_A1_20261103/` and `xrd_robustness/outputs/resnet_simxrd_guided_A1_20261103/`. [Execution evidence / discussion](https://github.com/Frysland-2024/AI4science/issues/55). **Status: STARTED, NOT CLAIMED COMPLETE.** No full-budget final performance/real RRUFF result, no automatic full tuning campaign has been completed. Original simulator and CNN11 instability evidence remain unchanged.

## 2026-11-03: Codex-free A1→A2 autonomous ablation and GitHub evidence handoff

**User decision:** After the direct-launch SimXRD-inspired ResNet A1 trial, the user asked not only to monitor its completion but to **automatically continue to A2 and upload an end-to-end evidence-backed conclusion to GitHub**, without using exhausted Codex quotas. This extends the previous one-shot handoff into a bounded, sequential experiment runner; it is not a new research stage.

**Hypothesis and experimental constraints:** A0 historical V10 ResNet = residual stage-transition strides (4,4,4), kernel9; A1 = strides (4,2,4), kernel9; A2 = strides (4,2,4), kernel5. The V10 simulator, 14,060-parent split, Validation panels, same-parent Dynamic JS λ60, LR1e-4, batch16 and seed 20260711 are fixed. A1 and A2 are **12,320-step single-seed screens**, not 49,280-step replicated claims. Changing kernel in A2 also changes parameter count (A1 ~14.84M; A2 ~9.96M), so interpretation needs careful compute/capacity disclosure. Select based on Validation OOD Macro-F1 only; do not tune on previously inspected RRUFF-70 or Test.

**Execution evidence and safeguards:** The direct local A1 job was still running (at 6,160-step Validation OOD Macro-F1 0.589445; matched historical A0 0.575300). A2 source `E:\AI4science\_local\run_resnet_guided_a2_20261103.py` passed syntax and 7-logit model-shape tests. A new **running** supervisor `E:\AI4science\_local\supervise_resnet_a1_a2_20261103.py`, initial session PID 30608, checks A1's completed training JSON and hashed checkpoint, then starts only one A2 GPU job, verifies A2 evidence, generates A0/A1/A2 summary and report, and uses locally authenticated `gh` to create a GitHub experiment branch plus PR without modifying the dirty root checkout. Separate hourly automation `A1训练完成与Git归档` serves as notification/fallback and was updated to follow both trials. The code preserves failed runs and refuses overwrites or concurrent duplicate jobs. [GitHub Issue #55 execution handoff](https://github.com/Frysland-2024/AI4science/issues/55).

**Status when recorded:** A1 underway, supervisor running; A2 had **not yet begun**, GitHub results PR and final performance conclusions **not yet available**. All final claims must depend on verified completion artifacts and PR links, not a task's existence. If no improvement emerges, that negative result is retained rather than running unbounded searches.

## 2026-11-03: Owner explicitly finalizes three-tier RRUFF performance acceptance and 3 headline outcomes

**Prior misunderstanding corrected:** The AI assistant repeatedly reinterpreted the earlier literature comparison as an invented grade scheme (first replacing the owner's chosen paper set with AlphaDiffract as the sole 80-point benchmark and SimXRD alone as full score, then excluding Salgado). The owner clarified the exact grade grouping and that the literature-comparison sheet should remain simple: paper/model, unique simulated structure count, number of real RRUFF evaluation spectra, seven-class RRUFF Accuracy, and number of labeled real RRUFF adaptation samples. Maintain this original intent rather than inventing extra criteria.

**Final owner decision:** **Pass/60 = Lee 2023 (74.24% RRUFF Accuracy); 80 = Salgado 2023 (86%, ~452 labeled real RRUFF training) AND AlphaDiffract 2026 (81.74 ± 0.78%, 734 RRUFF classification cases, 0 labeled RRUFF training; AlphaDiffract is the PRIMARY newer reference); Full/100 = SimXRD-4M 2025 CNN11 (89.3%) AND XQueryer-NoElem 2025 (91.5%).** This is a tiered literature target set, not a strict numerical conversion from Accuracy to grade, nor a claim that all papers have matched evaluation cohorts. The user additionally insists that the overall work have only three headline outcomes: **RRUFF real-data Accuracy** (the sole grade driver), **unique-parent data-efficiency curve**, and **ECE calibration**; simulation validation metrics remain internal/model-development support.

**Why this matters for the project narrative:** The lead wants a straightforward **industrial/benchmark-style competitive-performance objective** with transparent data scale and target-data adaptation budgets, not increasingly complicated criterion engineering or substitute simulated scores. The 80 tier intentionally includes both a legacy target-adapted model and a newer large-data ensemble; disclose protocol differences honestly. No change to frozen old results or permission to train on locked real test spectra. Canonical scorecard now lives in `docs/RRUFF_REAL_DOMAIN_LITERATURE_BENCHMARK_2026-10-22.md`, and the authoritative project objective is summarized in `docs/CURRENT_STATE.md`.

## 2026-11-03: RRUFF data curation becomes an explicit benchmark reproducibility question

**Owner insight:** After comparing Lee 2023, Salgado 2023, AlphaDiffract 2026, SimXRD-4M, and XQueryer-NoElem, the research lead challenged an implicit double standard: published methods explicitly curate/filter real RRUFF test datasets, so **our study may also use a scientifically justified, auditable selection protocol**, rather than holding itself uniquely to all raw/invalid spectra. The issue is to distinguish data completeness/physics-based quality screens from post-hoc performance cherry-picking. The lead asked for source-by-source verification of each RRUFF cohort rather than speculative attributions of Bin Cao's high score to network design or favorable data filtering.

**Verified research correction:** Lee explicitly removes the top 40% in a low-angle (5–8°) background-STD ranking; AlphaDiffract filters 1,362 corrected spectra and DIF-derived cell/space-group/lattice metadata down to 734 valid classification entries (59 derived computationally from single-crystal patterns); Salgado's 86% used approximately 452 labeled RRUFF entries for training and a roughly half-sized held-out test; XQueryer's paper reports 3,002 → 1,003 and Bin Cao's accompanying thesis documents 2,088 ID-matched XY_RAW+DIF profiles, excluding incomplete measurements/lattice metadata to reach 1,003, while 849 separate MP structure matches support the different *structure identification* task. Original public matching files independently contain 849 distinct paired IDs. **SimXRD-4M Table 5's exact RRUFF ID set and denominator remain unknown**; one cannot assume either 3,002 or XQueryer's 1,003. These different cohorts prevent a strict performance ranking without shared IDs and preprocessing, but provide legitimate *paper-inspired* curation templates.

**Resulting plan, not an executed RRUFF experiment:** preserve historical locked panels; for a prospective cohort create versioned, label/coverage/quality-motivated RRUFF selection rules and an audit manifest **before** measuring accuracy; separately report clean-paper-like and harder broad panels when useful; no HPO on RRUFF locked test. The complete five-paper primary-source and release-file verification is in [RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md). This adds benchmark reproducibility discipline, not a new scientific research pillar or change to the owner-frozen 60/80/full RRUFF Accuracy, unique-parent data efficiency, and ECE outcomes.

## 2026-11-03 — Final zero-shot-only acceptance correction (Salgado moved to pass)

**New owner decision:** Project performance grades are **strictly based on zero labeled RRUFF training/fine-tuning**. The owner explicitly rejected using Salgado 2023's **86% Large Souping** result for grading, because that model trained with about **452 labeled RRUFF spectra**. Instead use Salgado's **synthetic-only NPCNN zero-shot RRUFF Accuracy approximately 74%**, assign it to the **PASS / 60 tier alongside Lee 2023 (74.24%)**. The **80 tier now comprises AlphaDiffract 2026 (81.74 ± 0.78%), PRIMARY**; **FULL / 100 comprises SimXRD-4M 2025 CNN11 (89.3%) and XQueryer-NoElem 2025 (91.5%)**.

**Interpretation:** 'Zero-shot' for comparison denotes **zero labeled real RRUFF training/adaptation examples**. AlphaDiffract consulted RRUFF noise statistics and paper RRUFF scores in development, so the published result is zero labeled adaptation but not completely target-domain-blind; this qualification must accompany its 80-tier primary status. The 86% Salgado 452-labeled setting is retained in the historical evidence table but is not eligible for acceptance. Absolute published test cohort sizes/processing differ; they remain reference markers unless aligned. Model tuning must not use the locked RRUFF test. The scientific deliverables remain RRUFF top-1 Accuracy (grade), unique-parent data efficiency, and ECE.

**Reason for change:** The lead wishes to compare like-for-like *zero-real-label classification capability*, not to grant grade credit to models that saw hundreds of target labels. This corrects earlier assistant-authored scorecard mappings without erasing old discussion. Authoritative targets: `docs/CURRENT_STATE.md` and `docs/RRUFF_REAL_DOMAIN_LITERATURE_BENCHMARK_2026-10-22.md`.

## 2026-11-03: User adopts AlphaDiffract Table 1 as future slide reference; historical baselines expanded

**Decision and preference:** Seeing Andrejevic et al. 2026's minimalist black-background Table 1, the project lead requested that the reference be archived and that **future RRUFF presentation slides use a similarly concise, immediately readable paper/model × benchmark Accuracy comparison table** rather than an overburdened technical audit. The user explicitly added **Vecsei et al. 2019 Dense (70% RRUFF) and Convolutional (56% RRUFF)** plus **Choudhary 2025 DGPT-formula (28.75% RRUFF as re-evaluated by AlphaDiffract on its curated cohort)** to the reference model comparison library. Choudhary uses formula side information and is not a pure PXRD-only graded competitor. A source-attributed dark-theme SVG reference and expanded markdown library have been committed: [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md) and [table-style SVG](assets/alpha_diffract_2026_table1_style_reference.svg). The original user screenshot is retained as the source visual in this conversation; SVG is an explicitly named recreation.

**Further source-research insight:** SimXRD-4M's own ICLR 2025 Table 5 reports multiple architectures on the same RRUFF benchmark, including CNN11 89.3%, CNN7 86.8%, CNN10 85.9%, CNN9 79.2% and several recurrent/Transformer baselines, now separately recorded as *model variants from a single paper*. These additions do not create new 60/80/100 grading targets, alter the owner's zero-labeled-RRUFF adaptation rule, launch a new training campaign, or substitute for the agreed three outputs (RRUFF Accuracy, unique-CIF data-efficiency curve, ECE). The user's project narrative is moving toward a **simple, evidence-grounded competitive benchmark presentation** with more complete literature coverage.

## 2026-11-03: Owner expands RRUFF competitor eligibility to DiffractGPT regardless of formula input

**User's exact conceptual correction:** On seeing that a previous assistant excluded Choudhary's *DiffractGPT DGPT-formula* from the official RRUFF comparison on the basis of formula side-input, the project lead said it **should be included because it is also another researcher's work**. The purpose of the comparison library is a **complete, source-transparent literature competitor panel**, not an artificial exclusion of published alternative methods. The related project-score tiers remain **pass Lee/Salgado synthetic-only; 80 AlphaDiffract; full SimXRD/XQueryer-NoElem**—but lower-scoring competitors and models with additional declared inputs should still appear in the main benchmark comparison if they have an attributable RRUFF crystal-system Accuracy. Thus **DiffractGPT 2025 DGPT-formula 28.75%** joins as a **below-pass legitimate comparator**, with clear note that this particular number is **AlphaDiffract 2026's third-party re-evaluation**, not an original DiffractGPT 2025 headline result, and the model uses chemical formula input. Its original model trained on JARVIS-DFT simulated data without reported labeled RRUFF fitting. This clarification was committed to [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md), the benchmark scorecard, and the authoritative current state. It preserves the original five anchor-paper thresholds and the outcome trio of real RRUFF Accuracy / data efficiency / ECE.

## 2026-11-03: Vecsei Dense moves to pass-tier benchmark

The owner clarified that Vecsei et al. (2019) Dense/MLP with 70% RRUFF Accuracy belongs in the pass (60-point) tier, not below it. Pass-tier comparisons now include Vecsei Dense 70%, Salgado synthetic-only about 74%, and Lee 74.24%. Vecsei CNN 56% and DiffractGPT 28.75% remain comparative results; 80 and full tiers remain unchanged. This is a scoring-policy correction, not a new experiment. See the current state and RRUFF model comparison library.

## 2026-11-03: Five-column slide benchmark fixed — training structures and actual RRUFF N

**Owner's presentation preference refined:** After approving AlphaDiffract Table 1's compact score comparison style and freezing the six-row pass/80/full RRUFF zero-shot scorecard, the owner asked for **two additional visible numerical columns**: (a) **how many independently sourced simulated crystal structures are used in training**, and (b) **how many measured RRUFF spectra support the reported test accuracy**. The user explicitly preferred approximate values when exact paper cohorts are unavailable, but refused extra complexity: keep the slide to **grade, paper/model, simulated structures, RRUFF test N, RRUFF Accuracy**. RRUFF labeled-adaptation remains 0 for all graded comparators, reported in the notes instead of crowding the main table.

**Primary-source verification produced a new concrete finding:** Vecsei et al. 2019's original paper reports **128,404 distinct simulated samples after deduplication, of which 114,404 are actual training samples** after separate 7,000/7,000 validation/test, and about **800 RRUFF spectra**. The table labels other papers' counts as curated parent corpora, not verified final post-split training Ns; Lee's ~960 RRUFF is an **estimate** based on 1,600 initial spectra and a 40% low-angle background exclusion; SimXRD-4M's actual RRUFF Table 5 denominator stays **Unknown** even though its catalog records 3,002 entries. Verified and uncertain counts are now laid out, with source links and a compact slide-friendly format, in [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md). The important shift is from percent-only comparisons to **performance relative to simulation-data scale and real-test scope**, without implying identical cross-paper RRUFF panels. No new experiments or CIF acquisition were started as a result.

## 2026-11-03: Cao thesis reveals SimXRD's usable RRUFF cohort is approximately 1,003

The owner asked to resolve the RRUFF test count behind SimXRD's 89.3% and suggested it may share XQueryer's published **3,002 → 1,003** cohort. Source verification of **Bin Cao's own 2026 doctoral thesis PDF** shows the **SimXRD chapter 3** explicitly reports **3,002 catalog entries in March 2024, only 1,003 usable because of complete diffraction and structural information**, and the same chapter's **Table 3.5** repeats CNN11's **0.893 RRUFF accuracy**. The XQueryer chapter separately documents the **2,088 matched XY_RAW/DIF → 1,003 valid** cleaning flow. The lead instructed us to incorporate this evidence and treat it as likely the same underlying RRUFF dataset. The six-row benchmark slide table now writes **SimXRD RRUFF test ≈1,003 (same-author thesis-supported inference)** rather than an unconstrained Unknown or a misleading 3,002 tested. Exact scored sample IDs and an explicit Table-5 N are still unreleased, so identical test membership between the two papers is **likely but not proven**. This is a correction to earlier overly conservative source accounting, not new measured performance. See [revised cohort audit](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md) and [current leaderboard](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md).

## 2026-11-03: Reconsider old-data HPO after 154,975-structure library becomes available

**Status: research-method reconsideration / proposal, NOT an approved cancellation or a completed new HPO experiment.** The project lead questioned whether tuning hyperparameters with the historical 14,060-row / 9,842-train-parent library is wasted effort now that the 154,975-row, 154,968-parent library exists on external D: storage, split **108,478 actual train parent groups / 23,245 validation / 23,245 test**. The lead specifically hypothesized that the meaningful hyperparameter search should operate against the new larger corpus. This is an important shift in thinking: earlier 'finish tuning before collecting data' made sense when the larger database did not yet exist, but **the database has now been collected and structurally validated** (though full V11 PeakTable adaptation and corpus-scale spectrum generation are still not complete).

**Evidence from current HPO code inspection:** `E:\AI4science\_local\resnet_optuna_20261103\supervise_optuna.py` is still bound to the historical `formal_14060` train 9,842, fixed V10 pseudo-Voigt/Caglioti simulator, and `STEPS=49280`, `batch_size_parents=16`; the queued automatic follow-on explores up to **10** full-length trials plus independent-seed confirmation. This is **788,480 sampled parent presentations** per run, corresponding nominally to about **80.1 old-train-parent passes** or only **7.27 new-train-parent passes** at the same step budget. Moreover the old data are artificially seven-class balanced whereas the new dataset has substantially unequal class frequencies (for example new training hexagonal 7,493 parent groups versus monoclinic 25,593). Therefore exact LR, weight decay, JS lambda, schedule, sampling and training horizon selected on the old balanced sample are **not guaranteed to transfer** to the new data and V11 simulator.

**Provisional methodological recommendation (no code/process changes authorized by this entry):** Preserve all completed six-cell V10 architecture/downsampling and numerical-stability investigations as transferable exploratory evidence. **Do not invest the full planned 10-trial old-data Optuna budget in selecting final full-scale training hyperparameters.** Prefer **new-library-based multi-fidelity optimization** (representative new-parent subsets for broad filtering, full 108,478-train-parent runs only for finalists), with V11 bounded integration/preprocessing readiness checks first. Select checkpoints and hyperparameters on the new library's **validation only**, never its test split or locked RRUFF. Confirm finalists using a small number of seeds; do not require five by habit. The user has **not explicitly instructed stopping the live waiting Optuna supervisor**, so this entry does not claim processes stopped or change the active issue's execution permission. It records the thought evolution and its quantitative rationale for a later owner decision.

## 2026-11-03: Owner cancels old-data Optuna while letting A0/A1/A2 finish; moves final HPO to cloud on 108,478 parents

**Explicit owner decision after reviewing the new D-drive library:** The lead called the old-data hyperparameter optimization “无用功” *for the final target* and directed: **let the in-flight A0/A1/A2 experiments finish and simply archive them; stop further old-database HPO, and plan full 100k+ parent tuning on a new rented GPU server**. This overrides the previous proposal to fully complete the legacy 9,842-parent V10 Optuna before CIF expansion. The revision is not a rejection of the historical A0/A1/A2 architecture/numerical experiments: those already-completed runs are useful, but their `lambda_js`, learning-rate and schedule optima are not portable claims for the larger V11 task.

**Operational action actually performed, 2026-11-03 ~18:06 +0800:** Read process tree and statuses. The six-cell supervisor had completed **A0_R0, A0_R1, A1_R0, A1_R1, A2_R0** and was still running **A2_R1**, independently of Optuna. Targeted `supervise_optuna.py` only, stopped its Python/PowerShell PID chain **47944, 7024, 15928**; verified the A2_R1 Python trial and `run_joint_campaign.py` both remained running. The old Optuna had stayed at `waiting_previous` and **no new Optuna HPO GPU trials were launched**. Appended local `E:\AI4science\_local\resnet_optuna_20261103\owner_cancelled_20261103.json`, changed supervisor state to `cancelled_by_owner`, retaining prior state inside the local record; no training/checkpoint deleted. The prior hourly notification automation was updated to watch **only six-cell archival completion**, never resume old Optuna.

**New dataset was verified earlier in the same session:** `D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103` has **154,975 MP-ID rows, 154,968 independent parent fingerprints, 108,478 train parents, 23,245 val, 23,245 test**; integrity `passed`, old 14,060 kept. The library comprises `*.jsonl.gz` structures, **not** spectra or precomputed ideal peak tables. V11 renders the seven-system sample correctly but still requires conversion from `structure` to the runner's `standardized_structure`/PeakTable contract and corpus-scale readiness verification. The next HPO is therefore gated on the **new library + V11 training workflow**, and should compare candidate hyperparameters on **all 108,478 training parents**, never rely on a small subset as final HPO. Use parent-equivalent epochs not the historical hard-coded 49,280 steps (~80 legacy-parent passes vs ~7.3 new-parent passes at batch 16). Confirm finalists with 2–3 seeds, then freeze and evaluate real RRUFF only after tuning. No cloud instance was rented.

**Paper-trail and implemented status:** [authoritative current state](CURRENT_STATE.md), [new GPU/HPO execution plan](PXRD_154975_CLOUD_HPO_EXECUTION_PLAN_20261103.md), [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) retargeted to cloud/new data, [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61) corrected to already collected database, no repeat acquisition. This is a methodological pivot in response to available resources—not a retroactive rewrite of any experiment.

## 2026-11-03: PR #58 V11 simulator delivered; scale fix and evidence boundary

The earlier 2026-11-03 execution snapshot said implementation could not proceed while the authorized local editing route was unavailable. PR #58 now contains the runnable V11 renderer, online same-parent integration, CIF-to-paired-view path, and acceptance artifacts.

The review identified a mismatch between the V11 unit-area renderer and the legacy Gaussian reference scale: an isolated 0.08° Gaussian-limit peak would reach about 0.399, unintentionally changing the relative background and count-space noise. The PR corrects this at the integration boundary using the rendered V11 peak maximum, while preserving the standalone area-normalized renderer and V9's legacy default.

The PR head `b43e28d` passed 134 non-data-bound CI tests. Its separate validation record also reports seven-system label preservation, fixed-seed replay, V9 regression, broadening trends, and integrated peak-area checks. **No model training was run as part of the V11 validation reported in PR #58, and the PR reports no V11 HPO result.** Later model work follows the current-state readiness gates.

**Integration update (2026-11-05):** PR #58 merged into `main` as commit `940942d5a9c30307295eb7b7a68c08e47687f955`; Stage 1 simulator implementation and integration are complete. The merge commit's main `XRD tests` CI run [#41965621220](https://github.com/Frysland-2024/AI4science/actions/runs/41965621220) passed. The validation record's 50 focused tests and seven-system/paired-view acceptance are simulator engineering evidence only. No V11 model training, HPO, final RRUFF evaluation, or classification improvement is established. Subsequent full-scale HPO remains gated by the structure-schema adapter, corpus-scale PeakTable build, data audits and GPU-throughput proof.

## 2026-11-09: Issue #61 local preflight completed; target-GPU gate assigned to #55 Stage 0

**Date:** 2026-11-09

**Question / previous assumption:** Issue #61 combined local package/schema/manifest/CPU acceptance with target Linux GPU readiness and blocked Issue #55 until both were complete.

**New evidence or reasoning:** Latest `main` commit `158c989` contains the merged-library `--records-path` schema adapter, parent-safe Train+Validation manifest builder with per-PeakTable SHA checks, and regression tests. XRD CI [#42554396816](https://github.com/Frysland-2024/AI4science/actions/runs/42554396816) and V11 migration CI [#42554691047](https://github.com/Frysland-2024/AI4science/actions/runs/42554691047) passed. On the laptop, a fresh private kit using payload contract `v11-prefetch-validation-20261109.3` passed source/archive verification and `start_server.sh --plan`; the full 154,975-record shard/cache readiness audit, frozen 131,729-row Train+Validation manifest reconstruction, one-record CPU PeakTable adapter smoke, one-batch ResNet-A0 CE+JS CPU smoke, and two-worker bitwise prefetch parity smoke passed. Later CPU and local CUDA regressions of the actual shared checkpoint save/restore functions also passed: nine synthetic optimizer steps uninterrupted exactly matched four steps plus checkpoint/restart/restore and five further steps for model tensors, optimizer state, parent sampling, history, and CPU/CUDA Torch RNG. The CUDA test used the local RTX 4060 with PyTorch `2.13.0+cu126`; this does not establish target Linux full-trainer/prefetch resume. The follow-up source contract is `.5`; no `.5` package has been built. The full package evidence and immutable input/output hashes are in `docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md`.

**Decision:** Limit Issue #61 to local package/schema/manifest/CPU acceptance. Move target Linux/CUDA smoke, throughput/resource measurement, complete Validation access through the GPU path, and checkpoint/resume/RNG checks to Stage 0 of Issue #55, before HPO. Stage 0 and any later GPU/HPO work still require separate budget and owner authorization.

**What changes now:** Record the local preflight and CPU checkpoint regression; payload contract `.4` identifies the updated source and the already verified `.3` kit must be rebuilt before transfer. Issue #55 owns the outstanding target-GPU gate as Stage 0.

**What does NOT change:** No cloud instance or target Linux CUDA run was started. No throughput claim, HPO, formal training, research checkpoint, or Test/RRUFF inference was produced; temporary checkpoints in synthetic CPU/CUDA regressions are engineering fixtures only. Local micro-smokes do not establish target Linux GPU readiness, and passing Stage 0 will not automatically authorize HPO.

**Status:** CLOSED for Issue #61 local acceptance; Stage 0 remains ACTIVE / NOT_RUN in Issue #55.
**Relevant files / commits:** `docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md`; `server_migration/README.md`; `server_migration/one_click_v11.py`; `server_migration/tests/test_v11_prefetch_pipeline.py`; source code snapshot `158c989`; CI runs `42554396816`, `42554691047`.
