# 多时间框架一致性加分计划
## 目标

实现多时间框架一致性加分，并同步到推荐输出与 dashboard 展示。

## 实施步骤

1. 清理 `binance_day_contract_realtime_v5.py` 中重复定义与脏片段，恢复单一有效实现路径。
2. 扩展数据模型与配置项，增加一致性字段与 bonus 参数。
3. 改造评分流程，先算基础分，再按多周期上下文叠加一致性 bonus。
4. 同步更新 JSON/API 输出结构。
5. 前端卡片增加一致性摘要与加分展示。
6. 运行脚本和 dashboard 接口进行验证。

## 验证方式

- `python -m py_compile binance_day_contract_realtime_v5.py coin_recommendation_dashboard.py`
- 运行主脚本，检查 `coin_recommendations.json` 中新增一致性字段
- 检查至少一个多周期共振币种存在 `consistency_bonus > 0`
- 检查单周期币种 `consistency_bonus = 0`
- 访问 dashboard，确认卡片能展示一致性说明

## 预期结果

- 多周期共振币种排名上升
- 单周期结果仍保持原有主评分特征
- 前后端对一致性 bonus 的展示一致
