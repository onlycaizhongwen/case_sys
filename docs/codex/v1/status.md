# 项目状态

- 当前版本：v1
- 当前阶段：已完成
- 当前主题：multi-horizon-recommendation

## 需求索引

| 主题 | 状态 | Requirements | Design | Plan | 依赖 |
| --- | --- | --- | --- | --- | --- |
| coin-recommendation-system | 已完成 | `docs/codex/v1/requirements/coin-recommendation-system-requirements.md` | `docs/codex/v1/designs/coin-recommendation-system-design.md` | `docs/codex/v1/plans/coin-recommendation-system-plan.md` | `binance_day_contract_realtime_v5.py` |
| coin-recommendation-runtime-enhancement | 已完成 | `docs/codex/v1/requirements/coin-recommendation-runtime-enhancement-requirements.md` | `docs/codex/v1/designs/coin-recommendation-runtime-enhancement-design.md` | `docs/codex/v1/plans/coin-recommendation-runtime-enhancement-plan.md` | `binance_day_contract_realtime_v5.py` |
| coin-recommendation-dashboard | 已完成 | `docs/codex/v1/requirements/coin-recommendation-dashboard-requirements.md` | `docs/codex/v1/designs/coin-recommendation-dashboard-design.md` | `docs/codex/v1/plans/coin-recommendation-dashboard-plan.md` | `binance_day_contract_realtime_v5.py` |
| multi-horizon-recommendation | 已完成 | `docs/codex/v1/requirements/multi-horizon-recommendation-requirements.md` | `docs/codex/v1/designs/multi-horizon-recommendation-design.md` | `docs/codex/v1/plans/multi-horizon-recommendation-plan.md` | `binance_day_contract_realtime_v5.py` |

## 进度与状态表

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| requirements | 已完成 | 已从现有 MA 金叉脚本抽取推荐系统目标、范围与完成标准。 |
| design | 已完成 | 已确定推荐分层、评分模型、输出结构与兼容接入方式。 |
| plan | 已完成 | 已拆分为模型扩展、推荐引擎接入、输出增强、验证同步四步。 |
| implementation | 已完成 | 已完成长线 1d / 中期 4h / 短期 1h 三类候选列表，并同步到 JSON、API 和 dashboard。 |
| trace | 未开始 | 本次未单独产出 trace 审查文档，可在后续迭代补充。 |

## 变更记录

- 2026-04-20：初始化 `coin-recommendation-system` 主题，补齐 requirements、design、plan，并进入实现阶段。
- 2026-04-20：完成推荐币子系统开发，新增推荐评分、推荐等级、推荐理由、风险摘要与 JSON 输出；本地运行成功。
- 2026-04-20：启动 `coin-recommendation-runtime-enhancement` 主题，继续增强运行参数可配置和历史结果沉淀。
- 2026-04-20：完成 `coin-recommendation-runtime-enhancement`，新增 CLI 参数、示例配置文件和 `outputs/history/` 历史快照输出。
- 2026-04-20：启动 `coin-recommendation-dashboard` 主题，继续增强每小时自动执行和 Web 可视化界面。
- 2026-04-20：完成 `coin-recommendation-dashboard`，新增本地服务脚本、每小时调度、手动触发接口和静态前端页面。
- 2026-04-21：启动 `multi-horizon-recommendation` 主题，规划并实现长/中/短三周期推荐候选列表。
- 2026-04-21：完成 `multi-horizon-recommendation`，输出长线/中期/短期三类候选列表，并支持 dashboard 切换展示。

- 2026-04-22：启动 `consistency-bonus` 主题，补充多时间框架一致性加分的 requirements/design/plan，并进入实现阶段。

- 2026-04-22??? `consistency-bonus`????????????????????? dashboard ?????30 ???????????????
