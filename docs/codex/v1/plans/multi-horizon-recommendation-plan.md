# 多周期推荐计划

## 目标

实现长线（日线）、中期（4 小时）、短期（1 小时）三类候选列表，并在 dashboard 中展示。

## 实施步骤

1. 抽象周期策略配置与通用 K 线拉取逻辑。
2. 改造执行入口，分别跑三套周期分析。
3. 扩展 JSON / API 返回结构。
4. 改造前端页面展示三类候选列表。
5. 执行本地验证并同步状态。

## 验证方式

- `python -m py_compile binance_day_contract_realtime_v5.py coin_recommendation_dashboard.py`
- 运行主脚本，确认 JSON 中有三套策略结果。
- 启动 dashboard，确认接口和页面能读取三套列表。
