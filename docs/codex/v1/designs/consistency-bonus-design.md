# 多时间框架一致性加分设计
## 设计目标

在保持当前单周期评分结构稳定的前提下，为多周期共振币种追加一致性 bonus，并向输出层与前端同步这一信息。

## 方案概览

### 1. 评分模型分层

评分分为两层：

- 基础分：沿用当前 `freshness / trend / confidence / volume / rsi / change / volatility`
- 一致性 bonus：在基础分计算完成后追加

最终公式：

`final_score = clamp(base_score + consistency_bonus, 0, 100)`

### 2. 一致性上下文

在三套 `strategy_results` 全部生成后，按 `symbol` 汇总推荐入选情况，形成一致性上下文：

- `matched_strategies`
- `match_count`
- `watchlist_count`
- `strong_buy_count`
- `has_long_term`
- `has_mid_term`
- `has_short_term`

### 3. bonus 计算

默认策略：

- 双周期一致：`+4`
- 三周期一致：`+8`
- 两个及以上周期达到 `WATCHLIST`：`+2`
- 长线与中期同时成立：`+1`
- bonus 封顶：`10`

### 4. 数据模型扩展

`EnhancedMarketSignal` 增加：

- `base_recommendation_score`
- `consistency_bonus`
- `consistency_level`
- `matched_strategies`
- `consistency_summary`

`CoinRecommendation` 输出时同步带出：

- `base_score`
- `consistency_bonus`
- `consistency_level`
- `matched_strategies`
- `consistency_summary`

### 5. 执行流程调整

当前流程是每个周期独立生成推荐列表。扩展后改为：

1. 各周期先独立生成 `analysis_results`
2. 基于 `analysis_results` 计算各周期基础推荐列表
3. 汇总三周期推荐结果，构建一致性上下文
4. 对三套推荐结果统一执行 bonus 重算
5. 更新排序、tier、summary、reason 和输出 payload

### 6. 前端展示

推荐卡片增加一行轻量展示：

- 共振标签：如 `长线 + 中期`
- 一致性加分：如 `+5`

若无一致性 bonus，则不展示该区块。

## 兼容性

- 旧字段 `recommendations`、`strategy_results` 保持不删
- 新增字段为增量输出，旧消费者仍可继续读取旧结构
- 默认展示逻辑仍保持长线为主

## 风险与控制

### 风险

- 多周期 bonus 过大导致排行榜剧烈翻转
- 前端卡片信息过多影响可读性
- 当前脚本已有重复定义，若直接叠加易引入隐性覆盖

### 控制

- bonus 先采用保守参数并设置上限
- 前端仅加一行简短信息
- 实现前先清理重复函数与脏定义
