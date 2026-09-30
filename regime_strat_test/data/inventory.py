"""EIA inventory series + 5y seasonal z-scores (+ CSV fallback)."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import CURVE_START, DEFAULT_END, INVENTORY_TICKERS, MANUAL_INVENTORY_CSV, PRICE_FIELD
from data.cache import cached_frame


def _pull_inventory(
    ticker: str,
    start: datetime,
    end: datetime,
    on_server: bool,
) -> pd.Series:
    from bloomberg import BBGQuery
    bbg = BBGQuery(p_on_server=on_server)
    raw = bbg.fetch_hist(ticker, PRICE_FIELD, p_start=start, p_end=end, p_pd_datetime=True)
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    col = f"{ticker}_{PRICE_FIELD}"
    if col not in raw.columns:
        col = raw.columns[0]
    s = pd.to_numeric(raw[col], errors="coerce")
    s.index = pd.to_datetime(raw.index)
    s.name = "stocks"
    return s.sort_index().dropna()


def load_manual_inventory_csv(path: Path | None = None) -> pd.DataFrame:
    """
    Manual EIA dump. Expected columns: date + product codes (CL, XB, HO).
    Units arbitrary as long as consistent (z-score is scale-free).
    """
    path = path or MANUAL_INVENTORY_CSV
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce")


def load_inventory(
    products: list[str] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    *,
    use_cache: bool = True,
    refresh: bool = False,
    on_server: bool = False,
) -> pd.DataFrame:
    start = start or CURVE_START
    end = end or DEFAULT_END
    products = products or list(INVENTORY_TICKERS.keys())
    frames = []
    for product in products:
        ticker = INVENTORY_TICKERS[product]
        key = f"inv_{product}_{start:%Y%m%d}_{end:%Y%m%d}"

        def _builder(t=ticker):
            return _pull_inventory(t, start, end, on_server).to_frame()

        df = cached_frame(key, _builder, use_cache=use_cache, refresh=refresh)
        if df.empty:
            continue
        col = "stocks" if "stocks" in df.columns else df.columns[0]
        frames.append(df[[col]].rename(columns={col: product}))

    if not frames:
        manual = load_manual_inventory_csv()
        if not manual.empty:
            cols = [c for c in products if c in manual.columns]
            if cols:
                print(f"Using manual inventory CSV: {MANUAL_INVENTORY_CSV}")
                return manual[cols].loc[str(start.date()) : str(end.date())].ffill()
        return pd.DataFrame()

    out = frames[0]
    for f in frames[1:]:
        out = out.join(f, how="outer")
    return out.sort_index().ffill()


def inventory_zscore(
    stocks: pd.Series,
    years: int = 5,
    center: str = "mean",
) -> pd.Series:
    """Same-week-of-year z-score vs prior `years` seasons."""
    s = stocks.dropna().copy()
    s.index = pd.to_datetime(s.index)
    df = s.to_frame("v")
    df["woy"] = df.index.isocalendar().week.astype(int)
    df["year"] = df.index.year

    z = pd.Series(index=df.index, dtype=float)
    for ts, row in df.iterrows():
        hist = df[
            (df["woy"] == row["woy"])
            & (df["year"] < row["year"])
            & (df["year"] >= row["year"] - years)
        ]
        if len(hist) < 3:
            z.loc[ts] = np.nan
            continue
        loc = hist["v"].median() if center == "median" else hist["v"].mean()
        scale = hist["v"].std(ddof=1)
        z.loc[ts] = (row["v"] - loc) / scale if scale and scale > 0 else np.nan
    z.name = "inv_z"
    return z


def curve_tightness_proxy(curve: pd.DataFrame) -> pd.Series:
    """
    When EIA is unavailable: use negative contango % as a tightness proxy.
    High values ≈ backwardation ≈ economically similar to low inventories.
    """
    c = (curve["F2"] - curve["F1"]) / curve["F1"]
    return (-c).rename("tightness_proxy")
