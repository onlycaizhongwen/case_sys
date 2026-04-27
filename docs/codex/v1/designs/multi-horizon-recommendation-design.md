# 多周期推荐设计

## 设计目标

在保持现有推荐逻辑稳定的前提下，把单周期分析改造成可配置的多周期策略执行器。

## 方案概览

### 1. 策略配置抽象

新增策略配置模型，定义：

- `strategy_key`
- `strategy_label`
- `interval`
- `lookback_limit`
- `cross_labels`

默认内置三套：

- `long_term` -> `1d`
- `mid_term` -> `4h`
- `short_term` -> `1h`

### 2. 分析器改造

- 把 `get_daily_data()` 抽象成通用 K 线获取函数。
- `analyze_coin_with_precise_cross()` 支持传入周期配置。
- 推荐结果中增加策略标识、周期标识、交叉描述。

### 3. 输出结构

原先只有单个 `recommendations` 列表，现在扩展为：

- `strategy_results.long_term`
- `strategy_results.mid_term`
- `strategy_results.short_term`

同时保留一个默认 `recommendations` 字段，指向长线结果，兼容旧消费者。

### 4. Dashboard 展示

- 页面增加策略切换控件。
- 推荐列表随当前选择的策略切换。
- 顶部统计跟随当前策略更新。

## 取舍

- 先复用同一套 MA 金叉判定逻辑，不做周期差异化规则。
- 先把长线作为默认兼容策略，减少对现有页面和接口消费者的冲击。
