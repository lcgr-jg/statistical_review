"""Contango % regime for cash-and-carry."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from data.curves import contango_pct
from regimes.base import RegimeSeries, RegimeVariable, label_by_expanding_quantile


class ContangoRegime(RegimeVariable):
    name = "contango_pct"

    def __init__(self, near: int = 1, deferred: int = 2, q_low: float = 0.2, q_high: float = 0.8):
        self.near = near
        self.deferred = deferred
        self.q_low = q_low
        self.q_high = q_high

    def compute(self, curve: pd.DataFrame) -> RegimeSeries:
        c = contango_pct(curve, self.near, self.deferred)
        c.name = self.name
        # high = rich contango (carry friendly); low = backwardation
        state = label_by_expanding_quantile(
            c,
            q_low=self.q_low,
            q_high=self.q_high,
            labels=("backwardation", "neutral", "contango"),
        )
        return RegimeSeries(continuous=c, state=state, name=self.name)
