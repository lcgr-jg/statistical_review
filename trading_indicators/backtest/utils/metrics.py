"""
Performance analytics — calculates everything an institutional desk would track.
"""
import pandas as pd
import numpy as np


def calculate_metrics(trades: pd.DataFrame, initial_balance: float = 10_000) -> dict:
    """
    Comprehensive performance metrics from a DataFrame of closed trades.
    Expected columns: entry_price, exit_price, direction, pnl, r_multiple,
                      strategy, entry_time, exit_time
    """
    if trades.empty:
        return {"error": "No trades to analyze"}

    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] < 0]
    flat = trades[trades["pnl"] == 0]

    total = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / total if total > 0 else 0

    total_pnl = trades["pnl"].sum()
    avg_win = wins["pnl"].mean() if n_wins > 0 else 0
    avg_loss = losses["pnl"].mean() if n_losses > 0 else 0
    largest_win = wins["pnl"].max() if n_wins > 0 else 0
    largest_loss = losses["pnl"].min() if n_losses > 0 else 0

    # Expectancy: avg $ per trade
    expectancy = total_pnl / total if total > 0 else 0

    # Profit factor: gross wins / gross losses
    gross_wins = wins["pnl"].sum() if n_wins > 0 else 0
    gross_losses = abs(losses["pnl"].sum()) if n_losses > 0 else 1
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    # R-multiple stats
    avg_r = trades["r_multiple"].mean() if "r_multiple" in trades.columns else 0
    max_r = trades["r_multiple"].max() if "r_multiple" in trades.columns else 0
    min_r = trades["r_multiple"].min() if "r_multiple" in trades.columns else 0

    # Equity curve and drawdown
    equity = initial_balance + trades["pnl"].cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max
    max_drawdown_dollar = drawdown.min()
    max_drawdown_pct = (drawdown / running_max).min() if running_max.max() > 0 else 0

    # Sharpe ratio (annualized, assuming ~252 trading days)
    if "pnl" in trades.columns and len(trades) > 1:
        daily_returns = trades["pnl"] / initial_balance
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
    else:
        sharpe = 0

    # Sortino ratio (only penalizes downside volatility)
    if len(trades) > 1:
        downside = daily_returns[daily_returns < 0]
        sortino = (daily_returns.mean() / downside.std()) * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0
    else:
        sortino = 0

    # Consecutive wins/losses
    streak = trades["pnl"].apply(lambda x: 1 if x > 0 else -1)
    max_consec_wins = _max_consecutive(streak, 1)
    max_consec_losses = _max_consecutive(streak, -1)

    # Average hold time
    if "entry_time" in trades.columns and "exit_time" in trades.columns:
        trades_copy = trades.copy()
        trades_copy["hold_time"] = pd.to_datetime(trades_copy["exit_time"]) - pd.to_datetime(trades_copy["entry_time"])
        avg_hold = trades_copy["hold_time"].mean()
    else:
        avg_hold = "N/A"

    # Recovery factor
    recovery_factor = total_pnl / abs(max_drawdown_dollar) if max_drawdown_dollar != 0 else 0

    return {
        "total_trades": total,
        "wins": n_wins,
        "losses": n_losses,
        "flat": len(flat),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "expectancy_per_trade": expectancy,
        "profit_factor": profit_factor,
        "avg_r_multiple": avg_r,
        "best_r": max_r,
        "worst_r": min_r,
        "max_drawdown_dollar": max_drawdown_dollar,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "recovery_factor": recovery_factor,
        "max_consecutive_wins": max_consec_wins,
        "max_consecutive_losses": max_consec_losses,
        "avg_hold_time": str(avg_hold),
        "final_balance": initial_balance + total_pnl,
        "return_pct": total_pnl / initial_balance,
    }


def _max_consecutive(series, value):
    """Count max consecutive occurrences of a value."""
    groups = (series != value).cumsum()
    filtered = series[series == value]
    if filtered.empty:
        return 0
    return filtered.groupby(groups).count().max()


def print_report(metrics: dict, strategy_name: str = ""):
    """Pretty-print a performance report."""
    title = f" {strategy_name} Performance Report " if strategy_name else " Performance Report "
    print(f"\n{'='*60}")
    print(f"{title:=^60}")
    print(f"{'='*60}")

    sections = {
        "Trade Summary": [
            ("Total Trades", f"{metrics['total_trades']}"),
            ("Wins / Losses / Flat", f"{metrics['wins']} / {metrics['losses']} / {metrics['flat']}"),
            ("Win Rate", f"{metrics['win_rate']:.1%}"),
        ],
        "P&L": [
            ("Total Net P&L", f"${metrics['total_pnl']:,.2f}"),
            ("Avg Win", f"${metrics['avg_win']:,.2f}"),
            ("Avg Loss", f"${metrics['avg_loss']:,.2f}"),
            ("Largest Win", f"${metrics['largest_win']:,.2f}"),
            ("Largest Loss", f"${metrics['largest_loss']:,.2f}"),
            ("Expectancy/Trade", f"${metrics['expectancy_per_trade']:,.2f}"),
            ("Profit Factor", f"{metrics['profit_factor']:.2f}"),
        ],
        "Risk Metrics": [
            ("Max Drawdown ($)", f"${metrics['max_drawdown_dollar']:,.2f}"),
            ("Max Drawdown (%)", f"{metrics['max_drawdown_pct']:.1%}"),
            ("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}"),
            ("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}"),
            ("Recovery Factor", f"{metrics['recovery_factor']:.2f}"),
        ],
        "R-Multiple": [
            ("Avg R-Multiple", f"{metrics['avg_r_multiple']:.2f}R"),
            ("Best Trade", f"{metrics['best_r']:.2f}R"),
            ("Worst Trade", f"{metrics['worst_r']:.2f}R"),
        ],
        "Streaks & Timing": [
            ("Max Consecutive Wins", f"{metrics['max_consecutive_wins']}"),
            ("Max Consecutive Losses", f"{metrics['max_consecutive_losses']}"),
            ("Avg Hold Time", f"{metrics['avg_hold_time']}"),
        ],
        "Bottom Line": [
            ("Final Balance", f"${metrics['final_balance']:,.2f}"),
            ("Total Return", f"{metrics['return_pct']:.1%}"),
        ],
    }

    for section, items in sections.items():
        print(f"\n  {section}")
        print(f"  {'-'*40}")
        for label, value in items:
            print(f"  {label:<28} {value:>12}")
    print(f"\n{'='*60}\n")


def compare_strategies(results: dict[str, dict]):
    """Side-by-side comparison of multiple strategy results."""
    strategies = list(results.keys())
    print(f"\n{'='*80}")
    print(f"{'STRATEGY COMPARISON':^80}")
    print(f"{'='*80}")

    key_metrics = [
        ("Total Trades", "total_trades", "d"),
        ("Win Rate", "win_rate", ".1%"),
        ("Total P&L", "total_pnl", ",.2f"),
        ("Expectancy/Trade", "expectancy_per_trade", ",.2f"),
        ("Profit Factor", "profit_factor", ".2f"),
        ("Sharpe Ratio", "sharpe_ratio", ".2f"),
        ("Max Drawdown %", "max_drawdown_pct", ".1%"),
        ("Avg R-Multiple", "avg_r_multiple", ".2f"),
        ("Max Consec Losses", "max_consecutive_losses", "d"),
        ("Return %", "return_pct", ".1%"),
    ]

    # Header
    header = f"  {'Metric':<24}"
    for s in strategies:
        header += f" {s:>16}"
    print(header)
    print(f"  {'-'*24}" + f" {'-'*16}" * len(strategies))

    for label, key, fmt in key_metrics:
        row = f"  {label:<24}"
        values = []
        for s in strategies:
            val = results[s].get(key, 0)
            if fmt.endswith("%"):
                row += f" {val:>15{fmt}}"
            elif fmt.endswith("f"):
                row += f" ${val:>14{fmt}}" if "pnl" in key.lower() or "expectancy" in key.lower() else f" {val:>15{fmt}}"
            else:
                row += f" {val:>15{fmt}}"
            values.append(val)
        # Highlight best
        print(row)

    print(f"\n{'='*80}\n")


def plot_equity_curves(all_trades: dict[str, pd.DataFrame], initial_balance: float = 10_000):
    """Plot equity curves for multiple strategies."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]})

        colors = {"Breakout": "#3498DB", "Momentum": "#27AE60", "Mean Reversion": "#E74C3C"}

        # Equity curves
        ax1 = axes[0]
        for name, trades in all_trades.items():
            if trades.empty:
                continue
            equity = initial_balance + trades["pnl"].cumsum()
            color = colors.get(name, "#333333")
            ax1.plot(equity.values, label=f"{name} (${equity.iloc[-1] - initial_balance:+,.0f})",
                     color=color, linewidth=1.5)

        ax1.axhline(y=initial_balance, color="gray", linestyle="--", alpha=0.5)
        ax1.set_title("Equity Curves — Strategy Comparison", fontsize=14, fontweight="bold")
        ax1.set_ylabel("Account Balance ($)")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)

        # Drawdown
        ax2 = axes[1]
        for name, trades in all_trades.items():
            if trades.empty:
                continue
            equity = initial_balance + trades["pnl"].cumsum()
            dd = (equity - equity.cummax()) / equity.cummax() * 100
            color = colors.get(name, "#333333")
            ax2.fill_between(range(len(dd)), dd.values, 0, alpha=0.3, color=color, label=name)

        ax2.set_title("Drawdown (%)", fontsize=12)
        ax2.set_ylabel("Drawdown %")
        ax2.set_xlabel("Trade #")
        ax2.legend(loc="lower left")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("strategy_comparison.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Chart saved: strategy_comparison.png")
    except ImportError:
        print("matplotlib not available — skipping chart generation")
