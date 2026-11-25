# BaseIntent

BaseIntent 是工具使用型 LLM Agent 的间接提示词注入防御研究原型。它从可信任务编译意图与工具权限，校验候选批次，审计具体动作，并结合执行证据推进意图。

当前默认 `prompt_profile=legacy`，框架标识为 `BaseIntent`。运行名称只命名实验，不选择策略。Python 包为 `baseintent`；旧结果保留原身份，兼容范围见[迁移说明](docs/reference/migration.md)。

## 开始使用

从项目根目录执行；已有环境和本地配置可直接使用，无需覆盖：

```bash
# 首次安装时按需创建其中一个环境
conda env create -f environment.yml
# AgentDyn 使用 environment-agentdyn.yml
conda activate ipi
# 或 conda activate ipi-agentdyn
python -m baseintent.benchmark_catalog
```

最后一条命令只核对安装元数据并列出任务目录，不调用模型。配置参考 [config/models.example.toml](config/models.example.toml)，本地凭证放在忽略的 `config/models.local.toml` 或环境变量中。详见[模型与工具配置](docs/reference/model_tool_configuration.md)。

| 环境 | 实际后端 / 场景 | Full clean 计划 | Partial clean / typical 计划 |
| --- | --- | ---: | ---: |
| `ipi` | AgentDojo：workspace、travel、banking、slack | 97 | 12 / 108 |
| `ipi-agentdyn` | AgentDyn：shopping、github、dailylife | 60 | 9 / 81 |

后端以实际导入路径、安装来源、版本及 revision 识别；环境名仅供操作。计划数不是有效评分分母，AgentDyn 部分 `tool_knowledge` 目标不支持。

下列命令会调用真实模型；新实验使用新名称和独立输出目录：

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --model-config config/models.local.toml --name baseintent_partial_01 \
  --results-dir artifacts/20261027_example/partial --progress

python -m dashboard.app
```

Dashboard 默认地址为 [http://127.0.0.1:8888/](http://127.0.0.1:8888/)。完整任务、baseline、clean、目标筛选和续跑命令见[评测指南](docs/benchmark.md)。全量评测应由用户明确启动。

## 当前框架

- **Authorization** 两次主模型调用分别分解意图和冻结全局工具权限。宿主归并准备项、分配意图 ID，并保存工具与进度的关联。
- **Precheck** 校验整批候选的工具、权限、原生参数 schema 和元数据。任一项无效即拒绝整批。
- **Audit** 用四字段判决检查当前动作及完整任务约束。符合条件的 public/internal 读取固定免审。Reference Monitor 使用整批回执和一次性票据介导执行。
- **Intent Progress** 以实际执行与回复为证据推进目标。原生工具消息直接反馈给规划器，复杂目标保留语义判断。

CLI 路由默认 `shadow`，API/factory 默认 `off`。`off` 下 Audit 仍运行，固定读取免审范围在各模式一致。机制与边界见[框架说明](docs/reference/framework.md)。

最近固定键 12 例观察：TSR **8/12 → 7/12**，原生 ASR **0/8 → 0/8**，progress 调用 **61 → 43**，计分 Token **551,741 → 470,265（−14.8%）**。这是有限范围的历史观察，效用验收仍为 partial，不能宣称一般防御有效或整体安全通过。项目整理本身不产生新的效用结论。

## 文档与代码

[文档索引](docs/reference/README.md) · [框架](docs/reference/framework.md) · [配置](docs/reference/model_tool_configuration.md) · [测试](docs/reference/evaluation.md) · [结果](docs/reference/result_files.md) · [Dashboard](docs/reference/dashboard.md) · [迁移](docs/reference/migration.md)

核心代码位于 `baseintent/pipelines/defended.py`、`baseintent/authorization.py`、`baseintent/intent_flow.py` 和 `baseintent/decision_schema.py`。新检查和临时运行产物放在 `artifacts/<日期>_<任务>/`。详见[实验入口](experiments/README.md)。
