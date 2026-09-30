"""Cash-and-carry: long near / short deferred when contango is rich."""
from __future__ import annotations

from typing import Any

import pandas as pd

from data.curves import calendar_spread
from regimes.contango import ContangoRegime
from strategies.base import BaseStrategy


class CashAndCarryStrategy(BaseStrategy):
    """
    Canonical spread = F_deferred - F_near (carry spread).
    Signal +1 (long carry: short near / long deferred is the reverse of classic
    C&C storage; we define C&C as long near / short deferred in contango —
    i.e. short the contango / harvest roll if you believe curve is too steep...

    Desk definition used here (classic storage C&C):
      long near (or spot proxy), short deferred when contango is sufficiently rich.
    P&L unit: change in (F_near - F_deferred) = -change in contango spread.
    """

    name = "cash_and_carry"

    def __init__(self, near: int = 1, deferred: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.near = near
        self.deferred = deferred
        self.regime_model = ContangoRegime(near=near, deferred=deferred)

    def prepare(self, data: dict[str, Any]):
        curve = data["curves"][self.product]
        # long near / short deferred → P&L tracks (F_near - F_deferred)
        spread = -calendar_spread(curve, self.near, self.deferred)
        spread.name = "cnc_spread"
        regime = self.regime_model.compute(curve)
        # enter only in rich contango
        signal = (regime.state == "contango").astype(int)
        return spread, regime, signal
