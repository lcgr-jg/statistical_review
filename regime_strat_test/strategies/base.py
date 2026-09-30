"""Strategy interface: signals + trade construction with half-spread costs."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import HALF_SPREAD, HoldingConfig, HoldingMode
from regimes.base import RegimeSeries


@dataclass
class Trade:
    strategy: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: int  # +1 / -1 on the strategy's canonical spread
    entry_level: float
    exit_level: float
    pnl: float
    pnl_net: float
    cost: float
    regime_value: float
    regime_state: str
    meta: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    name: str = "base"

    def __init__(self, holding: HoldingConfig | None = None, product: str = "CL"):
        self.holding = holding or HoldingConfig()
        self.product = product
        self.half_spread = HALF_SPREAD.get(product, 0.01)

    @abstractmethod
    def prepare(self, data: dict[str, Any]) -> tuple[pd.Series, RegimeSeries, pd.Series]:
        """
        Returns
        -------
        spread : levels used for P&L (strategy unit)
        regime : RegimeSeries at each date
        signal : -1 / 0 / +1 desired position in the spread
        """

    def run(self, data: dict[str, Any]) -> list[Trade]:
        spread, regime, signal = self.prepare(data)
        idx = spread.dropna().index.intersection(signal.dropna().index)
        spread = spread.reindex(idx)
        signal = signal.reindex(idx).fillna(0).astype(int)
        regime = regime.aligned(idx)

        trades: list[Trade] = []
        i = 0
        n = len(idx)
        while i < n:
            sig = int(signal.iloc[i])
            if sig == 0:
                i += 1
                continue
            entry_i = i
            exit_i = self._resolve_exit_index(i, signal, regime)
            if exit_i <= entry_i:
                i += 1
                continue

            entry_level = float(spread.iloc[entry_i])
            exit_level = float(spread.iloc[exit_i])
            # direction: +1 means long the canonical spread (e.g. long F1-F2)
            gross = sig * (exit_level - entry_level)
            # half-spread on entry and exit (round-trip = full bid-ask once)
            cost = 2.0 * self.half_spread
            trades.append(
                Trade(
                    strategy=self.name,
                    entry_date=idx[entry_i],
                    exit_date=idx[exit_i],
                    direction=sig,
                    entry_level=entry_level,
                    exit_level=exit_level,
                    pnl=gross,
                    pnl_net=gross - cost,
                    cost=cost,
                    regime_value=float(regime.continuous.iloc[entry_i])
                    if not pd.isna(regime.continuous.iloc[entry_i])
                    else np.nan,
                    regime_state=str(regime.state.iloc[entry_i])
                    if regime.state is not None
                    else "na",
                )
            )
            i = exit_i + 1
        return trades

    def _resolve_exit_index(
        self,
        entry_i: int,
        signal: pd.Series,
        regime: RegimeSeries,
    ) -> int:
        n = len(signal)
        mode = self.holding.mode
        if mode == HoldingMode.FIXED_DAYS:
            return min(entry_i + self.holding.hold_days, n - 1)
        if mode == HoldingMode.WEEKLY:
            # ~5 business days
            return min(entry_i + 5, n - 1)
        if mode == HoldingMode.REGIME_EXIT:
            # flatten when signal flips or goes flat
            for j in range(entry_i + 1, n):
                if int(signal.iloc[j]) != int(signal.iloc[entry_i]):
                    return j
            return n - 1
        return min(entry_i + self.holding.hold_days, n - 1)
