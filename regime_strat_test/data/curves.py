"""Historical futures curve pulls via Bloomberg, cached to parquet."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import (
    CURVE_START,
    DEFAULT_END,
    ICE_CURVE,
    PRICE_FIELD,
    US_CURVE,
)
from data.cache import cached_frame


def _bbg(on_server: bool):
    from bloomberg import BBGQuery
    return BBGQuery(p_on_server=on_server)


def _clean_hist(raw: pd.DataFrame, tickers: list[str], field: str) -> pd.DataFrame:
    """Normalize BBGQuery.fetch_hist wide columns to tenor labels F1..Fn."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=pd.to_datetime(raw.index))
    for i, tkr in enumerate(tickers, start=1):
        col = f"{tkr}_{field}"
        if col in raw.columns:
            out[f"F{i}"] = pd.to_numeric(raw[col], errors="coerce")
        else:
            # single-ticker pulls sometimes drop the ticker prefix inconsistently
            candidates = [c for c in raw.columns if field in c and tkr.split()[0] in c]
            out[f"F{i}"] = pd.to_numeric(raw[candidates[0]], errors="coerce") if candidates else pd.NA
    out.index = pd.to_datetime(out.index)
    out.index.name = "date"
    return out.sort_index().dropna(how="all")


def _pull_product_curve(
    product: str,
    tickers: list[str],
    start: datetime,
    end: datetime,
    on_server: bool,
) -> pd.DataFrame:
    bbg = _bbg(on_server)
    raw = bbg.fetch_hist(
        tickers,
        PRICE_FIELD,
        p_start=start,
        p_end=end,
        p_pd_datetime=True,
    )
    return _clean_hist(raw, tickers, PRICE_FIELD)


def load_curves(
    complex_name: str = "BOTH",
    start: datetime | None = None,
    end: datetime | None = None,
    *,
    use_cache: bool = True,
    refresh: bool = False,
    on_server: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Return {product: DataFrame with columns F1..Fn}.

    complex_name: 'US' | 'ICE' | 'BOTH'
    """
    start = start or CURVE_START
    end = end or DEFAULT_END
    products: dict[str, list[str]] = {}
    if complex_name in ("US", "BOTH"):
        products.update(US_CURVE)
    if complex_name in ("ICE", "BOTH"):
        products.update(ICE_CURVE)

    curves: dict[str, pd.DataFrame] = {}
    for product, tickers in products.items():
        key = f"curve_{product}_{start:%Y%m%d}_{end:%Y%m%d}_{PRICE_FIELD}"

        def _builder(p=product, t=tickers):
            return _pull_product_curve(p, t, start, end, on_server)

        curves[product] = cached_frame(key, _builder, use_cache=use_cache, refresh=refresh)
    return curves


def contango_pct(curve: pd.DataFrame, near: int = 1, deferred: int = 2) -> pd.Series:
    """(F_deferred - F_near) / F_near — positive = contango."""
    n, d = f"F{near}", f"F{deferred}"
    return (curve[d] - curve[n]) / curve[n]


def calendar_spread(curve: pd.DataFrame, near: int = 1, deferred: int = 2) -> pd.Series:
    """Front minus back (price points)."""
    return curve[f"F{near}"] - curve[f"F{deferred}"]


def crack_321(
    cl: pd.DataFrame,
    xb: pd.DataFrame,
    ho: pd.DataFrame,
    products_in_cents: bool = True,
) -> pd.Series:
    """
    Classic 3-2-1 crack in $/bbl using front months:
      (2 * RBOB_bbl + HO_bbl - 3 * CL) / 3

    Bloomberg XB/HO generics are usually quoted in US cents/gal, so we convert
    cents -> $/gal (/100) then *42 to $/bbl. Set products_in_cents=False if your
    marks are already in $/gal.
    """
    scale = 100.0 if products_in_cents else 1.0
    rbob_bbl = (xb["F1"] / scale) * 42.0
    ho_bbl = (ho["F1"] / scale) * 42.0
    return (2 * rbob_bbl + ho_bbl - 3 * cl["F1"]) / 3


def crack_brent_gasoil(co: pd.DataFrame, qs: pd.DataFrame, factor: float = 7.45) -> pd.Series:
    """
    Rough Brent–gasoil crack: QS ($/mt) / factor → $/bbl, minus CO.
    factor ~7.45 bbl/mt is a common desk approximation; tune as needed.
    """
    return qs["F1"] / factor - co["F1"]
