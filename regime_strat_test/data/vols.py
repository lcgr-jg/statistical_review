"""ATM implied vol history + realized vol for regime construction."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import ATM_IV_TICKERS, DEFAULT_END, IV_FIELD, VOL_START
from data.cache import cached_frame


def _pull_iv_series(
    ticker: str,
    start: datetime,
    end: datetime,
    on_server: bool,
    field: str = IV_FIELD,
) -> pd.Series:
    from bloomberg import BBGQuery
    bbg = BBGQuery(p_on_server=on_server)
    raw = bbg.fetch_hist(ticker, field, p_start=start, p_end=end, p_pd_datetime=True)
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    col = f"{ticker}_{field}"
    if col not in raw.columns:
        col = [c for c in raw.columns if field in c][0]
    s = pd.to_numeric(raw[col], errors="coerce")
    s.index = pd.to_datetime(raw.index)
    s.name = "iv"
    return s.sort_index()


def load_atm_iv(
    products: list[str] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    *,
    use_cache: bool = True,
    refresh: bool = False,
    on_server: bool = False,
) -> pd.DataFrame:
    """
    Wide DataFrame of ATM IV by product.
    Start defaults to VOL_START — listed energy IV is often thin before ~2015.
    """
    start = start or VOL_START
    end = end or DEFAULT_END
    products = products or list(ATM_IV_TICKERS.keys())
    frames = []
    for product in products:
        ticker = ATM_IV_TICKERS[product]
        key = f"iv_{product}_{start:%Y%m%d}_{end:%Y%m%d}_{IV_FIELD}"

        def _builder(t=ticker):
            return _pull_iv_series(t, start, end, on_server).to_frame()

        df = cached_frame(key, _builder, use_cache=use_cache, refresh=refresh)
        if df.empty:
            continue
        col = "iv" if "iv" in df.columns else df.columns[0]
        frames.append(df[[col]].rename(columns={col: product}))
    if not frames:
        return pd.DataFrame()
    out = frames[0]
    for f in frames[1:]:
        out = out.join(f, how="outer")
    return out.sort_index()


def realized_vol(prices: pd.Series, window: int = 20, annualization: int = 252) -> pd.Series:
    """Close-to-close realized vol from a price series."""
    rets = np.log(prices / prices.shift(1))
    return rets.rolling(window).std() * np.sqrt(annualization) * 100.0


def iv_percentile(iv: pd.Series, lookback: int = 252) -> pd.Series:
    """Rolling percentile rank of IV in [0, 1]."""
    def _rank(x):
        if len(x) < 5 or np.isnan(x.iloc[-1]):
            return np.nan
        return (x <= x.iloc[-1]).mean()

    return iv.rolling(lookback, min_periods=max(60, lookback // 4)).apply(_rank, raw=False)


def rv_iv_ratio(rv: pd.Series, iv: pd.Series) -> pd.Series:
    """RV / IV — >1 means realized running hot vs implied."""
    return rv / iv.replace(0, np.nan)
