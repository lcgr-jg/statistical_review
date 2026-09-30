"""IV percentile and RV/IV ratio regimes for vol calendar spreads."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from data.vols import iv_percentile, realized_vol, rv_iv_ratio
from regimes.base import RegimeSeries, RegimeVariable, label_by_expanding_quantile


class IVRegime(RegimeVariable):
    name = "iv_regime"

    def __init__(self, rv_window: int = 20, iv_lookback: int = 252, use_ratio: bool = True):
        self.rv_window = rv_window
        self.iv_lookback = iv_lookback
        self.use_ratio = use_ratio

    def compute(self, prices: pd.Series, iv: pd.Series) -> RegimeSeries:
        iv = iv.reindex(prices.index).ffill()
        pct = iv_percentile(iv, lookback=self.iv_lookback)
        if self.use_ratio:
            rv = realized_vol(prices, window=self.rv_window)
            # Combine: rich near vol when high IV %ile AND low RV/IV (implied rich)
            ratio = rv_iv_ratio(rv, iv)
            # continuous score: IV percentile minus normalized richness of IV vs RV
            # high score → sell near vol
            score = pct - (ratio - 1.0).clip(-1, 1) * 0.5
            score.name = "iv_richness"
            state = label_by_expanding_quantile(
                score, labels=("cheap_vol", "fair_vol", "rich_vol")
            )
            return RegimeSeries(continuous=score, state=state, name=self.name)

        state = label_by_expanding_quantile(
            pct, labels=("cheap_vol", "fair_vol", "rich_vol")
        )
        pct.name = "iv_pctile"
        return RegimeSeries(continuous=pct, state=state, name=self.name)
