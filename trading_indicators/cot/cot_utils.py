"""Helpers for crude-oil Managed Money % Short from CFTC Disaggregated COT."""

from __future__ import annotations

from pathlib import Path

import cot_reports as cot
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

# Per-series parquet caches
WTI_CACHE = DATA_DIR / "wti_managed_money.parquet"
BRENT_CACHE = DATA_DIR / "brent_managed_money.parquet"
AGG_CACHE = DATA_DIR / "aggregate_crude_managed_money.parquet"

# NYMEX WTI — label changed when deliverable spec shifted (Feb 2022).
WTI_LEGACY = "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"
WTI_PHYSICAL = "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE"

# Brent — ICE Europe through 2014, then NYMEX-listed Brent Last Day contracts.
BRENT_ICE = "CRUDE OIL, LIGHT SWEET - ICE FUTURES EUROPE"
BRENT_NYMEX_LEGACY = "BRENT CRUDE OIL LAST DAY - NEW YORK MERCANTILE EXCHANGE"
BRENT_NYMEX = "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE"

DEFAULT_ROLLING_WEEKS = 156  # ~3 years of weekly COT reports
DEFAULT_UPPER_Q = 0.90
DEFAULT_LOWER_Q = 0.10

# (market name, stitch priority) — lower priority wins on duplicate report dates
WTI_MARKET_CHAIN: list[tuple[str, int]] = [
    (WTI_LEGACY, 0),
    (WTI_PHYSICAL, 1),
]
BRENT_MARKET_CHAIN: list[tuple[str, int]] = [
    (BRENT_ICE, 0),
    (BRENT_NYMEX_LEGACY, 1),
    (BRENT_NYMEX, 2),
]


def _extract_mm_rows(raw: pd.DataFrame, markets: list[tuple[str, int]]) -> pd.DataFrame:
    """Pull Managed Money long/short for a chain of CFTC market labels."""
    frames = []
    for market, priority in markets:
        part = raw[raw["Market_and_Exchange_Names"] == market].copy()
        if part.empty:
            continue
        part["report_date"] = pd.to_datetime(part["Report_Date_as_YYYY-MM-DD"])
        part["mm_long"] = pd.to_numeric(part["M_Money_Positions_Long_All"], errors="coerce")
        part["mm_short"] = pd.to_numeric(part["M_Money_Positions_Short_All"], errors="coerce")
        part["open_interest"] = pd.to_numeric(part["Open_Interest_All"], errors="coerce")
        part["source_market"] = market
        part["priority"] = priority
        frames.append(part)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["report_date", "priority"]).drop_duplicates("report_date", keep="first")
    df = df[(df["mm_long"] + df["mm_short"]) > 0].copy()
    df["pct_short"] = df["mm_short"] / (df["mm_long"] + df["mm_short"]) * 100
    return df[
        ["report_date", "mm_long", "mm_short", "open_interest", "pct_short", "source_market"]
    ].reset_index(drop=True)


def _download_raw() -> pd.DataFrame:
    return cot.cot_all(cot_report_type="disaggregated_fut")


def _load_series(
    markets: list[tuple[str, int]],
    cache_path: Path,
    use_cache: bool = True,
) -> pd.DataFrame:
    if use_cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    raw = _download_raw()
    out = _extract_mm_rows(raw, markets)
    if out.empty:
        raise ValueError(f"No rows found for markets: {[m for m, _ in markets]}")

    if use_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(cache_path, index=False)
    return out


def load_wti_managed_money(use_cache: bool = True) -> pd.DataFrame:
    """NYMEX WTI Managed Money % Short (legacy + physical stitch)."""
    return _load_series(WTI_MARKET_CHAIN, WTI_CACHE, use_cache=use_cache)


def load_brent_managed_money(use_cache: bool = True) -> pd.DataFrame:
    """Brent Managed Money % Short (ICE Europe legacy + NYMEX Last Day stitch)."""
    return _load_series(BRENT_MARKET_CHAIN, BRENT_CACHE, use_cache=use_cache)


def load_aggregate_crude_managed_money(use_cache: bool = True) -> pd.DataFrame:
    """
    Combined WTI (NYMEX) + Brent Managed Money positioning.

    Aggregates by summing MM long and short across both benchmarks on each
    report date, then recomputing % short on the combined book.
    """
    if use_cache and AGG_CACHE.exists():
        return pd.read_parquet(AGG_CACHE)

    wti = load_wti_managed_money(use_cache=use_cache)
    brent = load_brent_managed_money(use_cache=use_cache)
    merged = wti.merge(brent, on="report_date", suffixes=("_wti", "_brent"), how="inner")
    merged["mm_long"] = merged["mm_long_wti"] + merged["mm_long_brent"]
    merged["mm_short"] = merged["mm_short_wti"] + merged["mm_short_brent"]
    merged["open_interest"] = merged["open_interest_wti"] + merged["open_interest_brent"]
    merged["pct_short"] = merged["mm_short"] / (merged["mm_long"] + merged["mm_short"]) * 100
    merged["source_market"] = "AGGREGATE (WTI NYMEX + Brent)"

    out = merged[
        ["report_date", "mm_long", "mm_short", "open_interest", "pct_short", "source_market"]
    ].reset_index(drop=True)

    if use_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(AGG_CACHE, index=False)
    return out


def load_disaggregated_raw(use_cache: bool = True) -> pd.DataFrame:
    """Backward-compatible alias for WTI series."""
    return load_wti_managed_money(use_cache=use_cache)


def add_rolling_thresholds(
    df: pd.DataFrame,
    window: int = DEFAULT_ROLLING_WEEKS,
    upper_q: float = DEFAULT_UPPER_Q,
    lower_q: float = DEFAULT_LOWER_Q,
    min_periods: int = 52,
) -> pd.DataFrame:
    """Add rolling upper/lower bands and median from the indicator's own history."""
    out = df.copy()
    roll = out["pct_short"].rolling(window, min_periods=min_periods)
    out["upper"] = roll.quantile(upper_q)
    out["lower"] = roll.quantile(lower_q)
    out["median"] = roll.quantile(0.50)
    return out


def plot_pct_short(
    df: pd.DataFrame,
    title: str,
    *,
    color: str = "#2aa198",
) -> None:
    """Standard Managed Money % Short chart with rolling bands."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plot_df = df.dropna(subset=["upper", "lower"]).copy()
    last_val = plot_df["pct_short"].iloc[-1]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        plot_df["report_date"],
        plot_df["pct_short"],
        color=color,
        linewidth=1.5,
        label=f"Managed Money % Short (Last: {last_val:.2f}%)",
    )
    ax.plot(
        plot_df["report_date"],
        plot_df["upper"],
        color="#6c71c4",
        linestyle="--",
        linewidth=1,
        label="Rolling 90th pct (3y)",
    )
    ax.plot(
        plot_df["report_date"],
        plot_df["lower"],
        color="#6c71c4",
        linestyle="--",
        linewidth=1,
        label="Rolling 10th pct (3y)",
    )
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Percent")
    ax.legend(loc="upper center", ncol=3, frameon=False)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(plot_df["report_date"].min(), plot_df["report_date"].max())
    freq = (
        f"Weekly COT {plot_df['report_date'].min():%Y-%m-%d} "
        f"to {plot_df['report_date'].max():%Y-%m-%d}"
    )
    ax.text(0.99, 0.98, freq, transform=ax.transAxes, ha="right", va="top", fontsize=9, color="gray")
    fig.tight_layout()
    plt.show()


def fetch_wti_prices(start: str = "2006-01-01") -> pd.Series:
    """Front-month WTI continuous futures via yfinance (CL=F)."""
    import yfinance as yf

    px = yf.download("CL=F", start=start, progress=False)["Close"]
    if isinstance(px, pd.DataFrame):
        px = px.iloc[:, 0]
    px.index = pd.to_datetime(px.index)
    px.name = "close"
    return px.dropna()


def backtest_contrarian_extremes(
    cot_df: pd.DataFrame,
    prices: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simple weekly contrarian backtest:
    - Go long when prior week's % short >= rolling upper band (crowded shorts).
    - Go short when prior week's % short <= rolling lower band (crowded longs).
    - Exit to flat when % short crosses back through the rolling median.

    Positions apply to the following week's return (no look-ahead on thresholds).
    """
    weekly_px = prices.resample("W-TUE").last().rename("close")
    data = cot_df.merge(weekly_px, left_on="report_date", right_index=True, how="inner")
    data = data.sort_values("report_date").reset_index(drop=True)
    data["ret_1w"] = data["close"].pct_change()

    position = 0
    trades: list[dict] = []
    positions: list[int] = []

    for i in range(len(data)):
        if i == 0:
            positions.append(0)
            continue

        prev = data.iloc[i - 1]
        signal = position

        if pd.notna(prev["upper"]):
            if prev["pct_short"] >= prev["upper"]:
                signal = 1
            elif prev["pct_short"] <= prev["lower"]:
                signal = -1
            elif position == 1 and prev["pct_short"] <= prev["median"]:
                signal = 0
            elif position == -1 and prev["pct_short"] >= prev["median"]:
                signal = 0

        if signal != position:
            trades.append(
                {
                    "date": data.iloc[i]["report_date"],
                    "from_position": position,
                    "to_position": signal,
                    "pct_short": prev["pct_short"],
                    "upper": prev["upper"],
                    "lower": prev["lower"],
                    "price": data.iloc[i]["close"],
                }
            )
            position = signal

        positions.append(position)

    data["position"] = positions
    data["strategy_ret"] = data["position"].shift(1).fillna(0) * data["ret_1w"]
    return data, pd.DataFrame(trades)


def summarize_backtest(bt: pd.DataFrame, label: str = "Contrarian COT") -> dict:
    """Basic performance stats for the weekly strategy."""
    rets = bt["strategy_ret"].dropna()
    eq = (1 + rets).cumprod()
    total = eq.iloc[-1] - 1 if len(eq) else 0.0
    ann_factor = 52
    sharpe = (
        rets.mean() / rets.std() * (ann_factor**0.5)
        if len(rets) > 1 and rets.std() > 0
        else float("nan")
    )
    dd = (eq / eq.cummax() - 1).min() if len(eq) else 0.0
    active = rets[rets != 0]
    win_rate = (active > 0).mean() if len(active) else float("nan")

    bh = (1 + bt["ret_1w"].dropna()).cumprod()
    bh_total = bh.iloc[-1] - 1 if len(bh) else float("nan")

    return {
        "label": label,
        "weeks": len(rets),
        "total_return": total,
        "buy_hold_return": bh_total,
        "sharpe": sharpe,
        "max_drawdown": dd,
        "win_rate_active_weeks": win_rate,
        "pct_time_in_market": (bt["position"].shift(1).fillna(0) != 0).mean(),
    }
