# 推荐币子系统运行增强计划

## 目标

增强脚本的运行层能力，使其支持参数化运行和历史结果归档。

## 实施步骤

1. 新增运行配置模型与配置加载逻辑。
2. 新增命令行参数解析。
3. 改造报告和 JSON 输出路径，支持最新文件与历史快照双写。
4. 进行语法检查和一次带参数运行验证。

## 验证方式

- `python -m py_compile binance_day_contract_realtime_v5.py`
- `python binance_day_contract_realtime_v5.py --limit 30 --days 20`

## 风险

- 若实时接口慢，验证命令可能耗时较长，因此使用较小 `limit` 控制验证时间。
