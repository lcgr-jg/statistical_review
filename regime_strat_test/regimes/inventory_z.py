"""Inventory z-score regime for calendar spreads."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from data.inventory import inventory_zscore
from regimes.base import RegimeSeries, RegimeVariable, label_by_expanding_quantile


class InventoryZRegime(RegimeVariable):
    name = "inventory_z"

    def __init__(self, years: int = 5, center: str = "mean", z_low: float = -0.5, z_high: float = 0.5):
        self.years = years
        self.center = center
        self.z_low = z_low
        self.z_high = z_high

    def compute(self, stocks: pd.Series) -> RegimeSeries:
        z = inventory_zscore(stocks, years=self.years, center=self.center)
        # low inventory → tight / backwardation-prone; high → contango-prone
        state = z.apply(
            lambda v: (
                "na" if pd.isna(v)
                else "low_inv" if v <= self.z_low
                else "high_inv" if v >= self.z_high
                else "neutral"
            )
        )
        state.name = "state"
        return RegimeSeries(continuous=z, state=state, name=self.name)

    def compute_quantile(self, stocks: pd.Series) -> RegimeSeries:
        z = inventory_zscore(stocks, years=self.years, center=self.center)
        state = label_by_expanding_quantile(
            z, labels=("low_inv", "neutral", "high_inv")
        )
        return RegimeSeries(continuous=z, state=state, name=self.name)
