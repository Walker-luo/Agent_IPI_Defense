# 小批量评测

`experiments.run_partial_benchmark` 保留每场景注册顺序前 3 个用户与前 3 个注入目标，默认当前后端全部场景。AgentDojo 计划 clean 12 / typical 108，AgentDyn 计划 9 / 81；不支持、错误与 GOAL 单列，实际分母以输出为准。`--suites` 可缩小场景，不能跨后端混选。

## 常用参数

| 参数 | 简要说明 |
| --- | --- |
| `--suites SUITE [SUITE ...]` | 选择当前后端场景，默认全部；每场景仍限定注册前 3 用户 × 前 3 注入目标。 |
| `--attack NAME [NAME ...]` | 选择攻击，默认 `typical`（ignore_previous、important_instructions、tool_knowledge）；可用 `all`。 |
| `--baseline` / `--clean` | 分别选择原生无防御 Agent／无攻击控制；可以组合。 |
| `--model-config PATH` | 模型配置 TOML，缺省按环境变量／本地 `config/models.local.toml` 解析。 |
| `--name NAME` | 输出运行名称；新实验使用新名称，reuse 必填。 |
| `--results-dir DIR` | 结果根目录，默认 `results/partial_benchmark`。 |
| `--progress` | 显示 GOAL 与计分进度。 |
| `--fliter PATH` | 按排除表过滤原前 3 注入目标，不补位，保留前 3 用户。 |
| `--task-manifest PATH` | 使用冻结的 partial 任务 ID 清单。 |
| `--write-task-manifest PATH` | 离线导出当前 partial 清单并退出；目标文件必须不存在。 |
| `--reuse` / `--force-rerun` | 同名同配置续跑／强制重新执行，二者互斥。 |
| `--l1-projection-mode off|shadow|projected` | 当前 CLI 默认 `off`；观察候选用 `shadow`，启用有界银行投影用 `projected`。 |
| `--trace-level summary|standard|full` | 默认 `summary`（可由环境变量覆盖）；需要更多诊断时用 standard/full。 |
| `--no-checker` | 关闭语义动作审计，保留 L2／进度和执行监控。 |

`--fliter` 和 `--goal` 不适用于 clean、DoS 和清单导出。审计路由、profile、工具目录等其余共享选项见[公共防御参数](benchmark.md#可选控制与日志)。完整列表可运行 `python -m experiments.run_partial_benchmark --help`。

## 对照与输出

从 BaseIntent 根目录激活 `ipi` 或 `ipi-agentdyn`。以下命令会调用真实模型，两个对照保持相同环境、任务、攻击、模型配置和新名称：

```bash
python -m experiments.run_partial_benchmark --baseline --suites banking slack \
  --attack ignore_previous --name baseintent_partial_baseline_01 \
  --model-config config/models.local.toml \
  --results-dir artifacts/20261027_example/partial_baseline --progress

python -m experiments.run_partial_benchmark --suites banking slack \
  --attack ignore_previous --name baseintent_partial_01 \
  --model-config config/models.local.toml \
  --results-dir artifacts/20261027_example/partial --progress
```

clean 用 `--clean`，原生 clean 再加 `--baseline`。使用 `--fliter PATH` 从原前 3 个注入目标中删除名单项，不补位。默认直接计分。加 `--goal` 可对剩余目标预检，各攻击共享判定，只有通过者参与计分。

共享参数、攻击、进程调度、baseline 和 reuse 规则见[完整指南](benchmark.md)。默认输出分类根为 `results/partial_benchmark`，新 CLI 路径均为 `<results-dir>/<backend>/<model>_<name>/`。代理检查显式写入新的 `artifacts/<日期>_<任务>/`。

可用 `--task-manifest PATH` 固定 partial 任务 ID，或用 `--write-task-manifest PATH` 离线导出后退出。新 profile、投影、请求格式、进度或审计策略必须新 name，旧测量缓存不跨策略复用；冻结名单不因此重筛。诊断与评分口径见[结果文件](reference/result_files.md)，有限在线观察见[框架](reference/framework.md)。
