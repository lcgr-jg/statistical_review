"""Regime variable protocol — continuous signal + optional discrete state."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RegimeSeries:
    """Continuous regime input plus optional labeled buckets at each date."""
    continuous: pd.Series
    state: pd.Series | None = None  # categorical / string labels
    name: str = "regime"

    def aligned(self, index: pd.DatetimeIndex) -> "RegimeSeries":
        c = self.continuous.reindex(index).ffill()
        s = self.state.reindex(index).ffill() if self.state is not None else None
        return RegimeSeries(continuous=c, state=s, name=self.name)


class RegimeVariable(ABC):
    name: str = "regime"

    @abstractmethod
    def compute(self, *args, **kwargs) -> RegimeSeries:
        ...


def label_by_expanding_quantile(
    x: pd.Series,
    q_low: float = 0.2,
    q_high: float = 0.8,
    min_periods: int = 60,
    labels: tuple[str, str, str] = ("low", "mid", "high"),
) -> pd.Series:
    """
    Causal labels using expanding quantiles (no future peek).
    Prefer walk-forward re-estimation in engine.walk_forward for production cuts.
    """
    states: list[str] = []
    vals = x.astype(float)
    for i in range(len(vals)):
        hist = vals.iloc[: i + 1].dropna()
        v = vals.iloc[i]
        if len(hist) < min_periods or np.isnan(v):
            states.append("na")
            continue
        lo = hist.quantile(q_low)
        hi = hist.quantile(q_high)
        if v <= lo:
            states.append(labels[0])
        elif v >= hi:
            states.append(labels[2])
        else:
            states.append(labels[1])
    return pd.Series(states, index=x.index, name="state")


def label_by_fixed_thresholds(
    x: pd.Series,
    low: float,
    high: float,
    labels: tuple[str, str, str] = ("low", "mid", "high"),
) -> pd.Series:
    """Label using externally supplied thresholds (e.g. from walk-forward train)."""
    out = pd.Series(index=x.index, dtype=object)
    out[:] = "mid"
    out[x.isna()] = "na"
    out[x <= low] = labels[0]
    out[x >= high] = labels[2]
    out.name = "state"
    return out
