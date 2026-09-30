"""
Walk-forward re-estimation of regime thresholds.

Avoids full-sample percentile look-ahead: cutoffs are fit on train windows
only, then applied to the subsequent test window's trades.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import WalkForwardConfig
from engine.regime_analytics import summarize


@dataclass
class WFFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    q_low: float
    q_high: float
    n_test_trades: int
    test_sharpe: float
    test_hit_rate: float
    test_avg_pnl: float


def _year_delta(ts: pd.Timestamp, years: int) -> pd.Timestamp:
    return ts + pd.DateOffset(years=years)


def walk_forward_thresholds(
    trades: pd.DataFrame,
    regime_series: pd.Series | None = None,
    cfg: WalkForwardConfig | None = None,
    q_low: float = 0.2,
    q_high: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parameters
    ----------
    trades : trade blotter with entry_date, pnl_net, regime_value
    regime_series : optional daily continuous regime (preferred for threshold fit).
                    If None, uses regime_value observed on trade entry dates in train.
    cfg : walk-forward windows

    Returns
    -------
    folds_df : one row per fold with OOS metrics
    oos_trades : test trades labeled with train-estimated regime buckets
    """
    cfg = cfg or WalkForwardConfig()
    if trades.empty:
        return pd.DataFrame(), pd.DataFrame()

    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    t = t.sort_values("entry_date")

    start = t["entry_date"].min()
    end = t["entry_date"].max()

    folds: list[WFFold] = []
    oos_parts: list[pd.DataFrame] = []

    train_start = start
    while True:
        train_end = _year_delta(train_start, cfg.train_years) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = _year_delta(test_start, cfg.test_years) - pd.Timedelta(days=1)
        if test_start > end:
            break

        # Fit thresholds on train regime distribution
        if regime_series is not None:
            rs = regime_series.copy()
            rs.index = pd.to_datetime(rs.index)
            train_reg = rs.loc[(rs.index >= train_start) & (rs.index <= train_end)].dropna()
        else:
            train_reg = t.loc[
                (t["entry_date"] >= train_start) & (t["entry_date"] <= train_end),
                "regime_value",
            ].dropna()

        # Daily regime series needs more history; trade-entry values use a lower floor
        min_obs = cfg.min_train_obs if regime_series is not None else max(20, cfg.min_train_obs // 3)
        if len(train_reg) < min_obs:
            train_start = _year_delta(train_start, cfg.step_years)
            continue

        lo = float(np.nanquantile(train_reg, q_low))
        hi = float(np.nanquantile(train_reg, q_high))

        test = t.loc[(t["entry_date"] >= test_start) & (t["entry_date"] <= test_end)].copy()
        if test.empty:
            train_start = _year_delta(train_start, cfg.step_years)
            continue

        def _bucket(v):
            if pd.isna(v):
                return "na"
            if v <= lo:
                return "low"
            if v >= hi:
                return "high"
            return "mid"

        test["wf_bucket"] = test["regime_value"].map(_bucket)
        m = summarize(test["pnl"], test["pnl_net"])
        folds.append(
            WFFold(
                train_start=pd.Timestamp(train_start),
                train_end=pd.Timestamp(train_end),
                test_start=pd.Timestamp(test_start),
                test_end=pd.Timestamp(min(test_end, end)),
                q_low=lo,
                q_high=hi,
                n_test_trades=m.n,
                test_sharpe=m.sharpe_net,
                test_hit_rate=m.hit_rate,
                test_avg_pnl=m.avg_pnl_net,
            )
        )
        oos_parts.append(test)
        train_start = _year_delta(train_start, cfg.step_years)

    folds_df = pd.DataFrame([f.__dict__ for f in folds])
    oos = pd.concat(oos_parts, ignore_index=True) if oos_parts else pd.DataFrame()
    return folds_df, oos


def oos_bucket_summary(oos_trades: pd.DataFrame) -> pd.DataFrame:
    if oos_trades.empty or "wf_bucket" not in oos_trades.columns:
        return pd.DataFrame()
    rows = []
    for b, g in oos_trades.groupby("wf_bucket"):
        m = summarize(g["pnl"], g["pnl_net"])
        rows.append({"wf_bucket": b, **m.__dict__})
    return pd.DataFrame(rows)
