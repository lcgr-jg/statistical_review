"""
Compare all three strategies on the same data.

Usage:
    python run_comparison.py --source generate --bars 2000
    python run_comparison.py --source csv --file data/ES_1h.csv
    python run_comparison.py --source ib --symbol MES
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ACCOUNT, DATA
from strategies.breakout import BreakoutStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from utils.metrics import (calculate_metrics, print_report, compare_strategies,
                            plot_equity_curves)
from run_backtest import load_data


def main():
    parser = argparse.ArgumentParser(description="Compare all strategies")
    parser.add_argument("--source", default="generate",
                        choices=["csv", "generate", "bloomberg", "ib"])
    parser.add_argument("--file", default=None)
    parser.add_argument("--symbol", default="ES")
    parser.add_argument("--ticker", default="ESA Index")
    parser.add_argument("--instrument", default="MES")
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    # Load data once
    df = load_data(args.source, file=args.file, symbol=args.symbol,
                   ticker=args.ticker, bars=args.bars)

    if df.empty or len(df) < DATA.min_bars_required:
        print(f"Error: Need at least {DATA.min_bars_required} bars")
        return

    print(f"\nData loaded: {len(df)} bars")
    print(f"Period: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print(f"Instrument: {args.instrument}")
    print(f"Starting balance: ${ACCOUNT.balance:,.2f}")
    print(f"Risk per trade: {ACCOUNT.risk_per_trade_pct:.1%}")

    # Run each strategy on the same data
    strategies = [
        BreakoutStrategy(instrument=args.instrument),
        MomentumStrategy(instrument=args.instrument),
        MeanReversionStrategy(instrument=args.instrument),
    ]

    all_metrics = {}
    all_trades = {}

    for strat in strategies:
        trades_df = strat.run(df.copy())
        if trades_df.empty:
            print(f"\n{strat.name}: No trades generated")
            all_metrics[strat.name] = calculate_metrics(trades_df, ACCOUNT.balance)
        else:
            metrics = calculate_metrics(trades_df, ACCOUNT.balance)
            print_report(metrics, strat.name)
            all_metrics[strat.name] = metrics
            all_trades[strat.name] = trades_df

            # Save individual trade logs
            trades_df.to_csv(f"trades_{strat.name.lower().replace(' ','_')}_{args.instrument}.csv",
                             index=False)

    # Side-by-side comparison
    if len(all_metrics) > 1:
        compare_strategies(all_metrics)

    # Equity curve comparison chart
    if all_trades and not args.no_plot:
        plot_equity_curves(all_trades, ACCOUNT.balance)

    # Print recommendation
    print("\n" + "=" * 60)
    print("  RECOMMENDATION")
    print("=" * 60)

    valid = {k: v for k, v in all_metrics.items() if v.get("total_trades", 0) > 0}
    if valid:
        best_sharpe = max(valid, key=lambda k: valid[k].get("sharpe_ratio", -999))
        best_pf = max(valid, key=lambda k: valid[k].get("profit_factor", 0))
        least_dd = max(valid, key=lambda k: valid[k].get("max_drawdown_pct", -999))

        print(f"\n  Best risk-adjusted (Sharpe):  {best_sharpe}")
        print(f"  Best profit factor:           {best_pf}")
        print(f"  Smallest drawdown:            {least_dd}")
        print(f"\n  Start paper trading the top performer for 2-4 weeks.")
        print(f"  If results hold, you've found your edge.")
    else:
        print("\n  No strategies produced trades. Adjust parameters in config.py")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
