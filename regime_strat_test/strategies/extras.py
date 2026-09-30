"""Additional desk-relevant strategies beyond the core five."""
from __future__ import annotations

from typing import Any

import pandas as pd

from data.curves import calendar_spread
from data.inventory import inventory_zscore
from regimes.base import RegimeSeries, label_by_expanding_quantile
from strategies.base import BaseStrategy


class SeasonalInventoryStrategy(BaseStrategy):
    """
    Fade curve vs seasonal inventory surprise:
    if stocks are low vs 5y seasonality but curve still contango → long calendar.
    """

    name = "seasonal_inventory"

    def prepare(self, data: dict[str, Any]):
        curve = data["curves"][self.product]
        inv = data["inventory"][self.product]
        spread = calendar_spread(curve, 1, 2)
        z = inventory_zscore(inv)
        contango = (curve["F2"] - curve["F1"]) / curve["F1"]
        # continuous regime: inventory surprise (negative z = tight)
        regime = RegimeSeries(
            continuous=z,
            state=label_by_expanding_quantile(z, labels=("low_inv", "neutral", "high_inv")),
            name="inv_surprise",
        )
        # long cal when tight stocks but still contango (mispriced curve)
        signal = ((z < -0.5) & (contango > 0)).astype(int)
        return spread, regime, signal


class CrackSkewStrategy(BaseStrategy):
    """
    RBOB vs HO relative value inside the crack complex.
    Long RBOB short HO (gal) when gasoline is cheap vs distillate on a z-score.
    Regime: overall crack half-life / level richness via crack z.
    """

    name = "crack_skew"

    def __init__(self, z_window: int = 60, z_entry: float = 1.0, **kwargs):
        super().__init__(product="XB", **kwargs)
        self.z_window = z_window
        self.z_entry = z_entry

    def prepare(self, data: dict[str, Any]):
        xb = data["curves"]["XB"]["F1"]
        ho = data["curves"]["HO"]["F1"]
        skew = xb - ho
        skew.name = "rbob_ho_skew"
        mu = skew.rolling(self.z_window).mean()
        sd = skew.rolling(self.z_window).std()
        z = (skew - mu) / sd.replace(0, pd.NA)
        regime = RegimeSeries(
            continuous=z,
            state=label_by_expanding_quantile(z, labels=("cheap_rbob", "fair", "rich_rbob")),
            name="skew_z",
        )
        signal = pd.Series(0, index=skew.index, dtype=int)
        signal[z < -self.z_entry] = 1
        signal[z > self.z_entry] = -1
        return skew, regime, signal
