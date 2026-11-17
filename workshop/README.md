# Workshop 工程索引

当前框架为 **GrantBind v3.7**（`static-task-v354`）。本目录保存工程方案、阶段记录与实验产物；运行方法和机制以[项目 README](../README.md)、[当前问题](../docs/framework_updates.md)、[配置指南](../docs/model_tool_configuration.md)为准，进行中状态见 [DV_STATE.md](../DV_STATE.md)。

## 当前入口

| 材料 | 用途 |
| --- | --- |
| [L3 多步注入评估计划](l3_multistep_plan.md) | 待执行：用可实现的强攻击测出 L3 净贡献的阶段性方案 |
| [消融分析](../analysis/ablation.md) | full / NoL3 现状：ASR 天花板、L3 拦截与误拒 |
| [全量对比报告](completed/20261111_comparison_full.md) | Spotlighting / MELON / IPIGuard 对比与判定 |
| [AutoInject 接入](completed/20261114_autoinject_setup.md)／[三种攻击](completed/20261114_autoinject_three_attacks.md) | 自适应攻击环境、模板与可复现命令 |
| [Travel 回放](completed/20261116_autoinject_replay_travel.md)／[后缀选型](completed/20261116_suffix_pair_selection.md)／[后缀学习](completed/20261117_suffix_learning_global.md) | AutoInject 后缀在 DSCG 上的学习与回放 |
| [v3.7 发布记录](completed/v37_release_20261103.md) | 当前默认的输入形态与身份 |

完整阶段目录见 [completed](completed/README.md)。

## 目录约定

- `completed/`：阶段计划、实施与诊断报告；完成工程不等于通过研究或安全门槛。
- `artifacts/<YYYYMMDD>_<task>/`：agent 日志、检查、临时测量与快照；每次使用新目录。
- `archive/`：历史材料。`archive/legacy/` 保存早期顶层方案（L1/L2/L3 余项、v3.4/v3.5 计划等）；`archive/artifacts_manifest/` 保存 2026-11-17 的产物清单与清理记录。
- `results/`：旧 `workshop/results/` 证据，按 AGENTS 约定保留，不迁移、不改写。

## 清理记录（2026-11-17）

- `artifacts/` 仅保留 2026-11-01 及之后的产物，以及当前文档（DV_STATE、docs、analysis）引用的四个早期目录；清理前的完整清单与逐项删除记录见 `archive/artifacts_manifest/`。
- `20261104_aimll_paper` 删除本地 LaTeX 构建依赖（`pylibs/`、`tectonic/`、`home/`、`mplcache/`），保留 PDF、页面预览与脚本。
- 顶层历史方案移入 `archive/legacy/`；该时期报告中的旧链接仍按原文保留，不再指向可打开的文件。

在线评测只用 Qwen3.7-Flash 及既有授权规则，详见 [AGENTS.md](../AGENTS.md)。
