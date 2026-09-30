"""
Main backtest runner.

Usage:
    python run_backtest.py --source csv --file data/sample.csv --strategy breakout
    python run_backtest.py --source ib --symbol ES --strategy momentum
    python run_backtest.py --source bloomberg --ticker "ESA Index" --strategy mean_reversion
    python run_backtest.py --source generate --strategy breakout  # use synthetic data
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ACCOUNT, DATA
from strategies.breakout import BreakoutStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from utils.metrics import calculate_metrics, print_report, plot_equity_curves


STRATEGIES = {
    "breakout": BreakoutStrategy,
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
}


def load_data(source: str, **kwargs):
    """Load data from the specified source."""
    if source == "csv":
        from data.csv_loader import load_csv
        return load_csv(kwargs["file"])

    elif source == "generate":
        from data.csv_loader import generate_sample_data
        bars = kwargs.get("bars", 1000)
        print(f"Generating {bars} bars of synthetic data...")
        return generate_sample_data(bars=bars)

    elif source == "bloomberg":
        from data.bloomberg_pipeline import BloombergPipeline
        bbg = BloombergPipeline()
        ticker = kwargs.get("ticker", "ESA Index")
        return bbg.get_historical(ticker, DATA.start_date, DATA.end_date)

    elif source == "ib":
        from data.ib_pipeline import get_ib_data
        symbol = kwargs.get("symbol", "ES")
        return get_ib_data(symbol, DATA.timeframe)

    else:
        raise ValueError(f"Unknown source: {source}. Use: csv, generate, bloomberg, ib")


def main():
    parser = argparse.ArgumentParser(description="Backtest trading strategies")
    parser.add_argument("--source", default="generate",
                        choices=["csv", "generate", "bloomberg", "ib"],
                        help="Data source")
    parser.add_argument("--file", default=None, help="CSV file path (for --source csv)")
    parser.add_argument("--symbol", default="ES", help="IB symbol (for --source ib)")
    parser.add_argument("--ticker", default="ESA Index", help="Bloomberg ticker (for --source bloomberg)")
    parser.add_argument("--strategy", default="breakout",
                        choices=list(STRATEGIES.keys()),
                        help="Strategy to test")
    parser.add_argument("--instrument", default="MES", help="Instrument for position sizing (e.g., MES, ES, NQ)")
    parser.add_argument("--bars", type=int, default=1000, help="Bars for synthetic data")
    parser.add_argument("--no-plot", action="store_true", help="Skip chart generation")
    args = parser.parse_args()

    # Load data
    df = load_data(args.source, file=args.file, symbol=args.symbol,
                   ticker=args.ticker, bars=args.bars)

    if df.empty or len(df) < DATA.min_bars_required:
        print(f"Error: Need at least {DATA.min_bars_required} bars, got {len(df)}")
        return

    # Run strategy
    strategy_class = STRATEGIES[args.strategy]
    strategy = strategy_class(instrument=args.instrument)
    trades_df = strategy.run(df)

    if trades_df.empty:
        print("\nNo trades generated. Try adjusting strategy parameters in config.py")
        return

    # Calculate and print metrics
    metrics = calculate_metrics(trades_df, ACCOUNT.balance)
    print_report(metrics, strategy.name)

    # Save trade log
    output_file = f"trades_{args.strategy}_{args.instrument}.csv"
    trades_df.to_csv(output_file, index=False)
    print(f"Trade log saved: {output_file}")

    # Plot
    if not args.no_plot:
        plot_equity_curves({strategy.name: trades_df}, ACCOUNT.balance)

    return metrics, trades_df


if __name__ == "__main__":
    main()
