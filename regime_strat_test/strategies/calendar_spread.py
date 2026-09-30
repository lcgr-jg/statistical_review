"""Calendar spread long (front − back) in low-inventory / backwardation regimes."""
from __future__ import annotations

from typing import Any

import pandas as pd

from data.curves import calendar_spread
from data.inventory import curve_tightness_proxy
from regimes.base import RegimeSeries, label_by_expanding_quantile
from regimes.inventory_z import InventoryZRegime
from strategies.base import BaseStrategy


class CalendarSpreadStrategy(BaseStrategy):
    name = "calendar_spread"

    def __init__(self, near: int = 1, deferred: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.near = near
        self.deferred = deferred
        self.regime_model = InventoryZRegime()

    def prepare(self, data: dict[str, Any]):
        curve = data["curves"][self.product]
        spread = calendar_spread(curve, self.near, self.deferred)
        spread.name = "cal_spread"

        inv = data.get("inventory")
        has_inv = (
            inv is not None
            and not getattr(inv, "empty", True)
            and self.product in inv.columns
        )
        if has_inv:
            regime = self.regime_model.compute(inv[self.product])
            signal = (regime.state == "low_inv").astype(int)
        else:
            # Fallback: trade when curve is in backwardation / tight (proxy)
            tightness = curve_tightness_proxy(curve)
            state = label_by_expanding_quantile(
                tightness, labels=("loose", "neutral", "tight")
            )
            regime = RegimeSeries(
                continuous=tightness,
                state=state,
                name="curve_tightness_proxy",
            )
            signal = (state == "tight").astype(int)

        return spread, regime, signal
