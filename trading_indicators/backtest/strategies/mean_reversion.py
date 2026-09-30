"""
Mean Reversion Strategy
=======================
Trades price snapping back to mean after overextension.

Entry Long:  RSI < 30 AND price below lower Bollinger Band
             AND bullish rejection candle (long lower wick)
             AND NOT in strong downtrend (range-bound filter)
Entry Short: RSI > 70 AND price above upper Bollinger Band
             AND bearish rejection candle (long upper wick)
             AND NOT in strong uptrend
Stop:        1.5 ATR from entry
Target:      2.0 ATR (tighter than momentum — MR has lower R:R but higher win rate)
VWAP:        Use as secondary target / confluence zone
"""
import pandas as pd
import numpy as np
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.base import BaseStrategy
from utils.risk import TradeSetup
from utils.indicators import (atr, rsi, bollinger_bands, vwap, sma,
                               volume_ratio, rsi_divergence)
from config import MEAN_REVERSION


class MeanReversionStrategy(BaseStrategy):
    """Bollinger Band + RSI mean reversion with range-bound filter."""

    def __init__(self, instrument: str = "ES", config=None):
        super().__init__(instrument, config)
        self.cfg = config or MEAN_REVERSION

    @property
    def name(self):
        return "Mean Reversion"

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = atr(df, self.cfg.atr_period)
        df = rsi(df, self.cfg.rsi_period)
        df = bollinger_bands(df, self.cfg.bollinger_period, self.cfg.bollinger_std)
        df = vwap(df)
        df = sma(df, 50, name="sma_50")
        df = sma(df, 200, name="sma_200")
        df = volume_ratio(df, 20)
        df = rsi_divergence(df, lookback=10)

        # Range-bound detection: is the market trending or chopping?
        # Use ATR relative to recent price range
        df["range_high"] = df["high"].rolling(self.cfg.lookback_range).max()
        df["range_low"] = df["low"].rolling(self.cfg.lookback_range).min()
        df["range_width"] = (df["range_high"] - df["range_low"]) / df["close"]
        df["avg_range_width"] = df["range_width"].rolling(100).mean()
        df["is_ranging"] = df["range_width"] < df["avg_range_width"] * 1.5

        # Rejection candle detection
        body = (df["close"] - df["open"]).abs()
        upper_wick = df["high"] - df[["close", "open"]].max(axis=1)
        lower_wick = df[["close", "open"]].min(axis=1) - df["low"]
        total_range = df["high"] - df["low"]

        # Bullish rejection: long lower wick, small body, closes in upper half
        df["bullish_rejection"] = (
            (lower_wick > body * 1.5) &
            (df["close"] > (df["high"] + df["low"]) / 2) &
            (total_range > 0)
        )

        # Bearish rejection: long upper wick, small body, closes in lower half
        df["bearish_rejection"] = (
            (upper_wick > body * 1.5) &
            (df["close"] < (df["high"] + df["low"]) / 2) &
            (total_range > 0)
        )

        return df

    def check_entry(self, df: pd.DataFrame, i: int) -> Optional[TradeSetup]:
        bar = df.iloc[i]

        if pd.isna(bar["atr"]) or pd.isna(bar["rsi"]) or bar["atr"] <= 0:
            return None

        # CRITICAL FILTER: Only trade mean reversion in range-bound markets
        if not bar.get("is_ranging", False):
            return None

        atr_val = bar["atr"]

        # LONG MEAN REVERSION (oversold bounce)
        if bar["rsi"] < self.cfg.rsi_oversold and bar["close"] < bar["bb_lower"]:
            # Require rejection candle OR RSI divergence
            has_confirmation = False
            if self.cfg.require_rejection_candle:
                has_confirmation = bar.get("bullish_rejection", False)
            if bar.get("rsi_bull_divergence", False):
                has_confirmation = True
            if not has_confirmation:
                return None

            entry = bar["close"]
            stop = entry - (atr_val * self.cfg.stop_atr_multiple)
            # Target: middle Bollinger Band or VWAP, whichever is closer
            bb_target = bar["bb_mid"]
            vwap_target = bar.get("vwap", bb_target)
            target = min(bb_target, vwap_target) if not pd.isna(vwap_target) else bb_target
            # Ensure minimum R:R
            min_target = entry + (atr_val * self.cfg.target_atr_multiple)
            target = max(target, min_target)

            return TradeSetup(
                instrument=self.instrument,
                direction="long",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"MR long: RSI={bar['rsi']:.0f}, BB%={bar.get('bb_pct', 0):.2f}",
            )

        # SHORT MEAN REVERSION (overbought fade)
        if bar["rsi"] > self.cfg.rsi_overbought and bar["close"] > bar["bb_upper"]:
            has_confirmation = False
            if self.cfg.require_rejection_candle:
                has_confirmation = bar.get("bearish_rejection", False)
            if bar.get("rsi_bear_divergence", False):
                has_confirmation = True
            if not has_confirmation:
                return None

            entry = bar["close"]
            stop = entry + (atr_val * self.cfg.stop_atr_multiple)
            bb_target = bar["bb_mid"]
            vwap_target = bar.get("vwap", bb_target)
            target = max(bb_target, vwap_target) if not pd.isna(vwap_target) else bb_target
            max_target = entry - (atr_val * self.cfg.target_atr_multiple)
            target = min(target, max_target)

            return TradeSetup(
                instrument=self.instrument,
                direction="short",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"MR short: RSI={bar['rsi']:.0f}, BB%={bar.get('bb_pct', 0):.2f}",
            )

        return None
