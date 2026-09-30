"""Plot helpers for the regime cookbook notebook."""
from __future__ import annotations

from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import STRESS_WINDOWS


def _shade_stress(ax, windows: dict | None = None):
    windows = windows or STRESS_WINDOWS
    for i, (name, (start, end)) in enumerate(windows.items()):
        ax.axvspan(start, end, color="0.85" if i % 2 == 0 else "0.92", alpha=0.8, zorder=0)


def plot_curve_and_contango(curve: pd.DataFrame, title: str = "CL curve"):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    axes[0].plot(curve.index, curve["F1"], label="F1")
    axes[0].plot(curve.index, curve["F2"], label="F2", alpha=0.8)
    axes[0].set_ylabel("Price")
    axes[0].set_title(title)
    axes[0].legend(loc="upper left")
    _shade_stress(axes[0])

    contango = (curve["F2"] - curve["F1"]) / curve["F1"] * 100
    axes[1].plot(contango.index, contango, color="C2")
    axes[1].axhline(0, color="k", lw=0.8)
    axes[1].set_ylabel("Contango % (F2-F1)/F1")
    axes[1].set_title("Curve shape — positive = contango")
    _shade_stress(axes[1])
    fig.tight_layout()
    return fig


def plot_inventory_regime(stocks: pd.Series, inv_z: pd.Series, title: str = "Inventory"):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    axes[0].plot(stocks.index, stocks, color="C0")
    axes[0].set_title(f"{title} — stocks")
    axes[0].set_ylabel("mbbl / units")
    _shade_stress(axes[0])

    axes[1].plot(inv_z.index, inv_z, color="C3")
    axes[1].axhline(0, color="k", lw=0.8)
    axes[1].axhline(-0.5, color="C1", ls="--", lw=0.8, label="low_inv thresh")
    axes[1].axhline(0.5, color="C2", ls="--", lw=0.8, label="high_inv thresh")
    axes[1].set_ylabel("5y seasonal z")
    axes[1].legend(loc="upper left")
    _shade_stress(axes[1])
    fig.tight_layout()
    return fig


def plot_spread_with_trades(
    spread: pd.Series,
    trades: pd.DataFrame,
    regime: pd.Series | None = None,
    title: str = "Spread + trades",
):
    """Mark entries (green long / red short) and exits on the spread path."""
    n_rows = 2 if regime is not None else 1
    fig, axes = plt.subplots(n_rows, 1, figsize=(12, 3.5 * n_rows), sharex=True)
    if n_rows == 1:
        axes = [axes]

    axes[0].plot(spread.index, spread, color="0.3", lw=1, label="spread")
    if trades is not None and not trades.empty:
        t = trades.copy()
        t["entry_date"] = pd.to_datetime(t["entry_date"])
        t["exit_date"] = pd.to_datetime(t["exit_date"])
        longs = t[t["direction"] > 0]
        shorts = t[t["direction"] < 0]
        axes[0].scatter(longs["entry_date"], longs["entry_level"], c="green", s=28, label="long entry", zorder=3)
        axes[0].scatter(shorts["entry_date"], shorts["entry_level"], c="red", s=28, label="short entry", zorder=3)
        # win/loss exits
        wins = t[t["pnl_net"] > 0]
        losses = t[t["pnl_net"] <= 0]
        axes[0].scatter(wins["exit_date"], wins["exit_level"], marker="x", c="green", s=20, alpha=0.7)
        axes[0].scatter(losses["exit_date"], losses["exit_level"], marker="x", c="red", s=20, alpha=0.7)
    axes[0].set_title(title)
    axes[0].legend(loc="upper left", fontsize=8)
    _shade_stress(axes[0])

    if regime is not None:
        axes[1].plot(regime.index, regime, color="C4")
        axes[1].set_ylabel("regime")
        axes[1].set_title("Regime variable (continuous)")
        _shade_stress(axes[1])
    fig.tight_layout()
    return fig


def plot_bucket_bars(buckets: pd.DataFrame, metric: str = "sharpe_net", title: str | None = None):
    df = buckets[buckets["bucket"] != "UNCONDITIONAL"].copy()
    if df.empty:
        df = buckets.copy()
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["C0" if v >= 0 else "C3" for v in df[metric]]
    ax.bar(df["bucket"].astype(str), df[metric], color=colors)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel(metric)
    ax.set_title(title or f"Regime buckets — {metric}")
    fig.tight_layout()
    return fig


def plot_pnl_vs_regime(trades: pd.DataFrame, title: str = "PnL vs regime at entry"):
    fig, ax = plt.subplots(figsize=(7, 5))
    t = trades.dropna(subset=["regime_value", "pnl_net"])
    ax.scatter(t["regime_value"], t["pnl_net"], alpha=0.5, s=22)
    if len(t) >= 5:
        x = t["regime_value"].values
        y = t["pnl_net"].values
        coef = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, np.polyval(coef, xs), color="C3", lw=2, label=f"linear fit slope={coef[0]:.3g}")
        # quadratic for threshold intuition
        coef2 = np.polyfit(x, y, 2)
        ax.plot(xs, np.polyval(coef2, xs), color="C1", lw=1.5, ls="--", label="quadratic")
        ax.legend(fontsize=8)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("regime_value at entry")
    ax.set_ylabel("pnl_net")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_equity(trades: pd.DataFrame, title: str = "Trade equity curve"):
    fig, ax = plt.subplots(figsize=(12, 3.5))
    t = trades.sort_values("exit_date").copy()
    t["exit_date"] = pd.to_datetime(t["exit_date"])
    eq = t["pnl_net"].cumsum()
    ax.plot(t["exit_date"], eq, color="C0")
    ax.axhline(0, color="k", lw=0.6)
    _shade_stress(ax)
    ax.set_title(title)
    ax.set_ylabel("cumulative pnl_net")
    fig.tight_layout()
    return fig


def playbook_table(rows: Iterable[dict]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))
