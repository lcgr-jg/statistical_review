"""Stress panels over known regime-transition windows."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import STRESS_WINDOWS
from engine.regime_analytics import summarize


def stress_panels(
    trades: pd.DataFrame,
    windows: dict | None = None,
) -> pd.DataFrame:
    """
    Restrict trades by entry_date falling inside each labeled stress window.
    Reports the same core metrics as the unconditional summary.
    """
    windows = windows or STRESS_WINDOWS
    if trades.empty:
        return pd.DataFrame()

    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    rows = []
    for name, (start, end) in windows.items():
        g = t[(t["entry_date"] >= start) & (t["entry_date"] <= end)]
        m = summarize(g["pnl"], g["pnl_net"]) if not g.empty else summarize(pd.Series(dtype=float))
        rows.append(
            {
                "window": name,
                "start": pd.Timestamp(start),
                "end": pd.Timestamp(end),
                **m.__dict__,
            }
        )
    return pd.DataFrame(rows)
