"""
Breakout Strategy
=================
Enters when price breaks above/below a consolidation range with volume confirmation.

Entry Long:  Close above N-period high AND volume > 1.3x average
Entry Short: Close below N-period low AND volume > 1.3x average
Stop:        1.5 ATR from entry
Target:      3.0 ATR from entry (2:1 R:R)
Filter:      Bollinger Band width expanding (confirms end of squeeze)
"""
import pandas as pd
import numpy as np
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.base import BaseStrategy
from utils.risk import TradeSetup
from utils.indicators import (atr, bollinger_bands, donchian_channel,
                               volume_ratio, rsi, sma)
from config import BREAKOUT


class BreakoutStrategy(BaseStrategy):
    """Donchian channel breakout with volume and volatility filters."""

    def __init__(self, instrument: str = "ES", config=None):
        super().__init__(instrument, config)
        self.cfg = config or BREAKOUT

    @property
    def name(self):
        return "Breakout"

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = atr(df, self.cfg.atr_period)
        df = donchian_channel(df, self.cfg.lookback_period)
        df = bollinger_bands(df, self.cfg.bollinger_period, self.cfg.bollinger_std)
        df = volume_ratio(df, 20)
        df = rsi(df)
        df = sma(df, 50, name="sma_50")

        # Previous bar's channel (to avoid lookahead)
        df["prev_dc_upper"] = df["dc_upper"].shift(1)
        df["prev_dc_lower"] = df["dc_lower"].shift(1)

        # Bollinger squeeze detection: width percentile
        df["bb_width_pctile"] = df["bb_width"].rolling(100).rank(pct=True)

        return df

    def check_entry(self, df: pd.DataFrame, i: int) -> Optional[TradeSetup]:
        bar = df.iloc[i]
        prev = df.iloc[i - 1]

        # Skip if indicators not ready
        if pd.isna(bar["atr"]) or pd.isna(bar["prev_dc_upper"]) or bar["atr"] <= 0:
            return None

        # Volume filter: must be above average
        if bar["vol_ratio"] < self.cfg.volume_multiplier:
            return None

        atr_val = bar["atr"]

        # LONG BREAKOUT
        if self.cfg.require_close_above:
            long_break = bar["close"] > bar["prev_dc_upper"]
        else:
            long_break = bar["high"] > bar["prev_dc_upper"]

        if long_break and prev["close"] <= prev["dc_upper"]:
            # Confirm: Bollinger expanding (not in tight squeeze)
            if bar.get("bb_width_pctile", 0.5) < 0.2:
                return None  # Still in squeeze, wait for expansion

            entry = bar["close"]
            stop = entry - (atr_val * self.cfg.stop_atr_multiple)
            target = entry + (atr_val * self.cfg.target_atr_multiple)

            return TradeSetup(
                instrument=self.instrument,
                direction="long",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"Breakout above {bar['prev_dc_upper']:.2f}, vol_ratio={bar['vol_ratio']:.1f}",
            )

        # SHORT BREAKOUT
        if self.cfg.require_close_above:
            short_break = bar["close"] < bar["prev_dc_lower"]
        else:
            short_break = bar["low"] < bar["prev_dc_lower"]

        if short_break and prev["close"] >= prev["dc_lower"]:
            if bar.get("bb_width_pctile", 0.5) < 0.2:
                return None

            entry = bar["close"]
            stop = entry + (atr_val * self.cfg.stop_atr_multiple)
            target = entry - (atr_val * self.cfg.target_atr_multiple)

            return TradeSetup(
                instrument=self.instrument,
                direction="short",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                signal_bar_index=i,
                strategy=self.name,
                notes=f"Breakout below {bar['prev_dc_lower']:.2f}, vol_ratio={bar['vol_ratio']:.1f}",
            )

        return None
