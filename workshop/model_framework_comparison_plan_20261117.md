# GrantBind 投稿前模型与防御对照扩展计划

**状态**　P1 的 DRIFT 小批量（108 攻击键 + 12 clean）已于 2026-11-18 完成，见 [报告](completed/20261118_drift_p1.md)；全量（1947 + 97）待确认。核对基线为工作站 `workshop@84e4653`。

**目标**　为 IWCMC 2027 · AIMLL Workshop 补齐完整系统的 clean 与成本证据，增加一个可严格配对的外部防御，验证 GrantBind 能否迁移到独立的模型家族。正文按 6 页组织。

**测量配置**　GrantBind v3.7，默认 `static-task-v354 / authorization_input=v3 / audit_presentation=v3`。AgentDojo 0.1.35，suite v1.2，使用原生任务评分。

**依据**　[投稿目标](../README.md#论文投稿iwcmc-2027--aimll-workshop) · [当前稿件](../../paper/GrantBind/main.tex) · [外部防御归档](../results/workshop/agentdojo/comparison/README.md) · [运行约定](../AGENTS.md)

## 1. 起点与证据缺口

| 证据 | 当前状态 | 本轮处理 |
| --- | --- | --- |
| 三模型主结果 | Qwen3.7-Flash、DeepSeek-Flash、Qwen3.8-Flash 分别有 1,943、1,836、1,531 个 Native / GrantBind 共同有效注入键 | 保留三行主结果和模型内配对。Qwen3.5-Flash 继续作为历史诊断。 |
| Qwen3.7-Flash clean | `qwen3.7-flash/clean/` 有 97 条原生轨迹，缺根 `run_manifest.json`，稿件指出重试设置无法确认 | 先查历史配置与逐键错误；配对条件不能证实时补 Native / GrantBind 两臂。 |
| 五方法外部归档 | 1,657 个共同有效键中，Native、GrantBind、Spotlighting 的注入文本和位置一致。MELON 有 553 键与 Native 文本一致，均为 `ignore_previous`。IPIGuard 同一交集中有 0 键与 Native 文本完全一致 | 单列严格配对结果、MELON / IPIGuard 归档复现结果与整臂成本。Tool Filter 归档标为端点兼容性失败。 |
| Qwen3.7-Flash 108 键参考 | `comparison/partial_108` 的 `baseline_108` 和 `v37_108` 在全部 108 键的注入文本和位置一致，两个 clean 臂各有 12 条轨迹 | 作为 DRIFT 的参考臂候选，启动前再核实有效运行配置和原始计分范围。 |

## 2. P0 · 核证归档并补全 Qwen3.7-Flash clean

- [ ] 核对 `clean/` 与 `v3.6.3_clean/` 的模型 ID、提供方、角色采样设置、实际重试、后端/套件身份及逐键错误记录。统一用原生标签和当前共享错误投影得到共同有效 clean 键，解释历史汇总与稿件分母的差异。
- [ ] 若历史配置仍无法确认，使用 [完整入口](../docs/benchmark.md)在相同模型和设置下重跑 Native 与 GrantBind 的 97 个全场景 clean 任务。使用 `--clean`，Native 加 `--baseline`。新跑共 **194 个计划计分任务**。输出每臂有效分母和同键效用变化。
- [ ] 用逐任务完整成本记录在同一个共同试验集合上重算调用数、Token 和延迟，注明成本可用数。分别记录输入、输出、已知缓存用量、主模型、授权和审计，MELON embedding 独立呈现。只保留整臂账本的历史结果按归档覆盖量报告。正文用脚本生成表格。

## 3. P1 · 增加 DRIFT 严格配对对照

| 防御 | 处理方式 | 原因 |
| --- | --- | --- |
| **DRIFT（NeurIPS 2025）** | 首选新实验臂。固定官方实现 revision，保留约束生成、注入隔离和动态验证。 | 与 GrantBind 在运行时执行约束上直接可比，官方提供 AgentDojo 0.1.35 入口。 [论文](https://proceedings.neurips.cc/paper_files/paper/2025/hash/77f3b26c7907aa27b207df9b9d43f29a-Abstract-Conference.html) · [官方实现](https://github.com/SaFo-Lab/DRIFT) |
| **Progent** | DRIFT 同模型适配无法保真时的备选。记录策略生成模型、动态更新和回退设置。 | 直接比较可编程权限策略与任务级工具授权。 [论文](https://arxiv.org/abs/2504.11703) · [官方实现](https://github.com/lindsey98/progent) |
| **Spotlighting、MELON、IPIGuard** | 优先复用归档。Spotlighting 纳入已有同输入对照，MELON 和 IPIGuard 保留移植或套件差异说明。 | 分别代表输入标记、重执行与工具依赖图约束。 |

- [x] 从归档 `comparison/partial_108/{baseline_108,v37_108}` 冻结任务键、注入位置、原始输入摘要和排除表（108 攻击键 + 12 clean；注入 sha256 全部一致）。覆盖 Workspace、Travel、Banking、Slack 及 `ignore_previous`、`important_instructions`、`tool_knowledge`，每臂 **108 个注入计分键 + 12 个 clean 键**。clean 名单从对应历史 clean 臂冻结。
- [x] 锁定 DRIFT 官方 revision（`6fd3df4`）、套件（AgentDojo 0.1.35 / v1.2）和调用范围；Qwen 经 DashScope OpenAI 兼容端点接入，仅改 `base_url` 与 `max_tokens`。DRIFT 用独立对照入口，Native 和 GrantBind 用 [小批量入口](../docs/partial_benchmark.md)。开跑前逐臂核对测试键、原始注入文本与位置、任务定义、工具 schema、原生评分和实际请求设置。
- [x] Qwen3.7-Flash 历史 Native / GrantBind 满足配对要求，只跑 DRIFT 的 **120** 个计划计分任务（108 攻击 + 12 clean，0 缺失、0 注入不一致）。全量 1947+97 的 DRIFT 臂待单独确认。历史参考不能复用时，补跑所需参考臂，三臂全新上限 **360**。若 DRIFT 无法保真接入 Qwen，优先将 DRIFT 合并到下节获准的第四模型实验，三臂使用同一个模型。若保真条件仍不满足，评估 Progent 的单臂可行性并记录阻塞原因。

## 4. P2 · 扩展一个模型家族

| 候选 | 角色 |
| --- | --- |
| **GPT‑5.4 mini**，固定 `gpt-5.4-mini-2026-03-17` | 首选第四模型。官方支持 Chat Completions、函数调用及结构化输出，适合沿用现有 OpenAI 配置路径。 [官方文档](https://developers.openai.com/api/docs/models/gpt-5.4-mini) |
| **Claude Haiku 5.5** | 备选。适合验证不同提供方的工具消息结构，先核实 `tool_use`、`tool_result` 以及推理设置。 [官方文档](https://platform.claude.com/docs/en/models/haiku-5-5/overview) · [工具调用](https://platform.claude.com/docs/claude/docs/tool-use) |
| **Gemini 3.8 Flash** | 备选。若要与 DRIFT 共用其官方提供方路径，可优先评估。 [官方文档](https://ai.google.dev/gemini-api/docs/latest-model) |

- [ ] 选定一个当轮明确授权的候选。先确认账户可用的真实模型 ID、端点与请求参数，验证合法任务中的工具调用往返和结构化输出可用。以本项目原生评分衡量任务，GrantBind 的规划、授权和审计使用同一模型。
- [ ] 在同一冻结任务网格运行 Native / GrantBind。两臂各 **108 个注入键 + 12 个 clean 键**，合计 **240** 个计划计分任务。若并入 DRIFT，合计 **360**，共用两条参考臂。归档注入模板如果随模型生成文本，模型内各臂须绑定同一份实际输入；跨模型只比较各自的配对差值及覆盖。
- [ ] 按模型内配对给出 TSR、ASR、clean TSR、分母及代价，正文将该批次标为第四模型的小范围迁移验证。若关键场景缺失、协议失败或结果过于稀疏，先报告原因，再决定是否另立扩展批次。

## 5. 配对、计账与交付

- [ ] **开跑前**冻结每臂的计划键及输入哈希、模型/提供方、后端/套件、框架 revision、生效的采样和重试、计分投影以及对照实现版本。使用同一预先固定的排除名单。新实验以冻结网格计分，GOAL 预检费用如有发生则独立记录。
- [ ] **判分后**对每臂报告计划、尝试、完成、有效、错误及未完成计数。主对照按共同有效且实际输入一致的试验配对，单列缺键、输入不一致和错误数。报告 TSR / ASR 的计数、差值和配对变化，按场景和注入类型列出覆盖。clean 的 ASR 记为不适用。低事件数只报告观测范围。
- [ ] **成本**报告 API 尝试数、成功数、已知 Token、未知用量记录和计分范围；可比较时报告同键每任务成本和延迟中位数。费用与延迟按提供方及测量环境解释。
- [ ] **产物**正式结果放在服务器 `/home/yuxin_luo/DSCG/results/workshop/agentdojo/<model>/<name>/`，每臂采用新名字，clean 名称以 `_clean` 结尾。启动脚本、冻结名单、哈希、日志与复算输出放 `workshop/artifacts/<YYYYMMDD>_paper_expansion/`。阶段报告放 `workshop/completed/`，列出主机、conda 环境、revision、命令、退出码、结果路径、API 用量和覆盖限制。
- [ ] **执行顺序**先核证归档和 clean，再补 DRIFT，最后按授权补一个模型。在线默认授权为 Qwen3.7-Flash。计划中的第四模型候选及外部实现可能使用的额外模型，按 [AGENTS.md](../AGENTS.md) 核对当轮授权后启动。
