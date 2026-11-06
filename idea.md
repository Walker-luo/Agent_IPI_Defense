# BaseIntent：意图防御的可行性与改进方向

调研截至 2026-10-28；结合本地论文笔记、原始论文及当前源码。以下区分已有机制与改进建议，本次未运行新实验。

## 1. 当前 idea 与判断

主线是：**从可信用户请求提取目标与约束，以 intent 组织规划、动作审计和进度，用真实执行证据判断任务完成。**

当前已有两次 L2 调用、准备前缀归并、冻结全局工具授权、固定 ID 进度关联，以及宿主状态和证据匹配。困难在于：意图正文仍是自然语言，工具足迹不能表达全部对象、次数和完成条件；成功执行与业务满足之间仍依赖语义判断。已有 travel clean 案例中，同一日历事件分别在 answer 阶段和后续 effect 阶段被创建，说明越阶段执行和重复效果不能只靠事后推进修复。[源码](baseintent/intent_flow.py) · [既有验证](docs/reference/maintenance.md)

**判断：方向可做，但宽泛框架的独立新颖性不足，需要收窄贡献。** 可信预规划、任务对齐和证据驱动完成均已有先例；更值得研究的是“意图如何忠实编译，以及不完全证据下如何可靠推进”。现有小样本不足以证明该方向有效，也没有否定整个方向。

## 2. 最接近的论文

| 工作／状态 | 已覆盖的机制 | 与当前 idea 的关系 |
| --- | --- | --- |
| [IPIGuard][1]，EMNLP 2025 | 可信输入生成工具依赖图，按拓扑执行；运行时填未知参数、扩展只读节点 | 已覆盖可信预规划。其核心是工具 DAG，当前是全局授权与独立目标进度。 |
| [PlanGuard][2]，2026 预印本 v1 | 隔离生成参考动作集，工具硬检查后用语义 verifier 判断参数偏差 | 与 L2＋L3 高度重叠；当前另有运行证据推进，不能只靠模块组合声称创新。 |
| [Task Shield][13]，ACL 2025 | 提取用户任务集，检查指令、响应和工具调用是否贡献用户目标 | 已覆盖任务对齐；差异需落在义务表示、证据推进及独立验证。 |
| [CaMeL][4]，SaTML 2026／arXiv v2 | 分离可信控制流与不可信数据处理，用解释器追踪能力和信息流 | 当前保留原生工具循环，不提供同等数据流保证；CaMeL 也支持受限错误恢复。 |
| [Progent][5]，预印本 v3（2026） | 工具／参数符号策略，SMT 检查权限更新是否收缩；扩张需审批机制 | 当前冻结工具级授权，参数主要靠语义审计；更简单不等于更安全。 |
| [TraceGrant][6]，2026 预印本 v1 | 任务契约、活动义务、参数证据、预算、一次性授权、实际结果验证及完成门 | **最强近邻**：已覆盖整体生命周期；状态机、回执和完成门本身不足以构成新贡献。 |

另需区分 [IntentGuard][3]（2025 预印本 v1）：它提取模型打算遵循的指令并溯源，处理的 intent 与这里的用户业务目标不同。

TraceGrant §5.7 的反例尤其关键：来源合规的账单仍可能含假账号；编译器漏绑定可选收款人后，真实执行与有效回执也能确认错误业务效果。因此，**结构合法、来源可追踪、执行成功、目标正确必须分开验证**。[6]

## 3. 哪些算法能帮忙

下表是接入建议，尚未在 BaseIntent／现有 Qwen API 上验证；优先免训练。

| 算法路线 | 建议接入方式 | 前提与局限 |
| --- | --- | --- |
| nl2spec 式可追溯解析 [7] | 将对象、数量、条件、禁止项、顺序和交付绑定原文片段，再检查覆盖 | 原方法依靠交互纠错；片段覆盖不证明语义正确，全自动覆盖检查需另设计。 |
| LLM-Modulo／符号校验 [8] | 模型提出目标，宿主检查类型、引用、前置条件与约束一致性；有限模板再考虑 PDDL／HTN | 校验器只保证模型内一致性，错误领域模型仍可产生合法错计划；另一个 LLM 自审不是形式证明。 |
| LTLf／事件自动机 [9]、[11] | 用具体业务事件推进，区分准备、效果与交付，显式约束顺序和次数 | 需可靠的对象与事件接地；已有宿主状态机可扩展，不能重复计算为创新。只借用 Reward Machines 的状态表示，无须采用其 RL 训练。 |
| 未决监控＋证据依赖 [10]、[12] | 条件另记真／假／未知／冲突，用 AND／OR 证据图表达共同或替代支撑 | LTL 三值的“未决”针对未知未来，事实缺失需另建状态；溯源不认证内容，也不能单独处理否定或顺序。 |

例如“若支出超额则通知”：若未观察到支出，单独检查“超额→最终通知”可能真空满足。必须先要求条件得到证据，再决定分支；未知不能当作 false。自由文本答案的正确与完整，也仍需语义判断。

## 4. 优先改进与可证伪实验

**① 先测清解析错误，再改表示。** 在分配 ID 前增加原文可追溯的目标／约束表示，这是 L2 协议重设计；暂不追求完整规划语言。抽取既有任务，独立标注对象、量词、否定、条件与交付，再做最小改写对照。比较遗漏／新增约束率和语义等价率；若只提高 JSON 合法率，不能算解决解析。

**② 将推进依据落到具体义务。** 保留冻结授权与原效果归属，研究对象、次数和依赖谓词；不要按工具名简单去重。当前进度协议需重设计，执行前的阶段／重复效果门也属于新增机制。固定正确意图，分别测试未知条件、提前回答、跨阶段执行、重复效果、错误对象成功及多对象漏做；同时测试用户确实要求两次同类操作。若误完成减少但合法任务被大量阻挡，方案不成立。

**③ 最后验证是否产生独立防御收益。** 比较现有版本、仅改解析、仅改推进及组合版本，并纳入 TraceGrant 等近邻的同信息条件对照。开发／保留测试按任务分组，意图和结果真值不得用同一模型自评分替代。分别报告解析质量、误推进／停滞、clean TSR、攻击下效用、ASR、调用与 Token。若收益只来自更强模型、更多调用或提前获知答案，不能归因于 intent 机制。

近期建议选①作为切入口、②作为核心验证；只有③显示相对近邻的可检验差异，才适合凝练论文贡献。来源真实性和开放语义仍是边界，不作通用安全保证。上述均为后续实验建议，本次未执行。

## 5. 原始来源

近邻方法核验位置：[1] §3；[2] §IV／Algorithm 1；[3] §3；[4] §5；[5] §4–5、7；[6] §4.2–4.5、5.7；[13] §3–4。算法核验位置：[7] §3；[8] §3；[9] §2、4–5；[10] §2–3；[11] §3–4；[12] §3–4。预印本不视为正式录用，未检索到重合不证明新颖性。

- [1] An et al. *IPIGuard*，2025。
- [2] Gong & Deng. *PlanGuard*，2026。
- [3] Kang et al. *Mitigating Indirect Prompt Injection via Instruction-Following Intent Analysis*，2025。
- [4] Debenedetti et al. *Defeating Prompt Injections by Design*，2025／2026。
- [5] Shi et al. *Progent: Securing AI Agents with Privilege Control*，v3，2026。
- [6] Liao et al. *TraceGrant: A Contract-Governed Security Framework for the Task-Effect Lifecycle of Networked LLM Agents*，2026。
- [7] Cosler et al. *nl2spec*，CAV 2023。
- [8] Kambhampati et al. *Position: LLMs Can’t Plan, But Can Help Planning in LLM-Modulo Frameworks*，ICML 2024。
- [9] De Giacomo & Vardi. *Linear Temporal Logic and Linear Dynamic Logic on Finite Traces*，IJCAI 2013。
- [10] Bauer et al. *Runtime Verification for LTL and TLTL*，TOSEM 2011。
- [11] Toro Icarte et al. *Using Reward Machines for High-Level Task Specification and Decomposition in Reinforcement Learning*，ICML 2018。
- [12] Green et al. *Provenance Semirings*，PODS 2007。
- [13] Jia et al. *The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents*，ACL 2025。

[1]: https://aclanthology.org/2025.emnlp-main.53/
[2]: https://arxiv.org/html/2604.10134v1
[3]: https://arxiv.org/html/2512.00966v1
[4]: https://arxiv.org/html/2503.18813v2
[5]: https://arxiv.org/html/2504.11703v3
[6]: https://arxiv.org/html/2608.21126v1
[7]: https://arxiv.org/html/2303.04864
[8]: https://arxiv.org/html/2402.01817v3
[9]: https://www.cs.rice.edu/~vardi/papers/ijcai13.pdf
[10]: https://christian.schallhart.net/publications/2011--tosem--runtime-verification-for-ltl-and-tltl.pdf
[11]: https://proceedings.mlr.press/v80/icarte18a/icarte18a.pdf
[12]: https://www.cs.ucdavis.edu/~green/papers/pods07.pdf
[13]: https://aclanthology.org/2025.acl-long.1435/
