"""Orchestrate data load → strategy.run → trade frame."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import BacktestConfig
from strategies.base import BaseStrategy, Trade


def load_market_data(cfg: BacktestConfig) -> dict[str, Any]:
    from data.curves import load_curves
    from data.inventory import load_inventory
    from data.vols import load_atm_iv

    curves = load_curves(
        cfg.complex,
        start=cfg.start,
        end=cfg.end,
        use_cache=cfg.use_cache,
        refresh=cfg.refresh_cache,
        on_server=cfg.on_server,
    )
    inv_products = [p for p in ("CL", "XB", "HO") if p in curves]
    inventory = load_inventory(
        inv_products or None,
        start=cfg.start,
        end=cfg.end,
        use_cache=cfg.use_cache,
        refresh=cfg.refresh_cache,
        on_server=cfg.on_server,
    )
    iv_products = [p for p in curves if p in ("CL", "CO", "XB", "HO", "QS")]
    iv = load_atm_iv(
        iv_products,
        start=max(cfg.start, cfg.vol_start),
        end=cfg.end,
        use_cache=cfg.use_cache,
        refresh=cfg.refresh_cache,
        on_server=cfg.on_server,
    )
    return {"curves": curves, "inventory": inventory, "iv": iv}


def trades_to_frame(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(
            columns=[
                "strategy",
                "entry_date",
                "exit_date",
                "direction",
                "entry_level",
                "exit_level",
                "pnl",
                "pnl_net",
                "cost",
                "regime_value",
                "regime_state",
            ]
        )
    rows = [t.__dict__ for t in trades]
    df = pd.DataFrame(rows)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["exit_date"] = pd.to_datetime(df["exit_date"])
    return df.drop(columns=["meta"], errors="ignore")


def run_strategy(strategy: BaseStrategy, data: dict[str, Any]) -> pd.DataFrame:
    return trades_to_frame(strategy.run(data))
