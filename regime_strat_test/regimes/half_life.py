"""Ornstein–Uhlenbeck / AR(1) half-life of a spread for crack MR conditioning."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from regimes.base import RegimeSeries, RegimeVariable


def estimate_half_life(spread: pd.Series, min_obs: int = 40) -> float:
    """
    AR(1): x_t = a + b x_{t-1} + e.
    Half-life = -ln(2) / ln(b) for 0 < b < 1.
    Returns np.nan if not mean-reverting / insufficient data.
    """
    s = spread.dropna()
    if len(s) < min_obs:
        return np.nan
    x_lag = s.shift(1).iloc[1:]
    x = s.iloc[1:]
    # OLS via numpy
    X = np.column_stack([np.ones(len(x_lag)), x_lag.values])
    try:
        beta, _, _, _ = np.linalg.lstsq(X, x.values, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan
    b = beta[1]
    if not (0 < b < 1):
        return np.nan
    return float(-np.log(2) / np.log(b))


def rolling_half_life(spread: pd.Series, window: int = 126) -> pd.Series:
    vals = []
    for i in range(len(spread)):
        if i + 1 < window:
            vals.append(np.nan)
            continue
        vals.append(estimate_half_life(spread.iloc[i + 1 - window : i + 1]))
    return pd.Series(vals, index=spread.index, name="half_life")


class HalfLifeRegime(RegimeVariable):
    name = "half_life"

    def __init__(
        self,
        window: int = 126,
        hl_min: float = 5.0,
        hl_max: float = 60.0,
    ):
        self.window = window
        self.hl_min = hl_min
        self.hl_max = hl_max

    def compute(self, spread: pd.Series) -> RegimeSeries:
        hl = rolling_half_life(spread, window=self.window)
        # tradeable = mean-reverts fast enough but not noise
        state = hl.apply(
            lambda v: (
                "na" if pd.isna(v)
                else "tradeable" if self.hl_min <= v <= self.hl_max
                else "too_fast" if v < self.hl_min
                else "too_slow"
            )
        )
        state.name = "state"
        return RegimeSeries(continuous=hl, state=state, name=self.name)
