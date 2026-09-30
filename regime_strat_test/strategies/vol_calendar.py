"""
Vol calendar: sell rich near-term IV vs cheaper back-month proxy.

v1 mark-to-market: P&L ≈ -ΔIV_near + ΔIV_back (vol points), conditioned on
IV richness regime. This is a structure proxy, not a full option reval.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from regimes.iv_regime import IVRegime
from strategies.base import BaseStrategy


class VolCalendarStrategy(BaseStrategy):
    name = "vol_calendar"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regime_model = IVRegime()
        # vol point half-spread proxy (tune)
        self.half_spread = 0.25

    def prepare(self, data: dict[str, Any]):
        prices = data["curves"][self.product]["F1"]
        iv = data["iv"][self.product]
        # Back-month IV proxy: if only front IV available, use smoothed IV as "back"
        # When a second tenor column exists (e.g. product_back), use it.
        iv_back_key = f"{self.product}_back"
        if "iv" in data and iv_back_key in data["iv"].columns:
            iv_back = data["iv"][iv_back_key]
        else:
            # proxy: longer-horizon average as "deferred vol"
            iv_back = iv.rolling(60, min_periods=20).mean()

        # calendar vol spread: near - back (sell when rich)
        spread = -(iv - iv_back)
        spread.name = "vol_cal"
        regime = self.regime_model.compute(prices, iv)
        signal = (regime.state == "rich_vol").astype(int)
        return spread, regime, signal
