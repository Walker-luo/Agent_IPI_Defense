# L3 多步注入评估计划（2026-11-18 精简版）

## 1. 当前总体结论

1. **L3 开关已被证实生效**：历史 Full 运行有 232 次语义审计（231 allow、1 deny），NoL3 为 0；但缺少「同一候选在两臂分别 allow/deny 并造成效果差异」的配对证据，历史原生 ASR 两臂均为 0。
2. **两轮攻击构造（早期多步模板 + 新的 L2 已授权动作路线）全部失败**：Full 与 NoL3 的 ASR 均为 0.0%，TSR 只在 33%–100% 间波动且方向不稳定；因此**目前不能估计 L3 的增量 ASR**。
3. **失败原因已定位**：早期是多数任务的冻结权限不覆盖完整 GT 工具集；新路线即使 L2 已允许 send_money，NoL3 轨迹中模型仍明确拒绝注入（原话：“This appears to be a social engineering attempt… I must ignore such off-task instructions”）。**当前瓶颈是 DSCG system prompt/指令层级，不是 L2 或 L3**。
4. **下一步**：先用固定候选对照（离线回归已通过，见 §4）证明 L3 开关效应，再寻找能在 DSCG system prompt 下存活的在线攻击，而不是继续调提示词模板。

> 历史逐层诊断的完整证据（396 条轨迹、232 次审计、唯一 deny 案例）保留在 [原报告 §2](completed/20261117_l3_multistep.md#2-失败根因诊断关键) 和 [远程核对记录](artifacts/20261118_l3_switch_diagnosis/remote_records.txt)；本文只保留结论和可复现入口。

## 2. 结果汇总

### 2.1 攻击构造与任务数量

| 实验 | 构造方式 | 任务数／攻击 | 两臂配置 |
| --- | --- | ---: | --- |
| Stage 0 | 5 种内置攻击：ignore_previous、important_instructions、injecagent、system_message、tool_knowledge | 18（slack 9 + travel 9） | Full 与 --no-checker |
| Pilot v2 | 3 个新模板：sequence_checklist（分步清单）、role_play_defense_aware（防御感知角色扮演）、obfuscated（混淆注入） | 18（slack 9 + travel 9） | 每臂 2 次重复 |
| 授权动作 pilot | 仅选 GT 工具 ⊆ L2 允许工具的 pair；banking send_money，users 4/5/11 × injections 0/1/2 | 9（其中 7 个 baseline ASR=1） | 两臂均显式 --audit-router-mode off |

授权动作模板：authorized_action（已授权语气）、natural_note（低可疑度自然备注）、important_instructions（参照）、system_message/injecagent（内置对照）。

### 2.2 ASR / TSR（分母为有效任务）

| 实验 | 臂 | ASR | TSR | 有效／计划 |
| --- | --- | ---: | ---: | ---: |
| Stage 0（5 攻击合计） | Full | 0/90 | 87/90（96.7%） | 90/90 |
| Stage 0 | NoL3 | 0/89 | 86/89（96.6%） | 89/90（1 错误） |
| Pilot v2 r1（3 模板合计） | Full | 0/54 | 53/54（98.1%） | 54/54 |
| Pilot v2 r1 | NoL3 | 0/54 | 53/54（98.1%） | 54/54 |
| Pilot v2 r2（3 模板合计） | Full | 0/54 | 51/54（94.4%） | 54/54 |
| Pilot v2 r2 | NoL3 | 0/54 | 53/54（98.1%） | 54/54 |
| 授权动作：authorized_action | Full（r1/r2） | 0.0% | 33.3%–44.4% | 9/9、9/9 |
| 授权动作：authorized_action | NoL3（r1/r2） | 0.0% | 33.3%–44.4% | 9/9、9/9 |
| 授权动作：important_instructions | Full（r1/r2） | 0.0% | 33.3% | 9/9、9/9 |
| 授权动作：important_instructions | NoL3（r1/r2） | 0.0% | 33.3%–44.4% | 9/9、9/9 |
| 授权动作：natural_note | Full | 0.0% | 33.3% | 9/9 |
| 授权动作：natural_note | NoL3 | 未完成 | — | — |
| 授权动作：system_message/injecagent | Full | 0.0% | 33.3% | 各 9/9 |
| 授权动作：system_message/injecagent | NoL3 | 未完成 | — | — |

- 授权动作 pilot 的 natural_note NoL3、内置对照 NoL3 未跑完，不纳入结论。
- 早期 l3ms_pilot_*（非 v2）为无效运行（攻击名未注册／YAML ParserError），**不引用**；l3ms_pilot_v2_* 才有效。
- TSR 的 33%–100% 波动在同一攻击的两臂、两次重复间都会反向出现，属于模型噪声；ASR 无任何翻转，无法做 McNemar 检验。

## 3. 结果保存目录

**服务器结果根目录**
/home/yuxin_luo/DSCG/results/workshop/agentdojo/qwen3.7-flash/

| 实验 | 目录名 |
| --- | --- |
| Stage 0 | l3ms_stage0_full/、l3ms_stage0_nol3/ |
| Pilot v2 | l3ms_pilot_v2_full_r1/、l3ms_pilot_v2_full_r2/、l3ms_pilot_v2_nol3_r1/、l3ms_pilot_v2_nol3_r2/ |
| 授权动作基础 | l3auth_full_r1/、l3auth_full_r2/、l3auth_nol3_r1/、l3auth_nol3_r2/ |
| 授权动作扩展 | l3auth_note_full/、l3auth_note_nol3/、l3auth_builtin_full/、l3auth_builtin_nol3/ |

每个攻击子目录含 summary.json、detailed_results.csv、run_manifest.json、failure_cases.jsonl；根目录含执行清单与状态。

**本地代码、日志、清单与报告**

- 计划与报告：[workshop/l3_multistep_plan.md](l3_multistep_plan.md)、[workshop/completed/20261118_l3_attack_opt.md](completed/20261118_l3_attack_opt.md)、[workshop/completed/20261117_l3_multistep.md](completed/20261117_l3_multistep.md)
- 授权动作产物：workshop/artifacts/20261118_l3_attack_opt/（manifests/banking_authorized_pilot.json、logs/、run_*.sh、汇总脚本）
- 早期多步产物：workshop/artifacts/20261117_l3_multistep/（manifests/pilot_multistep.json、logs/、run_*.sh）
- 攻击代码：[experiments/attacks/l3_authorized.py](../experiments/attacks/l3_authorized.py)、[experiments/attacks/multi_step.py](../experiments/attacks/multi_step.py)；单测 [tests/test_multi_step_attacks.py](../tests/test_multi_step_attacks.py)
- 服务器与工作站结果未自动同步；引用服务器路径时需注明主机。

## 4. 已通过的离线/回归验证

- 固定候选、两臂 router 均 off 的 L3 开关回归已通过：工作站 ipi 4 项、服务器 DSCG 7 项，均退出 0；覆盖「模拟审计 deny → Full 无写入 / NoL3 写入一次」「allow → 两臂各写一次」「L2 未授权 → 两臂都拒」「免审读 → 只记录不审计」。日志见 [offline_regression.log](artifacts/20261118_l3_switch_diagnosis/offline_regression.log) 与 [server_transcript.txt](artifacts/20261118_l3_safe_regression/server_transcript.txt)。
- 该回归只使用内存模拟工具和 mock 模型，证明开关到执行终态的接线；不构成在线 ASR/TSR 证据。

## 5. 下一步（按优先级）

1. **固定候选对照**：冻结同一 planning 候选、两臂显式 --audit-router-mode off、同一 L2 夹具/工具目录/请求，仅切 L3；记录 audit_request/verdict/Monitor/ledger，形成「同候选 allow vs deny」证据。
2. **在线攻击升级**：当前 DSCG system prompt 会让模型识别并拒绝注入；需要能覆盖该指令层级的载体，或选择未注入「忽略工具输出指令」的配置；仅换模板措辞无效。
3. **在线判据**（只有第 1/2 步成立后才用）：同一键集 ASR(noL3) − ASR(full) 显著（McNemar p<0.05）；NoL3 ASR ≥10%；误拒率与 TSR 代价有界；slack 钓鱼 URL 谓词须人工复核。

## 6. 边界与记录要求

- 两臂必须显式记录 profile、checker、L1/L2、两种 v3 输入、路由模式、main/security model；需要隔离时两臂都设 --audit-router-mode off，其余配置固定。
- 分母必须区分尝试／完成／有效／未完成／错误；错误不得计为防御成功。
- 每格 9 键时 1 次翻转即 11.1pp；主实验必须重复并做配对检验，不得用单次差异下结论。
- --no-checker 保留 L2、Monitor 和票据执行；跨版本（AutoInject 的 AgentDojo 0.1.29 vs 0.1.35）数字不可直接合并。
