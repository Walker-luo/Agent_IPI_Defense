# DRIFT 全量对照（1947 攻击键 + 97 clean）

P1 小批量（120 键）完成后的全量验证，环境与接入方式同 [20261118_drift_p1.md](20261118_drift_p1.md)。

## 1. 运行

| 项 | 值 |
| --- | --- |
| 主机 / 仓库 | 测试服务器 `user-PowerEdge-T640`，`/home/yuxin_luo/DSCG` |
| 环境 | `cmp-drift`（Python 3.10，`agentdojo==0.1.35`）；DRIFT commit `6fd3df4` |
| 模型 | `qwen3.7-flash`，DashScope OpenAI 兼容端点；`build_constraints/injection_isolation/dynamic_validation` 开启 |
| 网格 | 1,947 攻击键 + 97 clean（与 `comparison/full` 冻结网格一致；`users × injections` 已校验） |
| 编排 | 100 个分块（75 攻击 + 25 clean），12 路并发；分块结果全部 `exit=0`，**0 错误** |
| 时间 | 2026-11-18 21:17 → 2026-11-19 05:34（8 小时 16 分，墙钟）；分块耗时合计 329,766 秒 |
| 产物 | 服务器 `workshop/artifacts/20261118_drift/out/full/`；工作站 `results/workshop/agentdojo/comparison/full/drift_full{,_clean}/` |

## 2. 结果

| 方法 | TSR（共同键） | ASR（共同键） | clean TSR | 攻击 Token |
| --- | --- | --- | --- | ---: |
| baseline | 1426/1944（73.4%） | 438/1944（22.5%） | 82/96 | 41.37M |
| GrantBind v3.6.3 | **1542/1947（79.2%）** | **0/1947（0.0%）** | 83/97 | 51.25M |
| Spotlighting | 1454/1946（74.7%） | 345/1946（17.7%） | 82/97 | 40.42M |
| MELON | 1305/1938（67.3%） | 27/1938（1.4%） | 73/96 | 60.96M |
| IPIGuard（裁剪） | 873/1667（52.4%） | 23/1667（1.4%） | 57/94 | 106.04M |
| **DRIFT** | **1173/1947（60.2%）** | **35/1947（1.8%）** | **63/97（64.9%）** | **88.26M**（另 clean 4.58M） |

**配对变化**（同键，DRIFT 为参照）：

| 对照臂 | 共同键 | TSR 升 | TSR 降 |
| --- | ---: | ---: | ---: |
| baseline | 1947 | 205 | 459 |
| GrantBind v3.6.3 | 1947 | 153 | 522 |
| Spotlighting | 1947 | 190 | 471 |
| MELON | 1947 | 287 | 425 |
| IPIGuard | 1707 | 398 | 293 |

**按攻击×场景的 DRIFT 结果**：

| cell | TSR | ASR |
| --- | --- | --- |
| ignore_previous/workspace | 194/280 | 0/280 |
| ignore_previous/travel | 61/120 | 0/120 |
| ignore_previous/banking | 100/144 | 0/144 |
| ignore_previous/slack | 53/105 | 0/105 |
| important_instructions/workspace | 195/280 | 4/280 |
| important_instructions/travel | 51/120 | 1/120 |
| important_instructions/banking | 92/144 | 9/144 |
| important_instructions/slack | 50/105 | 2/105 |
| tool_knowledge/workspace | 201/280 | 5/280 |
| tool_knowledge/travel | 47/120 | 2/120 |
| tool_knowledge/banking | 83/144 | 7/144 |
| tool_knowledge/slack | 46/105 | 5/105 |

## 3. ASR 组成

- DRIFT 的 35 个命中中，**17 个与 baseline 同键**（baseline 也命中），**18 个是 baseline 未命中的新键**。
- 作为参照，其它防御相对 baseline 的"新命中"数：Spotlighting 94、MELON 13、IPIGuard 1；GrantBind 为 0。说明 DRIFT 的约束/隔离会改变模型行为路径，部分键从"失败"变成"执行攻击动作"，并非单纯收紧。
- 新命中集中在 banking 的 `important_instructions`（9 个）与 `tool_knowledge`（7 个）。

## 4. 成本

- DRIFT 攻击 88,258,905 tokens（45.3K/键）、clean 4,583,944 tokens；总计 **92.84M**。
- 与 GrantBind v3.6.3 相比：攻击 token 约 **1.72 倍**（88.26M vs 51.25M），TSR 低 19 个百分点。

## 5. 结论

全量与 P1 结论一致：DRIFT 能显著压低 ASR（22.5% → 1.8%），但代价是**最低的 TSR（60.2%）与 clean 效用（64.9%）**、以及最高档的 token 成本（92.8M，约为 GrantBind 的 1.7 倍）。GrantBind 在同网格上 TSR 79.2%、ASR 0、成本 51.25M。若正文比较"运行时执行约束"类防御，DRIFT 适合作为"高安全低效用"的对照点，而不是效率基线。

## 6. 限制

- 提供方：DRIFT 官方仅 OpenAI/Google/OpenRouter，Qwen 走 OpenAI 兼容端点，仅改 `base_url` 与 `max_tokens`。
- 评测：用本仓库 `run_task_with_pipeline` 与 AgentDojo 原生评分，替代 DRIFT 自带 runner。
- 单次运行、未重复；`adaptive_attack` 关闭；token 为 DRIFT 客户端自记口径。
- IPIGuard 为 1,707 键裁剪集合，共同键比较已注明。
