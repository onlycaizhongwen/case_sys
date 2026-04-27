#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安合约交易智能分析系统 v5.0 - 推荐币子系统版
优化重点：在精确 MA7/MA10 金叉检测基础上，新增推荐评分、推荐分层和结构化输出。
"""

import argparse
import json
import logging
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("crypto_ma_cross_detector.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


@dataclass
class EnhancedMarketSignal:
    """精确 MA 交叉信号数据结构。"""

    symbol: str
    current_price: float
    market_change_24h: float
    strategy_key: str
    strategy_label: str
    timeframe: str
    ma7: float
    ma10: float
    ma20: float
    cross_day: int  # 金叉发生天数（0=今天，1=昨天，2=前天）
    cross_label: str
    cross_time: str
    cross_type: str
    live_cross_state: str
    live_gap_ratio: float
    trend_strength: float
    volatility_score: float
    volume_score: float
    rsi_position: float
    macd_signal: str
    support_level: float
    resistance_level: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float
    confidence_level: str
    market_view: str = "bullish"
    view_label: str = "看涨"
    recommendation: str = ""
    recommended_position: str = ""
    risk_level: str = ""
    base_recommendation_score: float = 0.0
    recommendation_score: float = 0.0
    recommendation_tier: str = ""
    recommendation_reasons: List[str] = field(default_factory=list)
    consistency_bonus: float = 0.0
    consistency_level: str = "single"
    matched_strategies: List[str] = field(default_factory=list)
    consistency_summary: str = ""
    risk_summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """导出为可序列化字典。"""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "market_change_24h": self.market_change_24h,
            "market_view": self.market_view,
            "view_label": self.view_label,
            "strategy_key": self.strategy_key,
            "strategy_label": self.strategy_label,
            "timeframe": self.timeframe,
            "ma7": self.ma7,
            "ma10": self.ma10,
            "ma20": self.ma20,
            "cross_day": self.cross_day,
            "cross_label": self.cross_label,
            "cross_time": self.cross_time,
            "cross_type": self.cross_type,
            "live_cross_state": self.live_cross_state,
            "live_gap_ratio": self.live_gap_ratio,
            "trend_strength": self.trend_strength,
            "volatility_score": self.volatility_score,
            "volume_score": self.volume_score,
            "rsi_position": self.rsi_position,
            "macd_signal": self.macd_signal,
            "support_level": self.support_level,
            "resistance_level": self.resistance_level,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "recommendation": self.recommendation,
            "recommended_position": self.recommended_position,
            "risk_level": self.risk_level,
            "base_recommendation_score": self.base_recommendation_score,
            "recommendation_score": self.recommendation_score,
            "recommendation_tier": self.recommendation_tier,
            "recommendation_reasons": self.recommendation_reasons,
            "consistency_bonus": self.consistency_bonus,
            "consistency_level": self.consistency_level,
            "matched_strategies": self.matched_strategies,
            "consistency_summary": self.consistency_summary,
            "risk_summary": self.risk_summary,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RecommendationConfig:
    """推荐系统配置。"""

    freshness_weight: float = 0.24
    trend_weight: float = 0.22
    confidence_weight: float = 0.22
    volume_weight: float = 0.12
    rsi_weight: float = 0.10
    change_weight: float = 0.10
    volatility_penalty_weight: float = 0.10
    strong_buy_threshold: float = 85.0
    watchlist_threshold: float = 72.0
    top_recommendation_limit: int = 10
    dual_timeframe_bonus: float = 4.0
    triple_timeframe_bonus: float = 8.0
    watchlist_alignment_bonus: float = 2.0
    long_mid_alignment_bonus: float = 1.0
    consistency_bonus_cap: float = 10.0


@dataclass
class StrategyConfig:
    """多周期策略配置。"""

    key: str
    label: str
    interval: str
    kline_limit: int
    cross_labels: List[str]


@dataclass
class RuntimeConfig:
    """脚本运行配置。"""

    candidate_limit: int = 200
    days: int = 30
    output_dir: str = "outputs/manual"
    write_history: bool = True
    history_dirname: str = "history"
    latest_report_name: str = "ma_cross_analysis_report.txt"
    latest_json_name: str = "coin_recommendations.json"
    request_pause_seconds: float = 0.15
    config_path: str = ""


@dataclass
class CoinRecommendation:
    """推荐结果实体。"""

    symbol: str
    score: float
    tier: str
    summary: str
    reasons: List[str]
    risk_summary: str
    position_hint: str
    signal: EnhancedMarketSignal

    def to_dict(self) -> Dict[str, Any]:
        """导出为可序列化字典。"""
        return {
            "symbol": self.symbol,
            "score": self.score,
            "base_score": self.signal.base_recommendation_score,
            "tier": self.tier,
            "summary": self.summary,
            "reasons": self.reasons,
            "risk_summary": self.risk_summary,
            "position_hint": self.position_hint,
            "consistency_bonus": self.signal.consistency_bonus,
            "consistency_level": self.signal.consistency_level,
            "matched_strategies": self.signal.matched_strategies,
            "consistency_summary": self.signal.consistency_summary,
            "signal": self.signal.to_dict(),
        }


def default_strategy_configs(runtime_config: Optional["RuntimeConfig"] = None) -> List[StrategyConfig]:
    """默认的长/中/短策略配置。"""
    base_limit = runtime_config.days if runtime_config else 30
    return [
        StrategyConfig(
            key="long_term",
            label="长线",
            interval="1d",
            kline_limit=base_limit,
            cross_labels=["今日实时", "昨日收盘", "前日收盘"],
        ),
        StrategyConfig(
            key="mid_term",
            label="中期",
            interval="4h",
            kline_limit=max(base_limit * 2, 60),
            cross_labels=["当前4小时实时", "上一根4小时收盘", "上二根4小时收盘"],
        ),
        StrategyConfig(
            key="short_term",
            label="短期",
            interval="1h",
            kline_limit=max(base_limit * 3, 72),
            cross_labels=["当前1小时实时", "上一根1小时收盘", "上二根1小时收盘"],
        ),
    ]


class PreciseMACrossAnalyzer:
    """精确 MA 交叉分析器。"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.api_key = api_key
        self.api_secret = api_secret
        self.min_volume_usdt = 1_000_000
        self._last_request_time = 0.0
        self._tradable_usdt_symbols: Optional[set[str]] = None

    def safe_request(
        self, url: str, params: Optional[dict] = None, max_retries: int = 3
    ) -> Optional[Any]:
        """安全请求函数，带重试和错误处理。"""
        for attempt in range(max_retries):
            try:
                time_since_last = time.time() - self._last_request_time
                if time_since_last < 0.2:
                    time.sleep(0.2 - time_since_last)

                response = requests.get(
                    url,
                    params=params,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                )
                self._last_request_time = time.time()

                if response.status_code == 200:
                    return response.json()
                if response.status_code == 429:
                    wait_time = min(2**attempt, 60)
                    logger.warning("API 频率限制，等待 %s 秒后重试", wait_time)
                    time.sleep(wait_time)
                    continue

                logger.warning("API 请求失败，状态码: %s", response.status_code)
                return None
            except Exception as exc:
                logger.error("请求异常: %s", exc)
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)
        return None

    def get_kline_data(
        self, symbol: str, interval: str = "1d", limit: int = 30
    ) -> Optional[pd.DataFrame]:
        """获取 K 线数据。"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "limit": limit + 1,
            }

            kline_data = self.safe_request(url, params)
            if not kline_data or len(kline_data) < limit:
                return None

            df = pd.DataFrame(
                kline_data,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_volume",
                    "trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )

            numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
            df["close_time"] = pd.to_numeric(df["close_time"], errors="coerce")
            df = df.dropna(subset=numeric_cols)
            if len(df) < 10:
                return None

            if len(df) < limit:
                return None

            df["is_closed"] = df["close_time"] <= int(time.time() * 1000)
            df = df.tail(limit + 1).copy()
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            return df
        except Exception as exc:
            logger.warning("获取 %s %s K 线数据失败: %s", symbol, interval, exc)
            return None

    def get_daily_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """兼容旧调用的日线数据入口。"""
        return self.get_kline_data(symbol, interval="1d", limit=days)

    def calculate_historical_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算历史移动平均线数据。"""
        df_ma = df.copy()
        df_ma["ma7"] = df_ma["close"].rolling(window=7).mean()
        df_ma["ma10"] = df_ma["close"].rolling(window=10).mean()
        df_ma["ma20"] = df_ma["close"].rolling(window=20).mean()
        if "is_closed" not in df_ma.columns:
            df_ma["is_closed"] = True
        return df_ma.dropna(subset=["ma7", "ma10"])

    def detect_ma7_ma10_cross(
        self,
        df_ma: pd.DataFrame,
        cross_labels: Optional[List[str]] = None,
        market_view: str = "bullish",
    ) -> Tuple[bool, int, str, str]:
        """
        精确检测 MA7 与 MA10 的交叉情况。
        返回: (是否发生金叉, 金叉发生的周期数, 交叉类型)
        """
        if len(df_ma) < 4:
            return False, 0, "数据不足", ""

        cross_labels = cross_labels or ["最近1个周期", "前1个周期", "前2个周期"]
        recent_data = df_ma.tail(6).reset_index(drop=True)
        closed_indices = [idx for idx, flag in enumerate(recent_data["is_closed"].tolist()) if bool(flag)]
        has_realtime_bar = bool(recent_data["is_closed"].tolist()) and not bool(recent_data["is_closed"].iloc[-1])

        candidate_pairs: List[Tuple[int, int, int]] = []
        if has_realtime_bar and closed_indices:
            candidate_pairs.append((0, closed_indices[-1], len(recent_data) - 1))

        if len(closed_indices) >= 2:
            candidate_pairs.append((1, closed_indices[-2], closed_indices[-1]))
        if len(closed_indices) >= 3:
            candidate_pairs.append((2, closed_indices[-3], closed_indices[-2]))

        for offset, prev_idx, curr_idx in candidate_pairs:
            prev_row = recent_data.iloc[prev_idx]
            curr_row = recent_data.iloc[curr_idx]
            if market_view == "bearish":
                cross_occurred = prev_row["ma7"] > prev_row["ma10"] and curr_row["ma7"] <= curr_row["ma10"]
                cross_type = "死叉"
            else:
                cross_occurred = prev_row["ma7"] < prev_row["ma10"] and curr_row["ma7"] >= curr_row["ma10"]
                cross_type = "金叉"
            if cross_occurred:
                logger.info(
                    "检测到 MA 金叉: %s, 前值 MA7=%.4f, 前值 MA10=%.4f, 当前 MA7=%.4f, 当前 MA10=%.4f",
                    cross_labels[offset],
                    prev_row["ma7"],
                    prev_row["ma10"],
                    curr_row["ma7"],
                    curr_row["ma10"],
                )
                cross_time = pd.to_datetime(curr_row["timestamp"]).strftime("%Y-%m-%d %H:%M")
                return True, offset, "金叉", cross_time

        return False, 0, "未检测到金叉", ""

    def check_ma_cross_conditions(
        self, current_price: float, df: pd.DataFrame, cross_labels: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """检查 MA 交叉条件。"""
        if df is None or len(df) < 10:
            return False, {}

        df_ma = self.calculate_historical_moving_averages(df)
        if len(df_ma) < 4:
            return False, {}

        has_realtime_bar = bool(df_ma["is_closed"].tolist()) and not bool(df_ma["is_closed"].iloc[-1])
        has_cross, days_ago, cross_type, cross_time = self.detect_ma7_ma10_cross(
            df_ma, cross_labels=cross_labels
        )
        if not has_cross:
            return False, {}

        latest_row = df_ma.iloc[-1]
        latest_ma7 = float(latest_row["ma7"])
        latest_ma10 = float(latest_row["ma10"])
        latest_gap_ratio = abs(latest_ma7 - latest_ma10) / latest_ma10 if latest_ma10 else 0.0

        # 对已在收盘线确认的历史金叉，要求最新实时均线关系仍然有效，
        # 避免出现“昨天金叉、今天实时又跌回 MA10 下方”却继续推荐的情况。
        if has_realtime_bar and days_ago > 0 and latest_ma7 < latest_ma10:
            logger.info(
                "忽略失效金叉: 最新实时 MA7=%.4f < MA10=%.4f，历史交叉时间=%s",
                latest_ma7,
                latest_ma10,
                cross_time,
            )
            return False, {}

        live_cross_state = "confirmed_close"
        if has_realtime_bar:
            if latest_gap_ratio <= 0.0015:
                live_cross_state = "weak_hold"
            elif latest_gap_ratio <= 0.004:
                live_cross_state = "normal_hold"
            else:
                live_cross_state = "strong_hold"

        reference_row = df_ma.iloc[-1]
        if days_ago > 0 and has_realtime_bar:
            reference_row = df_ma[df_ma["is_closed"]].iloc[-1]

        current_ma7 = float(reference_row["ma7"])
        current_ma10 = float(reference_row["ma10"])
        current_ma20 = float(reference_row["ma20"]) if not df_ma["ma20"].isna().all() else 0.0

        cross_info = {
            "has_golden_cross": True,
            "days_since_cross": days_ago,
            "cross_label": (cross_labels or ["最近1个周期", "前1个周期", "前2个周期"])[days_ago],
            "cross_time": cross_time,
            "cross_type": cross_type,
            "live_cross_state": live_cross_state,
            "live_gap_ratio": latest_gap_ratio,
            "current_ma7": current_ma7,
            "current_ma10": current_ma10,
            "current_ma20": current_ma20,
            "price_vs_ma7": current_price > current_ma7,
            "ma7_vs_ma10": current_ma7 > current_ma10,
            "cross_confirmed": days_ago > 0,
        }
        return True, cross_info

    def detect_ma7_ma10_death_cross(
        self, df_ma: pd.DataFrame, cross_labels: Optional[List[str]] = None
    ) -> Tuple[bool, int, str, str]:
        """Detect MA7 downward cross of MA10 within the recent 3 slots."""
        if len(df_ma) < 4:
            return False, 0, "数据不足", ""

        cross_labels = cross_labels or ["最近1个周期", "前1个周期", "前2个周期"]
        recent_data = df_ma.tail(6).reset_index(drop=True)
        closed_indices = [idx for idx, flag in enumerate(recent_data["is_closed"].tolist()) if bool(flag)]
        has_realtime_bar = bool(recent_data["is_closed"].tolist()) and not bool(recent_data["is_closed"].iloc[-1])

        candidate_pairs: List[Tuple[int, int, int]] = []
        if has_realtime_bar and closed_indices:
            candidate_pairs.append((0, closed_indices[-1], len(recent_data) - 1))
        if len(closed_indices) >= 2:
            candidate_pairs.append((1, closed_indices[-2], closed_indices[-1]))
        if len(closed_indices) >= 3:
            candidate_pairs.append((2, closed_indices[-3], closed_indices[-2]))

        for offset, prev_idx, curr_idx in candidate_pairs:
            prev_row = recent_data.iloc[prev_idx]
            curr_row = recent_data.iloc[curr_idx]
            death_cross_occurred = prev_row["ma7"] > prev_row["ma10"] and curr_row["ma7"] <= curr_row["ma10"]
            if death_cross_occurred:
                cross_time = pd.to_datetime(curr_row["timestamp"]).strftime("%Y-%m-%d %H:%M")
                return True, offset, "死叉", cross_time

        return False, 0, "未检测到死叉", ""

    def check_ma_death_cross_conditions(
        self, current_price: float, df: pd.DataFrame, cross_labels: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check bearish MA death-cross conditions."""
        if df is None or len(df) < 10:
            return False, {}

        df_ma = self.calculate_historical_moving_averages(df)
        if len(df_ma) < 4:
            return False, {}

        has_realtime_bar = bool(df_ma["is_closed"].tolist()) and not bool(df_ma["is_closed"].iloc[-1])
        has_cross, days_ago, cross_type, cross_time = self.detect_ma7_ma10_death_cross(
            df_ma, cross_labels=cross_labels
        )
        if not has_cross:
            return False, {}

        latest_row = df_ma.iloc[-1]
        latest_ma7 = float(latest_row["ma7"])
        latest_ma10 = float(latest_row["ma10"])
        latest_gap_ratio = abs(latest_ma7 - latest_ma10) / latest_ma10 if latest_ma10 else 0.0

        if has_realtime_bar and days_ago > 0 and latest_ma7 > latest_ma10:
            logger.info(
                "忽略失效死叉: 最新实时 MA7=%.4f > MA10=%.4f，历史交叉时间=%s",
                latest_ma7,
                latest_ma10,
                cross_time,
            )
            return False, {}

        live_cross_state = "confirmed_close"
        if has_realtime_bar:
            if latest_gap_ratio <= 0.0015:
                live_cross_state = "weak_hold"
            elif latest_gap_ratio <= 0.004:
                live_cross_state = "normal_hold"
            else:
                live_cross_state = "strong_hold"

        reference_row = df_ma.iloc[-1]
        if days_ago > 0 and has_realtime_bar:
            reference_row = df_ma[df_ma["is_closed"]].iloc[-1]

        current_ma7 = float(reference_row["ma7"])
        current_ma10 = float(reference_row["ma10"])
        current_ma20 = float(reference_row["ma20"]) if not df_ma["ma20"].isna().all() else 0.0

        return True, {
            "has_cross": True,
            "days_since_cross": days_ago,
            "cross_label": (cross_labels or ["最近1个周期", "前1个周期", "前2个周期"])[days_ago],
            "cross_time": cross_time,
            "cross_type": cross_type,
            "live_cross_state": live_cross_state,
            "live_gap_ratio": latest_gap_ratio,
            "current_ma7": current_ma7,
            "current_ma10": current_ma10,
            "current_ma20": current_ma20,
            "price_vs_ma7": current_price < current_ma7,
            "ma7_vs_ma10": current_ma7 < current_ma10,
            "cross_confirmed": days_ago > 0,
        }

    def get_top_coins_by_volume(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取交易量前 limit 的币种。"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            all_tickers = self.safe_request(url)
            if not all_tickers:
                return []

            usdt_pairs = [
                ticker
                for ticker in all_tickers
                if ticker["symbol"].endswith("USDT")
                and ticker["symbol"] in self.get_tradable_usdt_symbols()
                and float(ticker.get("quoteVolume", 0)) > self.min_volume_usdt
            ]
            usdt_pairs.sort(key=lambda item: float(item.get("quoteVolume", 0)), reverse=True)

            coins: List[Dict[str, Any]] = []
            selected_pairs = usdt_pairs if limit <= 0 else usdt_pairs[:limit]

            for ticker in selected_pairs:
                symbol = ticker["symbol"].replace("USDT", "")
                # 过滤稳定币及其衍生符号，避免进入推荐池。
                if symbol in {"USDT", "BUSD", "TUSD", "USDC", "DAI", "FDUSD"}:
                    continue
                if "USD" in symbol.upper():
                    continue

                price = float(ticker.get("lastPrice", 0))
                if price <= 0:
                    continue

                coins.append(
                    {
                        "symbol": symbol,
                        "price": price,
                        "change_24h": float(ticker.get("priceChangePercent", 0)),
                        "volume_24h": float(ticker.get("volume", 0)),
                        "quote_volume_24h": float(ticker.get("quoteVolume", 0)),
                        "data_fetch_time": datetime.now(),
                    }
                )

            logger.info("获取到 %s 个高交易量币种", len(coins))
            return coins
        except Exception as exc:
            logger.error("获取 Top 币种失败: %s", exc)
            return []

    def get_tradable_usdt_symbols(self) -> set[str]:
        """缓存并返回可交易的 U 本位 USDT 永续合约。"""
        if self._tradable_usdt_symbols is not None:
            return self._tradable_usdt_symbols

        url = f"{self.base_url}/exchangeInfo"
        payload = self.safe_request(url)
        if not payload:
            self._tradable_usdt_symbols = set()
            return self._tradable_usdt_symbols

        allowed_symbols = set()
        for item in payload.get("symbols", []):
            symbol = str(item.get("symbol", ""))
            if not symbol.endswith("USDT"):
                continue
            if item.get("status") != "TRADING":
                continue
            if item.get("contractType") != "PERPETUAL":
                continue
            if item.get("quoteAsset") != "USDT":
                continue
            allowed_symbols.add(symbol)

        self._tradable_usdt_symbols = allowed_symbols
        return self._tradable_usdt_symbols

    def analyze_coin_with_precise_cross(
        self,
        coin_data: Dict[str, Any],
        strategy_config: StrategyConfig,
    ) -> Optional[EnhancedMarketSignal]:
        """基于精确 MA 交叉分析单个币种。"""
        symbol = coin_data["symbol"]
        current_price = float(coin_data["price"])
        kline_data = self.get_kline_data(
            symbol,
            interval=strategy_config.interval,
            limit=strategy_config.kline_limit,
        )
        if kline_data is None or len(kline_data) < 10:
            return None

        valid_cross, cross_info = self.check_ma_cross_conditions(
            current_price,
            kline_data,
            cross_labels=strategy_config.cross_labels,
        )
        if not valid_cross:
            return None

        trend_strength = self.calculate_trend_strength(
            cross_info["current_ma7"],
            cross_info["current_ma10"],
            cross_info["current_ma20"],
        )

        signal = EnhancedMarketSignal(
            symbol=symbol,
            current_price=current_price,
            market_change_24h=float(coin_data.get("change_24h", 0.0)),
            strategy_key=strategy_config.key,
            strategy_label=strategy_config.label,
            timeframe=strategy_config.interval,
            ma7=cross_info["current_ma7"],
            ma10=cross_info["current_ma10"],
            ma20=cross_info["current_ma20"],
            cross_day=cross_info["days_since_cross"],
            cross_label=cross_info["cross_label"],
            cross_time=cross_info["cross_time"],
            cross_type=cross_info["cross_type"],
            live_cross_state=cross_info["live_cross_state"],
            live_gap_ratio=cross_info["live_gap_ratio"],
            trend_strength=trend_strength,
            volatility_score=self.calculate_volatility(kline_data),
            volume_score=float(coin_data.get("quote_volume_24h", 0.0)) / 1_000_000,
            rsi_position=self.calculate_rsi(kline_data),
            macd_signal="MA金叉突破",
            support_level=cross_info["current_ma7"],
            resistance_level=current_price * 1.08,
            stop_loss=cross_info["current_ma10"],
            take_profit=current_price * 1.15,
            risk_reward_ratio=3.0,
            confidence=self.calculate_confidence(cross_info, kline_data),
            confidence_level="高",
            recommendation=(
                f"{strategy_config.label}策略下 MA7 与 MA10 发生{cross_info['cross_type']}，趋势转强"
            ),
            recommended_position="1%-2%",
            risk_level="中等",
        )
        return signal

    def analyze_coin_with_precise_death_cross(
        self,
        coin_data: Dict[str, Any],
        strategy_config: StrategyConfig,
    ) -> Optional[EnhancedMarketSignal]:
        """Analyze bearish MA death-cross signal for one coin."""
        symbol = coin_data["symbol"]
        current_price = float(coin_data["price"])
        kline_data = self.get_kline_data(
            symbol,
            interval=strategy_config.interval,
            limit=strategy_config.kline_limit,
        )
        if kline_data is None or len(kline_data) < 10:
            return None

        valid_cross, cross_info = self.check_ma_death_cross_conditions(
            current_price,
            kline_data,
            cross_labels=strategy_config.cross_labels,
        )
        if not valid_cross:
            return None

        trend_strength = self.calculate_bearish_trend_strength(
            cross_info["current_ma7"],
            cross_info["current_ma10"],
            cross_info["current_ma20"],
        )

        signal = EnhancedMarketSignal(
            symbol=symbol,
            current_price=current_price,
            market_change_24h=float(coin_data.get("change_24h", 0.0)),
            market_view="bearish",
            view_label="看跌",
            strategy_key=strategy_config.key,
            strategy_label=strategy_config.label,
            timeframe=strategy_config.interval,
            ma7=cross_info["current_ma7"],
            ma10=cross_info["current_ma10"],
            ma20=cross_info["current_ma20"],
            cross_day=cross_info["days_since_cross"],
            cross_label=cross_info["cross_label"],
            cross_time=cross_info["cross_time"],
            cross_type=cross_info["cross_type"],
            live_cross_state=cross_info["live_cross_state"],
            live_gap_ratio=cross_info["live_gap_ratio"],
            trend_strength=trend_strength,
            volatility_score=self.calculate_volatility(kline_data),
            volume_score=float(coin_data.get("quote_volume_24h", 0.0)) / 1_000_000,
            rsi_position=self.calculate_rsi(kline_data),
            macd_signal="MA死叉转弱",
            support_level=current_price * 0.92,
            resistance_level=cross_info["current_ma10"],
            stop_loss=cross_info["current_ma10"],
            take_profit=current_price * 0.85,
            risk_reward_ratio=3.0,
            confidence=self.calculate_confidence(cross_info, kline_data),
            confidence_level="高",
            recommendation=(
                f"{strategy_config.label}策略下 MA7 与 MA10 发生{cross_info['cross_type']}，趋势转弱"
            ),
            recommended_position="1%-2%",
            risk_level="中等",
        )
        return signal

    def calculate_trend_strength(self, ma7: float, ma10: float, ma20: float) -> float:
        """计算趋势强度。"""
        if ma7 > ma10 > ma20:
            return 90.0
        if ma7 > ma10 and ma7 > ma20:
            return 75.0
        if ma7 > ma10:
            return 65.0
        return 40.0

    def calculate_bearish_trend_strength(self, ma7: float, ma10: float, ma20: float) -> float:
        """Calculate bearish trend strength."""
        if ma7 < ma10 < ma20:
            return 90.0
        if ma7 < ma10 and ma7 < ma20:
            return 75.0
        if ma7 < ma10:
            return 65.0
        return 40.0

    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """计算波动率评分。"""
        if len(df) < 10:
            return 50.0

        returns = df["close"].pct_change().dropna()
        volatility = returns.std() * np.sqrt(365)

        if volatility < 0.5:
            return 20.0 + (volatility / 0.5) * 30
        if volatility < 1.0:
            return 50.0 + ((volatility - 0.5) / 0.5) * 30
        return min(80.0, 50.0 + volatility * 10)

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 RSI 指标。"""
        if len(df) < period + 1:
            return 50.0

        close_prices = df["close"].values
        delta = np.diff(close_prices)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, np.abs(delta), 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_confidence(self, cross_info: Dict[str, Any], df: pd.DataFrame) -> float:
        """计算信号置信度。"""
        confidence = 70.0
        days_ago = cross_info["days_since_cross"]
        if days_ago == 0:
            confidence += 15
        elif days_ago == 1:
            confidence += 10
        elif days_ago == 2:
            confidence += 5

        if cross_info["price_vs_ma7"]:
            confidence += 5

        if len(df) > 0:
            recent_volume = df["volume"].tail(3).mean()
            avg_volume = df["volume"].mean()
            if recent_volume > avg_volume * 1.2:
                confidence += 5

        return min(confidence, 95.0)

class CoinRecommendationEngine:
    """Recommendation scoring engine."""

    def __init__(self, config: Optional[RecommendationConfig] = None):
        self.config = config or RecommendationConfig()

    def build_recommendations(
        self,
        signals: List[EnhancedMarketSignal],
        consistency_context: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[CoinRecommendation]:
        """Score, tier and sort signals."""
        recommendations: List[CoinRecommendation] = []
        for signal in signals:
            base_score = self.calculate_base_recommendation_score(signal)
            bonus_context = (consistency_context or {}).get(signal.symbol, {})
            consistency_bonus = self.calculate_consistency_bonus(bonus_context)
            total_score = round(self.clamp(base_score + consistency_bonus), 2)
            tier = self.classify_tier(total_score)

            signal.base_recommendation_score = round(base_score, 2)
            signal.consistency_bonus = round(consistency_bonus, 2)
            signal.consistency_level = bonus_context.get("consistency_level", "single")
            signal.matched_strategies = bonus_context.get("matched_strategy_labels", [])
            signal.consistency_summary = self.build_consistency_summary(signal, bonus_context)
            signal.recommendation_score = total_score
            signal.recommendation_tier = tier

            reasons = self.build_reasons(signal)
            risk_summary = self.build_risk_summary(signal)
            summary = self.build_summary(signal, tier, total_score)

            signal.recommendation_reasons = reasons
            signal.risk_summary = risk_summary
            signal.risk_level = self.classify_risk_level(signal)

            recommendations.append(
                CoinRecommendation(
                    symbol=signal.symbol,
                    score=total_score,
                    tier=tier,
                    summary=summary,
                    reasons=reasons,
                    risk_summary=risk_summary,
                    position_hint=signal.recommended_position,
                    signal=signal,
                )
            )

        recommendations.sort(key=lambda item: item.score, reverse=True)
        return recommendations

    def calculate_base_recommendation_score(self, signal: EnhancedMarketSignal) -> float:
        """Calculate score before consistency bonus."""
        freshness_score = self.get_freshness_score(signal.cross_day)
        trend_score = self.clamp(signal.trend_strength)
        confidence_score = self.clamp(signal.confidence)
        volume_score = self.normalize_volume_score(signal.volume_score)
        if signal.market_view == "bearish":
            rsi_score = self.calculate_bearish_rsi_score(signal.rsi_position)
            change_score = self.calculate_bearish_change_score(signal.market_change_24h)
        else:
            rsi_score = self.calculate_rsi_score(signal.rsi_position)
            change_score = self.calculate_change_score(signal.market_change_24h)
        volatility_penalty = self.calculate_volatility_penalty(signal.volatility_score)

        base_score = (
            freshness_score * self.config.freshness_weight
            + trend_score * self.config.trend_weight
            + confidence_score * self.config.confidence_weight
            + volume_score * self.config.volume_weight
            + rsi_score * self.config.rsi_weight
            + change_score * self.config.change_weight
        )
        total_score = base_score - volatility_penalty * self.config.volatility_penalty_weight

        if signal.live_cross_state == "weak_hold":
            total_score -= 6
        elif signal.live_cross_state == "normal_hold":
            total_score -= 2
        elif signal.live_cross_state == "strong_hold":
            total_score += 2

        return round(self.clamp(total_score), 2)

    def calculate_consistency_bonus(
        self, bonus_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate cross-timeframe consistency bonus."""
        context = bonus_context or {}
        strategy_count = int(context.get("strategy_count", 1))
        if strategy_count <= 1:
            return 0.0

        bonus = 0.0
        if strategy_count >= 3:
            bonus += self.config.triple_timeframe_bonus
        elif strategy_count == 2:
            bonus += self.config.dual_timeframe_bonus

        if int(context.get("watchlist_count", 0)) >= 2:
            bonus += self.config.watchlist_alignment_bonus

        matched_keys = set(context.get("matched_strategy_keys", []))
        if {"long_term", "mid_term"}.issubset(matched_keys):
            bonus += self.config.long_mid_alignment_bonus

        return round(min(bonus, self.config.consistency_bonus_cap), 2)

    def classify_tier(self, score: float) -> str:
        if score >= self.config.strong_buy_threshold:
            return "STRONG_BUY"
        if score >= self.config.watchlist_threshold:
            return "WATCHLIST"
        return "OBSERVE"

    def build_reasons(self, signal: EnhancedMarketSignal) -> List[str]:
        if signal.market_view == "bearish":
            return self.build_bearish_reasons(signal)

        reasons: List[str] = []
        if signal.cross_day == 0:
            reasons.append(f"{signal.cross_label}发生 MA7 上穿 MA10，属于最新事件触发")
        elif signal.cross_day == 1:
            reasons.append(f"{signal.cross_label}发生 MA7 上穿 MA10，趋势仍处于窗口期")
        else:
            reasons.append(f"{signal.cross_label}附近完成 MA 金叉，仍具备观察价值")

        if signal.live_cross_state == "weak_hold":
            reasons.append(
                f"最新实时仍站上 MA10，但仅高出 {signal.live_gap_ratio * 100:.2f}%，延续性偏弱"
            )
        elif signal.live_cross_state == "normal_hold":
            reasons.append(
                f"最新实时继续保持 MA7 在 MA10 上方，高出 {signal.live_gap_ratio * 100:.2f}%"
            )
        elif signal.live_cross_state == "strong_hold":
            reasons.append(
                f"最新实时保持强势站上 MA10，高出 {signal.live_gap_ratio * 100:.2f}%，趋势延续较好"
            )

        if signal.trend_strength >= 85:
            reasons.append("均线呈强势多头排列，趋势延续性较好")
        elif signal.trend_strength >= 70:
            reasons.append("短中期趋势偏强，具备继续走高基础")

        if signal.confidence >= 85:
            reasons.append("综合置信度较高，技术形态相对完整")

        if signal.volume_score >= 20:
            reasons.append("24h 成交额充足，流动性支持较好")
        elif signal.volume_score >= 8:
            reasons.append("成交量处于可接受区间，关注量价配合")

        if 48 <= signal.rsi_position <= 68:
            reasons.append("RSI 位于中强区间，尚未明显过热")
        elif signal.rsi_position > 75:
            reasons.append("价格动能很强，但短线已有偏热迹象")

        if signal.market_change_24h >= 3:
            reasons.append("24h 涨幅为正，短线资金偏向主动")

        if signal.consistency_summary:
            reasons.append(signal.consistency_summary)

        return reasons

    def build_risk_summary(self, signal: EnhancedMarketSignal) -> str:
        if signal.market_view == "bearish":
            return self.build_bearish_risk_summary(signal)

        risks: List[str] = []
        if signal.volatility_score >= 70:
            risks.append("波动率偏高")
        if signal.rsi_position >= 75:
            risks.append("RSI 偏热")
        elif signal.rsi_position <= 35:
            risks.append("RSI 偏弱")
        if signal.market_change_24h <= -3:
            risks.append("24h 跌幅承压")
        if signal.current_price <= signal.support_level * 1.01:
            risks.append("价格接近支撑，容易反复")

        if not risks:
            return "风险相对可控，适合结合止损位跟踪。"
        return "，".join(risks)

    def build_summary(self, signal: EnhancedMarketSignal, tier: str, score: float) -> str:
        if signal.market_view == "bearish":
            return self.build_bearish_summary(signal, tier, score)

        tier_label = {
            "STRONG_BUY": "强烈推荐",
            "WATCHLIST": "重点关注",
            "OBSERVE": "观察名单",
        }[tier]
        bonus_text = ""
        if signal.consistency_bonus > 0:
            bonus_text = f" | 一致性加分 +{signal.consistency_bonus:.1f}"
        live_text = ""
        if signal.live_cross_state == "weak_hold":
            live_text = f" | 当前仅小幅站上 {signal.live_gap_ratio * 100:.2f}%"
        elif signal.live_cross_state == "strong_hold":
            live_text = f" | 当前强势站上 {signal.live_gap_ratio * 100:.2f}%"
        return (
            f"{tier_label} | {signal.symbol} 在{signal.cross_label}({signal.cross_time})发生 {signal.strategy_label} MA7 上穿 MA10，"
            f"推荐分 {score:.2f}{bonus_text}{live_text}，当前价格 {signal.current_price:.4f}。"
        )

    def build_consistency_summary(
        self, signal: EnhancedMarketSignal, bonus_context: Optional[Dict[str, Any]] = None
    ) -> str:
        context = bonus_context or {}
        if signal.consistency_bonus <= 0:
            return ""

        strategy_labels = context.get("matched_strategy_labels", [])
        label_text = " / ".join(strategy_labels) if strategy_labels else signal.strategy_label
        return f"{label_text} 多周期共振，加分 +{signal.consistency_bonus:.1f}"

    def classify_risk_level(self, signal: EnhancedMarketSignal) -> str:
        if signal.market_view == "bearish":
            if signal.volatility_score >= 70 or signal.rsi_position <= 25:
                return "较高"
            if signal.volatility_score >= 55 or signal.rsi_position <= 35:
                return "中等"
            return "可控"
        if signal.volatility_score >= 70 or signal.rsi_position >= 75:
            return "较高"
        if signal.volatility_score >= 55 or signal.rsi_position >= 68:
            return "中等"
        return "可控"

    def build_bearish_reasons(self, signal: EnhancedMarketSignal) -> List[str]:
        reasons: List[str] = []
        if signal.cross_day == 0:
            reasons.append(f"{signal.cross_label}发生 MA7 下穿 MA10，属于最新空头触发")
        elif signal.cross_day == 1:
            reasons.append(f"{signal.cross_label}发生 MA7 下穿 MA10，空头仍处于窗口期")
        else:
            reasons.append(f"{signal.cross_label}附近完成 MA 死叉，仍具备观察价值")

        if signal.live_cross_state == "weak_hold":
            reasons.append(
                f"最新实时仍压在 MA10 下方，但仅低于 {signal.live_gap_ratio * 100:.2f}%，延续性偏弱"
            )
        elif signal.live_cross_state == "normal_hold":
            reasons.append(
                f"最新实时继续保持 MA7 在 MA10 下方，低于 {signal.live_gap_ratio * 100:.2f}%"
            )
        elif signal.live_cross_state == "strong_hold":
            reasons.append(
                f"最新实时保持强势压在 MA10 下方，低于 {signal.live_gap_ratio * 100:.2f}%，空头延续较好"
            )

        if signal.trend_strength >= 85:
            reasons.append("均线呈空头排列，弱势趋势延续性较好")
        elif signal.trend_strength >= 70:
            reasons.append("短中期转弱明显，具备继续回落基础")

        if signal.confidence >= 85:
            reasons.append("综合置信度较高，做空形态相对完整")

        if signal.volume_score >= 20:
            reasons.append("24h 成交额充足，空头流动性支持较好")
        elif signal.volume_score >= 8:
            reasons.append("成交量处于可接受区间，关注放量下行")

        if 32 <= signal.rsi_position <= 52:
            reasons.append("RSI 位于中弱区间，尚未明显超卖")
        elif signal.rsi_position < 25:
            reasons.append("RSI 已较弱，注意短线超卖反抽")

        if signal.market_change_24h <= -3:
            reasons.append("24h 跌幅为负，短线资金偏向空头")

        if signal.consistency_summary:
            reasons.append(signal.consistency_summary)

        return reasons

    def build_bearish_risk_summary(self, signal: EnhancedMarketSignal) -> str:
        risks: List[str] = []
        if signal.volatility_score >= 70:
            risks.append("波动率偏高")
        if signal.rsi_position <= 25:
            risks.append("RSI 偏低，易超卖反抽")
        elif signal.rsi_position >= 65:
            risks.append("RSI 回升，空头动能可能减弱")
        if signal.market_change_24h >= 3:
            risks.append("24h 涨幅承压，逆势做空风险增大")
        if signal.current_price >= signal.resistance_level * 0.99:
            risks.append("价格接近反压，需防止快速反抽")

        if not risks:
            return "风险相对可控，适合结合止损位跟踪。"
        return "，".join(risks)

    def build_bearish_summary(self, signal: EnhancedMarketSignal, tier: str, score: float) -> str:
        tier_label = {
            "STRONG_BUY": "强烈推荐",
            "WATCHLIST": "重点关注",
            "OBSERVE": "观察名单",
        }[tier]
        bonus_text = ""
        if signal.consistency_bonus > 0:
            bonus_text = f" | 一致性加分 +{signal.consistency_bonus:.1f}"
        live_text = ""
        if signal.live_cross_state == "weak_hold":
            live_text = f" | 当前仅小幅压下 {signal.live_gap_ratio * 100:.2f}%"
        elif signal.live_cross_state == "strong_hold":
            live_text = f" | 当前强势压下 {signal.live_gap_ratio * 100:.2f}%"
        return (
            f"{tier_label} | {signal.symbol} 在{signal.cross_label}({signal.cross_time})发生 "
            f"{signal.strategy_label} MA7 下穿 MA10，推荐分 {score:.2f}{bonus_text}{live_text}，"
            f"当前价格 {signal.current_price:.4f}。"
        )

    @staticmethod
    def calculate_bearish_rsi_score(rsi_position: float) -> float:
        ideal_center = 42.0
        distance = abs(rsi_position - ideal_center)
        return max(0.0, 100.0 - distance * 3)

    @staticmethod
    def calculate_bearish_change_score(change_24h: float) -> float:
        if change_24h <= -8:
            return 92.0
        if change_24h <= -4:
            return 82.0
        if change_24h <= 0:
            return 70.0
        if change_24h <= 3:
            return 55.0
        return 40.0

    @staticmethod
    def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def get_freshness_score(cross_day: int) -> float:
        return {0: 100.0, 1: 88.0, 2: 76.0}.get(cross_day, 60.0)

    @staticmethod
    def normalize_volume_score(volume_score: float) -> float:
        return min(100.0, max(0.0, volume_score * 4))

    @staticmethod
    def calculate_rsi_score(rsi_position: float) -> float:
        ideal_center = 58.0
        distance = abs(rsi_position - ideal_center)
        return max(0.0, 100.0 - distance * 3)

    @staticmethod
    def calculate_change_score(change_24h: float) -> float:
        if change_24h >= 8:
            return 92.0
        if change_24h >= 4:
            return 82.0
        if change_24h >= 0:
            return 70.0
        if change_24h >= -3:
            return 55.0
        return 40.0

    @staticmethod
    def calculate_volatility_penalty(volatility_score: float) -> float:
        return max(0.0, volatility_score - 45.0)


def build_consistency_context(
    strategy_results: Dict[str, Dict[str, Any]],
    recommendation_engine: CoinRecommendationEngine,
) -> Dict[str, Dict[str, Any]]:
    """Build symbol-level cross-timeframe consistency metadata."""
    symbol_context: Dict[str, Dict[str, Any]] = {}

    for strategy_key, result in strategy_results.items():
        for signal in result.get("analysis_results", []):
            base_score = recommendation_engine.calculate_base_recommendation_score(signal)
            base_tier = recommendation_engine.classify_tier(base_score)
            signal.base_recommendation_score = round(base_score, 2)

            context = symbol_context.setdefault(
                signal.symbol,
                {
                    "matched_strategy_keys": [],
                    "matched_strategy_labels": [],
                    "base_tiers": {},
                    "base_scores": {},
                },
            )
            context["matched_strategy_keys"].append(strategy_key)
            context["matched_strategy_labels"].append(signal.strategy_label)
            context["base_tiers"][strategy_key] = base_tier
            context["base_scores"][strategy_key] = round(base_score, 2)

    for context in symbol_context.values():
        context["matched_strategy_keys"] = list(dict.fromkeys(context["matched_strategy_keys"]))
        context["matched_strategy_labels"] = list(
            dict.fromkeys(context["matched_strategy_labels"])
        )
        context["strategy_count"] = len(context["matched_strategy_keys"])
        context["watchlist_count"] = sum(
            1 for tier in context["base_tiers"].values() if tier in {"WATCHLIST", "STRONG_BUY"}
        )
        if context["strategy_count"] >= 3:
            context["consistency_level"] = "triple"
        elif context["strategy_count"] == 2:
            context["consistency_level"] = "dual"
        else:
            context["consistency_level"] = "single"

    return symbol_context

def load_json_config(config_path: str) -> Dict[str, Any]:
    """读取 JSON 配置文件。"""
    if not config_path:
        return {}

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    with config_file.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def build_runtime_config(args: argparse.Namespace, config_data: Dict[str, Any]) -> RuntimeConfig:
    """按 默认值 < 配置文件 < CLI 的优先级构建运行配置。"""
    runtime = RuntimeConfig()
    runtime_data = config_data.get("runtime", {})

    for field_name in RuntimeConfig.__dataclass_fields__:
        if field_name in runtime_data:
            setattr(runtime, field_name, runtime_data[field_name])

    cli_mappings = {
        "candidate_limit": args.limit,
        "days": args.days,
        "output_dir": args.output_dir,
        "write_history": args.write_history,
        "history_dirname": args.history_dirname,
        "request_pause_seconds": args.pause,
    }
    for field_name, value in cli_mappings.items():
        if value is not None:
            setattr(runtime, field_name, value)

    if args.no_history:
        runtime.write_history = False
    if args.config:
        runtime.config_path = args.config

    return runtime


def build_recommendation_config(
    args: argparse.Namespace, config_data: Dict[str, Any]
) -> RecommendationConfig:
    """按 默认值 < 配置文件 < CLI 的优先级构建推荐配置。"""
    recommendation = RecommendationConfig()
    recommendation_data = config_data.get("recommendation", {})

    for field_name in RecommendationConfig.__dataclass_fields__:
        if field_name in recommendation_data:
            setattr(recommendation, field_name, recommendation_data[field_name])

    cli_mappings = {
        "strong_buy_threshold": args.strong_buy_threshold,
        "watchlist_threshold": args.watchlist_threshold,
        "top_recommendation_limit": args.top_n,
    }
    for field_name, value in cli_mappings.items():
        if value is not None:
            setattr(recommendation, field_name, value)

    return recommendation


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="币安推荐币子分析脚本")
    parser.add_argument("--config", help="JSON 配置文件路径")
    parser.add_argument(
        "--limit",
        type=int,
        help="候选币种数量上限，传 0 或负数表示不限制",
    )
    parser.add_argument("--days", type=int, help="日线数据获取天数")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--history-dirname", help="历史快照子目录名")
    parser.add_argument("--pause", type=float, help="每个币种分析后的暂停秒数")
    parser.add_argument("--top-n", type=int, help="控制台输出的推荐数量")
    parser.add_argument("--strong-buy-threshold", type=float, help="强烈推荐阈值")
    parser.add_argument("--watchlist-threshold", type=float, help="关注名单阈值")
    parser.add_argument(
        "--write-history",
        action="store_true",
        default=None,
        help="显式开启历史快照写入",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="关闭历史快照写入",
    )
    return parser.parse_args()


def prepare_output_paths(runtime_config: RuntimeConfig) -> Dict[str, Path]:
    """准备最新结果和历史结果路径。"""
    output_dir = Path(runtime_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_report = output_dir / runtime_config.latest_report_name
    latest_json = output_dir / runtime_config.latest_json_name

    paths: Dict[str, Path] = {
        "output_dir": output_dir,
        "latest_report": latest_report,
        "latest_json": latest_json,
    }

    if runtime_config.write_history:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_dir = output_dir / runtime_config.history_dirname / timestamp
        history_dir.mkdir(parents=True, exist_ok=True)
        paths["history_dir"] = history_dir
        paths["history_report"] = history_dir / runtime_config.latest_report_name
        paths["history_json"] = history_dir / runtime_config.latest_json_name

    return paths


def build_run_metadata(
    runtime_config: RuntimeConfig,
    recommendation_config: RecommendationConfig,
    strategy_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """构建本次运行元数据。"""
    return {
        "generated_at": datetime.now().isoformat(),
        "runtime": {
            "candidate_limit": runtime_config.candidate_limit,
            "days": runtime_config.days,
            "output_dir": runtime_config.output_dir,
            "write_history": runtime_config.write_history,
            "request_pause_seconds": runtime_config.request_pause_seconds,
            "config_path": runtime_config.config_path,
        },
        "recommendation": {
            "strong_buy_threshold": recommendation_config.strong_buy_threshold,
            "watchlist_threshold": recommendation_config.watchlist_threshold,
            "top_recommendation_limit": recommendation_config.top_recommendation_limit,
            "dual_timeframe_bonus": recommendation_config.dual_timeframe_bonus,
            "triple_timeframe_bonus": recommendation_config.triple_timeframe_bonus,
            "watchlist_alignment_bonus": recommendation_config.watchlist_alignment_bonus,
            "long_mid_alignment_bonus": recommendation_config.long_mid_alignment_bonus,
            "consistency_bonus_cap": recommendation_config.consistency_bonus_cap,
        },
        "summary": {
            "strategies": {
                key: {
                    "signal_count": value["signal_count"],
                    "recommendation_count": value["total"],
                    "label": value["strategy_label"],
                    "interval": value["interval"],
                }
                for key, value in strategy_results.items()
            }
        },
    }


def write_analysis_report(
    signals: List[EnhancedMarketSignal],
    recommendations: List[CoinRecommendation],
    filename: str = "ma_cross_analysis_report.txt",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """将分析结果写入 txt 报告。"""
    with open(filename, "w", encoding="utf-8") as report:
        report.write("=== 币安精确 MA 交叉分析与推荐报告 ===\n")
        report.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.write("=" * 70 + "\n\n")

        if metadata:
            runtime = metadata.get("runtime", {})
            recommendation_meta = metadata.get("recommendation", {})
            strategy_meta = metadata.get("summary", {}).get("strategies", {})
            report.write("运行参数\n")
            report.write(f"候选币种上限: {runtime.get('candidate_limit')}\n")
            report.write(f"K 线天数: {runtime.get('days')}\n")
            report.write(f"输出目录: {runtime.get('output_dir')}\n")
            report.write(
                f"推荐阈值: STRONG_BUY>={recommendation_meta.get('strong_buy_threshold')} | "
                f"WATCHLIST>={recommendation_meta.get('watchlist_threshold')}\n\n"
            )
            if strategy_meta:
                report.write("多周期摘要\n")
                for key in ("long_term", "mid_term", "short_term"):
                    if key in strategy_meta:
                        item = strategy_meta[key]
                        report.write(
                            f"- {item.get('label')} ({item.get('interval')}): "
                            f"信号 {item.get('signal_count')} 个, 推荐 {item.get('recommendation_count')} 个\n"
                        )
                report.write("\n")

        cross_day_count = {0: 0, 1: 0, 2: 0}
        for signal in signals:
            if signal.cross_day in cross_day_count:
                cross_day_count[signal.cross_day] += 1

        report.write("统计摘要\n")
        report.write(f"总发现信号: {len(signals)} 个\n")
        report.write(f"推荐结果数: {len(recommendations)} 个\n")
        report.write(f"今日金叉: {cross_day_count[0]} 个\n")
        report.write(f"昨日金叉: {cross_day_count[1]} 个\n")
        report.write(f"前日金叉: {cross_day_count[2]} 个\n")
        if signals:
            avg_trend = sum(item.trend_strength for item in signals) / len(signals)
            avg_confidence = sum(item.confidence for item in signals) / len(signals)
            report.write(f"平均趋势强度: {avg_trend:.1f}\n")
            report.write(f"平均置信度: {avg_confidence:.1f}%\n")
        report.write("\n")

        if recommendations:
            report.write("推荐币种 TOP 列表\n")
            report.write("-" * 60 + "\n")
            for index, recommendation in enumerate(recommendations, 1):
                signal = recommendation.signal
                report.write(
                    f"{index}. {recommendation.symbol} | {recommendation.tier} | "
                    f"推荐分 {recommendation.score:.2f}\n"
                )
                report.write(f"   摘要: {recommendation.summary}\n")
                report.write(f"   当前价格: ${signal.current_price:.4f}\n")
                report.write(
                    f"   MA7: ${signal.ma7:.4f} | MA10: ${signal.ma10:.4f} | "
                    f"MA20: ${signal.ma20:.4f}\n"
                )
                report.write(
                    f"   趋势强度: {signal.trend_strength:.1f} | "
                    f"置信度: {signal.confidence:.1f}% | "
                    f"24h 涨跌幅: {signal.market_change_24h:.2f}%\n"
                )
                report.write(
                    f"   风险等级: {signal.risk_level} | 风险摘要: {recommendation.risk_summary}\n"
                )
                report.write(f"   推荐理由: {'；'.join(recommendation.reasons)}\n")
                report.write(
                    f"   建议仓位: {recommendation.position_hint} | "
                    f"止损: ${signal.stop_loss:.4f} | 止盈: ${signal.take_profit:.4f}\n\n"
                )

        report.write("使用建议\n")
        report.write("-" * 60 + "\n")
        report.write("1. 优先关注 STRONG_BUY 等级币种，再观察 WATCHLIST。\n")
        report.write("2. 结合 MA10 止损位与仓位建议控制回撤。\n")
        report.write("3. 推荐分仅代表规则化排序，不代表收益保证。\n")
        report.write("4. 若出现高波动或 RSI 偏热，建议降低追高意愿。\n\n")

        report.write("风险提示\n")
        report.write("-" * 60 + "\n")
        report.write("此工具仅提供技术分析与推荐排序，不构成投资建议。\n")
        report.write("请结合基本面、流动性和自身风险承受能力综合判断。\n")

    print(f"分析报告已保存至: {filename}")


def write_recommendation_json(
    recommendations: List[CoinRecommendation],
    metadata: Optional[Dict[str, Any]] = None,
    strategy_results: Optional[Dict[str, Any]] = None,
    view_results: Optional[Dict[str, Any]] = None,
    default_view: str = "bullish",
    default_strategy: str = "long_term",
    filename: str = "coin_recommendations.json",
) -> None:
    """输出结构化推荐 JSON。"""
    payload = {
        "generated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "total": len(recommendations),
        "recommendations": [item.to_dict() for item in recommendations],
        "strategy_results": strategy_results or {},
        "view_results": view_results or {},
        "default_view": default_view,
        "default_strategy": default_strategy,
    }
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)
    print(f"推荐结果已保存至: {filename}")


def print_recommendation_summary(recommendations: List[CoinRecommendation], limit: int) -> None:
    """输出推荐摘要。"""
    if not recommendations:
        print("\n未生成推荐币列表，请检查市场是否存在符合条件的 MA 金叉币种。")
        return

    print("\n=== 推荐币种 TOP 列表 ===")
    for index, recommendation in enumerate(recommendations[:limit], 1):
        signal = recommendation.signal
        print(
            f"{index}. {recommendation.symbol} | {recommendation.tier} | "
            f"推荐分 {recommendation.score:.2f}"
        )
        print(f"   {recommendation.summary}")
        print(
            f"   趋势强度: {signal.trend_strength:.1f} | "
            f"置信度: {signal.confidence:.1f}% | "
            f"24h 涨跌幅: {signal.market_change_24h:.2f}%"
        )
        print(f"   推荐理由: {'；'.join(recommendation.reasons[:3])}")
        print(f"   风险摘要: {recommendation.risk_summary}")


def write_all_outputs(
    analysis_results: List[EnhancedMarketSignal],
    recommendations: List[CoinRecommendation],
    output_paths: Dict[str, Path],
    metadata: Dict[str, Any],
    strategy_payload: Optional[Dict[str, Any]] = None,
    view_payload: Optional[Dict[str, Any]] = None,
    default_view: str = "bullish",
    verbose: bool = True,
) -> None:
    """同时写最新结果和历史快照。"""
    write_analysis_report(
        analysis_results,
        recommendations,
        filename=str(output_paths["latest_report"]),
        metadata=metadata,
    )
    write_recommendation_json(
        recommendations,
        metadata=metadata,
        strategy_results=strategy_payload,
        view_results=view_payload,
        default_view=default_view,
        filename=str(output_paths["latest_json"]),
    )

    if "history_report" in output_paths and "history_json" in output_paths:
        write_analysis_report(
            analysis_results,
            recommendations,
            filename=str(output_paths["history_report"]),
            metadata=metadata,
        )
        write_recommendation_json(
            recommendations,
            metadata=metadata,
            strategy_results=strategy_payload,
            view_results=view_payload,
            default_view=default_view,
            filename=str(output_paths["history_json"]),
        )
        if verbose:
            print(f"历史快照已保存至: {output_paths['history_dir']}")


def execute_single_strategy(
    analyzer: PreciseMACrossAnalyzer,
    recommendation_engine: CoinRecommendationEngine,
    runtime_config: RuntimeConfig,
    strategy_config: StrategyConfig,
    coins: List[Dict[str, Any]],
    market_view: str = "bullish",
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行单个策略周期的一轮分析。"""
    analysis_results: List[EnhancedMarketSignal] = []

    if verbose:
        print(
            f"\n=== {strategy_config.label}策略分析中 "
            f"({strategy_config.interval}, 候选 {len(coins)} 个) ==="
        )

    for index, coin in enumerate(coins, 1):
        if verbose:
            print(
                f"[{strategy_config.label}] 分析进度: {index}/{len(coins)} - {coin['symbol']}"
            )

        if market_view == "bearish":
            signal = analyzer.analyze_coin_with_precise_death_cross(
                coin, strategy_config=strategy_config
            )
        else:
            signal = analyzer.analyze_coin_with_precise_cross(coin, strategy_config=strategy_config)
        if signal:
            analysis_results.append(signal)

        time.sleep(runtime_config.request_pause_seconds)

    analysis_results.sort(
        key=lambda item: (item.cross_day, -item.trend_strength, -item.confidence)
    )
    return {
        "market_view": market_view,
        "view_label": "看跌" if market_view == "bearish" else "看涨",
        "strategy_key": strategy_config.key,
        "strategy_label": strategy_config.label,
        "interval": strategy_config.interval,
        "signal_count": len(analysis_results),
        "analysis_results": analysis_results,
    }


def execute_analysis(
    runtime_config: RuntimeConfig,
    recommendation_config: RecommendationConfig,
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行一轮完整分析，供 CLI 与服务端复用。"""
    analyzer = PreciseMACrossAnalyzer()
    recommendation_engine = CoinRecommendationEngine(recommendation_config)
    output_paths = prepare_output_paths(runtime_config)
    strategy_configs = default_strategy_configs(runtime_config)

    if verbose:
        print("=== 币安精确 MA 交叉分析系统 v5.0 ===")
        print(
            f"开始分析前 {runtime_config.candidate_limit} 个币种，"
            "并生成长/中/短三类推荐币子列表..."
        )

    top_coins = analyzer.get_top_coins_by_volume(limit=runtime_config.candidate_limit)
    if verbose:
        print(f"获取到 {len(top_coins)} 个高交易量币种")

    view_results: Dict[str, Dict[str, Any]] = {}
    for market_view in ("bullish", "bearish"):
        current_results = {
            config.key: execute_single_strategy(
                analyzer,
                recommendation_engine,
                runtime_config,
                config,
                top_coins,
                market_view=market_view,
                verbose=verbose,
            )
            for config in strategy_configs
        }

        consistency_context = build_consistency_context(current_results, recommendation_engine)
        for value in current_results.values():
            recommendations = recommendation_engine.build_recommendations(
                value["analysis_results"],
                consistency_context=consistency_context,
            )
            value["recommendations"] = recommendations
            value["recommendation_payload"] = [item.to_dict() for item in recommendations]
            value["total"] = len(recommendations)

        view_results[market_view] = current_results

    strategy_results = view_results["bullish"]
    long_term_result = strategy_results["long_term"]
    analysis_results = long_term_result["analysis_results"]
    recommendations = long_term_result["recommendations"]

    if verbose:
        print("\n=== 多周期推荐摘要 ===")
        for key in ("long_term", "mid_term", "short_term"):
            result = strategy_results[key]
            print(
                f"{result['strategy_label']} ({result['interval']}): "
                f"信号 {result['signal_count']} 个, 推荐 {result['total']} 个"
            )

        print("\n=== 默认展示：长线推荐摘要 ===")
        print_recommendation_summary(
            recommendations,
            limit=recommendation_engine.config.top_recommendation_limit,
        )

    strategy_payload = {
        key: {
            "market_view": "bullish",
            "view_label": "看涨",
            "strategy_key": value["strategy_key"],
            "strategy_label": value["strategy_label"],
            "interval": value["interval"],
            "signal_count": value["signal_count"],
            "total": value["total"],
            "recommendations": value["recommendation_payload"],
        }
        for key, value in strategy_results.items()
    }

    view_payload = {
        market_view: {
            "view_label": "看跌" if market_view == "bearish" else "看涨",
            "strategy_results": {
                key: {
                    "market_view": market_view,
                    "view_label": "看跌" if market_view == "bearish" else "看涨",
                    "strategy_key": value["strategy_key"],
                    "strategy_label": value["strategy_label"],
                    "interval": value["interval"],
                    "signal_count": value["signal_count"],
                    "total": value["total"],
                    "recommendations": value["recommendation_payload"],
                }
                for key, value in results.items()
            },
        }
        for market_view, results in view_results.items()
    }

    metadata = build_run_metadata(runtime_config, recommendation_config, strategy_results)
    write_all_outputs(
        analysis_results,
        recommendations,
        output_paths,
        metadata,
        strategy_payload=strategy_payload,
        view_payload=view_payload,
        default_view="bullish",
        verbose=verbose,
    )

    if verbose:
        print(f"\n分析完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return {
        "analysis_results": analysis_results,
        "recommendations": recommendations,
        "strategy_results": strategy_results,
        "view_results": view_results,
        "metadata": metadata,
        "output_paths": {key: str(value) for key, value in output_paths.items()},
        "recommendation_payload": {
            "generated_at": metadata["generated_at"],
            "metadata": metadata,
            "total": len(recommendations),
            "recommendations": [item.to_dict() for item in recommendations],
            "strategy_results": strategy_payload,
            "view_results": view_payload,
            "default_view": "bullish",
            "default_strategy": "long_term",
        },
    }


def main() -> None:
    """主函数。"""
    args = parse_args()
    config_data = load_json_config(args.config) if args.config else {}
    runtime_config = build_runtime_config(args, config_data)
    recommendation_config = build_recommendation_config(args, config_data)
    execute_analysis(runtime_config, recommendation_config, verbose=True)


if __name__ == "__main__":
    main()
