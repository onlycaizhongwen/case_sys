# 推荐币子系统设计

## 背景与目标

基于现有 MA 金叉分析脚本，新增一层轻量推荐子系统，使脚本不仅能“找出近期金叉币”，还能“告诉用户哪些币更值得优先看、原因是什么、风险在哪里”。

## 设计范围

- 扩展原始信号模型，补充推荐层需要的评分输入。
- 新增推荐配置、推荐结果实体、推荐引擎。
- 接入现有分析与输出流程，保持单文件、低侵入、可直接运行。

## 方案概览

### 1. 数据模型扩展

- `EnhancedMarketSignal` 增加 `market_change_24h`、`recommendation_score`、`recommendation_tier`、`recommendation_reasons` 等字段。
- 新增 `RecommendationConfig`，集中定义各评分权重、等级阈值和输出数量。
- 新增 `CoinRecommendation`，承载推荐分数、等级、理由、风险摘要与对应原始信号。

### 2. 推荐引擎

新增 `CoinRecommendationEngine`，职责如下：

- 接收 `EnhancedMarketSignal` 列表。
- 按统一评分公式计算推荐总分。
- 输出推荐等级：
  - `STRONG_BUY`
  - `WATCHLIST`
  - `OBSERVE`
- 生成推荐理由和风险标签。
- 返回按分数排序后的推荐列表。

### 3. 评分公式

总分采用 100 分制的加权分，来源：

- 金叉新鲜度：越接近今天，得分越高。
- 趋势强度：复用现有 `trend_strength`。
- 置信度：复用现有 `confidence`。
- 成交量质量：对 `volume_score` 做归一化。
- RSI 位置：靠近中强区间加分，过热或过冷减分。
- 波动率惩罚：波动过高时拉低推荐分。

### 4. 输出增强

- 控制台增加“推荐币种 TOP 列表”。
- 文本报告新增推荐等级、推荐分数、推荐理由。
- 生成 `coin_recommendations.json`，提供结构化推荐结果。

## 模块流程

1. `get_top_coins_by_volume()` 获取候选币。
2. `analyze_coin_with_precise_cross()` 生成原始 MA 金叉信号。
3. `CoinRecommendationEngine.build_recommendations()` 对信号进行评分、分层、排序。
4. 主流程输出推荐摘要与完整报告。

## 数据结构

### RecommendationConfig

- `freshness_weight`
- `trend_weight`
- `confidence_weight`
- `volume_weight`
- `rsi_weight`
- `volatility_penalty_weight`
- `strong_buy_threshold`
- `watchlist_threshold`
- `top_recommendation_limit`

### CoinRecommendation

- `symbol`
- `score`
- `tier`
- `summary`
- `reasons`
- `risk_summary`
- `position_hint`
- `signal`

## 风险与取舍

1. 由于仍是单文件脚本，设计上选择低侵入扩展而不是大拆分，以控制本次实现成本。
2. 推荐分数不是回测收益指标，只是基于已有指标的规则化排序，需要在文档中明确风险边界。
3. 维持 MA 金叉为前置门槛，避免推荐系统与原脚本核心逻辑出现冲突。

## 待确认项

- 本次默认输出中文推荐语义和 JSON 文件名；后续若需服务化，再抽离为更稳定的接口结构。
