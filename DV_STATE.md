# BaseIntent Project State

更新：2026-11-20（Asia/Shanghai）。本文件记录本项目的当前状态和历史核验，恢复时与代码／Git 交叉核对。

## 系统架构图（2026-10-29）

- 已实现：依据当前 README、框架文档与核心源码绘制 `docs/figures/system-architecture.html` 并导出 SVG；仅文档图示，无防御行为或模型调用变更。
- 已核验：技能自检和 SVG 导出通过，SVG 可解析；按用户指定的 sharp 路径导出 3200×1800 PNG 并检查图面。浏览器安全策略禁止打开本地 HTML，几何检查脚本在已安装技能中缺失。记录见 `artifacts/20261029_system_architecture/verification.md`。
- 下一步：根据需要在目标论文或幻灯片中检查缩放后的可读性。

## 当前身份

- `/Users/luo/Desktop/AgentDefence/BaseIntent` 已从原 linked worktree 独立为 Git 仓库。Git 目录和公共目录均为仓库内的 `.git/`，当前只有一个工作区，分支为 `BaseIntent`。
- GitHub 地址为 `git@github.com:Walker-luo/Agent_IPI_Defense.git`，SSH 核验的默认分支为 `master`。核验时本地 `origin` 的拉取与推送地址仍为 `git@github.com:Walker-luo/DSCG.git`。
- 本次文档更新前，本地 `BaseIntent` 位于 `f80754a`，比 GitHub 上位于 `ad135a4` 的同名分支领先 3 个提交。此次核验保留已有的本地未提交改动。
- Python包 `baseintent`；默认引擎标识 `BaseIntent`；原生AgentDojo／AgentDyn、模型、环境名和当前防御算法保留。运行名不选择策略。
- 新环境变量、诊断字段／sidecar、协议命名使用 BaseIntent；旧历史通过只读边界加载，原身份／原生内容／字节不变。新旧环境变量冲突明确拒绝。

## 当前开发基线（2026-10-27 初始化）

- 初始化时核验的分支为 `BaseIntent`，HEAD 为 `ad135a4447e3409c6d1ad4d6458573b93a6f2402`，初始化前工作区干净。此前独立化任务的历史起点为 `361f7db5d76c540278f66464aad0d4942f2f85d4`。
- 已阅读项目约束、当前框架、维护／验证指南，并核对流水线工厂、L2两次授权、准备归并、固定读取免审及L3判决校验的源码入口。后续工作以框架防御设计和相关优化为主，具体方案尚未制定或实现。
- 本次离线检查：`conda run -n ipi python -B -m baseintent.benchmark_catalog` 与 `conda run -n ipi-agentdyn python -B -m baseintent.benchmark_catalog` 均 exit 0；实际导入分别识别 AgentDojo 0.1.35／4场景和锁定 revision 的 AgentDyn／3场景。两者均为 `metadata_only`、`runtime_variant=unverified`，不证明源代码或服务行为。
- 本次仅更新状态记录，未更改防御行为；未重跑完整回归、未调用模型，API调用与Token成本均为0。既有回归失败及有限效用结论仍沿用下文历史记录，不作为本次重新验证结果。
- 下一阶段优先分析意图阶段／完成判定与重复效果归属，再确定优化方案及相应对照；此前封闭评测不追加或重跑，新行为变更按项目验证契约执行。

## 文档整理（2026-10-27）

- 已实现：`docs/` 根目录仅保留 benchmark／partial_benchmark／injection_precheck 三份指南，其余10份移至 `docs/reference/`；同步当前入口和相对链接，三份指南补充参数、默认值及组合限制。
- 已核验：两环境三类 CLI 帮助共6条命令均 exit 0；当前文档链接与参数表检查通过，三个runner哈希与本任务开始时一致。当前用户改动使 full/partial CLI 投影默认为 off，API/factory 仍为 projected，文档分别说明；CLI旧帮助文案仍待单独同步。
- 本次未修改防御／runner行为，未运行完整回归或在线评测；API调用及Token成本为0。命令、源码身份与检查证据见 `artifacts/20261027_docs_cleanup/` 和维护记录。后续仍以框架防御设计和优化为主。

## Dashboard 框架说明（2026-10-27）

- 已更新工作台配置提示和框架介绍，说明 L1 视图、L2 两次授权、进度证据、L3 固定读取免审及 Monitor 边界；未修改防御或评测行为。
- 已验证：`ipi` 与 `ipi-agentdyn` 的 `test_dashboard*.py` 各 50 项通过；Node `tests/*.cjs` 49 项通过；未进行浏览器视觉检查、完整回归或在线评测，模型调用为 0。

## Dashboard 历史数据总览（2026-10-28）

- 已实现：历史分析按实验及已选场景显示 TSR、ASR 的成功数 / 有效分母和已记录 Token；完整明细可在与原汇总一致时补充缺失计数，保留状态与成本缺失提示，不跨实验合并。
- 已验证：两环境 `test_dashboard*.py` 各 50 项及 `test_history_overview.py` 各 3 项通过；Node 52 项通过。实际历史记录接口探针返回 TSR 0/9、ASR 0/9（明细）、已记录 364,922 Token（可能不完整）。
- 两环境完整回归启动后未完成；串行重试在多进程 barrier 测试处停滞并手动中断。沙箱拒绝本地监听，未作浏览器视觉检查；未调用模型。记录见 `artifacts/20261027_dashboard_overview/`。

## Dashboard 历史数据卡片（2026-10-28）

- 已实现：整体测试数据改为按实验和场景的响应式卡片，同场景相邻；版本标记与图表颜色一致，TSR、ASR、Token 使用不同数字颜色。保留原分母、缺失与成本说明，无防御和数据统计变更。
- 已验证：两环境 `test_dashboard*.py` 各 50 项、Node `tests/*.cjs` 54 项通过；浏览器用两条既有实验检查桌面卡片顺序与颜色。未做窄屏实机检查、完整回归或在线评测；模型调用为 0。见 `artifacts/20261028_history_cards/`。

## 意图防御调研（2026-10-28）

- 已完成：在分支 `BaseIntent`、HEAD `77c457818afb55301ac0b2bf8df4beb9397fc8fe` 的干净起点，只读参考用户指定的 Papers 目录并核验原始论文，形成根目录 [idea.md](idea.md)；正文1680个汉字、两张表、13项原始来源。
- 结论：TraceGrant 已覆盖任务—效果生命周期，Task Shield 已覆盖任务对齐，不能将 intent／FSM／回执本身主张为新点。建议优先研究原文可追溯解析与具体义务推进，独立贡献和效果均未验收。
- 已核验：算法／新颖性独立复核完成，补入 Task Shield；引用定义、当前本地链接、篇幅／结构及6份核心源码哈希检查通过，既有重复日历效果的原生记录已复核。未改防御逻辑、未执行完整回归或任何新评测；评测模型调用为0，调研代理usage未提供。证据见 `artifacts/20261028_intent_idea/`。

## Dashboard 历史实验表格（2026-10-28）

- 已实现：整体测试数据按结果统一为一张场景表；不同攻击使用带名称的颜色标签，继续保留实验颜色。仅在所选场景的已记录基准身份完整且一致时增加整体行；缺失、明细来源及 Token 完整性提示不变。
- 已验证：Node `tests/*.cjs` 53 项通过，两环境 `test_dashboard*.py` 各 50 项通过；浏览器检查三种已有攻击的桌面展示。未做窄屏实机检查、完整回归或在线评测；模型调用为 0。见 `artifacts/20261028_history_tables/`。

## Dashboard 历史数据排序（2026-10-28）

- 已实现：整体测试数据按攻击名称分组，再按结果名称自然排序；版本中的数字按数值排序，数据及原结果身份不变。
- 已验证：Node `tests/*.cjs` 54 项通过，两环境 `test_dashboard*.py` 各 50 项通过。未运行完整回归或在线评测；模型调用为 0。见 `artifacts/20261028_history_attack_order/`。

## 评测流程迁移（2026-11-06）

- 基线提交 `b149cae`。已实现 full／partial 的 `--fliter` 和默认关闭的 `--goal`，screen 生成排除表，旧 cohort 执行入口退役。目标过滤、一次 GOAL、续跑绑定、原生计分和成本分开记录。
- AgentDojo 真实 Qwen3.7-Flash 验收 12 次有效计分、9 个不同案例，另有 1 个 GOAL 通过。计分 93 次调用／161662 Token，GOAL 8 次调用／14275 Token。首次沙箱连接错误独立保留，未纳入有效案例。
- 定向验证及基线已知失败见 `artifacts/20261106_fliter_goal/verification.md`。用户更新范围后仅验证 AgentDojo。旧的目标型隐式 GOAL 结果使用新名称重新开始新实验，历史证据按原身份读取。

## 当前实现

L1来源视图和有限银行投影；L2两次调用、无损准备归并、冻结全局工具与固定ID键进度关联；宿主事件／语义进度；L3有限四字段审计；Monitor整批回执与一次性票据。详细行为和限制以 [框架](docs/reference/framework.md) 为准。

公开／internal有效读取在所有模式固定免审，不按sink、URL或对象隐私过滤；personal／secret读取及效果仍审计。自动完成只限于已审核的有界单次直接邀请模式；复杂／未知目标仍需语义判断。

## 本轮独立化（已完成）

- 已完成包导入／当前命名迁移，兼容测试5项通过；旧fixture和身份映射不做全局替换。
- 当前代码、测试及文档不再依赖退役工程目录；保留原目录和证据，新产物改到 `artifacts/`，测试临时父目录可自建。
- README／操作手册约1900行精简到约600行，新增当前框架与迁移指南；Dashboard品牌、框架说明和历史读取已同步。
- Dashboard两后端50项＋旧历史探针2项分别通过，Node49项通过；无退役目录快照Python回归782／786项，失败／错误集合与改名前完全相同（23／6与24／6），未全绿。
- 本轮授权18例已全部完成且有效，错误／未完成0；每组6条GOAL也完成。改名前TSR8/9→BaseIntent7/9，攻击成功均0/6；唯一损失为travel clean重复事件。291次API成功、849,605 Token（计分580,373／GOAL269,232），无usage缺失；不宣称效用等价。证据在 `artifacts/20261027_project_cleanup/`。
- 原结果／下载／退役工程目录23,924文件哈希不变，旧fixture／身份映射10份及归档配置4份原字节保留。旧screen跨命名空间续跑已拒绝。工作区改动未提交，Git结构保留。
- 自动审批曾拒绝全局替换，原命令未执行；已改为逐文件快照核验、AST导入和命名token迁移。在线启动也曾被拒，用户随后明确授权18例。

## 已知研究限制（前一阶段观察）

固定键版本12例原版TSR8/12→7/12、ASR均0/8；progress61→43、计分Token减少14.8%。工程功能可用，但没有通过TSR提升／一般安全的效果验收。餐厅多answer阶段、提前澄清、阶段与效果归属仍有问题；本次独立化不解决这些算法问题。

旧完整回归在ipi有23失败／6错误，在AgentDyn有24失败／6错误，不能以重命名掩盖。历史材料只作背景，不授予本任务额外调用余额。

## 下一步

框架调研已完成，见 [idea.md](idea.md)。下一阶段建议先独立测量解析错误，再设计具体义务／条件／交付的推进协议，并核对 TraceGrant 等近邻；这些方案尚未实施。此前封闭评测保持封闭，不追加或重跑；既有工程与效用限制见 [维护记录](docs/reference/maintenance.md)。
