"""
Momentum Strategy
=================
Trades in the direction of the prevailing trend using EMA crossovers
confirmed by RSI and MACD.

Entry Long:  Fast EMA > Slow EMA AND RSI > 55 AND MACD histogram positive
Entry Short: Fast EMA < Slow EMA AND RSI < 45 AND MACD histogram negative
Trend Filter: Price above 50-period SMA for longs, below for shorts
Stop:         2.0 ATR from entry
Target:       4.0 ATR from entry
Trailing:     Move stop to breakeven after 1R profit
"""
import pandas as pd
import numpy as np
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.base import BaseStrategy
from utils.risk import TradeSetup, SizedTrade
from utils.indicators import (atr, rsi, ema, sma, macd, rate_of_change,
                               volume_ratio)
from config import MOMENTUM


class MomentumStrategy(BaseStrategy):
    """EMA crossover momentum with RSI/MACD confirmation and trailing stop."""

    def __init__(self, instrument: str = "ES", config=None):
        super().__init__(instrument, config)
        self.cfg = config or MOMENTUM
        self._trailing_stop = None

    @property
    def name(self):
        return "Momentum"

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = atr(df, self.cfg.atr_period)
        df = rsi(df, self.cfg.rsi_period)
        df = ema(df, self.cfg.fast_ema, name="ema_fast")
        df = ema(df, self.cfg.slow_ema, name="ema_slow")
        df = sma(df, self.cfg.trend_ma_period, name="trend_ma")
        df = macd(df, self.cfg.macd_fast, self.cfg.macd_slow, self.cfg.macd_signal)
        df = rate_of_change(df, self.cfg.roc_period)
        df = volume_ratio(df, 20)

        # EMA crossover signals
        df["ema_cross_up"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        df["ema_cross_down"] = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

        # Trend state
        df["uptrend"] = df["ema_fast"] > df["ema_slow"]
        df["above_trend_ma"] = df["close"] > df["trend_ma"]

        return df

    def check_entry(self, df: pd.DataFrame, i: int) -> Optional[TradeSetup]:
        bar = df.iloc[i]

        if pd.isna(bar["atr"]) or pd.isna(bar["rsi"]) or bar["atr"] <= 0:
            return None

        atr_val = bar["atr"]

        # LONG MOMENTUM
        if (bar["ema_cross_up"] or bar["uptrend"]) and \
           bar["rsi"] > self.cfg.rsi_trend_threshold and \
           bar["macd_hist"] > 0 and \
           bar["above_trend_ma"]:

            # Only enter on crossover or strong momentum acceleration
            if not bar["ema_cross_up"] and bar["roc"] < 0:
                return None

            entry = bar["close"]
            stop = entry - (atr_val * self.cfg.stop_atr_multiple)
            target = entry + (atr_val * self.cfg.target_atr_multiple)

            self._trailing_stop = stop

            return TradeSetup(
                instrument=self.instrument,
                direction="long",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"Momentum long: RSI={bar['rsi']:.0f}, MACD_H={bar['macd_hist']:.2f}",
            )

        # SHORT MOMENTUM
        if (bar["ema_cross_down"] or not bar["uptrend"]) and \
           bar["rsi"] < self.cfg.rsi_trend_threshold_short and \
           bar["macd_hist"] < 0 and \
           not bar["above_trend_ma"]:

            if not bar["ema_cross_down"] and bar["roc"] > 0:
                return None

            entry = bar["close"]
            stop = entry + (atr_val * self.cfg.stop_atr_multiple)
            target = entry - (atr_val * self.cfg.target_atr_multiple)

            self._trailing_stop = stop

            return TradeSetup(
                instrument=self.instrument,
                direction="short",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"Momentum short: RSI={bar['rsi']:.0f}, MACD_H={bar['macd_hist']:.2f}",
            )

        return None

    def check_exit(self, df: pd.DataFrame, i: int,
                   trade: SizedTrade) -> Optional[tuple[float, str]]:
        """Enhanced exit with trailing stop: move to breakeven after 1R."""
        bar = df.iloc[i]
        atr_val = bar.get("atr", 0)

        if trade.direction == "long":
            # Update trailing stop: move to breakeven after 1R profit
            current_profit = bar["high"] - trade.entry_price
            initial_risk = trade.entry_price - trade.stop_price
            if initial_risk > 0 and current_profit >= initial_risk:
                new_stop = max(self._trailing_stop, trade.entry_price)
                # Trail behind by 1 ATR once in profit
                atr_trail = bar["close"] - atr_val if atr_val > 0 else new_stop
                new_stop = max(new_stop, atr_trail)
                self._trailing_stop = new_stop

            if bar["low"] <= self._trailing_stop:
                return (max(self._trailing_stop, bar["low"]), "trailing_stop")
            if bar["high"] >= trade.target_price:
                return (trade.target_price, "target")

        elif trade.direction == "short":
            current_profit = trade.entry_price - bar["low"]
            initial_risk = trade.stop_price - trade.entry_price
            if initial_risk > 0 and current_profit >= initial_risk:
                new_stop = min(self._trailing_stop, trade.entry_price)
                atr_trail = bar["close"] + atr_val if atr_val > 0 else new_stop
                new_stop = min(new_stop, atr_trail)
                self._trailing_stop = new_stop

            if bar["high"] >= self._trailing_stop:
                return (min(self._trailing_stop, bar["high"]), "trailing_stop")
            if bar["low"] <= trade.target_price:
                return (trade.target_price, "target")

        # Exit on momentum reversal (EMA cross against position)
        if trade.direction == "long" and bar.get("ema_cross_down", False):
            return (bar["close"], "signal_reversal")
        if trade.direction == "short" and bar.get("ema_cross_up", False):
            return (bar["close"], "signal_reversal")

        return None
