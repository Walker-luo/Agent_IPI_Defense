# GrantBind v3.7

GrantBind 用于防御工具调用智能体遇到的间接提示注入。L1 隔离规划输入，L2 从可信任务编译工具权限，L3 审计实际调用，Monitor 在执行前统一检查授权和审计结果。

默认策略为 `static-task-v354`，运行版本记录为 `DSCG_v3.7`。`dscg` 导入路径、`DSCG_*` 环境变量和诊断字段沿用现有标识。正常测试直接运行 benchmark，无需额外选择 profile。

## 当前框架与工作流程

| 组件 | 处理内容 | 输出与调用开销 |
| --- | --- | --- |
| L1 输入隔离 | 每轮从原始历史复制规划视图，标记工具返回为不可信数据并转义边界标记 | 仅改变主模型看到的内容，无独立模型调用 |
| L2 任务授权 | 完整可信请求 → 静态任务视图 → 全局动作工具权限，合并已注册读取工具 | 冻结授权和目录，向主模型展示已授权工具；普通动作任务通常两次 main 调用 |
| L3 动作审计 | 核对当前工具参数、原生 schema／效果、完整可信请求及相关原始返回 | 严格四字段判决；非免审批次通常一次 security 调用 |
| Monitor 执行监控 | 复核整批候选、目录、任务、授权、审计记录及一次性执行票据 | 按原生顺序执行或阻断，无独立模型调用 |

层间共享由宿主代码完成。L2 的静态任务视图供主模型和 L3 参考，冻结授权供前置检查与 Monitor 使用。工具原始返回分别进入 L1 规划视图和 L3 证据选择器；L3 使用原始历史，不使用 L1 投影后的正文。阻断经工具错误反馈给主模型，普通工具内容不能新增任务或权限。

详细机制、数据流和边界见 [v3.7 架构说明](docs/architecture.md)。

## 默认配置

- L1 输入隔离开启。CLI 的 `l1_projection_mode=off` 仍做来源封装；factory/API 默认 `projected`。结构化投影仅覆盖匹配的银行月支出任务，保留全部交易和六个结构字段。
- L2 默认两阶段，`authorization_input=v3` 使用紧凑工具目录。自动授权读取与 L3 免审是两个判定，私人读取仍需审计。
- L3 默认 `audit_presentation=v3`。相关返回的共享字符预算通常为 8192，需要时在同一次审计输入内扩至 32768，候选参数文本上限 8192；超限仍明确截断。
- 已注册、已授权、schema 有效的 `read + public/internal + sink=none` 调用固定免审。其他动作继续交给 L3。CLI router 默认 `shadow`，factory/API 默认 `off`，两者均保留此规则，`off` 仍运行 L3。
- 两种输入形态及其他有效配置进入 `run_manifest.json` 和缓存身份。普通运行保持 `audit_retries=0`、`completion_prompt=false`。

## 安装与配置

在项目根执行。已有环境和本地配置按原配置使用。

```bash
conda env create -f environment.yml
conda activate ipi
python -m dscg.benchmark_catalog
```

工作站 AgentDojo 环境为 `ipi`，测试服务器环境为 `DSCG`。服务器非交互终端使用 `~/miniconda3/bin/conda run -n DSCG ...`。当前评测使用 AgentDojo 0.1.35 / v1.2，包含 workspace、travel、banking、slack；后端身份由实际安装读取。

首次配置参考 [模型模板](config/models.example.toml)。`main` 负责规划、L2 和最终回答，`security` 负责 L3。日常在线验证统一使用真实 `qwen3.7-flash`，其他模型需当轮明确授权。连接地址、Key、工具风险目录和请求设置见 [配置指南](docs/model_tool_configuration.md)。

## 运行测试

以下命令会调用真实模型。先选择未使用的运行名，再运行匹配的 baseline clean 与 v3.7 clean。

```bash
python -m experiments.run_partial_benchmark --baseline --clean \
  --results-dir results/workshop --name baseline_doc01_clean --progress
python -m experiments.run_partial_benchmark --clean \
  --results-dir results/workshop --name v3.7_doc01_clean --progress
```

partial 固定每场景注册前 3 用户 × 前 3 注入目标，clean 只取用户前缀。完整所选场景使用 `experiments.run_benchmark`。攻击测试先用独立 `screen` 生成 `fliter.json`，再给 baseline 与 v3.7 使用同一名单；`--goal` 默认关闭，仅在需要当前框架再次筛选目标时添加。用法见 [评测入口](docs/evaluation.md)、[完整测试](docs/benchmark.md)、[小批量测试](docs/partial_benchmark.md)和 [筛选指南](docs/injection_precheck.md)。

指定上述输出根时，结果位于 `results/workshop/<backend>/<model>/<name>/`。先看根 `summary.md`，再通过 `failure_cases.jsonl` 定位轨迹。原生任务路径为 `<attack>/<suite>/<user>/<injection>.json`，防御诊断与完整 L3 回复使用同名 JSONL。成本同时核对 main 和 security，详情见 [结果文件](docs/result_files.md)。

## Dashboard

```bash
python -m dashboard.app
```

打开 [实验配置](http://127.0.0.1:8888/) 或 [历史分析](http://127.0.0.1:8888/history)。页面使用当前默认策略，运行名只命名实验。API、历史对比及下载说明见 [Dashboard 指南](docs/dashboard.md)。

## 当前限制

授权范围是工具级；静态任务视图与风险标签不能认证事实、对象隐私、条件成立或任务完成。最终文本没有独立动作审计，模型仍可能漏做、误判参数或交付不完整。

最新 workspace 消融中，完整组与 NoL3 均为零攻击命中；NoL2 路径同时丢失工具元数据，导致 L3 大量 `MISSING_EVIDENCE` 阻断。该缺陷尚未修复，当前结果须结合这一干扰解释，见 [当前问题](docs/framework_updates.md)。消融原始结果归档在 `results/workshop/agentdojo/ablation/`，Dashboard 历史页把 `ablation` 作为模型值直接选择。

## 论文投稿（IWCMC 2027 · AIMLL Workshop）

论文工作区在兄弟目录 [`../paper/GrantBind`](../paper/GrantBind)（稿件 `main.tex`、要求档案 `requirements/`、图与脚本 `fig/`、打包 `tools/`）；本仓库负责代码、结果与数据可重跑。目标是一篇 **≤6 页的 IEEEtran conference 双栏论文**，按 CFP 要求原创、未同时投稿，录用并报告后进入 IEEE Xplore（[AIMLL CFP](<../paper/GrantBind/requirements/AIMLL WS.pdf>)）。

| 里程碑 | 官方日期 | 交付物 |
| --- | --- | --- |
| 投稿截止 | 2027-01-15（时区待核实） | `main.pdf` ≤6 页 + `GrantBind.zip` 源包，Sparcly（conference=100 / entity=495）提交 |
| 录用通知 | 2027-03-30 | 评审意见归档，决定修订/撤稿 |
| Camera-ready | 2027-04-30 | 终稿 PDF（IEEE eCF / PDF eXpress）、版权表、图源 |
| 作者注册 | 2027-05-15 | 至少一位作者注册回执 |
| 会议 | 2027-06-13—17（官网列 06-13—18，差异待核） | 报告 slides；Best Paper 参评 |

**阶段**

1. **合规前置（P0）**：登录 Sparcly 核对 entry 显示名、主席、盲审规则与截止时区（本地 CFP 与官网列名不一致，CFP 还误写"IEEE IWCMC 2026 proceedings"）；确认原创且未同时投稿；复核 IEEE 的 AI 使用披露与伦理要求。结论回填论文仓 `requirements/venue.md` 与 `official-sources.md`。
2. **证据冻结**：正文口径固定为 v3.7（`v3.6.3` ≡ 同配置），三模型主结果 + 外部防御对照；补齐可比 clean 与同计分范围成本；页数与图只引用 `fig/` 脚本重算出的数字，禁止手抄。L3 相关主张以 [L3 多步注入评估计划](workshop/l3_multistep_plan.md) 的结论为准——未形成可分析结果时正文只写"机制互补"，不宣称实证增益。
3. **写作与页数**：按论文仓 `requirements/venue.md` 的 P0/P1 清单闭环；页数由 `tools/build.sh` 读取 `requirements/page_limit` 检查，超页优先压缩附录与图，不加页。
4. **发布检查**：`./tools/release.sh GrantBind` 生成提交包；核对页数、图引用、参考文献、未定义引用、匿名/署名与 AI 披露；`GrantBind.zip` 与目录名一致，只含正文引用图；旧 rev2 留在 `archive/`。
5. **提交与归档**：Sparcly 上传 PDF 与源包；把 submission ID、回执与截图归档到论文仓 `requirements/official-sources.md`，并在 `DV_STATE.md` 记一行状态。
6. **录用后**：按意见修订；camera-ready 核对 eCF、PDF eXpress、超页费、作者顺序与单位；准备 06 月报告。

**提交前清单**

- [ ] 页数 ≤6，IEEEtran conference 双栏，无未定义引用
- [ ] 匿名/署名与 track 规定一致（盲审规则核实后再定）
- [ ] 原创、未同时投稿（作者确认）
- [ ] AI 使用披露与致谢、基金信息合规
- [ ] 正文数字与图可由 `fig/` 脚本重跑，数据根为 `results/workshop`
- [ ] `GrantBind.zip` 命名与内容符合会务要求
- [ ] submission ID 与回执归档

**阻塞项**：Sparcly entry 的显示名与主席、盲审规则、截止时区、2027 作者指南/模板/纸型、PDF eXpress 编号与注册平台、Xplore 收录条件与超页费，均待官方页面可读或登录后核实，不能以往年流程替代。

## 文档与目录

[文档索引](docs/README.md) · [架构与层间通信](docs/architecture.md) · [项目状态](DV_STATE.md) · [协作规则](AGENTS.md)

| 路径 | 用途 |
| --- | --- |
| `dscg/`、`config/` | 框架与配置 |
| `experiments/`、`tests/`、`dashboard/` | 评测入口、回归与界面 |
| `analysis/`、`workshop/` | 分析、工程方案及阶段记录 |
| `workshop/artifacts/<YYYYMMDD>_<task>/` | 新建的 agent 检查与临时验证产物 |
| `results/`、`download/` | 正式原始结果与分析导出 |

研究路线见兄弟仓库的 [technical_route.md](../research/technical_route.md)。
