# 注入目标筛选与冻结名单

Screen 直接请求每个注入 GOAL，给每个目标一次完整原生轨迹：成功保留，失败排除，错误/中断单列跳过。不进行同轮、同名续跑或历史证据中的第二次机会。GOAL 不是用户×注入的计分任务，不能进入 TSR/ASR 分母。

## 参数

筛选使用 `screen` 子命令，以原生无防御 Agent 直接执行注入 GOAL；没有 benchmark 的攻击选择或防御参数。

| 参数 | 简要说明 |
| --- | --- |
| `screen` | 创建或恢复一次 GOAL 筛选，生成目标排除表。 |
| `--suites SUITE [SUITE ...]` | 选择当前后端场景，默认全部；AgentDojo 与 AgentDyn 场景不能混选。 |
| `--model-config PATH` | 主模型配置 TOML，缺省按环境变量／本地 `config/models.local.toml` 解析。 |
| `--name NAME` | 必填；筛选运行名称，中断后使用相同名称和配置继续。 |
| `--results-dir DIR` | 结果根目录，默认 `results/injection_precheck`；名单位于运行目录的 `fliter.json`。 |
| `--reuse-from PATH` | 可选；只读复用指定历史 baseline 运行中的首份兼容 GOAL 证据，不重试已失败目标。 |
| `--help` | 查看帮助；筛选参数列表使用 `python -m experiments.run_injection_precheck screen --help`。 |

screen 自带进度输出，无需 `--progress`；续跑直接重复同一命令，无需 `--reuse`，也不支持 `--force-rerun`。

## 创建名单

从 BaseIntent 根目录激活目标环境，核对配置后执行；本命令会调用真实模型：

```bash
python -m experiments.run_injection_precheck screen --suites banking slack \
  --model-config config/models.local.toml --name screen_01 \
  --results-dir artifacts/20261027_screen
```

默认分类根为 `results/injection_precheck`，新路径为 `<results-dir>/<backend>/<model>_<name>/`，实际 `fliter.json` 路径由命令输出。只读历史复用可显式加 `--reuse-from PATH`，选择第一份兼容证据，不自动重试失败。来源、模型/provider、后端、任务及筛选证据按创建协议校验，不改写原文件。

<a id="2-中断和错误后续跑"></a>

## 中断和错误后续跑

保留同一 screen 命令和 name 再运行，仅开始未启动目标，已完成失败/错误不重试。旧证据和冻结名单保持原字节/语义。即使有错误仍可生成排除表，错误保留且退出码为 1；不能把跳过或连接失败算作排除成功。

## 消费名单

Full 和 partial 使用 `--fliter PATH`。名单只包含 schema、后端和排除 ID。

```json
{
  "schema_version": "baseintent.fliter.v1",
  "benchmark": {
    "id": "agentdojo",
    "suite_version": "v1.2",
    "revision": "pypi:agentdojo==0.1.35"
  },
  "excluded": {"banking": ["injection_task_0"]}
}
```

显式传入的 GrantBind `dscg.fliter.v1` 可按相同规则读取。使用实际后端目录生成 ID 和 revision。传入 `--goal` 后，评测在应用排除表后用当前 pipeline 逐目标执行一次直接 GOAL。错误与失败分别报告，只有通过者计分。旧 cohort 和转发入口已退役。
