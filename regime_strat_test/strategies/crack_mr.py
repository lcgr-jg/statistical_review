"""Crack spread mean reversion conditioned on half-life."""
from __future__ import annotations

from typing import Any

import pandas as pd

from data.curves import crack_321, crack_brent_gasoil
from regimes.half_life import HalfLifeRegime
from strategies.base import BaseStrategy


class CrackMeanReversionStrategy(BaseStrategy):
    name = "crack_mr"

    def __init__(
        self,
        z_entry: float = 1.25,
        z_window: int = 60,
        complex_name: str = "US",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.z_entry = z_entry
        self.z_window = z_window
        self.complex_name = complex_name
        self.regime_model = HalfLifeRegime()

    def prepare(self, data: dict[str, Any]):
        curves = data["curves"]
        if self.complex_name == "US":
            spread = crack_321(curves["CL"], curves["XB"], curves["HO"])
            self.product = "CL"
        else:
            spread = crack_brent_gasoil(curves["CO"], curves["QS"])
            self.product = "CO"
        spread.name = "crack"

        regime = self.regime_model.compute(spread)
        mu = spread.rolling(self.z_window).mean()
        sd = spread.rolling(self.z_window).std()
        z = (spread - mu) / sd.replace(0, pd.NA)

        # fade rich/cheap crack only when half-life is in tradeable band
        tradeable = regime.state == "tradeable"
        signal = pd.Series(0, index=spread.index, dtype=int)
        signal[(z > self.z_entry) & tradeable] = -1
        signal[(z < -self.z_entry) & tradeable] = 1
        return spread, regime, signal
